#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h3_prompt_project_builder import build_project


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one new MiniMax H3 R2V project from structured JSON."
    )
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    result = build_project(ROOT, args.spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
