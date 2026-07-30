#!/usr/bin/env python3
"""Generate RaisingaDragonSeason01_EP01_v2 MSR prompt project from EP01 scenario."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = "RaisingaDragonSeason01_EP01_v2"
OUT = ROOT / "prompt_projects" / PROJECT_ID
SCENARIO = "RaisingaDragonSeason01/Raising a Dragon.md"

STYLE_FOOTER = (
    "Preserve the exact visual style of the supplied animated references. "
    "High-quality stylized feature-film animation. Preserve facial design, body proportions, "
    "clothing and color palette. Do not convert animated references into live-action realism.\n\n"
    "All spoken dialogue and voice-over must be natural Korean. "
    "Lip-sync and mouth movement should match Korean speech timing. "
    "Do not translate dialogue into English."
)

LUA_DESC = (
    "Reference {n} is Lua, a small coastal village girl with sun-browned skin, "
    "messy light-brown hair, large brown eyes, a short sleeveless tunic, a rope belt "
    "and small shell ornaments."
)
MIR_DESC = (
    "Reference {n} is Young Mir, a small blue-silver sea dragon with wet scales, "
    "short horns, fin-like wings, a water-drop crystal at the end of his tail "
    "and a faint crown-shaped wave mark on his chest."
)
CHILD1_DESC = (
    "Reference {n} is Village Child 1, a coastal village child in simple rustic clothes "
    "with a playful curious expression."
)
CHILD2_DESC = (
    "Reference {n} is Village Child 2, a coastal village child in simple rustic clothes "
    "with a teasing smile."
)
FISHERMAN_DESC = (
    "Reference {n} is the Old Fisherman, an elderly coastal villager with weathered skin, "
    "simple worn fishing clothes and a calm serious expression."
)
JELLYFISH_DESC = (
    "Reference {n} is the Black Jellyfish, a semi-transparent dark jellyfish with ink-like "
    "smoke swirling inside its bell and long tentacles trailing below the surface."
)

REF_PATHS = {
    "lua": "RaisingaDragonSeason01/Lua.png",
    "young_mir": "RaisingaDragonSeason01/YoungMir.png",
    "child1": "RaisingaDragonSeason01/villageChild01.png",
    "child2": "RaisingaDragonSeason01/village_child_2.png",
    "old_fisherman": "RaisingaDragonSeason01/old_fisherman.png",
    "jellyfish": "RaisingaDragonSeason01/BLACK JELLYFISH .png",
}


def ref(key: str, ref_id: int) -> dict[str, Any]:
    desc_map = {
        "lua": LUA_DESC,
        "young_mir": MIR_DESC,
        "child1": CHILD1_DESC,
        "child2": CHILD2_DESC,
        "old_fisherman": FISHERMAN_DESC,
        "jellyfish": JELLYFISH_DESC,
    }
    name_map = {
        "lua": "Lua",
        "young_mir": "Young Mir",
        "child1": "Village Child 1",
        "child2": "Village Child 2",
        "old_fisherman": "Old Fisherman",
        "jellyfish": "Black Jellyfish",
    }
    return {
        "reference_id": ref_id,
        "character_name": name_map[key],
        "description": desc_map[key].format(n=ref_id),
        "source_path": REF_PATHS[key],
    }


def bg_entry(
    bg_id: str,
    description: str,
    scenes: list[str],
    prompt: str,
    continuity_notes: list[str],
    *,
    reused_from: str | None = None,
) -> dict[str, Any]:
    entry = {
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
        entry["reused_from_v1"] = reused_from
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
    ),
    "BG_EP01_DEEP_SEA_BLACK_CURRENT": bg_entry(
        "BG_EP01_DEEP_SEA_BLACK_CURRENT",
        "Deep sea passage where living black water rises. Dark current with shadowy hand and face shapes in the water.",
        ["SC01-001"],
        BG_PROMPT_HEADER
        + "A deep underwater corridor above a living black ocean current. Foreground: teal water with open diagonal ascent path along a faint blue light beam. "
        "Middle distance: rising mass of living black water with subtle hand-like and mouth-like shadow shapes forming and dissolving within it. Background: dark abyss below, faint ruined coral edges at sides.\n\n"
        "Eye-level medium-wide composition angled slightly upward, 16:9 cinematic framing. Cold cyan ambient light from above-left, ominous purple-black glow from below.\n\n"
        "Hand-painted animated underwater horror background, strong depth separation.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Living black water below, blue ascent path above", "Shadow shapes in water not fully formed faces", "Matches deep sea palette of ruins clip"],
    ),
    "BG_EP01_MIR_VISION_PALACE_RUINS": bg_entry(
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Surreal vision space: broken dragon palace gate, ruined halls, sleeping giant dragon shadows, black abyss.",
        ["SC01-001", "SC01-005"],
        BG_PROMPT_HEADER
        + "A surreal vision version of a collapsed dragon palace interior and abyss. Foreground: floating debris and drifting dust motes with open central space. "
        "Middle distance: broken palace gate, ruined hall columns, enormous sleeping dragon shadows curled in darkness without clear faces. Background: endless black abyss fading into void.\n\n"
        "Eye-level wide composition with slight dutch unsettling tilt, 16:9 cinematic framing. Cold blue memory-light with deep black void, soft fog, dreamlike desaturation.\n\n"
        "Hand-painted animated vision background, nightmare memory atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Vision/dream palette — not physical cave or house", "Giant dragon shadows only as silhouettes", "Reused for S#1 vision and S#5 nightmare"],
    ),
    "BG_EP01_COASTAL_VILLAGE_MORNING": bg_entry(
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Post-storm morning coastal village.work shore with wet breakwater and distant cave cliff.",
        ["SC01-002"],
        BG_PROMPT_HEADER
        + "A small coastal fishing village work shore on the morning after a storm. Foreground: wet stone breakwater with clear open standing area, scattered wet rope at edges. "
        "Middle distance: overturned boats, tangled nets, broken wood on damp sand, villagers' repair activity spaces left empty. Background: soft post-storm sky, calm sea horizon, distant cliff with cave entrance hint.\n\n"
        "Eye-level medium-wide composition from breakwater facing sea, 16:9 cinematic framing. Soft diffused morning sunlight from frame right, cool blue bounce on wet stone.\n\n"
        "Detailed hand-painted animated village background — NOT photorealistic.\n\n"
        "Clean empty background plate. No characters, people, animals, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Hand-painted animation style matching character refs", "Breakwater center clear", "Cave cliff visible far background right"],
        reused_from="BG_EP01_COASTAL_VILLAGE_MORNING (v1 — style redo required)",
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
        reused_from="BG_EP01_COASTAL_CAVE_INTERIOR (v1 approved)",
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
        reused_from="BG_EP01_LUA_HOUSE_INTERIOR_DAY (v1 approved)",
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
        reused_from="BG_EP01_LUA_HOUSE_INTERIOR_NIGHT (v1 — layout continuity redo required)",
    ),
    "BG_EP01_NIGHT_SEA_JELLYFISH": bg_entry(
        "BG_EP01_NIGHT_SEA_JELLYFISH",
        "Night ocean viewed from house window height. One black semi-transparent jellyfish floating above dark sea.",
        ["SC01-005"],
        BG_PROMPT_HEADER
        + "Night ocean viewed from a slightly elevated coastal house window perspective. Foreground: window frame edge minimal, open view space. "
        "Middle distance: dark calm sea surface with one black semi-transparent jellyfish floating above water, ink-like smoke swirling inside its bell, long tentacles trailing below surface. Background: deep night sky with faint stars and distant horizon.\n\n"
        "Eye-level to slight high-angle composition through window framing optional at edges, 16:9 cinematic framing. Cool blue moonlight on sea, bioluminescent faint accents on jellyfish edges.\n\n"
        "Hand-painted animated night seascape background, ominous quiet atmosphere.\n\n"
        "Clean empty background plate. No characters, people, animals, dragons, crowds, silhouettes, faces, readable signs, text, logos or watermarks.",
        ["Single jellyfish centered over sea", "View matches Lua house window direction", "Ocean sounds visually implied as unnaturally still"],
    ),
}


def build_global_prompt(episode: str, scene_summary: str, ref_lines: list[str], env_lines: list[str]) -> str:
    parts = [f"Ocean fantasy animated film. {episode} — {scene_summary}.", ""]
    parts.append("Reference mapping:")
    parts.extend(ref_lines)
    parts.append("")
    parts.append("Fixed appearance:")
    parts.extend(ref_lines)
    parts.append("")
    parts.append("Environment:")
    parts.extend(env_lines)
    parts.append("")
    parts.append(STYLE_FOOTER)
    return "\n".join(parts)


def clip(
    scene_id: str,
    clip_id: str,
    sequence: int,
    seconds: float,
    bg_id: str,
    bg_desc: str,
    refs: list[dict[str, Any]],
    relay: list[dict[str, Any]],
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
    warnings: list[str] | None = None,
    unresolved: list[str] | None = None,
    review_flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    bg = BACKGROUNDS[bg_id]
    flags = review_flags or {}
    payload = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "episode_id": episode_id,
        "scene_id": scene_id,
        "clip_id": clip_id,
        "sequence": sequence,
        "status": "awaiting_background",
        "workflow": "msr_v2",
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
        "relay_segments": relay,
        "dialogue": dialogue,
        "review": {
            "scenario_consistent": flags.get("scenario_consistent", True),
            "dialogue_preserved": flags.get("dialogue_preserved", True),
            "reference_mapping_valid": flags.get("reference_mapping_valid", True),
            "duration_valid": flags.get("duration_valid", True),
            "animation_style_preserved": flags.get("animation_style_preserved", True),
            "warnings": warnings or [],
            "unresolved_questions": unresolved or [],
            "background_generation_valid": True,
        },
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
    return {
        "summary": summary,
        "payload": payload,
    }


CLIPS: list[dict[str, Any]] = []

# --- SC01-001 ---
CLIPS.append(
    clip(
        "SC01-001", "SC01-001_01", 1, 18,
        "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "Storm night ocean surface. Waves, lightning, rain. Distant blue pulse under water.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 6, "prompt": "Environment establishing: a violent storm night ocean fills the frame with giant waves, lightning forks and diagonal rain. No character visible yet. Camera holds wide on churning black water."},
            {"order": 2, "seconds": 6, "prompt": "Anticipation beat: far below the waves, a tiny blue bioluminescent pulse flickers once, then again — distant and fragile against the storm. Camera slowly tilts downward toward the glow without revealing its source."},
            {"order": 3, "seconds": 6, "prompt": "Transition end state: the camera continues descending toward the water surface as thunder rolls. The blue pulse brightens slightly beneath a wave trough. Hold on open dark water ready to plunge deeper."},
        ],
        [],
        {"start_state": "Night storm sea, no visible characters.", "end_state": "Camera descending toward distant underwater blue pulse.", "carry_to_next": ["Storm palette", "Distant blue glow location", "Night time"]},
        build_global_prompt("EP01 S#1 Cold open", "Storm sea surface establishing", ["Picture 1 = Young Mir (not yet visible on screen; reference for palette continuity only)"], ["Storm night ocean surface only", "Lightning from upper left", "Distant blue glow under waves"]),
        scenario_span="L109-L118",
        narrative_purpose="Establish pursuit mystery — something glows beneath the storm.",
        shot_type="Wide establishing",
        summary="EP01 S#1 opening — storm night sea and distant blue glow beneath the waves.",
        previous_clip=None,
        next_clip="SC01-001_02",
        warnings=["Young Mir reference included for MSR pipeline minimum; character not visible on screen in this clip."],
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_02", 2, 22,
        "BG_EP01_DEEP_SEA_RUINS_NIGHT",
        "Deep sea dragon palace ruins. Collapsed coral pillar. Young wounded Mir revealed.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 5, "prompt": "Environment establishing: deep underwater ruins. A sacred ancient coral pillar cracks slowly, marine snow drifting like snowflakes. Cold blue-teal ambient light."},
            {"order": 2, "seconds": 6, "prompt": "Character reveal preparation: within a faint blue glow, Picture 1 Young Mir becomes visible — small blue-silver body, wet scales, short horns, fin-like wings, tail crystal, chest wave mark. He is battered and half-conscious."},
            {"order": 3, "seconds": 6, "prompt": "Physical state beat: Picture 1 Young Mir's body tumbles weakly in the current. His eyes remain half closed. Tail crystal flickers weakly. Camera moves closer with gentle handheld drift."},
            {"order": 4, "seconds": 5, "prompt": "Recovery transition: Picture 1 Young Mir tries to orient upward but lacks strength. Hold on his vulnerable floating posture facing the blue diagonal above. End ready for pursuit beat."},
        ],
        [],
        {"start_state": "Deep sea ruins, pillar crumbling.", "end_state": "Young Mir revealed, wounded, drifting weakly.", "carry_to_next": ["Young Mir wounded state", "Deep sea ruins", "Blue glow on Mir"]},
        build_global_prompt("EP01 S#1 Cold open", "Deep sea ruins — Young Mir revealed", ["Picture 1 = Young Mir"], ["Collapsed coral palace pillar", "Deep teal abyss", "Bioluminescent blue accents"]),
        scenario_span="L119-L137",
        narrative_purpose="Reveal the chased creature without naming him.",
        shot_type="Medium reveal",
        summary="EP01 S#1 — deep sea ruins and wounded Young Mir revealed in blue glow.",
        previous_clip="SC01-001_01",
        next_clip="SC01-001_03",
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_03", 3, 20,
        "BG_EP01_DEEP_SEA_BLACK_CURRENT",
        "Living black water pursues Mir upward. Tail crystal rescue flash.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 5, "prompt": "Anticipation: below Picture 1 Young Mir, living black water rises — not mere darkness but moving mass with hand-like and mouth-like shadow shapes briefly forming and dissolving."},
            {"order": 2, "seconds": 5, "prompt": "Main action: Picture 1 Young Mir attempts to climb along a faint blue diagonal beam toward the surface, fins trembling, but his body barely moves against the current."},
            {"order": 3, "seconds": 5, "prompt": "Consequence beat: Picture 1 Young Mir's tail-end water-drop crystal flashes brightly once — like a rescue signal and a last shield. Black water recoils slightly."},
            {"order": 4, "seconds": 5, "prompt": "Recovery transition: Picture 1 Young Mir's vision wavers. Camera shudders. Hold on his trembling pupil reflecting blue and black. End ready for memory vision."},
        ],
        [],
        {"start_state": "Mir weak in deep water.", "end_state": "Crystal flashed; vision wavering.", "carry_to_next": ["Black pursuit active", "Tail crystal activated", "Mir weakness"]},
        build_global_prompt("EP01 S#1 Cold open", "Black current pursuit", ["Picture 1 = Young Mir"], ["Living black water below", "Blue ascent diagonal", "Deep sea corridor"]),
        scenario_span="L139-L149",
        narrative_purpose="Show Mir is hunted and nearly powerless.",
        shot_type="Action suspense",
        summary="EP01 S#1 — black living water pursues Mir; tail crystal flashes.",
        previous_clip="SC01-001_02",
        next_clip="SC01-001_04",
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_04", 4, 22,
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Mir's shaken vision: broken palace, sleeping dragon shadows, Deep Sea King voice.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 5, "prompt": "Vision establishing: shaky subjective drift through black abyss, broken palace gate and ruined halls. Enormous sleeping dragon shadows curl in darkness without revealing faces."},
            {"order": 2, "seconds": 5, "prompt": "Anticipation: Picture 1 Young Mir's eye fills part of frame, pupil trembling, reflected memory images sliding across it."},
            {"order": 3, "seconds": 6, "prompt": "Dialogue beat: a disembodied low voice in natural Korean, no visible mouth, reverberates through the vision — says in natural Korean, \"기억하지 마라.\" Picture 1 Young Mir's pupil shudders."},
            {"order": 4, "seconds": 6, "prompt": "Reaction and consequence: the same disembodied low voice in natural Korean says, \"그러면 아프지 않다.\" Picture 1 Young Mir trembles in fear. Vision begins tearing away into storm light above."},
        ],
        [
            {"speaker": "Deep Sea King", "text": "기억하지 마라.", "segment_order": 3},
            {"speaker": "Deep Sea King", "text": "그러면 아프지 않다.", "segment_order": 4},
        ],
        {"start_state": "Mir vision wavering.", "end_state": "Deep Sea King words delivered; fear peak.", "carry_to_next": ["Vision memory tone", "Deep Sea King voice", "Upward escape motivation"]},
        build_global_prompt("EP01 S#1 Cold open", "Mir vision — palace ruins memory", ["Picture 1 = Young Mir"], ["Surreal broken palace vision space", "Sleeping dragon shadows as silhouettes only", "Black abyss"]),
        scenario_span="L151-L171",
        narrative_purpose="Plant Deep Sea King suppression — forget to avoid pain.",
        shot_type="Subjective vision montage",
        summary="EP01 S#1 — Mir's vision of ruined palace and Deep Sea King voice.",
        previous_clip="SC01-001_03",
        next_clip="SC01-001_05",
    )
)

CLIPS.append(
    clip(
        "SC01-001", "SC01-001_05", 5, 18,
        "BG_EP01_STORM_SEA_SURFACE_NIGHT",
        "Mir's last push to storm surface; blue glow swept toward coast.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 6, "prompt": "Main action: Picture 1 Young Mir pushes upward with last strength through churning water toward storm-lit surface, body small against waves."},
            {"order": 2, "seconds": 6, "prompt": "Environment transition: camera breaks surface into storm night sea — rain, lightning, foam. A small blue glow is carried in waves, not yet identifiable as a creature."},
            {"order": 3, "seconds": 6, "prompt": "Closing consequence: the blue glow drifts far toward a coastal horizon. Do not reveal Mir's identity clearly. Hold on ominous sense that something chased is washing ashore. Fade motion toward coast."},
        ],
        [],
        {"start_state": "Mir fleeing memory upward.", "end_state": "Blue glow drifting toward coast in storm.", "carry_to_next": ["Storm morning follows", "Blue glow toward cave coast", "Chase unresolved"]},
        build_global_prompt("EP01 S#1 Cold open", "Ascent to storm surface", ["Picture 1 = Young Mir"], ["Storm sea surface return", "Small blue glow in waves", "Coastal direction implied"]),
        scenario_span="L173-L181",
        narrative_purpose="Close cold open on mystery — something hunted reaches the coast.",
        shot_type="Wide transition",
        summary="EP01 S#1 end — Mir ascends; blue glow swept toward coast.",
        previous_clip="SC01-001_04",
        next_clip="SC01-002_01",
    )
)

# --- SC01-002 ---
CLIPS.append(
    clip(
        "SC01-002", "SC01-002_01", 1, 22,
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Post-storm village morning. Lua spear fail. Village children mock.",
        [ref("lua", 1), ref("child1", 2), ref("child2", 3)],
        [
            {"order": 1, "seconds": 5, "prompt": "Environment establishing: post-storm coastal village morning. Wet nets, broken wood, overturned baskets, damaged small boats. Empty repair spaces imply villagers working off-screen."},
            {"order": 2, "seconds": 6, "prompt": "Character preparation: Picture 1 Lua stands at the breakwater end holding an awkward small spear, trying to mimic a great fisherman's stance. Her feet shift uneasily on wet stone. A small fish shadow passes below."},
            {"order": 3, "seconds": 6, "prompt": "Main action and reaction: Picture 1 Lua holds her breath and stabs — miss. Water splashes her face. She freezes embarrassed. Picture 2 Village Child 1 and Picture 3 Village Child 2 laugh behind her. Village Child 1 points at the empty water and says in natural Korean, \"또 놓쳤다!\""},
            {"order": 4, "seconds": 5, "prompt": "Dialogue and reaction: Village Child 2 says in natural Korean, \"루아 누나는 바다랑 안 맞아!\" Picture 1 Lua flushes with anger and snaps — says in natural Korean, \"안 맞긴 뭐가 안 맞아!\""},
        ],
        [
            {"speaker": "Village Child 1", "text": "또 놓쳤다!", "segment_order": 3},
            {"speaker": "Village Child 2", "text": "루아 누나는 바다랑 안 맞아!", "segment_order": 4},
            {"speaker": "Lua", "text": "안 맞긴 뭐가 안 맞아!", "segment_order": 4},
        ],
        {"start_state": "Morning after storm village.", "end_state": "Lua angry at mocking children.", "carry_to_next": ["Lua wet soon", "Spear in hand", "Breakwater location"]},
        build_global_prompt("EP01 S#2 Village morning", "Lua spear failure and mockery", ["Picture 1 = Lua", "Picture 2 = Village Child 1", "Picture 3 = Village Child 2"], ["Post-storm village shore", "Wet breakwater", "Morning soft light"]),
        scenario_span="L187-L233",
        narrative_purpose="Introduce Lua rejected by the sea; fix wrong speaker for '또 놓쳤다!'",
        shot_type="Character introduction",
        summary="EP01 S#2 — village morning, Lua misses fish, children mock.",
        previous_clip="SC01-001_05",
        next_clip="SC01-002_02",
    )
)

CLIPS.append(
    clip(
        "SC01-002", "SC01-002_02", 2, 22,
        "BG_EP01_COASTAL_VILLAGE_MORNING",
        "Lua slips, old fisherman warns, cave blue glow, Lua runs.",
        [ref("lua", 1), ref("old_fisherman", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Physical consequence: Picture 1 Lua slips on the wet breakwater and falls into shallow water. Village children laugh louder off-screen behind her. Picture 1 Lua pushes wet hair from her face, forcing bravado."},
            {"order": 2, "seconds": 6, "prompt": "Dialogue beat: Picture 1 Lua says in natural Korean, \"방금 건 일부러 빠진 거야.\" Brief held silence. She adds in natural Korean, \"수심 확인.\""},
            {"order": 3, "seconds": 6, "prompt": "Interruption: Picture 2 Old Fisherman approaches calmly without mocking. He says in natural Korean, \"루아야.\" Picture 1 Lua straightens — says in natural Korean, \"네!\" He says in natural Korean, \"바다는 고집으로 되는 게 아니다.\" Picture 1 Lua's expression hardens."},
            {"order": 4, "seconds": 5, "prompt": "Anticipation and exit: Picture 2 Old Fisherman looks toward the cliff cave and says in natural Korean, \"오늘은 동굴 쪽 가지 마라.\" then \"폭풍 뒤에는 뭐가 밀려올지 몰라.\" Picture 1 Lua does not answer. Faint blue flicker pulses in far cave. Her eyes widen. internal voice-over in natural Korean: \"가라면 가지 말아야 하는데.\" Beat. \"저렇게 빛나면 가야지.\" She runs toward cave with spear."},
        ],
        [
            {"speaker": "Lua", "text": "방금 건 일부러 빠진 거야.", "segment_order": 2},
            {"speaker": "Lua", "text": "수심 확인.", "segment_order": 2},
            {"speaker": "Old Fisherman", "text": "루아야.", "segment_order": 3},
            {"speaker": "Lua", "text": "네!", "segment_order": 3},
            {"speaker": "Old Fisherman", "text": "바다는 고집으로 되는 게 아니다.", "segment_order": 3},
            {"speaker": "Old Fisherman", "text": "오늘은 동굴 쪽 가지 마라.", "segment_order": 4},
            {"speaker": "Old Fisherman", "text": "폭풍 뒤에는 뭐가 밀려올지 몰라.", "segment_order": 4},
            {"speaker": "Lua (internal)", "text": "가라면 가지 말아야 하는데.", "segment_order": 4},
            {"speaker": "Lua (internal)", "text": "저렇게 빛na면 가야지.", "segment_order": 4},
        ],
        {"start_state": "Lua angry on breakwater.", "end_state": "Lua running to cave.", "carry_to_next": ["Lua wet clothes", "Spear", "Drawn to blue cave glow"]},
        build_global_prompt("EP01 S#2 Village morning", "Fisherman warning and cave pull", ["Picture 1 = Lua", "Picture 2 = Old Fisherman"], ["Same village breakwater", "Distant cave cliff visible"]),
        scenario_span="L235-L299",
        narrative_purpose="Foreshadow cave; establish Lua disobedience.",
        shot_type="Dialogue and exit",
        summary="EP01 S#2 — slip, fisherman warning, blue cave glow, Lua runs.",
        previous_clip="SC01-002_01",
        next_clip="SC01-003_01",
    )
)

# Fix typo in dialogue
CLIPS[-1]["payload"]["dialogue"][-1]["text"] = "저렇게 빛나면 가야지."
for seg in CLIPS[-1]["payload"]["relay_segments"]:
    if "빛na" in seg["prompt"]:
        seg["prompt"] = seg["prompt"].replace("빛na", "빛나")

# --- SC01-003 --- (4 clips)
CLIPS.append(
    clip(
        "SC01-003", "SC01-003_01", 1, 22,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua enters cave, bluffs bravely, hears squeak.",
        [ref("lua", 1)],
        [
            {"order": 1, "seconds": 5, "prompt": "Environment establishing: dark wet cave interior with dripping water, shallow seawater ripples and blue glow deeper inside. Picture 1 Lua enters cautiously with spear forward."},
            {"order": 2, "seconds": 6, "prompt": "Character preparation: Picture 1 Lua tries to look fearless while clearly afraid. She steadies breath, shifts weight on wet rock."},
            {"order": 3, "seconds": 6, "prompt": "Dialogue beat: Picture 1 Lua calls out — says in natural Korean, \"나와라.\" Brief pause. She adds in natural Korean, \"내가 마을에서 제일 무서운 사람은 아니지만.\" Another pause — \"상당히 귀찮은 사람이다.\""},
            {"order": 4, "seconds": 5, "prompt": "Anticipation: a tiny squeak (삐익) from deeper crevice. Picture 1 Lua freezes, eyes widening with curiosity. End on her leaning forward carefully."},
        ],
        [
            {"speaker": "Lua", "text": "나와라.", "segment_order": 3},
            {"speaker": "Lua", "text": "내가 마을에서 제일 무서운 사람은 아니지만.", "segment_order": 3},
            {"speaker": "Lua", "text": "상당히 귀찮은 사람이다.", "segment_order": 3},
        ],
        {"start_state": "Lua enters coastal cave.", "end_state": "Lua heard squeak, curious.", "carry_to_next": ["Spear lowered soon", "Blue inner glow", "Lua alone"]},
        build_global_prompt("EP01 S#3 Coastal cave", "Cave entry and bluff", ["Picture 1 = Lua"], ["Wet cave interior", "Shallow water floor", "Blue glow from depth"]),
        scenario_span="L305-L335",
        narrative_purpose="Build tension before Mir reveal.",
        shot_type="Suspense approach",
        summary="EP01 S#3 — Lua enters cave, bluffs, hears squeak.",
        previous_clip="SC01-002_02",
        next_clip="SC01-003_02",
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_02", 2, 22,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua discovers Young Mir, lowers spear, reaches out.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Main reveal: Picture 1 Lua peers into crevice. Picture 2 Young Mir visible — short horns, blue-silver tail, wet scales, half-open eyes. Picture 1 Lua lowers spear slowly."},
            {"order": 2, "seconds": 6, "prompt": "Reaction beat: Picture 1 Lua exhales shakily — says in natural Korean, \"방금 귀여웠는데?\" then whispered — \"너…\" pause — \"도마뱀은 아니지?\""},
            {"order": 3, "seconds": 6, "prompt": "Connection moment: Picture 2 Young Mir opens large clear eyes toward Picture 1 Lua — frightened but intelligent. Picture 1 Lua holds breath, awed — says in natural Korean, \"말도 안 돼.\""},
            {"order": 4, "seconds": 5, "prompt": "Preparation for contact: Picture 1 Lua slowly extends her hand. Picture 2 Young Mir tries to retreat but lacks strength, slipping on wet stone. Picture 1 Lua's face shifts from curiosity to worry. End on outstretched hand."},
        ],
        [
            {"speaker": "Lua", "text": "방금 귀여웠는데?", "segment_order": 2},
            {"speaker": "Lua", "text": "너…", "segment_order": 2},
            {"speaker": "Lua", "text": "도마뱀은 아니지?", "segment_order": 2},
            {"speaker": "Lua", "text": "말도 안 돼.", "segment_order": 3},
        ],
        {"start_state": "Lua heard squeak.", "end_state": "Lua reaching toward Mir.", "carry_to_next": ["Mir weak on wet rock", "Spear down", "Mutual eye contact"]},
        build_global_prompt("EP01 S#3 Coastal cave", "Discovery of Young Mir", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Same cave interior", "Crevice area", "Blue glow"]),
        scenario_span="L337-L379",
        narrative_purpose="First meeting — wonder not battle.",
        shot_type="Discovery two-shot",
        summary="EP01 S#3 — Lua discovers Young Mir in crevice.",
        previous_clip="SC01-003_01",
        next_clip="SC01-003_03",
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_03", 3, 24,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Contact, weak bite, blood, 용심 공명 vision overlay.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 6, "prompt": "Main action: Picture 1 Lua kneels lower — says in natural Korean, \"야, 야. 괜찮아.\" She keeps hand open — \"안 잡아먹어.\" touches her own stomach — \"나도 오늘 아침 못 먹었거든.\""},
            {"order": 2, "seconds": 5, "prompt": "Physical beat: Picture 2 Young Mir watches her fingers, then weakly bites Picture 1 Lua's finger — clinging not attacking. Picture 1 Lua flinches — says in natural Korean, \"악!\" then realizes he is begging to be saved."},
            {"order": 3, "seconds": 7, "prompt": "Consequence: a blood drop touches Picture 2 Young Mir's broken scale. Cave water ripples. Blue mark forms on Picture 1 Lua's wrist. Picture 2 Young Mir's chest mark reacts. Blue connection thread between them. Brief vision overlay: ruined palace, sleeping dragons, black roots, fading deep heart."},
            {"order": 4, "seconds": 6, "prompt": "Recovery: Picture 1 Lua gasps back to reality, staring at wrist mark. Picture 2 Young Mir whimpers softly. Hold trembling connection light fading."},
        ],
        [
            {"speaker": "Lua", "text": "야, 야. 괜찮아.", "segment_order": 1},
            {"speaker": "Lua", "text": "안 잡아먹어.", "segment_order": 1},
            {"speaker": "Lua", "text": "나도 오늘 아침 못 먹었거든.", "segment_order": 1},
            {"speaker": "Lua", "text": "악!", "segment_order": 2},
        ],
        {"start_state": "Lua hand extended.", "end_state": "용심 공명 triggered; wrist mark visible.", "carry_to_next": ["Wrist mark", "Chest mark reaction", "Lua shock"]},
        build_global_prompt("EP01 S#3 Coastal cave", "Contact and resonance", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Cave interior", "Shallow water ripples", "Vision overlay moment"]),
        scenario_span="L385-L441",
        narrative_purpose="Ability unlock — 용심 공명.",
        shot_type="Emotional action",
        summary="EP01 S#3 — bite, blood, resonance vision.",
        previous_clip="SC01-003_02",
        next_clip="SC01-003_04",
    )
)

CLIPS.append(
    clip(
        "SC01-003", "SC01-003_04", 4, 22,
        "BG_EP01_COASTAL_CAVE_INTERIOR",
        "Lua questions Mir, village voice, wraps and carries out.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 6, "prompt": "Dialogue beat: Picture 1 Lua breathes hard — says in natural Korean, \"방금…\" looks at wrist — \"내가 본 거야?\" Picture 2 Young Mir whimpers. Picture 1 Lua asks in natural Korean, \"너 대체 뭐야?\""},
            {"order": 2, "seconds": 5, "prompt": "Interruption: off-screen voice in natural Korean from cave mouth — \"루아! 거기 있냐?\" Picture 1 Lua panics, looks to exit."},
            {"order": 3, "seconds": 6, "prompt": "Main action: Picture 2 Young Mir crawls weakly toward Picture 1 Lua. She hesitates, then wraps him in part of her outer cloth. Says in natural Korean, \"하.\" pause — \"나 진짜 사고 쳤다.\""},
            {"order": 4, "seconds": 5, "prompt": "Exit transition: Picture 1 Lua cradles Picture 2 Young Mir and moves toward cave mouth light. Camera follows from behind. End on her stepping out of cave shadow."},
        ],
        [
            {"speaker": "Lua", "text": "방금…", "segment_order": 1},
            {"speaker": "Lua", "text": "내가 본 거야?", "segment_order": 1},
            {"speaker": "Lua", "text": "너 대체 뭐야?", "segment_order": 1},
            {"speaker": "Village person (off-screen)", "text": "루아! 거기 있냐?", "segment_order": 2},
            {"speaker": "Lua", "text": "하.", "segment_order": 3},
            {"speaker": "Lua", "text": "나 진짜 사고 쳤다.", "segment_order": 3},
        ],
        {"start_state": "Resonance just occurred.", "end_state": "Lua carrying Mir out of cave.", "carry_to_next": ["Mir wrapped in cloth", "Wrist mark hidden soon", "Lua committed"]},
        build_global_prompt("EP01 S#3 Coastal cave", "Wrap and escape", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Cave interior to mouth light transition within same bg"]),
        scenario_span="L443-L489",
        narrative_purpose="Lua chooses to steal Mir away.",
        shot_type="Escape beat",
        summary="EP01 S#3 — questions, village call, Lua carries Mir out.",
        previous_clip="SC01-003_03",
        next_clip="SC01-004_01",
    )
)

# --- SC01-004 ---
CLIPS.append(
    clip(
        "SC01-004", "SC01-004_01", 1, 22,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Secret arrival home, reality check, water basin.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Transition establishing: Picture 1 Lua quietly closes door of small worn house, listening for outside sounds. Picture 2 Young Mir peeks from wrapped cloth."},
            {"order": 2, "seconds": 6, "prompt": "Emotional beat: Picture 1 Lua stares — says in natural Korean, \"진짜네.\" pause — \"꿈이면 지금쯤 깨야 하는데.\""},
            {"order": 3, "seconds": 6, "prompt": "Care action: Picture 1 Lua places Picture 2 Young Mir into shallow water basin. He half-submerges and relaxes slightly. She watches amazed."},
            {"order": 4, "seconds": 5, "prompt": "Dialogue: Picture 1 Lua asks in natural Korean, \"너 물에서 자는 거야?\" Picture 2 Young Mir blinks. She sighs — \"좋겠다. 난 그러면 죽는데.\""},
        ],
        [
            {"speaker": "Lua", "text": "진짜네.", "segment_order": 2},
            {"speaker": "Lua", "text": "꿈이면 지금쯤 깨야 하는데.", "segment_order": 2},
            {"speaker": "Lua", "text": "너 물에서 자는 거야?", "segment_order": 4},
            {"speaker": "Lua", "text": "좋겠다. 난 그러면 죽는데.", "segment_order": 4},
        ],
        {"start_state": "Lua enters house with Mir.", "end_state": "Mir resting in basin.", "carry_to_next": ["Basin setup", "Day interior", "Secret hiding"]},
        build_global_prompt("EP01 S#4 Lua house day", "Secret arrival", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Small worn house day interior", "Water basin", "Hidden from village"]),
        scenario_span="L495-L529",
        narrative_purpose="First shelter — secret custody begins.",
        shot_type="Interior domestic",
        summary="EP01 S#4 — home arrival, Mir in basin.",
        previous_clip="SC01-003_04",
        next_clip="SC01-004_02",
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_02", 2, 20,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Fish rejected, shell preference.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Preparation: Picture 1 Lua brings dried fish from table, offering it gently to Picture 2 Young Mir in basin."},
            {"order": 2, "seconds": 5, "prompt": "Dialogue and reaction: Picture 1 Lua says in natural Korean, \"먹어.\" Picture 2 Young Mir recoils in disgust. Picture 1 Lua flustered — \"아니, 바다에서 왔잖아.\" \"생선 안 먹어?\""},
            {"order": 3, "seconds": 5, "prompt": "Main action: Picture 2 Young Mir crawls toward shell on table instead, licks it and hugs it like treasure. Picture 1 Lua deadpans."},
            {"order": 4, "seconds": 5, "prompt": "Dialogue reaction: Picture 1 Lua says in natural Korean, \"입맛도 귀족이네.\" Picture 2 Young Mir calms holding shell. End on domestic odd-couple beat."},
        ],
        [
            {"speaker": "Lua", "text": "먹어.", "segment_order": 2},
            {"speaker": "Lua", "text": "아니, 바다에서 왔잖아.", "segment_order": 2},
            {"speaker": "Lua", "text": "생선 안 먹어?", "segment_order": 2},
            {"speaker": "Lua", "text": "입맛도 귀족이네.", "segment_order": 4},
        ],
        {"start_state": "Mir in basin calm.", "end_state": "Mir prefers shell over fish.", "carry_to_next": ["Shell prop", "Mir calmer", "Lua learning Mir's tastes"]},
        build_global_prompt("EP01 S#4 Lua house day", "Feeding failed, shell comfort", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Same day house interior", "Table with shells and dried fish"]),
        scenario_span="L531-L557",
        narrative_purpose="Show Mir is not ordinary; build comedy warmth.",
        shot_type="Domestic comedy",
        summary="EP01 S#4 — fish rejected, Mir loves shell.",
        previous_clip="SC01-004_01",
        next_clip="SC01-004_03",
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_03", 3, 18,
        "BG_EP01_LUA_HOUSE_IMAGINED_VILLAGE",
        "Imagined village rejection — off-screen adult voices.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 4, "prompt": "Character preparation: Picture 1 Lua checks wrist mark, tries to hide it with cloth. Picture 2 Young Mir watches from basin."},
            {"order": 2, "seconds": 5, "prompt": "Imagination shift: desaturated overlay — ghostly village shore shapes blur at edges. Imagined off-screen voices in natural Korean shout — \"불길하다!\" \"바다에 돌려보내!\" Picture 2 Young Mir flinches as if thrown into basket in her mind."},
            {"order": 3, "seconds": 5, "prompt": "Reaction: Picture 1 Lua snaps back to reality, blocks Picture 2 Young Mir protectively — says in natural Korean, \"안 돼.\""},
            {"order": 4, "seconds": 4, "prompt": "Recovery transition: imagination fades to normal house day lighting. Picture 2 Young Mir looks up at Picture 1 Lua trustingly. End on her protective posture."},
        ],
        [
            {"speaker": "Imagined adult (off-screen)", "text": "불길하다!", "segment_order": 2},
            {"speaker": "Imagined adult (off-screen)", "text": "바다에 돌려보내!", "segment_order": 2},
            {"speaker": "Lua", "text": "안 돼.", "segment_order": 3},
        ],
        {"start_state": "Lua hides wrist mark.", "end_state": "Lua decides to protect Mir.", "carry_to_next": ["Protection promise next clip", "Fear of village", "Imagined rejection memory"]},
        build_global_prompt("EP01 S#4 imagined rejection", "Lua imagines village fear", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Stylized imagined village overlay", "Literal house returns after beat"]),
        scenario_span="L559-L579",
        narrative_purpose="Externalize Lua's fear of village rejection.",
        shot_type="Imagined sequence",
        summary="EP01 S#4 — imagined adults reject Mir; Lua refuses.",
        previous_clip="SC01-004_02",
        next_clip="SC01-004_04",
    )
)

CLIPS.append(
    clip(
        "SC01-004", "SC01-004_04", 4, 22,
        "BG_EP01_LUA_HOUSE_INTERIOR_DAY",
        "Promise to hide, water droplet, marks react.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 6, "prompt": "Dialogue beat: Picture 1 Lua clears throat pretending to be adult — says in natural Korean, \"그러니까… 당분간 여기 있어.\" Picture 2 Young Mir tilts head. \"근데 밥값은 해야 돼.\" points at water jar — \"예를 들면.\" \"물 좀 데워준다든가?\""},
            {"order": 2, "seconds": 5, "prompt": "Main action: Picture 2 Young Mir opens small mouth. Picture 1 Lua waits hopeful. Instead he creates one tiny water droplet floating briefly."},
            {"order": 3, "seconds": 6, "prompt": "Reaction: droplet lands on Picture 1 Lua's forehead. She freezes eyes closed — says in natural Korean, \"그래.\" pause — \"가능성은 있다.\" Small laugh between them."},
            {"order": 4, "seconds": 5, "prompt": "Consequence: Picture 2 Young Mir's chest mark flashes; Picture 1 Lua's wrist mark responds. Both freeze sensing connection. Hold warm beat."},
        ],
        [
            {"speaker": "Lua", "text": "그러니까… 당분간 여기 있어.", "segment_order": 1},
            {"speaker": "Lua", "text": "근데 밥값은 해야 돼.", "segment_order": 1},
            {"speaker": "Lua", "text": "예를 들면.", "segment_order": 1},
            {"speaker": "Lua", "text": "물 좀 데워준다든가?", "segment_order": 1},
            {"speaker": "Lua", "text": "그래.", "segment_order": 3},
            {"speaker": "Lua", "text": "가능성은 있다.", "segment_order": 3},
        ],
        {"start_state": "Lua protecting Mir after imagination.", "end_state": "Marks react together; bond felt.", "carry_to_next": ["Hidden custody agreed", "Marks linked", "Night transition ahead"]},
        build_global_prompt("EP01 S#4 Lua house day", "Hide promise and droplet", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Same day house interior", "Water jar prop"]),
        scenario_span="L581-L631",
        narrative_purpose="Secret pact and first tiny miracle.",
        shot_type="Warm character beat",
        summary="EP01 S#4 — hide promise, water droplet, marks flash.",
        previous_clip="SC01-004_03",
        next_clip="SC01-005_01",
    )
)

# --- SC01-005 ---
CLIPS.append(
    clip(
        "SC01-005", "SC01-005_01", 1, 16,
        "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "Night house — Lua and Mir sleep, marks glow.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Environment establishing: dark quiet house interior at night. Picture 1 Lua asleep in bed. Picture 2 Young Mir curled in water basin."},
            {"order": 2, "seconds": 6, "prompt": "Anticipation: faint synchronized glow from Picture 2 Young Mir's chest mark and Picture 1 Lua's wrist mark beneath cloth. Their breathing slows in parallel."},
            {"order": 3, "seconds": 5, "prompt": "Transition: Picture 2 Young Mir trembles in sleep. Picture 1 Lua's brow furrows in shared disturbance. Camera pushes slightly closer. End ready to enter dream."},
        ],
        [],
        {"start_state": "Night after first day together.", "end_state": "Both entering disturbed sleep.", "carry_to_next": ["Night interior", "Glowing marks", "Dream incoming"]},
        build_global_prompt("EP01 S#5 Night", "Sleep setup", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Dark house night interior", "Bed and basin positions"]),
        scenario_span="L637-L651",
        narrative_purpose="Bridge to shared nightmare.",
        shot_type="Quiet setup",
        summary="EP01 S#5 — night sleep, marks glow, trembling begins.",
        previous_clip="SC01-004_04",
        next_clip="SC01-005_02",
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_02", 2, 22,
        "BG_EP01_MIR_VISION_PALACE_RUINS",
        "Mir's nightmare dream — ruined palace, prince shadow, Deep Sea King.",
        [ref("young_mir", 1)],
        [
            {"order": 1, "seconds": 6, "prompt": "Dream establishing: ruined dragon palace, broken hall, black roots wrapped around a fading blue heart-stone. Picture 1 Young Mir stands small before it."},
            {"order": 2, "seconds": 6, "prompt": "Anticipation: behind Picture 1 Young Mir, enormous prince-dragon shadow with crown-like horn and long body — silhouette only, no full reveal."},
            {"order": 3, "seconds": 5, "prompt": "Dialogue: disembodied low voice in natural Korean, no visible mouth — says in natural Korean, \"너는 왕자가 아니다.\" Picture 1 Young Mir shudders."},
            {"order": 4, "seconds": 5, "prompt": "Consequence: same voice says in natural Korean, \"버려진 새끼 용이다.\" Picture 1 Young Mir trembles violently. Dream begins cracking back to reality."},
        ],
        [
            {"speaker": "Deep Sea King", "text": "너는 왕자가 아니다.", "segment_order": 3},
            {"speaker": "Deep Sea King", "text": "버려진 새끼 용이다.", "segment_order": 4},
        ],
        {"start_state": "Mir dreaming.", "end_state": "Nightmare peak; waking imminent.", "carry_to_next": ["Deep Sea King rejection words", "Prince shadow silhouette", "Fear for Mir"]},
        build_global_prompt("EP01 S#5 Nightmare dream", "Mir dream palace", ["Picture 1 = Young Mir"], ["Dream palace ruins bg", "Black roots on heart-stone", "Prince shadow silhouette only"]),
        scenario_span="L653-L679",
        narrative_purpose="Separate dream from house reality; echo cold open vision once.",
        shot_type="Nightmare dream",
        summary="EP01 S#5 — Mir's nightmare, Deep Sea King rejection.",
        previous_clip="SC01-005_01",
        next_clip="SC01-005_03",
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_03", 3, 22,
        "BG_EP01_LUA_HOUSE_INTERIOR_NIGHT",
        "Lua wakes, comforts Mir, fear transfers.",
        [ref("lua", 1), ref("young_mir", 2)],
        [
            {"order": 1, "seconds": 5, "prompt": "Recovery from dream cut: Picture 2 Young Mir shaking in basin. Picture 1 Lua jolts awake — says in natural Korean, \"뭐야…\""},
            {"order": 2, "seconds": 6, "prompt": "Comfort action: Picture 1 Lua lifts Picture 2 Young Mir from basin into her arms — says in natural Korean, \"야. 괜찮아.\" \"나 여기 있어.\""},
            {"order": 3, "seconds": 6, "prompt": "Fear transfer: Picture 1 Lua clutches her chest as foreign dread hits. internal voice-over in natural Korean — \"이거…\" pause — \"내 무서움이 아니야.\" She holds Picture 2 Young Mir tighter — says in natural Korean, \"너도 무서운 거구나.\""},
            {"order": 4, "seconds": 5, "prompt": "Reaction: Picture 2 Young Mir gently licks Picture 1 Lua's wrist mark. Mark glows softly. Picture 1 Lua notices ocean sound vanished. She turns toward window."},
        ],
        [
            {"speaker": "Lua", "text": "뭐야…", "segment_order": 1},
            {"speaker": "Lua", "text": "야. 괜찮아.", "segment_order": 2},
            {"speaker": "Lua", "text": "나 여기 있어.", "segment_order": 2},
            {"speaker": "Lua (internal)", "text": "이거…", "segment_order": 3},
            {"speaker": "Lua (internal)", "text": "내 무서움이 아니야.", "segment_order": 3},
            {"speaker": "Lua", "text": "너도 무서운 거구나.", "segment_order": 3},
        ],
        {"start_state": "Mir nightmare bleeding to reality.", "end_state": "Lua holds Mir; notices silent sea.", "carry_to_next": ["Lua at window next", "Shared fear established", "Marks glowing"]},
        build_global_prompt("EP01 S#5 Night house", "Comfort and fear transfer", ["Picture 1 = Lua", "Picture 2 = Young Mir"], ["Night house interior", "Basin and bed"]),
        scenario_span="L681-L725",
        narrative_purpose="Lua feels Mir's fear — bond deepens.",
        shot_type="Emotional interior",
        summary="EP01 S#5 — wake, comfort, fear transfer.",
        previous_clip="SC01-005_02",
        next_clip="SC01-005_04",
    )
)

CLIPS.append(
    clip(
        "SC01-005", "SC01-005_04", 4, 20,
        "BG_EP01_NIGHT_SEA_JELLYFISH",
        "Black jellyfish outside window, final EP01 hook.",
        [ref("lua", 1), ref("young_mir", 2), ref("jellyfish", 3)],
        [
            {"order": 1, "seconds": 5, "prompt": "Environment shift: Picture 1 Lua approaches window. Outside night sea unnaturally still. Picture 3 Black Jellyfish floats — semi-transparent dark bell with ink smoke inside, long tentacles below surface."},
            {"order": 2, "seconds": 5, "prompt": "Reaction: Picture 2 Young Mir growls low — first warning sound. Picture 1 Lua tense, protective arm around him."},
            {"order": 3, "seconds": 5, "prompt": "Dialogue: Picture 1 Lua whispering in natural Korean — \"저게…\" pause — \"널 찾으러 온 거야?\""},
            {"order": 4, "seconds": 5, "prompt": "Consequence and fade: Picture 2 Young Mir's chest mark and Picture 1 Lua's wrist mark flash together. Picture 3 Black Jellyfish turns orientation toward the house. Hold then fade to black — EP01 end."},
        ],
        [
            {"speaker": "Lua", "text": "저게…", "segment_order": 3},
            {"speaker": "Lua", "text": "널 찾으러 온 거야?", "segment_order": 3},
        ],
        {"start_state": "Lua at window, sea silent.", "end_state": "Jellyfish turns toward house; fade out.", "carry_to_next": ["EP02 hook — jellyfish threat", "Marks reacted", "Hunter arrived"]},
        build_global_prompt("EP01 S#5 Jellyfish hook", "Black jellyfish reveal", ["Picture 1 = Lua", "Picture 2 = Young Mir", "Picture 3 = Black Jellyfish"], ["Night sea through window", "Single black jellyfish", "Still ominous ocean"]),
        scenario_span="L727-L761",
        narrative_purpose="EP01 cliffhanger — hunter arrives.",
        shot_type="Horror reveal",
        summary="EP01 S#5 end — black jellyfish at window, fade out.",
        previous_clip="SC01-005_03",
        next_clip=None,
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
        lines.append(f"- **Segment {seg['order']} ({seg['seconds']}s):** {seg['prompt']}")
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


def main() -> int:
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

    status_counts = {"reviewed": 0, "awaiting_background": 0, "needs_confirmation": 0, "invalid": 0}
    for item in CLIPS:
        status_counts[item["payload"]["status"]] = status_counts.get(item["payload"]["status"], 0) + 1

    scene_times: dict[str, float] = {}
    for item in CLIPS:
        sid = item["payload"]["scene_id"]
        scene_times[sid] = scene_times.get(sid, 0) + item["payload"]["requested_seconds"]

    manifest = {
        "schema_version": 1,
        "project_id": PROJECT_ID,
        "title": "Raising a Dragon Season 1 — EP01 V2",
        "description": "EP01 바다에서 주운 용 — MSR V2 prompt project rewrite (English visual prompts, Korean dialogue preserved)",
        "scenario_source": SCENARIO,
        "episode_coverage": ["EP01"],
        "supersedes_project": "RaisingaDragonSeason01",
        "policy": {
            "language": "English visual prompts; Korean spoken dialogue only",
            "max_clip_seconds": 30,
            "target_clip_seconds": "18-28",
            "target_total_seconds_range": [330, 420],
        },
        "scene_count": len(scene_times),
        "clip_count": len(CLIPS),
        "total_requested_seconds": total_seconds,
        "scene_requested_seconds": scene_times,
        "status_summary": status_counts,
        "notes": [
            "V2 rewrite — original RaisingaDragonSeason01 project preserved untouched.",
            "All clips awaiting_background until background PNGs are linked.",
            "Reference PNGs must exist under RaisingaDragonSeason01/ for reviewed status.",
            "Split cold open, dream, and imagination beats into separate backgrounds.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {len(CLIPS)} clips, {total_seconds}s total -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
