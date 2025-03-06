import os
import subprocess
import sys
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.run_command import run_command

def install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=False, quiet=False):
    """
    Install repositories by creating symbolic links (via create_ink) and running setup commands.
    
    This version applies hash verification:
      - It retrieves the current commit hash using 'git rev-parse HEAD' and compares it to the
        configured 'verified' hash.
      - If the hashes do not match and no_verification is False, the user is prompted for confirmation.
      - If the user does not confirm, the installation for that repository is skipped.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Clone it first.")
            continue

        # Apply hash verification if a verified hash is defined.
        verified_hash = repo.get("verified")
        if verified_hash:
            current_hash = ""
            try:
                result = subprocess.run("git rev-parse HEAD", cwd=repo_dir, shell=True, check=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                current_hash = result.stdout.strip()
            except Exception as e:
                print(f"Error retrieving current commit for {repo_identifier}: {e}")
            
            proceed = True
            if not no_verification and current_hash and current_hash != verified_hash:
                print(f"Warning: For {repo_identifier}, the current commit hash ({current_hash}) does not match the verified hash ({verified_hash}).")
                choice = input("Proceed with installation? (y/N): ").strip().lower()
                if choice != "y":
                    proceed = False
            if not proceed:
                print(f"Skipping installation for {repo_identifier}.")
                continue

        # Create the symlink using the new create_ink function.
        create_ink(repo, repositories_base_dir, bin_dir, all_repos, quiet=quiet, preview=preview)

        setup_cmd = repo.get("setup")
        if setup_cmd:
            run_command(setup_cmd, cwd=repo_dir, preview=preview)