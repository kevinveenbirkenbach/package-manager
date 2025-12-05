import os
import subprocess
import sys
import tempfile
import shutil
import yaml

from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr.create_ink import create_ink
from pkgmgr.run_command import run_command
from pkgmgr.verify import verify_repository
from pkgmgr.clone_repos import clone_repos


def _extract_pkgbuild_array(repo_dir: str, var_name: str) -> list:
    """
    Extract a Bash array (depends/makedepends) from PKGBUILD using bash itself.
    Returns a list of package names or an empty list on error.
    """
    pkgbuild_path = os.path.join(repo_dir, "PKGBUILD")
    if not os.path.exists(pkgbuild_path):
        return []

    script = f'source PKGBUILD >/dev/null 2>&1; printf "%s\\n" "${{{var_name}[@]}}"'
    try:
        output = subprocess.check_output(
            ["bash", "-lc", script],
            cwd=repo_dir,
            text=True,
        )
    except Exception:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def _install_arch_dependencies_from_pkgbuild(repo_dir: str, preview: bool) -> None:
    """
    If PKGBUILD exists and pacman is available, install depends + makedepends
    via pacman.
    """
    if shutil.which("pacman") is None:
        return

    pkgbuild_path = os.path.join(repo_dir, "PKGBUILD")
    if not os.path.exists(pkgbuild_path):
        return

    depends = _extract_pkgbuild_array(repo_dir, "depends")
    makedepends = _extract_pkgbuild_array(repo_dir, "makedepends")
    all_pkgs = depends + makedepends

    if not all_pkgs:
        return

    cmd = "sudo pacman -S --noconfirm " + " ".join(all_pkgs)
    run_command(cmd, preview=preview)


def _install_nix_flake_profile(repo_dir: str, preview: bool) -> None:
    """
    If flake.nix exists and 'nix' is available, try to install a profile
    from the flake. Convention: try .#pkgmgr, then .#default.
    """
    flake_path = os.path.join(repo_dir, "flake.nix")
    if not os.path.exists(flake_path):
        return
    if shutil.which("nix") is None:
        print("Warning: flake.nix found but 'nix' command not available. Skipping flake setup.")
        return

    print("Nix flake detected, attempting to install profile output...")
    for output in ("pkgmgr", "default"):
        cmd = f"nix profile install {repo_dir}#{output}"
        try:
            run_command(cmd, preview=preview)
            print(f"Nix flake output '{output}' successfully installed.")
            break
        except SystemExit as e:
            print(f"[Warning] Failed to install Nix flake output '{output}': {e}")


def _install_pkgmgr_dependencies_from_manifest(
    repo_dir: str,
    no_verification: bool,
    update_dependencies: bool,
    clone_mode: str,
    preview: bool,
) -> None:
    """
    Read pkgmgr.yml (if present) and install referenced pkgmgr repository
    dependencies.

    Expected format:

    version: 1
    author: "..."
    url: "..."
    description: "..."
    dependencies:
      - repository: github:user/repo
        version: main
        reason: "Optional description"
    """
    manifest_path = os.path.join(repo_dir, "pkgmgr.yml")
    if not os.path.exists(manifest_path):
        return

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading pkgmgr.yml in '{repo_dir}': {e}")
        return

    dependencies = manifest.get("dependencies", []) or []
    if not isinstance(dependencies, list) or not dependencies:
        return

    # Optional: show basic metadata (author/url/description) if present
    author = manifest.get("author")
    url = manifest.get("url")
    description = manifest.get("description")

    if not preview:
        print("pkgmgr manifest detected:")
        if author:
            print(f"  author: {author}")
        if url:
            print(f"  url: {url}")
        if description:
            print(f"  description: {description}")

    dep_repo_ids = []
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        repo_id = dep.get("repository")
        if repo_id:
            dep_repo_ids.append(str(repo_id))

    # Optionally: update (pull) dependencies before installing
    if update_dependencies and dep_repo_ids:
        cmd_pull = "pkgmgr pull " + " ".join(dep_repo_ids)
        try:
            run_command(cmd_pull, preview=preview)
        except SystemExit as e:
            print(f"Warning: 'pkgmgr pull' for dependencies failed (exit code {e}).")

    # Install dependencies one by one
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue

        repo_id = dep.get("repository")
        if not repo_id:
            continue

        version = dep.get("version")
        reason = dep.get("reason")

        if reason and not preview:
            print(f"Installing dependency {repo_id}: {reason}")
        else:
            print(f"Installing dependency {repo_id}...")

        cmd = f"pkgmgr install {repo_id}"

        if version:
            cmd += f" --version {version}"

        if no_verification:
            cmd += " --no-verification"

        if update_dependencies:
            cmd += " --dependencies"

        if clone_mode:
            cmd += f" --clone-mode {clone_mode}"

        try:
            run_command(cmd, preview=preview)
        except SystemExit as e:
            print(f"[Warning] Failed to install dependency '{repo_id}': {e}")


def install_repos(
    selected_repos,
    repositories_base_dir,
    bin_dir,
    all_repos,
    no_verification,
    preview,
    quiet,
    clone_mode: str,
    update_dependencies: bool,
):
    """
    Install repositories by creating symbolic links and processing standard
    manifest files (pkgmgr.yml, PKGBUILD, flake.nix, Ansible requirements,
    Python manifests, Makefile).
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)

        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' does not exist. Cloning it now...")
            # Pass the clone_mode parameter to clone_repos
            clone_repos(
                [repo],
                repositories_base_dir,
                all_repos,
                preview,
                no_verification,
                clone_mode,
            )
            if not os.path.exists(repo_dir):
                print(f"Cloning failed for repository {repo_identifier}. Skipping installation.")
                continue

        verified_info = repo.get("verified")
        verified_ok, errors, commit_hash, signing_key = verify_repository(
            repo,
            repo_dir,
            mode="local",
            no_verification=no_verification,
        )

        if not no_verification and verified_info and not verified_ok:
            print(f"Warning: Verification failed for {repo_identifier}:")
            for err in errors:
                print(f"  - {err}")
            choice = input("Proceed with installation? (y/N): ").strip().lower()
            if choice != "y":
                print(f"Skipping installation for {repo_identifier}.")
                continue

        # Create the symlink using create_ink.
        create_ink(
            repo,
            repositories_base_dir,
            bin_dir,
            all_repos,
            quiet=quiet,
            preview=preview,
        )

        # 1) pkgmgr.yml (pkgmgr-internal manifest for other repositories)
        _install_pkgmgr_dependencies_from_manifest(
            repo_dir=repo_dir,
            no_verification=no_verification,
            update_dependencies=update_dependencies,
            clone_mode=clone_mode,
            preview=preview,
        )

        # 2) Arch: PKGBUILD (depends/makedepends)
        _install_arch_dependencies_from_pkgbuild(repo_dir, preview=preview)

        # 3) Nix: flake.nix
        _install_nix_flake_profile(repo_dir, preview=preview)

        # 4) Ansible: requirements.yml (only collections/roles)
        req_file = os.path.join(repo_dir, "requirements.yml")
        if os.path.exists(req_file):
            try:
                with open(req_file, "r", encoding="utf-8") as f:
                    requirements = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error loading requirements.yml in {repo_identifier}: {e}")
                requirements = None

            if requirements and isinstance(requirements, dict):
                if "collections" in requirements or "roles" in requirements:
                    print(f"Ansible dependencies found in {repo_identifier}, installing...")

                    ansible_requirements = {}
                    if "collections" in requirements:
                        ansible_requirements["collections"] = requirements["collections"]
                    if "roles" in requirements:
                        ansible_requirements["roles"] = requirements["roles"]

                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        suffix=".yml",
                        delete=False,
                    ) as tmp:
                        yaml.dump(ansible_requirements, tmp, default_flow_style=False)
                        tmp_filename = tmp.name

                    if "collections" in ansible_requirements:
                        print(f"Ansible collections found in {repo_identifier}, installing...")
                        cmd = f"ansible-galaxy collection install -r {tmp_filename}"
                        run_command(cmd, cwd=repo_dir, preview=preview)

                    if "roles" in ansible_requirements:
                        print(f"Ansible roles found in {repo_identifier}, installing...")
                        cmd = f"ansible-galaxy role install -r {tmp_filename}"
                        run_command(cmd, cwd=repo_dir, preview=preview)

        # 5) Python: pyproject.toml (modern) / requirements.txt (classic)
        pyproject_path = os.path.join(repo_dir, "pyproject.toml")
        if os.path.exists(pyproject_path):
            print(f"pyproject.toml found in {repo_identifier}, installing Python project...")
            cmd = "~/.venvs/pkgmgr/bin/pip install ."
            run_command(cmd, cwd=repo_dir, preview=preview)

        req_txt_file = os.path.join(repo_dir, "requirements.txt")
        if os.path.exists(req_txt_file):
            print(f"requirements.txt found in {repo_identifier}, installing Python dependencies...")
            cmd = "~/.venvs/pkgmgr/bin/pip install -r requirements.txt"
            run_command(cmd, cwd=repo_dir, preview=preview)

        # 6) Makefile: make install (if present)
        makefile_path = os.path.join(repo_dir, "Makefile")
        if os.path.exists(makefile_path):
            cmd = "make install"
            try:
                run_command(cmd, cwd=repo_dir, preview=preview)
            except SystemExit as e:
                print(f"[Warning] Failed to run '{cmd}' for {repo_identifier}: {e}")
