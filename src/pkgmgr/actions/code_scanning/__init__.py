"""Download GitHub code scanning results via the ``gh`` CLI.

Fetches all code scanning alerts (and the analysis metadata) for a
repository and writes them, plus a readable digest, into a timestamped
directory so they can be read and analysed offline. Authentication is
delegated to ``gh`` (credentials from its keyring/login).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


class CodeScanningError(RuntimeError):
    """Raised when code scanning results cannot be downloaded."""


@dataclass
class CodeScanningResult:
    repo: str
    output_dir: str
    alert_count: int
    files: List[str] = field(default_factory=list)


def _gh(args: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def _resolve_repo(repo: Optional[str]) -> str:
    if repo:
        return repo
    proc = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise CodeScanningError(
            "could not resolve the current repository; run inside a GitHub "
            "repo or pass --repo OWNER/REPO "
            f"({proc.stderr.strip()})"
        )
    return name


def _fetch_json(endpoint: str, params: Optional[List[str]] = None) -> Any:
    args = ["api", endpoint, "--paginate"]
    for param in params or []:
        args += ["-f", param]
    proc = _gh(args)
    if proc.returncode != 0:
        raise CodeScanningError(
            f"gh api {endpoint} failed: {proc.stderr.strip() or 'unknown error'}"
        )
    body = proc.stdout.strip()
    return json.loads(body) if body else []


def _alert_row(alert: dict) -> str:
    rule = alert.get("rule") or {}
    instance = alert.get("most_recent_instance") or {}
    location = instance.get("location") or {}
    message = (instance.get("message") or {}).get("text", "").strip().replace("\n", " ")
    severity = rule.get("security_severity_level") or rule.get("severity") or "unknown"
    path = location.get("path", "?")
    line = location.get("start_line", "?")
    state = alert.get("state", "?")
    rule_id = rule.get("id", "?")
    return f"- [{severity}] {rule_id} — {path}:{line} ({state})\n  {message}"


def _build_summary(repo: str, generated_at: str, alerts: List[dict]) -> str:
    by_severity: Counter = Counter()
    by_state: Counter = Counter()
    by_rule: Counter = Counter()
    for alert in alerts:
        rule = alert.get("rule") or {}
        by_severity[
            rule.get("security_severity_level") or rule.get("severity") or "unknown"
        ] += 1
        by_state[alert.get("state", "unknown")] += 1
        by_rule[rule.get("id", "unknown")] += 1

    lines = [
        f"# Code scanning summary — {repo}",
        "",
        f"- Generated: {generated_at}",
        f"- Total alerts: {len(alerts)}",
        "",
        "## By severity",
        "",
    ]
    lines += [f"- {sev}: {count}" for sev, count in by_severity.most_common()] or [
        "- none"
    ]
    lines += ["", "## By state", ""]
    lines += [f"- {state}: {count}" for state, count in by_state.most_common()] or [
        "- none"
    ]
    lines += ["", "## By rule", ""]
    lines += [f"- {rule}: {count}" for rule, count in by_rule.most_common()] or [
        "- none"
    ]
    lines += ["", "## Alerts", ""]
    lines += [_alert_row(alert) for alert in alerts] or ["- none"]
    return "\n".join(lines) + "\n"


def download_code_scanning(
    repo: Optional[str] = None,
    output_dir: Optional[str] = None,
    state: Optional[str] = None,
) -> CodeScanningResult:
    if not shutil.which("gh"):
        raise CodeScanningError("the GitHub CLI 'gh' is not installed or not on PATH")

    repo = _resolve_repo(repo)
    repo_name = repo.rstrip("/").split("/")[-1]

    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = os.path.join("/tmp", repo_name, "code-scanner", timestamp)
    output_dir = os.path.abspath(os.path.expanduser(output_dir))
    os.makedirs(output_dir, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")

    alerts = _fetch_json(
        f"repos/{repo}/code-scanning/alerts",
        params=[f"state={state}"] if state else None,
    )

    files: List[str] = []

    def _write(name: str, content: str) -> None:
        path = os.path.join(output_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        files.append(path)

    _write("alerts.json", json.dumps(alerts, indent=2, ensure_ascii=False) + "\n")
    _write("summary.md", _build_summary(repo, generated_at, alerts))

    try:
        analyses = _fetch_json(f"repos/{repo}/code-scanning/analyses")
        _write(
            "analyses.json", json.dumps(analyses, indent=2, ensure_ascii=False) + "\n"
        )
    except CodeScanningError as exc:
        _write("analyses.json", json.dumps({"error": str(exc)}, indent=2) + "\n")

    return CodeScanningResult(
        repo=repo,
        output_dir=output_dir,
        alert_count=len(alerts),
        files=files,
    )
