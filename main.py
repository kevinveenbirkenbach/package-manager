#!/usr/bin/env python3

import os
import yaml
import argparse
import json
import os
import sys

# Define configuration file paths.
USER_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "config.yaml")
BIN_DIR = os.path.expanduser("~/.local/bin")

from pkgmgr.clone_repos import clone_repos
from pkgmgr.config_init import config_init
from pkgmgr.create_ink import create_ink
from pkgmgr.deinstall_repos import deinstall_repos
from pkgmgr.delete_repos import delete_repos
from pkgmgr.exec_proxy_command import exec_proxy_command
from pkgmgr.filter_ignored import filter_ignored
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
PROXY_COMMANDS = {
    "git":[
        "pull",
        "push",
        "diff",
        "add",
        "show",
        "checkout",
        "clone",
        "reset",
        "revert",
        "rebase",
        "commit"
    ],
    "docker":[
        "start",
        "stop",
    ],
    "docker compose":[
        "up",
        "down",
        "exec",
        "ps"
    ]
}

class SortedSubParsersAction(argparse._SubParsersAction):
    def add_parser(self, name, **kwargs):
        parser = super().add_parser(name, **kwargs)
        # Sort the list of subparsers each time one is added
        self._choices_actions.sort(key=lambda a: a.dest)
        return parser

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
    subparsers = parser.add_subparsers(dest="command", help="Subcommands", action=SortedSubParsersAction)
    def add_identifier_arguments(subparser):
        subparser.add_argument(
            "identifiers",
            nargs="*",
            help="Identifier(s) for repositories. Default: Repository of current folder.",
            )
        subparser.add_argument(
            "--all", 
            action="store_true", 
            default=False, 
            help="Apply the subcommand to all repositories in the config. Some subcommands ask for confirmation. If you want to give this confirmation for all repositories, pipe 'yes'. E.g: yes | pkgmgr {subcommand} --all"
            )
        subparser.add_argument("--preview", action="store_true", help="Preview changes without executing commands")
        subparser.add_argument("--list", action="store_true", help="List affected repositories (with preview or status)")
        subparser.add_argument("-a", "--args", nargs=argparse.REMAINDER, dest="extra_args", help="Additional parameters to be attached.",default=[])

    install_parser = subparsers.add_parser("install", help="Setup repository/repositories alias links to executables")
    add_identifier_arguments(install_parser)
    install_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress warnings and info messages")
    install_parser.add_argument("--no-verification", action="store_true", default=False, help="Disable verification via commit/gpg")

    deinstall_parser = subparsers.add_parser("deinstall", help="Remove alias links to repository/repositories")
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser("delete", help="Delete repository/repositories alias links to executables")
    add_identifier_arguments(delete_parser)
    
    # Add the 'create' subcommand (with existing identifier arguments)
    create_parser = subparsers.add_parser(
        "create",
        help="Create new repository entries: add them to the config if not already present, initialize the local repository, and push remotely if --remote is set."
    )
    # Reuse the common identifier arguments
    add_identifier_arguments(create_parser)
    create_parser.add_argument(
        "--remote",
        action="store_true",
        help="If set, add the remote and push the initial commit."
    )

    update_parser = subparsers.add_parser("update", help="Update (pull + install) repository/repositories")
    add_identifier_arguments(update_parser)
    update_parser.add_argument("--system", action="store_true", help="Include system update commands")
    update_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress warnings and info messages")
    update_parser.add_argument("--no-verification", action="store_true", default=False, help="Disable verification via commit/gpg")

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
    explore_parser = subparsers.add_parser("explore", help="Open repository in Nautilus file manager")
    add_identifier_arguments(explore_parser)

    terminal_parser = subparsers.add_parser("terminal", help="Open repository in a new GNOME Terminal tab")
    add_identifier_arguments(terminal_parser)

    code_parser = subparsers.add_parser("code", help="Open repository workspace with VS Code")
    add_identifier_arguments(code_parser)   
    
    list_parser = subparsers.add_parser("list", help="List all repositories with details and status")
    list_parser.add_argument("--search", default="", help="Filter repositories that contain the given string")
    list_parser.add_argument("--status", type=str, default="", help="Filter repositories by status (case insensitive)")
    
    # Add the subcommand parser for "shell"
    shell_parser = subparsers.add_parser("shell", help="Execute a shell command in each repository")
    add_identifier_arguments(shell_parser)
    shell_parser.add_argument("-c", "--command", nargs=argparse.REMAINDER, dest="shell_command", help="The shell command (and its arguments) to execute in each repository",default=[])

    make_parser = subparsers.add_parser("make", help="Executes make commands")
    make_subparsers = make_parser.add_subparsers(dest="subcommand", help="Make subcommands", required=True)
    make_install = make_subparsers.add_parser("install", help="Executes the make install command")
    add_identifier_arguments(make_install)
    make_deinstall = make_subparsers.add_parser("deinstall", help="Executes the make deinstall command")
    add_identifier_arguments(make_deinstall)

    proxy_command_parsers = {}
    for command, subcommands in PROXY_COMMANDS.items():
        for subcommand in subcommands:
            proxy_command_parsers[f"{command}_{subcommand}"] = subparsers.add_parser(
                subcommand,
                help=f"Proxies '{command} {subcommand}' to repository/ies",
                description=f"Executes '{command} {subcommand}' for the identified repos.\nTo recieve more help execute '{command} {subcommand} --help'",
                formatter_class=argparse.RawTextHelpFormatter
                )
            if subcommand in ["pull","clone"]:
                proxy_command_parsers[f"{command}_{subcommand}"].add_argument("--no-verification", action="store_true", default=False, help="Disable verification via commit/gpg")
            add_identifier_arguments(proxy_command_parsers[f"{command}_{subcommand}"])
            
    args = parser.parse_args()

    # All 
    if args.command and not args.command in ["config","list","create"]:
        selected = get_selected_repos(args.all,all_repos_list,args.identifiers)
        
    for command, subcommands in PROXY_COMMANDS.items():
        for subcommand in subcommands:
            if args.command == subcommand:
                if args.command == "clone":
                    clone_repos(selected, repositories_base_dir, all_repos_list, args.preview, no_verification=args.no_verification)
                elif args.command == "pull":
                    from pkgmgr.pull_with_verification import pull_with_verification
                    pull_with_verification(selected, repositories_base_dir, all_repos_list, args.extra_args, no_verification=args.no_verification, preview=args.preview)
                else:
                    exec_proxy_command(command,selected, repositories_base_dir, all_repos_list, args.command, args.extra_args, args.preview)
                exit(0)
    
    if args.command in ["make"]:
        exec_proxy_command(args.command,selected, repositories_base_dir, all_repos_list, args.subcommand, args.extra_args, args.preview)
        exit(0)
        
    # Dispatch commands.
    if args.command == "install":
        install_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, args.no_verification, preview=args.preview, quiet=args.quiet)
    elif args.command == "create":
        from pkgmgr.create_repo import create_repo
        # If no identifiers are provided, you can decide to either use the repository of the current folder
        # or prompt the user to supply at least one identifier.
        if not args.identifiers:
            print("No identifiers provided. Please specify at least one identifier in the format provider/account/repository.")
            sys.exit(1)
        else:
            selected = get_selected_repos(True,all_repos_list,None)
            for identifier in args.identifiers:
                create_repo(identifier, config_merged, USER_CONFIG_PATH, BIN_DIR, remote=args.remote, preview=args.preview)
    elif args.command == "list":
        list_repositories(all_repos_list, repositories_base_dir, BIN_DIR, search_filter=args.search, status_filter=args.status)
    elif args.command == "deinstall":
        deinstall_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, preview=args.preview)
    elif args.command == "delete":
        delete_repos(selected,repositories_base_dir, all_repos_list, preview=args.preview)
    elif args.command == "update":
        update_repos(selected,repositories_base_dir, BIN_DIR, all_repos_list, args.no_verification, system_update=args.system, preview=args.preview, quiet=args.quiet)
    elif args.command == "status":
        status_repos(selected,repositories_base_dir, all_repos_list, args.extra_args, list_only=args.list, system_status=args.system, preview=args.preview)
    elif args.command == "explore":
        for repository in selected:
            run_command(f"nautilus {repository["directory"]} & disown")
    elif args.command == "code":
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
            for repository in selected:
                folders.append({"path": repository["directory"]})
            
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
        for repository in selected:
            run_command(f'gnome-terminal --tab --working-directory="{repository["directory"]}"')
    elif args.command == "path":
        for repository in selected:
            print(repository["directory"])
    elif args.command == "shell":
        if not args.shell_command:
            print("No shell command specified.")
            exit(2)
        # Join the provided shell command parts into one string.
        command_to_run = " ".join(args.shell_command)
        for repository in selected:
            print(f"Executing in '{repository["directory"]}': {command_to_run}")
            run_command(command_to_run, cwd=repository["directory"], preview=args.preview)
    elif args.command == "config":
        if args.subcommand == "show":
            if args.all or (not args.identifiers):
                show_config([], USER_CONFIG_PATH, full_config=True)
            else:
                selected = resolve_repos(args.identifiers, all_repos_list)
                if selected:
                    show_config(selected, USER_CONFIG_PATH, full_config=False)
        elif args.subcommand == "add":
            interactive_add(config_merged,USER_CONFIG_PATH)
        elif args.subcommand == "edit":
            """Open the user configuration file in nano."""
            run_command(f"nano {USER_CONFIG_PATH}")
        elif args.subcommand == "init":
            if os.path.exists(USER_CONFIG_PATH):
                with open(USER_CONFIG_PATH, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
            else:
                user_config = {"repositories": []}
            config_init(user_config, config_merged, BIN_DIR, USER_CONFIG_PATH)
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
                save_user_config(user_config,USER_CONFIG_PATH)
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
                save_user_config(user_config,USER_CONFIG_PATH)
    else:
        parser.print_help()
