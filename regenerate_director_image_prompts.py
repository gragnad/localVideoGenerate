from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import director_prompt_projects as projects


PROJECT_ID = "RaisingaDragonSeason01"
STYLE_PREFIX = (
    "Cinematic keyframe from a premium stylized 3D animated feature, "
    "widescreen 16:9."
)
INTERNAL_ID_RE = re.compile(r"\s*\((?:CHAR|ENTITY|PROP)_[A-Z0-9_]+\)")
OLD_PREFIX_RE = re.compile(
    r"^High-quality stylized feature-film animation still,\s*"
    r"16:9,\s*1280x704\.\s*",
    re.IGNORECASE,
)
REFERENCE_PATHS = {
    "Lua": "RaisingaDragonSeason01/Lua.png",
    "Village Child 1": "RaisingaDragonSeason01/villageChild01.png",
    "Village Child 2": "RaisingaDragonSeason01/village_child_2.png",
    "Old Fisherman": "RaisingaDragonSeason01/old_fisherman.png",
    "Young Mir": "RaisingaDragonSeason01/YoungMir.png",
    "Black Tide": "RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL .png",
    "Black Jellyfish": "RaisingaDragonSeason01/BLACK JELLYFISH .png",
    "spear": "RaisingaDragonSeason01/spear.png",
}


def regenerate_prompt(prompt: str) -> str:
    original = str(prompt or "").strip()
    if original.startswith(STYLE_PREFIX):
        body = original[len(STYLE_PREFIX) :].strip()
    else:
        body = OLD_PREFIX_RE.sub("", original)
    body = INTERNAL_ID_RE.sub("", body)
    body = re.sub(r"\bstatic\s+", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s+—\s+", " — ", body)
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"\bExactly one small dragon;\s*", "", body)
    body = re.sub(r"\bOne dragon only[.;]\s*", "", body)
    body = re.sub(
        r"\bfully dragon anatomy,\s*no human features[.;]?\s*",
        "",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(r"\s+([,.;:])", r"\1", body)
    body = body.strip(" .")
    if body:
        body = body[0].upper() + body[1:]
    return f"{STYLE_PREFIX} {body}."


def reference_paths_for(prompt: str) -> list[str]:
    return [
        path
        for name, path in REFERENCE_PATHS.items()
        if name.lower() in prompt.lower()
    ]


def audit_prompt(prompt: str) -> list[str]:
    errors: list[str] = []
    checks = {
        "내부 ID": r"\b(?:CHAR|ENTITY|PROP)_[A-Z0-9_]+\b",
        "static 반복어": r"\bstatic\b",
        "Picture 번호": r"\bPicture\s+\d+\b",
        "메타 지시": r"Specify screen positions",
        "카메라 이동": r"camera\s+(?:moves|tilts|drifts|continues)",
    }
    for label, pattern in checks.items():
        if re.search(pattern, prompt, re.IGNORECASE):
            errors.append(label)
    if not prompt.startswith(STYLE_PREFIX):
        errors.append("스타일 접두문 누락")
    return errors


def rewrite_project(root: Path, *, apply: bool) -> dict[str, Any]:
    project_dir = root / projects.DIRECTOR_PROMPT_PROJECTS_DIR / PROJECT_ID
    changed_files = 0
    segment_count = 0
    audit_errors: list[str] = []
    previews: list[dict[str, str]] = []
    for markdown_path in sorted(project_dir.rglob("*.md")):
        markdown = markdown_path.read_text(encoding="utf-8")
        payload = projects.extract_machine_payload(markdown)
        changed = False
        for segment in payload.get("segments") or []:
            image = dict(segment.get("scene_image") or {})
            before = str(image.get("prompt") or "")
            after = regenerate_prompt(before)
            before_references = list(image.get("reference_paths") or [])
            after_references = reference_paths_for(after)
            image["prompt"] = after
            image["prompt_version"] = "cinematic_keyframe_v3"
            image["reference_paths"] = after_references
            segment["scene_image"] = image
            segment_count += 1
            if before != after or before_references != after_references:
                changed = True
                if len(previews) < 5:
                    previews.append(
                        {
                            "clip_id": str(payload.get("clip_id") or ""),
                            "segment_id": str(segment.get("segment_id") or ""),
                            "before": before,
                            "after": after,
                        }
                    )
            issues = audit_prompt(after)
            if issues:
                audit_errors.append(
                    f"{payload.get('clip_id')}/{segment.get('segment_id')}: "
                    + ", ".join(issues)
                )
        review = dict(payload.get("prompt_review") or {})
        review["image_prompts_valid"] = not audit_errors
        notes = [
            str(note)
            for note in review.get("review_notes") or []
            if "cinematic_keyframe_v3" not in str(note)
        ]
        notes.append(
            "scene_image.prompt regenerated as cinematic_keyframe_v3; "
            "internal IDs and static-shot boilerplate removed."
        )
        review["review_notes"] = notes
        payload["prompt_review"] = review
        if changed:
            changed_files += 1
            if apply:
                replacement = "```json\n" + json.dumps(
                    payload, ensure_ascii=False, indent=2
                ) + "\n```"
                updated = projects.JSON_BLOCK_RE.sub(
                    lambda _match: replacement, markdown, count=1
                )
                temporary = markdown_path.with_name(
                    f".{markdown_path.name}.{os.getpid()}.tmp"
                )
                temporary.write_text(updated, encoding="utf-8")
                temporary.replace(markdown_path)
    return {
        "apply": apply,
        "changed_files": changed_files,
        "segments": segment_count,
        "audit_errors": audit_errors,
        "previews": previews,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            rewrite_project(args.root, apply=args.apply),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
