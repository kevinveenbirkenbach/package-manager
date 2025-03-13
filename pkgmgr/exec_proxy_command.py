import os
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.run_command import run_command

def exec_proxy_command(proxy_prefix:str,selected_repos, repositories_base_dir, all_repos, proxy_command:str, extra_args, preview:bool):
    """Execute a given proxy command with extra arguments for each repository."""
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir,repo)
        if os.path.exists(repo_dir):
            full_cmd = f"{proxy_prefix} {proxy_command} {' '.join(extra_args)}"
            run_command(full_cmd, cwd=repo_dir, preview=preview)
        else:
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")