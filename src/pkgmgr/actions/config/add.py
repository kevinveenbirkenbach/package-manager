import yaml
import os
from pkgmgr.core.config.save import save_user_config


def interactive_add(config, USER_CONFIG_PATH: str):
    """Interactively prompt the user to add a new repository entry to the user config."""
    print("Adding a new repository configuration entry.")
    new_entry = {}
    new_entry["provider"] = input("Provider (e.g., github.com): ").strip()
    new_entry["account"] = input("Account (e.g., yourusername): ").strip()
    new_entry["repository"] = input("Repository name (e.g., mytool): ").strip()
    new_entry["command"] = input(
        "Command (optional, leave blank to auto-detect): "
    ).strip()
    new_entry["description"] = input("Description (optional): ").strip()
    new_entry["replacement"] = input("Replacement (optional): ").strip()
    new_entry["alias"] = input("Alias (optional): ").strip()
    # Allow the user to mark this entry as ignored.
    ignore_val = input("Ignore this entry? (y/N): ").strip().lower()
    if ignore_val == "y":
        new_entry["ignore"] = True

    print("\nNew entry:")
    for key, value in new_entry.items():
        if value:
            print(f"{key}: {value}")
    confirm = input("Add this entry to user config? (y/N): ").strip().lower()
    if confirm == "y":
        if os.path.exists(USER_CONFIG_PATH):
            with open(USER_CONFIG_PATH, "r") as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {"repositories": []}
        user_config.setdefault("repositories", [])
        user_config["repositories"].append(new_entry)
        save_user_config(user_config, USER_CONFIG_PATH)
    else:
        print("Entry not added.")
