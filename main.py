#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure local src/ overrides installed package
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.is_dir():
    sys.path.insert(0, str(SRC))

from pkgmgr.cli import main

if __name__ == "__main__":
    main()
