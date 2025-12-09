import os
import subprocess
import sys
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.verify import verify_repository

def pull_with_verification(
    selected_repos,
    repositories_base_dir,
    all_repos,
    extra_args,
    no_verification,
    preview:bool):
    """
    Executes "git pull" for each repository with verification.
    
    Uses the verify_repository function in "pull" mode.
    If verification fails (and verification info is set) and --no-verification is not enabled,
    the user is prompted to confirm the pull.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")
            continue

        verified_info = repo.get("verified")
        verified_ok, errors, commit_hash, signing_key = verify_repository(repo, repo_dir, mode="pull", no_verification=no_verification)

        if not no_verification and verified_info and not verified_ok:
            print(f"Warning: Verification failed for {repo_identifier}:")
            for err in errors:
                print(f"  - {err}")
            choice = input("Proceed with 'git pull'? (y/N): ").strip().lower()
            if choice != "y":
                continue

        full_cmd = f"git pull {' '.join(extra_args)}"
        if preview:
            print(f"[Preview] In '{repo_dir}': {full_cmd}")
        else:
            print(f"Running in '{repo_dir}': {full_cmd}")
            result = subprocess.run(full_cmd, cwd=repo_dir, shell=True)
            if result.returncode != 0:
                print(f"'git pull' for {repo_identifier} failed with exit code {result.returncode}.")
                sys.exit(result.returncode)
