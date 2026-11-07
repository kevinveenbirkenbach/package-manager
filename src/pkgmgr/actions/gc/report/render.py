from __future__ import annotations

from pkgmgr.actions.branch.gc import human_size

UNITS = (("d", 86400), ("h", 3600), ("m", 60))
DOCKER_COLUMNS = ("type", "total", "active", "size", "reclaimable")


def _size(value: int | None) -> str:
    return "-" if value is None else human_size(value)


def _age(now: float, stamp: float | None) -> str:
    if not stamp:
        return "-"
    seconds = max(0.0, now - stamp)
    for unit, length in UNITS:
        if seconds >= length:
            return f"{seconds / length:.1f}{unit}"
    return f"{seconds:.0f}s"


def _section(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return [f"== {title}", "(none)"]
    widths = [max(len(cell) for cell in column) for column in zip(headers, *rows)]
    return [f"== {title}"] + [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in (headers, *rows)
    ]


def _branch(tree: dict) -> str:
    if tree["orphaned"]:
        return "-"
    return tree["branch"] or "(detached)"


def _state(tree: dict) -> str:
    if tree["orphaned"]:
        return "orphaned"
    return "missing" if tree["missing"] else "linked"


def render_text(report: dict) -> str:
    """
    Render a disk_report result as aligned text tables.

    Args:
        report: the dict disk_report returned.

    Returns:
        The tables, one section per report key, newline-joined.
    """
    now = report["generated_at"]
    lines = _section(
        "worktrees",
        ["SIZE", "ACTIVE", "FOREIGN", "STATE", "BRANCH", "PATH"],
        [
            [
                _size(t["size_bytes"]),
                _age(now, t["last_activity"]),
                str(t["foreign_entries"]),
                _state(t),
                _branch(t),
                t["path"],
            ]
            for t in report["worktrees"]
        ],
    )
    lines += _section(
        "preserved (dirty worktrees)",
        ["PRESERVED", "PATHS", "BRANCH", "PATH", "REASONS"],
        [
            [
                "yes" if p["preserved"] else "no",
                "-" if p["paths"] is None else str(p["paths"]),
                p["branch"] or "(detached)",
                p["path"],
                "; ".join(p["reasons"]),
            ]
            for p in report["preserved"]
        ],
    )
    for root in report["roots"]:
        lines += _section(
            f"root {root['root']} (over {human_size(report['threshold_bytes'])})",
            ["SIZE", "AGE", "KIND", "PATH"],
            [
                [
                    _size(c["size_bytes"]),
                    _age(now, c["newest_mtime"]),
                    c["kind"],
                    c["path"],
                ]
                for c in root["children"]
            ],
        )
    lines += _section(
        "core dumps",
        ["SIZE", "APPARENT", "AGE", "PATH"],
        [
            [
                _size(d["size_bytes"]),
                _size(d["apparent_bytes"]),
                _age(now, d["mtime"]),
                d["path"],
            ]
            for d in report["core_dumps"]
        ],
    )
    if report["docker"] is not None:
        lines += _section(
            "docker",
            ["TYPE", "TOTAL", "ACTIVE", "SIZE", "RECLAIMABLE"],
            [[str(row[key]) for key in DOCKER_COLUMNS] for row in report["docker"]],
        )
    lines += _section(
        "balance",
        ["FILESYSTEM", "TOTAL", "FREE", "ATTRIBUTED"],
        [
            [
                fs["filesystem"],
                _size(fs["total_bytes"]),
                _size(fs["free_bytes"]),
                _size(fs["attributed_bytes"]),
            ]
            for fs in report["balance"]
        ],
    )
    lines += [f"WARN  {warning}" for warning in report["warnings"]]
    return "\n".join(lines)
