import sys
from pkgmgr.pull_with_verification import pull_with_verification
from pkgmgr.install_repos import install_repos

def update_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification, system_update=False, preview=False, quiet=False):
    # Use pull_with_verification instead of the old git_default_exec.
    pull_with_verification(selected_repos, repositories_base_dir, all_repos, extra_args=[], no_verification=no_verification, preview=preview)
    
    # Proceed with the installation process.
    # Note: In the install process, we remove the --no-verification flag to avoid hash checks.
    install_repos(selected_repos, repositories_base_dir, bin_dir, all_repos, no_verification=no_verification, preview=preview, quiet=quiet)
    
    if system_update:
        from pkgmgr.run_command import run_command
        run_command("yay -Syu", preview=preview)
        run_command("sudo pacman -Syyu", preview=preview)
