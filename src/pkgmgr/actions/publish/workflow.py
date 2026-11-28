from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from pkgmgr.actions.mirror.io import read_mirrors_file
from pkgmgr.actions.mirror.types import Repository
from pkgmgr.core.credentials.resolver import ResolutionOptions, TokenResolver
from pkgmgr.core.version.semver import SemVer

from .git_tags import head_semver_tags
from .pypi_url import parse_pypi_project_url
from .types import PyPITarget

UPLOAD_URLS = {
    "pypi.org": "https://upload.pypi.org/legacy/",
    "test.pypi.org": "https://test.pypi.org/legacy/",
}


def _child_env(repo_dir: str) -> dict[str, str]:
    """
    Args:
        repo_dir: absolute path of the repository being published.

    Returns:
        The environment for build and twine without pkgmgr's own variables,
        so no PKGMGR_* token reaches a build backend or an upload, and
        without PYTHONPATH entries inside repo_dir, so no repository file
        shadows build or twine.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("PKGMGR_")}
    if "PYTHONPATH" in env:
        root = os.path.realpath(repo_dir)
        kept = [
            entry
            for entry in env["PYTHONPATH"].split(os.pathsep)
            if entry and os.path.commonpath([root, os.path.realpath(entry)]) != root
        ]
        if kept:
            env["PYTHONPATH"] = os.pathsep.join(kept)
        else:
            del env["PYTHONPATH"]
    return env


def _require_tool(module: str, cwd: str, env: dict[str, str]) -> None:
    """
    Args:
        module: the Python module run with -m.
        cwd: an empty private directory, so no file of the repository
            shadows the module on sys.path.
        env: the child environment from _child_env.
    """
    try:
        subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Required Python module '{module}' is not available to "
            f"{sys.executable}. Install it via: "
            f"{sys.executable} -m pip install {module}"
        ) from exc


def publish(
    repo: Repository,
    repo_dir: str,
    *,
    preview: bool = False,
    interactive: bool = True,
    allow_prompt: bool = True,
) -> None:
    mirrors = read_mirrors_file(repo_dir)

    targets = []
    for url in mirrors.values():
        t = parse_pypi_project_url(url)
        if t:
            targets.append(t)

    if not targets:
        print("[INFO] No PyPI mirror found. Skipping publish.")
        return

    if len(targets) > 1:
        raise RuntimeError("Multiple PyPI mirrors found; refusing to publish.")

    tags = head_semver_tags(cwd=repo_dir)
    if not tags:
        print("[INFO] No version tag on HEAD. Skipping publish.")
        return

    tag = max(tags, key=SemVer.parse)
    target = targets[0]

    print(f"[INFO] Publishing {target.project} for tag {tag}")

    if preview:
        print("[PREVIEW] Would build and upload to PyPI.")
        return

    with tempfile.TemporaryDirectory() as out:
        _upload(target, os.path.abspath(repo_dir), out, interactive, allow_prompt)

    print("[INFO] Publish completed.")


def _upload(
    target: PyPITarget, repo_dir: str, out: str, interactive: bool, allow_prompt: bool
) -> None:
    """
    Args:
        target: the PyPI target parsed from the mirror URL.
        repo_dir: absolute path of the repository to build.
        out: an empty private directory that receives the artifacts and is
            the working directory of every child process.
        interactive: allow interactive token resolution.
        allow_prompt: allow prompting for the token.
    """
    env = _child_env(repo_dir)
    _require_tool("build", out, env)
    _require_tool("twine", out, env)

    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", out, repo_dir],
        cwd=out,
        env=env,
        check=True,
    )

    artifacts = sorted(os.path.join(out, name) for name in os.listdir(out))
    if not artifacts:
        raise RuntimeError("No build artifacts found.")

    resolver = TokenResolver()

    # Store PyPI token per OS user (keyring is already user-scoped).
    # Do NOT scope by project name.
    token = resolver.get_token(
        provider_kind="pypi",
        host=target.host,
        owner=None,
        options=ResolutionOptions(
            interactive=interactive,
            allow_prompt=allow_prompt,
            save_prompt_token_to_keyring=True,
        ),
    ).token

    subprocess.run(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--non-interactive",
            "--repository-url",
            UPLOAD_URLS[target.host],
            *artifacts,
        ],
        cwd=out,
        env={**env, "TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token},
        check=True,
    )
