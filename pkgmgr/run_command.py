import sys
import subprocess
import os

def run_command(command, cwd=None, preview=False):
    """Run a shell command in a given directory, or print it in preview mode.
    
    If the command fails, exit the program with the command's exit code.
    """
    current_dir = cwd or os.getcwd()
    if preview:
        print(f"[Preview] In '{current_dir}': {command}")
    else:
        print(f"Running in '{current_dir}': {command}")
        result = subprocess.run(command, cwd=cwd, shell=True, check=False)
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}. Exiting.")
            sys.exit(result.returncode)