import yaml
from pkgmgr.core.config.load import load_config


def show_config(selected_repos, user_config_path, full_config=False):
    """Display configuration for one or more repositories, or the entire merged config."""
    if full_config:
        merged = load_config(user_config_path)
        print(yaml.dump(merged, default_flow_style=False))
    else:
        for repo in selected_repos:
            identifier = (
                f"{repo.get('provider')}/{repo.get('account')}/{repo.get('repository')}"
            )
            print(f"Repository: {identifier}")
            for key, value in repo.items():
                print(f"  {key}: {value}")
            print("-" * 40)
