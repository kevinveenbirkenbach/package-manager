from __future__ import annotations

import glob
import os
import shutil
import subprocess

from pkgmgr.actions.mirror.io import read_mirrors_file
from pkgmgr.actions.mirror.types import Repository
from pkgmgr.core.credentials.resolver import ResolutionOptions, TokenResolver
from pkgmgr.core.version.semver import SemVer

from .git_tags import head_semver_tags
from .pypi_url import parse_pypi_project_url


def _require_tool(module: str) -> None:
    try:
        subprocess.run(
            ["python", "-m", module, "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Required Python module '{module}' is not available. "
            f"Install it via: pip install {module}"
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

    _require_tool("build")
    _require_tool("twine")

    dist_dir = os.path.join(repo_dir, "dist")
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir, ignore_errors=True)

    subprocess.run(
        ["python", "-m", "build"],
        cwd=repo_dir,
        check=True,
    )

    artifacts = sorted(glob.glob(os.path.join(dist_dir, "*")))
    if not artifacts:
        raise RuntimeError("No build artifacts found in dist/.")

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

    env = dict(os.environ)
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token

    subprocess.run(
        ["python", "-m", "twine", "upload", *artifacts],
        cwd=repo_dir,
        env=env,
        check=True,
    )

    print("[INFO] Publish completed.")
