import sys
from .resolve_repos import resolve_repos
from .filter_ignored import filter_ignored

def get_selected_repos(show_all:bool,all_repos_list,identifiers=None):
    if show_all:
        selected = all_repos_list 
    else:
        selected = resolve_repos(identifiers, all_repos_list)
    filtered = filter_ignored(selected)
    if not selected:
        print("Error: No repositories had been selected.")
        sys.exit(1)
    return filtered