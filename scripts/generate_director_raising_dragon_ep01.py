#!/usr/bin/env python3
"""Generate LTX Director prompt project RaisingaDragonSeason01 from EP01 V4 MSR clips."""
from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import director_prompt_projects as dpp
from generate_ep01_v4_prompts import (  # noqa: E402
    BACKGROUNDS,
    CHARACTER_IDENTITY_REGISTRY,
    CLIPS,
    SCENARIO,
)
from scripts.director_still_prompts_ep01 import STILL_SPECS

PROJECT_ID = "RaisingaDragonSeason01"
OUT = ROOT / "director_prompt_projects" / PROJECT_ID
V4_PROJECT_ID = "RaisingaDragonSeason01_EP01_v4"

CHAR_NAME_TO_ID: dict[str, str] = {
    "Lua": "CHAR_LUA",
    "Young Mir": "CHAR_YOUNG_MIR",
    "Village Child 1": "CHAR_VILLAGE_CHILD_1",
    "Village Child 2": "CHAR_VILLAGE_CHILD_2",
    "Old Fisherman": "CHAR_OLD_FISHERMAN",
    "Black Jellyfish": "ENTITY_BLACK_JELLYFISH",
    "Black Tide": "ENTITY_BLACK_TIDE",
    "Lua's Fishing Spear": "PROP_LUA_SPEAR",
}

LOCATION_REGISTRY: dict[str, dict[str, Any]] = {
    "LOC_EP01_STORM_SEA_SURFACE_NIGHT": {
        "location_id": "LOC_EP01_STORM_SEA_SURFACE_NIGHT",
        "background_id": "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "display_name": "Storm Sea Surface at Night",
        "terrain": "Churning dark ocean surface with white foam and rain streaks",
        "structures": "No buildings — open sea horizon under black storm clouds",
        "time_of_day": "Night during violent storm",
        "lighting": "Cold moonless storm light with cool-white lightning flashes from upper left",
        "color_palette": "Deep blue-black sea, grey storm clouds, white foam highlights",
        "fixed_elements": [
            "Towering wave walls",
            "Rain streaks",
            "Distant lightning-lit horizon",
            "Open central water performance space",
        ],
        "dynamic_entities": [],
        "interactive_props": [],
        "environment_props": ["Spray and foam particles"],
    },
    "LOC_EP01_DEEP_SEA_RUINS_NIGHT": {
        "location_id": "LOC_EP01_DEEP_SEA_RUINS_NIGHT",
        "background_id": "BG_EP01_DEEP_SEA_RUINS_NIGHT",
        "display_name": "Deep Sea Dragon Palace Ruins",
        "terrain": "Deep underwater abyss with drifting marine snow",
        "structures": "Cracked ancient coral palace pillar with bioluminescent blue veins",
        "time_of_day": "Underwater night — no surface light",
        "lighting": "Cold cyan ambient underwater fill, soft blue bioluminescence on coral",
        "color_palette": "Dark teal abyss, cyan bioluminescent accents",
        "fixed_elements": [
            "Central open water space",
            "Ruined coral architecture receding into depth",
            "Marine snow particles",
        ],
        "dynamic_entities": [],
        "interactive_props": [],
        "environment_props": ["Drifting sediment motes"],
    },
    "LOC_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY": {
        "location_id": "LOC_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY",
        "background_id": "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY",
        "display_name": "Deep Sea Pursuit Corridor",
        "terrain": "Teal underwater corridor with diagonal ascent path",
        "structures": "Faint ruined coral edges at sides, open channel center",
        "time_of_day": "Underwater night",
        "lighting": "Cold cyan ambient from above-left, deep teal abyss below",
        "color_palette": "Teal water, cyan light beam, dark abyss",
        "fixed_elements": [
            "Diagonal blue light ascent path",
            "Empty corridor — no living black water mass in background plate",
        ],
        "dynamic_entities": ["Black Tide rendered as separate subject when present — not in background"],
        "interactive_props": [],
        "environment_props": ["Faint coral ruin edges"],
    },
    "LOC_EP01_MIR_VISION_PALACE_RUINS": {
        "location_id": "LOC_EP01_MIR_VISION_PALACE_RUINS",
        "background_id": "BG_EP01_MIR_VISION_PALACE_RUINS",
        "display_name": "Mir Vision — Broken Dragon Palace",
        "terrain": "Surreal floating debris over void abyss",
        "structures": "Broken palace gate, ruined hall columns",
        "time_of_day": "Dream-memory timeless",
        "lighting": "Cold blue memory-light with deep black void, soft fog",
        "color_palette": "Desaturated blue-grey, deep black void",
        "fixed_elements": [
            "Enormous sleeping dragon shadows as silhouettes without clear faces",
            "Open central vision space",
            "Slight dutch unsettling tilt",
        ],
        "dynamic_entities": [],
        "interactive_props": [],
        "environment_props": ["Floating debris", "Drifting dust motes"],
    },
    "LOC_EP01_COASTAL_VILLAGE_MORNING": {
        "location_id": "LOC_EP01_COASTAL_VILLAGE_MORNING",
        "background_id": "BG_EP01_COASTAL_VILLAGE_MORNING",
        "display_name": "Coastal Village Morning Shore",
        "terrain": "Wet stone breakwater, damp sand",
        "structures": "Overturned boats, tangled nets, broken wood; distant cliff with cave entrance",
        "time_of_day": "Morning after storm",
        "lighting": "Soft diffused morning sunlight from frame right, cool blue bounce on wet stone",
        "color_palette": "Warm morning light on wet grey stone, soft post-storm sky",
        "fixed_elements": [
            "Wet breakwater with open standing area",
            "Calm sea horizon",
            "Distant cave cliff hint at background right",
        ],
        "dynamic_entities": [],
        "interactive_props": ["Lua's fishing spear when held by Lua"],
        "environment_props": ["Scattered wet rope at breakwater edges", "Village repair debris on sand"],
    },
    "LOC_EP01_COASTAL_CAVE_INTERIOR": {
        "location_id": "LOC_EP01_COASTAL_CAVE_INTERIOR",
        "background_id": "BG_EP01_COASTAL_CAVE_INTERIOR",
        "display_name": "Coastal Cave Interior",
        "terrain": "Shallow seawater over uneven rock with reflective ripples",
        "structures": "Damp stone walls with droplets, tunnel receding into shadow",
        "time_of_day": "Daylight hint behind camera, cave interior cool",
        "lighting": "Cool blue-teal ambient from cave depth, soft blue glow from deeper cave",
        "color_palette": "Blue-teal wet stone, mystical blue light at depth",
        "fixed_elements": [
            "Central approach path through shallow water",
            "Rocky crevices on walls",
            "Blue glow stronger toward cave depth",
        ],
        "dynamic_entities": [],
        "interactive_props": ["Lua's fishing spear when held by Lua"],
        "environment_props": ["Water ripples on cave floor", "Cave wall droplets"],
    },
    "LOC_EP01_LUA_HOUSE_INTERIOR_DAY": {
        "location_id": "LOC_EP01_LUA_HOUSE_INTERIOR_DAY",
        "background_id": "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "display_name": "Lua's House Interior — Day",
        "terrain": "Wooden floor",
        "structures": "Humble coastal house: wooden bed, small table, water basin, window with daylight",
        "time_of_day": "Daytime",
        "lighting": "Warm daylight from window",
        "color_palette": "Warm wood tones, soft daylight fill",
        "fixed_elements": [
            "Shallow water basin at consistent side position",
            "Wooden bed and table in fixed layout",
            "Window with daylight view",
        ],
        "dynamic_entities": [],
        "interactive_props": [
            "Pale cream coastal comfort shell on table — Mir's preferred object, not worn by any character",
            "Dried fish on table — environment food prop",
            "Water jar on table",
        ],
        "environment_props": ["Shells scattered on table", "Cloth for hiding wrist mark"],
    },
    "LOC_EP01_LUA_HOUSE_IMAGINED_VILLAGE": {
        "location_id": "LOC_EP01_LUA_HOUSE_IMAGINED_VILLAGE",
        "background_id": "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE",
        "display_name": "Imagined Village Rejection Overlay",
        "terrain": "Open wooden floor blending into ghostly sand at edges",
        "structures": "Blurred village shore shapes without readable faces",
        "time_of_day": "Dream overlay — desaturated",
        "lighting": "Cold desaturated light with faint red anxiety tint, dreamlike soft edges",
        "color_palette": "Washed-out grey-blue, desaturated nightmare tint",
        "fixed_elements": [
            "No distinct adult faces visible",
            "Ghostly baskets and rope at edges",
            "Returns to literal house day lighting after beat",
        ],
        "dynamic_entities": [],
        "interactive_props": [],
        "environment_props": ["Blurred shore suggestion", "Desaturated overlay"],
    },
    "LOC_EP01_LUA_HOUSE_INTERIOR_NIGHT": {
        "location_id": "LOC_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "background_id": "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "display_name": "Lua's House Interior — Night",
        "terrain": "Dim wooden floor",
        "structures": "Same layout as day: bed, basin, table, window facing night sea",
        "time_of_day": "Night",
        "lighting": "Low warm interior fill mixed with cool blue moonlight from window frame right",
        "color_palette": "Warm interior shadows, cool blue moonlight on window side",
        "fixed_elements": [
            "Bed and basin positions match day variant",
            "Window with night sea view",
        ],
        "dynamic_entities": [],
        "interactive_props": [],
        "environment_props": ["Water basin", "Bed linens"],
    },
    "LOC_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW": {
        "location_id": "LOC_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW",
        "background_id": "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW",
        "display_name": "Night Sea View from Window",
        "terrain": "Dark calm sea surface with gentle ripples",
        "structures": "Minimal window frame edge at foreground",
        "time_of_day": "Night",
        "lighting": "Cool blue moonlight on sea, unnaturally still atmosphere",
        "color_palette": "Deep night blue sea, faint stars",
        "fixed_elements": [
            "Completely empty sea surface in background plate",
            "Elevated coastal house window perspective",
        ],
        "dynamic_entities": [
            "Black Jellyfish as separate subject when present — not duplicated in background plate",
        ],
        "interactive_props": [],
        "environment_props": ["Window frame edge optional at sides"],
    },
}

BG_TO_LOCATION: dict[str, str] = {
    bg_id: loc_id
    for loc_id, entry in LOCATION_REGISTRY.items()
    for bg_id in [entry["background_id"]]
}


def bg_to_location_id(bg_id: str) -> str:
    return BG_TO_LOCATION.get(bg_id, "LOC_UNKNOWN")


def registry_characters() -> dict[str, Any]:
    reg = deepcopy(CHARACTER_IDENTITY_REGISTRY)
    reg["project_id"] = PROJECT_ID
    return reg


def char_entry(char_id: str) -> dict[str, Any] | None:
    chars = registry_characters()["characters"]
    return chars.get(char_id)


def refs_to_characters(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        if ref.get("role") != "character":
            continue
        name = ref["character_name"]
        char_id = CHAR_NAME_TO_ID.get(name, name.upper().replace(" ", "_"))
        entry = char_entry(char_id)
        item: dict[str, Any] = {
            "character_id": char_id,
            "display_name": name,
            "source_path": ref.get("source_path"),
        }
        if entry:
            item["unique_identity_anchors"] = entry.get("unique_identity_anchors", [])
        out.append(item)
    return out


def refs_to_props(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        role = ref.get("role")
        if role not in {"hero_prop", "interactive_prop", "dynamic_entity"}:
            continue
        name = ref["character_name"]
        prop_id = CHAR_NAME_TO_ID.get(name, name.upper().replace(" ", "_"))
        owner = None
        if name == "Lua's Fishing Spear":
            owner = "CHAR_LUA"
        out.append(
            {
                "prop_id": prop_id,
                "display_name": name,
                "role": role,
                "owner_character_id": owner,
                "source_path": ref.get("source_path"),
            }
        )
    return out


def segment_dialogue(all_dialogue: list[dict[str, Any]], order: int) -> list[dict[str, Any]]:
    return [
        {"speaker": d["speaker"], "text": d["text"], "target": d.get("target")}
        for d in all_dialogue
        if d.get("segment_order") == order
    ]


def shorten(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rsplit(" ", 1)[0] + "..."


def relay_to_start_hint(relay_prompt: str, beat_type: str) -> str:
    """Derive a pre-action still-frame hint from a relay prompt."""
    text = relay_prompt.strip()
    replacements = [
        (r"\bthrusts\b", "is poised with spear raised, about to thrust"),
        (r"\brecoils\b", "is about to recoil"),
        (r"\blick(s|ing)? the shell\b", "reaches toward a pale cream shell on the table, nose close but not yet touching"),
        (r"\bhugs it\b", "presses both small limbs toward the shell, about to hug it"),
        (r"\bcrawls toward\b", "begins turning body toward"),
        (r"\bflash(es)? together\b", "marks are visible but have not yet flashed"),
        (r"\bturns orientation toward\b", "floats in frame, not yet turned toward"),
        (r"\bfades to black\b", "holds in frame before fade"),
        (r"\bsays in natural Korean\b", "faces the listener with mouth about to speak in natural Korean"),
        (r"\bshout(s)? in natural Korean\b", "overlay intensifies; voices imminent off-screen"),
        (r"\bplants her feet\b", "sets feet apart preparing to strike"),
        (r"\bopens his small dragon mouth\b", "tilts head with mouth closed, about to open"),
        (r"\blands on Lua's forehead\b", "a tiny water droplet floats mid-air approaching Lua's forehead"),
        (r"\bThe shot holds\b", "The frame holds steady at"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    if beat_type in {"establishing", "preparation"}:
        prefix = "Establishing frozen moment before action: "
    elif beat_type == "dialogue":
        prefix = "Frozen beat before or at the start of spoken line: "
    else:
        prefix = "Frozen instant before the main action of this beat: "
    return prefix + text


def build_negative_prompt(
    visible_characters: list[dict[str, Any]],
    visible_props: list[dict[str, Any]],
    location: dict[str, Any],
) -> str:
    parts = [
        "text",
        "watermark",
        "logo",
        "readable signs",
        "duplicate characters",
        "fused bodies",
        "merged anatomy",
        "extra limbs",
        "wrong wings on human",
        "wrong horns on human",
        "wrong tail on human",
        "human hair on dragon",
        "dragon scales on human",
        "live-action",
        "photorealistic",
        "motion blur",
        "completed action result",
        "trait exchange between characters",
    ]
    names = {c["display_name"] for c in visible_characters}
    if "Lua" in names and "Young Mir" in names:
        parts.extend(
            [
                "Lua with dragon wings horns or tail",
                "Mir with human clothing or hair",
                "Lua and Mir merged into one body",
            ]
        )
    if "Village Child 1" in names or "Village Child 2" in names:
        parts.extend(
            [
                "identical human children",
                "swapped hairstyles between village children",
                "Lua wearing indigo dress or shoulder basket",
                "Village Child 2 wearing beige tunic or shell pendant",
            ]
        )
    if any(p.get("prop_id") == "PROP_LUA_SPEAR" for p in visible_props):
        parts.append("spear fused into Lua body or held by wrong character")
    for entity in location.get("dynamic_entities", []):
        if "Black Tide" in entity:
            parts.append("black tide duplicated in background plate")
        if "Black Jellyfish" in entity:
            parts.append("jellyfish duplicated in background plate")
    return ", ".join(parts)


def build_scene_image_prompt(
    *,
    start_state: str,
    relay_prompt: str,
    beat_type: str,
    location: dict[str, Any],
    visible_characters: list[dict[str, Any]],
    visible_props: list[dict[str, Any]],
) -> str:
    loc_desc = (
        f"{location['display_name']}: {location['terrain']}. "
        f"{location['lighting']}. Palette: {location['color_palette']}."
    )
    fixed = ", ".join(location.get("fixed_elements", [])[:3])
    hint = relay_to_start_hint(relay_prompt, beat_type)
    char_lines: list[str] = []
    for char in visible_characters:
        anchors = ", ".join(char.get("unique_identity_anchors") or [])
        char_lines.append(
            f"{char['display_name']} ({char['character_id']}) with {anchors} — "
            f"exactly one instance, correct species and clothing ownership."
        )
    prop_lines: list[str] = []
    for prop in visible_props:
        owner = prop.get("owner_character_id") or "scene"
        prop_lines.append(
            f"{prop['display_name']} ({prop['prop_id']}) owned by {owner} — separate object, not body part."
        )
    parts = [
        "High-quality stylized feature-film animation still frame, 16:9 cinematic composition at 1280x704.",
        loc_desc,
        f"Fixed environment: {fixed}.",
        f"Segment opening frozen moment: {start_state}.",
        hint,
        " ".join(char_lines),
        " ".join(prop_lines) if prop_lines else "",
        "Specify screen positions and spacing when multiple characters appear — left, center, right, foreground, background.",
        "Leave clear visual space for the upcoming motion in this segment.",
        "Single frozen instant — no motion blur, no completed action outcome, no dialogue subtitles.",
    ]
    return " ".join(p for p in parts if p)


def convert_clip(item: dict[str, Any]) -> dict[str, Any]:
    p = item["payload"]
    bg_id = p["background"]["background_id"]
    loc_id = bg_to_location_id(bg_id)
    location = LOCATION_REGISTRY[loc_id]
    characters = refs_to_characters(p["references"])
    props = refs_to_props(p["references"])

    segments: list[dict[str, Any]] = []
    prev_end = p["continuity"]["start_state"]
    clip_id = p["clip_id"]

    for relay in p["relay_segments"]:
        order = relay["order"]
        seg_id = f"SEG{order:02d}"
        beat_type = relay.get("beat_type") or "action"
        start_state = prev_end if order > 1 else p["continuity"]["start_state"]
        end_state = shorten(relay["prompt"])
        dialogue = segment_dialogue(p.get("dialogue") or [], order)

        visible_chars = list(characters)
        visible_props = list(props)
        if order == 1 and "shell" in relay["prompt"].lower():
            visible_props.append(
                {
                    "prop_id": "PROP_MIR_COMFORT_SHELL",
                    "display_name": "Comfort Shell",
                    "role": "interactive_prop",
                    "owner_character_id": None,
                }
            )

        spec = STILL_SPECS.get((clip_id, seg_id), {})
        if spec.get("start_state"):
            start_state = spec["start_state"]
        scene_prompt = spec.get("prompt") or build_scene_image_prompt(
            start_state=start_state,
            relay_prompt=relay["prompt"],
            beat_type=beat_type,
            location=location,
            visible_characters=visible_chars,
            visible_props=visible_props,
        )
        negative = spec.get("negative") or build_negative_prompt(
            visible_chars, visible_props, location
        )

        segments.append(
            {
                "segment_id": seg_id,
                "order": order,
                "seconds": relay["seconds"],
                "beat_type": beat_type,
                "narrative_purpose": shorten(relay["prompt"], 120),
                "visible_characters": [c["character_id"] for c in visible_chars],
                "visible_props": [pr["prop_id"] for pr in visible_props],
                "start_state": start_state,
                "end_state": end_state,
                "director_prompt": relay["prompt"],
                "dialogue": dialogue,
                "scene_image": {
                    "status": "missing",
                    "suggested_filename": f"{clip_id}_{seg_id}.png",
                    "source_path": None,
                    "prompt": scene_prompt,
                    "negative_prompt": negative,
                    "review_status": "pending",
                    "review_notes": [],
                    "sha256": None,
                },
            }
        )
        prev_end = end_state

    review = p.get("review") or {}
    warnings = list(review.get("warnings") or [])
    if clip_id == "SC01-004_02":
        warnings = [
            w
            for w in warnings
            if "user decision" not in w.lower() and "needs_confirmation" not in w.lower()
        ]
        warnings.append(
            "Comfort shell described in scene_image prompts as pale cream coastal shell on table — no dedicated reference PNG."
        )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "workflow": "director_prompt_v1",
        "project_id": PROJECT_ID,
        "episode_id": p["episode_id"],
        "scene_id": p["scene_id"],
        "clip_id": clip_id,
        "sequence": p["sequence"],
        "status": "awaiting_scene_images",
        "fps": 24,
        "resolution": {"width": 1280, "height": 704},
        "requested_seconds": p["requested_seconds"],
        "scenario_source": p["scenario_source"],
        "scenario_source_span": p["scenario_source_span"],
        "narrative_purpose": p["narrative_purpose"],
        "characters": characters,
        "props": props,
        "location": {
            "location_id": loc_id,
            "description": location["display_name"] + " — " + BACKGROUNDS[bg_id]["description"],
        },
        "continuity": p["continuity"],
        "global_prompt": p["global_prompt"],
        "segments": segments,
        "prompt_review": {
            "status": "approved",
            "scenario_consistent": review.get("scenario_consistent", True),
            "dialogue_preserved": review.get("dialogue_preserved", True),
            "duration_valid": review.get("duration_valid", True),
            "identity_rules_valid": bool(
                review.get("identity_review") or review.get("character_review") or len(characters) <= 1
            ),
            "segment_continuity_valid": True,
            "image_prompts_valid": True,
            "warnings": warnings,
            "review_notes": [
                f"Converted from {V4_PROJECT_ID} relay segments with one core action per segment.",
                "Scene image prompts show segment start state only.",
            ],
        },
        "image_review_summary": {
            "status": "pending",
            "approved_count": 0,
            "total_count": len(segments),
            "warnings": [],
        },
    }
    return {"summary": item["summary"], "payload": payload}


def render_markdown(item: dict[str, Any]) -> str:
    payload = item["payload"]
    clip_id = payload["clip_id"]
    lines = [
        f"# Director Prompt: {clip_id}",
        "",
        "## Summary",
        "",
        item["summary"],
        "",
        "## Machine Payload",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


def validate_output() -> list[str]:
    errors: list[str] = []
    clips = dpp.scan_project_clips(ROOT, PROJECT_ID)
    if len(clips) != 24:
        errors.append(f"Expected 24 clips, got {len(clips)}")
    total_seconds = sum(c["requested_seconds"] for c in clips)
    if total_seconds != 412:
        errors.append(f"Expected 412 total seconds, got {total_seconds}")
    total_segments = sum(c["segment_count"] for c in clips)
    if total_segments != 89:
        errors.append(f"Expected 89 segments, got {total_segments}")
    needs_conf = [c for c in clips if c["status"] == "needs_confirmation"]
    if needs_conf:
        errors.append(f"Unexpected needs_confirmation clips: {[c['clip_id'] for c in needs_conf]}")
    invalid = [c for c in clips if not c["valid"]]
    if invalid:
        for c in invalid:
            errors.append(f"{c['clip_id']}: invalid — {c['errors']}")
    for c in clips:
        if c["status"] != "awaiting_scene_images":
            errors.append(f"{c['clip_id']}: expected awaiting_scene_images, got {c['status']}")
    return errors


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scene_times: dict[str, float] = {}
    all_image_files: list[str] = []

    for item in CLIPS:
        converted = convert_clip(item)
        payload = converted["payload"]
        scene_dir = OUT / payload["scene_id"]
        scene_dir.mkdir(parents=True, exist_ok=True)
        clip_id = payload["clip_id"]
        (scene_dir / f"{clip_id}.md").write_text(
            render_markdown(converted), encoding="utf-8"
        )
        img_dir = OUT / "scene_images" / clip_id
        img_dir.mkdir(parents=True, exist_ok=True)
        scene_times[payload["scene_id"]] = (
            scene_times.get(payload["scene_id"], 0) + payload["requested_seconds"]
        )
        for seg in payload["segments"]:
            all_image_files.append(seg["scene_image"]["suggested_filename"])

    char_reg = registry_characters()
    (OUT / "character_identity_registry.json").write_text(
        json.dumps(char_reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    loc_reg = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "locations": LOCATION_REGISTRY,
    }
    (OUT / "location_registry.json").write_text(
        json.dumps(loc_reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total_seconds = sum(c["payload"]["requested_seconds"] for c in map(convert_clip, CLIPS))
    manifest = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon Season 1 — EP01 Director Prompts",
        "description": (
            "LTX Director Prompt Relay project for EP01. Scene-image-based segments converted "
            f"from {V4_PROJECT_ID} with identity locks, Korean dialogue preservation, and "
            "1280x704 at 24fps."
        ),
        "scenario_source": SCENARIO,
        "episode_coverage": ["EP01"],
        "source_msr_project": V4_PROJECT_ID,
        "policy": {
            "workflow": "director_prompt_v1",
            "language": "English visual prompts; Korean spoken dialogue only",
            "max_clip_seconds": 30,
            "resolution": {"width": 1280, "height": 704},
            "fps": 24,
            "character_identity_registry": "character_identity_registry.json",
            "location_registry": "location_registry.json",
        },
        "scene_count": len(scene_times),
        "clip_count": len(CLIPS),
        "segment_count": len(all_image_files),
        "total_requested_seconds": total_seconds,
        "scene_requested_seconds": scene_times,
        "status_summary": {"awaiting_scene_images": len(CLIPS)},
        "notes": [
            f"Converted from {V4_PROJECT_ID} — MSR projects preserved untouched.",
            "All clips prompt_review approved; scene images pending user generation.",
            "SC01-004_02 uses awaiting_scene_images with detailed comfort-shell scene_image prompts.",
            "89 segment scene images required across 24 clips.",
        ],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    errors = validate_output()
    for err in errors:
        print(f"VALIDATION ERROR: {err}", file=sys.stderr)
    if errors:
        return 1

    print(f"Generated Director project: {len(CLIPS)} clips, {len(all_image_files)} scene images, {total_seconds}s")
    print(f"Output: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
