import os
import subprocess
import sys
import yaml
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.run_command import run_command
from pkgmgr.verify import verify_repository

def install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=False, quiet=False):
    """
    Install repositories by creating symbolic links, running setup commands, and
    installing additional packages if a requirements.yml or requirements.txt file is found.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        
        # If the repository directory does not exist, clone it automatically.
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Cloning it now...")
            clone_repos([repo], repositories_base_dir, all_repos, preview, no_verification)
            if not os.path.exists(repo_dir):
                print(f"Cloning failed for repository {repo_identifier}. Skipping installation.")
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

        # Create the symlink using create_ink.
        create_ink(repo, repositories_base_dir, bin_dir, all_repos, quiet=quiet, preview=preview)
        
        # Check if a requirements.yml file exists and install additional packages.
        req_file = os.path.join(repo_dir, "requirements.yml")
        if os.path.exists(req_file):
            try:
                with open(req_file, "r") as f:
                    requirements = yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading requirements.yml in {repo_identifier}: {e}")
                continue  # Skip to next repository if error occurs
            if requirements:
                # Install pacman packages if defined.
                if "pacman" in requirements:
                    pacman_packages = requirements["pacman"]
                    if pacman_packages:
                        cmd = "sudo pacman -S " + " ".join(pacman_packages)
                        run_command(cmd, preview=preview)
                # Install yay packages if defined.
                if "yay" in requirements:
                    yay_packages = requirements["yay"]
                    if yay_packages:
                        cmd = "yay -S " + " ".join(yay_packages)
                        run_command(cmd, preview=preview)
                # Install pkgmgr packages if defined.
                if "pkgmgr" in requirements:
                    pkgmgr_packages = requirements["pkgmgr"]
                    if pkgmgr_packages:
                        cmd = "pkgmgr install " + " ".join(pkgmgr_packages)
                        run_command(cmd, preview=preview)
                # Install pip packages if defined.
                if "pip" in requirements:
                    pip_packages = requirements["pip"]
                    if pip_packages:
                        cmd = "python3 -m pip install " + " ".join(pip_packages)
                        run_command(cmd, preview=preview)
                # Install ansible collections if defined.
                if "collections" in requirements:
                    print(f"Ansible collections found in {repo_identifier}, installing...")
                    cmd = "ansible-galaxy collection install -r requirements.yml"
                    run_command(cmd, cwd=repo_dir, preview=preview)
        
        # Check if a requirements.txt file exists and install Python packages.
        req_txt_file = os.path.join(repo_dir, "requirements.txt")
        if os.path.exists(req_txt_file):
            print(f"requirements.txt found in {repo_identifier}, installing Python dependencies...")
            cmd = "python3 -m pip install -r requirements.txt"
            run_command(cmd, cwd=repo_dir, preview=preview)
        
        # Check if a Makefile exists and run make.
        makefile_path = os.path.join(repo_dir, "Makefile")
        if os.path.exists(makefile_path):
            print(f"Makefile found in {repo_identifier}, running 'make install'...")
            run_command("make install", cwd=repo_dir, preview=preview)
