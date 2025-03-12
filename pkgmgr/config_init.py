import subprocess
import os

def config_init(user_config, defaults_config, bin_dir,USER_CONFIG_PATH:str):
    """
    Scan the base directory (defaults_config["base"]) for repositories.
    The folder structure is assumed to be:
      {base}/{provider}/{account}/{repository}
    For each repository found, automatically determine:
      - provider, account, repository from folder names.
      - verified: the latest commit (via 'git log -1 --format=%H').
      - alias: generated from the repository name using generate_alias().
    Repositories already defined in defaults_config["repositories"] or user_config["repositories"] are skipped.
    """
    repositories_base_dir = os.path.expanduser(defaults_config["directories"]["repositories"])
    if not os.path.isdir(repositories_base_dir):
        print(f"Base directory '{repositories_base_dir}' does not exist.")
        return

    default_keys = {(entry.get("provider"), entry.get("account"), entry.get("repository"))
                    for entry in defaults_config.get("repositories", [])}
    existing_keys = {(entry.get("provider"), entry.get("account"), entry.get("repository"))
                     for entry in user_config.get("repositories", [])}
    existing_aliases = {entry.get("alias") for entry in user_config.get("repositories", []) if entry.get("alias")}

    new_entries = []
    for provider in os.listdir(repositories_base_dir):
        provider_path = os.path.join(repositories_base_dir, provider)
        if not os.path.isdir(provider_path):
            continue
        for account in os.listdir(provider_path):
            account_path = os.path.join(provider_path, account)
            if not os.path.isdir(account_path):
                continue
            for repo_name in os.listdir(account_path):
                repo_path = os.path.join(account_path, repo_name)
                if not os.path.isdir(repo_path):
                    continue
                key = (provider, account, repo_name)
                if key in default_keys or key in existing_keys:
                    continue
                try:
                    result = subprocess.run(
                        ["git", "log", "-1", "--format=%H"],
                        cwd=repo_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    verified = result.stdout.strip()
                except Exception as e:
                    verified = ""
                    print(f"Could not determine latest commit for {repo_name} ({provider}/{account}): {e}")

                entry = {
                    "provider": provider,
                    "account": account,
                    "repository": repo_name,
                    "verified": verified,
                    "ignore": True
                }
                alias = generate_alias({"repository": repo_name, "provider": provider, "account": account}, bin_dir, existing_aliases)
                entry["alias"] = alias
                existing_aliases.add(alias)
                new_entries.append(entry)
                print(f"Adding new repo entry: {entry}")

    if new_entries:
        user_config.setdefault("repositories", []).extend(new_entries)
        save_user_config(user_config,USER_CONFIG_PATH)
    else:
        print("No new repositories found.")
