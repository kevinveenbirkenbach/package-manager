import os
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.command.run import run_command
import sys


def exec_proxy_command(
    proxy_prefix: str,
    selected_repos,
    repositories_base_dir,
    all_repos,
    proxy_command: str,
    extra_args,
    preview: bool,
):
    """Execute a given proxy command with extra arguments for each repository."""
    error_repos = []
    max_exit_code = 0

    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)

        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")
            continue

        full_cmd = f"{proxy_prefix} {proxy_command} {' '.join(extra_args)}"

        try:
            run_command(full_cmd, cwd=repo_dir, preview=preview)
        except SystemExit as e:
            print(
                f"[ERROR] Command failed in {repo_identifier} with exit code {e.code}."
            )
            error_repos.append((repo_identifier, e.code))
            max_exit_code = max(max_exit_code, e.code)

    if error_repos:
        print("\nSummary of failed commands:")
        for repo_identifier, exit_code in error_repos:
            print(f"- {repo_identifier} failed with exit code {exit_code}")
        sys.exit(max_exit_code)
