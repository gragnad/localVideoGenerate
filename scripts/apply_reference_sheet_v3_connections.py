#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from h3_prompt_projects import extract_payload, project_clips
from scripts.build_reference_requirement_audit_v3 import decision


PROJECT_IDS = (
    "RaisingaDragonSeason01_EP00_H3_R2V_V2",
    "RaisingaDragonSeason01_EP01_H3_R2V_V2",
)

DISPLAY_RE = re.compile(
    r"(## Final English H3 R2V Prompt\s*```text\s*)([\s\S]*?)(\s*```)",
)
PAYLOAD_RE = re.compile(
    r"(## Machine Payload\s*```json\s*)(\{[\s\S]*?\})(\s*```)",
)
PICTURE_PLAN_RE = re.compile(
    r"(## Picture Plan\n)([\s\S]*?)(?=\n## Final English H3 R2V Prompt)",
)
SECTION_RE = re.compile(
    r"^(subject_definitions|summary|retention_analysis|detailed_description|overall_soundscape|non_diegetic_music):$",
    re.M,
)


def section_map(prompt: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(prompt))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        result[match.group(1)] = prompt[match.end():end].strip()
    return result


def sheet_kind(path: str) -> str:
    if "/characters/" in path:
        return "multi-view character identity reference sheet"
    if "/creatures/" in path:
        return "multi-view creature identity reference sheet"
    if "/relationships/" in path:
        return "multi-view scale-and-contact relationship reference sheet"
    if "/props/" in path:
        return "multi-view prop design reference sheet"
    if "/enemies/" in path:
        return "multi-view partial-threat design reference sheet"
    if "/effects/" in path:
        return "multi-view VFX design reference sheet"
    if "/details/" in path:
        return "multi-view body-attached detail reference sheet"
    return "multi-view design reference sheet"


def normalize_reference(reference: dict, target: str, clip_id: str) -> dict:
    row = deepcopy(reference)
    row["source_path"] = target
    label = str(row.get("label") or row.get("role") or "Reference")
    if clip_id.startswith("EP00-") and target.endswith("Deep_Sea_King_Full_Reference_NEUTRAL_V2.png"):
        row["role"] = "enemy_full_identity"
        row["label"] = "Deep Sea King"
        row["description"] = (
            "Preserve one colossal Deep Sea King identity, its branching crown, ribbed torso, long arms and the continuous "
            "root-tendril mantle physically extending from the same body. Use this Picture only as a four-panel full-identity sheet."
        )
    elif "/enemies/" in target:
        row["role"] = "enemy_partial_threat"
        if "TAIL_FRAGMENT" in target:
            label = "Abyss Hound incomplete tail fragment"
            detail = "Only the incomplete tail or tentacle-end material and hooked tip are authored for the frame; the connected body remains outside the scene."
        elif "JAW_EDGE" in target:
            label = "Abyss Hound jaw-edge fragment"
            detail = "Only the incomplete jaw or head-edge fragment and its wet-black hooked structures are authored for the frame."
        else:
            label = "Deep Sea King root-mantle fragment"
            detail = "Only the exposed root, mantle and upper-edge fragment material is authored; this is not a full-body identity source."
        row["label"] = label
        row["description"] = f"{detail} Use this Picture only as a four-panel design sheet and do not stage its panels or gray canvas."
    elif "/effects/" in target:
        row["role"] = "effect_identity"
        if "FLOOR" in target:
            label = "Horizontal floor current ring"
            detail = "Preserve one flat floor-parallel cyan-white circular current ring and its translucent water structure."
        else:
            label = "Vertical directional current shield"
            detail = "Preserve one upright cyan-white directional water shield and its translucent water structure."
        row["label"] = label
        row["description"] = f"{detail} Use this Picture only as a four-panel VFX design sheet and do not stage its panels or gray canvas."
    elif "/details/" in target:
        row["role"] = "detail_identity"
        row["description"] = "Preserve the exact wrist placement, symbol geometry and cyan-white luminous material at the authored stage. Use this Picture only as a four-panel body-detail design sheet."
    elif "/relationships/" in target:
        held = "HELD" in target
        row["role"] = "lua_mir_scale_held" if held else "lua_mir_scale_separate"
        row["description"] = (
            "Preserve Lua and Young Mir's exact relative scale and the held support contact in every authored view. "
            if held else
            "Preserve Lua and Young Mir's exact relative scale and the clear separate state in every authored view. "
        ) + "Use this Picture only as a four-panel relationship sheet."
    elif "/props/" in target:
        row["description"] = f"Preserve the exact {label} proportions, construction, colors and materials. Use this Picture only as a four-panel prop design sheet."
    elif "/characters/" in target or "/creatures/" in target:
        row["description"] = f"Preserve the exact {label} identity, age or anatomy, proportions, colors, clothing and materials. Use this Picture only as a four-panel identity sheet."
    return row


def category(row: dict) -> tuple[int, int]:
    role = str(row.get("role") or "")
    path = str(row.get("source_path") or "")
    original = int(row["_old_index"])
    if role.startswith("environment") or path.startswith("backgrounds/"):
        return 0, original
    if "/characters/" in path or "/creatures/" in path or role in {"lua", "young_mir", "old_fisherman"} or role.startswith("village_"):
        return 1, original
    if "/relationships/" in path or "scale_" in role:
        return 2, original
    if "/props/" in path or "spear" in role or role in {"owned_prop", "heartstone"}:
        return 3, original
    if "/enemies/" in path or role.startswith("enemy"):
        return 4, original
    if "/effects/" in path or role == "effect_identity":
        return 5, original
    if "/details/" in path or "mark" in role:
        return 6, original
    return 7, original


def dropped_phrase(project_id: str, source_path: str) -> str:
    if "Wrist_Mark" in source_path:
        return "Lua's wrist mark"
    if "Current_Shield_Effects" in source_path:
        return "the authored cyan current"
    if "Deep_Sea_King_Full" in source_path:
        return "the incomplete hostile root shadow"
    return "the authored visual event"


def dropped_phrase_for_clip(project_id: str, clip_id: str, source_path: str) -> str:
    if project_id.endswith("EP00_H3_R2V_V2") and clip_id.startswith("EP00-S04-") and "Deep_Sea_King_Full" in source_path:
        return "the immense chamber-root structure"
    return dropped_phrase(project_id, source_path)


def replace_tags(text: str, old_to_new: dict[int, int], removed: dict[int, str]) -> str:
    for old in sorted(set(old_to_new) | set(removed), reverse=True):
        if old in old_to_new:
            text = text.replace(f"<Subject {old}>", f"<SUBJECT_TMP_{old_to_new[old]}>")
            text = text.replace(f"<Picture {old}>", f"<PICTURE_TMP_{old_to_new[old]}>")
        else:
            text = text.replace(f"<Subject {old}>", removed[old])
            text = text.replace(f"<Picture {old}>", removed[old])
    text = re.sub(r"<SUBJECT_TMP_(\d+)>", r"<Subject \1>", text)
    text = re.sub(r"<PICTURE_TMP_(\d+)>", r"<Picture \1>", text)
    return text


def subject_definition(index: int, row: dict) -> str:
    label = str(row.get("label") or row.get("role") or f"Reference {index}")
    path = str(row.get("source_path") or "")
    role = str(row.get("role") or "")
    if role.startswith("environment") or path.startswith("backgrounds/"):
        return f"<Subject {index}>: {label}; use <Picture {index}> as the authored three-dimensional environment anchor, preserving its topology, landmarks, contact plane, depth, light direction and camera axis."
    if role == "enemy_full_identity":
        return (
            f"<Subject {index}>: {label}; use <Picture {index}> as its four-panel full-identity reference sheet. "
            "Preserve one colossal wet-black humanoid, branching crown, ribbed torso, long arms and a continuous root-tendril mantle physically growing from the same body."
        )
    if path.endswith("Lua_Eye_Cave_Reflection_V1.png"):
        return f"<Subject {index}>: {label}; use <Picture {index}> as the authored semantic eye-reflection insert, preserving the eye and reflected cave event information."
    kind = sheet_kind(path)
    extra = ""
    if "TAIL_FRAGMENT" in path:
        extra = " Preserve only the incomplete tail or tentacle-end fragment; the connected body stays outside the scene."
    elif "JAW_EDGE" in path:
        extra = " Preserve only the incomplete jaw or head-edge fragment."
    elif "ROOT_MANTLE" in path:
        extra = " Preserve only the exposed root and mantle fragment, not a full-body identity."
    elif "FLOOR" in path:
        extra = " Preserve one horizontal floor-parallel ring orientation."
    elif "VERTICAL" in path:
        extra = " Preserve one upright directional shield orientation."
    elif "HELD" in path:
        extra = " Preserve the held state and relative scale in every use."
    elif "SEPARATE" in path:
        extra = " Preserve the separate state and relative scale in every use."
    return (
        f"<Subject {index}>: {label}; use <Picture {index}> only as its {kind}."
        f"{extra} Never reproduce the sheet panels, dividers, flat gray canvas or multiple authored views in the scene."
    )


def rebuild_prompt(prompt: str, rows: list[dict], old_to_new: dict[int, int], removed: dict[int, str]) -> str:
    sections = section_map(prompt)
    definitions = "\n".join(subject_definition(i, row) for i, row in enumerate(rows, 1))
    summary = replace_tags(sections["summary"], old_to_new, removed)

    retention_lines: list[str] = []
    for line in sections["retention_analysis"].splitlines():
        match = re.match(r"<Subject (\d+)>", line)
        if not match or int(match.group(1)) not in removed:
            retention_lines.append(replace_tags(line, old_to_new, removed))
    retention_lines.sort(
        key=lambda line: int(re.match(r"<Subject (\d+)>", line).group(1))
        if re.match(r"<Subject (\d+)>", line)
        else 10_000
    )
    retention = "\n".join(retention_lines)
    detail = replace_tags(sections["detailed_description"], old_to_new, removed)

    return (
        f"subject_definitions:\n{definitions}\n\n"
        f"summary:\n{summary}\n\n"
        f"retention_analysis:\n{retention}\n\n"
        f"detailed_description:\n{detail}\n\n"
        f"overall_soundscape:\n{sections['overall_soundscape']}\n\n"
        f"non_diegetic_music:\n{sections['non_diegetic_music']}"
    )


def nc01_restore(prompt: str) -> str:
    prompt = re.sub(
        r"CONNECTED ENEMY FRAMING / POST-PRODUCTION LOCK:[\s\S]*?END CONNECTED ENEMY FRAMING / POST-PRODUCTION LOCK\.",
        "PARTIAL THREAT / OFF-FRAME BODY LOCK:\nUse the incomplete tail-fragment reference only for the visible hooked end and wet-black surface. Only an incomplete tentacle or tail tip enters from frame-left. The connected body remains outside the scene and is never revealed.\nEND PARTIAL THREAT / OFF-FRAME BODY LOCK.",
        prompt,
    )
    replacements = {
        "connected Hound crop frame-left": "incomplete tail fragment entering at frame-left",
        "connected Hound crop behind-left": "incomplete tail fragment behind-left",
        "connected attacking appendage": "incomplete attacking tail fragment",
        "while still connected to the off-frame Hound": "while the connected body remains outside the scene",
        "The connected attacking appendage": "The incomplete attacking tail fragment",
        "connected side-view crop": "incomplete tail-fragment crop",
        "rear torso, tail base and long attacking appendage": "incomplete tail or tentacle tip",
        "rear torso-to-tail connection": "hooked tip and wet-black surface",
        "connected anatomy": "fragment anatomy",
        "one connected naturally shaded crop from a single source panel": "one incomplete naturally shaded fragment entering from the frame edge",
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    return prompt


def picture_plan(rows: list[dict]) -> str:
    return "\n".join(
        f"- Picture {index}: `{row.get('role')}` · {row.get('label')} · `{row.get('source_path')}`"
        for index, row in enumerate(rows, 1)
    ) + "\n"


def normalize_ep00_deep_sea_king(prompt: str, subject_index: int) -> str:
    replacements = {
        "Render the immense chamber-root structure as one naturally shaded connected upper-body camera crop based on the rightmost close-up panel; any silhouette treatment is post-production.": f"<Subject {subject_index}> occupies the far chamber boundary at colossal scale and every hostile root grows continuously from the same root-tendril mantle.",
        "The immense chamber-root structure is part of the authored environment and moves at architecture scale.": f"<Subject {subject_index}> occupies the far chamber boundary at colossal scale and every hostile root grows continuously from the same root-tendril mantle.",
        "while roots stay connected to the off-frame mantle": f"while every root remains connected through depth to <Subject {subject_index}>'s mantle",
        "while the enormous roots remain integrated into the surrounding chamber": f"while every root remains connected through depth to <Subject {subject_index}>'s mantle",
        "an incomplete root": f"a massive root connected to <Subject {subject_index}>'s mantle",
        "a massive chamber root": f"a massive root connected to <Subject {subject_index}>'s mantle",
        "the second fragment": "the second connected crossing root",
        "the second crossing root": "the second connected crossing root",
        "second fragment ahead-right": "second connected crossing root ahead-right",
        "second crossing root ahead-right": "second connected crossing root ahead-right",
        "two drifting fragments": "two displaced connected roots",
        "two displaced roots": "two displaced connected roots",
        "the fragment": "the connected massive root",
        "The fragment": "The connected massive root",
        "on the fragment": "on the connected massive root",
        "the incomplete roots": f"the roots connected to <Subject {subject_index}>'s mantle",
        "the immense chamber roots": f"the roots connected to <Subject {subject_index}>'s mantle",
        "supported by the authored cyan current through a visible fluid gap": "with both boots visibly loaded into two pressure troughs in the authored cyan current",
    }
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    prompt = prompt.replace(
        "ENVIRONMENTAL ROOT SCALE / CONTINUITY LOCK:\n",
        "DEEP SEA KING / COLOSSAL SINGLE-ENEMY LOCK:\n",
    ).replace(
        "Every hostile root is an enormous continuous chamber-spanning structure already integrated into the authored environment. Each visible root is several times thicker than Lua's torso and continues into stone, darkness or beyond multiple frame edges. Wet-black bark-like surfaces, branching mass and motion derive from the environment anchor and action description, keeping the roots architecture-scale throughout every cut.",
        f"<Subject {subject_index}> is one colossal Deep Sea King at the far chamber boundary. Every hostile root is a continuous extension of that same body's lower root-tendril mantle, several times thicker than Lua's torso and spanning through chamber depth, stone and frame edges. The crown, upper torso or mantle origin remains readable in wide views, establishing one body and one connected root network through every cut.",
    ).replace(
        "END ENVIRONMENTAL ROOT SCALE / CONTINUITY LOCK.",
        "END DEEP SEA KING / COLOSSAL SINGLE-ENEMY LOCK.",
    )
    prompt = re.sub(
        r"CONNECTED ENEMY FRAMING / POST-PRODUCTION LOCK:\n[\s\S]*?\nEND CONNECTED ENEMY FRAMING / POST-PRODUCTION LOCK\.",
        (
            "DEEP SEA KING / COLOSSAL SINGLE-ENEMY LOCK:\n"
            f"<Subject {subject_index}> is one colossal Deep Sea King occupying the far chamber depth. "
            "Its branching crown, ribbed torso, long arms and root-tendril mantle form one continuous wet-black body. "
            "Every attacking branch-limb remains visibly continuous through depth to that same mantle; camera framing may crop the body while its connected anatomy and monumental scale remain readable.\n"
            "END DEEP SEA KING / COLOSSAL SINGLE-ENEMY LOCK."
        ),
        prompt,
    )
    return prompt


def transform(path: Path, project_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    payload = extract_payload(text)
    clip_id = str(payload["clip_id"])
    original_refs = deepcopy(payload.get("references") or [])
    kept: list[dict] = []
    removed: dict[int, str] = {}

    for reference in original_refs:
        old_index = int(reference["picture_index"])
        source = str(reference.get("source_path") or "")
        if source.startswith("backgrounds/") or "/reference_sheets_v3/" in source:
            row = deepcopy(reference)
        else:
            verdict, target, _ = decision(project_id, clip_id, source)
            if verdict.startswith("REMOVE_"):
                removed[old_index] = dropped_phrase_for_clip(project_id, clip_id, source)
                continue
            row = normalize_reference(reference, target, clip_id)
        row["_old_index"] = old_index
        kept.append(row)

    kept.sort(key=category)
    old_to_new = {int(row["_old_index"]): index for index, row in enumerate(kept, 1)}
    for index, row in enumerate(kept, 1):
        row["picture_index"] = index
        row.pop("_old_index", None)

    prompt = rebuild_prompt(str(payload["video_prompt"]), kept, old_to_new, removed)
    prompt = prompt.replace("Lua's wrist mark provide their defined reference roles", "Lua's wrist mark provides its defined warning or charge role")
    if clip_id in {
        "EP00-S01-NC03", "EP00-S02-NC01", "EP00-S02-NC02",
        "EP00-S02-NC03", "EP00-S03-NC01", "EP00-S03-NC02",
    }:
        prompt = prompt.replace("Lua's wrist mark provides its defined warning or charge role. ", "")
        prompt = prompt.replace("Lua's wrist mark and <Subject 1> use only their defined visual roles.\n\n", "<Subject 1> uses its defined visual role.\n\n")
        prompt = prompt.replace("Lua's wrist mark use only their defined visual roles.\n\n", "")
        prompt = prompt.replace("wrist-to-shaft charge", "water-to-spear charge")
        prompt = prompt.replace("one short wrist pulse", "one short blade-tip pressure tone")
        prompt = prompt.replace("Wrist resonance", "Water-coil resonance")
        if clip_id == "EP00-S03-NC02":
            prompt = prompt.replace(", with Lua's wrist mark at its fixed origin", "")
    if project_id.endswith("EP00_H3_R2V_V2") and any(row.get("role") == "enemy_full_identity" for row in kept):
        full_index = next(i for i, row in enumerate(kept, 1) if row.get("role") == "enemy_full_identity")
        prompt = normalize_ep00_deep_sea_king(prompt, full_index)
    if clip_id == "EP00-S04-NC01":
        prompt = prompt.replace("the authored cyan current", "the narrow supporting cyan current")
        prompt = prompt.replace("the narrow supporting cyan current provide their defined reference roles. ", "")
        prompt = prompt.replace("the narrow supporting cyan current and <Subject 1> use only their defined visual roles.", "<Subject 1> uses its defined visual role.")
        prompt = prompt.replace("<Subject 3> and Lua's wrist mark provides its defined warning or charge role. ", "<Subject 3> remains protected through the recovery. ")
        prompt = prompt.replace("a narrow ankle-deep band of the narrow supporting cyan current", "a narrow ankle-deep cyan current")
        prompt = prompt.replace("A narrow ankle-deep band of the narrow supporting cyan current", "A narrow ankle-deep cyan current")
        prompt = prompt.replace("<Subject 1> use only their defined visual roles.", "<Subject 1> uses its defined visual role.")
    if clip_id == "EP00-S04-NC03":
        prompt = prompt.replace("the authored cyan current", "the narrow supporting cyan current")
        prompt = prompt.replace("the narrow supporting cyan current provide their defined reference roles. ", "")
        prompt = prompt.replace("the narrow supporting cyan current and <Subject 1> use only their defined visual roles.", "<Subject 1> uses its defined visual role.")

    payload["video_prompt"] = prompt
    payload["references"] = kept
    payload["prompt_revision"] = f"{str(payload.get('prompt_revision') or 'h3_r2v')}_reference_sheet_v3"
    payload["reference_sheet_revision"] = "standardized_four_panel_v3"
    payload["reference_pruning_revision"] = "clip_requirement_audit_v3"
    detail = section_map(prompt)["detailed_description"]
    payload["official_detail_word_count"] = len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", detail))

    if "enemy_reference_picture_index" in payload:
        old = int(payload.get("enemy_reference_picture_index") or 0)
        payload["enemy_reference_picture_index"] = old_to_new.get(old)
    if "effect_reference_picture" in payload:
        old = int(payload.get("effect_reference_picture") or 0)
        payload["effect_reference_picture"] = old_to_new.get(old)
    if project_id.endswith("EP00_H3_R2V_V2") and any(row.get("role") == "enemy_full_identity" for row in kept):
        full_index = next(i for i, row in enumerate(kept, 1) if row.get("role") == "enemy_full_identity")
        payload.pop("partial_threat_revision", None)
        payload.pop("root_reference_strategy", None)
        payload.pop("environmental_root_revision", None)
        payload["enemy_reference_identity"] = "DEEP-SEA-KING-FULL"
        payload["enemy_reference_picture_index"] = full_index
        payload["enemy_visibility_strategy"] = "colossal_single_boss_spanning_chamber_depth"
        payload["generation_enemy_treatment"] = "natural_full_identity_connected_body_render"
        payload["root_connection_strategy"] = "deep_sea_king_full_identity_connected_limbs_and_mantle"
        payload["deep_sea_king_revision"] = "single_colossal_enemy_episode00_v1"

    display = DISPLAY_RE.search(text)
    machine = PAYLOAD_RE.search(text)
    plan = PICTURE_PLAN_RE.search(text)
    if not display or not machine or not plan:
        raise RuntimeError(f"Clip structure missing: {path}")
    text = PICTURE_PLAN_RE.sub(lambda m: m.group(1) + picture_plan(kept), text, count=1)
    text = DISPLAY_RE.sub(lambda m: m.group(1) + prompt + m.group(3), text, count=1)
    text = PAYLOAD_RE.sub(
        lambda m: m.group(1) + json.dumps(payload, ensure_ascii=False, indent=2) + m.group(3),
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    for project_id in PROJECT_IDS:
        project = ROOT / "prompt_projects" / project_id
        for path in sorted(project.glob("*/*.md")):
            transform(path, project_id)
        clips = project_clips(ROOT, project_id)["clips"]
        manifest_path = project / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        refs = [reference for clip in clips for reference in clip.get("references", [])]
        v3_instances = sum("/reference_sheets_v3/" in str(reference.get("source_path") or "") for reference in refs)
        review = manifest.setdefault("asset_review", {})
        review["reference_instances"] = len(refs)
        review["linked_reference_instances"] = len(refs)
        review["mandatory_missing_assets"] = 0
        review["v3_reference_instances"] = v3_instances
        review["approved_unique_assets"] = len({str(reference.get("source_path") or "") for reference in refs})
        review["approved_new_asset_count"] = len({
            str(reference.get("source_path") or "")
            for reference in refs
            if "/reference_sheets_v3/" in str(reference.get("source_path") or "")
        })
        review["review_document"] = "REFERENCE_SHEET_VISUAL_NORMALIZATION_REVIEW_V3.md"
        if project_id.endswith("EP00_H3_R2V_V2"):
            boss_clips = [
                clip["clip_id"] for clip in clips
                if clip["clip_id"] not in {"EP00-S01-NC02", "EP00-S03-NC01", "EP00-S03-NC02"}
            ]
            manifest["single_enemy_reference_policy"] = {
                "revision": "single_colossal_deep_sea_king_episode00_v1",
                "clips": boss_clips,
                "picture_asset": "assets/enemies/Deep_Sea_King_Full_Reference_NEUTRAL_V2.png",
                "strategy": "single_full_identity_picture_with_connected_limbs_and_root_mantle",
                "rule": "Deep Sea King is the sole EP00 enemy. Its body reference is omitted in EP00-S03-NC01 and NC02, where the prior impact scar feeds three localized right-side root attack lanes before the King rises in NC03.",
            }
            manifest.pop("scene4_root_reference_policy", None)
            manifest["asset_revision"] = "ep00_single_deep_sea_king_reference_normalization_v1"
        else:
            manifest["asset_revision"] = "ep01_reference_sheet_visual_normalization_v3"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
