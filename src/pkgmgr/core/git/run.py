from __future__ import annotations

import contextvars
import os
import pwd
import re
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

from .errors import GitNotRepositoryError, GitRunError

SCAN_FLAGS = (
    "--no-pager",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
    # hook.<name>.command hooks from the config ignore core.hooksPath
    "-c",
    "hook.reference-transaction.enabled=false",
    "-c",
    "hook.prepare-commit-msg.enabled=false",
    "-c",
    "hook.post-commit.enabled=false",
    "-c",
    "hook.post-rewrite.enabled=false",
    "-c",
    "hook.post-index-change.enabled=false",
    "-c",
    "hook.pre-push.enabled=false",
    "-c",
    "hook.post-checkout.enabled=false",
    "-c",
    "core.pager=cat",
    "-c",
    "gc.auto=0",
    "-c",
    "maintenance.auto=false",
    "-c",
    "log.showSignature=false",
)
SCAN_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "/bin/false",
    "LC_ALL": "C",
}
SCAN_UNSET = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_EXTERNAL_DIFF",
    "GIT_PAGER",
    "PAGER",
)
STRICT_KEEP = ("GIT_CEILING_DIRECTORIES",)
CONFIG_READ_KEEP = re.compile(
    r"GIT_CONFIG_(GLOBAL|SYSTEM|PARAMETERS|COUNT|KEY_\d+|VALUE_\d+)"
)
CALLER_CONFIG = "caller"
DEFAULT_CONFIG = "default"
CONFIG_VIEWS = (CALLER_CONFIG, DEFAULT_CONFIG)
SCAN_TIMEOUT = 60
# ref and remote names come from repositories an agent may write: one named
# like --output=<path> would otherwise make rev-list create that file
END_OF_OPTIONS = "--end-of-options"
_STRICT_ENV: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "pkgmgr_git_strict_env", default=False
)


def _is_not_repo_error(stderr: str) -> bool:
    msg = (stderr or "").lower()
    return "not a git repository" in msg


@contextmanager
def strict_env() -> Iterator[None]:
    token = _STRICT_ENV.set(True)
    try:
        yield
    finally:
        _STRICT_ENV.reset(token)


def _strict_keeps(key: str, caller: bool) -> bool:
    return key in STRICT_KEEP or (
        caller and CONFIG_READ_KEEP.fullmatch(key) is not None
    )


def _passwd_home() -> str | None:
    try:
        return pwd.getpwuid(os.getuid()).pw_dir
    except KeyError:
        return None


def _scan_env(strict: bool = False, view: str | None = None) -> dict[str, str]:
    """
    Build the environment of a scan or strict git call.

    Args:
        strict: drop every inherited `GIT_*` variable but STRICT_KEEP.
        view: None, CALLER_CONFIG or DEFAULT_CONFIG, as run takes it.

    Returns:
        The inherited environment without SCAN_UNSET, plus SCAN_ENV; for a
        config view with the system config; for DEFAULT_CONFIG also without
        any `GIT_*` but STRICT_KEEP and XDG_CONFIG_HOME, HOME set to the
        passwd home (unset without a passwd entry).
    """
    caller = view == CALLER_CONFIG
    scrub = strict or view == DEFAULT_CONFIG
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in SCAN_UNSET
        and not (scrub and key.startswith("GIT_") and not _strict_keeps(key, caller))
    }
    env = {**env, **SCAN_ENV}
    if view is None:
        return env
    del env["GIT_CONFIG_NOSYSTEM"]
    if view == DEFAULT_CONFIG:
        env.pop("XDG_CONFIG_HOME", None)
        env.pop("HOME", None)
        home = _passwd_home()
        if home:
            env["HOME"] = home
    return env


def run(
    args: list[str],
    *,
    cwd: str = ".",
    preview: bool = False,
    scan: bool = False,
    input_text: str | None = None,
    config_view: str | None = None,
) -> str:
    """
    Run a Git command and return its stdout as a stripped string.

    Args:
        args: the git arguments.
        cwd: directory to run in.
        preview: print the command instead of running it.
        scan: read a repository an agent may have written: no fsmonitor, hook,
            pager, lazy fetch, replace object, system config or prompt, stdin
            closed, a timeout. Inside strict_env() every call, scan or not,
            also runs without any inherited `GIT_*` variable but
            `GIT_CEILING_DIRECTORIES`, which only narrows discovery.
        input_text: text fed to stdin, e.g. for `cat-file --batch-check`;
            replaces the closed stdin of scan mode.
        config_view: for a pure config read, the config it sees, both with
            the system config: CALLER_CONFIG also keeps, inside strict_env(),
            `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_PARAMETERS`,
            `GIT_CONFIG_COUNT` and its `GIT_CONFIG_KEY_<n>` and
            `GIT_CONFIG_VALUE_<n>`; DEFAULT_CONFIG reads the default system
            and passwd-home global config whatever the environment says.

    Raises GitRunError (or a subclass) if execution fails or times out.
    """
    cmd = ["git", *SCAN_FLAGS, *args] if scan else ["git"] + args
    cmd_str = " ".join(cmd)

    if preview:
        print(f"[PREVIEW] Would run in {cwd!r}: {cmd_str}")
        return ""

    strict = _STRICT_ENV.get()
    hardened: dict = (
        {
            "env": _scan_env(strict, config_view),
            "stdin": subprocess.DEVNULL,
            "timeout": SCAN_TIMEOUT,
        }
        if scan
        else ({"env": _scan_env(True, config_view)} if strict else {})
    )
    if input_text is not None:
        hardened.pop("stdin", None)
        hardened["input"] = input_text
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            **hardened,
        )
    except subprocess.TimeoutExpired as exc:
        err = GitRunError(f"Git command timed out in {cwd!r}: {cmd_str}")
        err.cwd, err.cmd, err.cmd_str, err.returncode = cwd, cmd, cmd_str, -1
        err.stdout, err.stderr = "", ""
        raise err from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        stdout = exc.stdout or ""

        if _is_not_repo_error(stderr):
            err = GitNotRepositoryError(
                f"Not a git repository: {cwd!r}\nCommand: {cmd_str}\nSTDERR:\n{stderr}"
            )
            # Attach details for callers who want to debug
            err.cwd = cwd
            err.cmd = cmd
            err.cmd_str = cmd_str
            err.returncode = exc.returncode
            err.stdout = stdout
            err.stderr = stderr
            raise err from exc

        err = GitRunError(
            f"Git command failed in {cwd!r}: {cmd_str}\n"
            f"Exit code: {exc.returncode}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )
        # Attach details for callers who want to debug
        err.cwd = cwd
        err.cmd = cmd
        err.cmd_str = cmd_str
        err.returncode = exc.returncode
        err.stdout = stdout
        err.stderr = stderr
        raise err from exc

    return result.stdout.strip()
