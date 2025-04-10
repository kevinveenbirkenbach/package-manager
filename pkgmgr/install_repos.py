import os
import subprocess
import sys
import yaml
import tempfile
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.run_command import run_command
from pkgmgr.verify import verify_repository
from pkgmgr.clone_repos import clone_repos

def install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=False, quiet=False, clone_mode: str = "ssh", update_dependencies: bool = True):
    """
    Install repositories by creating symbolic links, running setup commands, and
    installing additional packages if a requirements.yml or requirements.txt file is found.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Cloning it now...")
            # Pass the clone_mode parameter to clone_repos
            clone_repos([repo], repositories_base_dir, all_repos, preview, no_verification, clone_mode=clone_mode)
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
                        cmd = "sudo pacman -S --noconfirm " + " ".join(pacman_packages)
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
                        if update_dependencies:
                            cmd_pull = "pkgmgr pull " + " ".join(pkgmgr_packages)
                            try:
                                run_command(cmd_pull, preview=preview)
                            except SystemExit as e:
                                print(f"Warning: 'pkgmgr pull' command failed (exit code {e}). Ignoring error and continuing.")            
                        cmd = "pkgmgr install " + " ".join(pkgmgr_packages)
                        run_command(cmd, preview=preview)
                # Install pip packages if defined.
                if "pip" in requirements:
                    pip_packages = requirements["pip"]
                    if pip_packages:
                        cmd = "python3 -m pip install " + " ".join(pip_packages)
                        run_command(cmd, preview=preview)
                        
                # Check if the requirements contain either 'collections' or 'roles'
                if "collections" in requirements or "roles" in requirements:
                    print(f"Ansible dependencies found in {repo_identifier}, installing...")

                    # Build a new dictionary that only contains the Ansible dependencies
                    ansible_requirements = {}
                    if "collections" in requirements:
                        ansible_requirements["collections"] = requirements["collections"]
                    if "roles" in requirements:
                        ansible_requirements["roles"] = requirements["roles"]

                    # Write the ansible requirements to a temporary file.
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tmp:
                        yaml.dump(ansible_requirements, tmp, default_flow_style=False)
                        tmp_filename = tmp.name

                    # Install Ansible collections if defined.
                    if "collections" in ansible_requirements:
                        print(f"Ansible collections found in {repo_identifier}, installing...")
                        cmd = f"ansible-galaxy collection install -r {tmp_filename}"
                        run_command(cmd, cwd=repo_dir, preview=preview)

                    # Install Ansible roles if defined.
                    if "roles" in ansible_requirements:
                        print(f"Ansible roles found in {repo_identifier}, installing...")
                        cmd = f"ansible-galaxy role install -r {tmp_filename}"
                        run_command(cmd, cwd=repo_dir, preview=preview)
        
        # Check if a requirements.txt file exists and install Python packages.
        req_txt_file = os.path.join(repo_dir, "requirements.txt")
        if os.path.exists(req_txt_file):
            print(f"requirements.txt found in {repo_identifier}, installing Python dependencies...")
            cmd = "python3 -m pip install -r requirements.txt --break-system-packages"
            run_command(cmd, cwd=repo_dir, preview=preview)
        
        # Check if a Makefile exists and run make.
        makefile_path = os.path.join(repo_dir, "Makefile")
        if os.path.exists(makefile_path):
            print(f"Makefile found in {repo_identifier}, running 'make install'...")
            run_command("make install", cwd=repo_dir, preview=preview)
