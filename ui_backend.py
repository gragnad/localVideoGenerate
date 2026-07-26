from __future__ import annotations

import hashlib, hmac, json, os, secrets, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
from typing import Any

import correction_policy
from batch_manager import attach_job_to_batch, clear_open_batch_pointer, create_new_open_batch, find_batches_by_status, get_or_create_open_batch, load_batch, load_automation_settings, save_automation_settings, update_batch
from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json, update_status
from video_assembler import VideoAssemblerError, assemble_clips, probe_video
from workflow_builder import KOREAN_SPEECH_POLICY, resolve_seed, sanitize_token

HOME=Path.home()
ROOT=Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME/"local-ai/video-engine"))
JOBS=ROOT/"jobs"
WF_DIR=Path(os.environ.get("COMFY_WORKFLOW_DIR", HOME/"ai-workspace/apps/ComfyUI/user/default/workflows")).expanduser()
CR=WF_DIR/"(CR)LTX_Director_2_API.json"
MD=WF_DIR/"(MD)LTX_Retake_Partial_API.json"
VIDEO_SUFFIXES={".mp4",".webm",".mov",".mkv",".avi"}
COMFY_ROOT=Path(os.environ.get("COMFY_ROOT", HOME/"ai-workspace/apps/ComfyUI")).expanduser()
COMFY_OUTPUT=Path(os.environ.get("COMFY_OUTPUT_DIR", COMFY_ROOT/"output")).expanduser()
COMFY_INPUT=Path(os.environ.get("COMFY_INPUT_DIR", COMFY_ROOT/"input")).expanduser()
DELETABLE_BATCH_STATUSES={"completed_generation_only","review_completed","manual_review_required","modification_limit_reached","review_complete_needs_modification","ai_review_failed","failed","cancelled","pipeline_failed","awaiting_candidate_selection","candidate_selected"}
DEFAULT_GLOBAL="Project style: Original ocean fantasy growth-adventure world, cinematic fantasy realism, wide 16:9. "+KOREAN_SPEECH_POLICY
CANDIDATE_SETS=ROOT/"runtime/candidate_sets"
COMPOSITIONS=ROOT/"runtime/compositions"
MAX_ASSEMBLY_CLIPS=4
MIN_ASSEMBLY_CLIPS=2
MAX_ASSEMBLY_TOTAL_SECONDS=60.0
DEFAULT_GENERATION_WIDTH=1536
DEFAULT_GENERATION_HEIGHT=864

def job(job_id: str)->dict[str,Any]:
    if not job_id or Path(job_id).name!=job_id or job_id in {".",".."}: raise ValueError("허용되지 않는 작업 ID입니다.")
    d=JOBS/job_id
    if not d.is_dir(): raise FileNotFoundError(f"작업을 찾을 수 없습니다: {job_id}")
    return {"job_id":job_id,"dir":d,"request":read_json(d/"request.json",{}) or {},"manifest":read_json(d/"manifest.json",{}) or {},"status":read_json(d/"status.json",{}) or {}}

def root_for(item):
    root_id=str(item["request"].get("root_job_id") or item["manifest"].get("root_job_id") or item["job_id"])
    return job(root_id)

def report_for(item):
    direct=read_json(item["dir"]/"ai_review_report.json",{}) or {}
    if direct:return direct
    embedded=item["manifest"].get("ai_review")
    if isinstance(embedded,dict):return embedded
    p=item["request"].get("source_review_report") or item["manifest"].get("source_review_report")
    return read_json(Path(str(p)),{}) or {} if p else {}

def duration(root,report):
    return max(float(report.get("duration_seconds") or 0),sum(float(x.get("seconds") or 0) for x in root["request"].get("segments") or []),float(root["request"].get("target_total_seconds") or 0))

def prompt_action(data):
    source=job(str(data["source_job_id"])); root=root_for(source); report=report_for(source); total=duration(root,report)
    mode=str(data.get("correction_mode") or "partial_retake")
    if mode=="auto": mode=correction_policy.recommend_correction_mode(report) if report else "partial_retake"
    start=float(data.get("start_seconds") or 0); end=float(data.get("end_seconds") or total)
    if mode=="full_regeneration":start,end=0,total
    prompt=correction_policy.build_retake_prompt(report,root["request"],start_seconds=start,end_seconds=end,correction_mode=mode,user_instruction=str(data.get("user_instruction") or ""))
    return {"prompt":prompt,"correction_mode":mode,"start_seconds":start,"end_seconds":end,"duration_seconds":total}

def safe_name(name,data,index):
    suffix=Path(name).suffix.lower() or ".png"; stem=sanitize_token(Path(name).stem,fallback=f"image_{index:02d}")
    return f"{index:02d}_{stem}_{hashlib.sha256(data).hexdigest()[:10]}{suffix}"

def create_action(data, target_batch_id: str | None = None):
    template=Path(str(data.get("template_path") or CR)).expanduser().resolve()
    if not template.is_file() or WF_DIR.resolve() not in template.parents: raise ValueError("허용된 API 워크플로가 아닙니다.")
    payload=json.loads(template.read_text());
    if not payload or any(not isinstance(v,dict) or "class_type" not in v for v in payload.values()):raise ValueError("ComfyUI API 형식이 아닙니다.")
    rows=[x for x in data.get("segments") or [] if x.get("enabled",True)]
    if not rows:raise ValueError("이미지를 한 장 이상 선택하세요.")
    copied_source=job(str(data["copied_from_job_id"])) if data.get("copied_from_job_id") else None
    settings=load_automation_settings(ROOT)
    if target_batch_id:
        batch=load_batch(ROOT,target_batch_id)
        if not batch or batch.get("status")!="open" or bool(batch.get("registration_closed")):
            raise RuntimeError(f"후보 작업을 등록할 수 없는 배치입니다: {target_batch_id}")
    else:
        batch=get_or_create_open_batch(ROOT,settings)
    batch_id=batch["batch_id"]
    requested_candidate_set=str(data.get("candidate_set_id") or "").strip()
    existing_candidate_sets=list(batch.get("candidate_set_ids") or [])
    if batch.get("batch_mode")=="candidate_selection" and requested_candidate_set not in existing_candidate_sets:
        raise RuntimeError("후보 전용 배치에는 일반 생성 작업을 추가할 수 없습니다.")
    name=str(data.get("job_name") or "LTX_scene"); token=sanitize_token(name,fallback="LTX_scene")
    jid=f"{datetime.now():%Y%m%d_%H%M%S}_{token}_{secrets.token_hex(2)}"; d=JOBS/jid; src=d/"source_images"; src.mkdir(parents=True)
    snap=d/"selected_workflow_api.json"; shutil.copy2(template,snap); segments=[]
    for i,row in enumerate(sorted(rows,key=lambda x:(int(x.get("order") or 0),str(x.get("original_name") or ""))),1):
        incoming=Path(str(row["upload_path"])); raw=incoming.read_bytes(); stored=safe_name(str(row.get("original_name") or incoming.name),raw,i); dest=src/stored; shutil.copy2(incoming,dest)
        segments.append({"original_name":str(row.get("original_name") or incoming.name),"stored_name":stored,"source_path":str(dest),"sha256":hashlib.sha256(raw).hexdigest(),"prompt":str(row.get("prompt") or "").strip(),"seconds":float(row.get("seconds") or 5),"order":int(row.get("order") or i)})
    if any(not x["prompt"] for x in segments):raise ValueError("모든 이미지 구간에 프롬프트가 필요합니다.")
    seed=resolve_seed(int(data.get("seed",-1))); created=now_iso(); width=int(data.get("width") or DEFAULT_GENERATION_WIDTH); height=int(data.get("height") or DEFAULT_GENERATION_HEIGHT)
    req={"schema_version":2,"job_type":"generate","pipeline_stage":"initial_generation","job_id":jid,"batch_id":batch_id,"job_dir":str(d),"created_at":created,"job_name":name,"template_path":str(snap),"workflow_source_path":str(template),"workflow_filename":template.name,"workflow_kind":"create","workflow_kind_label":"생성 (CR)","comfy_url":os.environ.get("COMFY_URL","http://127.0.0.1:8188"),"comfy_public_url":os.environ.get("COMFY_PUBLIC_URL",""),"comfy_start_script":os.environ.get("COMFY_START_SCRIPT",str(HOME/"bin/ai-start-comfy")),"comfy_start_timeout":float(os.environ.get("COMFY_START_TIMEOUT","180")),"auto_start_comfy":True,"fps":int(data.get("fps") or 24),"seed":seed,"resolution":{"width":width,"height":height,"label":f"{width} × {height}"},"global_prompt":str(data.get("global_prompt") or DEFAULT_GLOBAL).strip(),"duration_mode":str(data.get("duration_mode") or "각 구간 시간의 합계"),"target_total_seconds":data.get("target_total_seconds"),"filename_prefix":f"video/jobs/{jid}/{token}","segments":segments,"parent_job_id":None,"attempt":0,"automation":dict(batch.get("automation") or settings)}
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    if candidate_set_id:
        req.update(candidate_set_id=candidate_set_id,
                   candidate_index=int(data["candidate_index"]),
                   candidate_count=int(data["candidate_count"]),
                   review_policy="user_candidate_selection",
                   workflow_kind_label="후보 생성 (LTX Director)")
    if copied_source:
        req.update(
            creation_source="revision_studio",
            copied_from_job_id=copied_source["job_id"],
            copied_from_root_job_id=root_for(copied_source)["job_id"],
        )
    man={k:req[k] for k in ("schema_version","job_id","batch_id","job_type","pipeline_stage","created_at","workflow_source_path","workflow_filename","workflow_kind","workflow_kind_label","seed","resolution","fps","segments")}; man.update(status="queued",outputs=[])
    for key in ("creation_source","copied_from_job_id","copied_from_root_job_id"):
        if key in req:man[key]=req[key]
    for key in ("candidate_set_id","candidate_index","candidate_count","review_policy"):
        if key in req:man[key]=req[key]
    atomic_write_json(d/"request.json",req);atomic_write_json(d/"manifest.json",man);attach_job_to_batch(ROOT,batch_id,jid,"candidate" if candidate_set_id else "generate");update_status(d,"queued",stage="후보 생성 worker 대기" if candidate_set_id else "worker 대기",message="후보 작업 큐에 등록되었습니다." if candidate_set_id else "작업 큐에 등록되었습니다.",progress=0,created_at=created)
    return {"job_id":jid,"batch_id":batch_id}

def candidate_set_path(candidate_set_id: str)->Path:
    if not candidate_set_id or Path(candidate_set_id).name!=candidate_set_id or candidate_set_id in {".",".."}:
        raise ValueError("허용되지 않는 후보군 ID입니다.")
    return CANDIDATE_SETS/candidate_set_id/"candidate_set.json"

def load_candidate_set(candidate_set_id: str)->dict[str,Any]:
    payload=read_json(candidate_set_path(candidate_set_id),{}) or {}
    if not payload:raise FileNotFoundError(f"후보군을 찾을 수 없습니다: {candidate_set_id}")
    return payload

def save_candidate_set(payload: dict[str,Any])->dict[str,Any]:
    path=candidate_set_path(str(payload["candidate_set_id"]));path.parent.mkdir(parents=True,exist_ok=True)
    payload["updated_at"]=now_iso();atomic_write_json(path,payload);return payload

def active_candidate_generation_batches()->list[dict[str,Any]]:
    return [
        batch for batch in find_batches_by_status(ROOT,{"open"},limit=1000)
        if batch.get("batch_mode")=="candidate_selection"
    ]

def create_candidates_action(data):
    count=int(data.get("candidate_count") or 3)
    if count<2 or count>8:raise ValueError("후보 개수는 2~8개여야 합니다.")
    candidate_set_id=f"cset_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"
    base_seed=resolve_seed(int(data.get("seed",-1)));modulus=(1<<63)-1
    explicit=data.get("candidate_seeds") or []
    if explicit and len(explicit)!=count:raise ValueError("candidate_seeds 개수가 후보 개수와 일치하지 않습니다.")
    settings=load_automation_settings(ROOT);batch=create_new_open_batch(ROOT,settings);batch_id=str(batch["batch_id"])
    created=now_iso();created_jobs=[]
    update_batch(ROOT,batch_id,candidate_set_ids=[candidate_set_id],
                 batch_mode="candidate_selection",registration_closed=False,
                 message=f"후보 영상 {count}개를 독립 배치에 등록하고 있습니다.")
    for index in range(1,count+1):
        candidate_data=dict(data)
        candidate_data.update(candidate_set_id=candidate_set_id,candidate_index=index,candidate_count=count,
                              seed=int(explicit[index-1]) if explicit else (base_seed+index-1)%modulus)
        created_jobs.append(create_action(candidate_data,target_batch_id=batch_id))
    batch_ids={item["batch_id"] for item in created_jobs}
    if len(batch_ids)!=1:raise RuntimeError("하나의 후보군이 여러 배치로 분리되었습니다.")
    payload=save_candidate_set({"schema_version":1,"candidate_set_id":candidate_set_id,
        "status":"generating","created_at":created,"batch_id":batch_id,
        "candidate_count":count,"candidate_job_ids":[item["job_id"] for item in created_jobs],
        "selected_job_id":None,"final_review_batch_id":None})
    update_batch(ROOT,batch_id,registration_closed=True,registration_closed_at=now_iso(),
                 stage="candidate_jobs_queued",next_stage="generation",
                 message=f"후보 영상 {count}개가 독립 배치에 등록되었습니다. 앞선 배치 뒤에 실행됩니다.")
    return payload

def select_candidate_action(data):
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    selected_job_id=str(data.get("job_id") or "").strip();payload=load_candidate_set(candidate_set_id)
    active_batches=active_candidate_generation_batches()
    if active_batches:
        raise RuntimeError(f"등록된 후보 생성 배치 {len(active_batches)}개가 모두 끝난 뒤 선택할 수 있습니다.")
    if selected_job_id not in payload.get("candidate_job_ids",[]):raise ValueError("해당 후보군에 속하지 않는 작업입니다.")
    if payload.get("final_review_batch_id"):raise RuntimeError("검수가 등록된 후보군은 선택을 변경할 수 없습니다.")
    items=[job(job_id) for job_id in payload.get("candidate_job_ids") or []]
    statuses={item["job_id"]:str(item["status"].get("status") or "") for item in items}
    if any(status not in JOB_TERMINAL_STATUSES for status in statuses.values()):
        raise RuntimeError("모든 후보 생성이 끝난 뒤 선택할 수 있습니다.")
    if statuses.get(selected_job_id)!="completed":raise RuntimeError("완료된 후보만 선택할 수 있습니다.")
    selected_at=now_iso()
    for item in items:
        selected=item["job_id"]==selected_job_id
        for filename in ("request.json","manifest.json"):
            path=item["dir"]/filename;record=read_json(path,{}) or {};record.update(candidate_selected=selected,selected_at=selected_at if selected else None);atomic_write_json(path,record)
    payload.update(status="selected",selected_job_id=selected_job_id,selected_at=selected_at)
    save_candidate_set(payload)
    update_batch(ROOT,str(payload["batch_id"]),status="candidate_selected",stage="user_candidate_selected",
                 next_stage="final_review",selected_candidate_job_id=selected_job_id,
                 message=f"최종 후보 {selected_job_id}가 선택되었습니다. 04 최종 마스터에서 AI 검수를 등록하세요.")
    return load_candidate_set(candidate_set_id)

def source_video_path(item: dict[str,Any])->Path:
    direct=Path(str(item["manifest"].get("review_video_local_path") or ""))
    if direct.is_file():return direct
    descriptors=list(item["manifest"].get("outputs") or [])+list(item["status"].get("outputs") or [])
    for descriptor in descriptors:
        if Path(str(descriptor.get("filename") or "")).suffix.lower() not in VIDEO_SUFFIXES:continue
        candidate=(COMFY_OUTPUT/str(descriptor.get("subfolder") or "")/str(descriptor.get("filename") or "")).resolve()
        if candidate.is_file() and COMFY_OUTPUT.resolve() in candidate.parents:return candidate
    raise FileNotFoundError(f"선택 후보의 로컬 영상 파일을 찾을 수 없습니다: {item['job_id']}")

def composition_path(composition_id: str)->Path:
    if not composition_id or Path(composition_id).name!=composition_id or composition_id in {".",".."}:
        raise ValueError("허용되지 않는 합성 ID입니다.")
    return COMPOSITIONS/composition_id/"composition.json"

def load_composition(composition_id: str)->dict[str,Any]:
    payload=read_json(composition_path(composition_id),{}) or {}
    if not payload:raise FileNotFoundError(f"합성 프로젝트를 찾을 수 없습니다: {composition_id}")
    return payload

def save_composition(payload: dict[str,Any])->dict[str,Any]:
    path=composition_path(str(payload["composition_id"]))
    path.parent.mkdir(parents=True,exist_ok=True)
    payload["updated_at"]=now_iso()
    atomic_write_json(path,payload)
    return payload

def list_compositions_action(_data=None)->dict[str,Any]:
    items=[]
    if COMPOSITIONS.is_dir():
        for directory in sorted(COMPOSITIONS.iterdir(),key=lambda x:x.name,reverse=True):
            if not directory.is_dir():continue
            payload=read_json(directory/"composition.json",{}) or {}
            if payload:items.append(payload)
    return {"compositions":items}

def _candidate_clip_item(item: dict[str,Any])->dict[str,Any]:
    request=item["request"];manifest=item["manifest"];status=item["status"]
    if not request.get("candidate_set_id"):raise ValueError("후보 작업만 선택할 수 있습니다.")
    if str(status.get("status") or "")!="completed":raise ValueError("완료된 후보만 선택할 수 있습니다.")
    source_path=source_video_path(item)
    probe=probe_video(source_path)
    resolution=request.get("resolution") or {}
    width=int(resolution.get("width") or probe.get("width") or 0)
    height=int(resolution.get("height") or probe.get("height") or 0)
    fps=int(request.get("fps") or round(float(probe.get("fps") or 24)))
    duration=float(probe.get("duration_seconds") or 0)
    if duration<=0:raise ValueError(f"영상 길이를 확인할 수 없습니다: {item['job_id']}")
    return {"source_job_id":item["job_id"],"candidate_set_id":str(request.get("candidate_set_id") or ""),
            "candidate_index":int(request.get("candidate_index") or 0),"job_name":str(request.get("job_name") or item["job_id"]),
            "batch_id":str(request.get("batch_id") or ""),"fps":fps,"resolution":{"width":width,"height":height},
            "duration_seconds":round(duration,3),"video_url":f"/api/jobs/{item['job_id']}/video",
            "source_path":str(source_path)}

def clip_library_action(_data=None)->dict[str,Any]:
    clips=[]
    if not JOBS.is_dir():return {"clips":[]}
    for directory in sorted(JOBS.iterdir(),key=lambda x:x.name,reverse=True):
        if not directory.is_dir():continue
        request=read_json(directory/"request.json",{}) or {}
        if not request.get("candidate_set_id"):continue
        status=read_json(directory/"status.json",{}) or {}
        if str(status.get("status") or "")!="completed":continue
        try:
            item=job(directory.name)
            meta=_candidate_clip_item(item)
            meta.pop("source_path", None)
            clips.append(meta)
        except (FileNotFoundError,ValueError,VideoAssemblerError):
            continue
    return {"clips":clips}

def _normalized_clip_rows(clips: list[dict[str,Any]])->list[dict[str,Any]]:
    if not isinstance(clips,list):raise ValueError("clips 배열이 필요합니다.")
    if len(clips)<MIN_ASSEMBLY_CLIPS or len(clips)>MAX_ASSEMBLY_CLIPS:
        raise ValueError(f"클립은 {MIN_ASSEMBLY_CLIPS}~{MAX_ASSEMBLY_CLIPS}개여야 합니다.")
    rows=[]
    for index,clip in enumerate(sorted(clips,key=lambda x:int(x.get("order") or 0)),1):
        source_job_id=str(clip.get("source_job_id") or "").strip()
        if not source_job_id:raise ValueError("모든 클립에 source_job_id가 필요합니다.")
        item=job(source_job_id)
        meta=_candidate_clip_item(item)
        start=float(clip.get("start_seconds") or 0)
        end=float(clip.get("end_seconds") or meta["duration_seconds"])
        if start<0 or end<=start:raise ValueError(f"클립 {index}의 시작·끝 시점이 올바르지 않습니다.")
        if end-start>meta["duration_seconds"]+0.05:
            raise ValueError(f"클립 {index}의 끝 시점이 원본 길이를 초과합니다.")
        if end>meta["duration_seconds"]+0.05:
            end=meta["duration_seconds"]
        rows.append({**meta,"order":int(clip.get("order") or index),"start_seconds":round(start,3),
                     "end_seconds":round(end,3),"duration_seconds":round(end-start,3),
                     "label":str(clip.get("label") or meta["job_name"])})
    fps=rows[0]["fps"];resolution=rows[0]["resolution"]
    total=0.0
    for row in rows:
        if row["fps"]!=fps:raise ValueError("모든 클립의 FPS가 같아야 합니다.")
        if row["resolution"]!=resolution:raise ValueError("모든 클립의 해상도가 같아야 합니다.")
        total+=row["duration_seconds"]
    if total>MAX_ASSEMBLY_TOTAL_SECONDS+0.01:
        raise ValueError(f"합성 총 길이는 최대 {int(MAX_ASSEMBLY_TOTAL_SECONDS)}초까지 가능합니다. 현재 {total:.1f}초")
    return rows

def create_composition_action(data):
    name=str(data.get("name") or "LTX_assembly").strip() or "LTX_assembly"
    composition_id=f"comp_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"
    clips=_normalized_clip_rows(data.get("clips") or []) if data.get("clips") else []
    payload={"schema_version":1,"composition_id":composition_id,"name":name,"status":"draft" if not clips else "ready",
             "created_at":now_iso(),"clips":clips,"fps":clips[0]["fps"] if clips else None,
             "resolution":clips[0]["resolution"] if clips else None,"total_duration_seconds":round(sum(x["duration_seconds"] for x in clips),3) if clips else 0,
             "assemble_job_id":None,"assembled_video_path":None,"final_review_batch_id":None}
    return save_composition(payload)

def update_composition_action(data):
    composition_id=str(data.get("composition_id") or "").strip()
    payload=load_composition(composition_id)
    if payload.get("status") in {"assembling"}:
        raise RuntimeError("실행 중인 합성 프로젝트는 수정할 수 없습니다.")
    if payload.get("status") in {"assembled","assemble_failed","final_review_failed","completed"}:
        payload["assemble_job_id"]=None
        payload["assembled_video_path"]=None
        payload["final_review_batch_id"]=None
        payload["status"]="ready"
    if "name" in data:payload["name"]=str(data.get("name") or payload.get("name") or "LTX_assembly").strip() or "LTX_assembly"
    if "clips" in data:
        clips=_normalized_clip_rows(data.get("clips") or [])
        payload.update(clips=clips,fps=clips[0]["fps"],resolution=clips[0]["resolution"],
                       total_duration_seconds=round(sum(x["duration_seconds"] for x in clips),3),status="ready")
    return save_composition(payload)

def assemble_composition_action(data):
    composition_id=str(data.get("composition_id") or "").strip()
    payload=load_composition(composition_id)
    if payload.get("status")=="assembling":raise RuntimeError("이미 합성이 진행 중입니다.")
    if payload.get("assemble_job_id"):
        existing=job(str(payload["assemble_job_id"]))
        if str(existing["status"].get("status") or "") not in JOB_TERMINAL_STATUSES:
            raise RuntimeError("기존 합성 작업이 아직 끝나지 않았습니다.")
    clips=_normalized_clip_rows(payload.get("clips") or [])
    settings=load_automation_settings(ROOT)
    final_settings=dict(settings);final_settings.update(auto_review=False,auto_modify=False,auto_recheck=False,max_modify_cycles=0)
    batch=create_new_open_batch(ROOT,final_settings);batch_id=str(batch["batch_id"])
    token=sanitize_token(str(payload.get("name") or composition_id),fallback="assembly")
    jid=f"{datetime.now():%Y%m%d_%H%M%S}_{token}_{secrets.token_hex(2)}"
    directory=JOBS/jid;directory.mkdir(parents=True);created=now_iso()
    req={"schema_version":2,"job_type":"assemble","pipeline_stage":"clip_stitch","job_id":jid,"batch_id":batch_id,
         "job_dir":str(directory),"created_at":created,"job_name":str(payload.get("name") or composition_id),
         "composition_id":composition_id,"workflow_kind":"assemble","workflow_kind_label":"후보 클립 합성",
         "fps":clips[0]["fps"],"resolution":clips[0]["resolution"],
         "total_duration_seconds":round(sum(x["duration_seconds"] for x in clips),3),
         "clips":[{key:clip[key] for key in ("order","source_job_id","candidate_set_id","candidate_index","start_seconds","end_seconds","duration_seconds","label","source_path")} for clip in clips],
         "filename_prefix":f"video/assembled/{composition_id}/{token}","automation":final_settings,"attempt":0}
    man={key:req[key] for key in ("schema_version","job_id","batch_id","job_type","pipeline_stage","created_at","composition_id","workflow_kind","workflow_kind_label","fps","resolution","total_duration_seconds")}
    man.update(status="queued",outputs=[])
    atomic_write_json(directory/"request.json",req);atomic_write_json(directory/"manifest.json",man)
    update_status(directory,"queued",stage="클립 합성 worker 대기",message=f"클립 {len(clips)}개",progress=0,created_at=created)
    attach_job_to_batch(ROOT,batch_id,jid,"assemble")
    update_batch(ROOT,batch_id,batch_mode="clip_assembly",composition_ids=[composition_id],registration_closed=True,
                 registration_closed_at=created,stage="assemble_queued",next_stage="generation",
                 message=f"후보 클립 {len(clips)}개 합성 작업이 등록되었습니다.")
    payload.update(status="assembling",assemble_job_id=jid,assembled_video_path=None,final_review_batch_id=None,assemble_batch_id=batch_id,assemble_queued_at=created)
    save_composition(payload)
    return {"composition_id":composition_id,"assemble_job_id":jid,"batch_id":batch_id,"clip_count":len(clips)}

def import_composition_video_action(data):
    upload_path=Path(str(data.get("upload_path") or ""))
    if not upload_path.is_file() or upload_path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError("편집본 영상 파일(mp4/webm/mov 등)을 업로드하세요.")
    composition_id=str(data.get("composition_id") or "").strip()
    name=str(data.get("name") or "LTX_assembly").strip() or "LTX_assembly"
    reference_source_job_id=str(data.get("reference_source_job_id") or "").strip()
    if composition_id:
        payload=load_composition(composition_id)
        if payload.get("status") in {"assembling"}:
            raise RuntimeError("실행 중인 합성 프로젝트에는 업로드할 수 없습니다.")
        payload["name"]=name
        if data.get("clips") is not None:
            if data.get("clips"):
                clips=_normalized_clip_rows(data.get("clips") or [])
                payload.update(clips=clips,fps=clips[0]["fps"],resolution=clips[0]["resolution"],
                               total_duration_seconds=round(sum(x["duration_seconds"] for x in clips),3))
            else:
                payload["clips"]=[]
        if reference_source_job_id:
            payload["reference_source_job_id"]=reference_source_job_id
    else:
        clips=_normalized_clip_rows(data.get("clips") or []) if data.get("clips") else []
        composition_id=f"comp_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"
        payload={"schema_version":1,"composition_id":composition_id,"name":name,
                 "status":"draft" if not clips else "ready","created_at":now_iso(),"clips":clips,
                 "fps":clips[0]["fps"] if clips else None,"resolution":clips[0]["resolution"] if clips else None,
                 "total_duration_seconds":round(sum(x["duration_seconds"] for x in clips),3) if clips else 0,
                 "assemble_job_id":None,"assembled_video_path":None,"final_review_batch_id":None}
        if reference_source_job_id:
            payload["reference_source_job_id"]=reference_source_job_id
    probe=probe_video(upload_path)
    duration=float(probe.get("duration_seconds") or 0)
    if duration<=0:
        raise ValueError("업로드 영상 길이를 확인할 수 없습니다.")
    if duration>MAX_ASSEMBLY_TOTAL_SECONDS+0.01:
        raise ValueError(f"업로드 영상은 최대 {int(MAX_ASSEMBLY_TOTAL_SECONDS)}초까지 가능합니다. 현재 {duration:.1f}초")
    width=int(probe.get("width") or DEFAULT_GENERATION_WIDTH);height=int(probe.get("height") or DEFAULT_GENERATION_HEIGHT)
    fps=int(round(float(probe.get("fps") or 24)))
    resolution={"width":width,"height":height}
    token=sanitize_token(name,fallback="manual")
    jid=f"{datetime.now():%Y%m%d_%H%M%S}_{token}_manual_{secrets.token_hex(2)}"
    directory=JOBS/jid;artifacts=directory/"artifacts";artifacts.mkdir(parents=True)
    output=artifacts/"assembled_master.mp4";shutil.copy2(upload_path,output)
    created=now_iso()
    settings=load_automation_settings(ROOT)
    final_settings=dict(settings);final_settings.update(auto_review=False,auto_modify=False,auto_recheck=False,max_modify_cycles=0)
    batch=create_new_open_batch(ROOT,final_settings);batch_id=str(batch["batch_id"])
    req={"schema_version":2,"job_type":"assemble","pipeline_stage":"manual_import","job_id":jid,"batch_id":batch_id,
         "job_dir":str(directory),"created_at":created,"job_name":name,"composition_id":composition_id,
         "workflow_kind":"assemble","workflow_kind_label":"외부 편집본 업로드","manual_upload":True,
         "fps":fps,"resolution":resolution,"total_duration_seconds":round(duration,3),
         "clips":payload.get("clips") or [],"reference_source_job_id":payload.get("reference_source_job_id"),
         "filename_prefix":f"video/assembled/{composition_id}/{token}","automation":final_settings,"attempt":0}
    summary={"duration_seconds":round(duration,3),"width":width,"height":height,"fps":fps,
             "source":"manual_upload","upload_path":str(upload_path)}
    man={key:req[key] for key in ("schema_version","job_id","batch_id","job_type","pipeline_stage","created_at",
         "composition_id","workflow_kind","workflow_kind_label","fps","resolution","total_duration_seconds")}
    man.update(status="completed",completed_at=created,updated_at=created,review_video_local_path=str(output),
               assembly_summary=summary,outputs=[{"filename":output.name,"subfolder":"","type":"local","local_path":str(output)}])
    atomic_write_json(directory/"request.json",req);atomic_write_json(directory/"manifest.json",man)
    update_status(directory,"completed",stage="외부 편집본 등록 완료",
                  message=f"{duration:.1f}초 · {width}×{height} · {fps}fps",progress=1.0,
                  created_at=created,started_at=created,completed_at=created)
    attach_job_to_batch(ROOT,batch_id,jid,"assemble")
    update_batch(ROOT,batch_id,batch_mode="clip_assembly",composition_ids=[composition_id],registration_closed=True,
                 registration_closed_at=created,stage="assemble_completed",next_stage="generation",
                 message="외부 편집본이 수동 등록되었습니다.")
    payload.update(status="assembled",assemble_job_id=jid,assembled_video_path=str(output),assembled_at=created,
                   assemble_batch_id=batch_id,assembly_source="manual_upload",fps=fps,resolution=resolution,
                   total_duration_seconds=round(duration,3),assembly_summary=summary,final_review_batch_id=None,last_error=None)
    save_composition(payload)
    return {"composition_id":composition_id,"assemble_job_id":jid,"batch_id":batch_id,
            "duration_seconds":round(duration,3),"resolution":resolution,"fps":fps}

FINAL_REVIEW_WAITING_BATCH_STATUSES={"completed_generation_only","ai_review_failed","engine_switch_failed",
    "review_complete_needs_modification","manual_review_required","modification_limit_reached"}
FINAL_REVIEW_ACTIVE_BATCH_STATUSES={"ready_for_review_preparation","ready_for_ai_review","switching_to_vllm","ai_reviewing"}

def _ensure_final_review_registration_allowed(batch: dict[str,Any]|None)->None:
    if not batch:return
    batch_status=str(batch.get("status") or "")
    if batch_status in FINAL_REVIEW_ACTIVE_BATCH_STATUSES:
        raise RuntimeError("이미 최종 AI 검수가 진행 중입니다.")
    if batch_status=="review_completed":
        raise RuntimeError("이미 통과한 최종 AI 검수가 있습니다.")

def _queue_final_review_batch(*,review_job_id:str,batch_link:dict[str,Any],message:str,existing_batch_id:str="")->dict[str,Any]:
    review=job(review_job_id)
    if str(review["status"].get("status") or "")!="completed":
        raise RuntimeError("검수 대상 영상 작업이 아직 완료되지 않았습니다.")
    queued_at=now_iso()
    if existing_batch_id:
        batch=load_batch(ROOT,existing_batch_id)
        if not batch:raise FileNotFoundError(f"배치를 찾을 수 없습니다: {existing_batch_id}")
        _ensure_final_review_registration_allowed(batch)
        batch_status=str(batch.get("status") or "")
        if batch_status not in FINAL_REVIEW_WAITING_BATCH_STATUSES:
            raise RuntimeError(f"최종 AI 검수를 등록할 수 없는 배치 상태입니다: {batch_status}")
        update_batch(ROOT,existing_batch_id,status="ready_for_review_preparation",stage="final_review_user_requested",
                     next_stage="video_review",review_job_ids=[review_job_id],generation_job_ids=[review_job_id],
                     job_ids=[review_job_id],message=message,ai_review_errors=[],engine_switch_error=None)
        return {"batch_id":existing_batch_id,"review_job_id":review_job_id,"status":"final_review_queued","queued_at":queued_at}
    settings=load_automation_settings(ROOT)
    final_settings=dict(settings);final_settings.update(auto_review=False,auto_modify=False,auto_recheck=False,max_modify_cycles=0)
    batch=create_new_open_batch(ROOT,final_settings);batch_id=str(batch["batch_id"])
    update_batch(ROOT,batch_id,batch_mode="final_review",registration_closed=True,registration_closed_at=queued_at,
                 status="ready_for_review_preparation",stage="final_review_user_requested",next_stage="video_review",
                 review_job_ids=[review_job_id],generation_job_ids=[review_job_id],job_ids=[review_job_id],
                 message=message,ai_review_errors=[],engine_switch_error=None,**batch_link)
    return {"batch_id":batch_id,"review_job_id":review_job_id,"status":"final_review_queued","queued_at":queued_at}

def register_candidate_final_review_action(data):
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    payload=load_candidate_set(candidate_set_id)
    selected_job_id=str(payload.get("selected_job_id") or "")
    if not selected_job_id:raise RuntimeError("후보를 먼저 선택하세요.")
    entity_status=str(payload.get("status") or "")
    if entity_status not in {"selected","final_review_failed","final_review_queued"}:
        raise RuntimeError("후보 선택 후 04 최종 마스터에서 AI 검수를 등록하세요.")
    result=_queue_final_review_batch(review_job_id=selected_job_id,batch_link={"candidate_set_ids":[candidate_set_id]},
                                     message="사용자가 04 최종 마스터에서 최종 AI 검수를 등록했습니다.",
                                     existing_batch_id=str(payload.get("final_review_batch_id") or ""))
    payload.update(status="final_review_queued",final_review_batch_id=result["batch_id"],
                   final_review_queued_at=result["queued_at"],last_error=None)
    save_candidate_set(payload)
    result["candidate_set_id"]=candidate_set_id
    return result

def register_composition_final_review_action(data):
    composition_id=str(data.get("composition_id") or "").strip()
    payload=load_composition(composition_id)
    assemble_job_id=str(payload.get("assemble_job_id") or "")
    if not assemble_job_id:raise RuntimeError("합성 작업이 없습니다.")
    entity_status=str(payload.get("status") or "")
    if entity_status not in {"assembled","final_review_failed","final_review_queued"}:
        raise RuntimeError("합성 완료 후 04 최종 마스터에서 AI 검수를 등록하세요.")
    result=_queue_final_review_batch(review_job_id=assemble_job_id,batch_link={"composition_ids":[composition_id]},
                                     message="사용자가 04 최종 마스터에서 합성본 AI 검수를 등록하세요.",
                                     existing_batch_id=str(payload.get("final_review_batch_id") or ""))
    payload.update(status="final_review_queued",final_review_batch_id=result["batch_id"],
                   final_review_queued_at=result["queued_at"],last_error=None)
    save_composition(payload)
    result["composition_id"]=composition_id
    return result

def delete_composition_action(data):
    composition_id=str(data.get("composition_id") or "").strip()
    payload=load_composition(composition_id)
    if payload.get("status") in {"assembling"}:
        raise RuntimeError("실행 중인 합성 프로젝트는 삭제할 수 없습니다.")
    for key in ("assemble_job_id",):
        job_id=str(payload.get(key) or "")
        if not job_id:continue
        try:
            item=job(job_id)
        except FileNotFoundError:
            continue
        if str(item["status"].get("status") or "") not in JOB_TERMINAL_STATUSES|{"queued"}:
            raise RuntimeError(f"연결된 작업이 실행 중이라 삭제할 수 없습니다: {job_id}")
    directory=composition_path(composition_id).parent
    if directory.is_dir():shutil.rmtree(directory)
    return {"composition_id":composition_id,"deleted":True}

def next_cycle(root_id):
    high=0
    for d in JOBS.iterdir():
        if d.is_dir():
            r=read_json(d/"request.json",{}) or {}
            if str(r.get("root_job_id") or "")==root_id:high=max(high,int(r.get("modify_cycle") or 0))
    return high+1

def manual_action(data):
    source=job(str(data["source_job_id"])); root=root_for(source); generated=prompt_action(data); mode=generated["correction_mode"]; total=generated["duration_seconds"]
    template=MD if mode=="partial_retake" else Path(str(root["request"].get("workflow_source_path") or root["request"].get("template_path"))).expanduser()
    if not template.is_file():raise FileNotFoundError(f"수정 워크플로가 없습니다: {template}")
    if mode=="partial_retake":
        uploaded=Path(str(data.get("upload_path") or ""));
        if not uploaded.is_file() or uploaded.suffix.lower() not in VIDEO_SUFFIXES:raise ValueError("부분 수정 기준 영상을 업로드하세요.")
    settings=load_automation_settings(ROOT);batch=get_or_create_open_batch(ROOT,settings);root_id=root["job_id"];cycle=next_cycle(root_id);token="manual_retake" if mode=="partial_retake" else "manual_regenerate";jid=f"{root_id}__{token}_c{cycle}_{secrets.token_hex(2)}";d=JOBS/jid;d.mkdir(parents=True);snap=d/"selected_workflow_api.json";shutil.copy2(template,snap)
    correction=generated["prompt"];block="MANDATORY RETAKE SPECIFICATION:\n"+correction;segments=[]
    for src in root["request"].get("segments") or []:
        x=dict(src);base=str(x.get("prompt") or "").strip();x["prompt"]=base+"\n\n"+block if base else block;segments.append(x)
    base=str(root["request"].get("global_prompt") or "").strip();created=now_iso();seed=secrets.randbelow((1<<63)-1);parent=source["job_id"]
    manual_name=f"{root['request'].get('job_name') or root_id} manual {cycle}"
    req=dict(root["request"]); req.update({"job_type":"modify","pipeline_stage":"retake_generation" if mode=="partial_retake" else "full_regeneration","correction_mode":mode,"manual_correction":True,"job_id":jid,"batch_id":batch["batch_id"],"job_dir":str(d),"created_at":created,"job_name":manual_name,"template_path":str(snap),"workflow_source_path":str(template),"workflow_filename":template.name,"workflow_kind":"modify","workflow_kind_label":"사용자 재수정 (부분 구간)" if mode=="partial_retake" else "사용자 재수정 (전체 재생성)","seed":seed,"global_prompt":base+"\n\n"+block,"filename_prefix":f"video/manual_retakes/{root_id}/cycle_{cycle}" if mode=="partial_retake" else f"video/manual_regenerations/{root_id}/cycle_{cycle}","segments":segments,"parent_job_id":parent,"root_job_id":root_id,"modify_cycle":cycle,"attempt":cycle,"automation":dict(batch.get("automation") or settings),"retake_corrections":correction,"generated_retake_prompt":correction,"retake_prompt_source":"ai_review_report_plus_user_instruction","source_review_report":str(source["dir"]/"ai_review_report.json")})
    if mode=="partial_retake":
        art=d/"artifacts";art.mkdir();dest=art/("manual_source"+Path(str(data["upload_path"])).suffix.lower());shutil.copy2(data["upload_path"],dest);req.update(retake_source_video_path=str(dest),retake_source_duration_seconds=total,retake_start_seconds=generated["start_seconds"],retake_end_seconds=generated["end_seconds"],retake_strength=1.0,retake_primary_issue={"severity":"user","type":"manual_correction","start_seconds":generated["start_seconds"],"end_seconds":generated["end_seconds"],"evidence_ko":"사용자가 UI에서 지정한 재수정 구간"})
    man={k:req[k] for k in ("schema_version","job_id","batch_id","parent_job_id","root_job_id","job_type","pipeline_stage","correction_mode","manual_correction","modify_cycle","created_at","workflow_source_path","workflow_filename","workflow_kind","workflow_kind_label","seed","resolution","fps","segments","retake_corrections","generated_retake_prompt","retake_prompt_source","source_review_report")};man.update(status="queued",outputs=[])
    for k in ("retake_source_video_path","retake_source_duration_seconds","retake_start_seconds","retake_end_seconds","retake_strength","retake_primary_issue"):
        if k in req:man[k]=req[k]
    atomic_write_json(d/"request.json",req);atomic_write_json(d/"manifest.json",man);update_status(d,"queued",stage="사용자 재수정 worker 대기",message=req["workflow_kind_label"],progress=0,created_at=created);attach_job_to_batch(ROOT,batch["batch_id"],jid,"generate")
    return {"job_id":jid,"batch_id":batch["batch_id"],**generated}

def require_deletion_password(data):
    expected=str(os.environ.get("VIDEO_UI_ACCESS_KEY") or "")
    provided=str(data.get("deletion_password") or "")
    if not expected: raise PermissionError("삭제 비밀번호가 설정되지 않았습니다.")
    if not hmac.compare_digest(provided,expected): raise PermissionError("삭제 비밀번호가 일치하지 않습니다.")

def _safe_delete_file(base: Path, relative: Path, deleted: list[str]):
    root=base.resolve(); target=(root/relative).resolve()
    if target.is_file() and root in target.parents:
        target.unlink(); deleted.append(str(target)); parent=target.parent
        while parent!=root and root in parent.parents:
            try: parent.rmdir()
            except OSError: break
            parent=parent.parent

def _delete_job_external_files(item: dict[str, Any], deleted_files: list[str]) -> None:
    descriptors=list(item["manifest"].get("outputs") or [])+list(item["status"].get("outputs") or [])
    for descriptor in descriptors:
        _safe_delete_file(COMFY_OUTPUT,Path(str(descriptor.get("subfolder") or ""))/str(descriptor.get("filename") or ""),deleted_files)
    for upload in item["manifest"].get("uploads") or []:
        descriptor=upload.get("comfy_response") or {}
        _safe_delete_file(COMFY_INPUT,Path(str(descriptor.get("subfolder") or ""))/str(descriptor.get("name") or ""),deleted_files)
    descriptor=item["manifest"].get("retake_video_upload") or {}
    if descriptor:
        _safe_delete_file(COMFY_INPUT,Path(str(descriptor.get("subfolder") or ""))/str(descriptor.get("name") or ""),deleted_files)
    for key in ("review_video_local_path","comparison_source_video_path"):
        local_path=Path(str(item["manifest"].get(key) or ""))
        if local_path.is_file() and item["dir"].resolve() in local_path.parents:
            local_path.unlink()
            deleted_files.append(str(local_path))

def _remove_jobs_from_batch(batch_id: str, deleted_set: set[str], candidate_set_id: str | None = None) -> None:
    batch_dir=ROOT/"runtime/batches"/batch_id; batch_path=batch_dir/"batch.json"; batch=read_json(batch_path,{}) or {}
    if not batch: return
    for key in BATCH_JOB_LIST_FIELDS:
        if key in batch:
            batch[key]=[value for value in batch.get(key) or [] if str(value) not in deleted_set]
    if candidate_set_id and "candidate_set_ids" in batch:
        batch["candidate_set_ids"]=[value for value in batch.get("candidate_set_ids") or [] if str(value)!=candidate_set_id]
    if str(batch.get("selected_candidate_job_id") or "") in deleted_set:
        batch["selected_candidate_job_id"]=None
    for key in ("review_video_paths","ai_reviews"):
        if isinstance(batch.get(key),dict):
            batch[key]={k:v for k,v in batch[key].items() if k not in deleted_set}
    if not batch.get("job_ids"):
        if batch_dir.is_dir(): shutil.rmtree(batch_dir)
        clear_open_batch_pointer(ROOT,batch_id)
    else:
        atomic_write_json(batch_path,batch)

def delete_candidate_set_action(data):
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    if not candidate_set_id: raise ValueError("후보군 ID가 필요합니다.")
    payload=load_candidate_set(candidate_set_id)
    job_ids=[]
    for key in ("candidate_job_ids",):
        job_ids.extend(str(job_id) for job_id in payload.get(key) or [])
    job_ids=list(dict.fromkeys(job_ids))
    items=[]
    for job_id in job_ids:
        try: items.append(job(str(job_id)))
        except FileNotFoundError: continue
    deletable_statuses=JOB_TERMINAL_STATUSES|{"queued"}
    active=[item for item in items if str(item["status"].get("status") or "") not in deletable_statuses]
    if active:
        summary=", ".join(f"{item['job_id']} ({item['status'].get('status')})" for item in active[:3])
        raise RuntimeError(f"실행 중인 작업이 있어 후보군을 삭제할 수 없습니다: {summary}")
    batch_ids=set()
    if payload.get("batch_id"): batch_ids.add(str(payload["batch_id"]))
    for item in items:
        batch_id=str(item["request"].get("batch_id") or item["manifest"].get("batch_id") or "")
        if batch_id: batch_ids.add(batch_id)
    deleted_files=[]
    with queue_claim_lock(JOBS):
        for item in items:
            current=job(item["job_id"])
            status=str(current["status"].get("status") or "")
            if status not in deletable_statuses:
                raise RuntimeError(f"실행 중인 작업이 있어 후보군을 삭제할 수 없습니다: {current['job_id']} ({status})")
            _delete_job_external_files(current,deleted_files)
            shutil.rmtree(current["dir"])
    deleted_set=set(job_ids)
    for batch_id in batch_ids:
        _remove_jobs_from_batch(batch_id,deleted_set,candidate_set_id)
    candidate_dir=candidate_set_path(candidate_set_id).parent
    if candidate_dir.is_dir(): shutil.rmtree(candidate_dir)
    return {"candidate_set_id":candidate_set_id,"deleted_job_ids":job_ids,"deleted_file_count":len(deleted_files)}

def delete_lineage_action(data):
    root_id=str(data.get("root_job_id") or "").strip()
    if not root_id: raise ValueError("작업 ID가 필요합니다.")
    require_deletion_password(data)
    root=job(root_id); lineage=[]
    for directory in JOBS.iterdir():
        if not directory.is_dir(): continue
        request=read_json(directory/"request.json",{}) or {}; manifest=read_json(directory/"manifest.json",{}) or {}
        candidate=str(request.get("root_job_id") or manifest.get("root_job_id") or directory.name)
        if candidate==root_id: lineage.append(job(directory.name))
    if root_id not in {item["job_id"] for item in lineage}: lineage.append(root)
    batch_ids={str(item["request"].get("batch_id") or item["manifest"].get("batch_id") or "") for item in lineage}; batch_ids.discard("")
    for batch_id in batch_ids:
        batch=read_json(ROOT/"runtime/batches"/batch_id/"batch.json",{}) or {}; status=str(batch.get("status") or "")
        if batch and status not in DELETABLE_BATCH_STATUSES: raise RuntimeError(f"활성 배치는 삭제할 수 없습니다: {batch_id} ({status})")
    deleted_files=[]
    for item in lineage:
        _delete_job_external_files(item,deleted_files)
    deleted_ids=sorted({item["job_id"] for item in lineage}); deleted_set=set(deleted_ids)
    for item in lineage: shutil.rmtree(item["dir"])
    for batch_id in batch_ids:
        _remove_jobs_from_batch(batch_id,deleted_set)
    return {"root_job_id":root_id,"deleted_job_ids":deleted_ids,"deleted_file_count":len(deleted_files)}

BATCH_JOB_LIST_FIELDS=("job_ids","generation_job_ids","candidate_job_ids","upscale_job_ids","assemble_job_ids","review_job_ids","check_job_ids","modify_job_ids","retake_job_ids","failed_generation_job_ids","failed_review_job_ids","failed_modify_job_ids","failed_check_job_ids")
JOB_TERMINAL_STATUSES={"completed","failed","cancelled"}
BATCH_TERMINAL_STATUSES=DELETABLE_BATCH_STATUSES|{"completed","done"}

def _detach_job_from_batch(batch_id: str, job_id: str):
    if not batch_id:return
    batch=load_batch(ROOT,batch_id)
    if not batch:return
    updates={}
    for key in BATCH_JOB_LIST_FIELDS:
        if key in batch:updates[key]=[value for value in batch.get(key) or [] if str(value)!=job_id]
    remaining=updates.get("job_ids",list(batch.get("job_ids") or []))
    if not remaining:
        updates.update(status="cancelled",stage="cancelled",next_stage="stopped",cancelled_at=now_iso(),message="등록된 대기 작업이 모두 삭제되어 배치를 취소했습니다.")
    else:
        updates["message"]=f"대기 작업 {job_id} 삭제 · 남은 작업 {len(remaining)}개"
    update_batch(ROOT,batch_id,**updates)
    if not remaining:clear_open_batch_pointer(ROOT,batch_id)

def delete_queued_job_action(data):
    job_id=str(data.get("job_id") or "").strip()
    require_deletion_password(data)
    with queue_claim_lock(JOBS):
        item=job(job_id)
        status=str(item["status"].get("status") or "")
        if status!="queued":raise RuntimeError(f"대기 중인 작업만 삭제할 수 있습니다: {job_id} ({status})")
        batch_id=str(item["request"].get("batch_id") or "")
        update_status(item["dir"],"cancelled",stage="사용자가 대기 작업 삭제",message="큐에 제출되기 전에 사용자가 삭제했습니다.",cancelled_at=now_iso())
        shutil.rmtree(item["dir"])
    _detach_job_from_batch(batch_id,job_id)
    return {"job_id":job_id,"batch_id":batch_id,"deleted":True}

def _run_control(command: list[str],timeout: float=75.0):
    if str(os.environ.get("VIDEO_CONTROL_DRY_RUN") or "").lower() in {"1","true","yes"}:return
    subprocess.run(command,check=True,timeout=timeout,capture_output=True,text=True)

def force_cancel_batch_action(data):
    batch_id=str(data.get("batch_id") or "").strip()
    if not batch_id or Path(batch_id).name!=batch_id or batch_id in {".",".."}:raise ValueError("허용되지 않는 배치 ID입니다.")
    require_deletion_password(data)
    batch=load_batch(ROOT,batch_id)
    if not batch:raise FileNotFoundError(f"배치를 찾을 수 없습니다: {batch_id}")
    batch_status=str(batch.get("status") or "")
    if batch_status in BATCH_TERMINAL_STATUSES:raise RuntimeError(f"이미 종료된 배치입니다: {batch_id} ({batch_status})")
    control_errors=[];worker_stopped=False;cancelled_ids=[]
    with queue_claim_lock(JOBS):
        items=[]
        for job_id in batch.get("job_ids") or []:
            try:items.append(job(str(job_id)))
            except FileNotFoundError:continue
        active=[item for item in items if str(item["status"].get("status") or "") not in JOB_TERMINAL_STATUSES|{"queued"}]
        must_stop_pipeline=bool(active) or batch_status!="open"
        if must_stop_pipeline:
            try:
                _run_control(["systemctl","--user","stop","ltx-video-worker.service"],40);worker_stopped=True
            except Exception as exc:
                raise RuntimeError(f"Worker를 중지하지 못해 배치를 종료하지 않았습니다: {type(exc).__name__}: {exc}") from exc
            for command in ([str(HOME/"bin/ai-stop-comfy")],[str(HOME/"bin/ai-stop-vllm")]):
                try:_run_control(command)
                except Exception as exc:control_errors.append(f"{Path(command[0]).name}: {type(exc).__name__}: {exc}")
        for item in items:
            current=job(item["job_id"])
            status=str(current["status"].get("status") or "")
            if status in JOB_TERMINAL_STATUSES:continue
            cancelled_ids.append(current["job_id"])
            stamp=now_iso()
            update_status(current["dir"],"cancelled",stage="사용자가 배치 강제 종료",message=f"배치 {batch_id} 강제 종료로 취소했습니다.",cancelled_at=stamp,progress=0.0)
            manifest=current["manifest"];manifest.update(status="cancelled",cancelled_at=stamp,updated_at=stamp);atomic_write_json(current["dir"]/"manifest.json",manifest)
    update_batch(ROOT,batch_id,status="cancelled",stage="cancelled",next_stage="stopped",cancelled_at=now_iso(),forced_cancel=True,cancelled_job_ids=cancelled_ids,message=f"사용자가 배치를 강제 종료했습니다. 취소 작업 {len(cancelled_ids)}개")
    clear_open_batch_pointer(ROOT,batch_id)
    worker_restarted=False
    if worker_stopped and not control_errors:
        try:_run_control(["systemctl","--user","start","ltx-video-worker.service"],30);worker_restarted=True
        except Exception as exc:control_errors.append(f"worker restart: {type(exc).__name__}: {exc}")
    return {"batch_id":batch_id,"status":"cancelled","cancelled_job_ids":cancelled_ids,"worker_restarted":worker_restarted,"warnings":control_errors}

def delete_batch_history_action(data):
    batch_id=str(data.get("batch_id") or "").strip()
    if not batch_id or Path(batch_id).name!=batch_id or batch_id in {".",".."}: raise ValueError("허용되지 않는 배치 ID입니다.")
    require_deletion_password(data)
    batch_dir=ROOT/"runtime/batches"/batch_id; batch_path=batch_dir/"batch.json"; batch=read_json(batch_path,{}) or {}
    if not batch: raise FileNotFoundError(f"배치 이력을 찾을 수 없습니다: {batch_id}")
    status=str(batch.get("status") or "")
    if status not in DELETABLE_BATCH_STATUSES: raise RuntimeError(f"진행 중인 배치 이력은 삭제할 수 없습니다: {batch_id} ({status})")
    shutil.rmtree(batch_dir)
    pointer=ROOT/"runtime/open_batch.json"; current=read_json(pointer,{}) or {}
    if current.get("batch_id")==batch_id: pointer.unlink(missing_ok=True)
    return {"batch_id":batch_id,"deleted":True}

def main():
    action=sys.argv[1]; data=json.load(sys.stdin)
    out={"prompt":prompt_action,"create":create_action,"create_candidates":create_candidates_action,"select_candidate":select_candidate_action,"manual":manual_action,"clip_library":clip_library_action,"list_compositions":list_compositions_action,"create_composition":create_composition_action,"update_composition":update_composition_action,"assemble_composition":assemble_composition_action,"import_composition_video":import_composition_video_action,"register_candidate_final_review":register_candidate_final_review_action,"register_composition_final_review":register_composition_final_review_action,"delete_composition":delete_composition_action,"delete_candidate_set":delete_candidate_set_action,"delete_lineage":delete_lineage_action,"delete_queued_job":delete_queued_job_action,"force_cancel_batch":force_cancel_batch_action,"delete_batch_history":delete_batch_history_action,"settings":lambda d:save_automation_settings(ROOT,d)}[action](data)
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__":main()
