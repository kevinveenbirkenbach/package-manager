def filter_ignored(repos):
    """Filter out repositories that have 'ignore' set to True."""
    return [r for r in repos if not r.get("ignore", False)]
