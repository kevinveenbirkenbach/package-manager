#!/usr/bin/env python3
"""
Package Manager Script

This script provides the following commands:
  install    {identifier(s)|--all}
      - Creates an executable bash wrapper in the bin folder that calls the command for the repository.
      - Executes the repository’s "setup" command if specified.
  pull       {identifier(s)|--all}
      - Executes 'git pull' in the repository directory.
  clone      {identifier(s)|--all}
      - Clones the repository from a remote (using provider/account/repository or an alternative if 'replacement' is defined).
  push       {identifier(s)|--all}
      - Executes 'git push' in the repository directory.
  deinstall  {identifier(s)|--all}
      - Deletes the executable command/alias.
      - Executes the repository’s "teardown" command if specified.
  delete     {identifier(s)|--all}
      - Deletes the repository directory.
  update     {identifier(s)|--all|--system}
      - Combines pull and install; if --system is specified also runs system update commands.
  status     {identifier(s)|--all|--system}
      - Shows git status for each repository or, if --system is set, shows basic system update information.
  config     {identifier(s)|--all}
      - Displays the configuration for one or more repositories. If no identifier is given, shows the entire config.
  add
      - Starts an interactive dialog to add a new repository configuration entry.
      
Additional flags:
  --preview   Only show the changes without executing commands.
  --list      When used with preview or status, only list affected repositories (for status).
  
Identifiers:
  - If a repository’s name is unique then you can just use the repository name.
  - If multiple repositories share the same name then use the full identifier in the form "provider/account/repository".

The configuration is read from a YAML file (default: config.yaml) with the following structure:

base: "/path/to/repositories"
repos:
  - provider: "github.com"
    account: "youraccount"
    repository: "mytool"
    verified: "commit-id"
    command: "bash main.sh"         # optional; if not set, the script checks for main.sh/main.py in the repository
    description: "My tool description"  # optional
    replacement: ""                  # optional; alternative provider/account/repository string to use instead
    setup: "echo Setting up..."      # optional setup command executed during install
    teardown: "echo Tearing down..." # optional command executed during deinstall

"""

import argparse
import os
import subprocess
import shutil
import sys
import yaml

# Define default paths
CONFIG_PATH = "config.yaml"
# Change BIN_DIR to a directory that is in your PATH (e.g., os.path.expanduser("~/.local/bin"))
BIN_DIR = os.path.expanduser("~/.local/bin")

def load_config(config_path):
    """Load YAML configuration file."""
    if not os.path.exists(config_path):
        print(f"Configuration file '{config_path}' not found.")
        sys.exit(1)
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    # Expecting keys: "base" and "repos"
    if "base" not in config or "repos" not in config:
        print("Config file must contain 'base' and 'repos' keys.")
        sys.exit(1)
    return config

def save_config(config, config_path):
    """Save the config dictionary back to the YAML file."""
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    print(f"Configuration updated in {config_path}.")

def run_command(command, cwd=None, preview=False):
    """Run a shell command in a given directory, or print it in preview mode."""
    if preview:
        print(f"[Preview] In '{cwd or os.getcwd()}': {command}")
    else:
        print(f"Running in '{cwd or os.getcwd()}': {command}")
        subprocess.run(command, cwd=cwd, shell=True, check=False)

def get_repo_identifier(repo, all_repos):
    """
    Return a unique identifier for the repository.
    If the repository name is unique among all_repos, return repository name.
    Otherwise, return 'provider/account/repository'.
    """
    repo_name = repo.get("repository")
    count = sum(1 for r in all_repos if r.get("repository") == repo_name)
    if count == 1:
        return repo_name
    else:
        return f'{repo.get("provider")}/{repo.get("account")}/{repo.get("repository")}'

def resolve_repos(identifiers, all_repos):
    """
    Given a list of identifier strings, return a list of repository configs.
    The identifier can be either just the repository name (if unique) or full provider/account/repository.
    """
    selected = []
    for ident in identifiers:
        matches = []
        for repo in all_repos:
            full_id = f'{repo.get("provider")}/{repo.get("account")}/{repo.get("repository")}'
            if ident == full_id:
                matches.append(repo)
            elif ident == repo.get("repository"):
                # Only add if it is unique among all_repos
                if sum(1 for r in all_repos if r.get("repository") == ident) == 1:
                    matches.append(repo)
        if not matches:
            print(f"Identifier '{ident}' did not match any repository in config.")
        else:
            selected.extend(matches)
    return selected

def create_executable(repo, base_dir, bin_dir, all_repos, preview=False):
    """Create an executable bash wrapper for the repository.
    
    If the 'verified' field is set in the configuration, the wrapper will attempt to
    checkout that commit before executing the command and warn in orange if the checkout did not
    result in the expected commit.
    
    If no verified commit is set, a warning in orange is printed on every execution.
    """
    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
    # Determine the command to execute
    command = repo.get("command")
    if not command:
        # Check for main.sh or main.py in the repository directory
        main_sh = os.path.join(repo_dir, "main.sh")
        main_py = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_sh):
            command = "bash main.sh"
        elif os.path.exists(main_py):
            command = "python3 main.py"
        else:
            print(f"No command defined and no main.sh/main.py found in {repo_dir}. Skipping alias creation.")
            return

    # ANSI escape for orange in many 256-color terminals (color code 208)
    ORANGE = r"\033[38;5;208m"
    RESET = r"\033[0m"

    # Build the preamble based on the 'verified' field.
    verified = repo.get("verified")
    if verified:
        # Checkout the verified commit and warn if not current.
        preamble = f"""\
git checkout {verified} || echo -e "{ORANGE}Warning: Failed to checkout commit {verified}.{RESET}"
CURRENT=$(git rev-parse HEAD)
if [ "$CURRENT" != "{verified}" ]; then
  echo -e "{ORANGE}Warning: Current commit ($CURRENT) does not match verified commit ({verified}).{RESET}"
fi
"""
    else:
        # Warn that no verified commit is set.
        preamble = f'echo -e "{ORANGE}Warning: No verified commit set for this repository.{RESET}"'
    
    # Create the bash wrapper content including the preamble.
    script_content = f"""#!/bin/bash
cd "{repo_dir}"
{preamble}
{command} "$@"
"""
    alias_path = os.path.join(bin_dir, repo_identifier)
    if preview:
        print(f"[Preview] Would create executable '{alias_path}' with content:\n{script_content}")
    else:
        os.makedirs(bin_dir, exist_ok=True)
        with open(alias_path, "w") as f:
            f.write(script_content)
        os.chmod(alias_path, 0o755)
        print(f"Installed executable for {repo_identifier} at {alias_path}")

def install_repos(selected_repos, base_dir, bin_dir, all_repos, preview=False):
    """Install one or more repositories by creating their executable wrappers and running setup."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Clone it first.")
            continue
        create_executable(repo, base_dir, bin_dir, all_repos, preview=preview)
        # Execute setup command if defined
        setup_cmd = repo.get("setup")
        if setup_cmd:
            run_command(setup_cmd, cwd=repo_dir, preview=preview)

def pull_repos(selected_repos, base_dir, all_repos, preview=False):
    """Run 'git pull' in the repository directory."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            run_command("git pull", cwd=repo_dir, preview=preview)
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

def clone_repos(selected_repos, base_dir, all_repos, preview=False):
    """Clone repositories based on the config.
       Uses replacement if defined; otherwise, constructs URL from provider/account/repository.
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            print(f"Repository '{repo_identifier}' already exists at '{repo_dir}'.")
            continue
        # Determine the repository to clone:
        target = repo.get("replacement") if repo.get("replacement") else f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
        # Construct a clone URL (assuming https)
        clone_url = f"https://{target}.git"
        parent_dir = os.path.dirname(repo_dir)
        os.makedirs(parent_dir, exist_ok=True)
        run_command(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, preview=preview)

def push_repos(selected_repos, base_dir, all_repos, preview=False):
    """Run 'git push' in the repository directory."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            run_command("git push", cwd=repo_dir, preview=preview)
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

def deinstall_repos(selected_repos, base_dir, bin_dir, all_repos, preview=False):
    """Remove the executable wrapper and run teardown command if defined."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        alias_path = os.path.join(bin_dir, repo_identifier)
        if os.path.exists(alias_path):
            if preview:
                print(f"[Preview] Would remove executable '{alias_path}'.")
            else:
                os.remove(alias_path)
                print(f"Removed executable for {repo_identifier}.")
        else:
            print(f"No executable found for {repo_identifier} in {bin_dir}.")
        # Execute teardown if defined
        teardown_cmd = repo.get("teardown")
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if teardown_cmd and os.path.exists(repo_dir):
            run_command(teardown_cmd, cwd=repo_dir, preview=preview)

def delete_repos(selected_repos, base_dir, all_repos, preview=False):
    """Delete the repository directory (rm -rv equivalent)."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            if preview:
                print(f"[Preview] Would delete directory '{repo_dir}' for {repo_identifier}.")
            else:
                shutil.rmtree(repo_dir)
                print(f"Deleted repository directory '{repo_dir}' for {repo_identifier}.")
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

def update_repos(selected_repos, base_dir, bin_dir, all_repos, system_update=False, preview=False):
    """Combine pull and install. If system_update is True, run system update commands."""
    pull_repos(selected_repos, base_dir, all_repos, preview=preview)
    install_repos(selected_repos, base_dir, bin_dir, all_repos, preview=preview)
    if system_update:
        # Example system update commands (for Arch-based systems)
        run_command("yay -S", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)

def status_repos(selected_repos, base_dir, all_repos, list_only=False, system_status=False, preview=False):
    """Show status information for repositories.
       If list_only is True, only list affected repositories.
       If system_status is True, show system update status.
    """
    if system_status:
        print("System status:")
        run_command("yay -Qu", preview=preview)
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        if list_only:
            print(repo_identifier)
        else:
            repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
            if os.path.exists(repo_dir):
                print(f"Status for {repo_identifier}:")
                run_command("git status", cwd=repo_dir, preview=preview)
            else:
                print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

def show_config(selected_repos, full_config=False):
    """Display configuration for one or more repositories. If full_config is True, display entire config."""
    if full_config:
        with open(CONFIG_PATH, 'r') as f:
            print(f.read())
    else:
        for repo in selected_repos:
            identifier = f'{repo.get("provider")}/{repo.get("account")}/{repo.get("repository")}'
            print(f"Repository: {identifier}")
            for key, value in repo.items():
                print(f"  {key}: {value}")
            print("-" * 40)

def interactive_add(config):
    """Interactively prompt the user to add a new repository entry to the config."""
    print("Adding a new repository configuration entry.")
    new_entry = {}
    new_entry["provider"] = input("Provider (e.g., github.com): ").strip()
    new_entry["account"] = input("Account (e.g., yourusername): ").strip()
    new_entry["repository"] = input("Repository name (e.g., mytool): ").strip()
    new_entry["verified"] = input("Verified commit id: ").strip()
    new_entry["command"] = input("Command (optional, leave blank to auto-detect): ").strip()
    new_entry["description"] = input("Description (optional): ").strip()
    new_entry["replacement"] = input("Replacement (optional): ").strip()
    new_entry["setup"] = input("Setup command (optional): ").strip()
    new_entry["teardown"] = input("Teardown command (optional): ").strip()

    # Confirm addition
    print("\nNew entry:")
    for key, value in new_entry.items():
        if value:
            print(f"{key}: {value}")
    confirm = input("Add this entry to config? (y/N): ").strip().lower()
    if confirm == "y":
        config["repos"].append(new_entry)
        save_config(config, CONFIG_PATH)
    else:
        print("Entry not added.")

if __name__ == "__main__":
    # Load configuration
    config = load_config(CONFIG_PATH)
    base_dir = os.path.expanduser(config["base"])
    all_repos_list = config["repos"]

    parser = argparse.ArgumentParser(description="Package Manager")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Define common arguments for subcommands that support identifiers
    def add_identifier_arguments(subparser):
        subparser.add_argument("identifiers", nargs="*", help="Identifier(s) for repositories")
        subparser.add_argument("--all", action="store_true", help="Apply to all repositories in the config")
        subparser.add_argument("--preview", action="store_true", help="Preview changes without executing commands")
        subparser.add_argument("--list", action="store_true", help="List affected repositories (with preview or status)")

    # install
    install_parser = subparsers.add_parser("install", help="Install repository/repositories")
    add_identifier_arguments(install_parser)

    # pull
    pull_parser = subparsers.add_parser("pull", help="Pull updates for repository/repositories")
    add_identifier_arguments(pull_parser)

    # clone
    clone_parser = subparsers.add_parser("clone", help="Clone repository/repositories")
    add_identifier_arguments(clone_parser)

    # push
    push_parser = subparsers.add_parser("push", help="Push changes for repository/repositories")
    add_identifier_arguments(push_parser)

    # deinstall
    deinstall_parser = subparsers.add_parser("deinstall", help="Deinstall repository/repositories")
    add_identifier_arguments(deinstall_parser)

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete repository directory for repository/repositories")
    add_identifier_arguments(delete_parser)

    # update
    update_parser = subparsers.add_parser("update", help="Update (pull + install) repository/repositories")
    add_identifier_arguments(update_parser)
    update_parser.add_argument("--system", action="store_true", help="Include system update commands")

    # status
    status_parser = subparsers.add_parser("status", help="Show status for repository/repositories or system")
    add_identifier_arguments(status_parser)
    status_parser.add_argument("--system", action="store_true", help="Show system status")

    # config: show configuration details
    config_parser = subparsers.add_parser("config", help="Show configuration for repository/repositories or entire config")
    add_identifier_arguments(config_parser)

    # add: interactive add of a new repository entry
    add_parser = subparsers.add_parser("add", help="Interactively add a new repository configuration entry")

    args = parser.parse_args()

    # Handle "config" command separately
    if args.command == "config":
        if args.all or (hasattr(args, "identifiers") and not args.identifiers):
            # Show the entire configuration file
            show_config([], full_config=True)
        else:
            selected = resolve_repos(args.identifiers, all_repos_list)
            if selected:
                show_config(selected, full_config=False)
        sys.exit(0)

    # Handle "add" command
    if args.command == "add":
        interactive_add(config)
        sys.exit(0)

    # For commands using identifiers, decide which repositories to operate on
    if hasattr(args, "identifiers"):
        if args.all or (not args.identifiers):
            selected = all_repos_list
        else:
            selected = resolve_repos(args.identifiers, all_repos_list)
    else:
        selected = []

    # Dispatch commands
    if args.command == "install":
        install_repos(selected, base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "pull":
        pull_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "clone":
        clone_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "push":
        push_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "deinstall":
        deinstall_repos(selected, base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "delete":
        delete_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "update":
        update_repos(selected, base_dir, BIN_DIR, all_repos_list, system_update=args.system, preview=args.preview)
    elif args.command == "status":
        status_repos(selected, base_dir, all_repos_list, list_only=args.list, system_status=args.system, preview=args.preview)
    else:
        parser.print_help()
