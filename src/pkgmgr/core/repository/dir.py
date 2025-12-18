import os
import sys
from typing import Any, Dict


def get_repo_dir(repositories_base_dir: str, repo: Dict[str, Any]) -> str:
    """
    Build the local repository directory path from:
      repositories_base_dir/provider/account/repository

    Exits with code 3 and prints diagnostics if the input config is invalid.
    """
    # Base dir must be set and non-empty
    if not repositories_base_dir:
        print(
            "Error: repositories_base_dir is missing.\n"
            "The base directory for repositories seems not correctly configured.\n"
            "Please configure it correctly."
        )
        sys.exit(3)

    # Repo must be a dict-like object
    if not isinstance(repo, dict):
        print(
            f"Error: invalid repo object '{repo}'.\n"
            "The repository entry seems not correctly configured.\n"
            "Please configure it correctly."
        )
        sys.exit(3)

    base_dir = os.path.expanduser(str(repositories_base_dir))

    provider = repo.get("provider")
    account = repo.get("account")
    repository = repo.get("repository")

    missing = [
        k
        for k, v in [
            ("provider", provider),
            ("account", account),
            ("repository", repository),
        ]
        if not v
    ]
    if missing:
        print(
            "Error: repository entry is missing required keys.\n"
            f"Repository: {repo}\n"
            "Please configure it correctly."
        )
        for k in missing:
            print(f"Key '{k}' is missing.")
        sys.exit(3)

    return os.path.join(base_dir, str(provider), str(account), str(repository))
