from __future__ import annotations

import os
import sys
from pathlib import Path

from pkgmgr.actions.review import ReviewError, write_review
from pkgmgr.cli.context import CLIContext


def handle_review(args, ctx: CLIContext) -> None:
    try:
        path = write_review(
            cwd=os.getcwd(),
            out=args.out,
            max_file_lines=args.max_file_lines,
            base=args.base,
            notes=args.note,
        )
    except ReviewError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(2)
    print(Path(path).as_uri())
