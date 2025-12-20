from __future__ import annotations

from typing import Tuple

from ..errors import GitRunError
from ..run import run


def _first_useful_line(text: str) -> str:
    lines: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s:
            lines.append(s)

    if not lines:
        return ""

    preferred_keywords = (
        "fatal:",
        "permission denied",
        "repository not found",
        "could not read from remote repository",
        "connection refused",
        "connection timed out",
        "no route to host",
        "name or service not known",
        "temporary failure in name resolution",
        "host key verification failed",
        "could not resolve hostname",
        "authentication failed",
        "publickey",
        "the authenticity of host",
        "known_hosts",
    )
    for s in lines:
        low = s.lower()
        if any(k in low for k in preferred_keywords):
            return s

    # Avoid returning a meaningless "error:" if possible
    for s in lines:
        if s.lower() not in ("error:", "error"):
            return s

    return lines[0]


def _looks_like_real_transport_error(text: str) -> bool:
    """
    True if stderr/stdout contains strong indicators that the remote is NOT usable.
    """
    low = (text or "").lower()
    indicators = (
        "repository not found",
        "could not read from remote repository",
        "permission denied",
        "authentication failed",
        "publickey",
        "host key verification failed",
        "could not resolve hostname",
        "name or service not known",
        "connection refused",
        "connection timed out",
        "no route to host",
    )
    return any(i in low for i in indicators)


def _format_reason(exc: GitRunError, *, url: str) -> str:
    stderr = getattr(exc, "stderr", "") or ""
    stdout = getattr(exc, "stdout", "") or ""
    rc = getattr(exc, "returncode", None)

    reason = (
        _first_useful_line(stderr)
        or _first_useful_line(stdout)
        or _first_useful_line(str(exc))
    )

    if rc is not None:
        reason = f"(exit {rc}) {reason}".strip() if reason else f"(exit {rc})"

    # If we still have nothing useful, provide a hint to debug SSH transport
    if not reason or reason.lower() in ("(exit 2)", "(exit 128)"):
        reason = (
            f"{reason} | hint: run "
            f"GIT_SSH_COMMAND='ssh -vvv' git ls-remote --exit-code {url!r}"
        ).strip()

    return reason.strip()


def probe_remote_reachable_detail(url: str, cwd: str = ".") -> Tuple[bool, str]:
    """
    Probe whether a remote URL is reachable.

    Implementation detail:
      - We run `git ls-remote --exit-code <url>`.
      - Git may return exit code 2 when the remote is reachable but no refs exist
        (e.g. an empty repository). We treat that as reachable.
    """
    try:
        run(["ls-remote", "--exit-code", url], cwd=cwd)
        return True, ""
    except GitRunError as exc:
        rc = getattr(exc, "returncode", None)
        stderr = getattr(exc, "stderr", "") or ""
        stdout = getattr(exc, "stdout", "") or ""

        # Important: `git ls-remote --exit-code` uses exit code 2 when no refs match.
        # For a completely empty repo, this can happen even though auth/transport is OK.
        if rc == 2 and not _looks_like_real_transport_error(stderr + "\n" + stdout):
            return True, "remote reachable, but no refs found yet (empty repository)"

        return False, _format_reason(exc, url=url)


def probe_remote_reachable(url: str, cwd: str = ".") -> bool:
    ok, _ = probe_remote_reachable_detail(url, cwd=cwd)
    return ok
