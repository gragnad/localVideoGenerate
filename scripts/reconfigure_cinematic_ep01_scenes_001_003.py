#!/usr/bin/env python3
"""Video-first cinematic reconfiguration for EP01 scenes SC01-001 through SC01-003."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import director_prompt_projects as projects

PROJECT_ID = "RaisingaDragonSeason01"
TARGET_SCENES = ("SC01-001", "SC01-002", "SC01-003")
REFERENCE_CLIP = "SC01-003_09"
PLAN_VERSION = "cinematic_plan_v1_restrained_camera"
IMAGE_VERSION = "cinematic_anchor_v3_video_first"

CLIP_PLANS: dict[str, dict[str, Any]] = {
    "SC01-001_01": {
        "lens": "grounded virtual 28mm wide lens",
        "intent": "Observe the storm at scale, then discover one fragile blue signal below it.",
        "movement_budget": 1,
        "lighting": "cold lightning from upper left, blue pulse below, black storm water",
        "phases": [
            "Locked extreme-wide observation; environmental motion supplies all energy while the camera remains still.",
            "The blue pulse motivates one restrained downward tilt that begins slowly and never accelerates.",
            "Continue that same downward move, then settle above the wave trough for the final reveal hold.",
        ],
        "axes": ["storm-wide", "storm-wide-descending", "storm-wide-settled"],
    },
    "SC01-001_02": {
        "lens": "grounded virtual 35mm underwater lens",
        "intent": "Reveal Young Mir as a vulnerable survivor inside an immense ruined world.",
        "movement_budget": 1,
        "lighting": "cold cyan ambience above, blue bioluminescence, deep teal falloff",
        "phases": [
            "Locked underwater wide composition; drifting particles and the cracking pillar create motion within the frame.",
            "Hold the same axis as Young Mir becomes readable inside the blue glow; no camera reposition is needed.",
            "Young Mir's tumble motivates one gentle forward drift that closes distance without orbiting him.",
            "End that same drift and settle into a stable medium composition while he attempts to orient upward.",
        ],
        "axes": ["ruin-wide", "ruin-wide", "mir-forward-drift", "mir-settled-medium"],
    },
    "SC01-001_03": {
        "lens": "grounded virtual 35mm underwater lens",
        "intent": "Keep Mir and the Black Tide in one readable pursuit axis and punctuate the threat with one eye move.",
        "movement_budget": 2,
        "lighting": "diagonal blue ascent beam above, black mass below, cold teal corridor",
        "phases": [
            "Locked vertical pursuit composition establishes Young Mir above and the Black Tide below.",
            "Young Mir's climb motivates one slow upward tracking move along the existing diagonal beam.",
            "The camera settles as the tail crystal flashes; allow the light burst and recoil to carry the beat.",
            "A second restrained move pushes toward Young Mir's eye and stops there; unstable reflected light supplies the motion.",
        ],
        "axes": ["vertical-pursuit", "vertical-pursuit-track", "vertical-pursuit-settle", "mir-eye"],
    },
    "SC01-001_04": {
        "lens": "grounded virtual 40mm dream lens",
        "intent": "Let the memory feel oppressive through a single weightless approach followed by still close observation.",
        "movement_budget": 1,
        "lighting": "cold memory-blue edges, black abyss, desaturated palace ruins",
        "phases": [
            "One slow weightless forward float enters the ruined palace vision; keep the trajectory straight and quiet.",
            "Complete that same float at Young Mir's reflected eye and hold the close composition.",
            "Locked eye composition during the first voice line; only reflections and the pupil move.",
            "Remain locked for the second line while the memory tears into storm light around the frame edges.",
        ],
        "axes": ["vision-forward", "mir-eye-locked", "mir-eye-locked", "mir-eye-locked"],
    },
    "SC01-001_05": {
        "lens": "grounded virtual 28mm underwater-to-surface lens",
        "intent": "Carry one continuous upward struggle from deep water to a distant coastal mystery.",
        "movement_budget": 1,
        "lighting": "blue glow below, lightning-lit surface above, distant dark coast",
        "phases": [
            "Young Mir's upward effort motivates one continuous vertical follow toward the storm-lit surface.",
            "Continue the same vertical movement through the waterline without changing direction or speed.",
            "Settle into a distant locked coastal wide; waves carry the blue glow while the camera remains still.",
        ],
        "axes": ["upward-follow", "surface-break-continuation", "coastal-wide-locked"],
    },
    "SC01-002_01": {
        "lens": "grounded virtual 35mm coastal lens",
        "intent": "Stage the comedy through actor blocking inside one readable breakwater composition.",
        "movement_budget": 1,
        "lighting": "soft post-storm daylight from frame right, cool wet-stone bounce",
        "phases": [
            "Locked medium-wide ensemble composition establishes Lua and both village children with clear separation.",
            "Remain on the same axis while Lua raises the spear; her awkward body movement is the visual focus.",
            "The failed thrust and splash motivate one short controlled push-in, ending on Lua's embarrassed reaction.",
            "Hold the resulting composition for the children's teasing and Lua's reply; no additional camera move.",
        ],
        "axes": ["breakwater-ensemble", "breakwater-ensemble", "lua-reaction-push", "lua-reaction-hold"],
    },
    "SC01-002_02": {
        "lens": "grounded virtual 35mm coastal lens",
        "intent": "Use stable adult blocking for the warning, then let gaze and off-screen space reveal the cave temptation.",
        "movement_budget": 2,
        "lighting": "soft morning daylight, wet-stone reflections, faint blue cave pulse in distance",
        "phases": [
            "Locked low medium-wide composition observes Lua recovering in the shallows.",
            "Hold the same camera position for Lua's embarrassed excuse; performance carries the beat.",
            "The Old Fisherman's entrance motivates one restrained pan that widens into a balanced two-shot.",
            "Remain locked in that two-shot during his lesson and Lua's hardened response.",
            "His gaze toward the cliff motivates one slow pan to include the distant cave while both characters stay readable.",
            "Hold the cave-inclusive composition as the blue pulse catches Lua's eye; Lua runs out of frame while the camera stays.",
        ],
        "axes": ["shallows-low", "shallows-low", "fisherman-two-shot", "fisherman-two-shot", "cave-reveal", "cave-reveal-hold"],
    },
    "SC01-003_01": {
        "lens": "grounded virtual 35mm cave lens",
        "intent": "Build tension with one nearly imperceptible approach into the cave and long periods of stillness.",
        "movement_budget": 1,
        "lighting": "blue cave glow from depth, faint daylight behind, wet rock highlights",
        "phases": [
            "Begin one extremely slow straight forward creep behind Lua as she enters; foreground rocks provide parallax.",
            "Continue the same barely perceptible creep while Lua steadies herself and the spear.",
            "Settle over Lua's left shoulder and hold through all three Korean dialogue lines.",
            "Remain locked after the squeak; Lua's listening stillness and cave droplets carry the suspense.",
        ],
        "axes": ["cave-entry-creep", "cave-entry-creep", "lua-shoulder-hold", "lua-shoulder-hold"],
    },
    "SC01-003_02": {
        "lens": "grounded virtual 40mm cave lens",
        "intent": "Let the first meeting grow through a single gentle reveal while both identities stay readable.",
        "movement_budget": 1,
        "lighting": "soft blue crevice glow, dim daylight rim, wet stone reflections",
        "phases": [
            "Lua's lean into the crevice motivates one gentle forward reveal that brings Young Mir into the same composition.",
            "Complete that reveal and hold the two-shot for Lua's first surprised line.",
            "Remain locked while Lua questions what Young Mir is; expression and breathing provide motion.",
            "Hold the same axis for their shared gaze and Lua's awed reaction.",
            "Use only a minimal downward reframing with Lua's extending hand, preserving the same camera position and screen direction.",
        ],
        "axes": ["crevice-reveal", "meeting-two-shot", "meeting-two-shot", "meeting-two-shot", "meeting-hand-reframe"],
    },
    "SC01-003_03": {
        "lens": "grounded virtual 40mm cave lens",
        "intent": "Protect the intimacy of the approach with one stable two-shot and no major camera movement.",
        "movement_budget": 0,
        "lighting": "soft blue cave ambience, gentle wet-rock bounce, readable faces",
        "phases": [
            "Locked eye-level medium two-shot; Lua's kneeling movement happens entirely within the frame.",
            "Keep the same locked composition as Lua extends her hand and Young Mir watches.",
            "Remain locked through Lua's reassurance so both separate silhouettes and her open hand stay readable.",
            "Remain locked for the final line; use performance and a small stomach gesture instead of camera movement.",
        ],
        "axes": ["contact-two-shot", "contact-two-shot", "contact-two-shot", "contact-two-shot"],
    },
    "SC01-003_04": {
        "lens": "grounded virtual 50mm intimate cave lens",
        "intent": "Make the first touch readable with a stable hand-and-face composition and one restrained emphasis.",
        "movement_budget": 1,
        "lighting": "soft blue cave ambience, skin and scale highlights, dark unobtrusive background",
        "phases": [
            "Locked intimate medium composition holds Lua's open hand and Young Mir's cautious approach together.",
            "Young Mir's contact motivates one very short controlled push toward the fingertip, then the camera stops for Lua's reaction.",
        ],
        "axes": ["hand-contact-medium", "hand-contact-close"],
    },
    "SC01-003_05": {
        "lens": "grounded virtual 50mm detail cave lens",
        "intent": "Let blood, water ripple and two separate marks transform within one stable contact composition.",
        "movement_budget": 0,
        "lighting": "soft blue supernatural glow, wet skin and scale detail, dark cave falloff",
        "phases": [
            "Locked detail composition keeps Lua's fingertip and Young Mir's shoulder in one spatially clear frame.",
            "Remain locked as the blood drop lands, ripples spread and Lua's wrist mark appears.",
            "Remain locked while Young Mir's chest mark answers; light changes direct attention without camera movement.",
        ],
        "axes": ["mark-contact-detail", "mark-contact-detail", "mark-contact-detail"],
    },
    "SC01-003_06": {
        "lens": "grounded virtual 40mm cave lens",
        "intent": "Reveal the energy connection without suggesting anatomical fusion.",
        "movement_budget": 1,
        "lighting": "thin blue connection light, cool cave ambience, separate silhouette rim light",
        "phases": [
            "The blue connection motivates one slow straight pullback until both separate bodies and the open gap are fully readable.",
            "Complete the pullback and hold the balanced two-shot; only the light pulses while anatomy stays unchanged.",
        ],
        "axes": ["connection-pullback", "connection-two-shot-hold"],
    },
    "SC01-003_07": {
        "lens": "grounded virtual 32mm dream lens",
        "intent": "Travel through the vision as one restrained forward float rather than a sequence of unrelated shots.",
        "movement_budget": 1,
        "lighting": "cold blue heart-stone glow, black roots, desaturated ruined palace shadows",
        "phases": [
            "Begin one slow weightless forward float into the collapsed dragon palace vision.",
            "Continue the same straight float toward the root-bound blue heart-stone; do not orbit it.",
            "Continue beyond the heart-stone into the black abyss and decelerate to a final still frame.",
        ],
        "axes": ["vision-forward", "heart-stone-forward", "abyss-settle"],
    },
    "SC01-003_08": {
        "lens": "grounded virtual 40mm cave lens",
        "intent": "Return to reality through stillness, then restore spatial context with one gentle pullback.",
        "movement_budget": 1,
        "lighting": "blue mark fading, cool cave ambience, stable wet-rock landmarks",
        "phases": [
            "Locked close-medium composition catches Lua's gasp and wrist-mark reaction without camera motion.",
            "The fading connection motivates one gentle pullback to a stable two-shot containing both separate bodies.",
        ],
        "axes": ["lua-return-close", "reality-two-shot-pullback"],
    },
}

CAMERA_REPHRASES = (
    (r"The camera holds wide on", "The wide composition shows"),
    (r"The camera slowly tilts downward toward", "Attention shifts downward toward"),
    (r"The camera continues descending toward", "The descent approaches"),
    (r"The camera moves closer with gentle handheld drift\.", "His weak tumble remains the sole source of instability."),
    (r"The shot holds on", "The composition settles on"),
    (r"The camera shudders slightly and holds on", "His unstable vision trembles around"),
    (r"The frame drifts shakily through", "A black abyss reveals"),
    (r"The camera breaks surface into", "The continuous upward movement reaches"),
    (r"The shot holds in", "A stable composition presents"),
    (r"The frame cuts to", "A surreal vision reveals"),
    (r"The camera drifts through", "The vision carries forward through"),
    (r"The camera holds in", "A stable composition keeps"),
)


def rephrase_embedded_camera(prompt: str) -> str:
    text = str(prompt or "").strip()
    for pattern, replacement in CAMERA_REPHRASES:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).strip()


def strip_still_prefix(prompt: str) -> str:
    text = str(prompt or "").strip()
    patterns = (
        r"^High-quality stylized feature-film animation still,\s*16:9,\s*1280x704\.\s*",
        r"^Cinematic keyframe from a premium stylized 3D animated feature,\s*widescreen 16:9\.\s*",
    )
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.I)
    return text.strip()


def cinematic_still_prompt(base: str, lens: str, axis: str) -> str:
    body = strip_still_prefix(base)
    return (
        "Cinematic keyframe from a premium stylized 3D animated feature, widescreen 16:9. "
        f"{lens.capitalize()}, motion-ready timed composition anchor on the {axis} axis. "
        f"{body} Build readable foreground, midground and background layers, preserve movement space, "
        "and avoid a flat centered poster pose."
    )


def cinematic_generation_prompt(base: str, lens: str, axis: str, lighting: str) -> str:
    text = str(base or "").strip()
    if not text:
        text = "Premium stylized 3D animated feature-film keyframe, cinematic widescreen 16:9 composition."
    marker = "Premium stylized 3D animated feature-film keyframe,"
    addition = (
        f" {lens.capitalize()}. This is a video-first timed composition anchor on the {axis} axis, "
        "designed for reachable blocking and continuous motion rather than an isolated poster frame."
    )
    if marker in text:
        text = text.replace(marker, marker + addition, 1)
    else:
        text = addition.strip() + "\n\n" + text
    return text.rstrip() + (
        f"\n\nCinematic continuity: {lighting}. Preserve foreground-midground-background depth, "
        "consistent lens height, screen direction, navigable movement space and all fixed environment landmarks."
    )


def render_markdown(markdown: str, payload: dict[str, Any]) -> str:
    replacement = "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"
    updated, count = projects.JSON_BLOCK_RE.subn(lambda _: replacement, markdown, count=1)
    if count != 1:
        raise RuntimeError(f"Machine payload block not found: {payload.get('clip_id')}")
    return updated


def reconfigure_payload(payload: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    segments = payload.get("segments") or []
    if len(segments) != len(plan["phases"]) or len(segments) != len(plan["axes"]):
        raise ValueError(f"Camera plan segment mismatch: {payload.get('clip_id')}")

    camera_bible = (
        f"CINEMATIC CAMERA BIBLE: {plan['lens']}. The entire clip follows one coherent spatial grammar. "
        f"Camera movement budget is {plan['movement_budget']} major move(s). {plan['intent']} "
        f"Lighting continuity: {plan['lighting']}. Camera movement must be motivated by subject action, gaze, "
        "environmental force or emotional change. Hold and settle whenever movement is not necessary."
    )
    base_global = str(payload.get("global_prompt_base") or payload.get("global_prompt") or "").strip()
    payload["global_prompt_base"] = base_global
    payload["global_prompt"] = base_global.rstrip() + "\n\n" + camera_bible
    payload["cinematic_plan"] = {
        "version": PLAN_VERSION,
        "continuous_generation": True,
        "intent": plan["intent"],
        "lens_language": plan["lens"],
        "camera_move_budget": plan["movement_budget"],
        "lighting_rule": plan["lighting"],
        "beats": [
            {
                "segment_id": segment["segment_id"],
                "start_second": sum(float(s["seconds"]) for s in segments[:index]),
                "duration_seconds": float(segment["seconds"]),
                "camera_behavior": plan["phases"][index],
                "camera_axis": plan["axes"][index],
            }
            for index, segment in enumerate(segments)
        ],
    }

    for index, segment in enumerate(segments):
        base_prompt = str(segment.get("director_prompt_base") or segment.get("director_prompt") or "").strip()
        segment["director_prompt_base"] = base_prompt
        segment["director_prompt"] = (
            plan["phases"][index] + " " + rephrase_embedded_camera(base_prompt)
        ).strip()
        image = dict(segment.get("scene_image") or {})
        base_still = str(image.get("prompt_base") or image.get("prompt") or "").strip()
        base_generation = str(
            image.get("generation_prompt_base") or image.get("generation_prompt") or ""
        ).strip()
        image["prompt_base"] = base_still
        image["generation_prompt_base"] = base_generation
        image["prompt"] = cinematic_still_prompt(base_still, plan["lens"], plan["axes"][index])
        image["generation_prompt"] = cinematic_generation_prompt(
            base_generation, plan["lens"], plan["axes"][index], plan["lighting"]
        )
        negative = str(image.get("negative_prompt") or "").strip().rstrip(", ")
        additions = (
            "flat centered poster composition, symmetrical lineup, inconsistent lens height, "
            "reversed screen direction, inconsistent lighting, blocked movement path"
        )
        if additions not in negative:
            negative = f"{negative}, {additions}" if negative else additions
        image["negative_prompt"] = negative
        image["prompt_version"] = IMAGE_VERSION
        image["anchor_second"] = sum(float(s["seconds"]) for s in segments[:index])
        image["anchor_role"] = "opening" if index == 0 else "timed_arrival"
        image["camera_axis"] = plan["axes"][index]
        image["recommended_guide_strength"] = 0.75
        image["status"] = "uploaded" if image.get("source_path") else "missing"
        image["review_status"] = "changes_required"
        image["review_notes"] = [
            "영상 우선 시네마틱 플랜에 맞춰 새 앵커 이미지를 생성하고 교체해야 합니다."
        ]
        segment["scene_image"] = image

    payload["status"] = "image_changes_required"
    payload["image_review_summary"] = {
        "status": "changes_required",
        "approved_count": 0,
        "total_count": len(segments),
        "warnings": ["모든 앵커 이미지를 새 영상 우선 프롬프트로 재생성하고 승인해야 합니다."],
    }
    review = dict(payload.get("prompt_review") or {})
    notes = [
        str(note) for note in review.get("review_notes") or []
        if PLAN_VERSION not in str(note)
    ]
    notes.append(
        f"{PLAN_VERSION}: restrained camera plan applied with a maximum of "
        f"{plan['movement_budget']} major move(s); all anchors require regeneration."
    )
    review.update(
        status="approved",
        duration_valid=True,
        segment_continuity_valid=True,
        image_prompts_valid=True,
        warnings=[],
        review_notes=notes,
    )
    payload["prompt_review"] = review
    return payload


def apply_reconfiguration(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    project_dir = root / projects.DIRECTOR_PROMPT_PROJECTS_DIR / PROJECT_ID
    changed: list[str] = []
    segments_changed = 0
    preserved: list[str] = []
    for scene_id in TARGET_SCENES:
        for markdown_path in sorted((project_dir / scene_id).glob("*.md")):
            markdown = markdown_path.read_text(encoding="utf-8")
            payload = projects.extract_machine_payload(markdown)
            clip_id = str(payload.get("clip_id") or "")
            if clip_id == REFERENCE_CLIP:
                preserved.append(clip_id)
                continue
            plan = CLIP_PLANS.get(clip_id)
            if plan is None:
                raise KeyError(f"Missing cinematic plan: {clip_id}")
            payload = reconfigure_payload(payload, plan)
            changed.append(clip_id)
            segments_changed += len(payload.get("segments") or [])
            if not dry_run:
                updated = render_markdown(markdown, payload)
                temporary = markdown_path.with_name(f".{markdown_path.name}.{os.getpid()}.tmp")
                temporary.write_text(updated, encoding="utf-8")
                temporary.replace(markdown_path)
    return {
        "dry_run": dry_run,
        "plan_version": PLAN_VERSION,
        "clips_changed": changed,
        "clip_count": len(changed),
        "segments_changed": segments_changed,
        "preserved_clips": preserved,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(apply_reconfiguration(args.root, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
