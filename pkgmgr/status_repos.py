import sys
from .exec_proxy_command import exec_proxy_command
from .run_command import run_command

def status_repos(selected_repos, repositories_base_dir, all_repos, extra_args, list_only=False, system_status=False, preview=False):
    if system_status:
        print("System status:")
        run_command("yay -Qu --noconfirm", preview=preview)
    if list_only:
        for repo in selected_repos:
            print(get_repo_identifier(repo, all_repos))
    else:
        exec_proxy_command('git',selected_repos, repositories_base_dir, all_repos, "status", extra_args, preview)