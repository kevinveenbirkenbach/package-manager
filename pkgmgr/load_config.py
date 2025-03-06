import sys
import yaml
import os
from .get_repo_dir import get_repo_dir
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../","config", "defaults.yaml")

def load_config(user_config_path):
    """Load configuration from defaults and merge in user config if present."""
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print(f"Default configuration file '{DEFAULT_CONFIG_PATH}' not found.")
        sys.exit(1)
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    if "directories" not in config or "repositories" not in config:
        print("Default config file must contain 'directories' and 'repositories' keys.")
        sys.exit(1)
    if os.path.exists(user_config_path):
        with open(user_config_path, 'r') as f:
            user_config = yaml.safe_load(f)
        if user_config:
            if "directories" in user_config:
                config["directories"] = user_config["directories"]
            if "repositories" in user_config:
                config["repositories"].extend(user_config["repositories"])
    for repository in config["repositories"]:
        # You can overwritte the directory path in the config
        if "directory" not in repository:
            directory = get_repo_dir(config["directories"]["repositories"], repository)
            repository["directory"] = os.path.expanduser(directory)
    return config