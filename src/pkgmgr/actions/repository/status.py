import shutil

from pkgmgr.actions.proxy import exec_proxy_command
from pkgmgr.core.command.run import run_command
from pkgmgr.core.repository.identifier import get_repo_identifier


def status_repos(
    selected_repos,
    repositories_base_dir,
    all_repos,
    extra_args,
    list_only: bool = False,
    system_status: bool = False,
    preview: bool = False,
):
    if system_status:
        print("System status:")

        # Arch / AUR updates (if yay / aur_builder is configured)
        run_command("sudo -u aur_builder yay -Qu --noconfirm", preview=preview)

        # Nix profile status (if Nix is available)
        if shutil.which("nix") is not None:
            print("\nNix profile status:")
            try:
                run_command("nix profile list", preview=preview)
            except SystemExit as e:
                print(f"[Warning] Failed to query Nix profiles: {e}")

    if list_only:
        for repo in selected_repos:
            print(get_repo_identifier(repo, all_repos))
    else:
        exec_proxy_command(
            "git",
            selected_repos,
            repositories_base_dir,
            all_repos,
            "status",
            extra_args,
            preview,
        )
