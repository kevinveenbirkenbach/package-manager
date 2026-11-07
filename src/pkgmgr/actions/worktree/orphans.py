from __future__ import annotations

import json
import time
from dataclasses import asdict

from pkgmgr.actions.branch.gc import Item, human_size, prepare

DAY = 86400
ORDER = ("merged-clean", "merged-dirty", "stale-open", "stale", "active")
PROPOSALS = {
    "merged-clean": "pkgmgr gc",
    "merged-dirty": "ask",
    "stale-open": "ask",
    "stale": "git worktree prune",
    "active": "keep",
}
GUARDS = ("process:", "lock:")
HEADER = (
    "Class",
    "Branch",
    "Worktree",
    "Dirty",
    "Unpushed",
    "Last activity",
    "Proposal",
)


def classify(item: Item, now: float, limit: float) -> str:
    """
    Sort one scanned item into an orphan class.

    Args:
        item: item from a scan with activity recorded.
        now: current epoch seconds.
        limit: seconds of inactivity after which unfinished work is stale.

    Returns:
        One of ORDER.
    """
    if item.state == "stale":
        return "stale"
    if (
        item.state == "protected"
        or (item.branch or "").startswith("archive/")
        or item.skip == "checked out in main worktree"
    ):
        return "active"
    if item.merged:
        return "merged-dirty" if item.state == "dirty" else "merged-clean"
    pending = item.state == "dirty" or bool(item.unpushed) or not item.remotes
    idle = item.last_activity is not None and now - item.last_activity > limit
    guarded = bool(item.skip) and item.skip.startswith(GUARDS)
    return "stale-open" if pending and idle and not guarded else "active"


def proposal(item: Item, cls: str) -> str:
    if cls == "active":
        return "keep"
    if item.skip and item.skip.startswith(GUARDS):
        return f"keep ({item.skip})"
    return PROPOSALS[cls]


def _cells(row: dict, now: float, sizes: bool) -> list[str]:
    activity = row["last_activity"]
    when = (
        f"{time.strftime('%Y-%m-%d', time.localtime(activity))} "
        f"({int((now - activity) // DAY)} d)"
        if activity
        else "-"
    )
    values = [
        row["class"],
        row["branch"] or "(detached)",
        row["worktree"] or "-",
        *(
            [human_size(row["size_bytes"]) if row["size_bytes"] else "-"]
            if sizes
            else []
        ),
        str(row["dirty"]),
        "-" if row["unpushed"] is None else str(row["unpushed"]),
        when,
        row["proposal"],
    ]
    return [value.replace("|", "\\|") for value in values]


def _table(rows: list[dict], now: float, sizes: bool) -> list[str]:
    header = [*HEADER[:3], *(["Size"] if sizes else []), *HEADER[3:]]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    return lines + ["| " + " | ".join(_cells(r, now, sizes)) + " |" for r in rows]


def worktree_orphans(
    repo_roots: list[str],
    *,
    stale_days: int,
    top: int,
    as_json: bool,
    include: list[str],
    exclude: list[str],
    merged_into: list[str],
    sizes: bool,
) -> int:
    """
    List merged and abandoned branches and worktrees with a proposal each.

    Read-only apart from the fetch the scan does. Merged covers ancestry, a
    merged pull request, an integration line and patch equivalence.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        stale_days: unfinished work idle for longer is stale-open.
        top: rows per class in the text table; 0 shows the counts only.
        as_json: print every row, active ones included, as JSON.
        include: only items whose branch or worktree path matches one of these.
        exclude: drop items whose branch or worktree path matches one of these.
        merged_into: integration lines (refs) that also count as merged.
        sizes: measure each worktree's disk usage and order by it.

    Returns:
        0 on success, 2 when refused.
    """
    options = {
        "merged_into": merged_into,
        "sizes": sizes,
        "min_age": None,
        "scope": "all",
        "activity": True,
        "hooks": {},
    }
    prepared = prepare(repo_roots, include, exclude, options)
    if prepared is None:
        return 2
    repos, host_ns, chosen = prepared
    now = time.time()
    limit = stale_days * DAY

    report = []
    for repo in repos:
        rows = []
        for item in repo.items:
            if not chosen(item):
                continue
            cls = classify(item, now, limit)
            rows.append({**asdict(item), "class": cls, "proposal": proposal(item, cls)})
        rows.sort(
            key=lambda r: (
                ORDER.index(r["class"]),
                -(r["size_bytes"] or 0) if sizes else 0,
                r["last_activity"] or 0,
            )
        )
        report.append({"repo": repo.repo, "warnings": repo.warnings, "rows": rows})

    if as_json:
        print(
            json.dumps(
                {
                    "host_pid_namespace": host_ns,
                    "stale_days": stale_days,
                    "repos": report,
                },
                indent=2,
            )
        )
        return 0
    for entry in report:
        print(f"== {entry['repo']} (stale after {stale_days} days)")
        for warning in entry["warnings"]:
            print(f"WARN     {warning}")
        for cls in ORDER:
            count = sum(r["class"] == cls for r in entry["rows"])
            print(f"- {cls}: {count} ({PROPOSALS[cls]})")
        shown = [
            row
            for cls in ORDER[:-1]
            for row in [r for r in entry["rows"] if r["class"] == cls][:top]
        ]
        if shown:
            print()
            print("\n".join(_table(shown, now, sizes)))
    if not host_ns:
        print(
            "WARN     busy and lock checks unavailable: not in the host PID namespace"
        )
    return 0
