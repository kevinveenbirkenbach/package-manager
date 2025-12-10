import os
import shutil
from typing import Optional


def resolve_command_for_repo(repo, repo_identifier: str, repo_dir: str) -> Optional[str]:
    """
    Resolve the executable command for a repository.

    Variant B implemented:
    -----------------------
    If the repository explicitly defines the key "command" in its config,
    the function immediately returns that value — even if it is None.

    This allows a repository to intentionally declare:
        command: null
    meaning it does NOT provide a CLI command and should not be resolved.

    This bypasses:
      - Python package detection
      - PATH / Nix / venv binary lookup
      - main.py / main.sh fallback logic
      - SystemExit errors for Python packages without installed commands

    If "command" is NOT defined, the normal resolution logic applies.
    """

    # ----------------------------------------------------------------------
    # 1) Explicit command declaration:
    #
    # If the repository defines the "command" key (even if the value is None),
    # we treat this as authoritative. The repository is explicitly declaring
    # whether it provides a command.
    #
    # - If command is a string → return it as the resolved command
    # - If command is None     → repository intentionally has no CLI command
    #                            → skip all resolution logic
    # ----------------------------------------------------------------------
    if "command" in repo:
        return repo.get("command")

    home = os.path.expanduser("~")

    def is_executable(path: str) -> bool:
        return os.path.exists(path) and os.access(path, os.X_OK)

    # ----------------------------------------------------------------------
    # 2) Detect Python package structure: src/<pkg>/__main__.py
    # ----------------------------------------------------------------------
    is_python_package = False
    src_dir = os.path.join(repo_dir, "src")

    if os.path.isdir(src_dir):
        for root, dirs, files in os.walk(src_dir):
            if "__main__.py" in files:
                is_python_package = True
                python_package_root = root  # for error reporting
                break

    # ----------------------------------------------------------------------
    # 3) Try resolving installed CLI commands (PATH, Nix, venv)
    # ----------------------------------------------------------------------
    path_candidate = shutil.which(repo_identifier)
    system_binary = None
    non_system_binary = None

    if path_candidate:
        # System-level binaries under /usr are not used as CLI commands
        # unless explicitly allowed later.
        if path_candidate.startswith("/usr"):
            system_binary = path_candidate
        else:
            non_system_binary = path_candidate

    # System-level binary → skip creating symlink and return None
    if system_binary:
        if repo.get("ignore_system_binary", False):
            print(
                f"[pkgmgr] System binary for '{repo_identifier}' found at "
                f"{system_binary}; no symlink will be created."
            )
        return None

    # Nix profile binary
    nix_candidate = os.path.join(home, ".nix-profile", "bin", repo_identifier)
    if is_executable(nix_candidate):
        return nix_candidate

    # Non-system PATH binary (user-installed or venv)
    if non_system_binary and is_executable(non_system_binary):
        return non_system_binary

    # ----------------------------------------------------------------------
    # 4) If it is a Python package, it must provide an installed command
    # ----------------------------------------------------------------------
    if is_python_package:
        raise SystemExit(
            f"Repository '{repo_identifier}' appears to be a Python package "
            f"(src-layout with __main__.py detected in '{python_package_root}'). "
            f"No installed command found (PATH, venv, Nix). "
            f"Python packages must be executed via their installed entry point."
        )

    # ----------------------------------------------------------------------
    # 5) Fallback for script-style repositories: main.sh or main.py
    # ----------------------------------------------------------------------
    main_sh = os.path.join(repo_dir, "main.sh")
    main_py = os.path.join(repo_dir, "main.py")

    if is_executable(main_sh):
        return main_sh

    # main.py does not need to be executable
    if os.path.exists(main_py):
        return main_py

    # ----------------------------------------------------------------------
    # 6) Complete resolution failure
    # ----------------------------------------------------------------------
    raise SystemExit(
        f"No executable command could be resolved for repository '{repo_identifier}'. "
        f"No explicit 'command' configured, no installed binary (system/venv/Nix), "
        f"and no main.sh/main.py fallback found."
    )
