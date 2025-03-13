import os
import subprocess
import yaml
from pkgmgr.generate_alias import generate_alias
from pkgmgr.save_user_config import save_user_config

def create_repo(identifier, config_merged, user_config_path, bin_dir, remote=False, preview=False):
    """
    Creates a new repository by performing the following steps:
    
    1. Parses the identifier (provider/account/repository) and adds a new entry to the user config
       if it is not already present.
    2. Creates the local repository directory and initializes a Git repository.
    3. If --remote is set, adds a remote, creates an initial commit (e.g. with a README.md), and pushes to remote.
    """
    parts = identifier.split("/")
    if len(parts) != 3:
        print("Identifier must be in the format 'provider/account/repository'.")
        return

    provider, account, repository = parts

    # Check if the repository is already present in the merged config
    exists = False
    for repo in config_merged.get("repositories", []):
        if repo.get("provider") == provider and repo.get("account") == account and repo.get("repository") == repository:
            exists = True
            print(f"Repository {identifier} already exists in the configuration.")
            break

    if not exists:
        # Create a new entry with an automatically generated alias
        new_entry = {
            "provider": provider,
            "account": account,
            "repository": repository,
            "alias": generate_alias({"repository": repository, "provider": provider, "account": account}, bin_dir, existing_aliases=set()),
            "verified": {}  # No initial verification info
        }
        # Load or initialize the user configuration
        if os.path.exists(user_config_path):
            with open(user_config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {"repositories": []}
        user_config.setdefault("repositories", [])
        user_config["repositories"].append(new_entry)
        save_user_config(user_config, user_config_path)
        print(f"Repository {identifier} added to the configuration.")
        # Also update the merged configuration object
        config_merged.setdefault("repositories", []).append(new_entry)

    # Create the local repository directory based on the configured base directory
    base_dir = os.path.expanduser(config_merged["directories"]["repositories"])
    repo_dir = os.path.join(base_dir, provider, account, repository)
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir, exist_ok=True)
        print(f"Local repository directory created: {repo_dir}")
    else:
        print(f"Local repository directory already exists: {repo_dir}")

    # Initialize a Git repository if not already initialized
    if not os.path.exists(os.path.join(repo_dir, ".git")):
        cmd_init = "git init"
        if preview:
            print(f"[Preview] Would execute: '{cmd_init}' in {repo_dir}")
        else:
            subprocess.run(cmd_init, cwd=repo_dir, shell=True, check=True)
            print(f"Git repository initialized in {repo_dir}.")
    else:
        print("Git repository is already initialized.")

    if remote:
        # Create a README.md if it does not exist to have content for an initial commit
        readme_path = os.path.join(repo_dir, "README.md")
        if not os.path.exists(readme_path):
            if preview:
                print(f"[Preview] Would create README.md in {repo_dir}.")
            else:
                with open(readme_path, "w") as f:
                    f.write(f"# {repository}\n")
                subprocess.run("git add README.md", cwd=repo_dir, shell=True, check=True)
                subprocess.run('git commit -m "Initial commit"', cwd=repo_dir, shell=True, check=True)
                print("README.md created and initial commit made.")
        # Add a remote named "origin"
        remote_url = f"git@{provider}:{account}/{repository}.git"
        cmd_remote = f"git remote add origin {remote_url}"
        if preview:
            print(f"[Preview] Would execute: '{cmd_remote}' in {repo_dir}")
        else:
            subprocess.run(cmd_remote, cwd=repo_dir, shell=True, check=True)
            print(f"Remote 'origin' added: {remote_url}")
        # Push the initial commit to the remote repository
        cmd_push = "git push -u origin master"
        if preview:
            print(f"[Preview] Would execute: '{cmd_push}' in {repo_dir}")
        else:
            subprocess.run(cmd_push, cwd=repo_dir, shell=True, check=True)
            print("Initial push to the remote repository completed.")
            exit(7)