from __future__ import annotations

"""Immutable, content-addressed assets used by canonical benchmark cases."""

import hashlib
import json
from pathlib import Path
from typing import Any

MAX_ASSET_BYTES = 50 * 1024 * 1024


def _image_format(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    raise ValueError("PNG, JPEG 또는 WEBP 이미지 파일만 사용할 수 있습니다.")


def _safe_text(value: Any, maximum: int = 500) -> str:
    result = str(value or "").strip()
    if len(result) > maximum:
        raise ValueError(f"텍스트는 {maximum}자 이하여야 합니다.")
    return result


def save_and_link(root: Path, connection, data: dict[str, Any]) -> dict[str, Any]:
    case_version_id = _safe_text(data.get("case_version_id"))
    role = _safe_text(data.get("role"))
    upload_path = Path(str(data.get("upload_path") or ""))
    if not case_version_id or not role:
        raise ValueError("테스트 케이스와 자산 역할이 필요합니다.")
    requirement = connection.execute(
        "SELECT * FROM benchmark_case_asset_requirements WHERE case_version_id=? AND role=?",
        (case_version_id, role),
    ).fetchone()
    if not requirement:
        raise ValueError("이 테스트 케이스에 정의되지 않은 자산 역할입니다.")
    if not upload_path.is_file():
        raise FileNotFoundError("업로드된 테스트 자산을 찾을 수 없습니다.")
    size = upload_path.stat().st_size
    if size <= 0 or size > MAX_ASSET_BYTES:
        raise ValueError("테스트 이미지는 0바이트보다 크고 50MB 이하여야 합니다.")
    data_bytes = upload_path.read_bytes()
    suffix, mime_type = _image_format(data_bytes)
    digest = hashlib.sha256(data_bytes).hexdigest()
    asset_id = f"asset_{digest}"
    asset_dir = root / "runtime/evaluation/assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    target = asset_dir / f"{digest}{suffix}"
    if not target.exists():
        temporary = asset_dir / f".{digest}.tmp"
        temporary.write_bytes(data_bytes)
        temporary.replace(target)
    metadata = {
        "original_name": Path(_safe_text(data.get("original_name")) or upload_path.name).name,
        "mime_type": mime_type,
        "size_bytes": size,
    }
    connection.execute(
        """INSERT OR IGNORE INTO assets(asset_id,kind,path,sha256,metadata_json)
           VALUES (?,'image',?,?,?)""",
        (asset_id, str(target), digest, json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
    )
    connection.execute(
        """INSERT INTO benchmark_case_assets(case_version_id,asset_id,role,ordering)
           VALUES (?,?,?,1)
           ON CONFLICT(case_version_id,role,ordering) DO UPDATE SET asset_id=excluded.asset_id,linked_at=CURRENT_TIMESTAMP""",
        (case_version_id, asset_id, role),
    )
    connection.commit()
    return {"asset_id": asset_id, "case_version_id": case_version_id, "role": role, "sha256": digest, "size_bytes": size, "mime_type": mime_type}


def unlink(connection, data: dict[str, Any]) -> dict[str, Any]:
    case_version_id = _safe_text(data.get("case_version_id"))
    role = _safe_text(data.get("role"))
    cursor = connection.execute(
        "DELETE FROM benchmark_case_assets WHERE case_version_id=? AND role=?",
        (case_version_id, role),
    )
    connection.commit()
    if not cursor.rowcount:
        raise FileNotFoundError("연결된 테스트 자산을 찾을 수 없습니다.")
    return {"case_version_id": case_version_id, "role": role, "unlinked": True}


def _r2v_shared_targets(connection, shared_asset_key: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    rows = connection.execute(
        """SELECT DISTINCT v.case_version_id,v.title,v.contract_json
           FROM benchmark_case_versions v
           JOIN suite_cases sc ON sc.case_version_id=v.case_version_id
           JOIN benchmark_suites s ON s.suite_id=sc.suite_id
           WHERE s.active=1 ORDER BY v.case_version_id"""
    )
    for row in rows:
        contract = json.loads(row["contract_json"] or "{}")
        if contract.get("input_mode") != "h3_r2v_multi_reference":
            continue
        for slot in contract.get("reference_slots") or []:
            if str(slot.get("shared_asset_key") or "") != shared_asset_key:
                continue
            targets.append({
                "case_version_id": str(row["case_version_id"]),
                "case_title": str(row["title"]),
                "role": str(slot["role"]),
                "label_ko": str(slot.get("label_ko") or slot["role"]),
                "visual_style": str(contract.get("visual_style") or "stylized_3d"),
                "image_generation_prompt": str(slot.get("image_generation_prompt") or ""),
            })
    return targets


def r2v_shared_groups(connection) -> list[dict[str, Any]]:
    keys: set[str] = set()
    for row in connection.execute(
        """SELECT DISTINCT v.contract_json FROM benchmark_case_versions v
           JOIN suite_cases sc ON sc.case_version_id=v.case_version_id
           JOIN benchmark_suites s ON s.suite_id=sc.suite_id WHERE s.active=1"""
    ):
        contract = json.loads(row["contract_json"] or "{}")
        if contract.get("input_mode") != "h3_r2v_multi_reference":
            continue
        keys.update(
            str(slot.get("shared_asset_key"))
            for slot in (contract.get("reference_slots") or [])
            if slot.get("shared_asset_key")
        )
    groups = []
    for key in sorted(keys):
        targets = _r2v_shared_targets(connection, key)
        links = connection.execute(
            """SELECT DISTINCT l.asset_id,a.sha256,a.metadata_json
               FROM benchmark_case_assets l JOIN assets a ON a.asset_id=l.asset_id
               WHERE (l.case_version_id,l.role) IN (
                   SELECT v.case_version_id,json_extract(slot.value,'$.role')
                   FROM benchmark_case_versions v
                   JOIN json_each(v.contract_json,'$.reference_slots') slot
                   WHERE json_extract(slot.value,'$.shared_asset_key')=?
               )""",
            (key,),
        ).fetchall()
        asset = None
        if len(links) == 1:
            row = links[0]
            metadata = json.loads(row["metadata_json"] or "{}")
            asset = {
                "asset_id": row["asset_id"],
                "sha256": row["sha256"],
                "metadata": metadata,
                "file_url": f"/api/model-tests/assets/{row['asset_id']}/file",
            }
        groups.append({
            "shared_asset_key": key,
            "label_ko": targets[0]["label_ko"] if targets else key,
            "visual_style": targets[0]["visual_style"] if targets else "",
            "target_count": len(targets),
            "linked_count": sum(
                1
                for target in targets
                if connection.execute(
                    "SELECT 1 FROM benchmark_case_assets WHERE case_version_id=? AND role=?",
                    (target["case_version_id"], target["role"]),
                ).fetchone()
            ),
            "targets": targets,
            "image_generation_prompt": targets[0]["image_generation_prompt"] if targets else "",
            "asset": asset,
            "conflict": len(links) > 1,
        })
    return groups


def save_and_link_r2v_shared(root: Path, connection, data: dict[str, Any]) -> dict[str, Any]:
    key = _safe_text(data.get("shared_asset_key"))
    targets = _r2v_shared_targets(connection, key)
    if not key or not targets:
        raise ValueError("정의된 R2V 전역 공유 자산 그룹을 찾을 수 없습니다.")
    first = targets[0]
    saved = save_and_link(root, connection, {
        **data,
        "case_version_id": first["case_version_id"],
        "role": first["role"],
    })
    for target in targets[1:]:
        requirement = connection.execute(
            "SELECT 1 FROM benchmark_case_asset_requirements WHERE case_version_id=? AND role=?",
            (target["case_version_id"], target["role"]),
        ).fetchone()
        if not requirement:
            raise ValueError("공유 그룹의 Picture 역할 정의가 일치하지 않습니다.")
        connection.execute(
            """INSERT INTO benchmark_case_assets(case_version_id,asset_id,role,ordering)
               VALUES (?,?,?,1)
               ON CONFLICT(case_version_id,role,ordering)
               DO UPDATE SET asset_id=excluded.asset_id,linked_at=CURRENT_TIMESTAMP""",
            (target["case_version_id"], saved["asset_id"], target["role"]),
        )
    connection.commit()
    return {
        **saved,
        "shared_asset_key": key,
        "linked_count": len(targets),
        "targets": targets,
    }


def unlink_r2v_shared(connection, data: dict[str, Any]) -> dict[str, Any]:
    key = _safe_text(data.get("shared_asset_key"))
    targets = _r2v_shared_targets(connection, key)
    if not key or not targets:
        raise ValueError("정의된 R2V 전역 공유 자산 그룹을 찾을 수 없습니다.")
    deleted = 0
    for target in targets:
        cursor = connection.execute(
            "DELETE FROM benchmark_case_assets WHERE case_version_id=? AND role=?",
            (target["case_version_id"], target["role"]),
        )
        deleted += int(cursor.rowcount or 0)
    connection.commit()
    if not deleted:
        raise FileNotFoundError("연결된 R2V 전역 공유 자산을 찾을 수 없습니다.")
    return {"shared_asset_key": key, "unlinked": True, "unlinked_count": deleted}


def resolve_file(root: Path, connection, asset_id: str) -> Path:
    row = connection.execute("SELECT path,sha256 FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
    if not row:
        raise FileNotFoundError("테스트 자산을 찾을 수 없습니다.")
    base = (root / "runtime/evaluation/assets").resolve()
    path = Path(row["path"]).resolve()
    if base not in path.parents or not path.is_file():
        raise FileNotFoundError("허용된 자산 폴더에서 파일을 찾을 수 없습니다.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise ValueError("테스트 자산 파일 해시가 변경되었습니다.")
    return path


def case_assets(connection) -> list[dict[str, Any]]:
    rows = []
    for row in connection.execute(
        """SELECT l.case_version_id,l.asset_id,l.role,l.ordering,l.linked_at,
                  a.sha256,a.path,a.metadata_json
           FROM benchmark_case_assets l JOIN assets a ON a.asset_id=l.asset_id
           ORDER BY l.case_version_id,l.role,l.ordering"""
    ):
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        item.pop("path", None)
        item["file_url"] = f"/api/model-tests/assets/{item['asset_id']}/file"
        rows.append(item)
    return rows
