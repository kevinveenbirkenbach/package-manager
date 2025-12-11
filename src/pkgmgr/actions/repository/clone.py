import subprocess
import os
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.verify import verify_repository

def clone_repos(
    selected_repos, 
    repositories_base_dir: str, 
    all_repos, 
    preview: bool, 
    no_verification: bool, 
    clone_mode: str
    ):
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if os.path.exists(repo_dir):
            print(f"[INFO] Repository '{repo_identifier}' already exists at '{repo_dir}'. Skipping clone.")
            continue

        parent_dir = os.path.dirname(repo_dir)
        os.makedirs(parent_dir, exist_ok=True)
        # Build clone URL based on the clone_mode
        # Build clone URL based on the clone_mode
        if clone_mode == "ssh":
            clone_url = (
                f"git@{repo.get('provider')}:"
                f"{repo.get('account')}/"
                f"{repo.get('repository')}.git"
            )
        elif clone_mode in ("https", "shallow"):
            # Use replacement if defined, otherwise construct from provider/account/repository
            if repo.get("replacement"):
                clone_url = f"https://{repo.get('replacement')}.git"
            else:
                clone_url = (
                    f"https://{repo.get('provider')}/"
                    f"{repo.get('account')}/"
                    f"{repo.get('repository')}.git"
                )
        else:
            print(f"Unknown clone mode '{clone_mode}'. Aborting clone for {repo_identifier}.")
            continue

        # Build base clone command
        base_clone_cmd = "git clone"
        if clone_mode == "shallow":
            # Shallow clone: only latest state via HTTPS, no full history
            base_clone_cmd += " --depth 1 --single-branch"

        mode_label = "HTTPS (shallow)" if clone_mode == "shallow" else clone_mode.upper()
        print(
            f"[INFO] Attempting to clone '{repo_identifier}' using {mode_label} "
            f"from {clone_url} into '{repo_dir}'."
        )

        if preview:
            print(f"[Preview] Would run: {base_clone_cmd} {clone_url} {repo_dir} in {parent_dir}")
            result = subprocess.CompletedProcess(args=[], returncode=0)
        else:
            result = subprocess.run(
                f"{base_clone_cmd} {clone_url} {repo_dir}",
                cwd=parent_dir,
                shell=True,
            )
        
        if result.returncode != 0:
            # Only offer fallback if the original mode was SSH.
            if clone_mode == "ssh":
                print(f"[WARNING] SSH clone failed for '{repo_identifier}' with return code {result.returncode}.")
                choice = input("Do you want to attempt HTTPS clone instead? (y/N): ").strip().lower()
                if choice == 'y':
                    # Attempt HTTPS clone
                    if repo.get("replacement"):
                        clone_url = f"https://{repo.get('replacement')}.git"
                    else:
                        clone_url = f"https://{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}.git"
                    print(f"[INFO] Attempting to clone '{repo_identifier}' using HTTPS from {clone_url} into '{repo_dir}'.")
                    if preview:
                        print(f"[Preview] Would run: git clone {clone_url} {repo_dir} in {parent_dir}")
                        result = subprocess.CompletedProcess(args=[], returncode=0)
                    else:
                        result = subprocess.run(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, shell=True)
                else:
                    print(f"[INFO] HTTPS clone not attempted for '{repo_identifier}'.")
                    continue
            else:
                # For https mode, do not attempt fallback.
                print(f"[WARNING] HTTPS clone failed for '{repo_identifier}' with return code {result.returncode}.")
                continue
        
        # After cloning, perform verification in local mode.
        verified_info = repo.get("verified")
        if verified_info:
            verified_ok, errors, commit_hash, signing_key = verify_repository(repo, repo_dir, mode="local", no_verification=no_verification)
            if not no_verification and not verified_ok:
                print(f"Warning: Verification failed for {repo_identifier} after cloning:")
                for err in errors:
                    print(f"  - {err}")
                choice = input("Proceed anyway? (y/N): ").strip().lower()
                if choice != "y":
                    print(f"Skipping repository {repo_identifier} due to failed verification.")
