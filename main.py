#!/usr/bin/env python3
"""
Package Manager Script

This script provides the following commands:
  install    {identifier(s)|--all}
      - Creates an executable bash wrapper in the bin folder that calls the command for the repository.
      - Executes the repository’s "setup" command if specified.
  pull       {identifier(s)|--all} [<git-args>...]
      - Executes 'git pull' with any extra arguments passed.
  clone      {identifier(s)|--all}
      - Clones the repository from a remote.
  push       {identifier(s)|--all} [<git-args>...]
      - Executes 'git push' with any extra arguments passed.
  deinstall  {identifier(s)|--all}
      - Removes the executable alias.
      - Executes the repository’s "teardown" command if specified.
  delete     {identifier(s)|--all}
      - Deletes the repository directory.
  update     {identifier(s)|--all|--system}
      - Combines pull and install; if --system is specified also runs system update commands.
  status     {identifier(s)|--all} [<git-args>...] [--system] [--list]
      - Executes 'git status' with any extra arguments passed.
  diff       {identifier(s)|--all} [<git-args>...]
      - Executes 'git diff' with any extra arguments passed.
  add        {identifier(s)|--all} [<git-args>...]
      - Executes 'git add' with any extra arguments passed.
  show       {identifier(s)|--all} [<git-args>...]
      - Executes 'git show' with any extra arguments passed.
  checkout   {identifier(s)|--all} [<git-args>...]
      - Executes 'git checkout' with any extra arguments passed.

Additionally, there is a **config** command with subcommands:
  config show   {identifier(s)|--all}
      - Displays the merged configuration (defaults plus user additions).
  config add
      - Interactively adds a new repository entry to the user configuration.
  config edit
      - Opens the user configuration file (config/config.yaml) in nano.

Additional flags:
  --preview   Only show the changes without executing commands.
  --list      When used with preview or status, only list affected repositories.

Identifiers:
  - If a repository’s name is unique then you can just use the repository name.
  - Otherwise use "provider/account/repository".

Configuration is merged from two files:
  - **config/defaults.yaml** (system defaults)
  - **config/config.yaml** (user-specific configuration)

The user config supplements the default repositories and can override the base path.

"""

import argparse
import os
import subprocess
import shutil
import sys
import yaml

# Define configuration file paths.
DEFAULT_CONFIG_PATH = os.path.join("config", "defaults.yaml")
USER_CONFIG_PATH = os.path.join("config", "config.yaml")
BIN_DIR = os.path.expanduser("~/.local/bin")

def load_config():
    """Load configuration from defaults and merge in user config if present.
    
    If the user config defines a 'base', it overrides the default.
    The user config's 'repos' are appended to the default repos.
    """
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print(f"Default configuration file '{DEFAULT_CONFIG_PATH}' not found.")
        sys.exit(1)
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    # Verify defaults have required keys.
    if "base" not in config or "repos" not in config:
        print("Default config file must contain 'base' and 'repos' keys.")
        sys.exit(1)

    # If user config exists, merge it.
    if os.path.exists(USER_CONFIG_PATH):
        with open(USER_CONFIG_PATH, 'r') as f:
            user_config = yaml.safe_load(f)
        if user_config:
            # Override base if defined.
            if "base" in user_config:
                config["base"] = user_config["base"]
            # Append any user-defined repos.
            if "repos" in user_config:
                config["repos"].extend(user_config["repos"])
    return config

def save_user_config(user_config):
    """Save the user configuration to USER_CONFIG_PATH."""
    os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
    with open(USER_CONFIG_PATH, 'w') as f:
        yaml.dump(user_config, f)
    print(f"User configuration updated in {USER_CONFIG_PATH}.")

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
                if sum(1 for r in all_repos if r.get("repository") == ident) == 1:
                    matches.append(repo)
        if not matches:
            print(f"Identifier '{ident}' did not match any repository in config.")
        else:
            selected.extend(matches)
    return selected

def create_executable(repo, base_dir, bin_dir, all_repos, preview=False):
    """Create an executable bash wrapper for the repository.
    
    If 'verified' is set, the wrapper will checkout that commit and warn in orange if it does not match.
    If no verified commit is set, a warning in orange is printed.
    If an 'alias' field is provided, a symlink is created in the bin directory with that name.
    """
    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
    command = repo.get("command")
    if not command:
        main_sh = os.path.join(repo_dir, "main.sh")
        main_py = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_sh):
            command = "bash main.sh"
        elif os.path.exists(main_py):
            command = "python3 main.py"
        else:
            print(f"No command defined and no main.sh/main.py found in {repo_dir}. Skipping alias creation.")
            return

    # ANSI escape codes for orange (color code 208) and reset.
    ORANGE = r"\033[38;5;208m"
    RESET = r"\033[0m"

    verified = repo.get("verified")
    if verified:
        preamble = f"""\
git checkout {verified} || echo -e "{ORANGE}Warning: Failed to checkout commit {verified}.{RESET}"
CURRENT=$(git rev-parse HEAD)
if [ "$CURRENT" != "{verified}" ]; then
  echo -e "{ORANGE}Warning: Current commit ($CURRENT) does not match verified commit ({verified}).{RESET}"
fi
"""
    else:
        preamble = f'echo -e "{ORANGE}Warning: No verified commit set for this repository.{RESET}"'
    
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

        # Create alias if provided in the config.
        alias_name = repo.get("alias")
        if alias_name:
            alias_link_path = os.path.join(bin_dir, alias_name)
            try:
                if os.path.exists(alias_link_path) or os.path.islink(alias_link_path):
                    os.remove(alias_link_path)
                os.symlink(alias_path, alias_link_path)
                print(f"Created alias '{alias_name}' pointing to {repo_identifier}")
            except Exception as e:
                print(f"Error creating alias '{alias_name}': {e}")
                
def install_repos(selected_repos, base_dir, bin_dir, all_repos, preview=False):
    """Install repositories by creating executable wrappers and running setup."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Clone it first.")
            continue
        create_executable(repo, base_dir, bin_dir, all_repos, preview=preview)
        setup_cmd = repo.get("setup")
        if setup_cmd:
            run_command(setup_cmd, cwd=repo_dir, preview=preview)

# Common helper to execute a git command with extra arguments.
def exec_git_command(selected_repos, base_dir, all_repos, git_cmd, extra_args, preview=False):
    """Execute a given git command with extra arguments for each repository."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            full_cmd = f"git {git_cmd} {' '.join(extra_args)}"
            run_command(full_cmd, cwd=repo_dir, preview=preview)
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

# Refactored git command functions.
def pull_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "pull", extra_args, preview)

def push_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "push", extra_args, preview)

def status_repos(selected_repos, base_dir, all_repos, extra_args, list_only=False, system_status=False, preview=False):
    if system_status:
        print("System status:")
        run_command("yay -Qu", preview=preview)
    if list_only:
        for repo in selected_repos:
            print(get_repo_identifier(repo, all_repos))
    else:
        exec_git_command(selected_repos, base_dir, all_repos, "status", extra_args, preview)

def clone_repos(selected_repos, base_dir, all_repos, preview=False):
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if os.path.exists(repo_dir):
            print(f"Repository '{repo_identifier}' already exists at '{repo_dir}'.")
            continue
        target = repo.get("replacement") if repo.get("replacement") else f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
        clone_url = f"https://{target}.git"
        parent_dir = os.path.dirname(repo_dir)
        os.makedirs(parent_dir, exist_ok=True)
        run_command(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, preview=preview)

def deinstall_repos(selected_repos, base_dir, bin_dir, all_repos, preview=False):
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
        teardown_cmd = repo.get("teardown")
        repo_dir = os.path.join(base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
        if teardown_cmd and os.path.exists(repo_dir):
            run_command(teardown_cmd, cwd=repo_dir, preview=preview)

def delete_repos(selected_repos, base_dir, all_repos, preview=False):
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
    pull_repos(selected_repos, base_dir, all_repos, extra_args=[], preview=preview)
    install_repos(selected_repos, base_dir, bin_dir, all_repos, preview=preview)
    if system_update:
        run_command("yay -S", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)

# Additional git commands.
def diff_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "diff", extra_args, preview)

def gitadd_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "add", extra_args, preview)

def show_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "show", extra_args, preview)

def checkout_repos(selected_repos, base_dir, all_repos, extra_args, preview=False):
    exec_git_command(selected_repos, base_dir, all_repos, "checkout", extra_args, preview)

def show_config(selected_repos, full_config=False):
    """Display configuration for one or more repositories, or entire merged config."""
    if full_config:
        # Print the merged config.
        merged = load_config()
        print(yaml.dump(merged, default_flow_style=False))
    else:
        for repo in selected_repos:
            identifier = f'{repo.get("provider")}/{repo.get("account")}/{repo.get("repository")}'
            print(f"Repository: {identifier}")
            for key, value in repo.items():
                print(f"  {key}: {value}")
            print("-" * 40)

def interactive_add(config):
    """Interactively prompt the user to add a new repository entry to the user config.
    
    The new entry is saved into the user config file (config/config.yaml).
    """
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
    new_entry["alias"] = input("Alias (optional): ").strip()

    print("\nNew entry:")
    for key, value in new_entry.items():
        if value:
            print(f"{key}: {value}")
    confirm = input("Add this entry to user config? (y/N): ").strip().lower()
    if confirm == "y":
        # Load existing user config or initialize.
        if os.path.exists(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {}
        user_config.setdefault("repos", [])
        user_config["repos"].append(new_entry)
        save_user_config(user_config)
    else:
        print("Entry not added.")

def edit_config():
    """Open the user configuration file in nano."""
    run_command(f"nano {USER_CONFIG_PATH}")

if __name__ == "__main__":
    config = load_config()
    base_dir = os.path.expanduser(config["base"])
    all_repos_list = config["repos"]

    parser = argparse.ArgumentParser(description="Package Manager")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    def add_identifier_arguments(subparser):
        subparser.add_argument("identifiers", nargs="*", help="Identifier(s) for repositories")
        subparser.add_argument("--all", action="store_true", help="Apply to all repositories in the config")
        subparser.add_argument("--preview", action="store_true", help="Preview changes without executing commands")
        subparser.add_argument("--list", action="store_true", help="List affected repositories (with preview or status)")
        subparser.add_argument("extra_args", nargs=argparse.REMAINDER, help="Extra arguments for the git command")

    # Top-level commands
    install_parser = subparsers.add_parser("install", help="Install repository/repositories")
    add_identifier_arguments(install_parser)

    pull_parser = subparsers.add_parser("pull", help="Pull updates for repository/repositories")
    add_identifier_arguments(pull_parser)

    clone_parser = subparsers.add_parser("clone", help="Clone repository/repositories")
    add_identifier_arguments(clone_parser)

    push_parser = subparsers.add_parser("push", help="Push changes for repository/repositories")
    add_identifier_arguments(push_parser)

    deinstall_parser = subparsers.add_parser("deinstall", help="Deinstall repository/repositories")
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser("delete", help="Delete repository directory for repository/repositories")
    add_identifier_arguments(delete_parser)

    update_parser = subparsers.add_parser("update", help="Update (pull + install) repository/repositories")
    add_identifier_arguments(update_parser)
    update_parser.add_argument("--system", action="store_true", help="Include system update commands")

    status_parser = subparsers.add_parser("status", help="Show status for repository/repositories or system")
    add_identifier_arguments(status_parser)
    status_parser.add_argument("--system", action="store_true", help="Show system status")

    diff_parser = subparsers.add_parser("diff", help="Execute 'git diff' for repository/repositories")
    add_identifier_arguments(diff_parser)

    gitadd_parser = subparsers.add_parser("add", help="Execute 'git add' for repository/repositories")
    add_identifier_arguments(gitadd_parser)

    show_parser = subparsers.add_parser("show", help="Execute 'git show' for repository/repositories")
    add_identifier_arguments(show_parser)

    checkout_parser = subparsers.add_parser("checkout", help="Execute 'git checkout' for repository/repositories")
    add_identifier_arguments(checkout_parser)

    # Config commands
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="subcommand", help="Config subcommands", required=True)

    config_show = config_subparsers.add_parser("show", help="Show configuration")
    add_identifier_arguments(config_show)

    config_add = config_subparsers.add_parser("add", help="Interactively add a new repository entry")
    config_edit = config_subparsers.add_parser("edit", help="Edit configuration file with nano")

    args = parser.parse_args()

    if args.command == "install":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        install_repos(selected, base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "pull":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        pull_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "clone":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        clone_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "push":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        push_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "deinstall":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        deinstall_repos(selected, base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "delete":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        delete_repos(selected, base_dir, all_repos_list, preview=args.preview)
    elif args.command == "update":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        update_repos(selected, base_dir, BIN_DIR, all_repos_list, system_update=args.system, preview=args.preview)
    elif args.command == "status":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        status_repos(selected, base_dir, all_repos_list, args.extra_args, list_only=args.list, system_status=args.system, preview=args.preview)
    elif args.command == "diff":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        diff_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "add":
        # Top-level 'add' is used for git add.
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        gitadd_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "show":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        show_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "checkout":
        selected = all_repos_list if args.all or (not args.identifiers) else resolve_repos(args.identifiers, all_repos_list)
        checkout_repos(selected, base_dir, all_repos_list, args.extra_args, preview=args.preview)
    elif args.command == "config":
        if args.subcommand == "show":
            if args.all or (not args.identifiers):
                show_config([], full_config=True)
            else:
                selected = resolve_repos(args.identifiers, all_repos_list)
                if selected:
                    show_config(selected, full_config=False)
        elif args.subcommand == "add":
            interactive_add(config)
        elif args.subcommand == "edit":
            edit_config()
    else:
        parser.print_help()
