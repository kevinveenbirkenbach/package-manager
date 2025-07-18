import sys
from pkgmgr.pull_with_verification import pull_with_verification
from pkgmgr.install_repos import install_repos

def update_repos(
    selected_repos,
    repositories_base_dir,
    bin_dir,
    all_repos,
    no_verification,
    system_update,
    preview: bool,
    quiet: bool, 
    update_dependencies: bool,
    clone_mode: str):
    """
    Update repositories by pulling latest changes and installing them.

    Parameters:
    - selected_repos: List of selected repositories.
    - repositories_base_dir: Base directory for repositories.
    - bin_dir: Directory for symbolic links.
    - all_repos: All repository configurations.
    - no_verification: Whether to skip verification.
    - system_update: Whether to run system update.
    - preview: If True, only show commands without executing.
    - quiet: If True, suppress messages.
    - update_dependencies: Whether to update dependent repositories.
    - clone_mode: Method to clone repositories (ssh or https).
    """
    pull_with_verification(
        selected_repos, 
        repositories_base_dir, 
        all_repos, 
        [], 
        no_verification, 
        preview
    )

    install_repos(
        selected_repos,
        repositories_base_dir,
        bin_dir,
        all_repos,
        no_verification,
        preview,
        quiet,
        clone_mode,
        update_dependencies
    )

    if system_update:
        from pkgmgr.run_command import run_command
        run_command("yay -Syu --noconfirm", preview=preview)
        run_command("sudo pacman -Syyu --noconfirm", preview=preview)