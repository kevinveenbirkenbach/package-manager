from __future__ import annotations

import sys

from pkgmgr.actions.code_scanning import CodeScanningError, download_code_scanning
from pkgmgr.cli.context import CLIContext


def handle_code_scanning(args, ctx: CLIContext) -> None:
    try:
        result = download_code_scanning(
            repo=getattr(args, "repo", None),
            output_dir=getattr(args, "output", None),
            state=getattr(args, "state", None),
        )
    except CodeScanningError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[code-scanning] Repository: {result.repo}")
    print(f"[code-scanning] Alerts:     {result.alert_count}")
    print(f"[code-scanning] Output:     {result.output_dir}")
    for path in result.files:
        print(f"  - {path}")
