import os

def list_repositories(all_repos, repositories_base_dir, bin_dir, search_filter="", status_filter=""):
    """
    List all repositories with their attributes and status information.

    Parameters:
      all_repos (list): List of repository configurations.
      repositories_base_dir (str): The base directory where repositories are located.
      bin_dir (str): The directory where executable wrappers are stored.
      search_filter (str): Filter for repository attributes (case insensitive).
      status_filter (str): Filter for computed status info (case insensitive).

    For each repository, the identifier is printed in bold, the description (if available)
    in italic, then all other attributes and computed status are printed.
    If the repository is installed, a hint is displayed under the attributes.
    Repositories are filtered out if either the search_filter is not found in any attribute or
    if the status_filter is not found in the computed status string.
    """
    search_filter = search_filter.lower() if search_filter else ""
    status_filter = status_filter.lower() if status_filter else ""
    
    # Define status colors using colors not used for other attributes:
    # Avoid red (for ignore), blue (for homepage) and yellow (for verified).
    status_colors = {
        "Installed": "\033[1;32m",       # Green
        "Not Installed": "\033[1;35m",   # Magenta
        "Cloned": "\033[1;36m",          # Cyan
        "Clonable": "\033[1;37m",        # White
        "Ignored": "\033[38;5;208m",     # Orange (extended)
        "Active": "\033[38;5;129m",      # Light Purple (extended)
        "Installable": "\033[38;5;82m"   # Light Green (extended)
    }
    
    for repo in all_repos:
        # Combine all attribute values into one string for filtering.
        repo_text = " ".join(str(v) for v in repo.values()).lower()
        if search_filter and search_filter not in repo_text:
            continue

        # Compute status information for the repository.
        identifier = get_repo_identifier(repo, all_repos)
        executable_path = os.path.join(bin_dir, identifier)
        repo_dir = get_repo_dir(repositories_base_dir, repo)
        status_list = []
        
        # Check if the executable exists (Installed).
        if os.path.exists(executable_path):
            status_list.append("Installed")
        else:
            status_list.append("Not Installed")
        # Check if the repository directory exists (Cloned).
        if os.path.exists(repo_dir):
            status_list.append("Cloned")
        else:
            status_list.append("Clonable")
        # Mark ignored repositories.
        if repo.get("ignore", False):
            status_list.append("Ignored")
        else:
            status_list.append("Active")
        # Define installable as cloned but not installed.
        if os.path.exists(repo_dir) and not os.path.exists(executable_path):
            status_list.append("Installable")
        
        # Build a colored status string.
        colored_statuses = [f"{status_colors.get(s, '')}{s}\033[0m" for s in status_list]
        status_str = ", ".join(colored_statuses)
        
        # If a status_filter is provided, only display repos whose status contains the filter.
        if status_filter and status_filter not in status_str.lower():
            continue

        # Display repository details:
        # Print the identifier in bold.
        print(f"\033[1m{identifier}\033[0m")
        # Print the description in italic if it exists.
        description = repo.get("description")
        if description:
            print(f"\n\033[3m{description}\033[0m")
        print("\nAttributes:")
        # Loop through all attributes.
        for key, value in repo.items():
            formatted_value = str(value)
            # Special formatting for "verified" attribute (yellow).
            if key == "verified" and value:
                formatted_value = f"\033[1;33m{value}\033[0m"
            # Special formatting for "ignore" flag (red if True).
            if key == "ignore" and value:
                formatted_value = f"\033[1;31m{value}\033[0m"
            if key == "description":
                continue
            # Highlight homepage in blue.
            if key.lower() == "homepage" and value:
                formatted_value = f"\033[1;34m{value}\033[0m"
            print(f"  {key}: {formatted_value}")
        # Always display the computed status.
        print(f"  Status: {status_str}")
        # If the repository is installed, display a hint for more info.
        if os.path.exists(executable_path):
            print(f"\nMore information and help: \033[1;4mpkgmgr {identifier} --help\033[0m\n")
        print("-" * 40)