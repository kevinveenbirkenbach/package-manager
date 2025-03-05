import re
import hashlib
import os
import subprocess
import shutil
import sys
import yaml
import argparse
import json

# Define configuration file paths.
DEFAULT_CONFIG_PATH = os.path.join("config", "defaults.yaml")
USER_CONFIG_PATH = os.path.join("config", "config.yaml")
BIN_DIR = os.path.expanduser("~/.local/bin")

# Commands proxied by package-manager
GIT_DEFAULT_COMMANDS = [
    "pull",
    "push",
    "diff",
    "add",
    "show",
    "checkout",
    "clone",
    "reset",
    "revert",
    "commit"
]

def load_config():
    """Load configuration from defaults and merge in user config if present."""
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print(f"Default configuration file '{DEFAULT_CONFIG_PATH}' not found.")
        sys.exit(1)
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    if "directories" not in config or "repositories" not in config:
        print("Default config file must contain 'directories' and 'repositories' keys.")
        sys.exit(1)
    if os.path.exists(USER_CONFIG_PATH):
        with open(USER_CONFIG_PATH, 'r') as f:
            user_config = yaml.safe_load(f)
        if user_config:
            if "directories" in user_config:
                config["directories"] = user_config["directories"]
            if "repositories" in user_config:
                config["repositories"].extend(user_config["repositories"])
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
    If the repository name is unique among all_repos, return repository name;
    otherwise, return 'provider/account/repository'.
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
    The identifier can be:
      - the full identifier "provider/account/repository"
      - the repository name (if unique among all_repos)
      - the alias (if defined)
    """
    selected = []
    for ident in identifiers:
        matches = []
        for repo in all_repos:
            full_id = f'{repo.get("provider")}/{repo.get("account")}/{repo.get("repository")}'
            if ident == full_id:
                matches.append(repo)
            elif ident == repo.get("alias"):
                matches.append(repo)
            elif ident == repo.get("repository"):
                # Only match if repository name is unique among all_repos.
                if sum(1 for r in all_repos if r.get("repository") == ident) == 1:
                    matches.append(repo)
        if not matches:
            print(f"Identifier '{ident}' did not match any repository in config.")
        else:
            selected.extend(matches)
    return selected

def filter_ignored(repos):
    """Filter out repositories that have 'ignore' set to True."""
    return [r for r in repos if not r.get("ignore", False)]

def generate_alias(repo, bin_dir, existing_aliases):
    """
    Generate an alias for a repository based on its repository name.
    
    Steps:
      1. Keep only consonants from the repository name (letters from BCDFGHJKLMNPQRSTVWXYZ).
      2. Collapse consecutive identical consonants.
      3. Truncate to at most 12 characters.
      4. If that alias conflicts (already in existing_aliases or a file exists in bin_dir),
         then prefix with the first letter of provider and account.
      5. If still conflicting, append a three-character hash until the alias is unique.
    """
    repo_name = repo.get("repository")
    # Keep only consonants.
    consonants = re.sub(r"[^bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]", "", repo_name)
    # Collapse consecutive identical consonants.
    collapsed = re.sub(r"(.)\1+", r"\1", consonants)
    base_alias = collapsed[:12] if len(collapsed) > 12 else collapsed
    candidate = base_alias.lower()

    def conflict(alias):
        alias_path = os.path.join(bin_dir, alias)
        return alias in existing_aliases or os.path.exists(alias_path)

    if not conflict(candidate):
        return candidate

    prefix = (repo.get("provider", "")[0] + repo.get("account", "")[0]).lower()
    candidate2 = (prefix + candidate)[:12]
    if not conflict(candidate2):
        return candidate2

    h = hashlib.md5(repo_name.encode("utf-8")).hexdigest()[:3]
    candidate3 = (candidate2 + h)[:12]
    while conflict(candidate3):
        candidate3 += "x"
        candidate3 = candidate3[:12]
    return candidate3

def create_executable(repo, repositories_base_dir, bin_dir, all_repos, quiet=False, preview=False, no_verification=False):
    """
    Create an executable bash wrapper for the repository.
    
    If 'verified' is set, the wrapper will checkout that commit and warn (unless quiet is True).
    If no verified commit is set, a warning is printed unless quiet is True.
    If an 'alias' field is provided, a symlink is created in bin_dir with that alias.
    """
    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = get_repo_dir(repositories_base_dir,repo)
    command = repo.get("command")
    if not command:
        main_sh = os.path.join(repo_dir, "main.sh")
        main_py = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_sh):
            command = "bash main.sh"
        elif os.path.exists(main_py):
            command = "python3 main.py"
        else:
            if not quiet:
                print(f"No command defined and no main.sh/main.py found in {repo_dir}. Skipping alias creation.")
            return

    ORANGE = r"\033[38;5;208m"
    RESET = r"\033[0m"
    
    if no_verification:
        preamble = ""
    else:
        if verified := repo.get("verified"):
            if not quiet:
                preamble = f"""\
git checkout {verified} || echo -e "{ORANGE}Warning: Failed to checkout commit {verified}.{RESET}"
CURRENT=$(git rev-parse HEAD)
if [ "$CURRENT" != "{verified}" ]; then
  echo -e "{ORANGE}Warning: Current commit ($CURRENT) does not match verified commit ({verified}).{RESET}"
fi
"""
            else:
                preamble = ""
        else:
            preamble = "" if quiet else f'echo -e "{ORANGE}Warning: No verified commit set for this repository.{RESET}"'
   
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
        if not quiet:
            print(f"Installed executable for {repo_identifier} at {alias_path}")

        alias_name = repo.get("alias")
        if alias_name:
            alias_link_path = os.path.join(bin_dir, alias_name)
            try:
                if os.path.exists(alias_link_path) or os.path.islink(alias_link_path):
                    os.remove(alias_link_path)
                os.symlink(alias_path, alias_link_path)
                if not quiet:
                    print(f"Created alias '{alias_name}' pointing to {repo_identifier}")
            except Exception as e:
                if not quiet:
                    print(f"Error creating alias '{alias_name}': {e}")

def install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos:[], no_verification:bool, preview=False, quiet=False):
    """Install repositories by creating executable wrappers and running setup."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir,repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Clone it first.")
            continue
        create_executable(repo, repositories_base_dir, bin_dir, all_repos, quiet=quiet, preview=preview, no_verification=no_verification)
        setup_cmd = repo.get("setup")
        if setup_cmd:
            run_command(setup_cmd, cwd=repo_dir, preview=preview)

def exec_git_command(selected_repos, repositories_base_dir, all_repos, git_cmd, extra_args, preview=False):
    """Execute a given git command with extra arguments for each repository."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir,repo)
        if os.path.exists(repo_dir):
            full_cmd = f"git {git_cmd} {' '.join(extra_args)}"
            run_command(full_cmd, cwd=repo_dir, preview=preview)
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")


def status_repos(selected_repos, repositories_base_dir, all_repos, extra_args, list_only=False, system_status=False, preview=False):
    if system_status:
        print("System status:")
        run_command("yay -Qu", preview=preview)
    if list_only:
        for repo in selected_repos:
            print(get_repo_identifier(repo, all_repos))
    else:
        exec_git_command(selected_repos, repositories_base_dir, all_repos, "status", extra_args, preview)

def get_repo_dir(repositories_base_dir:str,repo:{})->str:
    try:
        return os.path.join(repositories_base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
    except TypeError as e:
        if repositories_base_dir:
            print(f"Error: {e} \nThe repository {repo} seems not correct configured.\nPlease configure it correct.")
            for key in ["provider","account","repository"]:
                if not repo.get(key,False):
                   print(f"Key '{key}' is missing.")
        else:
            print(f"Error: {e} \nThe base {base} seems not correct configured.\nPlease configure it correct.")
        sys.exit(1)

def clone_repos(selected_repos, repositories_base_dir: str, all_repos, preview=False):
    import subprocess  # ensure subprocess is imported
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
            # Simulate a successful clone in preview mode.
            result = subprocess.CompletedProcess(args=[], returncode=0)
        else:
            result = subprocess.run(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, shell=True)
        
        # If SSH clone returns an error code, ask user whether to try HTTPS.
        if result.returncode != 0:
            print(f"[WARNING] SSH clone failed for '{repo_identifier}' with return code {result.returncode}.")
            choice = input("Do you want to attempt HTTPS clone instead? (y/N): ").strip().lower()
            if choice == 'y':
                target = repo.get("replacement") if repo.get("replacement") else f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
                clone_url = f"https://{target}.git"
                print(f"[INFO] Attempting to clone '{repo_identifier}' using HTTPS from {clone_url} into '{repo_dir}'.")
                if preview:
                    print(f"[Preview] Would run: git clone {clone_url} {repo_dir} in {parent_dir}")
                else:
                    subprocess.run(f"git clone {clone_url} {repo_dir}", cwd=parent_dir, shell=True)
            else:
                print(f"[INFO] HTTPS clone not attempted for '{repo_identifier}'.")

def deinstall_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, preview=False):
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
        repo_dir = get_repo_dir(repositories_base_dir,repo)
        if teardown_cmd and os.path.exists(repo_dir):
            run_command(teardown_cmd, cwd=repo_dir, preview=preview)

def delete_repos(selected_repos, repositories_base_dir, all_repos, preview=False):
    if not selected_repos:
        print("Error: No repositories selected for deletion.")
        return

    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if os.path.exists(repo_dir):
            confirm = input(f"Are you sure you want to delete directory '{repo_dir}' for {repo_identifier}? [y/N]: ").strip().lower()
            if confirm == "y":
                if preview:
                    print(f"[Preview] Would delete directory '{repo_dir}' for {repo_identifier}.")
                else:
                    try:
                        shutil.rmtree(repo_dir)
                        print(f"Deleted repository directory '{repo_dir}' for {repo_identifier}.")
                    except Exception as e:
                        print(f"Error deleting '{repo_dir}' for {repo_identifier}: {e}")
            else:
                print(f"Skipped deletion of '{repo_dir}' for {repo_identifier}.")
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")

def update_repos(selected_repos, repositories_base_dir, bin_dir, all_repos:[], no_verification:bool, system_update=False, preview=False, quiet=False):
    git_default_exec(selected_repos, repositories_base_dir, all_repos, extra_args=[],command="pull", preview=preview)
    install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=preview, quiet=quiet)
    if system_update:
        run_command("yay -Syu", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)
        
def git_default_exec(selected_repos, repositories_base_dir, all_repos, extra_args, command:str, preview=False):
    exec_git_command(selected_repos, repositories_base_dir, all_repos, command, extra_args, preview)

def show_config(selected_repos, full_config=False):
    """Display configuration for one or more repositories, or the entire merged config."""
    if full_config:
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
    """Interactively prompt the user to add a new repository entry to the user config."""
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
    # Allow the user to mark this entry as ignored.
    ignore_val = input("Ignore this entry? (y/N): ").strip().lower()
    if ignore_val == "y":
        new_entry["ignore"] = True

    print("\nNew entry:")
    for key, value in new_entry.items():
        if value:
            print(f"{key}: {value}")
    confirm = input("Add this entry to user config? (y/N): ").strip().lower()
    if confirm == "y":
        if os.path.exists(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, 'r') as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {"repositories": []}
        user_config.setdefault("repositories", [])
        user_config["repositories"].append(new_entry)
        save_user_config(user_config)
    else:
        print("Entry not added.")

def edit_config():
    """Open the user configuration file in nano."""
    run_command(f"nano {USER_CONFIG_PATH}")

def config_init(user_config, defaults_config, bin_dir):
    """
    Scan the base directory (defaults_config["base"]) for repositories.
    The folder structure is assumed to be:
      {base}/{provider}/{account}/{repository}
    For each repository found, automatically determine:
      - provider, account, repository from folder names.
      - verified: the latest commit (via 'git log -1 --format=%H').
      - alias: generated from the repository name using generate_alias().
    Repositories already defined in defaults_config["repositories"] or user_config["repositories"] are skipped.
    """
    repositories_base_dir = os.path.expanduser(defaults_config["directories"]["repositories"])
    if not os.path.isdir(repositories_base_dir):
        print(f"Base directory '{repositories_base_dir}' does not exist.")
        return

    default_keys = {(entry.get("provider"), entry.get("account"), entry.get("repository"))
                    for entry in defaults_config.get("repositories", [])}
    existing_keys = {(entry.get("provider"), entry.get("account"), entry.get("repository"))
                     for entry in user_config.get("repositories", [])}
    existing_aliases = {entry.get("alias") for entry in user_config.get("repositories", []) if entry.get("alias")}

    new_entries = []
    for provider in os.listdir(repositories_base_dir):
        provider_path = os.path.join(repositories_base_dir, provider)
        if not os.path.isdir(provider_path):
            continue
        for account in os.listdir(provider_path):
            account_path = os.path.join(provider_path, account)
            if not os.path.isdir(account_path):
                continue
            for repo_name in os.listdir(account_path):
                repo_path = os.path.join(account_path, repo_name)
                if not os.path.isdir(repo_path):
                    continue
                key = (provider, account, repo_name)
                if key in default_keys or key in existing_keys:
                    continue
                try:
                    result = subprocess.run(
                        ["git", "log", "-1", "--format=%H"],
                        cwd=repo_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    verified = result.stdout.strip()
                except Exception as e:
                    verified = ""
                    print(f"Could not determine latest commit for {repo_name} ({provider}/{account}): {e}")

                entry = {
                    "provider": provider,
                    "account": account,
                    "repository": repo_name,
                    "verified": verified,
                    "ignore": True
                }
                alias = generate_alias({"repository": repo_name, "provider": provider, "account": account}, bin_dir, existing_aliases)
                entry["alias"] = alias
                existing_aliases.add(alias)
                new_entries.append(entry)
                print(f"Adding new repo entry: {entry}")

    if new_entries:
        user_config.setdefault("repositories", []).extend(new_entries)
        save_user_config(user_config)
    else:
        print("No new repositories found.")
        
def get_selected_repos(show_all:bool,all_repos_list,identifiers=None):
    if show_all:
        selected = all_repos_list 
    else:
        selected = resolve_repos(identifiers, all_repos_list)
    return filter_ignored(selected)

def list_repositories(all_repos, repositories_base_dir, bin_dir, search_filter="", status_filter=""):
    """
    List all repositories with their attributes and status information.

    Parameters:
      all_repos (list): List of repository configurations.
      repositories_base_dir (str): The base directory where repositories are located.
      bin_dir (str): The directory where executable wrappers are stored.
      search_filter (str): Filter for repository attributes (case insensitive).
      status_filter (str): Filter for computed status info (case insensitive).

    For each repository, the identifier is printed in bold, the description (if available)
    in italic, then all other attributes and computed status are printed.
    If the repository is installed, a hint is displayed under the attributes.
    Repositories are filtered out if either the search_filter is not found in any attribute or
    if the status_filter is not found in the computed status string.
    """
    search_filter = search_filter.lower() if search_filter else ""
    status_filter = status_filter.lower() if status_filter else ""
    
    # Define status colors using colors not used for other attributes:
    # Avoid red (for ignore), blue (for homepage) and yellow (for verified).
    status_colors = {
        "Installed": "\033[1;32m",       # Green
        "Not Installed": "\033[1;35m",   # Magenta
        "Cloned": "\033[1;36m",          # Cyan
        "Clonable": "\033[1;37m",        # White
        "Ignored": "\033[38;5;208m",     # Orange (extended)
        "Active": "\033[38;5;129m",      # Light Purple (extended)
        "Installable": "\033[38;5;82m"   # Light Green (extended)
    }
    
    for repo in all_repos:
        # Combine all attribute values into one string for filtering.
        repo_text = " ".join(str(v) for v in repo.values()).lower()
        if search_filter and search_filter not in repo_text:
            continue

        # Compute status information for the repository.
        identifier = get_repo_identifier(repo, all_repos)
        executable_path = os.path.join(bin_dir, identifier)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        status_list = []
        
        # Check if the executable exists (Installed).
        if os.path.exists(executable_path):
            status_list.append("Installed")
        else:
            status_list.append("Not Installed")
        # Check if the repository directory exists (Cloned).
        if os.path.exists(repo_dir):
            status_list.append("Cloned")
        else:
            status_list.append("Clonable")
        # Mark ignored repositories.
        if repo.get("ignore", False):
            status_list.append("Ignored")
        else:
            status_list.append("Active")
        # Define installable as cloned but not installed.
        if os.path.exists(repo_dir) and not os.path.exists(executable_path):
            status_list.append("Installable")
        
        # Build a colored status string.
        colored_statuses = [f"{status_colors.get(s, '')}{s}\033[0m" for s in status_list]
        status_str = ", ".join(colored_statuses)
        
        # If a status_filter is provided, only display repos whose status contains the filter.
        if status_filter and status_filter not in status_str.lower():
            continue

        # Display repository details:
        # Print the identifier in bold.
        print(f"\033[1m{identifier}\033[0m")
        # Print the description in italic if it exists.
        description = repo.get("description")
        if description:
            print(f"\n\033[3m{description}\033[0m")
        print("\nAttributes:")
        # Loop through all attributes.
        for key, value in repo.items():
            formatted_value = str(value)
            # Special formatting for "verified" attribute (yellow).
            if key == "verified" and value:
                formatted_value = f"\033[1;33m{value}\033[0m"
            # Special formatting for "ignore" flag (red if True).
            if key == "ignore" and value:
                formatted_value = f"\033[1;31m{value}\033[0m"
            if key == "description":
                continue
            # Highlight homepage in blue.
            if key.lower() == "homepage" and value:
                formatted_value = f"\033[1;34m{value}\033[0m"
            print(f"  {key}: {formatted_value}")
        # Always display the computed status.
        print(f"  Status: {status_str}")
        # If the repository is installed, display a hint for more info.
        if os.path.exists(executable_path):
            print(f"\nMore information and help: \033[1;4mpkgmgr {identifier} --help\033[0m\n")
        print("-" * 40)
# Main program.
if __name__ == "__main__":
    config_merged = load_config()
    repositories_base_dir = os.path.expanduser(config_merged["directories"]["repositories"])
    all_repos_list = config_merged["repositories"]
    description_text = """\
\033[1;32mPackage Manager 🤖📦\033[0m
\033[3mKevin's Package Manager ist drafted by and designed for:
  \033[1;34mKevin Veen-Birkenbach
  \033[0m\033[4mhttps://www.veen.world/\033[0m

\033[1mOverview:\033[0m
A configurable Python tool to manage multiple repositories via a unified command-line interface.
This tool automates common Git operations (clone, pull, push, status, etc.) and creates executable wrappers and custom aliases to simplify your workflow.

\033[1mFeatures:\033[0m
  • \033[1;33mAuto-install & Setup:\033[0m Automatically detect and set up repositories.
  • \033[1;33mGit Command Integration:\033[0m Execute Git commands with extra parameters.
  • \033[1;33mExplorer & Terminal Support:\033[0m Open repositories in your file manager or a new terminal tab.
  • \033[1;33mComprehensive Configuration:\033[0m Manage settings via YAML files (default & user-specific).

For detailed help on each command, use:
    \033[1m pkgmgr <command> --help\033[0m
"""

    parser = argparse.ArgumentParser(description=description_text,formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    def add_identifier_arguments(subparser):
        subparser.add_argument("identifiers", nargs="*", help="Identifier(s) for repositories")
        subparser.add_argument("--all", action="store_true", default=False, help="Apply to all repositories in the config")
        subparser.add_argument("--preview", action="store_true", help="Preview changes without executing commands")
        subparser.add_argument("--list", action="store_true", help="List affected repositories (with preview or status)")
        subparser.add_argument("-a", "--args", nargs=argparse.REMAINDER, dest="extra_args", help="Additional parameters to be forwarded e.g. to the git command",default=[])

    install_parser = subparsers.add_parser("install", help="Install repository/repositories")
    add_identifier_arguments(install_parser)
    install_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress warnings and info messages")
    install_parser.add_argument("--no-verification", default=False, action="store_true", help="Disable verification of repository commit")

    deinstall_parser = subparsers.add_parser("deinstall", help="Deinstall repository/repositories")
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser("delete", help="Delete repository directory for repository/repositories")
    add_identifier_arguments(delete_parser)

    update_parser = subparsers.add_parser("update", help="Update (pull + install) repository/repositories")
    add_identifier_arguments(update_parser)
    update_parser.add_argument("--system", action="store_true", help="Include system update commands")
    update_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress warnings and info messages")
    update_parser.add_argument("--no-verification", action="store_true", default=False, help="Disable verification of repository commit")

    status_parser = subparsers.add_parser("status", help="Show status for repository/repositories or system")
    add_identifier_arguments(status_parser)
    status_parser.add_argument("--system", action="store_true", help="Show system status")

    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="subcommand", help="Config subcommands", required=True)
    config_show = config_subparsers.add_parser("show", help="Show configuration")
    add_identifier_arguments(config_show)
    config_add = config_subparsers.add_parser("add", help="Interactively add a new repository entry")
    config_edit = config_subparsers.add_parser("edit", help="Edit configuration file with nano")
    config_init_parser = config_subparsers.add_parser("init", help="Initialize user configuration by scanning the base directory")
    config_delete = config_subparsers.add_parser("delete", help="Delete repository entry from user config")
    add_identifier_arguments(config_delete)
    config_ignore = config_subparsers.add_parser("ignore", help="Set ignore flag for repository entries in user config")
    add_identifier_arguments(config_ignore)
    config_ignore.add_argument("--set", choices=["true", "false"], required=True, help="Set ignore to true or false")
    path_parser = subparsers.add_parser("path", help="Print the path(s) of repository/repositories")
    add_identifier_arguments(path_parser)
    explor_parser = subparsers.add_parser("explor", help="Open repository in Nautilus file manager")
    add_identifier_arguments(explor_parser)

    terminal_parser = subparsers.add_parser("terminal", help="Open repository in a new GNOME Terminal tab")
    add_identifier_arguments(terminal_parser)

    code_parser = subparsers.add_parser("code", help="Open repository workspace with VS Code")
    add_identifier_arguments(code_parser)   
    
    list_parser = subparsers.add_parser("list", help="List all repositories with details and status")
    list_parser.add_argument("--search", default="", help="Filter repositories that contain the given string")
    list_parser.add_argument("--status", type=str, default="", help="Filter repositories by status (case insensitive)")
    
    # Proxies the default git commands
    for git_command in GIT_DEFAULT_COMMANDS:
        add_identifier_arguments(
            subparsers.add_parser(
                git_command,
                help=f"Proxies 'git {git_command}' to one repository/repositories",
                description=f"Executes 'git {git_command}' for the identified repos.\nTo recieve more help execute 'git {git_command} --help'",
                formatter_class=argparse.RawTextHelpFormatter
                )
        )

    args = parser.parse_args()

    # Dispatch commands.
    if args.command == "install":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        install_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, args.no_verification, preview=args.preview, quiet=args.quiet)
    elif args.command in GIT_DEFAULT_COMMANDS:
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        if args.command == "clone":
            clone_repos(selected, repositories_base_dir, all_repos_list, args.preview)
        else:
            git_default_exec(selected, repositories_base_dir, all_repos_list, args.extra_args, args.command, preview=args.preview)
    elif args.command == "list":
        list_repositories(all_repos_list, repositories_base_dir, BIN_DIR, search_filter=args.search, status_filter=args.status)
    elif args.command == "deinstall":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        deinstall_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "delete":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        delete_repos(selected,repositories_base_dir, all_repos_list, preview=args.preview)
    elif args.command == "update":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        update_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, args.no_verification, system_update=args.system, preview=args.preview, quiet=args.quiet)
    elif args.command == "status":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        status_repos(selected,repositories_base_dir, all_repos_list, args.extra_args, list_only=args.list, system_status=args.system, preview=args.preview)
    elif args.command == "explor":
        selected = get_selected_repos(args.all, all_repos_list, args.identifiers)
        for repo in selected:
            repo_dir = get_repo_dir(repositories_base_dir, repo)
            run_command(f"nautilus {repo_dir}")
    elif args.command == "code":
        selected = get_selected_repos(args.all, all_repos_list, args.identifiers)
        if not selected:
            print("No repositories selected.")
        else:
            identifiers = [get_repo_identifier(repo, all_repos_list) for repo in selected]
            sorted_identifiers = sorted(identifiers)
            workspace_name = "_".join(sorted_identifiers) + ".code-workspace"
            workspaces_dir = os.path.expanduser(config_merged.get("directories").get("workspaces"))
            os.makedirs(workspaces_dir, exist_ok=True)
            workspace_file = os.path.join(workspaces_dir, workspace_name)
            
            folders = []
            for repo in selected:
                repo_dir = os.path.expanduser(get_repo_dir(repositories_base_dir, repo))
                folders.append({"path": repo_dir})
            
            workspace_data = {
                "folders": folders,
                "settings": {}
            }
            
            if not os.path.exists(workspace_file):
                with open(workspace_file, "w") as f:
                    json.dump(workspace_data, f, indent=4)
                print(f"Created workspace file: {workspace_file}")
            else:
                print(f"Using existing workspace file: {workspace_file}")
            run_command(f'code "{workspace_file}"')


    elif args.command == "terminal":
        selected = get_selected_repos(args.all, all_repos_list, args.identifiers)
        for repo in selected:
            repo_dir = get_repo_dir(repositories_base_dir, repo)
            run_command(f'gnome-terminal --tab --working-directory="{repo_dir}"')

    elif args.command == "path":
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        paths = [
            get_repo_dir(repositories_base_dir,repo)
            for repo in selected
        ]
        print(" ".join(paths))
    elif args.command == "config":
        if args.subcommand == "show":
            if args.all or (not args.identifiers):
                show_config([], full_config=True)
            else:
                selected = resolve_repos(args.identifiers, all_repos_list)
                if selected:
                    show_config(selected, full_config=False)
        elif args.subcommand == "add":
            interactive_add(config_merged)
        elif args.subcommand == "edit":
            edit_config()
        elif args.subcommand == "init":
            if os.path.exists(USER_CONFIG_PATH):
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
            else:
                user_config = {"repositories": []}
            config_init(user_config, config_merged, BIN_DIR)
        elif args.subcommand == "delete":
            # Load user config from USER_CONFIG_PATH.
            if os.path.exists(USER_CONFIG_PATH):
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = yaml.safe_load(f) or {"repositories": []}
            else:
                user_config = {"repositories": []}
            if args.all or not args.identifiers:
                print("You must specify identifiers to delete.")
            else:
                to_delete = resolve_repos(args.identifiers, user_config.get("repositories", []))
                new_repos = [entry for entry in user_config.get("repositories", []) if entry not in to_delete]
                user_config["repositories"] = new_repos
                save_user_config(user_config)
                print(f"Deleted {len(to_delete)} entries from user config.")
        elif args.subcommand == "ignore":
            # Load user config from USER_CONFIG_PATH.
            if os.path.exists(USER_CONFIG_PATH):
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = yaml.safe_load(f) or {"repositories": []}
            else:
                user_config = {"repositories": []}
            if args.all or not args.identifiers:
                print("You must specify identifiers to modify ignore flag.")
            else:
                to_modify = resolve_repos(args.identifiers, user_config.get("repositories", []))
                for entry in user_config["repositories"]:
                    key = (entry.get("provider"), entry.get("account"), entry.get("repository"))
                    for mod in to_modify:
                        mod_key = (mod.get("provider"), mod.get("account"), mod.get("repository"))
                        if key == mod_key:
                            entry["ignore"] = (args.set == "true")
                            print(f"Set ignore for {key} to {entry['ignore']}")
                save_user_config(user_config)
    else:
        parser.print_help()
