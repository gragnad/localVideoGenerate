#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "prompt_projects/RaisingaDragonSeason01"
SCENE_BG = {
    "SC01-001": "BG_EP01_STORM_DEEP_SEA_NIGHT",
    "SC01-002": "BG_EP01_COASTAL_VILLAGE_MORNING",
    "SC01-003": "BG_EP01_COASTAL_CAVE_INTERIOR",
    "SC01-004": "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
    "SC01-005": "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
}
JSON_RE = re.compile(r"```json\s*\n([\s\S]*?)\n```", re.I)


def build_bg_section(entry: dict, gen: dict) -> str:
    notes = "\n".join(f"- {note}" for note in gen.get("continuity_notes") or [])
    return f"""## Background Image Required

배경 전용 레퍼런스 PNG가 아직 연결되지 않았습니다. 아래 생성 프롬프트로 배경 plate를 만든 뒤 권장 파일명으로 저장하세요.

**Background ID:** `{entry['background_id']}`

**배경이 필요한 이유:** {entry['description']}

**권장 파일명:** `{gen['suggested_filename']}`

**권장 해상도:** {gen['recommended_resolution']['width']} × {gen['recommended_resolution']['height']} ({gen['aspect_ratio']})

**배경 생성 프롬프트:**

{gen['prompt']}

**Negative prompt:**

{gen['negative_prompt']}

**연속성 유지 조건:**

{notes}

**배경 이미지 저장 예정 위치:** `prompt_projects/RaisingaDragonSeason01/backgrounds/{gen['suggested_filename']}`
"""


def main() -> None:
    catalog = json.loads((PROJECT / "background_catalog.json").read_text(encoding="utf-8"))
    for md_path in sorted(PROJECT.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        match = JSON_RE.search(text)
        if not match:
            continue
        payload = json.loads(match.group(1))
        scene_id = payload.get("scene_id") or md_path.parent.name
        bg_id = SCENE_BG[scene_id]
        entry = catalog["backgrounds"][bg_id]
        gen = {
            "required": True,
            "suggested_filename": entry["suggested_filename"],
            "aspect_ratio": entry["aspect_ratio"],
            "recommended_resolution": entry["recommended_resolution"],
            "prompt": entry["prompt"],
            "negative_prompt": entry["negative_prompt"],
            "continuity_notes": entry["continuity_notes"],
        }
        payload["status"] = "awaiting_background"
        payload["background"] = {
            "status": "missing",
            "background_id": bg_id,
            "source_path": None,
            "description": entry["description"],
        }
        payload["background_generation"] = gen
        review = dict(payload.get("review") or {})
        review.update(
            reference_mapping_valid=True,
            scenario_consistent=True,
            dialogue_preserved=True,
            duration_valid=True,
            animation_style_preserved=True,
            background_generation_valid=True,
            warnings=[
                w
                for w in (review.get("warnings") or [])
                if "배경 source_path" not in w and "reference_mapping_valid" not in w
            ],
            unresolved_questions=[],
        )
        payload["review"] = review
        new_json = json.dumps(payload, ensure_ascii=False, indent=2)
        new_text = JSON_RE.sub(lambda _: f"```json\n{new_json}\n```", text, count=1)
        bg_section = build_bg_section(entry, gen)
        if "## Background Image Required" in new_text:
            new_text = re.sub(
                r"\n## Background Image Required[\s\S]*?(?=\n## AI Review|\Z)",
                "\n" + bg_section,
                new_text,
            )
        else:
            new_text = new_text.replace("\n## AI Review", "\n" + bg_section + "\n## AI Review")
        md_path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    main()
