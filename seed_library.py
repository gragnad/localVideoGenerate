from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from job_queue import atomic_write_json, now_iso, read_json

STOPWORDS={
    "a","an","the","and","or","to","of","in","on","at","for","with","from","by","is","are","was","were",
    "be","been","being","this","that","these","those","it","its","as","not","all","any","each","both",
    "project","style","original","wide","must","only","natural","all","spoken","dialogue","clip","visible",
    "characters","action","flow","using","into","while","without","after","before","during","through",
}

TOKEN_PATTERN=re.compile(r"[0-9a-zA-Z가-힣]+(?:[-_][0-9a-zA-Z가-힣]+)*")


def library_dir(root: Path)->Path:
    return root/"runtime/seed_library"


def entries_dir(root: Path)->Path:
    return library_dir(root)/"entries"


def entry_path(root: Path, entry_id: str)->Path:
    safe=str(entry_id or "").strip()
    if not safe or Path(safe).name!=safe or safe in {".",".."}:
        raise ValueError("허용되지 않는 seed 라이브러리 ID입니다.")
    return entries_dir(root)/f"{safe}.json"


def tokenize_prompt(text: str)->list[str]:
    tokens=[]
    seen=set()
    for match in TOKEN_PATTERN.finditer(str(text or "").lower()):
        token=match.group(0).strip("_-")
        if len(token)<2 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def combined_prompt_text(global_prompt: str, segments: list[dict[str, Any]]|None)->str:
    parts=[str(global_prompt or "").strip()]
    for segment in sorted(segments or [], key=lambda x:int(x.get("order") or 0)):
        prompt=str(segment.get("prompt") or "").strip()
        if prompt:
            parts.append(prompt)
    return "\n".join(part for part in parts if part)


def image_fingerprints(segments: list[dict[str, Any]]|None)->list[str]:
    values=[]
    seen=set()
    for segment in segments or []:
        digest=str(segment.get("sha256") or "").strip().lower()
        if len(digest)!=64 or digest in seen:
            continue
        seen.add(digest)
        values.append(digest)
    return values


def _parse_iso(value: str)->datetime|None:
    try:
        parsed=datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed=parsed.replace(tzinfo=timezone.utc)
    return parsed


def _lora_seed_from_workflow(job_dir: Path)->int|None:
    for name in ("workflow_api_runtime.json","selected_workflow_api.json"):
        payload=read_json(job_dir/name,{}) or {}
        if not isinstance(payload,dict):
            continue
        for node in payload.values():
            if not isinstance(node,dict):
                continue
            inputs=node.get("inputs") or {}
            if "seed" in inputs and "lora" in str(node.get("class_type") or "").lower():
                try:
                    return int(inputs["seed"])
                except (TypeError,ValueError):
                    continue
    return None


def entry_from_request(request: dict[str,Any], *, job_id: str, source_kind: str, job_dir: Path|None=None)->dict[str,Any]:
    resolution=request.get("resolution") or {}
    segments=list(request.get("segments") or [])
    combined=combined_prompt_text(str(request.get("global_prompt") or ""), segments)
    video_seed=int(request.get("seed") or 0)
    raw_input=request.get("seed_input")
    seed_mode=str(request.get("seed_mode") or ("random" if isinstance(raw_input,int) and raw_input<0 else "fixed"))
    lora_seed=_lora_seed_from_workflow(job_dir) if job_dir else None
    return {
        "schema_version":1,
        "entry_id":f"seed_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}",
        "created_at":now_iso(),
        "updated_at":now_iso(),
        "source":{
            "kind":source_kind,
            "job_id":job_id,
            "candidate_set_id":str(request.get("candidate_set_id") or ""),
            "candidate_index":int(request.get("candidate_index") or 0) or None,
        },
        "seeds":{
            "video_noise_seed":video_seed,
            "lora_seed":lora_seed,
            "seed_mode":seed_mode,
            "seed_input":raw_input,
        },
        "generation":{
            "workflow":"LTX_Director_2",
            "workflow_kind":str(request.get("workflow_kind") or "create"),
            "resolution":{"width":int(resolution.get("width") or 0), "height":int(resolution.get("height") or 0)},
            "fps":int(request.get("fps") or 24),
            "segment_count":len(segments),
        },
        "prompts":{
            "global_prompt":str(request.get("global_prompt") or ""),
            "segments":[{"order":int(x.get("order") or 0), "original_name":str(x.get("original_name") or ""), "prompt":str(x.get("prompt") or ""), "seconds":float(x.get("seconds") or 0), "sha256":str(x.get("sha256") or "")} for x in segments],
            "combined_text":combined,
        },
        "index_tokens":tokenize_prompt(combined),
        "image_fingerprints":image_fingerprints(segments),
        "signals":{"liked":source_kind.endswith("_like"), "liked_at":now_iso() if source_kind.endswith("_like") else None, "selected_final":source_kind=="candidate_select", "review_accepted":None},
        "usage_stats":{"like_count":1 if source_kind.endswith("_like") else 0, "recommended_count":0, "applied_count":0},
    }


def save_entry(root: Path, entry: dict[str,Any])->dict[str,Any]:
    directory=entries_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path=entry_path(root,str(entry["entry_id"]))
    entry["updated_at"]=now_iso()
    atomic_write_json(path,entry)
    return entry


def load_entry(root: Path, entry_id: str)->dict[str,Any]:
    payload=read_json(entry_path(root,entry_id),{}) or {}
    if not payload:
        raise FileNotFoundError(f"seed 라이브러리 항목을 찾을 수 없습니다: {entry_id}")
    return payload


def list_entries(root: Path)->list[dict[str,Any]]:
    directory=entries_dir(root)
    if not directory.is_dir():
        return []
    entries=[]
    for path in sorted(directory.glob("seed_*.json"), key=lambda x:x.stat().st_mtime, reverse=True):
        payload=read_json(path,{}) or {}
        if payload:
            entries.append(payload)
    return entries


def find_entry_by_job(root: Path, job_id: str)->dict[str,Any]|None:
    for entry in list_entries(root):
        if str(entry.get("source",{}).get("job_id") or "")==job_id:
            return entry
    return None


def like_seed_entry(root: Path, job_id: str, request: dict[str,Any], job_dir: Path)->dict[str,Any]:
    existing=find_entry_by_job(root,job_id)
    if existing:
        existing.setdefault("signals",{})["liked"]=True
        existing["signals"]["liked_at"]=now_iso()
        existing.setdefault("usage_stats",{})["like_count"]=int(existing.get("usage_stats",{}).get("like_count") or 0)+1
        return save_entry(root,existing)
    entry=entry_from_request(request, job_id=job_id, source_kind="candidate_like", job_dir=job_dir)
    return save_entry(root,entry)


def mark_selected_final(root: Path, job_id: str, request: dict[str,Any], job_dir: Path)->dict[str,Any]|None:
    existing=find_entry_by_job(root,job_id)
    if existing:
        existing.setdefault("signals",{})["selected_final"]=True
        existing["signals"]["selected_at"]=now_iso()
        return save_entry(root,existing)
    entry=entry_from_request(request, job_id=job_id, source_kind="candidate_select", job_dir=job_dir)
    entry["signals"]["liked"]=False
    entry["usage_stats"]["like_count"]=0
    return save_entry(root,entry)


def delete_seed_entry(root: Path, entry_id: str)->dict[str,Any]:
    path=entry_path(root,entry_id)
    if not path.is_file():
        raise FileNotFoundError(f"seed 라이브러리 항목을 찾을 수 없습니다: {entry_id}")
    path.unlink(missing_ok=True)
    return {"entry_id":entry_id,"deleted":True}


def _score_entry(entry: dict[str,Any], query: dict[str,Any])->dict[str,Any]|None:
    query_tokens=set(tokenize_prompt(str(query.get("combined_text") or "")))
    if not query_tokens:
        return None
    entry_tokens=set(entry.get("index_tokens") or [])
    if not entry_tokens:
        return None
    matched=sorted(query_tokens & entry_tokens)
    union=query_tokens | entry_tokens
    overlap=len(matched)/len(union) if union else 0.0
    score=overlap*10.0
    reasons=[]
    if matched:
        reasons.append(f"토큰 {len(matched)}개 매칭")
    query_res=query.get("resolution") or {}
    entry_res=(entry.get("generation") or {}).get("resolution") or {}
    if int(query_res.get("width") or 0)==int(entry_res.get("width") or 0) and int(query_res.get("height") or 0)==int(entry_res.get("height") or 0):
        score+=3.0
        reasons.append(f"{entry_res.get('width')}×{entry_res.get('height')} 동일")
    if int(query.get("fps") or 0)==int((entry.get("generation") or {}).get("fps") or 0):
        score+=1.0
        reasons.append("FPS 동일")
    query_segments=int(query.get("segment_count") or 0)
    entry_segments=int((entry.get("generation") or {}).get("segment_count") or 0)
    if query_segments and entry_segments and abs(query_segments-entry_segments)<=1:
        score+=1.0
        reasons.append("세그먼트 수 유사")
    query_images=set(query.get("image_fingerprints") or [])
    entry_images=set(entry.get("image_fingerprints") or [])
    shared=sorted(query_images & entry_images)
    if shared:
        score+=5.0
        reasons.append(f"이미지 {len(shared)}개 동일")
    signals=entry.get("signals") or {}
    if signals.get("selected_final"):
        score+=4.0
        reasons.append("최종 선택됨")
    if signals.get("review_accepted") is True:
        score+=2.0
        reasons.append("AI 검수 통과")
    if signals.get("liked"):
        score+=2.0
        reasons.append("좋아요 저장")
    liked_at=_parse_iso(str(signals.get("liked_at") or entry.get("created_at") or ""))
    if liked_at:
        age_days=max(0.0,(datetime.now(timezone.utc)-liked_at.astimezone(timezone.utc)).total_seconds()/86400.0)
        if age_days<=30:
            score+=1.0
    if score<=0:
        return None
    return {
        "entry_id":entry.get("entry_id"),
        "video_noise_seed":int((entry.get("seeds") or {}).get("video_noise_seed") or 0),
        "score":round(score,2),
        "reasons":reasons,
        "matched_tokens":matched[:8],
        "sample_job_id":str((entry.get("source") or {}).get("job_id") or ""),
        "liked_at":signals.get("liked_at") or entry.get("created_at"),
    }


def recommend_seeds(root: Path, query: dict[str,Any], *, limit: int=5)->dict[str,Any]:
    combined=combined_prompt_text(str(query.get("global_prompt") or ""), query.get("segments") or [])
    normalized={
        "combined_text":combined,
        "global_prompt":str(query.get("global_prompt") or ""),
        "segments":query.get("segments") or [],
        "fps":int(query.get("fps") or 24),
        "width":int(query.get("width") or 0),
        "height":int(query.get("height") or 0),
        "resolution":{"width":int(query.get("width") or 0), "height":int(query.get("height") or 0)},
        "segment_count":len(query.get("segments") or []),
        "image_fingerprints":image_fingerprints(query.get("segments") or []),
    }
    scored=[]
    seen_seeds=set()
    for entry in list_entries(root):
        signals=entry.get("signals") or {}
        if not (signals.get("liked") or signals.get("selected_final")):
            continue
        result=_score_entry(entry,normalized)
        if not result:
            continue
        seed=result["video_noise_seed"]
        if seed in seen_seeds:
            continue
        seen_seeds.add(seed)
        scored.append(result)
    scored.sort(key=lambda item:(item["score"], item.get("liked_at") or ""), reverse=True)
    return {
        "recommendations":scored[:max(1,limit)],
        "mode":"random_default",
        "query_token_count":len(tokenize_prompt(combined)),
    }


def list_seed_library(root: Path)->dict[str,Any]:
    entries=list_entries(root)
    liked_job_ids=sorted({str(entry.get("source",{}).get("job_id") or "") for entry in entries if (entry.get("signals") or {}).get("liked") and entry.get("source",{}).get("job_id")})
    return {"entries":entries, "liked_job_ids":liked_job_ids, "count":len(entries)}
