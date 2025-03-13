import os
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir

def deinstall_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, preview=False):
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        alias_path = os.path.join(bin_dir, repo_identifier)
        if os.path.exists(alias_path):
            confirm = input(f"Are you sure you want to delete link '{alias_path}' for {repo_identifier}? [y/N]: ").strip().lower()
            if confirm == "y":
                if preview:
                    print(f"[Preview] Would remove link '{alias_path}'.")
                else:
                    os.remove(alias_path)
                    print(f"Removed link for {repo_identifier}.")
        else:
            print(f"No link found for {repo_identifier} in {bin_dir}.")
        # Check if a Makefile exists and run make.
        makefile_path = os.path.join(repo_dir, "Makefile")
        if os.path.exists(makefile_path):
            print(f"Makefile found in {repo_identifier}, running 'make deinstall'...")
            run_command("make deinstall", cwd=repo_dir, preview=preview)