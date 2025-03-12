import os
import subprocess
import sys
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir

def pull_with_verification(selected_repos, repositories_base_dir, all_repos, extra_args, no_verification, preview=False):
    """
    Executes "git pull" for each repository with hash verification.

    For repositories with a 'verified' hash in the configuration, this function first
    retrieves the remote commit hash (using 'git ls-remote origin HEAD'). If the remote hash
    does not match the verified hash, the user is prompted to confirm the pull (unless --no-verification
    is set, in which case the pull proceeds automatically).
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")
            continue

        verified_hash = repo.get("verified")
        remote_hash = ""
        try:
            result = subprocess.run("git ls-remote origin HEAD", cwd=repo_dir, shell=True, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # The first token in the output is the remote HEAD commit hash.
            remote_hash = result.stdout.split()[0].strip()
        except Exception as e:
            print(f"Error retrieving remote commit for {repo_identifier}: {e}")

        proceed = True
        if not no_verification and verified_hash and remote_hash and remote_hash != verified_hash:
            print(f"Warning: For {repo_identifier}, the remote hash ({remote_hash}) does not match the verified hash ({verified_hash}).")
            choice = input("Proceed with 'git pull'? (y/N): ").strip().lower()
            if choice != "y":
                proceed = False

        if proceed:
            full_cmd = f"git pull {' '.join(extra_args)}"
            if preview:
                print(f"[Preview] In '{repo_dir}': {full_cmd}")
            else:
                print(f"Running in '{repo_dir}': {full_cmd}")
                result = subprocess.run(full_cmd, cwd=repo_dir, shell=True)
                if result.returncode != 0:
                    print(f"'git pull' for {repo_identifier} failed with exit code {result.returncode}.")
                    sys.exit(result.returncode)
