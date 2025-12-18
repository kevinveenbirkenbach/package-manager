from __future__ import annotations

from pkgmgr.core.git.queries import (
    get_head_commit,
    get_latest_signing_key,
    get_remote_head_commit,
    GitLatestSigningKeyQueryError,
    GitRemoteHeadCommitQueryError,
)


def verify_repository(repo, repo_dir, mode="local", no_verification=False):
    _ = no_verification

    verified_info = repo.get("verified")

    commit_hash = ""
    signing_key = ""

    # best-effort info collection
    try:
        if mode == "pull":
            commit_hash = get_remote_head_commit(cwd=repo_dir)
        else:
            commit_hash = get_head_commit(cwd=repo_dir) or ""
    except GitRemoteHeadCommitQueryError:
        commit_hash = ""

    try:
        signing_key = get_latest_signing_key(cwd=repo_dir)
    except GitLatestSigningKeyQueryError:
        signing_key = ""

    if not verified_info:
        return True, [], commit_hash, signing_key

    expected_commit = None
    expected_gpg_keys = None
    if isinstance(verified_info, dict):
        expected_commit = verified_info.get("commit")
        expected_gpg_keys = verified_info.get("gpg_keys")
    else:
        expected_commit = verified_info

    error_details: list[str] = []

    # strict retrieval when verification is configured
    if mode == "pull":
        try:
            commit_hash = get_remote_head_commit(cwd=repo_dir)
        except GitRemoteHeadCommitQueryError as exc:
            error_details.append(str(exc))
            commit_hash = ""
    else:
        commit_hash = get_head_commit(cwd=repo_dir) or ""

    try:
        signing_key = get_latest_signing_key(cwd=repo_dir)
    except GitLatestSigningKeyQueryError as exc:
        error_details.append(str(exc))
        signing_key = ""

    commit_check_passed = True
    gpg_check_passed = True

    if expected_commit:
        if not commit_hash:
            commit_check_passed = False
            error_details.append(
                f"Expected commit: {expected_commit}, but could not determine current commit."
            )
        elif commit_hash != expected_commit:
            commit_check_passed = False
            error_details.append(
                f"Expected commit: {expected_commit}, found: {commit_hash}"
            )

    if expected_gpg_keys:
        if not signing_key:
            gpg_check_passed = False
            error_details.append(
                f"Expected one of GPG keys: {expected_gpg_keys}, but no signing key was found."
            )
        elif signing_key not in expected_gpg_keys:
            gpg_check_passed = False
            error_details.append(
                f"Expected one of GPG keys: {expected_gpg_keys}, found: {signing_key}"
            )

    if expected_commit and expected_gpg_keys:
        verified_ok = commit_check_passed and gpg_check_passed
    elif expected_commit:
        verified_ok = commit_check_passed
    elif expected_gpg_keys:
        verified_ok = gpg_check_passed
    else:
        verified_ok = True

    return verified_ok, error_details, commit_hash, signing_key
