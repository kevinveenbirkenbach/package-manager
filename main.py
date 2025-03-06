#!/usr/bin/env python3

import os
import yaml
import argparse
import json
import os
# Ensure the current working directory is the script’s directory
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# Define configuration file paths.
USER_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "config.yaml")
BIN_DIR = os.path.expanduser("~/.local/bin")

from pkgmgr.clone_repos import clone_repos
from pkgmgr.config_init import config_init
from pkgmgr.create_ink import create_ink
from pkgmgr.deinstall_repos import deinstall_repos
from pkgmgr.delete_repos import delete_repos
from pkgmgr.exec_git_command import exec_git_command
from pkgmgr.filter_ignored import filter_ignored
from pkgmgr.generate_alias import generate_alias
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_selected_repos import get_selected_repos
from pkgmgr.install_repos import install_repos
from pkgmgr.interactive_add import interactive_add
from pkgmgr.list_repositories import list_repositories
from pkgmgr.load_config import load_config
from pkgmgr.resolve_repos import resolve_repos
from pkgmgr.run_command import run_command
from pkgmgr.save_user_config import save_user_config
from pkgmgr.show_config import show_config
from pkgmgr.status_repos import status_repos
from pkgmgr.update_repos import update_repos

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

# Main program.
if __name__ == "__main__":
    config_merged = load_config(USER_CONFIG_PATH)
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
        subparser.add_argument(
            "--all", 
            action="store_true", 
            default=False, 
            help="Apply the subcommand to all repositories in the config. Some subcommands ask for confirmation. If you want to give this confirmation for all repositories, pipe 'yes'. E.g: yes | pkgmgr {subcommand} --all"
            )
        subparser.add_argument("--preview", action="store_true", help="Preview changes without executing commands")
        subparser.add_argument("--list", action="store_true", help="List affected repositories (with preview or status)")
        subparser.add_argument("-a", "--args", nargs=argparse.REMAINDER, dest="extra_args", help="Additional parameters to be forwarded e.g. to the git command",default=[])

    install_parser = subparsers.add_parser("install", help="Setup repository/repositories alias links to executables")
    add_identifier_arguments(install_parser)
    install_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress warnings and info messages")
    install_parser.add_argument("--no-verification", default=False, action="store_true", help="Disable verification of repository commit")

    deinstall_parser = subparsers.add_parser("deinstall", help="Remove alias links to repository/repositories")
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser("delete", help="Delete repository/repositories alias links to executables")
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
        selected = get_selected_repos(args.all, all_repos_list, args.identifiers)
        if args.command == "clone":
            clone_repos(selected, repositories_base_dir, all_repos_list, args.preview)
        elif args.command == "pull":
            from pkgmgr.pull_with_verification import pull_with_verification
            pull_with_verification(selected, repositories_base_dir, all_repos_list, args.extra_args, no_verification=args.no_verification, preview=args.preview)
        else:
            exec_git_command(selected, repositories_base_dir, all_repos_list, args.command, args.extra_args, args.preview)
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
                show_config([], USER_CONFIG_PATH, full_config=True)
            else:
                selected = resolve_repos(args.identifiers, all_repos_list)
                if selected:
                    show_config(selected, USER_CONFIG_PATH, full_config=False)
        elif args.subcommand == "add":
            interactive_add(config_merged)
        elif args.subcommand == "edit":
            """Open the user configuration file in nano."""
            run_command(f"nano {USER_CONFIG_PATH}")
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
