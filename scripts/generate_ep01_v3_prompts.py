#!/usr/bin/env python3
"""Generate RaisingaDragonSeason01_EP01_v3 MSR prompt project from EP01 scenario."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_v3"
OUT = ROOT / "prompt_projects" / PROJECT_ID
SCENARIO = "RaisingaDragonSeason01/Raising a Dragon.md"
SUPERSEDES = "RaisingaDragonSeason01_EP01_v2"

STYLE_FOOTER = (
    "Preserve the exact visual style of the supplied animated references. "
    "High-quality stylized feature-film animation. Preserve facial design, body proportions, "
    "clothing and color palette. Do not convert animated references into live-action realism.\n\n"
    "All spoken dialogue and voice-over must be natural Korean. "
    "Lip-sync and mouth movement should match Korean speech timing. "
    "Do not translate dialogue into English."
)

LUA_APPEARANCE = (
    "Picture {n} is Lua, one human coastal village girl. She has sun-browned human skin, "
    "messy light-brown human hair, large brown eyes, two human arms and two human legs. "
    "She wears a short sleeveless coastal tunic, a rope belt, simple shorts, sandals and "
    "small shell ornaments. Lua has a completely human body with no dragon wings, no horns, "
    "no scales, no tail and no dragon anatomy."
)
MIR_APPEARANCE = (
    "Picture {n} is Young Mir, one small blue-silver sea dragon. He has silver-blue scales, "
    "short curved horns, one pair of fin-like dragon wings, four small dragon limbs, a long "
    "scaled tail ending in a water-drop crystal and a faint crown-shaped wave mark on his chest. "
    "Young Mir is a small dragon, not a human child."
)
CHILD1_APPEARANCE = (
    "Picture {n} is Village Child 1, a coastal village child in simple rustic clothes "
    "with a playful curious expression."
)
CHILD2_APPEARANCE = (
    "Picture {n} is Village Child 2, a coastal village child in simple rustic clothes "
    "with a teasing smile."
)
FISHERMAN_APPEARANCE = (
    "Picture {n} is the Old Fisherman, an elderly coastal villager with weathered skin, "
    "simple worn fishing clothes and a calm serious expression."
)
JELLYFISH_APPEARANCE = (
    "Picture {n} is the Black Jellyfish, a semi-transparent dark jellyfish with ink-like "
    "smoke swirling inside its bell and long tentacles trailing below the surface."
)
BLACK_TIDE_APPEARANCE = (
    "Picture {n} is the Black Tide, a living supernatural mass of black water that moves "
    "independently through the deep sea. It forms brief hand-like and mouth-like shadow shapes "
    "within its dark body as it rises and pursues prey."
)
SPEAR_APPEARANCE = (
    "Picture {n} is Lua's fixed handmade coastal fishing spear. Preserve the exact shaft length, "
    "spearhead silhouette, rope wrapping, material, color and small ornaments shown in the "
    "reference throughout the clip. Lua carries and uses this same spear without redesigning "
    "or replacing it."
)

ANATOMY_SEPARATION = (
    "Exactly two distinct subjects appear in this clip: one human Lua and one small dragon Young Mir. "
    "Keep Lua and Young Mir as two separate species, two separate identities and two separate bodies "
    "throughout the entire clip. Do not merge, fuse, duplicate or replace either subject. "
    "Do not transfer Young Mir's wings, horns, scales, tail, blue coloration or chest mark onto Lua. "
    "Do not transfer Lua's human face, hair, clothing, arms or legs onto Young Mir. "
    "Young Mir's wings belong only to Young Mir and may fold, relax or open naturally according to "
    "his movement and emotional state, but must never appear on Lua. "
    "Lua's clothing and accessories belong only to Lua. Young Mir must remain unclothed as shown "
    "in his dragon reference unless the scenario explicitly states otherwise. "
    "Exactly one Lua and exactly one Young Mir. No duplicate Lua. No duplicate Young Mir. "
    "Their bodies remain visibly separate and their silhouettes remain readable."
)

REF_PATHS = {
    "lua": "RaisingaDragonSeason01/Lua.png",
    "young_mir": "RaisingaDragonSeason01/YoungMir.png",
    "child1": "RaisingaDragonSeason01/villageChild01.png",
    "child2": "RaisingaDragonSeason01/village_child_2.png",
    "old_fisherman": "RaisingaDragonSeason01/old_fisherman.png",
    "jellyfish": "RaisingaDragonSeason01/BLACK JELLYFISH .png",
    "black_tide": "RaisingaDragonSeason01/BLACK TIDE — SUPERNATURAL .png",
    "spear": "RaisingaDragonSeason01/spear.png",
}

ROLE_MAP = {
    "lua": "character",
    "young_mir": "character",
    "child1": "character",
    "child2": "character",
    "old_fisherman": "character",
    "jellyfish": "dynamic_entity",
    "black_tide": "dynamic_entity",
    "spear": "hero_prop",
}

NAME_MAP = {
    "lua": "Lua",
    "young_mir": "Young Mir",
    "child1": "Village Child 1",
    "child2": "Village Child 2",
    "old_fisherman": "Old Fisherman",
    "jellyfish": "Black Jellyfish",
    "black_tide": "Black Tide",
    "spear": "Lua's Fishing Spear",
}

APPEARANCE_MAP = {
    "lua": LUA_APPEARANCE,
    "young_mir": MIR_APPEARANCE,
    "child1": CHILD1_APPEARANCE,
    "child2": CHILD2_APPEARANCE,
    "old_fisherman": FISHERMAN_APPEARANCE,
    "jellyfish": JELLYFISH_APPEARANCE,
    "black_tide": BLACK_TIDE_APPEARANCE,
    "spear": SPEAR_APPEARANCE,
}

CHARACTER_REVIEW = {
    "exactly_one_lua": True,
    "exactly_one_young_mir": True,
    "lua_fully_human": True,
    "young_mir_small_dragon": True,
    "lua_no_wings": True,
    "lua_no_horns": True,
    "lua_no_scales": True,
    "lua_no_tail": True,
    "young_mir_no_human_hair": True,
    "young_mir_no_human_clothing": True,
    "anatomy_does_not_transfer": True,
    "bodies_remain_separate": True,
    "no_subject_duplication": True,
    "contact_ownership_clear": True,
    "vision_separated_from_contact": True,
    "character_sheets_unchanged": True,
    "young_mir_wing_pose_not_fixed": True,
}


def ref(key: str, ref_id: int, *, role: str | None = None) -> dict[str, Any]:
    return {
        "reference_id": ref_id,
        "character_name": NAME_MAP[key],
        "role": role or ROLE_MAP[key],
        "description": APPEARANCE_MAP[key].format(n=ref_id),
        "source_path": REF_PATHS[key],
    }


def relay(order: int, seconds: float, prompt: str, *, beat_type: str | None = None) -> dict[str, Any]:
    seg: dict[str, Any] = {"order": order, "seconds": seconds, "prompt": prompt}
    if beat_type:
        seg["beat_type"] = beat_type
    return seg


def build_global_prompt(
    scene_label: str,
    scene_summary: str,
    ref_keys: list[tuple[str, int]],
    env_lines: list[str],
    *,
    lighting: str | None = None,
    include_anatomy_separation: bool = False,
    consistency_notes: list[str] | None = None,
) -> str:
    parts = [
        f"Ocean fantasy animated film. {scene_label} — {scene_summary}.",
        "High-quality stylized feature-film animation matching the supplied references.",
        "",
    ]
    for key, n in ref_keys:
        parts.append(APPEARANCE_MAP[key].format(n=n))
    parts.append("")
    if include_anatomy_separation:
        parts.append(ANATOMY_SEPARATION)
        parts.append("")
    parts.append("Environment and setting:")
    parts.extend(f"- {line}" for line in env_lines)
    parts.append("")
    if lighting:
        parts.append(f"Lighting and color: {lighting}")
        parts.append("")
    if consistency_notes:
        parts.append("Reference consistency:")
        parts.extend(f"- {note}" for note in consistency_notes)
        parts.append("")
    parts.append(STYLE_FOOTER)
    return "\n".join(parts)


def bg_entry(
    bg_id: str,
    description: str,
    scenes: list[str],
    prompt: str,
    continuity_notes: list[str],
    *,
    reused_from: str | None = None,
    background_exclusions: list[str] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "background_id": bg_id,
        "suggested_filename": f"{bg_id}.png",
        "description": description,
        "scenes": scenes,
        "aspect_ratio": "16:9",
        "recommended_resolution": {"width": 1536, "height": 864},
        "prompt": prompt,
        "negative_prompt": (
            "characters, people, animals, dragons, crowd, silhouettes, faces, readable text, "
            "logo, watermark, sign, live-action, photorealistic, 3D render, blurry, low quality"
        ),
        "continuity_notes": continuity_notes,
    }
    if reused_from:
        entry["reused_from_v2"] = reused_from
    if background_exclusions:
        entry["background_exclusions"] = background_exclusions
    return entry


BG_PROMPT_HEADER = (
    "High-quality feature-film animation background plate matching the exact visual style, "
    "line quality, color palette and rendering finish of the supplied character references. "
    "Ocean fantasy animated film aesthetic.\n\n"
)

BACKGROUNDS: dict[str, dict[str, Any]] = {
    "BG_EP01_STORM_SEA_SURFACE_NIGHT": bg_entry(
        "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "Storm-tossed night ocean surface only. Giant waves, lightning, rain. No underwater ruins visible.",
        ["SC01-001"],
        BG_PROMPT_HEADER
        + "A vast storm-tossed night ocean surface. Foreground: churning dark waves with white foam and rain streaks, clear open water space at center. "
        "Middle distance: towering wave walls under black storm clouds. Background: lightning-lit cloud mass, distant horizon. "
        "Eye-level wide composition facing open sea, 16:9 cinematic framing. Cold moonless storm lighting with cool-white lightning flashes from upper left, deep blue-black sea palette.\n\n"
        "Hand-painted animated ocean background, cinematic depth, violent weather atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Storm night palette only — surface layer", "Open central water for distant glow placement", "Lightning from upper left"],
        reused_from="BG_EP01_STORM_SEA_SURFACE_NIGHT (v2 approved)",
    ),
    "BG_EP01_DEEP_SEA_RUINS_NIGHT": bg_entry(
        "BG_EP01_DEEP_SEA_RUINS_NIGHT",
        "Deep underwater ruins of an ancient dragon palace. Collapsed coral pillar, bioluminescent blue accents, drifting marine snow.",
        ["SC01-001"],
        BG_PROMPT_HEADER
        + "Deep underwater environment beneath a storm sea. Foreground: open drifting water with marine snow particles and clear performance space. "
        "Middle distance: a cracked ancient coral palace pillar with bioluminescent blue veins, slowly crumbling. Background: dark teal abyss with faint silhouettes of more ruined coral architecture receding into depth.\n\n"
        "Eye-level to slight downward angle wide composition, 16:9 cinematic framing. Cold cyan ambient underwater fill, soft blue bioluminescence on coral, no surface storm visible.\n\n"
        "Hand-painted animated deep-sea background, sacred ruined kingdom atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Deep sea only — no storm surface", "Central open water for small dragon placement", "Blue bioluminescent coral accents"],
        reused_from="BG_EP01_DEEP_SEA_RUINS_NIGHT (v2 approved)",
    ),
    "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY": bg_entry(
        "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY",
        "Deep underwater corridor with clear diagonal escape path. No black tide, no shadow creatures, no characters.",
        ["SC01-001"],
        BG_PROMPT_HEADER
        + "A deep underwater corridor beneath a storm sea. Foreground: teal water with open diagonal ascent path along a faint blue light beam. "
        "Middle distance: clear open water channel with faint ruined coral edges at sides. Background: dark abyss below with no living black water mass.\n\n"
        "Eye-level medium-wide composition angled slightly upward, 16:9 cinematic framing. Cold cyan ambient light from above-left, deep teal abyss below.\n\n"
        "Hand-painted animated underwater background, strong depth separation, ominous but empty corridor.\n\n"
        "Clean empty background plate. No black tide, no shadow creatures, no dragons, no characters, no crowds, no silhouettes, no faces, no readable signs, text, logos or watermarks.",
        ["Empty corridor — Black Tide rendered as Object Reference only", "Blue ascent diagonal preserved", "No living black water in plate"],
        background_exclusions=["Black Tide", "shadow creatures", "dragons", "characters"],
    ),
    "BG_EP01_MIR_VISION_PALACE_RUINS": bg_entry(
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Surreal vision space: broken dragon palace gate, ruined halls, sleeping giant dragon shadows, black abyss.",
        ["SC01-001", "SC01-003", "SC01-005"],
        BG_PROMPT_HEADER
        + "A surreal vision version of a collapsed dragon palace interior and abyss. Foreground: floating debris and drifting dust motes with open central space. "
        "Middle distance: broken palace gate, ruined hall columns, enormous sleeping dragon shadows curled in darkness without clear faces. Background: endless black abyss fading into void.\n\n"
        "Eye-level wide composition with slight dutch unsettling tilt, 16:9 cinematic framing. Cold blue memory-light with deep black void, soft fog, dreamlike desaturation.\n\n"
        "Hand-painted animated vision background, nightmare memory atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Vision/dream palette — not physical cave or house", "Giant dragon shadows only as silhouettes", "Reused for S#1 vision, S#3 resonance vision, S#5 nightmare"],
        reused_from="BG_EP01_MIR_VISION_PALACE_RUINS (v2 approved)",
    ),
    "BG_EP01_COASTAL_VILLAGE_MORNING": bg_entry(
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Post-storm morning coastal village work shore with wet breakwater and distant cave cliff.",
        ["SC01-002"],
        BG_PROMPT_HEADER
        + "A small coastal fishing village work shore on the morning after a storm. Foreground: wet stone breakwater with clear open standing area, scattered wet rope at edges. "
        "Middle distance: overturned boats, tangled nets, broken wood on damp sand, villagers' repair activity spaces left empty. Background: soft post-storm sky, calm sea horizon, distant cliff with cave entrance hint.\n\n"
        "Eye-level medium-wide composition from breakwater facing sea, 16:9 cinematic framing. Soft diffused morning sunlight from frame right, cool blue bounce on wet stone.\n\n"
        "Detailed hand-painted animated village background — NOT photorealistic.\n\n"
        "Clean empty background plate. No characters, people, animals, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Hand-painted animation style matching character refs", "Breakwater center clear", "Cave cliff visible far background right"],
        reused_from="BG_EP01_COASTAL_VILLAGE_MORNING (v2 — style redo required)",
    ),
    "BG_EP01_COASTAL_CAVE_INTERIOR": bg_entry(
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Narrow wet coastal cave interior with shallow seawater and blue glow from depth.",
        ["SC01-003"],
        BG_PROMPT_HEADER
        + "A narrow wet coastal cave interior beneath sea cliffs. Foreground: shallow seawater over uneven rock with reflective ripples and clear central approach path. "
        "Middle distance: damp stone walls with droplets, rocky crevices, soft blue glow from deeper cave. Background: tunnel receding into shadow with mystical blue light source.\n\n"
        "Eye-level medium composition looking into cave depth, 16:9 cinematic framing. Cool blue-teal ambient from cave interior, faint daylight hint behind camera.\n\n"
        "Hand-painted animated cave environment, moist atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Wet cave palette", "Central floor for Lua and Young Mir", "Blue glow stronger toward depth"],
        reused_from="BG_EP01_COASTAL_CAVE_INTERIOR (v2 approved)",
    ),
    "BG_EP01_LUA_HOUSE_INTERIOR_DAY": bg_entry(
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Lua's small worn coastal house interior by day. Bed, table, water basin, shells, dried fish, net.",
        ["SC01-004"],
        BG_PROMPT_HEADER
        + "A small worn coastal house interior during daytime. Foreground: wooden floor with open center space, shallow water basin at side. "
        "Middle distance: simple wooden bed, small table with dried fish and shells, rolled fishing net, clay water container, cloth by window. Background: small window with warm daylight streaming in, modest wooden walls.\n\n"
        "Eye-level medium-wide interior composition, 16:9 cinematic framing. Warm daylight from window frame left, cozy humble atmosphere.\n\n"
        "Hand-painted animated interior background, lived-in props.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Humble wooden interior", "Water basin placement for Mir", "Open center floor"],
        reused_from="BG_EP01_LUA_HOUSE_INTERIOR_DAY (v2 approved)",
    ),
    "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE": bg_entry(
        "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE",
        "Stylized imagined village rejection space — desaturated fearful overlay suggesting village shore without showing distinct adult faces.",
        ["SC01-004"],
        BG_PROMPT_HEADER
        + "A stylized imagined coastal village shore seen as a fearful mental overlay. Foreground: open wooden floor space blending into ghostly sand at edges, no distinct people. "
        "Middle distance: blurred suggestion of village baskets, rope and shore without readable faces or identifiable villagers. Background: washed-out grey-blue sky and sea, desaturated nightmare tint over humble coastal shapes.\n\n"
        "Eye-level medium composition, 16:9 cinematic framing. Cold desaturated light with faint red anxiety tint, dreamlike soft edges.\n\n"
        "Hand-painted animated imagination background, clearly not the literal house room but emotionally connected.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Imagined scene — adult voices are off-screen only", "Desaturated overlay distinct from literal house day bg", "Open center for Lua protecting Mir"],
    ),
    "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT": bg_entry(
        "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "Same Lua house interior at night. Bed, basin, window with night sea view. Layout matches day variant.",
        ["SC01-005"],
        BG_PROMPT_HEADER
        + "The same small coastal house interior at night with identical layout to the daytime variant. Foreground: dim wooden floor, shallow water basin at same side position. "
        "Middle distance: wooden bed in same position, small table, water container, window with night sea view. Background: dark night sky and faint ocean through window.\n\n"
        "Eye-level medium-wide interior composition, 16:9 cinematic framing. Low warm interior fill mixed with cool blue moonlight from window frame right.\n\n"
        "Hand-painted animated night interior, exact room layout continuity with day variant.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Same layout as BG_EP01_LUA_HOUSE_INTERIOR_DAY", "Window faces night sea for jellyfish beat", "Bed and basin positions unchanged"],
        reused_from="BG_EP01_LUA_HOUSE_INTERIOR_NIGHT (v2 — layout continuity redo required)",
    ),
    "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW": bg_entry(
        "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW",
        "Night ocean viewed from Lua's house window height. Empty calm sea surface, no jellyfish or creatures.",
        ["SC01-005"],
        BG_PROMPT_HEADER
        + "Night ocean viewed from a slightly elevated coastal house window perspective. Foreground: minimal window frame edge, open view space. "
        "Middle distance: dark calm sea surface with gentle ripples, completely empty of creatures. Background: deep night sky with faint stars and distant horizon.\n\n"
        "Eye-level to slight high-angle composition through optional window framing at edges, 16:9 cinematic framing. Cool blue moonlight on sea, unnaturally still atmosphere.\n\n"
        "Hand-painted animated night seascape background, ominous quiet atmosphere.\n\n"
        "Clean empty background plate. No jellyfish, no sea creatures, no characters, no dragons, no crowds, no silhouettes, no faces, no readable signs, text, logos or watermarks.",
        ["Empty night sea — Black Jellyfish rendered as Object Reference only", "View matches Lua house window direction", "Ocean unnaturally still"],
        background_exclusions=["Black Jellyfish", "sea creatures", "characters"],
    ),
}

SHELL_PROP_GENERATION = {
    "required": True,
    "asset_role": "interactive_prop",
    "suggested_filename": "PROP_MIR_COMFORT_SHELL.png",
    "prompt": (
        "High-quality feature-film animation prop reference on a plain neutral background. "
        "A single small coastal seashell with a smooth curved surface, pale cream and soft pink tones, "
        "subtle spiral ridges and a slightly worn edge from village use. Three-quarter view showing "
        "both the outer curve and inner lip. Hand-painted stylized animation finish matching the "
        "Raising a Dragon character references. No character hands, no table, no background scene."
    ),
    "negative_prompt": (
        "character, hand, person, dragon, table, room, live-action, photorealistic, text, watermark, "
        "multiple shells, broken shell, blurry, low quality"
    ),
    "recommended_reference_view": "three-quarter view on plain neutral background",
    "affected_clips": ["SC01-004_02"],
    "reason": (
        "No dedicated shell reference image exists in RaisingaDragonSeason01/. Mir licks and hugs "
        "the shell in close-up; user must decide whether to generate this interactive_prop reference "
        "or accept background-table shell with reduced consistency."
    ),
}


def clip(
    scene_id: str,
    clip_id: str,
    sequence: int,
    seconds: float,
    bg_id: str,
    bg_desc: str,
    refs: list[dict[str, Any]],
    relay_segments: list[dict[str, Any]],
    dialogue: list[dict[str, Any]],
    continuity: dict[str, Any],
    global_prompt: str,
    *,
    episode_id: str = "EP01",
    scenario_span: str,
    narrative_purpose: str,
    shot_type: str,
    summary: str,
    previous_clip: str | None,
    next_clip: str | None,
    status: str = "awaiting_background",
    warnings: list[str] | None = None,
    unresolved: list[str] | None = None,
    review_flags: dict[str, bool] | None = None,
    required_assets: list[dict[str, Any]] | None = None,
    asset_roles: dict[str, str] | None = None,
    background_exclusions: list[str] | None = None,
    reference_consistency_notes: list[str] | None = None,
    prop_generation: dict[str, Any] | None = None,
    source_evidence: list[str] | None = None,
    include_character_review: bool = False,
) -> dict[str, Any]:
    bg = BACKGROUNDS[bg_id]
    flags = review_flags or {}
    review: dict[str, Any] = {
        "scenario_consistent": flags.get("scenario_consistent", True),
        "dialogue_preserved": flags.get("dialogue_preserved", True),
        "reference_mapping_valid": flags.get("reference_mapping_valid", True),
        "duration_valid": flags.get("duration_valid", True),
        "animation_style_preserved": flags.get("animation_style_preserved", True),
        "warnings": warnings or [],
        "unresolved_questions": unresolved or [],
        "background_generation_valid": True,
    }
    if include_character_review:
        review["character_review"] = CHARACTER_REVIEW.copy()

    payload: dict[str, Any] = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "episode_id": episode_id,
        "scene_id": scene_id,
        "clip_id": clip_id,
        "sequence": sequence,
        "status": status,
        "workflow": "msr_v3",
        "fps": 24,
        "resolution": {"width": 1280, "height": 704},
        "requested_seconds": seconds,
        "estimated_actual_seconds": seconds,
        "estimated_actual_frames": int(seconds * 24),
        "previous_clip": previous_clip,
        "next_clip": next_clip,
        "scenario_source": SCENARIO,
        "scenario_source_span": scenario_span,
        "narrative_purpose": narrative_purpose,
        "shot_type": shot_type,
        "references": refs,
        "background": {
            "status": "missing",
            "background_id": bg_id,
            "source_path": None,
            "description": bg_desc,
        },
        "continuity": continuity,
        "global_prompt": global_prompt,
        "relay_segments": relay_segments,
        "dialogue": dialogue,
        "review": review,
        "background_generation": {
            "required": True,
            "suggested_filename": bg["suggested_filename"],
            "aspect_ratio": bg["aspect_ratio"],
            "recommended_resolution": bg["recommended_resolution"],
            "prompt": bg["prompt"],
            "negative_prompt": bg["negative_prompt"],
            "continuity_notes": bg["continuity_notes"],
        },
    }
    if required_assets:
        payload["required_assets"] = required_assets
    if asset_roles:
        payload["asset_roles"] = asset_roles
    if background_exclusions:
        payload["background_exclusions"] = background_exclusions
    if reference_consistency_notes:
        payload["reference_consistency_notes"] = reference_consistency_notes
    if prop_generation:
        payload["prop_generation"] = prop_generation
    if source_evidence:
        payload["source_evidence"] = source_evidence
    return {"summary": summary, "payload": payload}


CLIPS: list[dict[str, Any]] = []

# --- SC01-001 (5 clips, 90s) ---
CLIPS.append(
    clip(
        "SC01-001", "SC01-001_01", 1, 16,
        "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "Storm night ocean surface. Waves, lightning, rain. Distant blue pulse under water.",
        [ref("young_mir", 1)],
        [
            relay(1, 6, "A violent storm night ocean fills the frame with giant waves, lightning forks and diagonal rain. The camera holds wide on churning black water with no character visible yet.", beat_type="establishing"),
            relay(2, 5, "Far below the waves, a tiny blue bioluminescent pulse flickers once, then again — distant and fragile against the storm. The camera slowly tilts downward toward the glow without revealing its source.", beat_type="anticipation"),
            relay(3, 5, "The camera continues descending toward the water surface as thunder rolls. The blue pulse brightens slightly beneath a wave trough. The shot holds on open dark water ready to plunge deeper.", beat_type="transition"),
        ],
        [],
        {"start_state": "Night storm sea, no visible characters.", "end_state": "Camera descending toward distant underwater blue pulse.", "carry_to_next": ["Storm palette", "Distant blue glow location", "Night time"]},
        build_global_prompt(
            "EP01 S#1 Cold open", "Storm sea surface establishing",
            [("young_mir", 1)],
            ["Storm night ocean surface only", "Lightning from upper left", "Distant blue glow under waves"],
            lighting="Cold moonless storm with cool-white lightning flashes from upper left, deep blue-black sea palette.",
            consistency_notes=["Young Mir reference included for MSR pipeline minimum; character not visible on screen in this clip."],
        ),
        scenario_span="L109-L118", narrative_purpose="Establish pursuit mystery — something glows beneath the storm.",
        shot_type="Wide establishing", summary="EP01 S#1 opening — storm night sea and distant blue glow beneath the waves.",
        previous_clip=None, next_clip="SC01-001_02",
        warnings=["Young Mir reference included for MSR pipeline minimum; character not visible on screen in this clip."],
        source_evidence=["Scenario L109-L115 storm open", "L117-L118 distant blue glow"],
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_02", 2, 20,
        "BG_EP01_DEEP_SEA_RUINS_NIGHT",
        "Deep sea dragon palace ruins. Collapsed coral pillar. Young wounded Mir revealed.",
        [ref("young_mir", 1)],
        [
            relay(1, 5, "Deep underwater ruins fill the frame. A sacred ancient coral pillar cracks slowly while marine snow drifts like snowflakes through cold blue-teal ambient light.", beat_type="establishing"),
            relay(2, 6, "Within a faint blue glow, Young Mir (Picture 1) becomes visible — small blue-silver body, wet scales, short horns, fin-like wings, tail crystal and chest wave mark. He is battered and half-conscious.", beat_type="reveal"),
            relay(3, 5, "Young Mir's body tumbles weakly in the current. His eyes remain half closed and his tail crystal flickers weakly. The camera moves closer with gentle handheld drift.", beat_type="physical_state"),
            relay(4, 4, "Young Mir tries to orient upward but lacks strength. The shot holds on his vulnerable floating posture facing the blue diagonal above, ready for pursuit.", beat_type="transition"),
        ],
        [],
        {"start_state": "Deep sea ruins, pillar crumbling.", "end_state": "Young Mir revealed, wounded, drifting weakly.", "carry_to_next": ["Young Mir wounded state", "Deep sea ruins", "Blue glow on Mir"]},
        build_global_prompt(
            "EP01 S#1 Cold open", "Deep sea ruins — Young Mir revealed",
            [("young_mir", 1)],
            ["Collapsed coral palace pillar", "Deep teal abyss", "Bioluminescent blue accents"],
            lighting="Cold cyan ambient underwater fill with soft blue bioluminescence on coral.",
        ),
        scenario_span="L119-L137", narrative_purpose="Reveal the chased creature without naming him.",
        shot_type="Medium reveal", summary="EP01 S#1 — deep sea ruins and wounded Young Mir revealed in blue glow.",
        previous_clip="SC01-001_01", next_clip="SC01-001_03",
        source_evidence=["Scenario L119-L125 descent to deep sea", "L127-L137 Young Mir revealed wounded"],
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_03", 3, 18,
        "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY",
        "Deep sea corridor. Black Tide pursues Mir upward. Tail crystal rescue flash.",
        [ref("young_mir", 1), ref("black_tide", 2)],
        [
            relay(1, 5, "Below Young Mir (Picture 1), the Black Tide (Picture 2) rises through the deep corridor — a living supernatural mass of black water with hand-like and mouth-like shadow shapes briefly forming and dissolving within it.", beat_type="anticipation"),
            relay(2, 5, "Young Mir attempts to climb along a faint blue diagonal beam toward the surface. His fins tremble but his body barely moves against the current while the Black Tide (Picture 2) gains ground below.", beat_type="action"),
            relay(3, 4, "Young Mir's tail-end water-drop crystal flashes brightly once — like a rescue signal and a last shield. The Black Tide (Picture 2) recoils slightly from the burst of blue light.", beat_type="consequence"),
            relay(4, 4, "Young Mir's vision wavers. The camera shudders slightly and holds on his trembling pupil reflecting blue light and black shadow, ready for memory vision.", beat_type="transition"),
        ],
        [],
        {"start_state": "Mir weak in deep water.", "end_state": "Crystal flashed; vision wavering.", "carry_to_next": ["Black pursuit active", "Tail crystal activated", "Mir weakness"]},
        build_global_prompt(
            "EP01 S#1 Cold open", "Black Tide pursuit in empty deep corridor",
            [("young_mir", 1), ("black_tide", 2)],
            ["Deep underwater corridor with blue ascent diagonal", "Empty corridor plate — no black tide in background", "Faint ruined coral edges at sides"],
            lighting="Cold cyan ambient from above-left, deep teal abyss below.",
            consistency_notes=["Black Tide (Picture 2) is the only living black water in frame — not duplicated in background plate."],
        ),
        scenario_span="L139-L149", narrative_purpose="Show Mir is hunted and nearly powerless.",
        shot_type="Action suspense", summary="EP01 S#1 — Black Tide pursues Mir; tail crystal flashes.",
        previous_clip="SC01-001_02", next_clip="SC01-001_04",
        required_assets=[{"asset_id": "ENTITY_BLACK_TIDE", "role": "dynamic_entity", "source_path": REF_PATHS["black_tide"], "reference_required": True, "affected_relay_segments": [1, 2, 3]}],
        asset_roles={"young_mir": "character", "black_tide": "dynamic_entity"},
        background_exclusions=["Black Tide", "shadow creatures"],
        reference_consistency_notes=["Background plate must not contain Black Tide — Picture 2 handles all black water movement."],
        source_evidence=["Scenario L139-L149 black current pursuit and crystal flash"],
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_04", 4, 20,
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Mir's shaken vision: broken palace, sleeping dragon shadows, Deep Sea King voice.",
        [ref("young_mir", 1)],
        [
            relay(1, 5, "The frame drifts shakily through a black abyss past a broken palace gate and ruined halls. Enormous sleeping dragon shadows curl in darkness without revealing faces.", beat_type="vision_establishing"),
            relay(2, 5, "Young Mir's eye fills part of the frame. His pupil trembles while reflected memory images slide across it.", beat_type="anticipation"),
            relay(3, 5, "A disembodied low voice reverberates through the vision with no visible mouth and says in natural Korean, \"기억하지 마라.\" Young Mir's pupil shudders.", beat_type="dialogue"),
            relay(4, 5, "The same disembodied low voice says in natural Korean, \"그러면 아프지 않다.\" Young Mir trembles in fear as the vision begins tearing away into storm light above.", beat_type="reaction"),
        ],
        [
            {"speaker": "Deep Sea King", "text": "기억하지 마라.", "segment_order": 3},
            {"speaker": "Deep Sea King", "text": "그러면 아프지 않다.", "segment_order": 4},
        ],
        {"start_state": "Mir vision wavering.", "end_state": "Deep Sea King words delivered; fear peak.", "carry_to_next": ["Vision memory tone", "Deep Sea King voice", "Upward escape motivation"]},
        build_global_prompt(
            "EP01 S#1 Cold open", "Mir vision — palace ruins memory",
            [("young_mir", 1)],
            ["Surreal broken palace vision space", "Sleeping dragon shadows as silhouettes only", "Black abyss"],
            lighting="Cold blue memory-light with deep black void, soft fog, dreamlike desaturation.",
        ),
        scenario_span="L151-L171", narrative_purpose="Plant Deep Sea King suppression — forget to avoid pain.",
        shot_type="Subjective vision montage", summary="EP01 S#1 — Mir's vision of ruined palace and Deep Sea King voice.",
        previous_clip="SC01-001_03", next_clip="SC01-001_05",
        source_evidence=["Scenario L151-L171 palace vision and Deep Sea King voice"],
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_05", 5, 16,
        "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "Mir's last push to storm surface; blue glow swept toward coast.",
        [ref("young_mir", 1)],
        [
            relay(1, 5, "Young Mir pushes upward with last strength through churning water toward the storm-lit surface. His small body struggles against the current.", beat_type="action"),
            relay(2, 6, "The camera breaks surface into storm night sea — rain, lightning and foam. A small blue glow is carried in the waves, not yet identifiable as a creature.", beat_type="transition"),
            relay(3, 5, "The blue glow drifts far toward a coastal horizon. Mir's identity stays unclear. The shot holds on the ominous sense that something chased is washing ashore.", beat_type="closing"),
        ],
        [],
        {"start_state": "Mir fleeing memory upward.", "end_state": "Blue glow drifting toward coast in storm.", "carry_to_next": ["Storm morning follows", "Blue glow toward cave coast", "Chase unresolved"]},
        build_global_prompt(
            "EP01 S#1 Cold open", "Ascent to storm surface",
            [("young_mir", 1)],
            ["Storm sea surface return", "Small blue glow in waves", "Coastal direction implied"],
            lighting="Cold storm night with lightning flashes and rain streaks.",
        ),
        scenario_span="L173-L181", narrative_purpose="Close cold open on mystery — something hunted reaches the coast.",
        shot_type="Wide transition", summary="EP01 S#1 end — Mir ascends; blue glow swept toward coast.",
        previous_clip="SC01-001_04", next_clip="SC01-002_01",
        source_evidence=["Scenario L173-L181 ascent and coastal drift"],
    )
)

# --- SC01-002 (2 clips, 48s) ---
CLIPS.append(
    clip(
        "SC01-002", "SC01-002_01", 1, 22,
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Post-storm village morning. Lua spear fail. Village children mock.",
        [ref("lua", 1), ref("child1", 2), ref("child2", 3), ref("spear", 4)],
        [
            relay(1, 5, "The shot holds in a medium-wide view of the wet breakwater on a post-storm coastal village morning. Overturned boats, tangled nets and broken wood line the damp shore while repair spaces remain empty.", beat_type="establishing"),
            relay(2, 6, "Lua (Picture 1) plants her feet apart and grips her fixed fishing spear (Picture 4) with both hands. She narrows her eyes at a small fish shadow beneath the shallow water and slowly raises the spear over her shoulder.", beat_type="preparation"),
            relay(3, 6, "Lua thrusts Picture 4 downward too early. The fish darts away and a sharp splash hits her face. She freezes with both hands still wrapped around the same spear. Village Child 1 (Picture 2) points toward the empty water and says in natural Korean, \"또 놓쳤다!\"", beat_type="action"),
            relay(4, 5, "Village Child 2 (Picture 3) laughs and says in natural Korean, \"루아 누나는 바다랑 안 맞아!\" Lua flushes with anger, still gripping Picture 4, and snaps back in natural Korean, \"안 맞긴 뭐가 안 맞아!\"", beat_type="dialogue"),
        ],
        [
            {"speaker": "Village Child 1", "text": "또 놓쳤다!", "segment_order": 3},
            {"speaker": "Village Child 2", "text": "루아 누나는 바다랑 안 맞아!", "segment_order": 4},
            {"speaker": "Lua", "text": "안 맞긴 뭐가 안 맞아!", "segment_order": 4},
        ],
        {"start_state": "Morning after storm village.", "end_state": "Lua angry at mocking children.", "carry_to_next": ["Lua wet soon", "Spear in hand", "Breakwater location"]},
        build_global_prompt(
            "EP01 S#2 Village morning", "Lua spear failure and mockery",
            [("lua", 1), ("child1", 2), ("child2", 3), ("spear", 4)],
            ["Post-storm village shore", "Wet breakwater", "Morning soft light"],
            lighting="Soft diffused morning sunlight from frame right, cool blue bounce on wet stone.",
            consistency_notes=["Lua keeps the same fishing spear (Picture 4) throughout all spear clips."],
        ),
        scenario_span="L187-L233", narrative_purpose="Introduce Lua rejected by the sea; Village Child 1 speaks '또 놓쳤다!'",
        shot_type="Character introduction", summary="EP01 S#2 — village morning, Lua misses fish, children mock.",
        previous_clip="SC01-001_05", next_clip="SC01-002_02",
        required_assets=[{"asset_id": "PROP_LUA_SPEAR", "role": "hero_prop", "source_path": REF_PATHS["spear"], "reference_required": True, "affected_relay_segments": [2, 3, 4]}],
        asset_roles={"lua": "character", "child1": "character", "child2": "character", "spear": "hero_prop"},
        background_exclusions=["Lua's fishing spear"],
        source_evidence=["Scenario L187-L233 village morning spear fail"],
    )
)

CLIPS.append(
    clip(
        "SC01-002", "SC01-002_02", 2, 26,
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Lua slips, old fisherman warns, cave blue glow, Lua runs.",
        [ref("lua", 1), ref("old_fisherman", 2), ref("spear", 3)],
        [
            relay(1, 3, "Lua (Picture 1) slips on the wet breakwater and falls into shallow water, still holding her fishing spear (Picture 3). Village children laugh louder off-screen behind her. She pushes wet hair from her face and forces bravado.", beat_type="physical_consequence"),
            relay(2, 5, "Lua stands in the shallows gripping Picture 3 and says in natural Korean, \"방금 건 일부러 빠진 거야.\" After a brief held silence she adds in natural Korean, \"수심 확인.\"", beat_type="dialogue"),
            relay(3, 5, "The Old Fisherman (Picture 2) approaches calmly without mocking. He says in natural Korean, \"루아야.\" Lua straightens and answers in natural Korean, \"네!\"", beat_type="dialogue"),
            relay(4, 5, "The Old Fisherman (Picture 2) says in natural Korean, \"바다는 고집으로 되는 게 아니다.\" Lua's expression hardens as she grips her fishing spear (Picture 3).", beat_type="dialogue"),
            relay(5, 5, "The Old Fisherman (Picture 2) looks toward the cliff cave and says in natural Korean, \"오늘은 동굴 쪽 가지 마라.\" After a pause he adds in natural Korean, \"폭풍 뒤에는 뭐가 밀려올지 몰라.\" Lua does not answer.", beat_type="dialogue"),
            relay(6, 3, "A faint blue flicker pulses in the far cave. Lua's eyes widen. Her internal voice-over says in natural Korean, \"가라면 가지 말아야 하는데.\" Then in natural Korean, \"저렇게 빛나면 가야지.\" She runs toward the cave still gripping Picture 3.", beat_type="exit"),
        ],
        [
            {"speaker": "Lua", "text": "방금 건 일부러 빠진 거야.", "segment_order": 2},
            {"speaker": "Lua", "text": "수심 확인.", "segment_order": 2},
            {"speaker": "Old Fisherman", "text": "루아야.", "segment_order": 3},
            {"speaker": "Lua", "text": "네!", "segment_order": 3},
            {"speaker": "Old Fisherman", "text": "바다는 고집으로 되는 게 아니다.", "segment_order": 4},
            {"speaker": "Old Fisherman", "text": "오늘은 동굴 쪽 가지 마라.", "segment_order": 5},
            {"speaker": "Old Fisherman", "text": "폭풍 뒤에는 뭐가 밀려올지 몰라.", "segment_order": 5},
            {"speaker": "Lua (internal)", "text": "가라면 가지 말아야 하는데.", "segment_order": 6},
            {"speaker": "Lua (internal)", "text": "저렇게 빛나면 가야지.", "segment_order": 6},
        ],
        {"start_state": "Lua angry on breakwater.", "end_state": "Lua running to cave.", "carry_to_next": ["Lua wet clothes", "Spear", "Drawn to blue cave glow"]},
        build_global_prompt(
            "EP01 S#2 Village morning", "Fisherman warning and cave pull",
            [("lua", 1), ("old_fisherman", 2), ("spear", 3)],
            ["Same village breakwater", "Distant cave cliff visible"],
            lighting="Soft post-storm morning light with cool wet stone reflections.",
            consistency_notes=["Lua carries the same fishing spear (Picture 3) when she runs toward the cave."],
        ),
        scenario_span="L235-L299", narrative_purpose="Foreshadow cave; establish Lua disobedience.",
        shot_type="Dialogue and exit", summary="EP01 S#2 — slip, fisherman warning, blue cave glow, Lua runs.",
        previous_clip="SC01-002_01", next_clip="SC01-003_01",
        required_assets=[{"asset_id": "PROP_LUA_SPEAR", "role": "hero_prop", "source_path": REF_PATHS["spear"], "reference_required": True, "affected_relay_segments": [1, 6]}],
        asset_roles={"lua": "character", "old_fisherman": "character", "spear": "hero_prop"},
        background_exclusions=["Lua's fishing spear"],
        source_evidence=["Scenario L235-L299 slip, fisherman warning, cave pull"],
    )
)

# --- SC01-003 (9 clips, 130s) — contact/vision separation A-F ---
CLIPS.append(
    clip(
        "SC01-003", "SC01-003_01", 1, 20,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua enters cave with spear, bluffs bravely, hears squeak.",
        [ref("lua", 1), ref("spear", 2)],
        [
            relay(1, 5, "A dark wet cave interior opens with dripping water, shallow seawater ripples and blue glow deeper inside. Lua (Picture 1) enters cautiously with her fishing spear (Picture 2) held forward.", beat_type="establishing"),
            relay(2, 5, "Lua tries to look fearless while clearly afraid. She steadies her breath and shifts her weight on wet rock, keeping Picture 2 angled toward the shadows.", beat_type="preparation"),
            relay(3, 6, "Lua calls out in natural Korean, \"나와라.\" After a brief pause she adds in natural Korean, \"내가 마을에서 제일 무서운 사람은 아니지만.\"", beat_type="dialogue"),
            relay(4, 4, "Lua finishes in natural Korean, \"상당히 귀찮은 사람이다.\" A tiny squeak comes from a deeper crevice. Lua freezes and her eyes widen with curiosity as she leans forward carefully.", beat_type="anticipation"),
        ],
        [
            {"speaker": "Lua", "text": "나와라.", "segment_order": 3},
            {"speaker": "Lua", "text": "내가 마을에서 제일 무서운 사람은 아니지만.", "segment_order": 3},
            {"speaker": "Lua", "text": "상당히 귀찮은 사람이다.", "segment_order": 4},
        ],
        {"start_state": "Lua enters coastal cave.", "end_state": "Lua heard squeak, curious.", "carry_to_next": ["Spear lowered soon", "Blue inner glow", "Lua alone"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Cave entry and bluff",
            [("lua", 1), ("spear", 2)],
            ["Wet cave interior", "Shallow water floor", "Blue glow from depth"],
            lighting="Cool blue-teal ambient from cave interior, faint daylight hint behind camera.",
        ),
        scenario_span="L305-L335", narrative_purpose="Build tension before Mir reveal.",
        shot_type="Suspense approach", summary="EP01 S#3 — Lua enters cave, bluffs, hears squeak.",
        previous_clip="SC01-002_02", next_clip="SC01-003_02",
        required_assets=[{"asset_id": "PROP_LUA_SPEAR", "role": "hero_prop", "source_path": REF_PATHS["spear"], "reference_required": True, "affected_relay_segments": [1, 2]}],
        asset_roles={"lua": "character", "spear": "hero_prop"},
        background_exclusions=["Lua's fishing spear"],
        source_evidence=["Scenario L305-L335 cave entry and bluff"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_02", 2, 20,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua discovers Young Mir, lowers spear, reaches out.",
        [ref("lua", 1), ref("young_mir", 2), ref("spear", 3)],
        [
            relay(1, 4, "Lua (Picture 1) peers into a crevice. Young Mir (Picture 2) is visible with short horns, blue-silver tail, wet scales and half-open eyes at frame right. Lua slowly lowers her fishing spear (Picture 3) to the wet stone.", beat_type="reveal"),
            relay(2, 4, "Lua (Picture 1) exhales shakily and says in natural Korean, \"방금 귀여웠는데?\" She stares at Young Mir (Picture 2) with wide brown eyes.", beat_type="dialogue"),
            relay(3, 5, "Lua whispers in natural Korean, \"너…\" After a held pause she adds in natural Korean, \"도마뱀은 아니지?\"", beat_type="dialogue"),
            relay(4, 4, "Young Mir (Picture 2) opens large clear eyes toward Lua — frightened but intelligent. Lua holds her breath, awed, and says in natural Korean, \"말도 안 돼.\"", beat_type="reaction"),
            relay(5, 3, "Lua (Picture 1) slowly extends her open human hand while Young Mir (Picture 2) tries to retreat but lacks strength, slipping on wet stone. Lua's face shifts from curiosity to worry. The shot holds on her outstretched hand.", beat_type="preparation"),
        ],
        [
            {"speaker": "Lua", "text": "방금 귀여웠는데?", "segment_order": 2},
            {"speaker": "Lua", "text": "너…", "segment_order": 3},
            {"speaker": "Lua", "text": "도마뱀은 아니지?", "segment_order": 3},
            {"speaker": "Lua", "text": "말도 안 돼.", "segment_order": 4},
        ],
        {"start_state": "Lua heard squeak.", "end_state": "Lua reaching toward Mir.", "carry_to_next": ["Mir weak on wet rock", "Spear down", "Mutual eye contact"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Discovery of Young Mir",
            [("lua", 1), ("young_mir", 2), ("spear", 3)],
            ["Same cave interior", "Crevice area", "Blue glow", "Lua at frame left, Young Mir at frame right"],
            lighting="Cool blue-teal cave ambient with soft glow from depth.",
            include_anatomy_separation=True,
        ),
        scenario_span="L337-L379", narrative_purpose="First meeting — wonder not battle.",
        shot_type="Discovery two-shot", summary="EP01 S#3 — Lua discovers Young Mir in crevice.",
        previous_clip="SC01-003_01", next_clip="SC01-003_03",
        include_character_review=True,
        required_assets=[{"asset_id": "PROP_LUA_SPEAR", "role": "hero_prop", "source_path": REF_PATHS["spear"], "reference_required": True, "affected_relay_segments": [1]}],
        asset_roles={"lua": "character", "young_mir": "character", "spear": "hero_prop"},
        background_exclusions=["Lua's fishing spear"],
        source_evidence=["Scenario L337-L379 Mir discovery"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_03", 3, 12,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "A — Approach and reassurance. Lua kneels, open hand, no contact yet.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 3, "Lua (Picture 1) lowers her fishing spear fully and slowly kneels at frame left. Young Mir (Picture 2) rests against wet stone at frame right. Clear visible space remains between their separate silhouettes.", beat_type="approach"),
            relay(2, 3, "Lua extends her open human hand low toward Young Mir, keeping her fingers relaxed and below his eye level. Young Mir watches the movement with wide blue eyes while keeping his small dragon wings close to his own body.", beat_type="reassurance"),
            relay(3, 3, "The camera holds in a medium two-shot so both separate silhouettes remain visible. Lua (Picture 1) says softly in natural Korean, \"야, 야. 괜찮아.\" then in natural Korean, \"안 잡아먹어.\"", beat_type="dialogue"),
            relay(4, 3, "Lua touches her own stomach and adds in natural Korean, \"나도 오늘 아침 못 먹었거든.\" Young Mir (Picture 2) keeps watching her fingers without moving closer.", beat_type="dialogue"),
        ],
        [
            {"speaker": "Lua", "text": "야, 야. 괜찮아.", "segment_order": 3},
            {"speaker": "Lua", "text": "안 잡아먹어.", "segment_order": 3},
            {"speaker": "Lua", "text": "나도 오늘 아침 못 먹었거든.", "segment_order": 4},
        ],
        {"start_state": "Lua hand extended toward Mir.", "end_state": "Lua reassuring; no contact yet.", "carry_to_next": ["Open hand offered", "Mir watching", "No magic yet"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Approach and reassurance — no contact",
            [("lua", 1), ("young_mir", 2)],
            ["Wet cave crevice", "Shallow water ripples", "Lua kneeling at frame left, Young Mir at frame right"],
            lighting="Soft blue cave glow from depth.",
            include_anatomy_separation=True,
        ),
        scenario_span="L385-L395", narrative_purpose="Contact beat A — approach without touching.",
        shot_type="Emotional two-shot", summary="EP01 S#3A — Lua kneels and reassures Young Mir without contact.",
        previous_clip="SC01-003_02", next_clip="SC01-003_04",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L385-L395 Lua reassures before contact"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_04", 4, 10,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "B — First contact. Young Mir weakly bites Lua's finger.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 4, "Young Mir (Picture 2) shifts his small dragon body forward by only a few centimeters and watches Lua's fingers. Lua (Picture 1) keeps her human hand steady and open.", beat_type="anticipation"),
            relay(2, 6, "Young Mir weakly closes his small dragon mouth around the tip of Lua's index finger and hangs on for support — clinging, not attacking. Lua's human hand remains clearly separate from Young Mir's scaled head and body. Lua flinches and says in natural Korean, \"악!\" The camera holds on the contact point without changing either character's anatomy.", beat_type="contact"),
        ],
        [{"speaker": "Lua", "text": "악!", "segment_order": 2}],
        {"start_state": "Lua hand offered, no contact.", "end_state": "Weak bite contact; no magic yet.", "carry_to_next": ["Finger contact", "Clinging not attack", "Lua realizes he needs help"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "First contact — weak bite",
            [("lua", 1), ("young_mir", 2)],
            ["Same cave crevice", "Close contact framing", "Separate human hand and dragon body"],
            lighting="Soft blue cave ambient.",
            include_anatomy_separation=True,
        ),
        scenario_span="L397-L405", narrative_purpose="Contact beat B — first physical contact only.",
        shot_type="Close contact", summary="EP01 S#3B — Young Mir weakly bites Lua's finger for support.",
        previous_clip="SC01-003_03", next_clip="SC01-003_05",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L397-L405 weak bite contact"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_05", 5, 12,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "C — Blood and resonance start. Marks appear on separate bodies.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 4, "A single drop of blood forms on Lua's human fingertip where Young Mir's small dragon mouth touched. Lua's human hand remains separate from Young Mir's dragon body.", beat_type="blood"),
            relay(2, 4, "The blood drop falls onto one broken scale on Young Mir's shoulder. Cave water ripples outward. A soft blue mark appears only on Lua's wrist.", beat_type="mark_lua"),
            relay(3, 4, "Young Mir's existing chest mark glows only on his own scaled chest. Both characters remain fully separate — Lua human with no wings, horns, scales or tail; Young Mir a small dragon with his own wings, horns, scales and tail.", beat_type="mark_mir"),
        ],
        [],
        {"start_state": "Weak bite contact.", "end_state": "Wrist and chest marks activated.", "carry_to_next": ["Wrist mark visible", "Chest mark glowing", "No vision yet"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Blood and resonance marks",
            [("lua", 1), ("young_mir", 2)],
            ["Cave interior", "Shallow water ripples", "Marks on separate bodies only"],
            lighting="Blue resonance glow building on marks.",
            include_anatomy_separation=True,
        ),
        scenario_span="L407-L425", narrative_purpose="Contact beat C — blood and mark activation.",
        shot_type="Resonance start", summary="EP01 S#3C — blood drop, wrist and chest marks appear.",
        previous_clip="SC01-003_04", next_clip="SC01-003_06",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L407-L425 blood and mark activation"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_06", 6, 10,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "D — Light connection between marks. No body fusion.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 5, "A thin line of blue light connects Lua's wrist mark and Young Mir's chest mark across the open space between their separate bodies. The light does not merge their silhouettes.", beat_type="connection"),
            relay(2, 5, "Lua (Picture 1) remains fully human with no wings, horns, scales or tail. Young Mir (Picture 2) remains a small blue-silver dragon with his own wings, horns, scales and tail. No body deformation or fusion occurs.", beat_type="separation_hold"),
        ],
        [],
        {"start_state": "Marks activated.", "end_state": "Blue connection line visible.", "carry_to_next": ["Connection line active", "Bodies separate", "Vision incoming"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Light connection between marks",
            [("lua", 1), ("young_mir", 2)],
            ["Cave interior", "Blue energy line between wrist and chest marks"],
            lighting="Pulsing blue resonance connecting two separate bodies.",
            include_anatomy_separation=True,
        ),
        scenario_span="L427-L435", narrative_purpose="Contact beat D — energy connection without fusion.",
        shot_type="Magic connection", summary="EP01 S#3D — blue light connects wrist and chest marks.",
        previous_clip="SC01-003_05", next_clip="SC01-003_07",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L427-L435 blue connection thread"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_07", 7, 16,
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "E — Palace vision separated from physical contact.",
        [ref("young_mir", 1)],
        [
            relay(1, 5, "The frame cuts to a surreal vision space — a collapsed dragon palace with broken gate, ruined halls and enormous sleeping dragon shadows curled in darkness without clear faces.", beat_type="vision_establishing"),
            relay(2, 5, "Black roots wrap around a fading blue heart-stone at the center of the ruined hall. No human Lua appears in this vision.", beat_type="vision_detail"),
            relay(3, 6, "The camera drifts through the nightmare memory space past sleeping dragon silhouettes and into black abyss. No physical contact between Lua and Young Mir is shown in this vision clip.", beat_type="vision_drift"),
        ],
        [],
        {"start_state": "Resonance connection active in cave.", "end_state": "Vision memory shown separately.", "carry_to_next": ["Palace ruins memory", "Sleeping dragon shadows", "Return to cave next"]},
        build_global_prompt(
            "EP01 S#3 Resonance vision", "Palace ruins vision — separated from contact",
            [("young_mir", 1)],
            ["Surreal collapsed dragon palace", "Sleeping dragon shadows as silhouettes", "Black roots on fading heart-stone", "No Lua in vision frame"],
            lighting="Cold blue memory-light with deep black void, dreamlike desaturation.",
            consistency_notes=["Vision clip uses separate background — no Lua+Mir physical contact repeated here."],
        ),
        scenario_span="L437-L441", narrative_purpose="Contact beat E — 용심 공명 vision separated from cave contact.",
        shot_type="Vision overlay", summary="EP01 S#3E — resonance palace vision, no contact.",
        previous_clip="SC01-003_06", next_clip="SC01-003_08",
        source_evidence=["Scenario L437-L441 resonance vision overlay"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_08", 8, 10,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "F — Return to reality. Lua checks wrist mark, Mir whimpers.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 5, "Lua (Picture 1) gasps back to reality in the cave, fully human with no dragon anatomy. She stares at the blue mark on her wrist.", beat_type="return"),
            relay(2, 5, "Young Mir (Picture 2) whimpers softly on the wet stone at frame right, remaining a separate small dragon. The blue connection light fades. Both silhouettes stay clearly separated in a medium two-shot.", beat_type="recovery"),
        ],
        [],
        {"start_state": "Vision fading.", "end_state": "Lua shock at wrist mark; Mir whimpering.", "carry_to_next": ["Wrist mark visible", "Mir weak", "Lua committed to help"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Return to reality after vision",
            [("lua", 1), ("young_mir", 2)],
            ["Cave interior returns to physical reality", "Lua at frame left, Young Mir at frame right"],
            lighting="Normal cave blue-teal ambient resumes.",
            include_anatomy_separation=True,
        ),
        scenario_span="L441-L445", narrative_purpose="Contact beat F — reality return.",
        shot_type="Recovery", summary="EP01 S#3F — Lua returns from vision, checks wrist mark.",
        previous_clip="SC01-003_07", next_clip="SC01-003_09",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L441-L445 return from vision"],
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_09", 9, 20,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua questions Mir, village voice, wraps and carries out.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 6, "Lua (Picture 1) breathes hard and says in natural Korean, \"방금…\" She looks at her wrist and asks in natural Korean, \"내가 본 거야?\" Young Mir (Picture 2) whimpers.", beat_type="dialogue"),
            relay(2, 4, "Lua asks in natural Korean, \"너 대체 뭐야?\" An off-screen voice from the cave mouth calls in natural Korean, \"루아! 거기 있냐?\" Lua panics and looks toward the exit.", beat_type="interruption"),
            relay(3, 5, "Young Mir crawls weakly toward Lua. She hesitates, then wraps him in part of her outer cloth and says in natural Korean, \"하.\" After a pause she adds in natural Korean, \"나 진짜 사고 쳤다.\"", beat_type="action"),
            relay(4, 5, "Lua cradles Young Mir and moves toward the cave mouth light. The camera follows from behind as she steps out of the cave shadow.", beat_type="exit"),
        ],
        [
            {"speaker": "Lua", "text": "방금…", "segment_order": 1},
            {"speaker": "Lua", "text": "내가 본 거야?", "segment_order": 1},
            {"speaker": "Lua", "text": "너 대체 뭐야?", "segment_order": 2},
            {"speaker": "Village person (off-screen)", "text": "루아! 거기 있냐?", "segment_order": 2},
            {"speaker": "Lua", "text": "하.", "segment_order": 3},
            {"speaker": "Lua", "text": "나 진짜 사고 쳤다.", "segment_order": 3},
        ],
        {"start_state": "Resonance just occurred.", "end_state": "Lua carrying Mir out of cave.", "carry_to_next": ["Mir wrapped in cloth", "Wrist mark hidden soon", "Lua committed"]},
        build_global_prompt(
            "EP01 S#3 Coastal cave", "Wrap and escape",
            [("lua", 1), ("young_mir", 2)],
            ["Cave interior to mouth light transition within same bg"],
            lighting="Blue inner glow fading toward daylight at cave mouth.",
            include_anatomy_separation=True,
        ),
        scenario_span="L443-L489", narrative_purpose="Lua chooses to steal Mir away.",
        shot_type="Escape beat", summary="EP01 S#3 — questions, village call, Lua carries Mir out.",
        previous_clip="SC01-003_08", next_clip="SC01-004_01",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L443-L489 wrap and escape"],
    )
)

# --- SC01-004 (4 clips, 74s) ---
CLIPS.append(
    clip(
        "SC01-004", "SC01-004_01", 1, 20,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Secret arrival home, reality check, water basin.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 5, "Lua (Picture 1) quietly closes the door of her small worn house and listens for outside sounds. Young Mir (Picture 2) peeks from wrapped cloth at frame right.", beat_type="establishing"),
            relay(2, 5, "Lua stares at Young Mir and says in natural Korean, \"진짜네.\" After a pause she adds in natural Korean, \"꿈이면 지금쯤 깨야 하는데.\"", beat_type="dialogue"),
            relay(3, 5, "Lua places Young Mir into the shallow water basin. He half-submerges and relaxes slightly while Lua watches amazed.", beat_type="care_action"),
            relay(4, 5, "Lua asks in natural Korean, \"너 물에서 자는 거야?\" Young Mir blinks. Lua sighs and says in natural Korean, \"좋겠다. 난 그러면 죽는데.\"", beat_type="dialogue"),
        ],
        [
            {"speaker": "Lua", "text": "진짜네.", "segment_order": 2},
            {"speaker": "Lua", "text": "꿈이면 지금쯤 깨야 하는데.", "segment_order": 2},
            {"speaker": "Lua", "text": "너 물에서 자는 거야?", "segment_order": 4},
            {"speaker": "Lua", "text": "좋겠다. 난 그러면 죽는데.", "segment_order": 4},
        ],
        {"start_state": "Lua enters house with Mir.", "end_state": "Mir resting in basin.", "carry_to_next": ["Basin setup", "Day interior", "Secret hiding"]},
        build_global_prompt(
            "EP01 S#4 Lua house day", "Secret arrival",
            [("lua", 1), ("young_mir", 2)],
            ["Small worn house day interior", "Water basin as environment prop", "Hidden from village"],
            lighting="Warm daylight from window frame left.",
            include_anatomy_separation=True,
        ),
        scenario_span="L495-L529", narrative_purpose="First shelter — secret custody begins.",
        shot_type="Interior domestic", summary="EP01 S#4 — home arrival, Mir in basin.",
        previous_clip="SC01-003_09", next_clip="SC01-004_02",
        include_character_review=True,
        warnings=["Water basin is environment_prop — shape may shift if Mir is placed inside in close-up."],
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L495-L529 secret arrival and basin"],
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_02", 2, 18,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Fish rejected, shell preference.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 4, "Lua (Picture 1) brings dried fish from the table and offers it gently to Young Mir (Picture 2) in the basin.", beat_type="preparation"),
            relay(2, 5, "Lua says in natural Korean, \"먹어.\" Young Mir recoils in disgust. Lua flusters and says in natural Korean, \"아니, 바다에서 왔잖아.\"", beat_type="dialogue"),
            relay(3, 4, "Lua adds in natural Korean, \"생선 안 먹어?\" Young Mir crawls toward a shell on the table instead.", beat_type="dialogue"),
            relay(4, 5, "Young Mir licks the shell and hugs it like treasure. Lua deadpans and says in natural Korean, \"입맛도 귀족이네.\" Young Mir calms holding the shell.", beat_type="reaction"),
        ],
        [
            {"speaker": "Lua", "text": "먹어.", "segment_order": 2},
            {"speaker": "Lua", "text": "아니, 바다에서 왔잖아.", "segment_order": 2},
            {"speaker": "Lua", "text": "생선 안 먹어?", "segment_order": 3},
            {"speaker": "Lua", "text": "입맛도 귀족이네.", "segment_order": 4},
        ],
        {"start_state": "Mir in basin calm.", "end_state": "Mir prefers shell over fish.", "carry_to_next": ["Shell prop", "Mir calmer", "Lua learning Mir's tastes"]},
        build_global_prompt(
            "EP01 S#4 Lua house day", "Feeding failed, shell comfort",
            [("lua", 1), ("young_mir", 2)],
            ["Same day house interior", "Table with shells and dried fish as environment props"],
            lighting="Warm daylight from window.",
            include_anatomy_separation=True,
        ),
        scenario_span="L531-L557", narrative_purpose="Show Mir is not ordinary; build comedy warmth.",
        shot_type="Domestic comedy", summary="EP01 S#4 — fish rejected, Mir loves shell.",
        previous_clip="SC01-004_01", next_clip="SC01-004_03",
        status="needs_confirmation",
        include_character_review=True,
        warnings=[
            "No dedicated shell reference image exists — Mir licks and hugs shell in close-up.",
            "Shell consistency depends on user decision: generate interactive_prop reference or accept background-table shell.",
            "Dried fish treated as incidental_prop — no Reference slot used.",
        ],
        unresolved=[
            "Should the comfort shell receive a dedicated interactive_prop Reference image for cross-episode consistency?",
        ],
        prop_generation=SHELL_PROP_GENERATION,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L531-L557 fish rejected, shell comfort"],
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_03", 3, 16,
        "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE",
        "Imagined village rejection — off-screen adult voices.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 4, "Lua (Picture 1) checks the mark on her wrist and tries to hide it with cloth. Young Mir (Picture 2) watches from the basin.", beat_type="preparation"),
            relay(2, 5, "The frame shifts to a desaturated overlay with ghostly village shore shapes at the edges. Imagined off-screen voices shout in natural Korean, \"불길하다!\" and in natural Korean, \"바다에 돌려보내!\" Young Mir flinches.", beat_type="imagination"),
            relay(3, 4, "Lua snaps back to reality and blocks Young Mir protectively, saying in natural Korean, \"안 돼.\"", beat_type="reaction"),
            relay(4, 3, "The imagination fades to normal house day lighting. Young Mir looks up at Lua trustingly. The shot holds on her protective posture.", beat_type="recovery"),
        ],
        [
            {"speaker": "Imagined adult (off-screen)", "text": "불길하다!", "segment_order": 2},
            {"speaker": "Imagined adult (off-screen)", "text": "바다에 돌려보내!", "segment_order": 2},
            {"speaker": "Lua", "text": "안 돼.", "segment_order": 3},
        ],
        {"start_state": "Lua hides wrist mark.", "end_state": "Lua decides to protect Mir.", "carry_to_next": ["Protection promise next clip", "Fear of village", "Imagined rejection memory"]},
        build_global_prompt(
            "EP01 S#4 imagined rejection", "Lua imagines village fear",
            [("lua", 1), ("young_mir", 2)],
            ["Stylized imagined village overlay", "Literal house returns after beat"],
            lighting="Cold desaturated overlay shifting back to warm house daylight.",
            include_anatomy_separation=True,
        ),
        scenario_span="L559-L579", narrative_purpose="Externalize Lua's fear of village rejection.",
        shot_type="Imagined sequence", summary="EP01 S#4 — imagined adults reject Mir; Lua refuses.",
        previous_clip="SC01-004_02", next_clip="SC01-004_04",
        include_character_review=True,
        warnings=["Basket in imagined scene is environment_prop — no separate Reference; form consistency not guaranteed."],
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L559-L579 imagined village rejection"],
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_04", 4, 20,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Promise to hide, water droplet, marks react.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 6, "Lua (Picture 1) clears her throat pretending to be adult and says in natural Korean, \"그러니까… 당분간 여기 있어.\" Young Mir (Picture 2) tilts his head.", beat_type="dialogue"),
            relay(2, 4, "Lua (Picture 1) continues in natural Korean, \"근데 밥값은 해야 돼.\" She points at the water jar on the table.", beat_type="dialogue"),
            relay(3, 4, "Lua (Picture 1) says in natural Korean, \"예를 들면.\" then in natural Korean, \"물 좀 데워준다든가?\" Young Mir (Picture 2) watches her with tilted head.", beat_type="dialogue"),
            relay(4, 3, "Young Mir (Picture 2) opens his small dragon mouth. Lua waits hopeful. Instead he creates one tiny water droplet that floats briefly.", beat_type="action"),
            relay(5, 3, "The droplet lands on Lua's forehead. She freezes with eyes closed and says in natural Korean, \"그래.\" then in natural Korean, \"가능성은 있다.\" Young Mir's chest mark and Lua's wrist mark flash together.", beat_type="reaction"),
        ],
        [
            {"speaker": "Lua", "text": "그러니까… 당분간 여기 있어.", "segment_order": 1},
            {"speaker": "Lua", "text": "근데 밥값은 해야 돼.", "segment_order": 2},
            {"speaker": "Lua", "text": "예를 들면.", "segment_order": 3},
            {"speaker": "Lua", "text": "물 좀 데워준다든가?", "segment_order": 3},
            {"speaker": "Lua", "text": "그래.", "segment_order": 5},
            {"speaker": "Lua", "text": "가능성은 있다.", "segment_order": 5},
        ],
        {"start_state": "Lua protecting Mir after imagination.", "end_state": "Marks react together; bond felt.", "carry_to_next": ["Hidden custody agreed", "Marks linked", "Night transition ahead"]},
        build_global_prompt(
            "EP01 S#4 Lua house day", "Hide promise and droplet",
            [("lua", 1), ("young_mir", 2)],
            ["Same day house interior", "Water jar as environment prop"],
            lighting="Warm daylight from window.",
            include_anatomy_separation=True,
        ),
        scenario_span="L581-L631", narrative_purpose="Secret pact and first tiny miracle.",
        shot_type="Warm character beat", summary="EP01 S#4 — hide promise, water droplet, marks flash.",
        previous_clip="SC01-004_03", next_clip="SC01-005_01",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L581-L631 hide promise and droplet"],
    )
)

# --- SC01-005 (4 clips, 70s) ---
CLIPS.append(
    clip(
        "SC01-005", "SC01-005_01", 1, 14,
        "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "Night house — Lua and Mir sleep, marks glow.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 5, "The dark quiet house interior at night fills the frame. Lua (Picture 1) sleeps in bed. Young Mir (Picture 2) curls in the water basin.", beat_type="establishing"),
            relay(2, 5, "A faint synchronized glow pulses from Young Mir's chest mark and Lua's wrist mark beneath her cloth. Their breathing slows in parallel.", beat_type="anticipation"),
            relay(3, 4, "Young Mir trembles in sleep. Lua's brow furrows in shared disturbance. The camera pushes slightly closer, ready to enter dream.", beat_type="transition"),
        ],
        [],
        {"start_state": "Night after first day together.", "end_state": "Both entering disturbed sleep.", "carry_to_next": ["Night interior", "Glowing marks", "Dream incoming"]},
        build_global_prompt(
            "EP01 S#5 Night", "Sleep setup",
            [("lua", 1), ("young_mir", 2)],
            ["Dark house night interior", "Bed and basin positions match day layout"],
            lighting="Low warm interior fill mixed with cool blue moonlight from window.",
            include_anatomy_separation=True,
        ),
        scenario_span="L637-L651", narrative_purpose="Bridge to shared nightmare.",
        shot_type="Quiet setup", summary="EP01 S#5 — night sleep, marks glow, trembling begins.",
        previous_clip="SC01-004_04", next_clip="SC01-005_02",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L637-L651 night sleep setup"],
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_02", 2, 20,
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Mir's nightmare dream — ruined palace, prince shadow, Deep Sea King.",
        [ref("young_mir", 1)],
        [
            relay(1, 6, "A ruined dragon palace fills the dream frame — broken hall, black roots wrapped around a fading blue heart-stone. Young Mir (Picture 1) stands small before it.", beat_type="dream_establishing"),
            relay(2, 5, "Behind Young Mir, an enormous prince-dragon shadow with crown-like horn and long body appears — silhouette only, no full reveal.", beat_type="anticipation"),
            relay(3, 5, "A disembodied low voice with no visible mouth says in natural Korean, \"너는 왕자가 아니다.\" Young Mir shudders.", beat_type="dialogue"),
            relay(4, 4, "The same voice says in natural Korean, \"버려진 새끼 용이다.\" Young Mir trembles violently as the dream begins cracking back to reality.", beat_type="consequence"),
        ],
        [
            {"speaker": "Deep Sea King", "text": "너는 왕자가 아니다.", "segment_order": 3},
            {"speaker": "Deep Sea King", "text": "버려진 새끼 용이다.", "segment_order": 4},
        ],
        {"start_state": "Mir dreaming.", "end_state": "Nightmare peak; waking imminent.", "carry_to_next": ["Deep Sea King rejection words", "Prince shadow silhouette", "Fear for Mir"]},
        build_global_prompt(
            "EP01 S#5 Nightmare dream", "Mir dream palace",
            [("young_mir", 1)],
            ["Dream palace ruins bg", "Black roots on heart-stone", "Prince shadow silhouette only"],
            lighting="Cold blue memory-light with deep black void.",
        ),
        scenario_span="L653-L679", narrative_purpose="Separate dream from house reality; echo cold open vision once.",
        shot_type="Nightmare dream", summary="EP01 S#5 — Mir's nightmare, Deep Sea King rejection.",
        previous_clip="SC01-005_01", next_clip="SC01-005_03",
        source_evidence=["Scenario L653-L679 nightmare dream"],
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_03", 3, 18,
        "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "Lua wakes, comforts Mir, fear transfers.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            relay(1, 4, "Young Mir (Picture 2) shakes in the basin. Lua (Picture 1) jolts awake and says in natural Korean, \"뭐야…\"", beat_type="recovery"),
            relay(2, 5, "Lua lifts Young Mir from the basin into her arms and says in natural Korean, \"야. 괜찮아.\" She adds in natural Korean, \"나 여기 있어.\"", beat_type="comfort"),
            relay(3, 5, "Lua clutches her chest as foreign dread hits. Her internal voice-over says in natural Korean, \"이거…\" After a pause the voice-over continues in natural Korean, \"내 무서움이 아니야.\"", beat_type="fear_transfer"),
            relay(4, 4, "Lua holds Young Mir tighter and says in natural Korean, \"너도 무서운 거구나.\" Young Mir gently licks Lua's wrist mark. The mark glows softly. Lua turns toward the window.", beat_type="reaction"),
        ],
        [
            {"speaker": "Lua", "text": "뭐야…", "segment_order": 1},
            {"speaker": "Lua", "text": "야. 괜찮아.", "segment_order": 2},
            {"speaker": "Lua", "text": "나 여기 있어.", "segment_order": 2},
            {"speaker": "Lua (internal)", "text": "이거…", "segment_order": 3},
            {"speaker": "Lua (internal)", "text": "내 무서움이 아니야.", "segment_order": 3},
            {"speaker": "Lua", "text": "너도 무서운 거구나.", "segment_order": 4},
        ],
        {"start_state": "Mir nightmare bleeding to reality.", "end_state": "Lua holds Mir; notices silent sea.", "carry_to_next": ["Lua at window next", "Shared fear established", "Marks glowing"]},
        build_global_prompt(
            "EP01 S#5 Night house", "Comfort and fear transfer",
            [("lua", 1), ("young_mir", 2)],
            ["Night house interior", "Basin and bed"],
            lighting="Dim warm interior with cool moonlight from window.",
            include_anatomy_separation=True,
        ),
        scenario_span="L681-L725", narrative_purpose="Lua feels Mir's fear — bond deepens.",
        shot_type="Emotional interior", summary="EP01 S#5 — wake, comfort, fear transfer.",
        previous_clip="SC01-005_02", next_clip="SC01-005_04",
        include_character_review=True,
        asset_roles={"lua": "character", "young_mir": "character"},
        source_evidence=["Scenario L681-L725 comfort and fear transfer"],
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_04", 4, 18,
        "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW",
        "Black jellyfish outside window, final EP01 hook.",
        [ref("lua", 1), ref("young_mir", 2), ref("jellyfish", 3)],
        [
            relay(1, 5, "Lua (Picture 1) approaches the window. Outside, the night sea is unnaturally still with no creatures in the empty background plate.", beat_type="establishing"),
            relay(2, 4, "The Black Jellyfish (Picture 3) floats above the dark sea — semi-transparent dark bell with ink smoke inside and long tentacles below the surface. Young Mir (Picture 2) growls low.", beat_type="reveal"),
            relay(3, 5, "Lua tense, protective arm around Young Mir, whispers in natural Korean, \"저게…\" After a pause she adds in natural Korean, \"널 찾으러 온 거야?\"", beat_type="dialogue"),
            relay(4, 4, "Young Mir's chest mark and Lua's wrist mark flash together. The Black Jellyfish (Picture 3) turns orientation toward the house. The shot holds then fades to black.", beat_type="closing"),
        ],
        [
            {"speaker": "Lua", "text": "저게…", "segment_order": 3},
            {"speaker": "Lua", "text": "널 찾으러 온 거야?", "segment_order": 3},
        ],
        {"start_state": "Lua at window, sea silent.", "end_state": "Jellyfish turns toward house; fade out.", "carry_to_next": ["EP02 hook — jellyfish threat", "Marks reacted", "Hunter arrived"]},
        build_global_prompt(
            "EP01 S#5 Jellyfish hook", "Black jellyfish reveal",
            [("lua", 1), ("young_mir", 2), ("jellyfish", 3)],
            ["Night sea through window", "Empty ocean background — no jellyfish in plate", "Unnaturally still ocean"],
            lighting="Cool blue moonlight on sea, faint bioluminescent accents on jellyfish edges.",
            include_anatomy_separation=True,
            consistency_notes=["Black Jellyfish (Picture 3) is the only jellyfish in frame — not duplicated in background plate."],
        ),
        scenario_span="L727-L761", narrative_purpose="EP01 cliffhanger — hunter arrives.",
        shot_type="Horror reveal", summary="EP01 S#5 end — black jellyfish at window, fade out.",
        previous_clip="SC01-005_03", next_clip=None,
        include_character_review=True,
        required_assets=[{"asset_id": "ENTITY_BLACK_JELLYFISH", "role": "dynamic_entity", "source_path": REF_PATHS["jellyfish"], "reference_required": True, "affected_relay_segments": [2, 4]}],
        asset_roles={"lua": "character", "young_mir": "character", "jellyfish": "dynamic_entity"},
        background_exclusions=["Black Jellyfish", "sea creatures"],
        reference_consistency_notes=["Background plate must not contain jellyfish — Picture 3 handles all jellyfish movement."],
        source_evidence=["Scenario L727-L761 black jellyfish hook"],
    )
)


def render_markdown(item: dict[str, Any]) -> str:
    payload = item["payload"]
    clip_id = payload["clip_id"]
    lines = [
        "---",
        f"# MSR Prompt: {clip_id}",
        "",
        "## Summary",
        "",
        item["summary"],
        "",
        "## Narrative Purpose",
        "",
        payload["narrative_purpose"],
        "",
        "## Scenario Source",
        "",
        f"- Source: `{payload['scenario_source']}`",
        f"- Span: {payload['scenario_source_span']}",
        "",
        "## Machine Payload",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Global Prompt",
        "",
        payload["global_prompt"],
        "",
        "## Relay Segments",
        "",
    ]
    for seg in payload["relay_segments"]:
        beat = f" [{seg['beat_type']}]" if seg.get("beat_type") else ""
        lines.append(f"- **Segment {seg['order']} ({seg['seconds']}s){beat}:** {seg['prompt']}")
    lines.extend(["", "## Original Dialogue Check", ""])
    if payload["dialogue"]:
        for d in payload["dialogue"]:
            lines.append(f"- **{d['speaker']}** (segment {d['segment_order']}): 「{d['text']}」")
    else:
        lines.append("- *(no spoken dialogue)*")
    cont = payload["continuity"]
    lines.extend(
        [
            "",
            "## Continuity",
            "",
            f"**Start:** {cont['start_state']}",
            "",
            f"**End:** {cont['end_state']}",
            "",
            "**Carry to next:**",
        ]
    )
    for c in cont["carry_to_next"]:
        lines.append(f"- {c}")
    bg = payload["background"]
    gen = payload["background_generation"]
    lines.extend(
        [
            "",
            "## Background Requirements",
            "",
            f"**Background ID:** `{bg['background_id']}`",
            "",
            f"**Description:** {bg['description']}",
            "",
            f"**Suggested filename:** `{gen['suggested_filename']}`",
            "",
            f"**Resolution:** {gen['recommended_resolution']['width']} × {gen['recommended_resolution']['height']} ({gen['aspect_ratio']})",
            "",
            "## AI Review",
            "",
        ]
    )
    review = payload["review"]
    checks = [
        ("Scenario order match", review["scenario_consistent"]),
        ("Dialogue preserved", review["dialogue_preserved"]),
        ("Reference mapping valid", review["reference_mapping_valid"]),
        ("Duration ≤30s", review["duration_valid"]),
        ("Animation style", review["animation_style_preserved"]),
        ("Background generation present", review["background_generation_valid"]),
    ]
    for label, ok in checks:
        lines.append(f"- [{'x' if ok else ' '}] {label}")
    if review.get("character_review"):
        lines.extend(["", "## Character Review (Lua + Young Mir)", ""])
        for key, ok in review["character_review"].items():
            label = key.replace("_", " ").title()
            lines.append(f"- [{'x' if ok else ' '}] {label}")
    if review["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for w in review["warnings"]:
            lines.append(f"- {w}")
    if review["unresolved_questions"]:
        lines.extend(["", "## Unresolved Questions", ""])
        for q in review["unresolved_questions"]:
            lines.append(f"- {q}")
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def validate_clips() -> list[str]:
    errors: list[str] = []
    ids = [c["payload"]["clip_id"] for c in CLIPS]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate clip_id detected")
    if len(CLIPS) != 24:
        errors.append(f"Expected 24 clips, got {len(CLIPS)}")

    total = sum(c["payload"]["requested_seconds"] for c in CLIPS)
    if total != 412:
        errors.append(f"Expected 412 total seconds, got {total}")

    prev = None
    for item in CLIPS:
        p = item["payload"]
        if p["previous_clip"] != prev:
            errors.append(f"{p['clip_id']}: previous_clip mismatch (expected {prev})")
        prev = p["clip_id"]
        if p["requested_seconds"] > 30:
            errors.append(f"{p['clip_id']}: exceeds 30s")
        relay_sum = sum(s["seconds"] for s in p["relay_segments"])
        if abs(relay_sum - p["requested_seconds"]) > 0.01:
            errors.append(f"{p['clip_id']}: relay sum {relay_sum} != requested {p['requested_seconds']}")
        refs = p["references"]
        if len(refs) > 4:
            errors.append(f"{p['clip_id']}: more than 4 references")
        ref_ids = [r["reference_id"] for r in refs]
        if ref_ids != list(range(1, len(ref_ids) + 1)):
            errors.append(f"{p['clip_id']}: reference_id not consecutive from 1")
        for r in refs:
            if "role" not in r:
                errors.append(f"{p['clip_id']}: missing role on {r['character_name']}")
        gp = p["global_prompt"]
        if "Fixed appearance:" in gp or re.search(r"Picture \d+ = \w+$", gp, re.M):
            errors.append(f"{p['clip_id']}: global_prompt uses deprecated Picture N = Name pattern")
        has_lua_mir = any(r["character_name"] == "Lua" for r in refs) and any(
            r["character_name"] == "Young Mir" for r in refs
        )
        if has_lua_mir:
            if "human" not in gp.lower() or "dragon" not in gp.lower():
                errors.append(f"{p['clip_id']}: Lua+Mir clip missing anatomy separation in global_prompt")
            if "character_review" not in p["review"]:
                errors.append(f"{p['clip_id']}: Lua+Mir clip missing character_review checklist")

    spear_clips = {"SC01-002_01", "SC01-002_02", "SC01-003_01", "SC01-003_02"}
    for item in CLIPS:
        p = item["payload"]
        if p["clip_id"] in spear_clips:
            if not any(r.get("source_path") == REF_PATHS["spear"] for r in p["references"]):
                errors.append(f"{p['clip_id']}: missing spear reference")

    for item in CLIPS:
        p = item["payload"]
        if p["clip_id"] == "SC01-001_03":
            if not any(r["character_name"] == "Black Tide" for r in p["references"]):
                errors.append("SC01-001_03: missing Black Tide reference")
            if p["background"]["background_id"] != "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY":
                errors.append("SC01-001_03: wrong background")
        if p["clip_id"] == "SC01-005_04":
            if p["background"]["background_id"] != "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW":
                errors.append("SC01-005_04: wrong background")

    if CLIPS[-1]["payload"]["next_clip"] is not None:
        errors.append("Last clip should have next_clip=None")

    return errors


V2_DIALOGUE: list[tuple[str, str, str]] = [
    ("SC01-001_04", "Deep Sea King", "기억하지 마라."),
    ("SC01-001_04", "Deep Sea King", "그러면 아프지 않다."),
    ("SC01-002_01", "Village Child 1", "또 놓쳤다!"),
    ("SC01-002_01", "Village Child 2", "루아 누나는 바다랑 안 맞아!"),
    ("SC01-002_01", "Lua", "안 맞긴 뭐가 안 맞아!"),
    ("SC01-002_02", "Lua", "방금 건 일부러 빠진 거야."),
    ("SC01-002_02", "Lua", "수심 확인."),
    ("SC01-002_02", "Old Fisherman", "루아야."),
    ("SC01-002_02", "Lua", "네!"),
    ("SC01-002_02", "Old Fisherman", "바다는 고집으로 되는 게 아니다."),
    ("SC01-002_02", "Old Fisherman", "오늘은 동굴 쪽 가지 마라."),
    ("SC01-002_02", "Old Fisherman", "폭풍 뒤에는 뭐가 밀려올지 몰라."),
    ("SC01-002_02", "Lua (internal)", "가라면 가지 말아야 하는데."),
    ("SC01-002_02", "Lua (internal)", "저렇게 빛나면 가야지."),
    ("SC01-003_01", "Lua", "나와라."),
    ("SC01-003_01", "Lua", "내가 마을에서 제일 무서운 사람은 아니지만."),
    ("SC01-003_01", "Lua", "상당히 귀찮은 사람이다."),
    ("SC01-003_02", "Lua", "방금 귀여웠는데?"),
    ("SC01-003_02", "Lua", "너…"),
    ("SC01-003_02", "Lua", "도마뱀은 아니지?"),
    ("SC01-003_02", "Lua", "말도 안 돼."),
    ("SC01-003_03", "Lua", "야, 야. 괜찮아."),
    ("SC01-003_03", "Lua", "안 잡아먹어."),
    ("SC01-003_03", "Lua", "나도 오늘 아침 못 먹었거든."),
    ("SC01-003_04", "Lua", "악!"),
    ("SC01-003_09", "Lua", "방금…"),
    ("SC01-003_09", "Lua", "내가 본 거야?"),
    ("SC01-003_09", "Lua", "너 대체 뭐야?"),
    ("SC01-003_09", "Village person (off-screen)", "루아! 거기 있냐?"),
    ("SC01-003_09", "Lua", "하."),
    ("SC01-003_09", "Lua", "나 진짜 사고 쳤다."),
    ("SC01-004_01", "Lua", "진짜네."),
    ("SC01-004_01", "Lua", "꿈이면 지금쯤 깨야 하는데."),
    ("SC01-004_01", "Lua", "너 물에서 자는 거야?"),
    ("SC01-004_01", "Lua", "좋겠다. 난 그러면 죽는데."),
    ("SC01-004_02", "Lua", "먹어."),
    ("SC01-004_02", "Lua", "아니, 바다에서 왔잖아."),
    ("SC01-004_02", "Lua", "생선 안 먹어?"),
    ("SC01-004_02", "Lua", "입맛도 귀족이네."),
    ("SC01-004_03", "Imagined adult (off-screen)", "불길하다!"),
    ("SC01-004_03", "Imagined adult (off-screen)", "바다에 돌려보내!"),
    ("SC01-004_03", "Lua", "안 돼."),
    ("SC01-004_04", "Lua", "그러니까… 당분간 여기 있어."),
    ("SC01-004_04", "Lua", "근데 밥값은 해야 돼."),
    ("SC01-004_04", "Lua", "예를 들면."),
    ("SC01-004_04", "Lua", "물 좀 데워준다든가?"),
    ("SC01-004_04", "Lua", "그래."),
    ("SC01-004_04", "Lua", "가능성은 있다."),
    ("SC01-005_02", "Deep Sea King", "너는 왕자가 아니다."),
    ("SC01-005_02", "Deep Sea King", "버려진 새끼 용이다."),
    ("SC01-005_03", "Lua", "뭐야…"),
    ("SC01-005_03", "Lua", "야. 괜찮아."),
    ("SC01-005_03", "Lua", "나 여기 있어."),
    ("SC01-005_03", "Lua (internal)", "이거…"),
    ("SC01-005_03", "Lua (internal)", "내 무서움이 아니야."),
    ("SC01-005_03", "Lua", "너도 무서운 거구나."),
    ("SC01-005_04", "Lua", "저게…"),
    ("SC01-005_04", "Lua", "널 찾으러 온 거야?"),
]


def validate_dialogue() -> list[str]:
    errors: list[str] = []
    v3_lines: list[tuple[str, str, str]] = []
    for item in CLIPS:
        p = item["payload"]
        for d in p["dialogue"]:
            v3_lines.append((p["clip_id"], d["speaker"], d["text"]))
    if len(v3_lines) != 58:
        errors.append(f"Expected 58 dialogue lines, got {len(v3_lines)}")
    if v3_lines != V2_DIALOGUE:
        for i, (a, b) in enumerate(zip(v3_lines, V2_DIALOGUE)):
            if a != b:
                errors.append(f"Dialogue mismatch at index {i}: v3={a} v2={b}")
                break
        if len(v3_lines) != len(V2_DIALOGUE):
            pass
        elif not any("mismatch at index" in e for e in errors):
            errors.append("Dialogue content differs from V2 preserved lines")
    return errors


def main() -> int:
    validation_errors = validate_clips() + validate_dialogue()
    for err in validation_errors:
        print(f"VALIDATION ERROR: {err}", file=sys.stderr)
    if validation_errors:
        return 1

    total_seconds = sum(c["payload"]["requested_seconds"] for c in CLIPS)
    if not (330 <= total_seconds <= 420):
        print(f"WARNING: total seconds {total_seconds} outside 330-420 target range", file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "backgrounds").mkdir(exist_ok=True)

    for item in CLIPS:
        payload = item["payload"]
        scene_dir = OUT / payload["scene_id"]
        scene_dir.mkdir(parents=True, exist_ok=True)
        path = scene_dir / f"{payload['clip_id']}.md"
        path.write_text(render_markdown(item), encoding="utf-8")

    bg_catalog = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "backgrounds": BACKGROUNDS,
    }
    (OUT / "background_catalog.json").write_text(
        json.dumps(bg_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    (OUT / "background_links.json").write_text(
        json.dumps(
            {"schema_version": 1, "project_id": PROJECT_ID, "links": {}, "updated_at": None},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    status_counts: dict[str, int] = {}
    for item in CLIPS:
        st = item["payload"]["status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    scene_times: dict[str, float] = {}
    for item in CLIPS:
        sid = item["payload"]["scene_id"]
        scene_times[sid] = scene_times.get(sid, 0) + item["payload"]["requested_seconds"]

    hero_prop_count = sum(
        1 for item in CLIPS for r in item["payload"]["references"] if r.get("role") == "hero_prop"
    )
    dynamic_count = sum(
        1 for item in CLIPS for r in item["payload"]["references"] if r.get("role") == "dynamic_entity"
    )
    char_count = sum(
        1 for item in CLIPS for r in item["payload"]["references"] if r.get("role") == "character"
    )

    manifest = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon Season 1 — EP01 V3",
        "description": (
            "EP01 바다에서 주운 용 — MSR V3 prompt project with Object References, "
            "LTX-style relay prompts, anatomy separation, and background/dynamic entity split"
        ),
        "scenario_source": SCENARIO,
        "episode_coverage": ["EP01"],
        "supersedes_project": SUPERSEDES,
        "policy": {
            "language": "English visual prompts; Korean spoken dialogue only",
            "max_clip_seconds": 30,
            "target_clip_seconds": "10-26",
            "target_total_seconds_range": [330, 420],
            "max_references_per_clip": 4,
            "object_reference_roles": ["character", "hero_prop", "dynamic_entity", "interactive_prop"],
            "background_entity_separation": True,
            "ltx_prompt_guide_applied": True,
        },
        "scene_count": len(scene_times),
        "clip_count": len(CLIPS),
        "total_requested_seconds": total_seconds,
        "scene_requested_seconds": scene_times,
        "reference_counts": {
            "character": char_count,
            "hero_prop": hero_prop_count,
            "dynamic_entity": dynamic_count,
        },
        "status_summary": status_counts,
        "new_backgrounds_required": [
            "BG_EP01_DEEP_SEA_PURSUIT_CORRIDOR_EMPTY",
            "BG_EP01_NIGHT_SEA_EMPTY_FROM_WINDOW",
        ],
        "notes": [
            "V3 supersedes V2 — RaisingaDragonSeason01_EP01_v2 preserved untouched.",
            "All clips awaiting_background except SC01-004_02 needs_confirmation (shell interactive_prop).",
            "Black Tide and Black Jellyfish separated from background plates.",
            "Lua fishing spear added as hero_prop Reference in SC01-002_01, _02 and SC01-003_01, _02.",
            "SC01-003 expanded to 9 clips with contact/vision separation A-F.",
            "Lua+Young Mir clips include anatomy separation block and character_review checklist.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {len(CLIPS)} clips, {total_seconds}s total -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
