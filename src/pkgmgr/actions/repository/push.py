from __future__ import annotations

import subprocess
import threading
from typing import Any

from pkgmgr.actions.repository._parallel import (
    RepoRef,
    resolve_repos,
    run_on_repos,
)
from pkgmgr.core.git import GitRunError, run

Repository = dict[str, Any]

# Re-signing opens pinentry; parallel pushes must not ask for the passphrase at once.
_SIGN_LOCK = threading.Lock()


class PushRefusedError(RuntimeError):
    """Raised when a push would ship unsigned commits or overwrite a mirror."""


def _try_git(repo_dir: str, *args: str) -> str | None:
    try:
        return run(list(args), cwd=repo_dir)
    except GitRunError:
        return None


def _push_target(repo_dir: str) -> tuple[str, str]:
    branch = run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if branch == "HEAD":
        raise PushRefusedError(f"{repo_dir}: detached HEAD, nothing to push")
    remote = (
        _try_git(repo_dir, "config", "--get", f"branch.{branch}.pushRemote")
        or _try_git(repo_dir, "config", "--get", "remote.pushDefault")
        or _try_git(repo_dir, "config", "--get", f"branch.{branch}.remote")
        or "origin"
    )
    return branch, remote


def _unpushed_signatures(
    repo_dir: str, remote: str, branch: str
) -> tuple[str, dict[str, str]]:
    for ref in (
        f"refs/remotes/{remote}/{branch}",
        "@{u}",
        f"refs/remotes/{remote}/main",
        f"refs/remotes/{remote}/master",
    ):
        base = _try_git(repo_dir, "merge-base", "HEAD", ref)
        if base:
            lines = run(
                ["log", "--format=%H %G?", f"{base}..HEAD"], cwd=repo_dir
            ).splitlines()
            return base, dict(line.split() for line in lines)
    raise PushRefusedError(
        f"{repo_dir}: no {remote}/{branch}, no upstream and no {remote}/main or "
        f"{remote}/master to sign against"
    )


def sign_unpushed(repo_dir: str, *, preview: bool = False) -> None:
    """
    Args:
      repo_dir: checkout whose current branch is signed.
      preview: print the fetch and the amend instead of running them.
    """
    branch, remote = _push_target(repo_dir)
    run(["fetch", "--quiet", remote], cwd=repo_dir, preview=preview)
    base, signatures = _unpushed_signatures(repo_dir, remote, branch)
    head = run(["rev-parse", "HEAD"], cwd=repo_dir)
    older = sum(1 for sha, s in signatures.items() if sha != head and s != "G")
    if older:
        print(
            f"[push] WARN {older} older unsigned commit(s) in {base[:10]}..HEAD~ of "
            f"{repo_dir} stay unsigned: signing them would rewrite history"
        )
    if signatures.get(head, "G") == "G":
        return
    if run(["status", "--porcelain", "--untracked-files=no"], cwd=repo_dir):
        raise PushRefusedError(f"{repo_dir}: uncommitted changes, cannot sign HEAD")

    cmd = [
        "git",
        "commit",
        "--amend",
        "--no-edit",
        "--no-verify",
        "--allow-empty",
        "-S",
    ]
    print(f"[push] Signing HEAD {head[:10]} in {repo_dir}")
    if preview:
        print(f"[PREVIEW] Would run in {repo_dir!r}: {' '.join(cmd)}")
        return
    with _SIGN_LOCK:
        result = subprocess.run(cmd, cwd=repo_dir, check=False)
    if result.returncode != 0:
        raise PushRefusedError(f"{repo_dir}: signing HEAD {head[:10]} failed")


def _lease(
    repo_dir: str,
    url: str,
    branch_ref: str,
    tracking: str | None,
    keep: tuple[str, ...],
    preview: bool,
) -> str:
    if tracking is not None:
        sha = _try_git(repo_dir, "rev-parse", "--verify", "--quiet", tracking) or ""
    else:
        listed = run(["ls-remote", url, branch_ref], cwd=repo_dir).splitlines()
        sha = next(
            (ln.split()[0] for ln in listed if ln.split()[1:] == [branch_ref]), ""
        )
        if sha and not preview:
            run(["fetch", "--quiet", "--no-tags", url, branch_ref], cwd=repo_dir)
    if not sha or preview:
        return sha
    lost: set[str] | None = None
    for tip in keep:
        plus = {
            line[2:]
            for line in run(["cherry", tip, sha], cwd=repo_dir).splitlines()
            if line.startswith("+")
        }
        lost = plus if lost is None else lost & plus
    if lost:
        raise PushRefusedError(
            f"{url}: {len(lost)} commit(s) exist only there, not overwritten: "
            f"{' '.join(s[:10] for s in sorted(lost))}; "
            "pass --rewrite for a deliberate history rewrite"
        )
    return sha


def push_branch(
    repo_dir: str,
    extra_args: list[str],
    *,
    sign: bool,
    refs: tuple[str, ...] = (),
    rewrite: bool = False,
    preview: bool = False,
) -> None:
    """
    Push the current branch to every pushurl of its push remote, each with its own lease.

    The fetch URL is leased against the remote-tracking ref, every other
    pushurl against its own branch tip; each only after `git cherry` shows it
    holds no commit the new tip lacks. A mirror failure is reported after the
    others were pushed; a canonical failure stops before any mirror.

    Args:
      repo_dir: checkout whose current branch is pushed.
      extra_args: flags appended to every `git push`.
      sign: refuse an unpushed, unsigned HEAD; False pushes it as it is.
      refs: extra refs (e.g. a release tag) pushed to every URL.
      rewrite: replace commits of the old canonical tip; the fetch URL skips
        the cherry check, mirrors only refuse commits the old tip never had.
      preview: print the pushes instead of running them.
    """
    branch, remote = _push_target(repo_dir)
    head = run(["rev-parse", "HEAD"], cwd=repo_dir)
    if sign:
        _base, signatures = _unpushed_signatures(repo_dir, remote, branch)
        if not preview and signatures.get(head, "G") != "G":
            raise PushRefusedError(
                f"{repo_dir}: HEAD {head[:10]} is unsigned; run `pkgmgr push` to sign it"
            )

    fetch_url = run(["remote", "get-url", remote], cwd=repo_dir)
    push_urls = run(
        ["remote", "get-url", "--push", "--all", remote], cwd=repo_dir
    ).splitlines()
    branch_ref = f"refs/heads/{branch}"
    tracking = f"refs/remotes/{remote}/{branch}"
    old_tip = _try_git(repo_dir, "rev-parse", "--verify", "--quiet", tracking)
    if fetch_url not in push_urls:
        print(
            f"[push] WARN {remote}: fetch URL is no pushurl; every URL is leased "
            "as a mirror, tracking ref and upstream stay untouched"
        )

    failed: list[str] = []
    for url in sorted(push_urls, key=lambda u: u != fetch_url):
        if url == fetch_url:
            keep: tuple[str, ...] = () if rewrite else (head,)
        else:
            keep = (head, old_tip) if rewrite and old_tip else (head,)
        try:
            expect = _lease(
                repo_dir,
                url,
                branch_ref,
                tracking if url == fetch_url else None,
                keep,
                preview,
            )
            run(
                [
                    "push",
                    "--follow-tags",
                    f"--force-with-lease={branch_ref}:{expect}",
                    *extra_args,
                    url,
                    branch_ref,
                    *refs,
                ],
                cwd=repo_dir,
                preview=preview,
            )
        except (GitRunError, PushRefusedError) as exc:
            if url == fetch_url:
                raise
            print(f"[push] FAILED {url}\n{exc}")
            failed.append(url)
            continue
        print(f"[push] {url} <- {branch} {head[:10]}")
        if url == fetch_url and not preview:
            run(["update-ref", tracking, head], cwd=repo_dir)
            if not _try_git(repo_dir, "rev-parse", "--abbrev-ref", "@{u}"):
                run(["branch", f"--set-upstream-to={remote}/{branch}"], cwd=repo_dir)

    if failed:
        raise PushRefusedError(f"{repo_dir}: push failed for {', '.join(failed)}")


def _push_one(
    repo_dir: str, extra_args: list[str], sign: bool, rewrite: bool, preview: bool
) -> tuple[bool, str]:
    try:
        if sign:
            sign_unpushed(repo_dir, preview=preview)
        push_branch(repo_dir, extra_args, sign=sign, rewrite=rewrite, preview=preview)
        return (True, "")
    except (GitRunError, PushRefusedError) as exc:
        return (False, str(exc))


def push_repo_dirs(
    repos: list[RepoRef],
    extra_args: list[str],
    preview: bool,
    sign: bool,
    jobs: int = 1,
    rewrite: bool = False,
) -> None:
    """
    Sign and push each ``(identifier, repo_dir)``, optionally in parallel.
    """
    run_on_repos(
        repos,
        lambda rd: _push_one(rd, extra_args, sign, rewrite, preview),
        jobs=jobs,
        op_name="push",
    )


def push_in_parallel(
    selected_repos: list[Repository],
    repositories_base_dir: str,
    all_repos: list[Repository],
    extra_args: list[str],
    preview: bool,
    sign: bool,
    jobs: int = 1,
    rewrite: bool = False,
) -> None:
    """
    Sign and push each selected repository, optionally in parallel.
    """
    push_repo_dirs(
        resolve_repos(selected_repos, repositories_base_dir, all_repos),
        extra_args,
        preview,
        sign,
        jobs=jobs,
        rewrite=rewrite,
    )
