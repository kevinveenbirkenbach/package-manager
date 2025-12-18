import os
import hashlib
import re


def generate_alias(repo, bin_dir, existing_aliases):
    """
    Generate an alias for a repository based on its repository name.

    Steps:
      1. Keep only consonants from the repository name (letters from BCDFGHJKLMNPQRSTVWXYZ).
      2. Collapse consecutive identical consonants.
      3. Truncate to at most 12 characters.
      4. If that alias conflicts (already in existing_aliases or a file exists in bin_dir),
         then prefix with the first letter of provider and account.
      5. If still conflicting, append a three-character hash until the alias is unique.
    """
    repo_name = repo.get("repository")
    # Keep only consonants.
    consonants = re.sub(r"[^bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]", "", repo_name)
    # Collapse consecutive identical consonants.
    collapsed = re.sub(r"(.)\1+", r"\1", consonants)
    base_alias = collapsed[:12] if len(collapsed) > 12 else collapsed
    candidate = base_alias.lower()

    def conflict(alias):
        alias_path = os.path.join(bin_dir, alias)
        return alias in existing_aliases or os.path.exists(alias_path)

    if not conflict(candidate):
        return candidate

    prefix = (repo.get("provider", "")[0] + repo.get("account", "")[0]).lower()
    candidate2 = (prefix + candidate)[:12]
    if not conflict(candidate2):
        return candidate2

    h = hashlib.md5(repo_name.encode("utf-8")).hexdigest()[:3]
    candidate3 = (candidate2 + h)[:12]
    while conflict(candidate3):
        candidate3 += "x"
        candidate3 = candidate3[:12]
    return candidate3
