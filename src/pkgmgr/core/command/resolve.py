import os
import shutil
from typing import Optional, List, Dict, Any


Repository = Dict[str, Any]


def _is_executable(path: str) -> bool:
    return os.path.exists(path) and os.access(path, os.X_OK)


def _find_python_package_root(repo_dir: str) -> Optional[str]:
    """
    Detect a Python src-layout package:

        repo_dir/src/<package>/__main__.py

    Returns the directory containing __main__.py (e.g. ".../src/arc")
    or None if no such structure exists.
    """
    src_dir = os.path.join(repo_dir, "src")
    if not os.path.isdir(src_dir):
        return None

    for root, _dirs, files in os.walk(src_dir):
        if "__main__.py" in files:
            return root

    return None


def _nix_binary_candidates(home: str, names: List[str]) -> List[str]:
    """
    Build possible Nix profile binary paths for a list of candidate names.
    """
    return [os.path.join(home, ".nix-profile", "bin", name) for name in names if name]


def _path_binary_candidates(names: List[str]) -> List[str]:
    """
    Resolve candidate names via PATH using shutil.which.
    Returns only existing, executable paths.
    """
    binaries: List[str] = []
    for name in names:
        if not name:
            continue
        candidate = shutil.which(name)
        if candidate and _is_executable(candidate):
            binaries.append(candidate)
    return binaries


def resolve_command_for_repo(
    repo: Repository,
    repo_identifier: str,
    repo_dir: str,
) -> Optional[str]:
    """
    Resolve the executable command for a repository.

    Semantics:
    ----------
    - If the repository explicitly defines the key "command" (even if None),
      that is treated as authoritative and returned immediately.
      This allows e.g.:

          command: null

      for pure library repositories with no CLI.

    - If "command" is not defined, we try to discover a suitable CLI command:
        1. Prefer already installed binaries (PATH, Nix profile).
        2. For Python src-layout packages (src/*/__main__.py), try to infer
           a sensible command name (alias, repo identifier, repository name,
           package directory name) and resolve those via PATH / Nix.
        3. For script-style repos, fall back to main.sh / main.py.
        4. If nothing matches, return None (no CLI) instead of raising.

    The caller can interpret:
      - str  → path to the command (symlink target)
      - None → no CLI command for this repository
    """

    # ------------------------------------------------------------------
    # 1) Explicit command declaration (including explicit "no command")
    # ------------------------------------------------------------------
    if "command" in repo:
        # May be a string path or None. None means: this repo intentionally
        # has no CLI command and should not be resolved.
        return repo.get("command")

    home = os.path.expanduser("~")

    # ------------------------------------------------------------------
    # 2) Collect candidate names for CLI binaries
    #
    #    Order of preference:
    #      - repo_identifier        (usually alias or configured id)
    #      - alias                  (if defined)
    #      - repository name        (e.g. "analysis-ready-code")
    #      - python package name    (e.g. "arc" from src/arc/__main__.py)
    # ------------------------------------------------------------------
    alias = repo.get("alias")
    repository_name = repo.get("repository")

    python_package_root = _find_python_package_root(repo_dir)
    if python_package_root:
        python_package_name = os.path.basename(python_package_root)
    else:
        python_package_name = None

    candidate_names: List[str] = []
    seen: set[str] = set()

    for name in (
        repo_identifier,
        alias,
        repository_name,
        python_package_name,
    ):
        if name and name not in seen:
            seen.add(name)
            candidate_names.append(name)

    # ------------------------------------------------------------------
    # 3) Try resolve via PATH (non-system and system) and Nix profile
    # ------------------------------------------------------------------
    # a) PATH binaries
    path_binaries = _path_binary_candidates(candidate_names)

    # b) Classify system (/usr/...) vs non-system
    system_binary: Optional[str] = None
    non_system_binary: Optional[str] = None

    for bin_path in path_binaries:
        if bin_path.startswith("/usr"):
            # Last system binary wins, but usually there is only one anyway
            system_binary = bin_path
        else:
            non_system_binary = bin_path
            break  # prefer the first non-system binary

    # c) Nix profile binaries
    nix_binaries = [
        path
        for path in _nix_binary_candidates(home, candidate_names)
        if _is_executable(path)
    ]
    nix_binary = nix_binaries[0] if nix_binaries else None

    # Decide priority:
    #   1) non-system PATH binary (user/venv)
    #   2) Nix profile binary
    #   3) system binary (/usr/...)  → only if we want to expose it
    if non_system_binary:
        return non_system_binary

    if nix_binary:
        return nix_binary

    if system_binary:
        # Respect system packages. Depending on your policy you can decide
        # to return None (no symlink, OS owns the command) or to expose it.
        # Here we choose: no symlink for pure system binaries.
        if repo.get("ignore_system_binary", False):
            print(
                f"[pkgmgr] System binary for '{repo_identifier}' found at "
                f"{system_binary}; no symlink will be created."
            )
        return None

    # ------------------------------------------------------------------
    # 4) Script-style repository: fallback to main.sh / main.py
    # ------------------------------------------------------------------
    main_sh = os.path.join(repo_dir, "main.sh")
    main_py = os.path.join(repo_dir, "main.py")

    if _is_executable(main_sh):
        return main_sh

    if os.path.exists(main_py):
        return main_py

    # ------------------------------------------------------------------
    # 5) No CLI discovered
    #
    #    At this point we may still have a Python package structure, but
    #    without any installed CLI entry point and without main.sh/main.py.
    #
    #    This is perfectly valid for library-only repositories, so we do
    #    NOT treat this as an error. The caller can then decide to simply
    #    skip symlink creation.
    # ------------------------------------------------------------------
    if python_package_root:
        print(
            f"[INFO] Repository '{repo_identifier}' appears to be a Python "
            f"package at '{python_package_root}' but no CLI entry point was "
            "found (PATH, Nix, main.sh/main.py). Treating it as a "
            "library-only repository with no command."
        )

    return None
