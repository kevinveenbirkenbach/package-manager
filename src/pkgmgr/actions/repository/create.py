import os
import subprocess
import yaml
from pkgmgr.core.command.alias import generate_alias
from pkgmgr.core.config.save import save_user_config

def create_repo(identifier, config_merged, user_config_path, bin_dir, remote=False, preview=False):
    """
    Creates a new repository by performing the following steps:
    
    1. Parses the identifier (provider:port/account/repository) and adds a new entry to the user config
       if it is not already present. The provider part is split into provider and port (if provided).
    2. Creates the local repository directory and initializes a Git repository.
    3. If --remote is set, checks for an existing "origin" remote (removing it if found),
       adds the remote using a URL built from provider, port, account, and repository,
       creates an initial commit (e.g. with a README.md), and pushes to the remote.
       The push is attempted on both "main" and "master" branches.
    """
    parts = identifier.split("/")
    if len(parts) != 3:
        print("Identifier must be in the format 'provider:port/account/repository' (port is optional).")
        return

    provider_with_port, account, repository = parts
    # Split provider and port if a colon is present.
    if ":" in provider_with_port:
        provider_name, port = provider_with_port.split(":", 1)
    else:
        provider_name = provider_with_port
        port = None

    # Check if the repository is already present in the merged config (including port)
    exists = False
    for repo in config_merged.get("repositories", []):
        if (repo.get("provider") == provider_name and 
            repo.get("account") == account and 
            repo.get("repository") == repository):
            exists = True
            print(f"Repository {identifier} already exists in the configuration.")
            break

    if not exists:
        # Create a new entry with an automatically generated alias.
        new_entry = {
            "provider": provider_name,
            "port": port,
            "account": account,
            "repository": repository,
            "alias": generate_alias({"repository": repository, "provider": provider_name, "account": account}, bin_dir, existing_aliases=set()),
            "verified": {}  # No initial verification info
        }
        # Load or initialize the user configuration.
        if os.path.exists(user_config_path):
            with open(user_config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {"repositories": []}
        user_config.setdefault("repositories", [])
        user_config["repositories"].append(new_entry)
        save_user_config(user_config, user_config_path)
        print(f"Repository {identifier} added to the configuration.")
        # Also update the merged configuration object.
        config_merged.setdefault("repositories", []).append(new_entry)

    # Create the local repository directory based on the configured base directory.
    base_dir = os.path.expanduser(config_merged["directories"]["repositories"])
    repo_dir = os.path.join(base_dir, provider_name, account, repository)
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir, exist_ok=True)
        print(f"Local repository directory created: {repo_dir}")
    else:
        print(f"Local repository directory already exists: {repo_dir}")

    # Initialize a Git repository if not already initialized.
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
        # Create a README.md if it does not exist to have content for an initial commit.
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

        # Build the remote URL.
        if provider_name.lower() == "github.com":
            remote_url = f"git@{provider_name}:{account}/{repository}.git"
        else:
            if port:
                remote_url = f"ssh://git@{provider_name}:{port}/{account}/{repository}.git"
            else:
                remote_url = f"ssh://git@{provider_name}/{account}/{repository}.git"

        # Check if the remote "origin" already exists.
        cmd_list = "git remote"
        if preview:
            print(f"[Preview] Would check for existing remotes in {repo_dir}")
            remote_exists = False  # Assume no remote in preview mode.
        else:
            result = subprocess.run(cmd_list, cwd=repo_dir, shell=True, capture_output=True, text=True, check=True)
            remote_list = result.stdout.strip().split()
            remote_exists = "origin" in remote_list

        if remote_exists:
            # Remove the existing remote "origin".
            cmd_remove = "git remote remove origin"
            if preview:
                print(f"[Preview] Would execute: '{cmd_remove}' in {repo_dir}")
            else:
                subprocess.run(cmd_remove, cwd=repo_dir, shell=True, check=True)
                print("Existing remote 'origin' removed.")

        # Now add the new remote.
        cmd_remote = f"git remote add origin {remote_url}"
        if preview:
            print(f"[Preview] Would execute: '{cmd_remote}' in {repo_dir}")
        else:
            try:
                subprocess.run(cmd_remote, cwd=repo_dir, shell=True, check=True)
                print(f"Remote 'origin' added: {remote_url}")
            except subprocess.CalledProcessError:
                print(f"Failed to add remote using URL: {remote_url}.")

        # Push the initial commit to the remote repository
        cmd_push = "git push -u origin master"
        if preview:
            print(f"[Preview] Would execute: '{cmd_push}' in {repo_dir}")
        else:
            subprocess.run(cmd_push, cwd=repo_dir, shell=True, check=True)
            print("Initial push to the remote repository completed.")