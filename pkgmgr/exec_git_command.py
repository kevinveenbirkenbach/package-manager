import os

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