#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import h3_prompt_projects
from h3_prompt_contract import validate_prompt


def _targets(path: Path, duration_override: float | None) -> list[tuple[str, str, float | None]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() != ".md" or "## Machine Payload" not in text:
        return [(path.name, text, duration_override)]
    payload: dict[str, Any] = h3_prompt_projects.extract_payload(text)
    duration = duration_override
    if duration is None:
        duration = float(payload.get("duration_seconds") or 0) or None
    variants = payload.get("prompt_variants") or []
    if variants:
        return [
            (
                str(row.get("variant_id") or index),
                str(row.get("video_prompt") or ""),
                duration,
            )
            for index, row in enumerate(variants, start=1)
        ]
    return [("video_prompt", str(payload.get("video_prompt") or ""), duration)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate canonical MiniMax H3 full-reference prompts."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--duration", type=float)
    args = parser.parse_args()

    reports = []
    for label, prompt, duration in _targets(args.input, args.duration):
        report = validate_prompt(prompt, duration_seconds=duration)
        reports.append({"label": label, **report.as_dict()})
    result = {
        "input": str(args.input),
        "valid": all(row["valid"] for row in reports),
        "reports": reports,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
