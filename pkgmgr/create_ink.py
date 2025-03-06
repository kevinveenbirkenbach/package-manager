import os
from pkgmgr.get_repo_identifier import get_repo_identifier
from pkgmgr.get_repo_dir import get_repo_dir

def create_ink(repo, repositories_base_dir, bin_dir, all_repos, quiet=False, preview=False):
    """
    Creates a symbolic link for the repository's command.
    
    Instead of creating an executable wrapper, this function creates a symlink
    that points to the command file within the repository (e.g., main.sh or main.py).
    """
    repo_identifier = get_repo_identifier(repo, all_repos)
    repo_dir = get_repo_dir(repositories_base_dir, repo)
    command = repo.get("command")
    if not command:
        # Automatically detect main.sh or main.py:
        main_sh = os.path.join(repo_dir, "main.sh")
        main_py = os.path.join(repo_dir, "main.py")
        if os.path.exists(main_sh):
            command = main_sh
        elif os.path.exists(main_py):
            command = main_py
        else:
            if not quiet:
                print(f"No command defined and neither main.sh nor main.py found in {repo_dir}. Skipping link creation.")
            return

    link_path = os.path.join(bin_dir, repo_identifier)
    if preview:
        print(f"[Preview] Would create symlink '{link_path}' pointing to '{command}'.")
    else:
        os.makedirs(bin_dir, exist_ok=True)
        if os.path.exists(link_path) or os.path.islink(link_path):
            os.remove(link_path)
        os.symlink(command, link_path)
        if not quiet:
            print(f"Symlink for {repo_identifier} created at {link_path}.")

        alias_name = repo.get("alias")
        if alias_name:
            alias_link_path = os.path.join(bin_dir, alias_name)
            try:
                if os.path.exists(alias_link_path) or os.path.islink(alias_link_path):
                    os.remove(alias_link_path)
                os.symlink(link_path, alias_link_path)
                if not quiet:
                    print(f"Alias '{alias_name}' has been set to point to {repo_identifier}.")
            except Exception as e:
                if not quiet:
                    print(f"Error creating alias '{alias_name}': {e}")
