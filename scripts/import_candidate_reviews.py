#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluation_db


def main() -> int:
    parser = argparse.ArgumentParser(
        description="기존 후보 리뷰 JSON을 공통 모델 평가 SQLite DB로 가져옵니다."
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="video-engine 프로젝트 루트")
    parser.add_argument("--db", type=Path, help="SQLite 경로(기본: runtime/evaluation/evaluation.db)")
    args = parser.parse_args()

    root = args.root.resolve()
    db_path = args.db.resolve() if args.db else root / evaluation_db.DEFAULT_DB_PATH
    report = evaluation_db.import_from_root(root, db_path)
    print(json.dumps({"database": str(db_path), **report.as_dict()}, ensure_ascii=False, indent=2))
    return 1 if report.failed or report.conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
