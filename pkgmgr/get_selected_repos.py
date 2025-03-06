import os
import sys
from .resolve_repos import resolve_repos
from .filter_ignored import filter_ignored
from .get_repo_dir import get_repo_dir

def get_selected_repos(show_all: bool, all_repos_list, identifiers=None):
    if show_all:
        selected = all_repos_list 
    else:
        selected = resolve_repos(identifiers, all_repos_list)
    
    # If no repositories were found using the provided identifiers,
    # try to automatically select based on the current directory:
    if not selected:
        current_dir = os.getcwd()
        directory_name = os.path.basename(current_dir)
        # Pack the directory name in a list since resolve_repos expects a list.
        auto_selected = resolve_repos([directory_name], all_repos_list)
        if auto_selected:
            # Check if the path of the first auto-selected repository matches the current directory.
            if os.path.abspath(auto_selected[0].get("directory")) == os.path.abspath(current_dir):
                print(f"Repository {auto_selected[0]['repository']} has been auto-selected by path.")
                selected = auto_selected
    filtered = filter_ignored(selected)
    if not filtered:
        print("Error: No repositories had been selected.")
        sys.exit(1)
    return filtered
