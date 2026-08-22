from __future__ import annotations

"""Prepare immutable planning inputs for the independent EP00 V2 project."""

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ep00_reader_action_v2_project_data as data  # noqa: E402


PROJECT_ROOT = ROOT / "projects" / "RaisingaDragonSeason01" / "ep00_reader_action_v2_new"
SOURCE_PATH = PROJECT_ROOT / "EP00_READER_SCREENPLAY_ACTION_REVISION_V2.md"
SEGMENTATION_PATH = PROJECT_ROOT / "EP00_V2_PRODUCTION_SEGMENTATION_V1.json"
DIALOGUE_PATH = PROJECT_ROOT / "EP00_V2_DIALOGUE_LOCK_V1.json"
STORYBOARD_MANIFEST_PATH = PROJECT_ROOT / "EP00_V2_STORYBOARD_GENERATION_MANIFEST_V1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def storyboard_prompt(clip: dict) -> str:
    panel_lines = "\n".join(
        f"{index}. {description}"
        for index, description in enumerate(clip["panels"], start=1)
    )
    return f"""Use case: illustration-story
Asset type: production storyboard sheet for a high-detail hand-drawn 2D cel animation
Primary request: Create one clean 2x2 chronological storyboard sheet for a dark maritime fantasy action sequence.
Input images: approved young spear-fighter identity sheet for exact face, hair, clothing, and right-side scale boundaries; approved black liquid-stone humanoid identity sheet for exact anatomy and two-hand limit; approved spear sheet for exact single weapon geometry. References define identity and style only; create a new canvas.
Scene/backdrop: one submerged circular ancient stone altar chamber with carved cyan water channels, shallow floor water, dark wet masonry, and no unrelated location.
Composition/framing: one 16:9 sheet divided into four equal 16:9 panels with thin neutral dividers. Read top-left, top-right, bottom-left, bottom-right. Each panel is a different full-screen Shot starting state.
Panel states:
{panel_lines}
Style/medium: original high-detail hand-drawn 2D cel animation, grounded anatomy, crisp ink contours, painterly wet materials, controlled cyan light, deep black threat shapes, cinematic but readable action silhouettes.
Continuity: the same single fighter, the same single connected black humanoid with exactly two arms and two hands, and the same single spear across all panels. Preserve accumulated injury, fatigue, water, channel light, screen direction, and prop ownership.
Constraints: no captions, dialogue balloons, labels, numbers, UI, watermark, logo, turnaround poses, white reference-sheet background, montage overlap, extra panels, or inset images. No additional person, limb, hand, weapon, aura, beam, root, tentacle, or unexplained power. The humanoid lower body remains one connected black liquid mass.
"""


def main() -> int:
    if sha256(SOURCE_PATH) != data.SOURCE_SHA256:
        raise ValueError("Independent EP00 source hash does not match the approved V2 screenplay.")
    segmentation = {
        "version": "ep00_reader_action_v2_segmentation_v1",
        "source_file": SOURCE_PATH.name,
        "source_sha256": data.SOURCE_SHA256,
        "clip_count": len(data.CLIPS),
        "total_duration_seconds": sum(float(row["duration"]) for row in data.CLIPS),
        "clips": data.CLIPS,
    }
    dialogue = {
        "version": "ep00_reader_action_v2_dialogue_lock_v1",
        "source_file": SOURCE_PATH.name,
        "source_sha256": data.SOURCE_SHA256,
        "dialogue_clip_count": len({row["clip_id"] for row in data.DIALOGUE_LOCK}),
        "dialogue_line_count": len(data.DIALOGUE_LOCK),
        "lines": data.DIALOGUE_LOCK,
    }
    storyboard = {
        "version": "ep00_reader_action_v2_storyboard_generation_v1",
        "source_file": SOURCE_PATH.name,
        "source_sha256": data.SOURCE_SHA256,
        "storyboard_count": len(data.CLIPS),
        "panel_count": len(data.CLIPS) * 4,
        "reading_order": ["top-left", "top-right", "bottom-left", "bottom-right"],
        "items": [
            {
                "clip_id": row["clip_id"],
                "output_file": f"storyboards/{row['clip_id'].replace('-', '_')}_STORYBOARD_V1.png",
                "panels": row["panels"],
                "prompt": storyboard_prompt(row),
                "status": "pending_generation",
            }
            for row in data.CLIPS
        ],
    }
    for path, payload in (
        (SEGMENTATION_PATH, segmentation),
        (DIALOGUE_PATH, dialogue),
        (STORYBOARD_MANIFEST_PATH, storyboard),
    ):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "project_root": str(PROJECT_ROOT),
        "clip_count": len(data.CLIPS),
        "panel_count": len(data.CLIPS) * 4,
        "dialogue_line_count": len(data.DIALOGUE_LOCK),
        "total_duration_seconds": segmentation["total_duration_seconds"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
