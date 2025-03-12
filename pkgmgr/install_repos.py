import os
import subprocess
import sys
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.run_command import run_command
from pkgmgr.verify import verify_repository

def install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=False, quiet=False):
    """
    Install repositories by creating symbolic links and running setup commands.
    
    Verifies repository state using verify_repository in local mode.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Clone it first.")
            continue

        verified_info = repo.get("verified")
        verified_ok, errors, commit_hash, signing_key = verify_repository(repo, repo_dir, mode="local", no_verification=no_verification)

        if not no_verification and verified_info and not verified_ok:
            print(f"Warning: Verification failed for {repo_identifier}:")
            for err in errors:
                print(f"  - {err}")
            choice = input("Proceed with installation? (y/N): ").strip().lower()
            if choice != "y":
                print(f"Skipping installation for {repo_identifier}.")
                continue

        # Create the symlink using the create_ink function.
        create_ink(repo, repositories_base_dir, bin_dir, all_repos, quiet=quiet, preview=preview)

        setup_cmd = repo.get("setup")
        if setup_cmd:
            run_command(setup_cmd, cwd=repo_dir, preview=preview)
