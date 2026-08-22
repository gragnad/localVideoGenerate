from __future__ import annotations

"""Fail-closed audit for the EP00 V8 action-causality rebuild."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import h3_prompt_contract
import h3_prompt_projects


EPISODE_DIR = ROOT / "projects" / "RaisingaDragonSeason01"
PROJECT_ID = "RaisingaDragonSeason01_EP00_H3_R2V_ACTION_CAUSALITY_V8"
PROJECT_DIR = ROOT / "prompt_projects" / PROJECT_ID
LOCK_PATH = EPISODE_DIR / "EP00_LOCKED_PRODUCTION_RULES_V2.json"
CANONICAL_PATH = EPISODE_DIR / "EP00_CANONICAL_CLIPS_V2.json"
EVENTS_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_EVENT_CONTRACTS.json"
SPEC_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_SPEC.json"
CURRENT_STATE_PATH = EPISODE_DIR / "EP00_CURRENT_PRODUCTION_STATE.md"
SCREENPLAY_PATH = EPISODE_DIR / "EP00_VISUAL_PRODUCTION_SCREENPLAY_REBUILD_V2.md"
AUTHORING_GUIDE_PATH = EPISODE_DIR / "H3_R2V_SCENARIO_AUTHORING_GUIDE.md"
STORYBOARD_DIR = EPISODE_DIR / "storyboards_ep00_action_v2"
CONTACT_PATH = STORYBOARD_DIR / "EP00_ACTION_CAUSALITY_V8_CONTACT_SHEET.png"
CONTACT_MANIFEST_PATH = STORYBOARD_DIR / "EP00_ACTION_CAUSALITY_V8_CONTACT_SHEET_MANIFEST.json"
REPORT_JSON_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_AUDIT.json"
REPORT_MD_PATH = EPISODE_DIR / "EP00_H3_R2V_ACTION_CAUSALITY_V8_AUDIT.md"
POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    return struct.unpack(">II", header[16:24])


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append({"name": name, "passed": bool(passed), "detail": detail})

    @property
    def passed(self) -> bool:
        return all(row["passed"] for row in self.checks)

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_id": PROJECT_ID,
            "passed": self.passed,
            "check_count": len(self.checks),
            "passed_count": sum(1 for row in self.checks if row["passed"]),
            "failed_count": sum(1 for row in self.checks if not row["passed"]),
            "checks": self.checks,
        }


def build_contact_sheet(canonical: dict[str, Any]) -> dict[str, Any]:
    previous: dict[str, Any] = {}
    if CONTACT_MANIFEST_PATH.exists():
        previous = json.loads(CONTACT_MANIFEST_PATH.read_text(encoding="utf-8"))
    previous_reviews = {
        (row.get("path"), row.get("sha256")): row.get("visual_review")
        for row in previous.get("sources", [])
    }
    tile_size = (418, 235)
    sheet = Image.new("RGB", (1672, 940), (0, 0, 0))
    sources: list[dict[str, Any]] = []
    for sequence, row in enumerate(canonical["clips"], start=1):
        path = STORYBOARD_DIR / row["storyboard"]
        with Image.open(path) as source:
            rgb = source.convert("RGB")
            rgb.thumbnail(tile_size, Image.Resampling.LANCZOS)
            tile = Image.new("RGB", tile_size, (0, 0, 0))
            tile.paste(rgb, ((tile_size[0] - rgb.width) // 2, (tile_size[1] - rgb.height) // 2))
            x = ((sequence - 1) % 4) * tile_size[0]
            y = ((sequence - 1) // 4) * tile_size[1]
            sheet.paste(tile, (x, y))
        width, height = png_size(path)
        source_hash = sha256(path)
        sources.append({
            "sequence": sequence,
            "clip_id": row["clip"],
            "path": path.relative_to(EPISODE_DIR).as_posix(),
            "sha256": source_hash,
            "width": width,
            "height": height,
            "visual_review": previous_reviews.get(
                (path.relative_to(EPISODE_DIR).as_posix(), source_hash),
                "pending_full_contact_sheet_review",
            ),
        })
    sheet.save(CONTACT_PATH)
    manifest = {
        "schema_version": 1,
        "contact_sheet": CONTACT_PATH.relative_to(EPISODE_DIR).as_posix(),
        "contact_sheet_sha256": sha256(CONTACT_PATH),
        "contact_sheet_size": list(png_size(CONTACT_PATH)),
        "source_count": len(sources),
        "sources": sources,
        "review_status": (
            "verified"
            if sources and all(row["visual_review"] == "agent_passed_full_sheet" for row in sources)
            else "pending_full_contact_sheet_review"
        ),
    }
    CONTACT_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def run(require_status: str) -> Audit:
    audit = Audit()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    manifest = json.loads((PROJECT_DIR / "manifest.json").read_text(encoding="utf-8"))
    overview = h3_prompt_projects.project_clips(ROOT, PROJECT_ID)
    clips = overview["clips"]
    clip_by_id = {row["clip_id"]: row for row in clips}
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(PROJECT_DIR.glob("EP00-S*/EP00-*.md")):
        payload = h3_prompt_projects.extract_payload(path.read_text(encoding="utf-8"))
        payloads[payload["clip_id"]] = payload
    expected_ids = [row["clip"] for row in canonical["clips"]]

    lineage = manifest.get("canonical_source_lineage") or []
    audit.check(
        "v2_canonical_source_lineage",
        manifest.get("locked_rule_id") == lock["lock_id"]
        and manifest.get("source_policy") == "v2_screenplay_and_locked_action_causality_only_no_v1_v7_prompt_lineage"
        and lineage == spec.get("canonical_source_lineage")
        and "EP00_VISUAL_PRODUCTION_SCREENPLAY_REBUILD_V2.md" in lineage
        and all("_V7_" not in source and "CANONICAL_CLIPS_V1" not in source for source in lineage),
        "V2 시나리오·V2 잠금·V2 canonical만 현행 입력",
    )
    current_state = CURRENT_STATE_PATH.read_text(encoding="utf-8")
    screenplay = SCREENPLAY_PATH.read_text(encoding="utf-8")
    guide = AUTHORING_GUIDE_PATH.read_text(encoding="utf-8")
    audit.check(
        "regression_barrier_documents",
        lock.get("status") == "active_verified_current"
        and PROJECT_ID in current_state
        and "EP00_LOCKED_PRODUCTION_RULES_V2.json" in current_state
        and "EP00_CANONICAL_CLIPS_V2.json" in current_state
        and "V7 정본" not in current_state
        and "현행 검수 정본" in screenplay
        and "개별 액션 예시" in screenplay
        and "EP00_LOCKED_PRODUCTION_RULES_V2.json" in guide
        and "그 부분만 교체하라는 뜻으로 축소하지 않는다" in guide,
        "현행 인덱스·시나리오·작성 가이드가 V2/V8 전체 각색 원칙을 고정",
    )
    source = (ROOT / "scripts/build_ep00_action_causality_v8.py").read_text(encoding="utf-8")
    audit.check(
        "no_old_prompt_project_import",
        not re.search(r"STORYBOARD_ADE_V[1-7].*(?:SPEC|EVENT|prompt_projects)", source, re.IGNORECASE),
        "V8 빌더가 V1~V7 prompt spec·event·project를 읽지 않음",
    )
    audit.check(
        "clip_identity_and_order",
        [row["clip_id"] for row in clips] == expected_ids and list(payloads) == expected_ids,
        f"clips={len(clips)}, payloads={len(payloads)}",
    )
    prompt_count = sum(len(row["prompt_variants"]) for row in clips)
    total = sum(float(row["duration_seconds"]) for row in clips)
    audit.check(
        "counts_and_duration",
        len(clips) == 14 and prompt_count == 42 and total == 121.5,
        f"14 Clip, {prompt_count} Prompt, {total:g}초",
    )
    audit.check(
        "review_status",
        manifest.get("review_status") == require_status
        and all(payload.get("status") == require_status for payload in payloads.values()),
        f"required={require_status}",
    )
    audit.check("all_clips_ready", all(row["ready"] for row in clips), "14/14 H3 기술 검증 ready")

    expected_actions = {
        "EP00-S02-NC01": ("horizontal sweep", "airborne", "combat roll", "aligns the spear"),
        "EP00-S02-NC02": ("sprints three hard steps", "torso", "clamps the wooden shaft", "lifts the captured spear"),
        "EP00-S02-NC03": ("throw", "travel on one low arc", "breakfall", "curved water sheet"),
    }
    exact_ok = True
    for clip_id, fragments in expected_actions.items():
        text = " ".join(beat["description"] for beat in events["clips"][clip_id]["beats"]).lower()
        exact_ok &= all(fragment.lower() in text for fragment in fragments)
    audit.check(
        "user_action_examples_generalized_exactly",
        exact_ok,
        "Scene 2 세 Clip이 sweep·jump/roll, sprint/contact/catch/lift, throw/breakfall/shield 순서를 모두 포함",
    )
    audit.check(
        "action_density",
        all(
            len(row["panels"]) == 4
            and len(set(row["panels"])) == 4
            and len(row["motions"]) == 3
            for row in canonical["clips"]
        ),
        "14개 Clip 모두 네 개의 서로 다른 행동 상태와 세 연결 동작",
    )
    scene1 = canonical["clips"][:2]
    audit.check(
        "scene1_distinct_tension_functions",
        "three-times-taller" in scene1[0]["summary"].lower()
        and "swing" in scene1[1]["summary"].lower()
        and scene1[0]["cameras"] != scene1[1]["cameras"],
        "Clip 1은 공간·크기 공개, Clip 2는 공격 가속·선행 반응",
    )
    scene3_text = " ".join(
        beat["description"]
        for clip_id in ("EP00-S03-NC01", "EP00-S03-NC02", "EP00-S03-NC03")
        for beat in events["clips"][clip_id]["beats"]
    ).lower().replace("does not grab", "").replace("never touches", "")
    audit.check(
        "scene3_no_spear_grab",
        not any(fragment in scene3_text for fragment in ("catches the spear", "clamps the", "grabs the spear", "holds the spear")),
        "Scene 3에서 심해왕의 창 포획·반복 잡기 없음",
    )
    shield_text = " ".join(
        beat["description"]
        for clip_id in ("EP00-S02-NC03", "EP00-S03-NC01", "EP00-S03-NC02", "EP00-S03-NC03")
        for beat in events["clips"][clip_id]["beats"]
    ).lower()
    audit.check(
        "shield_lifecycle",
        "forms one transparent irregular curved water sheet" in shield_text
        and "tilt the same shield" in shield_text
        and "outer edge tears first" in shield_text
        and "no shield remains" in shield_text,
        "단일 방패 생성→방향 전환→가장자리 파손→완전 소멸",
    )
    audit.check(
        "effect_causality",
        all(term in " ".join(
            panel for row in canonical["clips"] for panel in row["panels"]
        ).lower() for term in (
            "pressure wake", "directional droplets", "water-surface geometry", "surface ripples"
        )),
        "수압·물방울·용언 수면·검은 표면 반응이 행동 원인과 연결",
    )

    prompt_ids: list[str] = []
    contract_ok = True
    four_shot_ok = True
    current_anchor_ok = True
    next_anchor_ok = True
    background_ok = True
    descriptions: list[str] = []
    d_transitions: list[str] = []
    e_transitions: list[str] = []
    forbidden_hits: list[str] = []
    forbidden_patterns = {
        "roots": r"\b(?:thick|giant|moving|attacking)?\s*roots?\b",
        "independent_tentacles": r"\bindependent\s+tentacles?\b",
        "extra_arms": r"\bextra\s+arms?\b",
        "extra_hands": r"\bextra\s+hands?\b",
        # Lua's legs are valid. Only a legged Abyss King violates the silhouette lock.
        "legs": r"\b(?:abyss\s+king|king|his)\b[^.]{0,50}\blegs?\b|\blegged\s+(?:abyss\s+king|king)\b",
        "wings": r"\bwings?\b",
        "tail": r"\btails?\b",
        "beam": r"\bbeams?\b",
        "explosion": r"\bexplosions?\b",
        "lightning": r"\blightning\b",
        "fire": r"\bfire\b",
        "memory_attack": r"\bmemory\s+attacks?\b",
        "voices": r"\b(?:disembodied|unseen|external|whispering)\s+voices?\b|\bvoices?\s+(?:speak|whisper|call)\b",
        "magic_spear": r"\bmagic\s+spear\b",
        "autonomous_spear": r"\bautonomous\s+spear\b|\bspear\b[^.]{0,50}\b(?:moves|flies|attacks)\s+by\s+itself\b",
        "Heartstone_response": r"\bheartstone\b[^.]{0,50}\b(?:responds?|reacts?|awakens?)\b",
        "visible_new_power": r"(?<!no )(?<!any )(?<!without )(?<!without any )\bvisible\s+new\s+power\b",
    }
    id_pattern = re.compile(r"\bEP\d{2}[-_]|\bSCENE\s*\d|\bCLIP\s*\d|\bNC\d+\b", re.IGNORECASE)
    for canonical_row in canonical["clips"]:
        clip_id = canonical_row["clip"]
        storyboard_picture_id = 4 if canonical_row["has_spear"] else 3
        for variant in clip_by_id[clip_id]["prompt_variants"]:
            prompt = variant["video_prompt"]
            detail = variant["detailed_description"]
            descriptions.append(detail)
            report = h3_prompt_contract.validate_prompt(
                prompt, duration_seconds=float(clip_by_id[clip_id]["duration_seconds"])
            )
            contract_ok &= report.valid
            if id_pattern.search(prompt):
                prompt_ids.append(f"{clip_id}/{variant['variant_id']}")
            background_ok &= all(term in prompt for term in (
                "same circular underwater Heartstone Chamber",
                "central round dais",
                "concentric cyan water channels",
                "dragon-statue columns",
                "upper black hanging strands",
            ))
            shots = list(h3_prompt_contract.SHOT_RE.finditer(detail))
            four_shot_ok &= len(shots) == 4
            for number, shot in enumerate(shots, start=1):
                body = shot.group(4)
                current_anchor_ok &= (
                    f"<Picture {storyboard_picture_id}>" in body
                    and bool(re.search(rf"\bpanel\s+{number}\b", body, re.IGNORECASE))
                    and POSITIONS[number - 1] in body.lower()
                )
                if variant["variant_id"] in {"D", "E"} and number < 4:
                    next_anchor_ok &= (
                        f"<Picture {storyboard_picture_id}> panel {number + 1} at the {POSITIONS[number]}" in body
                    )
            low = prompt.lower()
            for phrase in lock["character_contract"]["forbidden_events"]:
                pattern = forbidden_patterns[phrase]
                if re.search(pattern, low, re.IGNORECASE):
                    forbidden_hits.append(f"{clip_id}/{variant['variant_id']}:{phrase}")
    audit.check("official_h3_contract", contract_ok, "42 Prompt 공식 H3 6-section·시간 계약 통과")
    audit.check("four_panel_four_shot", four_shot_ok, "42 Prompt 모두 4패널=4Shot")
    audit.check("current_storyboard_anchor", current_anchor_ok, "168 Shot 모두 현재 Picture·panel·절대 위치")
    audit.check("next_storyboard_anchor", next_anchor_ok, "D/E Shot 1~3 모두 다음 Picture·panel·절대 위치")
    audit.check("no_production_ids_inside_prompt", not prompt_ids, f"hits={prompt_ids}")
    audit.check("persistent_environment_prompt", background_ok, "42 Prompt 모두 동일 해심석 방 특징을 명시")
    audit.check("forbidden_event_absence", not forbidden_hits, f"hits={forbidden_hits}")
    audit.check(
        "candidate_descriptions_unique",
        len(descriptions) == len(set(descriptions)) == 42,
        f"unique={len(set(descriptions))}/42",
    )

    for contract in events["clips"].values():
        for variant_id in ("D", "E"):
            for shot in contract["candidate_plans"][variant_id]["shots"][:-1]:
                if variant_id == "D":
                    d_transitions.append(shot["transition_to_next"])
                else:
                    e_transitions.append(shot["transition_to_next"])
    audit.check("d_camera_paths_unique", len(d_transitions) == len(set(d_transitions)) == 42, "D transition unique=42/42")
    audit.check("e_action_reveals_unique", len(e_transitions) == len(set(e_transitions)) == 42, "E transition unique=42/42")

    refs_ok = True
    copied_hash_ok = True
    for row in canonical["clips"]:
        refs = payloads[row["clip"]]["references"]
        roles = [ref["role"] for ref in refs]
        refs_ok &= set(roles) <= {"lua_identity", "abyss_king_identity", "major_prop_spear", "chronological_storyboard"}
        refs_ok &= ("major_prop_spear" in roles) == bool(row["has_spear"])
        for ref in refs:
            target = PROJECT_DIR / ref["source_path"]
            if ref["role"] == "chronological_storyboard":
                expected = sha256(STORYBOARD_DIR / row["storyboard"])
            elif ref["role"] == "lua_identity":
                expected = lock["asset_locks"]["lua_awakened"]["sha256"]
            elif ref["role"] == "abyss_king_identity":
                expected = lock["asset_locks"]["abyss_king"]["sha256"]
            else:
                expected = lock["asset_locks"]["dragon_spear"]["sha256"]
            copied_hash_ok &= sha256(target) == expected
    audit.check("reference_policy", refs_ok, "캐릭터+필요 시 창+스토리보드만 연결")
    audit.check("project_asset_hashes", copied_hash_ok, "프로젝트 복사 자산과 정본 해시 일치")

    bridge_ok = True
    rows = [events["clips"][clip_id] for clip_id in expected_ids]
    for current, following in zip(rows, rows[1:]):
        bridge_ok &= current["bridge_out_id"] == following["bridge_in_id"]
    bridge_ok &= rows[-1]["boundary_policy"] == "terminal"
    audit.check("bridge_continuity", bridge_ok, "14개 경계 ID 연속, 마지막 terminal")
    audit.check(
        "ending_contract",
        "full black" in rows[-1]["beats"][3]["description"].lower()
        and "before the second internal heartbeat completes" in rows[-1]["outgoing_bridge"].lower(),
        "두 번째 박동 완료 전 직접 완전 암전",
    )

    facts = manifest.get("build_facts") or {}
    audit.check(
        "execution_guard",
        facts == {"clip_count": 14, "prompt_count": 42, "total_duration_seconds": 121.5}
        and manifest.get("queue_authorized") is False
        and manifest.get("video_generation_authorized") is False
        and manifest.get("queue_registration_performed") is False
        and manifest.get("video_generation_performed") is False,
        "수치 고정, 큐·영상 권한 false 및 미수행",
    )
    workflow = Path(lock["workflow_lock"]["path"])
    audit.check("workflow_hash", sha256(workflow) == lock["workflow_lock"]["sha256"], "Resize/Scale/Crop 없는 잠금 workflow 해시 일치")
    contact = build_contact_sheet(canonical)
    audit.check(
        "contact_sheet_sources",
        contact["source_count"] == 14
        and contact["contact_sheet_size"] == [1672, 940]
        and all(row["width"] == 1672 and row["height"] == 941 for row in contact["sources"]),
        "14개 1672x941 원본과 1672x940 접촉 시트",
    )
    return audit


def write_reports(audit: Audit) -> None:
    payload = audit.payload()
    REPORT_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = [
        "# EP00 H3 R2V Action Causality V8 Audit",
        "",
        f"- 결과: {'PASS' if audit.passed else 'FAIL'}",
        f"- 통과: {payload['passed_count']}/{payload['check_count']}",
        "- 시각 검수 상태: 접촉 시트 manifest와 프로젝트 검수 결정에서 별도 관리",
        "- 큐 등록·영상 생성: 수행하지 않음",
        "",
        "| 상태 | 검사항목 | 근거 |",
        "| --- | --- | --- |",
    ]
    for row in audit.checks:
        rows.append(f"| {'PASS' if row['passed'] else 'FAIL'} | `{row['name']}` | {row['detail']} |")
    REPORT_MD_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-status", default="pending_review")
    args = parser.parse_args()
    audit = run(args.require_status)
    write_reports(audit)
    print(json.dumps(audit.payload(), ensure_ascii=False, indent=2))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
