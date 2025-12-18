import yaml
import os


def save_user_config(user_config, USER_CONFIG_PATH: str):
    """Save the user configuration to USER_CONFIG_PATH."""
    os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
    with open(USER_CONFIG_PATH, "w") as f:
        yaml.dump(user_config, f)
    print(f"User configuration updated in {USER_CONFIG_PATH}.")
