import subprocess

def verify_repository(repo, repo_dir, mode="local", no_verification=False):
    """
    Verifies the repository based on its 'verified' field.
    
    The 'verified' field can be a dictionary with the following keys:
      commit:   The expected commit hash.
      gpg_keys: A list of valid GPG key IDs (at least one must match the signing key).

    If mode == "pull", the remote HEAD commit is checked via "git ls-remote origin HEAD".
    Otherwise (mode "local", used for install and clone), the local HEAD commit is checked via "git rev-parse HEAD".

    Returns a tuple:
      (verified_ok, error_details, commit_hash, signing_key)
        - verified_ok: True if the verification passed (or no verification info is set), False otherwise.
        - error_details: A list of error messages for any failed checks.
        - commit_hash: The obtained commit hash.
        - signing_key: The GPG key ID that signed the latest commit (obtained via "git log -1 --format=%GK").
    """
    verified_info = repo.get("verified")
    if not verified_info:
        # Nothing to verify.
        commit_hash = ""
        signing_key = ""
        if mode == "pull":
            try:
                result = subprocess.run("git ls-remote origin HEAD", cwd=repo_dir, shell=True, check=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                commit_hash = result.stdout.split()[0].strip()
            except Exception:
                commit_hash = ""
        else:
            try:
                result = subprocess.run("git rev-parse HEAD", cwd=repo_dir, shell=True, check=True,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                commit_hash = result.stdout.strip()
            except Exception:
                commit_hash = ""
        try:
            result = subprocess.run(["git", "log", "-1", "--format=%GK"], cwd=repo_dir, shell=False, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            signing_key = result.stdout.strip()
        except Exception:
            signing_key = ""
        return True, [], commit_hash, signing_key

    expected_commit = None
    expected_gpg_keys = None
    if isinstance(verified_info, dict):
        expected_commit = verified_info.get("commit")
        expected_gpg_keys = verified_info.get("gpg_keys")
    else:
        # If verified is a plain string, treat it as the expected commit.
        expected_commit = verified_info

    error_details = []

    # Get commit hash according to the mode.
    commit_hash = ""
    if mode == "pull":
        try:
            result = subprocess.run("git ls-remote origin HEAD", cwd=repo_dir, shell=True, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            commit_hash = result.stdout.split()[0].strip()
        except Exception as e:
            error_details.append(f"Error retrieving remote commit: {e}")
    else:
        try:
            result = subprocess.run("git rev-parse HEAD", cwd=repo_dir, shell=True, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            commit_hash = result.stdout.strip()
        except Exception as e:
            error_details.append(f"Error retrieving local commit: {e}")

    # Get the signing key using "git log -1 --format=%GK"
    signing_key = ""
    try:
        result = subprocess.run(["git", "log", "-1", "--format=%GK"], cwd=repo_dir, shell=False, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        signing_key = result.stdout.strip()
    except Exception as e:
        error_details.append(f"Error retrieving signing key: {e}")

    commit_check_passed = True
    gpg_check_passed = True

    if expected_commit:
        if commit_hash != expected_commit:
            commit_check_passed = False
            error_details.append(f"Expected commit: {expected_commit}, found: {commit_hash}")

    if expected_gpg_keys:
        if signing_key not in expected_gpg_keys:
            gpg_check_passed = False
            error_details.append(f"Expected one of GPG keys: {expected_gpg_keys}, found: {signing_key}")

    if expected_commit and expected_gpg_keys:
        verified_ok = commit_check_passed and gpg_check_passed
    elif expected_commit:
        verified_ok = commit_check_passed
    elif expected_gpg_keys:
        verified_ok = gpg_check_passed
    else:
        verified_ok = True

    return verified_ok, error_details, commit_hash, signing_key
