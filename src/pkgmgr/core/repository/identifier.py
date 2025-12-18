def get_repo_identifier(repo, all_repos):
    """
    Return a unique identifier for the repository.
    If the repository name is unique among all_repos, return repository name;
    otherwise, return 'provider/account/repository'.
    """
    repo_name = repo.get("repository")
    count = sum(1 for r in all_repos if r.get("repository") == repo_name)
    if count == 1:
        return repo_name
    else:
        return f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
