#!/usr/bin/env python3
"""Apply three Codex-authored prompts to one saved H3 revision request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import h3_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request_id")
    parser.add_argument(
        "variants_file",
        nargs="?",
        help="JSON file containing prompt_variants; defaults to the request folder's authored_variants.json",
    )
    args = parser.parse_args()
    variants_path = (
        Path(args.variants_file).expanduser().resolve()
        if args.variants_file
        else ROOT
        / "runtime/h3/prompt_revision_requests"
        / args.request_id
        / "authored_variants.json"
    )
    payload = json.loads(variants_path.read_text(encoding="utf-8"))
    variants = payload.get("prompt_variants") if isinstance(payload, dict) else payload
    result = h3_queue.apply_authored_prompt_revision(
        ROOT,
        args.request_id,
        {"prompt_variants": variants},
    )
    print(json.dumps({
        "prompt_revision_request_id": args.request_id,
        "candidate_set_id": result["candidate_set_id"],
        "clip_version": result.get("clip_version"),
        "candidate_round": result.get("candidate_round"),
        "variant_ids": [row["variant_id"] for row in result.get("prompt_variants") or []],
        "job_ids": result.get("candidate_job_ids") or [],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
