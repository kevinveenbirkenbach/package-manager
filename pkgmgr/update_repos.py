import sys
from pkgmgr.pull_with_verification import pull_with_verification
from pkgmgr.install_repos import install_repos

def update_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, system_update=False, preview=False, quiet=False, update_dependencies=False):
    
    pull_with_verification(selected_repos, repositories_base_dir, all_repos, extra_args=[], no_verification=no_verification, preview=preview)
    
    install_repos(
        selected_repos,
        repositories_base_dir,
        bin_dir,
        all_repos,
        no_verification=no_verification,
        preview=preview,
        quiet=quiet,
        update_dependencies=update_dependencies
    )
    
    if system_update:
        from pkgmgr.run_command import run_command
        run_command("yay -Syu", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)