"""
pkgmgr/release.py

This module defines a 'release' function that:
  - Increments the version in pyproject.toml based on the release type (major, minor, patch)
  - Updates the CHANGELOG.md with a new release entry (including an optional message)
  - Executes Git commands to commit, tag, and push the release.
"""

import re
import subprocess
from datetime import date
import sys
import argparse

def bump_version(version_str: str, release_type: str) -> str:
    """
    Parse the version string and return the incremented version.
    
    Parameters:
      version_str: The current version in the form "X.Y.Z".
      release_type: One of "major", "minor", or "patch".
    
    Returns:
      The bumped version string.
    """
    parts = version_str.split('.')
    if len(parts) != 3:
        raise ValueError("Version format is unexpected. Expected format: X.Y.Z")
    major, minor, patch = map(int, parts)
    if release_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif release_type == "minor":
        minor += 1
        patch = 0
    elif release_type == "patch":
        patch += 1
    else:
        raise ValueError("release_type must be 'major', 'minor', or 'patch'.")
    return f"{major}.{minor}.{patch}"

def update_pyproject_version(pyproject_path: str, new_version: str):
    """
    Update the version in pyproject.toml with the new version.
    
    Parameters:
      pyproject_path: Path to the pyproject.toml file.
      new_version: The new version string.
    """
    with open(pyproject_path, "r") as f:
        content = f.read()
    # Search for the version string in the format: version = "X.Y.Z"
    new_content, count = re.subn(r'(version\s*=\s*")([\d\.]+)(")', r'\1' + new_version + r'\3', content)
    if count == 0:
        print("Could not find version line in pyproject.toml")
        sys.exit(1)
    with open(pyproject_path, "w") as f:
        f.write(new_content)
    print(f"Updated pyproject.toml version to {new_version}")

def update_changelog(changelog_path: str, new_version: str, message: str = None):
    """
    Prepend a new release section to CHANGELOG.md with the new version,
    today’s date and an optional release message.
    
    Parameters:
      changelog_path: Path to the CHANGELOG.md file.
      new_version: The new version string.
      message: An optional release message.
    """
    release_date = date.today().isoformat()
    header = f"## [{new_version}] - {release_date}\n"
    if message:
        header += f"{message}\n"
    header += "\n"
    try:
        with open(changelog_path, "r") as f:
            changelog = f.read()
    except FileNotFoundError:
        changelog = ""
    new_changelog = header + changelog
    with open(changelog_path, "w") as f:
        f.write(new_changelog)
    print(f"Updated CHANGELOG.md with version {new_version}")

def run_git_command(cmd: str):
    """
    Execute a shell command via Git and exit if it fails.
    
    Parameters:
      cmd: The shell command to run.
    """
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(result.returncode)

def release(pyproject_path: str = "pyproject.toml",
            changelog_path: str = "CHANGELOG.md",
            release_type: str = "patch",
            message: str = None):
    """
    Perform a release by incrementing the version in pyproject.toml,
    updating CHANGELOG.md with the release version and message, then executing
    the Git commands to commit, tag, and push the changes.
    
    Parameters:
      pyproject_path: The path to pyproject.toml.
      changelog_path: The path to CHANGELOG.md.
      release_type: A string indicating the type of release ("major", "minor", "patch").
      message: An optional release message to include in CHANGELOG.md and Git tag.
    """
    try:
        with open(pyproject_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"{pyproject_path} not found.")
        sys.exit(1)
        
    match = re.search(r'version\s*=\s*"([\d\.]+)"', content)
    if not match:
        print("Could not find version in pyproject.toml")
        sys.exit(1)
    current_version = match.group(1)
    new_version = bump_version(current_version, release_type)
    
    # Update files.
    update_pyproject_version(pyproject_path, new_version)
    update_changelog(changelog_path, new_version, message)
    
    # Execute Git commands.
    commit_msg = f"Release version {new_version}"
    run_git_command(f'git commit -am "{commit_msg}"')
    run_git_command(f'git tag -a v{new_version} -m "{commit_msg}"')
    run_git_command("git push origin main")
    run_git_command("git push origin --tags")
    print(f"Release {new_version} completed successfully.")

# Allow the script to be used as a CLI tool.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform a release by updating version and changelog, then executing Git commands."
    )
    parser.add_argument("release_type", choices=["major", "minor", "patch"],
                        help="Type of release increment (major, minor, patch).")
    parser.add_argument("-m", "--message", help="Optional release message for changelog and tag.", default=None)
    
    args = parser.parse_args()
    release(release_type=args.release_type, message=args.message)