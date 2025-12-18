import os

from pkgmgr.core.command.run import run_command
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier


def deinstall_repos(
    selected_repos,
    repositories_base_dir,
    bin_dir,
    all_repos,
    preview: bool = False,
) -> None:
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)

        # Resolve repository directory
        repo_dir = get_repo_dir(repositories_base_dir, repo)

        # Prefer alias if available; fall back to identifier
        alias_name = str(repo.get("alias") or repo_identifier)
        alias_path = os.path.join(os.path.expanduser(bin_dir), alias_name)

        # Remove alias link/file (interactive)
        if os.path.exists(alias_path):
            confirm = (
                input(
                    f"Are you sure you want to delete link '{alias_path}' for {repo_identifier}? [y/N]: "
                )
                .strip()
                .lower()
            )
            if confirm == "y":
                if preview:
                    print(f"[Preview] Would remove link '{alias_path}'.")
                else:
                    os.remove(alias_path)
                    print(f"Removed link for {repo_identifier}.")
        else:
            print(f"No link found for {repo_identifier} in {bin_dir}.")

        # Run make deinstall if repository exists and has a Makefile
        makefile_path = os.path.join(repo_dir, "Makefile")
        if os.path.exists(makefile_path):
            print(f"Makefile found in {repo_identifier}, running 'make deinstall'...")
            try:
                run_command("make deinstall", cwd=repo_dir, preview=preview)
            except SystemExit as e:
                print(
                    f"[Warning] Failed to run 'make deinstall' for {repo_identifier}: {e}"
                )
