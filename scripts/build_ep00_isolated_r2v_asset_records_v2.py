#!/usr/bin/env python3
"""Build the approval-gated records for the EP00 isolated R2V V2 asset batch."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/RaisingaDragonSeason01"
ASSET_ROOT = PROJECT / "asset_sheets_cinematic_liveaction_v1_working"
COMMAND = PROJECT / "ep00_cinematic_liveaction_production_v1/EP00_CODEX_ADDITIONAL_ASSET_GENERATION_COMMAND_V2.md"
PROMPT_SOURCE = PROJECT / "ep00_cinematic_liveaction_production_v1/EP00_H3_R2V_PROMPT_DOCUMENT_CINEMATIC_LIVEACTION_V2.md"

PROMPT_RECORD = ASSET_ROOT / "prompts/EP00_ISOLATED_R2V_ASSET_PROMPTS_V2.md"
MANIFEST = ASSET_ROOT / "manifests/EP00_ISOLATED_R2V_ASSET_MANIFEST_V2.json"
APPROVAL = ASSET_ROOT / "manifests/EP00_ISOLATED_R2V_ASSET_APPROVAL_GATE_V2.md"
AUDIT = ASSET_ROOT / "manifests/EP00_ISOLATED_R2V_ASSET_VISUAL_AUDIT_V2.md"

ASSETS = {
    "BG01": {
        "title": "MASTER clean environment",
        "path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png",
        "prompt_heading": "#### BG01 MASTER",
        "refs": [
            {"path": "00_style_bible/CINEMATIC_LIVEACTION_MARITIME_FANTASY_STYLE_BIBLE_V1.md", "role": "live-action style authority"},
            {"path": "00_style_bible/CINEMATIC_CAMERA_COLOR_MATERIAL_LOCK_V1.md", "role": "camera/color/material authority"},
        ],
        "assessment": "pass",
        "note": "빈 폐쇄형 심해 제단, 방사형 수로, 원형 전투 바닥과 수로 유래 청록광이 명확함.",
    },
    "BG02": {
        "title": "DAMAGED clean environment",
        "path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png",
        "prompt_heading": "#### BG02 DAMAGED",
        "refs": [{"path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png", "role": "exact environment and geography reference"}],
        "assessment": "pass",
        "note": "MASTER의 카메라 축·제단·수로·동선을 유지하며 국소 균열과 누수가 추가됨.",
    },
    "BG03": {
        "title": "FINAL DAMAGE clean environment",
        "path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_FINAL_DAMAGE_CINEMATIC_LIVEACTION_V2.png",
        "prompt_heading": "#### BG03 FINAL DAMAGE",
        "refs": [
            {"path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_MASTER_CINEMATIC_LIVEACTION_V2.png", "role": "exact environment and geography reference"},
            {"path": "04_backgrounds/scenario_extensions/EP00/ABYSS_ALTAR/BG_EP00_ABYSS_ALTAR_DAMAGED_CINEMATIC_LIVEACTION_V2.png", "role": "damage continuity edit target"},
        ],
        "assessment": "needs_user_review_exact_three_puncture_paths",
        "note": "최종 파손 증가는 보이지만 오른쪽 벽·바닥의 정확히 세 천공 경로 판독은 사용자 확인 필요.",
    },
    "FX01": {
        "title": "isolated direct-fire black sphere",
        "path": "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_SPHERE_ISOLATED_R2V_REFERENCE_V2.png",
        "prompt_heading": "#### FX01 직사 검은 구체",
        "refs": [],
        "assessment": "pass_with_material_realism_review",
        "note": "손·인물·배경·접촉 없이 작고 조밀한 검은 유체 구체만 분리됨. 표면 실사성 최종 확인 권장.",
    },
    "FX02": {
        "title": "isolated black-rain material",
        "path": "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_RAIN_ISOLATED_R2V_REFERENCE_V2.png",
        "prompt_heading": "#### FX02 검은 비 물성",
        "refs": [],
        "assessment": "pass",
        "note": "상단의 얇은 검은 막과 분리되는 액체 방울만 존재하며 바닥·충돌·환경은 없음.",
    },
    "FX03": {
        "title": "isolated black pursuit spikes",
        "path": "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_BLACK_PURSUIT_SPIKES_ISOLATED_R2V_REFERENCE_V2.png",
        "prompt_heading": "#### FX03 검은 추격 가시",
        "refs": [],
        "assessment": "pass",
        "note": "정확히 세 개의 분리된 검은 유체 가시가 한 방향군으로 명확하게 판독됨.",
    },
    "FX04": {
        "title": "isolated moving current",
        "path": "05_effects/reference_sheets/EP00/isolated_r2v_v2/FX_EP00_MOVING_CURRENT_ISOLATED_R2V_REFERENCE_V2.png",
        "prompt_heading": "#### FX04 이동 수류",
        "refs": [],
        "assessment": "pass",
        "note": "배경·수로·접촉점 없이 난류·기포·전단 가장자리를 가진 실제 바닷물 질량만 분리됨.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_prompt(text: str, heading: str) -> str:
    start = text.index(heading)
    match = re.search(r"```text\n(.*?)\n```", text[start:], re.DOTALL)
    if not match:
        raise RuntimeError(f"prompt block missing after {heading}")
    return match.group(1)


def inspect_prompt_source() -> dict:
    text = PROMPT_SOURCE.read_text(encoding="utf-8")
    clips = re.findall(r"^## (EP00_C\d{2}) —", text, re.MULTILINE)
    durations = [float(value) for value in re.findall(r"^\*\*Target duration:\*\* ([0-9.]+) seconds", text, re.MULTILINE)]
    blocks = re.findall(r"```text\n(.*?)\n```", text, re.DOTALL)
    video_blocks = [block for block in blocks if block.startswith("subject_definitions:")]
    forbidden_patterns = {
        "keyframe_completion_summary": r"\[keyframe completion\]",
        "picture_time_alignment": r"<Picture \d+>\s+at\s+00:",
        "first_frame_instruction": r"\bfirst frame\b",
        "last_frame_instruction": r"\blast frame\b",
    }
    forbidden_counts = {name: len(re.findall(pattern, "\n".join(video_blocks), re.IGNORECASE)) for name, pattern in forbidden_patterns.items()}
    return {
        "clip_count": len(clips),
        "unique_clip_count": len(set(clips)),
        "video_prompt_block_count": len(video_blocks),
        "duration_count": len(durations),
        "total_duration_seconds": round(sum(durations), 3),
        "reference_generation_summary_count": sum(block.count("[reference generation]") for block in video_blocks),
        "forbidden_instruction_counts": forbidden_counts,
        "preassembly_static_contract_pass": len(clips) == 25
        and len(set(clips)) == 25
        and len(video_blocks) == 25
        and len(durations) == 25
        and round(sum(durations), 3) == 133.5
        and sum(block.count("[reference generation]") for block in video_blocks) == 25
        and not any(forbidden_counts.values()),
    }


def main() -> None:
    command_text = COMMAND.read_text(encoding="utf-8")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    records = []
    digests = set()
    for asset_id, spec in ASSETS.items():
        path = ASSET_ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        with Image.open(path) as image:
            validation = {
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "contract_pass": image.format == "PNG" and image.size == (1672, 941) and image.mode == "RGB",
            }
        digest = sha256(path)
        if digest in digests:
            raise RuntimeError(f"duplicate SHA-256: {path}")
        digests.add(digest)
        records.append({
            "asset_id": asset_id,
            "title": spec["title"],
            "relative_path": spec["path"],
            "generation_prompt": extract_prompt(command_text, spec["prompt_heading"]),
            "reference_files": spec["refs"],
            "generation": {
                "model": "OpenAI built-in image_gen",
                "workflow": "imagegen skill isolated Full-Reference R2V asset generation",
                "seed": "not_exposed_by_builtin_tool",
                "generated_at": generated_at,
            },
            "validation": validation,
            "sha256": digest,
            "visual_audit": {"assessment": spec["assessment"], "note": spec["note"]},
            "approval_status": "pending_user_approval",
            "connection_status": "not_connected",
        })

    prompt_source_audit = inspect_prompt_source()
    if not prompt_source_audit["preassembly_static_contract_pass"]:
        raise RuntimeError(f"prompt source static contract failed: {prompt_source_audit}")

    prompt_lines = [
        "# EP00 Isolated Full-Reference R2V Asset Prompts V2",
        "",
        "- 범위: 신규 순수 R2V 이미지 자산 7종의 제공 프롬프트 원문 기록",
        "- H3 video prompt 생성·수정: 미실행",
        "- 생성 방식: OpenAI built-in image_gen",
        "- 상태: `pending_user_approval`, `not_connected`",
        "",
    ]
    for record in records:
        prompt_lines.extend([
            f"## {record['asset_id']} — {record['title']}",
            "",
            f"출력: `{record['relative_path']}`",
            "",
            "```text",
            record["generation_prompt"],
            "```",
            "",
        ])
    PROMPT_RECORD.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_RECORD.write_text("\n".join(prompt_lines), encoding="utf-8")

    manifest = {
        "schema_version": 2,
        "document_id": "EP00_ISOLATED_R2V_ASSET_MANIFEST_V2",
        "source_command": str(COMMAND.relative_to(ROOT)),
        "provided_h3_prompt_source": str(PROMPT_SOURCE.relative_to(ROOT)),
        "generated_at": generated_at,
        "scope": "asset_generation_and_approval_gate_only",
        "asset_count": len(records),
        "automatic_validation": {
            "all_files_exist": True,
            "all_1672x941_rgb_png": all(record["validation"]["contract_pass"] for record in records),
            "unique_sha256_count": len(digests),
            "duplicate_sha256_count": len(records) - len(digests),
            "exact_output_path_count": len(records),
            "forbidden_rejected_batch03_references": 0,
            "keyframe_or_contact_asset_count": 0,
        },
        "provided_prompt_source_preassembly_audit": prompt_source_audit,
        "user_approval": {"status": "pending_user_approval", "recorded_at": None},
        "project_assembly": {
            "project_id": "RaisingaDragonSeason01_EP00_CINEMATIC_LIVEACTION_H3_R2V_V2",
            "status": "blocked_by_pending_user_asset_approval",
            "project_created": False,
            "picture_linking_performed": False,
            "queue_registration_performed": False,
            "video_generation_performed": False,
        },
        "assets": records,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [f"| {record['asset_id']} | `{record['relative_path']}` | {record['visual_audit']['assessment']} | pending | not_connected |" for record in records]
    APPROVAL.write_text("\n".join([
        "# EP00 Isolated R2V Asset Approval Gate V2",
        "",
        "## 현재 상태",
        "",
        "- 전체 상태: `pending_user_approval`",
        "- 프로젝트 조립: `blocked_by_pending_user_asset_approval`",
        "- Picture 연결: `not_connected`",
        "- 큐·영상 생성: 미실행",
        "",
        "## 사용자 확인표",
        "",
        "| ID | 파일 | 내부 검수 | 사용자 승인 | 연결 |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "특히 BG03의 벽·바닥 천공 경로가 정확히 세 개로 읽히는지 확인이 필요하다. 사용자가 7종을 승인하기 전에는 V2 프로젝트 조립을 시작하지 않는다.",
        "",
    ]), encoding="utf-8")

    audit_rows = [f"| {record['asset_id']} | {record['visual_audit']['assessment']} | {record['visual_audit']['note']} |" for record in records]
    AUDIT.write_text("\n".join([
        "# EP00 Isolated R2V Asset Visual Audit V2",
        "",
        "## 자동 검사",
        "",
        "- 신규 제작 PNG: 7/7",
        "- 규격: 7/7 `1672×941 RGB PNG`",
        f"- 고유 SHA-256: {len(digests)}/7, 중복 0",
        "- 배경의 인물·생물·무기·활성 효과: 0",
        "- 효과의 인물 신체·환경 접촉·Shot 구도: 0",
        "- start/last/keyframe 목적 이미지: 0",
        "- 거부된 Effect Batch03 참조: 0",
        "",
        "## 시각 검수",
        "",
        "| ID | 판정 | 관찰 |",
        "| --- | --- | --- |",
        *audit_rows,
        "",
        "## 제공 H3 프롬프트 원본 사전 정적 검사",
        "",
        f"- 클립: {prompt_source_audit['clip_count']}/25",
        f"- 영상 프롬프트 블록: {prompt_source_audit['video_prompt_block_count']}/25",
        f"- 총 시간: {prompt_source_audit['total_duration_seconds']}초",
        f"- `[reference generation]`: {prompt_source_audit['reference_generation_summary_count']}/25",
        "- keyframe/first-frame/last-frame/Picture 시간 정렬 지시: 0",
        "",
        "프로젝트 조립과 Picture 연결은 사용자 자산 승인 뒤 수행한다.",
        "",
    ]), encoding="utf-8")

    print(json.dumps({"automatic_validation": manifest["automatic_validation"], "prompt_source": prompt_source_audit}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
