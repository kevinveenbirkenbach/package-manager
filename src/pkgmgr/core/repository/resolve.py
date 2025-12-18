def resolve_repos(identifiers: [], all_repos: []):
    """
    Given a list of identifier strings, return a list of repository configs.
    The identifier can be:
      - the full identifier "provider/account/repository"
      - the repository name (if unique among all_repos)
      - the alias (if defined)
    """
    selected = []
    for ident in identifiers:
        matches = []
        for repo in all_repos:
            full_id = (
                f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
            )
            if ident == full_id:
                matches.append(repo)
            elif ident == repo.get("alias"):
                matches.append(repo)
            elif ident == repo.get("repository"):
                # Only match if repository name is unique among all_repos.
                if sum(1 for r in all_repos if r.get("repository") == ident) == 1:
                    matches.append(repo)
        if not matches:
            print(f"Identifier '{ident}' did not match any repository in config.")
        else:
            selected.extend(matches)
    return selected
