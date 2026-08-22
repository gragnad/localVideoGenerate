#!/usr/bin/env python3
from __future__ import annotations

"""Audit the separated EP01 V3 dialogue lock and rendered A/D/E prompts."""

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "projects" / "RaisingaDragonSeason01" / "rebuild_v2"
LOCK_PATH = SOURCE_DIR / "EP01_DIALOGUE_PERFORMANCE_LOCK_V3.json"
SPEC_PATH = SOURCE_DIR / "EP01_H3_R2V_STORYBOARD_ADE_V3_SPEC.json"
PROJECT_DIR = ROOT / "prompt_projects" / "RaisingaDragonSeason01_EP01_H3_R2V_STORYBOARD_ADE_V3"
MANIFEST_PATH = PROJECT_DIR / "manifest.json"
DIALOGUE_RE = re.compile(r"<d>\[Korean\]\s*(.*?)</d>", re.DOTALL)
SPEAKER_RE = re.compile(
    r"<Subject (\d+)> \(S1\)[^<]*<d>\[Korean\]\s*(.*?)</d>",
    re.DOTALL,
)


def _machine_payload(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])


def _shot_text(prompt: str, shot: int) -> str:
    start = prompt.index(f"\n[Shot {shot}]") + 1
    if shot < 4:
        end = prompt.index(f"\n[Shot {shot + 1}]", start)
    else:
        end = prompt.index("\noverall_soundscape:", start)
    return prompt[start:end]


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    dialogue = lock["dialogue_by_clip"]
    spec_clips = {clip["clip_id"]: clip for clip in spec["clips"]}
    paths = sorted(PROJECT_DIR.glob("EP01-S*/EP01-*.md"))
    failures: list[str] = []
    max_prompt = (0, "", "")
    total_tags = 0

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    check(len(spec_clips) == lock["expected_clip_count"] == 42, "clip count is not 42")
    check(len(dialogue) == lock["expected_dialogue_clip_count"] == 20, "dialogue clip count is not 20")
    check(sum(map(len, dialogue.values())) == lock["expected_line_count"] == 42, "dialogue line count is not 42")
    check(len(paths) == 42, "rendered markdown count is not 42")
    check(spec.get("dialogue_lock_version") == lock["version"], "spec dialogue lock version mismatch")
    check(LOCK_PATH.name in spec.get("canonical_source_lineage", []), "dialogue lock missing from spec lineage")
    check(LOCK_PATH.name in manifest.get("canonical_source_lineage", []), "dialogue lock missing from manifest lineage")
    check(manifest.get("dialogue_lock_version") == lock["version"], "manifest dialogue lock version mismatch")
    check(manifest.get("dialogue_clip_count") == 20, "manifest dialogue clip count mismatch")
    check(manifest.get("dialogue_line_count") == 42, "manifest dialogue line count mismatch")
    check(manifest.get("generation_blocked") is False, "EP01 project is unexpectedly generation-blocked")
    check(manifest.get("queue_registration_performed") is False, "queue side effect detected")
    check(manifest.get("video_generation_performed") is False, "video generation side effect detected")

    for path in paths:
        payload = _machine_payload(path)
        clip_id = payload["clip_id"]
        clip = spec_clips[clip_id]
        rows = dialogue.get(clip_id, [])
        expected_lines = [str(row["line"]).strip() for row in rows]
        expected_speakers = [clip["references"].index(row["speaker"]) + 1 for row in rows]
        check(payload.get("required_dialogue") == expected_lines, f"{clip_id}: payload required_dialogue mismatch")
        check(payload.get("dialogue_lock_version") == lock["version"], f"{clip_id}: payload dialogue lock mismatch")
        variants = payload.get("prompt_variants") or []
        check([row.get("variant_id") for row in variants] == ["A", "D", "E"], f"{clip_id}: A/D/E variants missing")
        for variant in variants:
            variant_id = variant["variant_id"]
            prompt = variant["video_prompt"]
            prompt_size = len(prompt)
            max_prompt = max(max_prompt, (prompt_size, clip_id, variant_id))
            actual_lines = [line.strip() for line in DIALOGUE_RE.findall(prompt)]
            speaker_rows = [(int(subject), line.strip()) for subject, line in SPEAKER_RE.findall(prompt)]
            total_tags += len(actual_lines)
            check(actual_lines == expected_lines, f"{clip_id}/{variant_id}: dialogue order or text mismatch")
            check([subject for subject, _line in speaker_rows] == expected_speakers, f"{clip_id}/{variant_id}: speaker mismatch")
            check([line for _subject, line in speaker_rows] == expected_lines, f"{clip_id}/{variant_id}: speaker markup missing")
            for shot in range(1, 5):
                expected_in_shot = [
                    str(row["line"]).strip() for row in rows if int(row["shot"]) == shot
                ]
                actual_in_shot = [line.strip() for line in DIALOGUE_RE.findall(_shot_text(prompt, shot))]
                check(actual_in_shot == expected_in_shot, f"{clip_id}/{variant_id}/Shot {shot}: placement mismatch")
            if rows:
                check("Render each tagged Korean line exactly once in order" in prompt, f"{clip_id}/{variant_id}: dialogue sound rule missing")
            else:
                check("No intelligible dialogue is authorized" in prompt, f"{clip_id}/{variant_id}: silence rule missing")

    check(total_tags == 42 * 3 == 126, f"dialogue tag total mismatch: {total_tags}")
    check(max_prompt[0] <= 7000, f"prompt exceeds 7000 characters: {max_prompt}")
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS",
        "checks": 13,
        "clip_count": 42,
        "dialogue_clip_count": 20,
        "locked_line_count": 42,
        "rendered_dialogue_tags": total_tags,
        "max_prompt_characters": max_prompt[0],
        "max_prompt_clip": max_prompt[1],
        "queue_or_video_side_effects": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
