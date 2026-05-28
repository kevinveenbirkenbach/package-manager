from __future__ import annotations

import sys
from pathlib import Path

from pkgmgr.actions.archive import ArchivePlan, run_archive
from pkgmgr.cli.context import CLIContext


def _print_summary(
    directory: Path, readme: Path, plan: ArchivePlan, dry_run: bool
) -> None:
    print(f"[archive] Directory:              {directory}")
    print(f"[archive] README:                 {readme}")
    print(f"[archive] Files to process:       {len(plan.archived)}")
    print(f"[archive] Skipped (incomplete):   {len(plan.skipped_incomplete)}")
    print(f"[archive] New archive entries:    {len(plan.new_entries)}")
    print(f"[archive] Dry-run:                {dry_run}")


def _print_skips(plan: ArchivePlan, cwd: Path) -> None:
    if plan.skipped_incomplete:
        print(
            "[archive] SKIP: files with unchecked `- [ ]` items "
            "(not archived, not deleted):"
        )
        for path, count in plan.skipped_incomplete:
            suffix = "s" if count != 1 else ""
            rel = _rel_or_abs(path, cwd)
            print(f"  - {rel} ({count} unchecked item{suffix})")
    if plan.skipped_without_h1:
        print("[archive] WARN: skipped files without an H1 heading:")
        for path in plan.skipped_without_h1:
            print(f"  - {_rel_or_abs(path, cwd)}")


def _print_actions(plan: ArchivePlan, cwd: Path, dry_run: bool) -> None:
    verb = "would archive" if dry_run else "archived"
    rm_verb = "would delete" if dry_run else "deleted"
    for path, title in plan.archived:
        rel = _rel_or_abs(path, cwd)
        print(f"[archive] {verb}: {rel}  ->  '{title}'")
        if not dry_run:
            print(f"[archive] {rm_verb}: {rel}")


def _rel_or_abs(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd).as_posix()
    except ValueError:
        return path.as_posix()


def handle_archive(args, _ctx: CLIContext) -> None:
    directory = Path(args.directory).resolve()
    readme = (
        Path(args.readme).resolve()
        if args.readme
        else (directory / "README.md").resolve()
    )

    try:
        plan = run_archive(
            directory=directory,
            readme_path=readme,
            dry_run=args.dry_run,
            include_template=args.include_template,
        )
    except FileNotFoundError as exc:
        print(f"[archive] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    cwd = Path.cwd().resolve()
    _print_summary(directory, readme, plan, args.dry_run)
    _print_skips(plan, cwd)
    _print_actions(plan, cwd, args.dry_run)
