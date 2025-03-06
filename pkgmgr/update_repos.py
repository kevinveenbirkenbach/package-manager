import sys

def update_repos(selected_repos, repositories_base_dir, bin_dir, all_repos:[], no_verification:bool, system_update=False, preview=False, quiet=False):
    git_default_exec(selected_repos, repositories_base_dir, all_repos, extra_args=[],command="pull", preview=preview)
    install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, preview=preview, quiet=quiet)
    if system_update:
        run_command("yay -Syu", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)