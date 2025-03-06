import os

def create_executable(repo, repositories_base_dir, bin_dir, all_repos, quiet=False, preview=False, no_verification=False):
    """
    Create an executable bash wrapper for the repository.
    
    If 'verified' is set, the wrapper will checkout that commit and warn (unless quiet is True).
    If no verified commit is set, a warning is printed unless quiet is True.
    If an 'alias' field is provided, a symlink is created in bin_dir with that alias.
    """
    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = get_repo_dir(repositories_base_dir,repo)
    command = repo.get("command")
    if not command:
        main_sh = os.path.join(repo_dir, "main.sh")
        main_py = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_sh):
            command = "bash main.sh"
        elif os.path.exists(main_py):
            command = "python3 main.py"
        else:
            if not quiet:
                print(f"No command defined and no main.sh/main.py found in {repo_dir}. Skipping alias creation.")
            return

    ORANGE = r"\033[38;5;208m"
    RESET = r"\033[0m"
    
    if no_verification:
        preamble = ""
    else:
        if verified := repo.get("verified"):
            if not quiet:
                preamble = f"""\
git checkout {verified} || echo -e "{ORANGE}Warning: Failed to checkout commit {verified}.{RESET}"
CURRENT=$(git rev-parse HEAD)
if [ "$CURRENT" != "{verified}" ]; then
  echo -e "{ORANGE}Warning: Current commit ($CURRENT) does not match verified commit ({verified}).{RESET}"
fi
"""
            else:
                preamble = ""
        else:
            preamble = "" if quiet else f'echo -e "{ORANGE}Warning: No verified commit set for this repository.{RESET}"'
   
    script_content = f"""#!/bin/bash
cd "{repo_dir}"
{preamble}
{command} "$@"
"""
    alias_path = os.path.join(bin_dir, repo_identifier)
    if preview:
        print(f"[Preview] Would create executable '{alias_path}' with content:\n{script_content}")
    else:
        os.makedirs(bin_dir, exist_ok=True)
        with open(alias_path, "w") as f:
            f.write(script_content)
        os.chmod(alias_path, 0o755)
        if not quiet:
            print(f"Installed executable for {repo_identifier} at {alias_path}")

        alias_name = repo.get("alias")
        if alias_name:
            alias_link_path = os.path.join(bin_dir, alias_name)
            try:
                if os.path.exists(alias_link_path) or os.path.islink(alias_link_path):
                    os.remove(alias_link_path)
                os.symlink(alias_path, alias_link_path)
                if not quiet:
                    print(f"Created alias '{alias_name}' pointing to {repo_identifier}")
            except Exception as e:
                if not quiet:
                    print(f"Error creating alias '{alias_name}': {e}")