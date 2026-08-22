from __future__ import annotations

"""General reference-aware Qwen3-Omni reviewer for R2V benchmarks."""

import base64
from io import BytesIO
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from PIL import Image

import review_contract
import model_test_ai_reviewer as common
import vllm_reviewer as omni


RUBRIC_VERSION = "r2v_storyboard_action_flow_v7"
R2V_REVIEW_IMAGE_MAX_DIMENSION = max(
    512, int(os.environ.get("R2V_REVIEW_IMAGE_MAX_DIMENSION", "960"))
)
SCORE_KEYS = (
    "storyboard_adherence", "panel_sequence_fidelity", "camera_path_transition",
    "action_flow", "action_pacing",
    "emotional_progression",
    "prompt_understanding", "reference_adherence", "reference_role_binding", "identity_consistency",
    "prop_consistency", "event_execution", "interaction_contact",
    "visual_consistency", "temporal_quality", "camera_control", "shot_structure", "style_fidelity",
    "audio_dialogue", "overall_visual_quality",
)

SYSTEM_PROMPT = r"""
You are a storyboard-aware, reference-grounded evaluator for R2V video benchmarks.
You receive the complete generated video, ordered visual references, a text execution prompt,
role-limited reference contracts, storyboard panel contracts when available, and text shot guidance.

Keep six questions separate. When a storyboard is supplied, question 1 is the primary decision axis:
1. Storyboard adherence: did the video reproduce every ordered panel's action state, subject placement,
   scale relationship, prop/effect state and emotional beat in the declared reading order?
2. Reference adherence: did the output preserve only what each non-storyboard visual reference defines?
3. Prompt understanding: did the video interpret the requested scenario, relationships and ending?
4. Action execution: did the required motion, causal order and physical contact occur?
5. Visual consistency: did identities, props, environment, style and temporal rendering remain stable?
6. Camera and shot structure: did the shot boundaries support the storyboard rather than replace it?

Reference discipline:
- Evaluate every supplied visual reference exactly once and in Picture order.
- Character sheets define identity, face, silhouette, proportions, wardrobe and palette only.
- Environment plates define geometry, landmarks, lighting language and action space only.
- Prop and creature sheets define shape, material, anatomy, scale and ownership only as declared.
- A reference sheet may contain several views of one design; do not count those views as duplicates.
- A storyboard sheet is different from a character or prop sheet. Read its panels in the declared order
  and compare each panel with the corresponding video interval. Do not treat its repeated characters as
  duplicate scene instances.
- For every storyboard panel, judge the complete checkpoint: composition, relative placement and scale,
  pose and contact, prop/effect state, facial emotion, and the physical result that leads to the next panel.
- Exact pixel copying is not required. Small framing drift is minor only when the panel's action state,
  emotional beat, spatial relationship and transition remain clearly recognizable.
- A missing, reordered or contradicted storyboard panel is a hard storyboard failure. Rendering the 2x2
  grid, gutters, captions or simultaneous panel layout inside the video is also a hard failure.
- Storyboard panels are checkpoints inside one continuous video, not four unrelated restarts. Verify that
  contact force, motion vector, velocity, foot displacement and accumulated shield damage carry across cuts.
- If a later shot re-establishes a held pose, repeats preparation, restores contact or resets damage instead
  of continuing the prior shot's active motion, mark action_flow_status contradicted.
- Never demand an unmentioned pose, action, camera move, background, or exact frame copy from a sheet.
- Keep identity, environment, creature and prop roles separate. Do not transfer a trait between roles.
- Use matched, minor_drift, major_mismatch, or uncertain. Uncertain is not a failure.

Prompt, action and shot discipline:
- The storyboard and text execution prompt jointly define the scenario, action checkpoints and shot order.
- Evaluate each declared [Shot N] as a textual instruction. Verify shot count and order, cut timing/rhythm,
  viewpoint/framing, subject placement, requested camera motion, screen direction and ending state.
- A missing or reordered required shot is a hard structural contradiction. Small timing, framing or camera
  amplitude differences are minor drift when the intended action boundaries and order remain readable.
- Verify action preparation, execution, contact or avoidance, consequence and recovery separately when
  requested. Do not infer successful contact from intent alone.
- Judge spatial causality across cuts: subject identity, scale, screen direction, prop ownership and action
  state must carry over unless the prompt explicitly changes them.
- Judge requested action pace separately. Unrequested slow motion, long static holds, or delayed preparation
  that makes a fast action read as sluggish is a pacing contradiction; compact motion blur is not a defect.

Genre calibration:
- stylized_3d: judge designed proportions, silhouette, materials, readable contact and animation
  continuity; do not demand photoreal skin.
- live_action: judge stable face/skin/hands, natural motion blur, practical lighting and coherent VFX.
- hand_drawn_2d: judge line/color/cel consistency and recovery after intentional smear frames;
  intentional smear, held drawings and stepped timing are not defects by themselves.

Evidence and decision discipline:
- The prompt and references are intent, never proof. Cite narrow video timestamps.
- Distinguish observed contradiction from uncertainty or limited visibility.
- Do not reject because a detail is occluded, too small, or genuinely unverifiable.
- A negative identity/reference judgment needs a concrete visible mismatch, not a general impression.
- Reject only for a critical unusable defect, a clearly contradicted core event, an observed forbidden
  failure, or a clearly evidenced major mismatch of a required identity/role.
- Use needs_improvement or human_review_required for uncertainty.
- acceptable requires no major/critical issue, no contradicted core event, no observed forbidden
  failure, and no major reference mismatch.
- Scores are 0-5; use null when a dimension is not exercised.
- For every declared dialogue line, verify the bound Subject, stable speaker ID, exact Korean words,
  line order, lip sync and non-speakers' closed mouths. Do not infer a contradiction without audible
  or visible evidence; use uncertain when transcription or lips are not verifiable.
- Evaluate every declared Subject role once. Keep identity, environment, creature and prop roles separate.
- If the text prompt explicitly contains multiple [Shot N] instructions, a generic rule that merely bans
  scene cuts is obsolete and must not be counted as a failure. Still report unintended or missing cuts
  through the structured shot-count/order and cut-timing checks.
- Verify shot count/order, cut timing, screen direction and camera-plan adherence as separate checks.
- When the prompt treats storyboard panels as camera waypoints, verify that the camera visibly travels or
  uses the requested action-motivated occlusion toward the next panel composition; a direct reset at the
  destination is not successful camera-path execution.
- Keep Korean notes and evidence concise (each at most 240 characters) and return at most 8 highest-value issues.
- Begin the JSON immediately. Do not emit analysis, reasoning, markdown or <think> tags.
- Return one complete JSON object and no prose outside it.

Schema:
{
  "verdict":"acceptable|needs_improvement|reject|unrated",
  "confidence":0.0,
  "human_review_required":false,
  "positive_note":"Korean factual strengths",
  "overall_note":"Korean evidence-based summary",
  "scores":{
    "storyboard_adherence":0,"panel_sequence_fidelity":0,"camera_path_transition":0,
    "action_flow":0,"action_pacing":0,
    "emotional_progression":0,
    "prompt_understanding":0,"reference_adherence":0,"reference_role_binding":0,"identity_consistency":0,
    "prop_consistency":null,"event_execution":0,"interaction_contact":null,
    "visual_consistency":0,"temporal_quality":0,"camera_control":null,"shot_structure":0,"style_fidelity":0,
    "audio_dialogue":null,"overall_visual_quality":0
  },
  "reference_checks":[
    {"picture_index":1,"role":"","status":"matched|minor_drift|major_mismatch|uncertain",
     "evidence_ko":"","role_limit_ko":"","reference_kind":"visual_reference|storyboard",
     "panel_beat_checks":[
       {"panel_index":1,"status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
        "evidence_ko":"","start_seconds":0.0,"end_seconds":0.0}
     ]}
  ],
  "dialogue_checks":[
    {"speaker":"A","subject_index":1,"speaker_id":"S1","line_ko":"",
     "exact_text_status":"verified|contradicted|uncertain|not_verifiable",
     "speaker_identity_status":"verified|contradicted|uncertain|not_verifiable",
     "order_status":"verified|contradicted|uncertain|not_verifiable",
     "lip_sync_status":"verified|contradicted|uncertain|not_verifiable",
     "non_speaker_mouth_status":"verified|contradicted|uncertain|not_verifiable",
     "evidence_ko":"","start_seconds":0.0,"end_seconds":0.0}
  ],
  "subject_binding_checks":[
    {"subject_index":1,"picture_index":1,"status":"matched|minor_drift|major_mismatch|uncertain",
     "evidence_ko":"","role_limit_ko":""}
  ],
  "shot_structure_check":{
    "shot_count_order_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "cut_timing_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "screen_direction_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "camera_plan_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "action_flow_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "pacing_status":"verified|minor_drift|contradicted|uncertain|not_verifiable",
    "storyboard_layout_leak":"absent|observed|uncertain|not_verifiable",
    "evidence_ko":""
  },
  "event_checks":[
    {"requirement_ko":"","status":"verified|contradicted|uncertain|not_verifiable",
     "evidence_ko":"","start_seconds":0.0,"end_seconds":0.0}
  ],
  "forbidden_checks":[
    {"failure_ko":"","status":"absent|observed|uncertain","evidence_ko":"",
     "start_seconds":0.0,"end_seconds":0.0}
  ],
  "issues":[
    {"issue_id":"r2v_issue_01","category":"other","subcategory":"other",
     "severity":"minor|major|critical","start_seconds":0.0,"end_seconds":0.0,
     "expected":"","observed":"","difference":"","cause_hypothesis":"","suggestion":""}
  ]
}
""".strip()


def _is_storyboard_slot(item: dict[str, Any]) -> bool:
    return (
        str(item.get("reference_kind") or "").lower() == "storyboard"
        or "스토리보드" in str(item.get("label_ko") or "")
        or "storyboard" in str(item.get("instruction_en") or "").lower()
    )


def _visual_references(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(references)


def _general_review_prompt(prompt: str) -> str:
    """Preserve storyboard instructions because they are part of the review evidence."""
    return str(prompt or "").strip()


def _expected_shot_count(prompt: str, shot_guidance: list[dict[str, Any]]) -> int:
    shot_numbers = {
        int(value) for value in re.findall(r"\[Shot\s+(\d+)\]", str(prompt or ""), re.IGNORECASE)
    }
    guidance_numbers = {
        int(item.get("shot_index") or 0)
        for item in shot_guidance if isinstance(item, dict) and int(item.get("shot_index") or 0) > 0
    }
    return max(shot_numbers | guidance_numbers | {1})


def _review_reference_data_url(path: Path) -> str:
    """Encode a bounded review copy without modifying the source asset."""
    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    try:
        with Image.open(path) as source:
            width, height = source.size
            if max(width, height) <= R2V_REVIEW_IMAGE_MAX_DIMENSION:
                encoded = raw
            else:
                image = source.copy()
                image.thumbnail(
                    (R2V_REVIEW_IMAGE_MAX_DIMENSION, R2V_REVIEW_IMAGE_MAX_DIMENSION),
                    Image.Resampling.LANCZOS,
                )
                if image.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
                    image = image.convert("RGB")
                buffer = BytesIO()
                image.save(buffer, format="PNG", optimize=True)
                encoded = buffer.getvalue()
                mime = "image/png"
    except (OSError, ValueError):
        # Tests and legacy assets may not contain decodable image bytes. The
        # downstream model remains the authority for whether media is valid.
        encoded = raw
    return f"data:{mime};base64,{base64.b64encode(encoded).decode('ascii')}"


def _reference_media(request: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    contract = request.get("benchmark_contract") or {}
    slots = {
        int(item.get("picture_index") or 0): item
        for item in (contract.get("reference_slots") or [])
        if (
            isinstance(item, dict)
            and int(item.get("picture_index") or 0) > 0
        )
    }
    media: list[dict[str, str]] = []
    descriptions: list[dict[str, Any]] = []
    for asset in sorted(
        (item for item in (request.get("assets") or []) if isinstance(item, dict)),
        key=lambda item: int(item.get("picture_index") or str(item.get("role") or "0").rsplit("_", 1)[-1] or 0),
    ):
        role = str(asset.get("role") or "")
        try:
            index = int(asset.get("picture_index") or role.rsplit("_", 1)[-1])
        except (TypeError, ValueError):
            continue
        slot = slots.get(index)
        if slot is None:
            continue
        path = Path(str(asset.get("source_path") or ""))
        if not path.is_file():
            raise FileNotFoundError(f"R2V 검수 참조 이미지가 없습니다: {path}")
        url = _review_reference_data_url(path)
        label = str(slot.get("label_ko") or role)
        role_limit = str(slot.get("instruction_en") or "")
        reference_kind = (
            "storyboard" if _is_storyboard_slot(slot) else "visual_reference"
        )
        media_label = f"<Picture {index}> {label} · kind: {reference_kind} · role limit: {role_limit}"
        media.append({"label": media_label, "url": url})
        descriptions.append({
            "picture_index": index,
            "role": role,
            "label_ko": label,
            "role_limit_en": role_limit,
            "reference_kind": reference_kind,
            "shared_asset_key": slot.get("shared_asset_key"),
            "sha256": asset.get("sha256"),
            **(
                {
                    "storyboard_panel_count": int(slot.get("storyboard_panel_count") or 0),
                    "storyboard_reading_order": str(slot.get("storyboard_reading_order") or ""),
                    "storyboard_beats": list(slot.get("storyboard_beats") or []),
                }
                if reference_kind == "storyboard"
                else {}
            ),
        })
    if len(media) != len(slots):
        supplied = {item["picture_index"] for item in descriptions}
        missing = sorted(set(slots) - supplied)
        raise FileNotFoundError(f"R2V 검수 참조 이미지 누락: Picture {missing}")
    return media, descriptions


def _reference_checks(payload: dict[str, Any], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_checks = [item for item in (payload.get("reference_checks") or []) if isinstance(item, dict)]
    allowed = {"matched", "minor_drift", "major_mismatch", "uncertain"}
    result = []
    for reference in references:
        index = reference["picture_index"]
        raw = next((item for item in raw_checks if int(item.get("picture_index") or 0) == index), {})
        status = str(raw.get("status") or "uncertain")
        if status not in allowed:
            status = "uncertain"
        evidence = str(raw.get("evidence_ko") or "").strip()
        if status == "major_mismatch" and not evidence:
            status = "uncertain"
        reference_kind = str(reference.get("reference_kind") or "visual_reference")
        panel_checks = []
        if reference_kind == "storyboard":
            raw_panels = [
                item for item in (raw.get("panel_beat_checks") or [])
                if isinstance(item, dict)
            ]
            panel_count = int(reference.get("storyboard_panel_count") or 0)
            panel_allowed = {
                "verified", "minor_drift", "contradicted", "uncertain", "not_verifiable"
            }
            for panel_index in range(1, panel_count + 1):
                raw_panel = next(
                    (
                        item for item in raw_panels
                        if int(item.get("panel_index") or item.get("shot_index") or 0)
                        == panel_index
                    ),
                    {},
                )
                panel_status = str(raw_panel.get("status") or "not_verifiable")
                if panel_status not in panel_allowed:
                    panel_status = "not_verifiable"
                panel_evidence = str(raw_panel.get("evidence_ko") or "").strip()
                if panel_status == "contradicted" and not panel_evidence:
                    panel_status = "uncertain"
                start, end = common._normalize_check_time(raw_panel, float(payload.get("duration_seconds") or 0))
                panel_checks.append({
                    "panel_index": panel_index,
                    "status": panel_status,
                    "evidence_ko": panel_evidence,
                    "start_seconds": start,
                    "end_seconds": end,
                })
        result.append({
            "picture_index": index,
            "role": reference["role"],
            "label_ko": reference["label_ko"],
            "status": status,
            "evidence_ko": evidence,
            "role_limit_ko": str(raw.get("role_limit_ko") or reference["role_limit_en"]).strip(),
            "reference_kind": reference_kind,
            **({"panel_beat_checks": panel_checks} if reference_kind == "storyboard" else {}),
        })
    return result


def _dialogue_checks(payload: dict[str, Any], dialogue: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    raw_checks = [item for item in (payload.get("dialogue_checks") or []) if isinstance(item, dict)]
    allowed = {"verified", "contradicted", "uncertain", "not_verifiable"}
    result = []
    for order, expected in enumerate(dialogue, start=1):
        speaker = str(expected.get("speaker") or chr(64 + order))
        subject_index = ord(speaker[0]) - ord("A") + 1 if speaker else order
        raw = next(
            (item for item in raw_checks if str(item.get("speaker") or "") == speaker),
            {},
        )
        evidence = str(raw.get("evidence_ko") or "").strip()
        normalized = {}
        for key in (
            "exact_text_status", "speaker_identity_status", "order_status",
            "lip_sync_status", "non_speaker_mouth_status",
        ):
            status = str(raw.get(key) or "not_verifiable")
            if status not in allowed:
                status = "not_verifiable"
            if status == "contradicted" and not evidence:
                status = "uncertain"
            normalized[key] = status
        start, end = common._normalize_check_time(raw, duration)
        result.append({
            "order": order,
            "speaker": speaker,
            "subject_index": subject_index,
            "speaker_id": f"S{subject_index}",
            "line_ko": str(expected.get("line_ko") or ""),
            **normalized,
            "evidence_ko": evidence,
            "start_seconds": start,
            "end_seconds": end,
        })
    return result


def _subject_binding_checks(payload: dict[str, Any], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_checks = [item for item in (payload.get("subject_binding_checks") or []) if isinstance(item, dict)]
    allowed = {"matched", "minor_drift", "major_mismatch", "uncertain"}
    result = []
    for subject_index, reference in enumerate(references, start=1):
        raw = next(
            (item for item in raw_checks if int(item.get("subject_index") or 0) == subject_index),
            {},
        )
        evidence = str(raw.get("evidence_ko") or "").strip()
        status = str(raw.get("status") or "uncertain")
        if status not in allowed:
            status = "uncertain"
        if status == "major_mismatch" and not evidence:
            status = "uncertain"
        result.append({
            "subject_index": subject_index,
            "picture_index": reference["picture_index"],
            "role": reference["role"],
            "label_ko": reference["label_ko"],
            "status": status,
            "evidence_ko": evidence,
            "role_limit_ko": str(raw.get("role_limit_ko") or reference["role_limit_en"]).strip(),
        })
    return result


def _shot_structure_check(payload: dict[str, Any], *, storyboard_present: bool = False) -> dict[str, Any]:
    raw = payload.get("shot_structure_check") if isinstance(payload.get("shot_structure_check"), dict) else {}
    allowed = {"verified", "minor_drift", "contradicted", "uncertain", "not_verifiable"}
    evidence = str(raw.get("evidence_ko") or "").strip()
    result = {"evidence_ko": evidence}
    for key in (
        "shot_count_order_status", "cut_timing_status",
        "screen_direction_status", "camera_plan_status",
        "action_flow_status", "pacing_status",
    ):
        status = str(raw.get(key) or "not_verifiable")
        if status not in allowed:
            status = "not_verifiable"
        if status == "contradicted" and not evidence:
            status = "uncertain"
        result[key] = status
    if storyboard_present:
        layout = str(raw.get("storyboard_layout_leak") or "not_verifiable")
        if layout not in {"absent", "observed", "uncertain", "not_verifiable"}:
            layout = "not_verifiable"
        if layout == "observed" and not evidence:
            layout = "uncertain"
        result["storyboard_layout_leak"] = layout
    return result


def _effective_forbidden_failures(
    forbidden_failures: list[str], expected_shot_count: int,
) -> tuple[list[str], list[str]]:
    """Ignore only the obsolete no-cut rule when the text explicitly requires multiple shots."""
    if expected_shot_count <= 1:
        return list(forbidden_failures), []
    ignored = [item for item in forbidden_failures if str(item).strip() == "장면 컷 전환"]
    effective = [item for item in forbidden_failures if str(item).strip() != "장면 컷 전환"]
    return effective, ignored


def _normalize(
    payload: dict[str, Any], *, duration: float, intent_ko: str,
    required_events: list[str], forbidden_failures: list[str],
    references: list[dict[str, Any]], dialogue: list[dict[str, Any]] | None = None,
    expected_shot_count: int = 1,
) -> dict[str, Any]:
    references = _visual_references(references)
    storyboard_references = [item for item in references if _is_storyboard_slot(item)]
    subject_references = [item for item in references if not _is_storyboard_slot(item)]
    forbidden_failures, ignored_legacy_forbidden = _effective_forbidden_failures(
        forbidden_failures, expected_shot_count,
    )
    events = common._ordered_required_checks(payload, required_events, duration)
    forbidden = common._ordered_forbidden_checks(payload, forbidden_failures, duration)
    payload = {**payload, "duration_seconds": duration}
    references_checked = _reference_checks(payload, references)
    dialogue_checked = _dialogue_checks(payload, list(dialogue or []), duration)
    subject_bindings = _subject_binding_checks(payload, subject_references)
    shot_structure = _shot_structure_check(
        payload, storyboard_present=bool(storyboard_references)
    )
    raw_scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    scores: dict[str, float] = {}
    for key in SCORE_KEYS:
        if raw_scores.get(key) in (None, ""):
            continue
        try:
            scores[key] = round(max(0.0, min(5.0, float(raw_scores[key]))), 2)
        except (TypeError, ValueError):
            continue

    issues = []
    for index, raw in enumerate((payload.get("issues") or [])[:review_contract.MAX_ISSUES], 1):
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category") or "other")
        if category not in review_contract.CATEGORIES:
            category = "other"
        severity = str(raw.get("severity") or "major")
        if severity not in review_contract.SEVERITIES:
            severity = "major"
        start, end = common._normalize_check_time(raw, duration)
        issues.append({
            "issue_id": str(raw.get("issue_id") or f"r2v_issue_{index:02d}"),
            "category": category,
            "subcategory": str(raw.get("subcategory") or "other"),
            "severity": severity,
            "start_seconds": start,
            "end_seconds": end,
            "expected": str(raw.get("expected") or intent_ko).strip(),
            "observed": str(raw.get("observed") or raw.get("evidence_ko") or "직접 근거가 제한됨").strip(),
            "difference": str(raw.get("difference") or "").strip(),
            "cause_hypothesis": str(raw.get("cause_hypothesis") or "").strip(),
            "suggestion": str(raw.get("suggestion") or "").strip(),
        })

    contradicted = [item for item in events if item["status"] == "contradicted"]
    unresolved = [item for item in events if item["status"] in {"uncertain", "not_verifiable"}]
    observed_forbidden = [item for item in forbidden if item["status"] == "observed"]
    uncertain_forbidden = [item for item in forbidden if item["status"] == "uncertain"]
    major_refs = [item for item in references_checked if item["status"] == "major_mismatch"]
    uncertain_refs = [item for item in references_checked if item["status"] == "uncertain"]
    storyboard_panels = [
        panel
        for item in references_checked
        if item.get("reference_kind") == "storyboard"
        for panel in (item.get("panel_beat_checks") or [])
    ]
    storyboard_contradicted = [
        item for item in storyboard_panels if item["status"] == "contradicted"
    ]
    storyboard_minor = [
        item for item in storyboard_panels if item["status"] == "minor_drift"
    ]
    storyboard_uncertain = [
        item for item in storyboard_panels
        if item["status"] in {"uncertain", "not_verifiable"}
    ]
    dialogue_hard_contradicted = [
        item for item in dialogue_checked
        if any(item[key] == "contradicted" for key in (
            "exact_text_status", "speaker_identity_status", "order_status",
        ))
    ]
    dialogue_soft_contradicted = [
        item for item in dialogue_checked
        if any(item[key] == "contradicted" for key in (
            "lip_sync_status", "non_speaker_mouth_status",
        ))
    ]
    dialogue_uncertain = [
        item for item in dialogue_checked
        if any(item[key] in {"uncertain", "not_verifiable"} for key in (
            "exact_text_status", "speaker_identity_status", "order_status",
            "lip_sync_status", "non_speaker_mouth_status",
        ))
    ]
    major_bindings = [item for item in subject_bindings if item["status"] == "major_mismatch"]
    minor_bindings = [item for item in subject_bindings if item["status"] == "minor_drift"]
    uncertain_bindings = [item for item in subject_bindings if item["status"] == "uncertain"]
    hard_shot_failure = bool(
        shot_structure["shot_count_order_status"] == "contradicted"
        or shot_structure["screen_direction_status"] == "contradicted"
        or shot_structure["action_flow_status"] == "contradicted"
        or storyboard_contradicted
        or shot_structure.get("storyboard_layout_leak") == "observed"
    )
    soft_shot_failure = bool(
        shot_structure["cut_timing_status"] in {"minor_drift", "contradicted"}
        or shot_structure["camera_plan_status"] in {"minor_drift", "contradicted"}
        or shot_structure["shot_count_order_status"] == "minor_drift"
        or shot_structure["screen_direction_status"] == "minor_drift"
        or shot_structure["action_flow_status"] == "minor_drift"
        or shot_structure["pacing_status"] in {"minor_drift", "contradicted"}
        or storyboard_minor
    )
    uncertain_shot = bool(
        any(shot_structure[key] in {"uncertain", "not_verifiable"} for key in (
            "shot_count_order_status", "cut_timing_status",
            "screen_direction_status", "camera_plan_status",
            "action_flow_status", "pacing_status",
        ))
        or storyboard_uncertain
        or shot_structure.get("storyboard_layout_leak") in {"uncertain", "not_verifiable"}
    )
    critical = any(item["severity"] == "critical" for item in issues)
    major = any(item["severity"] == "major" for item in issues)
    hard_reject = bool(
        critical or contradicted or observed_forbidden or major_refs
        or dialogue_hard_contradicted or major_bindings or hard_shot_failure
    )
    soft_failure = bool(
        dialogue_soft_contradicted or minor_bindings or soft_shot_failure
    )
    human_review_required = bool(
        payload.get("human_review_required") or unresolved or uncertain_forbidden or uncertain_refs
        or dialogue_uncertain or uncertain_bindings or uncertain_shot
    )
    gate_passed = not (hard_reject or major or soft_failure or human_review_required)
    verdict = "reject" if hard_reject else ("acceptable" if gate_passed else "needs_improvement")
    summary = (
        f"참조 일치 {sum(x['status'] == 'matched' for x in references_checked)}/{len(references_checked)}"
        f" · 스토리보드 패널 {sum(x['status'] == 'verified' for x in storyboard_panels)}/{len(storyboard_panels)}"
        f" · 필수 사건 확인 {sum(x['status'] == 'verified' for x in events)}/{len(events)}"
        f" · 사람 확인 {'필요' if human_review_required else '불필요'}"
    )
    note = str(payload.get("overall_note") or "").strip()
    return {
        "verdict": verdict,
        "positive_note": str(payload.get("positive_note") or "").strip(),
        "overall_note": f"{note} | R2V 보정 게이트: {summary}" if note else f"R2V 보정 게이트: {summary}",
        "scores": scores,
        "issues": issues,
        "reference_checks": references_checked,
        "dialogue_checks": dialogue_checked,
        "subject_binding_checks": subject_bindings,
        "shot_structure_check": shot_structure,
        "event_checks": events,
        "forbidden_checks": forbidden,
        "enforcement": {
            "rubric_version": RUBRIC_VERSION,
            "gate_passed": gate_passed,
            "human_review_required": human_review_required,
            "reference_matched": sum(x["status"] == "matched" for x in references_checked),
            "reference_total": len(references_checked),
            "reference_major_mismatch": len(major_refs),
            "reference_uncertain": len(uncertain_refs),
            "storyboard_panel_verified": sum(
                x["status"] == "verified" for x in storyboard_panels
            ),
            "storyboard_panel_total": len(storyboard_panels),
            "storyboard_panel_contradicted": len(storyboard_contradicted),
            "storyboard_panel_minor_drift": len(storyboard_minor),
            "storyboard_panel_uncertain": len(storyboard_uncertain),
            "dialogue_total": len(dialogue_checked),
            "dialogue_hard_contradicted": len(dialogue_hard_contradicted),
            "dialogue_soft_contradicted": len(dialogue_soft_contradicted),
            "dialogue_uncertain": len(dialogue_uncertain),
            "subject_binding_total": len(subject_bindings),
            "subject_binding_major_mismatch": len(major_bindings),
            "subject_binding_minor_drift": len(minor_bindings),
            "subject_binding_uncertain": len(uncertain_bindings),
            "shot_structure_hard_failure": hard_shot_failure,
            "shot_structure_soft_failure": soft_shot_failure,
            "expected_shot_count": expected_shot_count,
            "required_verified": sum(x["status"] == "verified" for x in events),
            "required_total": len(events),
            "required_contradicted": len(contradicted),
            "required_uncertain": len(unresolved),
            "forbidden_observed": len(observed_forbidden),
            "forbidden_uncertain": len(uncertain_forbidden),
            "ignored_legacy_forbidden": ignored_legacy_forbidden,
        },
    }


def review_benchmark_video(
    *, video_path: Path, request: dict[str, Any], review_queue_id: str, job_id: str,
) -> dict[str, Any]:
    contract = request.get("benchmark_contract") or {}
    if str(contract.get("input_mode") or "") not in {
        "h3_r2v_multi_reference", "r2v_multi_reference",
    }:
        raise ValueError("R2V 전용 검수기는 다중 참조 R2V 작업만 처리합니다.")
    if not video_path.is_file():
        raise FileNotFoundError(f"검수 영상 파일이 없습니다: {video_path}")
    probe = omni.probe_video(video_path)
    if not probe.get("has_video"):
        raise omni.VLLMReviewError(f"검수 파일에 영상 스트림이 없습니다: {video_path}")
    duration = float(probe.get("duration_seconds") or request.get("settings", {}).get("duration_seconds") or 0)
    use_audio = omni._should_use_audio(probe)
    probe["audio_reviewed"] = use_audio
    video_data_url, video_metadata = omni._direct_video_data_url(video_path)
    audio_data_url = None
    if use_audio:
        audio_data_url, audio_metadata = omni._direct_audio_data_url(video_path)
        video_metadata["audio_input"] = audio_metadata
    reference_media, references = _reference_media(request)
    text_shot_guidance = list(contract.get("prompt_only_shot_guidance") or [])
    execution_prompt = _general_review_prompt(str(request.get("canonical_prompt") or ""))
    expected_shot_count = _expected_shot_count(execution_prompt, text_shot_guidance)
    effective_forbidden, _ignored_legacy_forbidden = _effective_forbidden_failures(
        list(contract.get("forbidden_failures") or []), expected_shot_count,
    )
    model = omni._model_id()
    context = {
        "case_title": request.get("case_title"),
        "execution_prompt_en": execution_prompt,
        "intent_ko": request.get("review_intent_ko"),
        "visual_style": contract.get("visual_style"),
        "reference_contract": references,
        "storyboard_review_contract": contract.get("storyboard_review_contract") or {},
        "required_events": contract.get("required_events") or [],
        "forbidden_failures": effective_forbidden,
        "text_shot_guidance": text_shot_guidance,
        "expected_shot_count": expected_shot_count,
        "dialogue": contract.get("dialogue") or [],
        "duration_seconds": duration,
        "audio_reviewed": use_audio,
    }
    payload, _message, raw = omni._response_json(
        model=model, system_prompt=SYSTEM_PROMPT,
        required_keys={
            "verdict", "positive_note", "overall_note", "scores", "issues",
            "reference_checks", "dialogue_checks", "subject_binding_checks",
            "shot_structure_check", "event_checks", "forbidden_checks",
        },
        user_text="Evaluate this R2V output with the reference-grounded rubric.\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":")),
        video_data_url=video_data_url, audio_data_url=audio_data_url,
        video_metadata=video_metadata, image_data_urls=reference_media,
    )
    review = _normalize(
        payload, duration=duration,
        intent_ko=str(request.get("review_intent_ko") or ""),
        required_events=list(contract.get("required_events") or []),
        forbidden_failures=list(contract.get("forbidden_failures") or []),
        references=references,
        dialogue=list(contract.get("dialogue") or []),
        expected_shot_count=expected_shot_count,
    )
    return {
        "review": review,
        "confidence": max(0.0, min(1.0, float(payload.get("confidence") or 0))),
        "reference_checks": review["reference_checks"],
        "dialogue_checks": review["dialogue_checks"],
        "subject_binding_checks": review["subject_binding_checks"],
        "shot_structure_check": review["shot_structure_check"],
        "event_checks": review["event_checks"],
        "forbidden_checks": review["forbidden_checks"],
        "enforcement": review["enforcement"],
        "model": model,
        "review_mode": "qwen_omni_r2v_storyboard_action_flow_v7",
        "rubric_version": RUBRIC_VERSION,
        "duration_seconds": round(duration, 3),
        "media_probe": probe,
        "reference_count": len(references),
        "observation": None,
        "raw_observation_response": "",
        "raw_response": raw,
        "review_queue_id": review_queue_id,
        "job_id": job_id,
    }
