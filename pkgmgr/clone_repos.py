import subprocess
import os
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.verify import verify_repository

def clone_repos(selected_repos, repositories_base_dir: str, all_repos, preview:bool, no_verification:bool):
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if os.path.exists(repo_dir):
            print(f"[INFO] Repository '{repo_identifier}' already exists at '{repo_dir}'. Skipping clone.")
            continue
        
        parent_dir = os.path.dirname(repo_dir)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Attempt SSH clone first.
        target = repo.get("replacement") if repo.get("replacement") else f"{repo.get('provider')}:{repo.get('account')}/{repo.get('repository')}"
        clone_url = f"git@{target}.git"
        print(f"[INFO] Attempting to clone '{repo_identifier}' using SSH from {clone_url} into '{repo_dir}'.")
        
        if preview:
            print(f"[Preview] Would run: git clone {clone_url} {repo_dir} in {parent_dir}")
            result = subprocess.CompletedProcess(args=[], returncode=0)
        else:
            result = subprocess.run(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, shell=True)
        
        if result.returncode != 0:
            print(f"[WARNING] SSH clone failed for '{repo_identifier}' with return code {result.returncode}.")
            choice = input("Do you want to attempt HTTPS clone instead? (y/N): ").strip().lower()
            if choice == 'y':
                target = repo.get("replacement") if repo.get("replacement") else f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
                clone_url = f"https://{target}.git"
                print(f"[INFO] Attempting to clone '{repo_identifier}' using HTTPS from {clone_url} into '{repo_dir}'.")
                if preview:
                    print(f"[Preview] Would run: git clone {clone_url} {repo_dir} in {parent_dir}")
                    result = subprocess.CompletedProcess(args=[], returncode=0)
                else:
                    result = subprocess.run(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, shell=True)
            else:
                print(f"[INFO] HTTPS clone not attempted for '{repo_identifier}'.")
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
