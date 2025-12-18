import shutil
import os
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir


def delete_repos(selected_repos, repositories_base_dir, all_repos, preview=False):
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if os.path.exists(repo_dir):
            confirm = (
                input(
                    f"Are you sure you want to delete directory '{repo_dir}' for {repo_identifier}? [y/N]: "
                )
                .strip()
                .lower()
            )
            if confirm == "y":
                if preview:
                    print(
                        f"[Preview] Would delete directory '{repo_dir}' for {repo_identifier}."
                    )
                else:
                    try:
                        shutil.rmtree(repo_dir)
                        print(
                            f"Deleted repository directory '{repo_dir}' for {repo_identifier}."
                        )
                    except Exception as e:
                        print(f"Error deleting '{repo_dir}' for {repo_identifier}: {e}")
            else:
                print(f"Skipped deletion of '{repo_dir}' for {repo_identifier}.")
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")
