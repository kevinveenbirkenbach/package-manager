from __future__ import annotations

from typing import List, Tuple

from pkgmgr.core.git import run_git, GitError

from .context import build_context
from .git_remote import determine_primary_remote_url, ensure_origin_remote
from .types import Repository


def _setup_local_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    """
    Ensure local Git state is sane (currently: 'origin' remote).
    """
    ctx = build_context(repo, repositories_base_dir, all_repos)

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:LOCAL] {ctx.identifier}")
    print(f"[MIRROR SETUP:LOCAL] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    ensure_origin_remote(repo, ctx, preview=preview)
    print()


def _probe_mirror(url: str, repo_dir: str) -> Tuple[bool, str]:
    """
    Probe a remote mirror by running `git ls-remote <url>`.

    Returns:
      (True, "") on success,
      (False, error_message) on failure.

    Wichtig:
      - Wir werten ausschließlich den Exit-Code aus.
      - STDERR kann Hinweise/Warnings enthalten und ist NICHT automatisch ein Fehler.
    """
    try:
        # Wir ignorieren stdout komplett; wichtig ist nur, dass der Befehl ohne
        # GitError (also Exit-Code 0) durchläuft.
        run_git(["ls-remote", url], cwd=repo_dir)
        return True, ""
    except GitError as exc:
        return False, str(exc)


def _setup_remote_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    """
    Remote-side setup / validation.

    Aktuell werden nur **nicht-destruktive Checks** gemacht:

      - Für jeden Mirror (aus config + MIRRORS-Datei, file gewinnt):
          * `git ls-remote <url>` wird ausgeführt.
          * Bei Exit-Code 0 → [OK]
          * Bei Fehler → [WARN] + Details aus der GitError-Exception

    Es werden **keine** Provider-APIs aufgerufen und keine Repos angelegt.
    """
    ctx = build_context(repo, repositories_base_dir, all_repos)
    resolved_m = ctx.resolved_mirrors

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    if not resolved_m:
        # Optional: Fallback auf eine heuristisch bestimmte URL, falls wir
        # irgendwann "automatisch anlegen" implementieren wollen.
        primary_url = determine_primary_remote_url(repo, resolved_m)
        if not primary_url:
            print(
                "[INFO] No mirrors configured (config or MIRRORS file), and no "
                "primary URL could be derived from provider/account/repository."
            )
            print()
            return

        ok, error_message = _probe_mirror(primary_url, ctx.repo_dir)
        if ok:
            print(f"[OK]   Remote mirror (primary) is reachable: {primary_url}")
        else:
            print("[WARN] Primary remote URL is NOT reachable:")
            print(f"       {primary_url}")
            if error_message:
                print("       Details:")
                for line in error_message.splitlines():
                    print(f"         {line}")

        print()
        print(
            "[INFO] Remote checks are non-destructive and only use `git ls-remote` "
            "to probe mirror URLs."
        )
        print()
        return

    # Normaler Fall: wir haben benannte Mirrors aus config/MIRRORS
    for name, url in sorted(resolved_m.items()):
        ok, error_message = _probe_mirror(url, ctx.repo_dir)
        if ok:
            print(f"[OK]   Remote mirror '{name}' is reachable: {url}")
        else:
            print(f"[WARN] Remote mirror '{name}' is NOT reachable:")
            print(f"       {url}")
            if error_message:
                print("       Details:")
                for line in error_message.splitlines():
                    print(f"         {line}")

    print()
    print(
        "[INFO] Remote checks are non-destructive and only use `git ls-remote` "
        "to probe mirror URLs."
    )
    print()


def setup_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool = False,
    local: bool = True,
    remote: bool = True,
) -> None:
    """
    Setup mirrors for the selected repositories.

    local:
      - Configure local Git remotes (currently: ensure 'origin' is present and
        points to a reasonable URL).

    remote:
      - Non-destructive remote checks using `git ls-remote` for each mirror URL.
        Es werden keine Repositories auf dem Provider angelegt.
    """
    for repo in selected_repos:
        if local:
            _setup_local_mirrors_for_repo(
                repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
            )

        if remote:
            _setup_remote_mirrors_for_repo(
                repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
            )
