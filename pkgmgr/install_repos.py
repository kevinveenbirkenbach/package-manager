import os

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