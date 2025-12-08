from __future__ import annotations

import argparse

from pkgmgr.cli_core.proxy import register_proxy_commands


class SortedSubParsersAction(argparse._SubParsersAction):
    """
    Subparsers action that keeps choices sorted alphabetically.
    """

    def add_parser(self, name, **kwargs):
        parser = super().add_parser(name, **kwargs)
        self._choices_actions.sort(key=lambda a: a.dest)
        return parser


def add_identifier_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Attach generic repository selection arguments to a subparser.
    """
    subparser.add_argument(
        "identifiers",
        nargs="*",
        help=(
            "Identifier(s) for repositories. "
            "Default: Repository of current folder."
        ),
    )
    subparser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help=(
            "Apply the subcommand to all repositories in the config. "
            "Some subcommands ask for confirmation. If you want to give this "
            "confirmation for all repositories, pipe 'yes'. E.g: "
            "yes | pkgmgr {subcommand} --all"
        ),
    )
    subparser.add_argument(
        "--preview",
        action="store_true",
        help="Preview changes without executing commands",
    )
    subparser.add_argument(
        "--list",
        action="store_true",
        help="List affected repositories (with preview or status)",
    )
    subparser.add_argument(
        "-a",
        "--args",
        nargs=argparse.REMAINDER,
        dest="extra_args",
        help="Additional parameters to be attached.",
        default=[],
    )


def add_install_update_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Attach shared flags for install/update-like commands.
    """
    add_identifier_arguments(subparser)
    subparser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress warnings and info messages",
    )
    subparser.add_argument(
        "--no-verification",
        action="store_true",
        default=False,
        help="Disable verification via commit/gpg",
    )
    subparser.add_argument(
        "--dependencies",
        action="store_true",
        help="Also pull and update dependencies",
    )
    subparser.add_argument(
        "--clone-mode",
        choices=["ssh", "https", "shallow"],
        default="ssh",
        help=(
            "Specify the clone mode: ssh, https, or shallow "
            "(HTTPS shallow clone; default: ssh)"
        ),
    )


def create_parser(description_text: str) -> argparse.ArgumentParser:
    """
    Create and configure the top-level argument parser for pkgmgr.

    This function defines *only* the CLI surface (arguments & subcommands),
    but no business logic.
    """
    parser = argparse.ArgumentParser(
        description=description_text,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        help="Subcommands",
        action=SortedSubParsersAction,
    )

    # ------------------------------------------------------------
    # install / update
    # ------------------------------------------------------------
    install_parser = subparsers.add_parser(
        "install",
        help="Setup repository/repositories alias links to executables",
    )
    add_install_update_arguments(install_parser)

    update_parser = subparsers.add_parser(
        "update",
        help="Update (pull + install) repository/repositories",
    )
    add_install_update_arguments(update_parser)
    update_parser.add_argument(
        "--system",
        action="store_true",
        help="Include system update commands",
    )

    # ------------------------------------------------------------
    # deinstall / delete
    # ------------------------------------------------------------
    deinstall_parser = subparsers.add_parser(
        "deinstall",
        help="Remove alias links to repository/repositories",
    )
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete repository/repositories alias links to executables",
    )
    add_identifier_arguments(delete_parser)

    # ------------------------------------------------------------
    # create
    # ------------------------------------------------------------
    create_parser = subparsers.add_parser(
        "create",
        help=(
            "Create new repository entries: add them to the config if not "
            "already present, initialize the local repository, and push "
            "remotely if --remote is set."
        ),
    )
    add_identifier_arguments(create_parser)
    create_parser.add_argument(
        "--remote",
        action="store_true",
        help="If set, add the remote and push the initial commit.",
    )

    # ------------------------------------------------------------
    # status
    # ------------------------------------------------------------
    status_parser = subparsers.add_parser(
        "status",
        help="Show status for repository/repositories or system",
    )
    add_identifier_arguments(status_parser)
    status_parser.add_argument(
        "--system",
        action="store_true",
        help="Show system status",
    )

    # ------------------------------------------------------------
    # config
    # ------------------------------------------------------------
    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="subcommand",
        help="Config subcommands",
        required=True,
    )

    config_show = config_subparsers.add_parser(
        "show",
        help="Show configuration",
    )
    add_identifier_arguments(config_show)

    config_subparsers.add_parser(
        "add",
        help="Interactively add a new repository entry",
    )

    config_subparsers.add_parser(
        "edit",
        help="Edit configuration file with nano",
    )

    config_subparsers.add_parser(
        "init",
        help="Initialize user configuration by scanning the base directory",
    )

    config_delete = config_subparsers.add_parser(
        "delete",
        help="Delete repository entry from user config",
    )
    add_identifier_arguments(config_delete)

    config_ignore = config_subparsers.add_parser(
        "ignore",
        help="Set ignore flag for repository entries in user config",
    )
    add_identifier_arguments(config_ignore)
    config_ignore.add_argument(
        "--set",
        choices=["true", "false"],
        required=True,
        help="Set ignore to true or false",
    )

    # ------------------------------------------------------------
    # path / explore / terminal / code / shell
    # ------------------------------------------------------------
    path_parser = subparsers.add_parser(
        "path",
        help="Print the path(s) of repository/repositories",
    )
    add_identifier_arguments(path_parser)

    explore_parser = subparsers.add_parser(
        "explore",
        help="Open repository in Nautilus file manager",
    )
    add_identifier_arguments(explore_parser)

    terminal_parser = subparsers.add_parser(
        "terminal",
        help="Open repository in a new GNOME Terminal tab",
    )
    add_identifier_arguments(terminal_parser)

    code_parser = subparsers.add_parser(
        "code",
        help="Open repository workspace with VS Code",
    )
    add_identifier_arguments(code_parser)

    shell_parser = subparsers.add_parser(
        "shell",
        help="Execute a shell command in each repository",
    )
    add_identifier_arguments(shell_parser)
    shell_parser.add_argument(
        "-c",
        "--command",
        nargs=argparse.REMAINDER,
        dest="shell_command",
        help="The shell command (and its arguments) to execute in each repository",
        default=[],
    )

    # ------------------------------------------------------------
    # branch
    # ------------------------------------------------------------
    branch_parser = subparsers.add_parser(
        "branch",
        help="Branch-related utilities (e.g. open feature branches)",
    )
    branch_subparsers = branch_parser.add_subparsers(
        dest="subcommand",
        help="Branch subcommands",
        required=True,
    )

    branch_open = branch_subparsers.add_parser(
        "open",
        help="Create and push a new branch on top of a base branch",
    )
    branch_open.add_argument(
        "name",
        nargs="?",
        help="Name of the new branch (optional; will be asked interactively if omitted)",
    )
    branch_open.add_argument(
        "--base",
        default="main",
        help="Base branch to create the new branch from (default: main)",
    )

    # ------------------------------------------------------------
    # release
    # ------------------------------------------------------------
    release_parser = subparsers.add_parser(
        "release",
        help=(
            "Create a release for repository/ies by incrementing version "
            "and updating the changelog."
        ),
    )
    release_parser.add_argument(
        "release_type",
        choices=["major", "minor", "patch"],
        help="Type of version increment for the release (major, minor, patch).",
    )
    release_parser.add_argument(
        "-m",
        "--message",
        default=None,
        help=(
            "Optional release message to add to the changelog and tag."
        ),
    )
    # Generic selection / preview / list / extra_args
    add_identifier_arguments(release_parser)
    # Close current branch after successful release
    release_parser.add_argument(
        "--close",
        action="store_true",
        help=(
            "Close the current branch after a successful release in each "
            "repository, if it is not main/master."
        ),
    )
    # Force: skip preview+confirmation and run release directly
    release_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=(
            "Skip the interactive preview+confirmation step and run the "
            "release directly."
        ),
    )

    # ------------------------------------------------------------
    # version
    # ------------------------------------------------------------
    version_parser = subparsers.add_parser(
        "version",
        help=(
            "Show version information for repository/ies "
            "(git tags, pyproject.toml, flake.nix, PKGBUILD, debian, spec, Ansible Galaxy)."
        ),
    )
    add_identifier_arguments(version_parser)

    # ------------------------------------------------------------
    # changelog
    # ------------------------------------------------------------
    changelog_parser = subparsers.add_parser(
        "changelog",
        help=(
            "Show changelog derived from Git history. "
            "By default, shows the changes between the last two SemVer tags."
        ),
    )
    changelog_parser.add_argument(
        "range",
        nargs="?",
        default="",
        help=(
            "Optional tag or range (e.g. v1.2.3 or v1.2.0..v1.2.3). "
            "If omitted, the changelog between the last two SemVer "
            "tags is shown."
        ),
    )
    add_identifier_arguments(changelog_parser)

    # ------------------------------------------------------------
    # list
    # ------------------------------------------------------------
    list_parser = subparsers.add_parser(
        "list",
        help="List all repositories with details and status",
    )
    list_parser.add_argument(
        "--search",
        default="",
        help="Filter repositories that contain the given string",
    )
    list_parser.add_argument(
        "--status",
        type=str,
        default="",
        help="Filter repositories by status (case insensitive)",
    )

    # ------------------------------------------------------------
    # make (wrapper around make in repositories)
    # ------------------------------------------------------------
    make_parser = subparsers.add_parser(
        "make",
        help="Executes make commands",
    )
    add_identifier_arguments(make_parser)
    make_subparsers = make_parser.add_subparsers(
        dest="subcommand",
        help="Make subcommands",
        required=True,
    )

    make_install = make_subparsers.add_parser(
        "install",
        help="Executes the make install command",
    )
    add_identifier_arguments(make_install)

    make_deinstall = make_subparsers.add_parser(
        "deinstall",
        help="Executes the make deinstall command",
    )
    add_identifier_arguments(make_deinstall)

    # ------------------------------------------------------------
    # Proxy commands (git, docker, docker compose)
    # ------------------------------------------------------------
    register_proxy_commands(subparsers)

    return parser
