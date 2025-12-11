import sys
import os

def get_repo_dir(repositories_base_dir:str,repo:{})->str:
    try:
        return os.path.join(repositories_base_dir, repo.get("provider"), repo.get("account"), repo.get("repository"))
    except TypeError as e:
        if repositories_base_dir:
            print(f"Error: {e} \nThe repository {repo} seems not correct configured.\nPlease configure it correct.")
            for key in ["provider","account","repository"]:
                if not repo.get(key,False):
                   print(f"Key '{key}' is missing.")
        else:
            print(f"Error: {e} \nThe base {base} seems not correct configured.\nPlease configure it correct.")
        sys.exit(3)