"""Independent notebooks. No project/job ownership or cascading deletion."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from job_queue import atomic_write_json, now_iso, queue_claim_lock


def directory(root: Path, note_id: str) -> Path:
    if not re.fullmatch(r"note_[0-9a-f]{32}", str(note_id)):
        raise ValueError("유효하지 않은 노트 ID입니다.")
    base = (root / "runtime/feedback_notes").resolve()
    target = base / note_id
    if target.resolve().parent != base:
        raise ValueError("노트 경로가 저장소 밖에 있습니다.")
    return target


def read(path: Path):
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(record, dict) or not record.get("revision"):
        raise ValueError("노트 저장 파일을 읽을 수 없습니다. 원본을 보존하고 복구가 필요합니다.")
    return record


def metadata(record):
    return {key: record[key] for key in ("note_id", "title", "revision", "created_at", "updated_at", "archived")}


def listing(root: Path, data: dict) -> dict:
    base = root / "runtime/feedback_notes"
    notes = []
    if base.is_dir():
        for item in base.glob("note_*/note.json"):
            record = read(item)
            if record and bool(record["archived"]) == bool(data.get("archived")):
                notes.append(metadata(record))
    notes.sort(key=lambda item: (item["updated_at"], item["note_id"]), reverse=True)
    return {"notes": notes}


def load(root: Path, data: dict) -> dict:
    folder = directory(root, data.get("note_id", ""))
    revision = data.get("revision")
    if revision is not None:
        if not re.fullmatch(r"[0-9a-f]{32}", str(revision)):
            raise ValueError("유효하지 않은 노트 버전입니다.")
        record = read(folder / "revisions" / f"{revision}.json")
    else:
        record = read(folder / "note.json")
    return record or {"not_found": True, "error": "노트를 찾을 수 없습니다."}


def history(root: Path, data: dict) -> dict:
    folder = directory(root, data.get("note_id", ""))
    if not (folder / "note.json").is_file():
        return {"not_found": True, "error": "노트를 찾을 수 없습니다."}
    records, seen = [], set()
    record = read(folder / "note.json")
    while record:
        revision = record["revision"]
        if revision in seen:
            raise ValueError("노트 이력 연결이 손상되었습니다.")
        seen.add(revision)
        records.append(metadata(record))
        parent = record.get("parent_revision")
        record = read(folder / "revisions" / f"{parent}.json") if parent else None
    return {"revisions": records}


def save(root: Path, data: dict) -> dict:
    note_id = data.get("note_id") or f"note_{uuid.uuid4().hex}"
    folder = directory(root, note_id)
    if "expected_revision" not in data:
        raise ValueError("저장 기준 revision이 필요합니다.")
    with queue_claim_lock(folder):
        previous = read(folder / "note.json")
        expected = previous["revision"] if previous else None
        if data["expected_revision"] != expected:
            return {"conflict": True, "error": "다른 화면에서 수정된 노트입니다. 작성 중인 내용을 보존한 채 서버 버전을 확인하세요.", "current": previous}
        title = data.get("title", previous["title"] if previous else "제목 없는 노트")
        body = data.get("body", previous["body"] if previous else "")
        archived = data.get("archived", previous["archived"] if previous else False)
        if not isinstance(title, str) or len(title) > 200:
            raise ValueError("노트 제목은 200자 이하여야 합니다.")
        if not isinstance(body, str) or len(body) > 500_000:
            raise ValueError("노트 본문은 500,000자 이하여야 합니다.")
        if not isinstance(archived, bool):
            raise ValueError("보관 상태가 올바르지 않습니다.")
        title = title.strip() or "제목 없는 노트"
        if previous and all(previous[key] == value for key, value in (("title", title), ("body", body), ("archived", archived))):
            return previous
        timestamp = now_iso()
        record = {"schema_version": 1, "note_id": note_id, "title": title, "body": body,
                  "revision": uuid.uuid4().hex, "parent_revision": expected, "archived": archived,
                  "created_at": previous["created_at"] if previous else timestamp, "updated_at": timestamp}
        atomic_write_json(folder / "revisions" / f"{record['revision']}.json", record)
        atomic_write_json(folder / "note.json", record)
        return record


def video_context(root: Path, data: dict) -> dict:
    """Resolve an optional bookmark, even after its project was removed."""
    from job_queue import read_json
    import h3_queue

    job_id = h3_queue._safe_id(str(data.get("job_id") or ""), "작업 ID")
    folder = h3_queue.roots(root)["jobs"] / job_id
    request = read_json(folder / "request.json", None)
    if not request:
        return {"not_found": True, "error": "참조한 생성 기록을 찾을 수 없습니다. 노트 내용은 유지됩니다."}
    status = read_json(folder / "status.json", {}) or {}
    return {"job_id": job_id, "request": request, "status": status}
