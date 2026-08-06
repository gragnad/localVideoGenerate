from __future__ import annotations

import copy, hashlib, hmac, json, os, secrets, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
from typing import Any

import candidate_set_status
import candidate_reviews
import correction_policy
import director_prompt_projects
import director_prompt_overview
import director_prompt_uploads
from comfy_workflow_export import graph_to_api
from batch_manager import attach_job_to_batch, clear_open_batch_pointer, create_new_open_batch, find_batches_by_status, get_or_create_open_batch, load_batch, load_automation_settings, save_automation_settings, update_batch
from job_queue import atomic_write_json, now_iso, queue_claim_lock, read_json, update_status
from video_assembler import VideoAssemblerError, assemble_clips, probe_video
import msr_prompt_projects
import msr_sequence_v2
import model_test_registry
import model_test_assets
import model_test_reviews
import model_test_analysis
import model_test_exports
import benchmark_jobs
import workflow_adapter
import seed_library
from workflow_builder import KOREAN_SPEECH_POLICY, resolve_seed, sanitize_token

HOME=Path.home()
ROOT=Path(os.environ.get("VIDEO_ENGINE_ROOT", HOME/"local-ai/video-engine"))
JOBS=ROOT/"jobs"
WF_DIR=Path(os.environ.get("COMFY_WORKFLOW_DIR", HOME/"ai-workspace/apps/ComfyUI/user/default/workflows")).expanduser()
CR=WF_DIR/"(CR)LTX_Director_2_API.json"
MD=WF_DIR/"(MD)LTX_Retake_Partial_API.json"
MSR_GRAPH=WF_DIR/"LTX-2.3_MSR_sample_workflow_V2+multiGuide.json"
VIDEO_SUFFIXES={".mp4",".webm",".mov",".mkv",".avi"}
COMFY_ROOT=Path(os.environ.get("COMFY_ROOT", HOME/"ai-workspace/apps/ComfyUI")).expanduser()
COMFY_OUTPUT=Path(os.environ.get("COMFY_OUTPUT_DIR", COMFY_ROOT/"output")).expanduser()
COMFY_INPUT=Path(os.environ.get("COMFY_INPUT_DIR", COMFY_ROOT/"input")).expanduser()
DELETABLE_BATCH_STATUSES={"completed_generation_only","review_completed","manual_review_required","modification_limit_reached","review_complete_needs_modification","ai_review_failed","failed","cancelled","pipeline_failed","awaiting_candidate_selection","candidate_selected","benchmark_completed","benchmark_completed_with_failures"}
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

def _is_candidate_generation_job(item: dict[str,Any]|None)->bool:
    if not item:
        return False
    request=item.get("request") or {}
    if str(request.get("job_type") or "generate")!="generate":
        return False
    if not request.get("candidate_set_id"):
        return False
    try:
        index=int(request.get("candidate_index") or 0)
    except (TypeError,ValueError):
        return False
    return index>0

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

def resolve_video_seed(data: dict[str,Any])->tuple[int,int,str]:
    raw=int(data.get("seed_input", data.get("seed", -1)))
    explicit=int(data.get("seed", raw))
    if explicit>=0:
        return explicit, raw, "fixed" if raw>=0 else "fixed_override"
    return resolve_seed(-1), raw, "random"

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
    seed,raw_seed,seed_mode=resolve_video_seed(data); created=now_iso(); width=int(data.get("width") or DEFAULT_GENERATION_WIDTH); height=int(data.get("height") or DEFAULT_GENERATION_HEIGHT)
    req={"schema_version":2,"job_type":"generate","pipeline_stage":"initial_generation","job_id":jid,"batch_id":batch_id,"job_dir":str(d),"created_at":created,"job_name":name,"template_path":str(snap),"workflow_source_path":str(template),"workflow_filename":template.name,"workflow_kind":"create","workflow_kind_label":"생성 (CR)","comfy_url":os.environ.get("COMFY_URL","http://127.0.0.1:8188"),"comfy_public_url":os.environ.get("COMFY_PUBLIC_URL",""),"comfy_start_script":os.environ.get("COMFY_START_SCRIPT",str(HOME/"bin/ai-start-comfy")),"comfy_start_timeout":float(os.environ.get("COMFY_START_TIMEOUT","180")),"auto_start_comfy":True,"fps":int(data.get("fps") or 24),"seed":seed,"seed_input":raw_seed,"seed_mode":seed_mode,"resolution":{"width":width,"height":height,"label":f"{width} × {height}"},"global_prompt":str(data.get("global_prompt") or DEFAULT_GLOBAL).strip(),"duration_mode":str(data.get("duration_mode") or "각 구간 시간의 합계"),"target_total_seconds":data.get("target_total_seconds"),"filename_prefix":f"video/jobs/{jid}/{token}","segments":segments,"parent_job_id":None,"attempt":0,"automation":dict(batch.get("automation") or settings)}
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

def _msr_api_template(reference_count_or_slots: int | list[int] | set[int])->dict[str,Any]:
    if not MSR_GRAPH.is_file():
        raise FileNotFoundError(f"MSR V2 샘플 워크플로를 찾을 수 없습니다: {MSR_GRAPH}")
    if isinstance(reference_count_or_slots,int):
        slots=set(range(1,reference_count_or_slots+1))
    else:
        slots={int(value) for value in reference_count_or_slots}
    graph=json.loads(MSR_GRAPH.read_text(encoding="utf-8"))
    for node in graph.get("nodes") or []:
        if int(node.get("id") or 0)==196:node["mode"]=0 if 3 in slots else 4
        elif int(node.get("id") or 0)==201:node["mode"]=0 if 4 in slots else 4
    return graph_to_api(graph)


def create_msr_action(data, target_batch_id: str):
    references=[row for row in data.get("references") or [] if row.get("upload_path") or row.get("source_path")]
    if not 1<=len(references)<=4:raise ValueError("MSR V2 참조 이미지는 1~4장이어야 합니다.")
    background=dict(data.get("background") or {})
    if not background.get("upload_path") and not background.get("source_path"):raise ValueError("MSR V2 배경 이미지를 선택하세요.")
    relay_segments=[dict(row) for row in data.get("relay_segments") or []]
    if not relay_segments or any(not str(row.get("prompt") or "").strip() for row in relay_segments):
        raise ValueError("프롬프트 릴레이 구간을 한 개 이상 입력하세요.")
    if any(float(row.get("seconds") or 0)<=0 for row in relay_segments):raise ValueError("릴레이 구간 시간은 0초보다 커야 합니다.")
    batch=load_batch(ROOT,target_batch_id)
    if not batch or batch.get("status")!="open" or bool(batch.get("registration_closed")):
        raise RuntimeError(f"후보 작업을 등록할 수 없는 배치입니다: {target_batch_id}")
    name=str(data.get("job_name") or "MSR_v2_scene");token=sanitize_token(name,fallback="MSR_v2_scene")
    jid=f"{datetime.now():%Y%m%d_%H%M%S}_{token}_{secrets.token_hex(2)}";d=JOBS/jid;src=d/"source_images";src.mkdir(parents=True)
    copied=[]
    for index,(role,row) in enumerate([(f"subject_{i}",row) for i,row in enumerate(references,1)]+[("background",background)],1):
        incoming=msr_prompt_projects.resolve_msr_upload_path(ROOT,row);raw=incoming.read_bytes();stored=safe_name(str(row.get("original_name") or incoming.name),raw,index);dest=src/stored;shutil.copy2(incoming,dest)
        copied.append({"role":role,"original_name":str(row.get("original_name") or incoming.name),"stored_name":stored,"source_path":str(dest),"sha256":hashlib.sha256(raw).hexdigest(),"description":str(row.get("description") or "").strip(),"prompt":str(row.get("description") or role),"seconds":0,"order":index})
    snap=d/"selected_workflow_api.json";atomic_write_json(snap,_msr_api_template(len(references)))
    seed,raw_seed,seed_mode=resolve_video_seed(data);created=now_iso();width=int(data.get("width") or 1280);height=int(data.get("height") or 704)
    req={"schema_version":2,"job_type":"generate","pipeline_stage":"initial_generation","job_id":jid,"batch_id":target_batch_id,"job_dir":str(d),"created_at":created,"job_name":name,"template_path":str(snap),"workflow_source_path":str(MSR_GRAPH),"workflow_filename":MSR_GRAPH.name,"workflow_kind":"msr_v2","workflow_kind_label":"후보 생성 (MSR V2)","reference_mode":"up_to_four_subjects_plus_background","comfy_url":os.environ.get("COMFY_URL","http://127.0.0.1:8188"),"comfy_public_url":os.environ.get("COMFY_PUBLIC_URL",""),"comfy_start_script":os.environ.get("COMFY_START_SCRIPT",str(HOME/"bin/ai-start-comfy")),"comfy_start_timeout":float(os.environ.get("COMFY_START_TIMEOUT","180")),"auto_start_comfy":True,"fps":24,"seed":seed,"seed_input":raw_seed,"seed_mode":seed_mode,"resolution":{"width":width,"height":height,"label":f"{width} × {height}"},"global_prompt":str(data.get("global_prompt") or DEFAULT_GLOBAL).strip(),"filename_prefix":f"video/jobs/{jid}/{token}","segments":copied,"msr_references":[row for row in copied if row["role"]!="background"],"msr_background":next(row for row in copied if row["role"]=="background"),"relay_segments":relay_segments,"relay_epsilon":float(data.get("epsilon") or 0.0011),"msr_reference_frame_count":65,"parent_job_id":None,"attempt":0,"automation":dict(batch.get("automation") or load_automation_settings(ROOT)),"candidate_set_id":str(data["candidate_set_id"]),"candidate_index":int(data["candidate_index"]),"candidate_count":int(data["candidate_count"]),"review_policy":"user_candidate_selection"}
    man={k:req[k] for k in ("schema_version","job_id","batch_id","job_type","pipeline_stage","created_at","workflow_source_path","workflow_filename","workflow_kind","workflow_kind_label","seed","resolution","fps","segments","reference_mode","candidate_set_id","candidate_index","candidate_count","review_policy")};man.update(status="queued",outputs=[])
    atomic_write_json(d/"request.json",req);atomic_write_json(d/"manifest.json",man);attach_job_to_batch(ROOT,target_batch_id,jid,"candidate");update_status(d,"queued",stage="MSR V2 후보 생성 worker 대기",message="MSR V2 후보 작업이 큐에 등록되었습니다.",progress=0,created_at=created)
    return {"job_id":jid,"batch_id":target_batch_id}


def create_msr_candidates_action(data):
    count=int(data.get("candidate_count") or 3)
    if count<2 or count>8:raise ValueError("후보 개수는 2~8개여야 합니다.")
    prompt_project_id=str(data.get("prompt_project_id") or "").strip()
    prompt_clip_id=str(data.get("prompt_clip_id") or "").strip()
    if prompt_project_id or prompt_clip_id:
        if not prompt_project_id or not prompt_clip_id:
            raise ValueError("prompt_project_id와 prompt_clip_id를 함께 지정해야 합니다.")
        prompt_clip=msr_prompt_projects.get_prompt_project_clip_action(
            ROOT,{"project_id":prompt_project_id,"clip_id":prompt_clip_id}
        )
        if not prompt_clip.get("can_register_msr"):
            reason=str(prompt_clip.get("registration_block_reason") or "프롬프트 검수가 완료되지 않았습니다.")
            raise ValueError(f"MSR 후보 등록이 차단되었습니다: {reason}")
    candidate_set_id=f"cset_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}";raw_seed=int(data.get("seed",-1));modulus=(1<<63)-1
    settings=load_automation_settings(ROOT);batch=create_new_open_batch(ROOT,settings);batch_id=str(batch["batch_id"]);created=now_iso();jobs=[]
    update_batch(ROOT,batch_id,candidate_set_ids=[candidate_set_id],batch_mode="candidate_selection",registration_closed=False,message=f"MSR V2 후보 영상 {count}개를 등록하고 있습니다.")
    for index in range(1,count+1):
        item=copy.deepcopy(data);candidate_seed=resolve_seed(-1) if raw_seed<0 else (raw_seed+index-1)%modulus
        item.update(candidate_set_id=candidate_set_id,candidate_index=index,candidate_count=count,seed=candidate_seed,seed_input=raw_seed)
        jobs.append(create_msr_action(item,batch_id))
    payload=save_candidate_set({"schema_version":1,"candidate_set_id":candidate_set_id,"generation_mode":"msr_v2","status":"generating","created_at":created,"batch_id":batch_id,"candidate_count":count,"candidate_job_ids":[item["job_id"] for item in jobs],"selected_job_id":None,"final_review_batch_id":None})
    update_batch(ROOT,batch_id,registration_closed=True,registration_closed_at=now_iso(),stage="candidate_jobs_queued",next_stage="generation",message=f"MSR V2 후보 영상 {count}개가 등록되었습니다. 앞선 배치 뒤에 실행됩니다.")
    return payload


def create_msr_sequence_action(data: dict[str,Any], target_batch_id: str):
    normalized=msr_sequence_v2.validate_submission(data)
    references=list(normalized["references"])
    anchor=dict(normalized["anchor"])
    batch=load_batch(ROOT,target_batch_id)
    if not batch or batch.get("status")!="open" or bool(batch.get("registration_closed")):
        raise RuntimeError(f"후보 작업을 등록할 수 없는 배치입니다: {target_batch_id}")
    name=str(normalized.get("job_name") or "MSR_sequence");token=sanitize_token(name,fallback="MSR_sequence")
    jid=f"{datetime.now():%Y%m%d_%H%M%S}_{token}_{secrets.token_hex(2)}";d=JOBS/jid;src=d/"source_images";src.mkdir(parents=True)
    copied=[]
    rows=[(str(row["role"]),row) for row in references]+[("anchor",anchor)]
    for index,(role,row) in enumerate(rows,1):
        incoming=msr_prompt_projects.resolve_msr_upload_path(ROOT,row);raw=incoming.read_bytes();stored=safe_name(str(row.get("original_name") or incoming.name),raw,index);dest=src/stored;shutil.copy2(incoming,dest)
        copied.append({"role":role,"slot":row.get("slot"),"reference_id":row.get("reference_id"),"original_name":str(row.get("original_name") or incoming.name),"stored_name":stored,"source_path":str(dest),"sha256":hashlib.sha256(raw).hexdigest(),"description":str(row.get("description") or "").strip(),"prompt":str(row.get("description") or role),"seconds":0,"order":index})
    slots=[int(row["slot"]) for row in references]
    snap=d/"selected_workflow_api.json";atomic_write_json(snap,_msr_api_template(slots))
    seed,raw_seed,seed_mode=resolve_video_seed(normalized);created=now_iso();width=int(normalized.get("width") or 1280);height=int(normalized.get("height") or 704)
    ref_rows=[row for row in copied if row["role"]!="anchor"];anchor_row=next(row for row in copied if row["role"]=="anchor")
    req={"schema_version":3,"workflow":"msr_sequence_v2","prompt_strategy":"msr_continuity_v1","director_prompt_inheritance":False,"job_type":"generate","pipeline_stage":"initial_generation","job_id":jid,"batch_id":target_batch_id,"job_dir":str(d),"created_at":created,"job_name":name,"template_path":str(snap),"workflow_source_path":str(MSR_GRAPH),"workflow_filename":MSR_GRAPH.name,"workflow_kind":"msr_sequence_v2","workflow_kind_label":"연속 구간 후보 생성 (MSR V2)","comfy_url":os.environ.get("COMFY_URL","http://127.0.0.1:8188"),"comfy_public_url":os.environ.get("COMFY_PUBLIC_URL",""),"comfy_start_script":os.environ.get("COMFY_START_SCRIPT",str(HOME/"bin/ai-start-comfy")),"comfy_start_timeout":float(os.environ.get("COMFY_START_TIMEOUT","180")),"auto_start_comfy":True,"fps":24,"seed":seed,"seed_input":raw_seed,"seed_mode":seed_mode,"resolution":{"width":width,"height":height,"label":f"{width} × {height}"},"world_prompt":normalized["world_prompt"],"global_prompt":normalized["global_prompt"],"reference_mode":normalized["reference_mode"],"review_intent_ko":normalized["review_intent_ko"],"filename_prefix":f"video/jobs/{jid}/{token}","segments":copied,"msr_references":ref_rows,"msr_anchor":anchor_row,"msr_background":anchor_row,"relay_segments":normalized["relay_segments"],"requested_seconds":normalized["requested_seconds"],"maximum_duration_seconds":20.0,"continuity_mode":normalized["continuity_mode"],"source_scene_refs":normalized["source_scene_refs"],"relay_epsilon":float(normalized.get("epsilon") or 0.0011),"msr_reference_frame_count":65,"parent_job_id":None,"attempt":0,"automation":dict(batch.get("automation") or load_automation_settings(ROOT)),"candidate_set_id":str(normalized["candidate_set_id"]),"candidate_index":int(normalized["candidate_index"]),"candidate_count":int(normalized["candidate_count"]),"review_policy":"user_candidate_selection"}
    man={k:req[k] for k in ("schema_version","workflow","prompt_strategy","director_prompt_inheritance","job_id","batch_id","job_type","pipeline_stage","created_at","workflow_source_path","workflow_filename","workflow_kind","workflow_kind_label","seed","resolution","fps","segments","candidate_set_id","candidate_index","candidate_count","review_policy")};man.update(status="queued",outputs=[])
    atomic_write_json(d/"request.json",req);atomic_write_json(d/"manifest.json",man);attach_job_to_batch(ROOT,target_batch_id,jid,"candidate");update_status(d,"queued",stage="MSR 연속 구간 후보 생성 worker 대기",message="새 MSR 연속 생성 후보가 큐에 등록되었습니다.",progress=0,created_at=created)
    return {"job_id":jid,"batch_id":target_batch_id}


def create_msr_sequence_candidates_action(data: dict[str,Any]):
    normalized=msr_sequence_v2.validate_submission(data)
    count=int(normalized.get("candidate_count") or 3)
    if count<2 or count>8:raise ValueError("후보 개수는 2~8개여야 합니다.")
    prompt_project_id=str(normalized.get("prompt_project_id") or "").strip();prompt_clip_id=str(normalized.get("prompt_clip_id") or "").strip()
    if prompt_project_id or prompt_clip_id:
        if not prompt_project_id or not prompt_clip_id:raise ValueError("prompt_project_id와 prompt_clip_id를 함께 지정해야 합니다.")
        prompt_clip=msr_prompt_projects.get_prompt_project_clip_action(ROOT,{"project_id":prompt_project_id,"clip_id":prompt_clip_id})
        machine=prompt_clip.get("machine_payload") or {}
        if machine.get("workflow")!="msr_sequence_v2" or machine.get("prompt_strategy")!="msr_continuity_v1":
            raise ValueError("기존 Director/MSR 프롬프트 프로젝트는 새 MSR 연속 생성에 사용할 수 없습니다.")
        if not prompt_clip.get("can_register_msr"):raise ValueError(f"MSR 후보 등록이 차단되었습니다: {prompt_clip.get('registration_block_reason') or '검수가 완료되지 않았습니다.'}")
        machine_reference_mode=str(machine.get("reference_mode") or "subject_references")
        if machine_reference_mode!=normalized["reference_mode"]:
            raise ValueError(f"프롬프트 프로젝트 참조 모드가 일치하지 않습니다: {machine_reference_mode}")
    candidate_set_id=f"cset_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}";raw_seed=int(normalized.get("seed",-1));modulus=(1<<63)-1
    settings=load_automation_settings(ROOT);batch=create_new_open_batch(ROOT,settings);batch_id=str(batch["batch_id"]);created=now_iso();jobs=[]
    update_batch(ROOT,batch_id,candidate_set_ids=[candidate_set_id],batch_mode="candidate_selection",registration_closed=False,message=f"새 MSR 연속 구간 후보 {count}개를 등록하고 있습니다.")
    for index in range(1,count+1):
        item=copy.deepcopy(normalized);candidate_seed=resolve_seed(-1) if raw_seed<0 else (raw_seed+index-1)%modulus
        item.update(candidate_set_id=candidate_set_id,candidate_index=index,candidate_count=count,seed=candidate_seed,seed_input=raw_seed)
        jobs.append(create_msr_sequence_action(item,batch_id))
    payload=save_candidate_set({"schema_version":2,"candidate_set_id":candidate_set_id,"generation_mode":"msr_sequence_v2","prompt_strategy":"msr_continuity_v1","status":"generating","created_at":created,"batch_id":batch_id,"candidate_count":count,"candidate_job_ids":[item["job_id"] for item in jobs],"selected_job_id":None,"final_review_batch_id":None})
    update_batch(ROOT,batch_id,registration_closed=True,registration_closed_at=now_iso(),stage="candidate_jobs_queued",next_stage="generation",message=f"새 MSR 연속 구간 후보 {count}개가 등록되었습니다. 앞선 배치 뒤에 실행됩니다.")
    return payload


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


def _candidate_review_context(data: dict[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    job_id=str(data.get("job_id") or "").strip()
    payload=load_candidate_set(candidate_set_id)
    if job_id not in {str(value) for value in payload.get("candidate_job_ids") or []}:
        raise ValueError("해당 후보군에 속하지 않는 작업입니다.")
    item=job(job_id)
    if not _is_candidate_generation_job(item):
        raise ValueError("후보 생성 작업만 문제 리뷰를 저장할 수 있습니다.")
    if str(item["request"].get("candidate_set_id") or "")!=candidate_set_id:
        raise ValueError("후보 작업의 후보군 정보가 일치하지 않습니다.")
    return payload,item


def _candidate_review_expected_default_ko(request: dict[str,Any])->str:
    direct=str(request.get("review_intent_ko") or "").strip()
    if direct:return direct
    clip_id=str(request.get("job_name") or "").strip()
    if clip_id and Path(clip_id).name==clip_id:
        source=str(request.get("source_scene_refs") or "").strip()
        matches=[]
        for path in (ROOT/"prompt_projects").rglob(f"{clip_id}.md"):
            try:
                payload=msr_prompt_projects.extract_machine_payload(path.read_text(encoding="utf-8"))
            except (OSError,ValueError,msr_prompt_projects.PromptProjectError):
                continue
            translated=str(payload.get("review_intent_ko") or "").strip()
            if not translated:continue
            same_source=bool(source and str(payload.get("source_scene_refs") or "").strip()==source)
            matches.append((not same_source,str(path),translated))
        if matches:
            matches.sort()
            return matches[0][2]
    return candidate_reviews.expected_default_ko(request)


def get_candidate_review_action(data: dict[str,Any])->dict[str,Any]:
    payload,item=_candidate_review_context(data)
    review=candidate_reviews.load_review(ROOT,str(payload["candidate_set_id"]),str(item["job_id"]))
    return {
        "review":review,
        "expected_default_ko":_candidate_review_expected_default_ko(item["request"]),
    }


def save_candidate_review_action(data: dict[str,Any])->dict[str,Any]:
    payload,item=_candidate_review_context(data)
    review=candidate_reviews.save_review(
        ROOT,
        candidate_set_id=str(payload["candidate_set_id"]),
        job_id=str(item["job_id"]),
        candidate_index=int(item["request"].get("candidate_index") or 0) or None,
        request=item["request"],
        job_dir=item["dir"],
        data=data,
    )
    summaries=dict(payload.get("candidate_reviews") or {})
    summaries[item["job_id"]]=candidate_reviews.review_summary(review)
    payload["candidate_reviews"]=summaries
    save_candidate_set(payload)
    return {"review":review,"summary":summaries[item["job_id"]]}

def sync_candidate_sets_action(data):
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    payloads=candidate_set_status.reconcile_candidate_sets(
        ROOT,[candidate_set_id] if candidate_set_id else None
    )
    return {
        "synced_count":len(payloads),
        "statuses":{
            str(item["candidate_set_id"]):str(item["status"]) for item in payloads
        },
    }

def active_candidate_generation_batches()->list[dict[str,Any]]:
    return [
        batch for batch in find_batches_by_status(ROOT,{"open"},limit=1000)
        if batch.get("batch_mode")=="candidate_selection"
    ]

def create_candidates_action(data):
    count=int(data.get("candidate_count") or 3)
    if count<2 or count>8:raise ValueError("후보 개수는 2~8개여야 합니다.")
    candidate_set_id=f"cset_{datetime.now():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"
    raw_seed=int(data.get("seed",-1));modulus=(1<<63)-1
    explicit=data.get("candidate_seeds") or []
    if explicit and len(explicit)!=count:raise ValueError("candidate_seeds 개수가 후보 개수와 일치하지 않습니다.")
    settings=load_automation_settings(ROOT);batch=create_new_open_batch(ROOT,settings);batch_id=str(batch["batch_id"])
    created=now_iso();created_jobs=[]
    update_batch(ROOT,batch_id,candidate_set_ids=[candidate_set_id],
                 batch_mode="candidate_selection",registration_closed=False,
                 message=f"후보 영상 {count}개를 독립 배치에 등록하고 있습니다.")
    for index in range(1,count+1):
        candidate_data=dict(data)
        if explicit:
            candidate_seed=int(explicit[index-1])
        elif raw_seed<0:
            candidate_seed=resolve_seed(-1)
        else:
            candidate_seed=(raw_seed+index-1)%modulus
        candidate_data.update(candidate_set_id=candidate_set_id,candidate_index=index,candidate_count=count,
                              seed=candidate_seed,seed_input=raw_seed,seed_mode="random" if raw_seed<0 else "fixed")
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

def _candidate_generation_jobs_for_set(payload: dict[str,Any])->list[dict[str,Any]]:
    candidate_set_id=str(payload.get("candidate_set_id") or "")
    items=[]
    for job_id in payload.get("candidate_job_ids") or []:
        try:
            item=job(job_id)
        except FileNotFoundError:
            continue
        if _is_candidate_generation_job(item) and str(item["request"].get("candidate_set_id") or "")==candidate_set_id:
            items.append(item)
    return items

def _candidate_set_batch_ready(payload: dict[str,Any])->None:
    items=_candidate_generation_jobs_for_set(payload)
    if not items:
        return
    if any(str(item["status"].get("status") or "") not in JOB_TERMINAL_STATUSES for item in items):
        raise RuntimeError("모든 후보 생성이 끝난 뒤 선택할 수 있습니다.")

def _selected_job_ids_from_payload(payload: dict[str,Any])->list[str]:
    raw=payload.get("selected_job_ids")
    if isinstance(raw,list):
        ids=[str(item).strip() for item in raw if str(item).strip()]
        if ids:
            return ids
    primary=str(payload.get("selected_job_id") or "").strip()
    return [primary] if primary else []

def select_candidate_action(data):
    candidate_set_id=str(data.get("candidate_set_id") or "").strip()
    payload=load_candidate_set(candidate_set_id)
    _candidate_set_batch_ready(payload)
    items=_candidate_generation_jobs_for_set(payload)
    valid_ids={item["job_id"] for item in items}
    if not valid_ids:
        raise RuntimeError("선택 가능한 후보 작업이 없습니다.")
    raw_ids=data.get("job_ids")
    if isinstance(raw_ids,list) and raw_ids:
        selected_job_ids=[str(item).strip() for item in raw_ids if str(item).strip()]
    else:
        single=str(data.get("job_id") or "").strip()
        selected_job_ids=[single] if single else []
    deduped=[]
    for job_id in selected_job_ids:
        if job_id and job_id not in deduped:
            deduped.append(job_id)
    selected_job_ids=deduped
    if not selected_job_ids:
        raise ValueError("선택할 후보를 한 개 이상 지정하세요.")
    for selected_job_id in selected_job_ids:
        if selected_job_id not in valid_ids:
            raise ValueError("해당 후보군에 속하지 않는 작업입니다.")
    if payload.get("final_review_batch_id"):
        raise RuntimeError("검수가 등록된 후보군은 선택을 변경할 수 있습니다.")
    statuses={item["job_id"]:str(item["status"].get("status") or "") for item in items}
    for selected_job_id in selected_job_ids:
        if statuses.get(selected_job_id)!="completed":
            raise RuntimeError("완료된 후보만 선택할 수 있습니다.")
    primary_job_id=str(data.get("primary_job_id") or "").strip() or selected_job_ids[0]
    if primary_job_id not in selected_job_ids:
        raise ValueError("대표 후보는 선택 목록에 포함되어야 합니다.")
    selected_set=set(selected_job_ids)
    selected_item=job(primary_job_id)
    selected_at=now_iso()
    for item in items:
        selected=item["job_id"] in selected_set
        for filename in ("request.json","manifest.json"):
            path=item["dir"]/filename;record=read_json(path,{}) or {};record.update(candidate_selected=selected,selected_at=selected_at if selected else None);atomic_write_json(path,record)
    payload.update(status="selected",selected_job_id=primary_job_id,selected_job_ids=selected_job_ids,selected_at=selected_at)
    save_candidate_set(payload)
    seed_library.mark_selected_final(ROOT,primary_job_id,selected_item["request"],selected_item["dir"])
    count=len(selected_job_ids)
    summary=f"후보 {count}개 선택 · 대표 {primary_job_id}"
    update_batch(ROOT,str(payload["batch_id"]),status="candidate_selected",stage="user_candidate_selected",
                 next_stage="final_review",selected_candidate_job_id=primary_job_id,selected_candidate_job_ids=selected_job_ids,
                 message=f"{summary}. 04 최종 마스터에서 AI 검수를 등록하세요.")
    return load_candidate_set(candidate_set_id)

def source_video_path(item: dict[str,Any])->Path:
    direct=Path(str(item["manifest"].get("review_video_local_path") or ""))
    if direct.is_file():return direct
    descriptors=list(item["manifest"].get("outputs") or [])+list(item["status"].get("outputs") or [])
    for descriptor in descriptors:
        if Path(str(descriptor.get("filename") or "")).suffix.lower() not in VIDEO_SUFFIXES:continue
        candidate=(COMFY_OUTPUT/str(descriptor.get("subfolder") or "")/str(descriptor.get("filename") or "")).resolve()
        if candidate.is_file() and COMFY_OUTPUT.resolve() in candidate.parents:return candidate
    artifacts=item["dir"]/"artifacts"
    if artifacts.is_dir():
        for name in ("review_source_video.mp4","review_source_video.webm","review_source_video.mov","assembled_master.mp4"):
            path=artifacts/name
            if path.is_file():
                return path
        for path in sorted(artifacts.iterdir(), key=lambda x:x.name, reverse=True):
            if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
                return path
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
    if not _is_candidate_generation_job(item):raise ValueError("후보 생성 작업만 선택할 수 있습니다.")
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

IMAGE_SUFFIXES={".png",".jpg",".jpeg",".webp"}
PREVIEW_MAX_DIM_MIN=64
PREVIEW_MAX_DIM_MAX=2048

def resolve_job_source_image_path(job_id: str,index: int)->Path:
    item=job(job_id)
    root=root_for(item)
    segments=list(root["request"].get("segments") or [])
    if index<0 or index>=len(segments):
        raise IndexError(f"원본 이미지 index가 범위를 벗어났습니다: {index}")
    raw=segments[index]
    source_root=(root["dir"]/"source_images").resolve()
    image_path=Path(str(raw.get("source_path") or "")).resolve()
    try:image_path.relative_to(source_root)
    except ValueError as exc:
        raise PermissionError("허용되지 않는 원본 이미지 경로입니다.") from exc
    if image_path.suffix.lower() not in IMAGE_SUFFIXES or not image_path.is_file():
        raise FileNotFoundError(f"원본 이미지를 찾을 수 없습니다: {job_id} [{index}]")
    return image_path

def ensure_source_image_preview(job_id: str,index: int,max_dim: int)->Path:
    source=resolve_job_source_image_path(job_id,index)
    if max_dim<=0:
        return source
    bounded=max(PREVIEW_MAX_DIM_MIN,min(PREVIEW_MAX_DIM_MAX,int(max_dim)))
    item=job(job_id)
    cache_dir=item["dir"]/"artifacts"
    cache_dir.mkdir(parents=True,exist_ok=True)
    cache_path=cache_dir/f"source_preview_{index}_{bounded}.jpg"
    source_mtime=source.stat().st_mtime
    if cache_path.is_file() and cache_path.stat().st_size>0 and cache_path.stat().st_mtime>=source_mtime:
        return cache_path
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow가 설치되어 있지 않아 미리보기를 생성할 수 없습니다.") from exc
    with Image.open(source) as image:
        preview=image.convert("RGB")
        preview.thumbnail((bounded,bounded),Image.Resampling.LANCZOS)
        preview.save(cache_path,"JPEG",quality=85,optimize=True)
    return cache_path

def source_image_preview_action(data)->dict[str,Any]:
    job_id=str(data.get("job_id") or "").strip()
    index=int(data.get("index") or 0)
    max_dim=int(data.get("max") or 0)
    path=ensure_source_image_preview(job_id,index,max_dim)
    return {"path":str(path)}

def _safe_job_source_path(path: Path)->bool:
    try:path.resolve().relative_to(JOBS.resolve())
    except ValueError:return False
    return path.suffix.lower() in IMAGE_SUFFIXES

def _iter_source_image_refs():
    if not JOBS.is_dir():return
    for directory in sorted(JOBS.iterdir(),key=lambda x:x.name,reverse=True):
        if not directory.is_dir():continue
        request=read_json(directory/"request.json",{}) or {}
        for segment in request.get("segments") or []:
            sha=str(segment.get("sha256") or "").strip().lower()
            if len(sha)!=64:continue
            yield {"job_id":directory.name,"sha256":sha,"original_name":str(segment.get("original_name") or segment.get("stored_name") or "image.png"),
                   "source_path":Path(str(segment.get("source_path") or "")),"created_at":str(request.get("created_at") or "")}

def source_image_library_action(_data=None)->dict[str,Any]:
    entries: dict[str,dict[str,Any]]={}
    for ref in _iter_source_image_refs():
        path=ref["source_path"]
        if not path.is_file() or not _safe_job_source_path(path):continue
        sha=ref["sha256"]; size=path.stat().st_size
        if sha not in entries:
            entries[sha]={"sha256":sha,"original_name":ref["original_name"],"size_bytes":size,"ref_count":0,
                          "preview_url":f"/api/source-images/{sha}/file","latest_job_id":ref["job_id"],
                          "latest_created_at":ref["created_at"],"job_ids":[]}
        entry=entries[sha]; entry["ref_count"]+=1
        if ref["job_id"] not in entry["job_ids"]:entry["job_ids"].append(ref["job_id"])
        if ref["created_at"]>=entry.get("latest_created_at",""):
            entry.update(latest_job_id=ref["job_id"],latest_created_at=ref["created_at"],original_name=ref["original_name"],size_bytes=size)
    images=sorted(entries.values(),key=lambda x:(x.get("latest_created_at") or "",x["sha256"]),reverse=True)
    for item in images:item.pop("latest_created_at",None)
    return {"images":images}

def _canonical_source_image_path(sha256: str)->Path:
    digest=str(sha256 or "").strip().lower()
    if len(digest)!=64 or any(ch not in "0123456789abcdef" for ch in digest):raise ValueError("허용되지 않는 이미지 해시입니다.")
    for ref in _iter_source_image_refs():
        if ref["sha256"]!=digest:continue
        path=ref["source_path"]
        if path.is_file() and _safe_job_source_path(path):return path
    raise FileNotFoundError(f"저장된 이미지를 찾을 수 없습니다: {digest[:12]}…")

def source_image_file_action(data)->dict[str,Any]:
    return {"path":str(_canonical_source_image_path(str(data.get("sha256") or "")))}

def delete_source_image_action(data)->dict[str,Any]:
    digest=str(data.get("sha256") or "").strip().lower()
    if len(digest)!=64 or any(ch not in "0123456789abcdef" for ch in digest):raise ValueError("허용되지 않는 이미지 해시입니다.")
    deleted_paths:set[str]=set()
    for ref in _iter_source_image_refs():
        if ref["sha256"]!=digest:continue
        path=ref["source_path"]
        if not path.is_file() or not _safe_job_source_path(path):continue
        resolved=str(path.resolve())
        if resolved in deleted_paths:continue
        path.unlink(missing_ok=True); deleted_paths.add(resolved)
    if not deleted_paths:raise FileNotFoundError(f"삭제할 저장 이미지가 없습니다: {digest[:12]}…")
    return {"sha256":digest,"deleted_files":len(deleted_paths),"deleted":True}

def clip_library_action(_data=None)->dict[str,Any]:
    clips=[]
    if not JOBS.is_dir():return {"clips":[]}
    for directory in sorted(JOBS.iterdir(),key=lambda x:x.name,reverse=True):
        if not directory.is_dir():continue
        request=read_json(directory/"request.json",{}) or {}
        if not _is_candidate_generation_job({"request":request}):continue
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
        if str(item["request"].get("job_type") or "") == "model_benchmark":
            benchmark_jobs.record_result(ROOT, item["request"], status="cancelled")
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
            if str(current["request"].get("job_type") or "") == "model_benchmark":
                benchmark_jobs.record_result(ROOT, current["request"], status="cancelled")
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

def like_seed_action(data)->dict[str,Any]:
    job_id=str(data.get("job_id") or "").strip()
    item=job(job_id)
    if str(item["status"].get("status") or "")!="completed":
        raise RuntimeError("완료된 후보만 seed를 저장할 수 있습니다.")
    entry=seed_library.like_seed_entry(ROOT,job_id,item["request"],item["dir"])
    return {"entry":entry,"liked":True,"job_id":job_id}

def unlike_seed_action(data)->dict[str,Any]:
    job_id=str(data.get("job_id") or "").strip()
    result=seed_library.unlike_seed_entry(ROOT,job_id)
    result["liked"]=False
    return result

def list_seed_library_action(_data=None)->dict[str,Any]:
    return seed_library.list_seed_library(ROOT)

def recommend_seeds_action(data)->dict[str,Any]:
    limit=int(data.get("limit") or 5)
    return seed_library.recommend_seeds(ROOT,data,limit=max(1,min(limit,10)))

def delete_seed_library_action(data)->dict[str,Any]:
    return seed_library.delete_seed_entry(ROOT,str(data.get("entry_id") or ""))

def _is_msr_sequence_payload(payload: dict[str,Any])->bool:
    return payload.get("workflow")==msr_sequence_v2.WORKFLOW and payload.get("prompt_strategy")==msr_sequence_v2.PROMPT_STRATEGY and payload.get("director_prompt_inheritance") is False


def list_msr_sequence_projects_action(_data=None)->dict[str,Any]:
    projects=[]
    for project in msr_prompt_projects.list_prompt_projects_action(ROOT,_data).get("projects") or []:
        project_id=str(project.get("project_id") or "")
        clips=list_msr_sequence_project_clips_action({"project_id":project_id}).get("clips") or []
        if not clips:continue
        projects.append({**project,"clip_count":len(clips),"reviewed_count":sum(1 for item in clips if item.get("status")=="reviewed"),"needs_confirmation_count":sum(1 for item in clips if item.get("status")=="needs_confirmation"),"awaiting_background_count":sum(1 for item in clips if item.get("status")=="awaiting_background")})
    return {"projects":projects,"workflow":msr_sequence_v2.WORKFLOW,"prompt_strategy":msr_sequence_v2.PROMPT_STRATEGY}


def list_msr_sequence_project_clips_action(data)->dict[str,Any]:
    project_id=str(data.get("project_id") or "")
    compatible=[]
    for clip in msr_prompt_projects.list_prompt_project_clips_action(ROOT,data).get("clips") or []:
        try:detail=msr_prompt_projects.get_prompt_project_clip_action(ROOT,{"project_id":project_id,"clip_id":clip["clip_id"]})
        except Exception:continue
        if _is_msr_sequence_payload(detail.get("machine_payload") or {}):compatible.append(clip)
    return {"project_id":project_id,"clips":compatible,"workflow":msr_sequence_v2.WORKFLOW,"prompt_strategy":msr_sequence_v2.PROMPT_STRATEGY}


def get_msr_sequence_project_clip_action(data)->dict[str,Any]:
    detail=msr_prompt_projects.get_prompt_project_clip_action(ROOT,data)
    if not _is_msr_sequence_payload(detail.get("machine_payload") or {}):
        raise ValueError("기존 Director/MSR 프롬프트는 새 MSR 연속 생성에서 조회할 수 없습니다.")
    return detail


def list_msr_prompt_projects_action(_data=None)->dict[str,Any]:
    return msr_prompt_projects.list_prompt_projects_action(ROOT,_data)

def list_msr_prompt_project_clips_action(data)->dict[str,Any]:
    return msr_prompt_projects.list_prompt_project_clips_action(ROOT,data)

def get_msr_prompt_project_clip_action(data)->dict[str,Any]:
    return msr_prompt_projects.get_prompt_project_clip_action(ROOT,data)

def msr_prompt_asset_action(data)->dict[str,Any]:
    return msr_prompt_projects.resolve_prompt_asset_action(ROOT,data)

def list_director_prompt_projects_action(_data=None)->dict[str,Any]:
    return director_prompt_projects.list_projects_action(ROOT,_data)

def list_director_prompt_project_clips_action(data)->dict[str,Any]:
    return director_prompt_projects.list_clips_action(ROOT,data)

def get_director_prompt_project_overview_action(data)->dict[str,Any]:
    return director_prompt_overview.project_overview_action(ROOT,data)

def get_director_prompt_project_clip_action(data)->dict[str,Any]:
    return director_prompt_projects.get_clip_action(ROOT,data)

def director_prompt_asset_action(data)->dict[str,Any]:
    return director_prompt_projects.resolve_asset_action(ROOT,data)

def save_director_prompt_segment_image_action(data)->dict[str,Any]:
    return director_prompt_uploads.save_segment_image_action(ROOT,data)

def review_director_prompt_segment_image_action(data)->dict[str,Any]:
    return director_prompt_uploads.review_segment_image_action(ROOT,data)

def list_msr_prompt_backgrounds_action(data)->dict[str,Any]:
    return msr_prompt_projects.list_project_backgrounds_action(ROOT,data)

def save_msr_prompt_background_link_action(data)->dict[str,Any]:
    return msr_prompt_projects.save_background_link_action(ROOT,data)

def model_test_dashboard_action(_data=None):
    return model_test_registry.dashboard(ROOT, WF_DIR)

def register_test_model_action(data):
    return model_test_registry.register_model(ROOT, data)

def register_test_workflow_action(data):
    return model_test_registry.register_workflow(ROOT, WF_DIR, data)

def inspect_test_workflow_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.inspect_workflow(connection, str(data.get("workflow_profile_id") or ""))

def register_test_adapter_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.register_adapter(connection, data)

def create_model_test_session_action(data):
    return model_test_registry.create_session(ROOT, data)

def delete_model_test_session_action(data):
    return model_test_registry.delete_session(ROOT, str(data.get("session_id") or ""))

def save_model_test_asset_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.save_and_link(ROOT, connection, data)

def unlink_model_test_asset_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.unlink(connection, data)

def save_r2v_shared_asset_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.save_and_link_r2v_shared(ROOT, connection, data)

def unlink_r2v_shared_asset_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return model_test_assets.unlink_r2v_shared(connection, data)

def model_test_asset_file_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return {"path": str(model_test_assets.resolve_file(ROOT, connection, str(data.get("asset_id") or "")))}

def preflight_model_test_session_action(data):
    with model_test_registry.open_registry(ROOT) as connection:
        return workflow_adapter.preflight_session(connection, str(data.get("session_id") or ""))
def model_test_session_results_action(data):
    return model_test_reviews.session_results(ROOT, str(data.get("session_id") or ""))

def model_test_run_review_action(data):
    run_id = str(data.get("run_id") or "")
    if data.get("review") is None:
        return model_test_reviews.run_review(ROOT, run_id)
    return model_test_reviews.save_review(ROOT, run_id, dict(data.get("review") or {}))

def model_test_comparison_action(_data=None):
    return model_test_reviews.comparison(ROOT)
def model_test_analysis_action(data):
    return model_test_analysis.analyze(
        ROOT, str(data.get("model_id") or ""),
        str(data.get("workflow_profile_id") or "") or None,
    )

def save_model_test_policy_action(data):
    return model_test_analysis.save_policy(ROOT, data)

def set_model_test_policy_active_action(data):
    return model_test_analysis.set_policy_active(
        ROOT, str(data.get("policy_id") or ""), bool(data.get("active")),
    )

def create_model_test_followup_action(data):
    return model_test_registry.create_followup_session(ROOT, data)

def export_model_tests_action(data):
    return model_test_exports.create_export(ROOT, str(data.get("format") or "json"))



def queue_model_test_session_action(data):
    return benchmark_jobs.queue_session(ROOT, str(data.get("session_id") or ""))

def queue_model_test_ai_review_action(data):
    return benchmark_jobs.queue_ai_review(ROOT, str(data.get("session_id") or ""))

def cancel_model_test_ai_review_action(data):
    session_id = str(data.get("session_id") or "").strip()
    if not session_id:
        raise ValueError("테스트 세션 ID가 필요합니다.")
    with model_test_registry.open_registry(ROOT) as connection:
        row = connection.execute(
            "SELECT batch_id FROM test_session_batches WHERE session_id=?",
            (session_id,),
        ).fetchone()
    if not row:
        raise FileNotFoundError("연결된 모델 테스트 배치를 찾을 수 없습니다.")
    batch_id = str(row["batch_id"])
    batch = load_batch(ROOT, batch_id)
    if not batch:
        raise FileNotFoundError("연결된 모델 테스트 배치 이력을 찾을 수 없습니다.")
    active = {
        "ready_for_review_preparation", "preparing_video_review",
        "ready_for_ai_review", "switching_to_vllm", "ai_reviewing",
    }
    if str(batch.get("status") or "") not in active:
        return {"session_id": session_id, "batch_id": batch_id, "already_stopped": True}

    _run_control(["systemctl", "--user", "stop", "ltx-video-worker.service"], 40)
    stopped_at = now_iso()
    update_batch(
        ROOT, batch_id,
        status="benchmark_review_cancelled", stage="cancelled", next_stage="stopped",
        cancelled_at=stopped_at, review_cancelled=True,
        message="사용자가 구기준 Qwen 검수를 중단했습니다. 완료된 리뷰는 유지됩니다.",
    )
    benchmark_jobs.set_session_review_status(ROOT, [session_id], "review_cancelled")
    cancelled_count = 0
    for job_id in batch.get("review_job_ids") or []:
        job_dir = JOBS / str(job_id)
        status_payload = read_json(job_dir / "status.json", {}) or {}
        if str(status_payload.get("ai_review_batch_id") or batch_id) != batch_id:
            continue
        if str(status_payload.get("ai_review_status") or "") not in {
            "queued", "preparing", "reviewing",
        }:
            continue
        update_status(
            job_dir, str(status_payload.get("status") or "completed"),
            ai_review_status="cancelled", ai_review_batch_id=batch_id,
            ai_review_updated_at=stopped_at,
        )
        cancelled_count += 1
    warnings = []
    try:
        _run_control([str(HOME / "bin/ai-stop-vllm")])
    except Exception as exc:
        warnings.append(f"ai-stop-vllm: {type(exc).__name__}: {exc}")
    try:
        _run_control(["systemctl", "--user", "start", "ltx-video-worker.service"], 30)
    except Exception as exc:
        warnings.append(f"worker start: {type(exc).__name__}: {exc}")
    return {
        "session_id": session_id, "batch_id": batch_id,
        "status": "benchmark_review_cancelled",
        "cancelled_review_count": cancelled_count,
        "completed_reviews_preserved": True,
        "warnings": warnings,
    }

def main():
    action=sys.argv[1]; data=json.load(sys.stdin)
    director_actions={
        "list_director_prompt_projects":list_director_prompt_projects_action,
        "list_director_prompt_project_clips":list_director_prompt_project_clips_action,
        "get_director_prompt_project_overview":get_director_prompt_project_overview_action,
        "get_director_prompt_project_clip":get_director_prompt_project_clip_action,
        "director_prompt_asset":director_prompt_asset_action,
        "save_director_prompt_segment_image":save_director_prompt_segment_image_action,
        "review_director_prompt_segment_image":review_director_prompt_segment_image_action,
    }
    if action in director_actions:
        out=director_actions[action](data)
        print(json.dumps(out,ensure_ascii=False))
        return
    if action=="sync_candidate_sets":
        out=sync_candidate_sets_action(data)
        print(json.dumps(out,ensure_ascii=False))
        return
    out={"prompt":prompt_action,"create":create_action,"create_candidates":create_candidates_action,"create_msr_candidates":create_msr_candidates_action,"create_msr_sequence_candidates":create_msr_sequence_candidates_action,"select_candidate":select_candidate_action,"get_candidate_review":get_candidate_review_action,"save_candidate_review":save_candidate_review_action,"manual":manual_action,"clip_library":clip_library_action,"source_image_library":source_image_library_action,"source_image_file":source_image_file_action,"source_image_preview":source_image_preview_action,"delete_source_image":delete_source_image_action,"like_seed":like_seed_action,"unlike_seed":unlike_seed_action,"list_seed_library":list_seed_library_action,"recommend_seeds":recommend_seeds_action,"delete_seed_library":delete_seed_library_action,"list_compositions":list_compositions_action,"create_composition":create_composition_action,"update_composition":update_composition_action,"assemble_composition":assemble_composition_action,"import_composition_video":import_composition_video_action,"register_candidate_final_review":register_candidate_final_review_action,"register_composition_final_review":register_composition_final_review_action,"delete_composition":delete_composition_action,"delete_candidate_set":delete_candidate_set_action,"delete_lineage":delete_lineage_action,"delete_queued_job":delete_queued_job_action,"force_cancel_batch":force_cancel_batch_action,"delete_batch_history":delete_batch_history_action,"list_msr_sequence_projects":list_msr_sequence_projects_action,"list_msr_sequence_project_clips":list_msr_sequence_project_clips_action,"get_msr_sequence_project_clip":get_msr_sequence_project_clip_action,"list_msr_prompt_projects":list_msr_prompt_projects_action,"list_msr_prompt_project_clips":list_msr_prompt_project_clips_action,"get_msr_prompt_project_clip":get_msr_prompt_project_clip_action,"msr_prompt_asset":msr_prompt_asset_action,"list_msr_prompt_backgrounds":list_msr_prompt_backgrounds_action,"save_msr_prompt_background_link":save_msr_prompt_background_link_action,"model_test_dashboard":model_test_dashboard_action,"register_test_model":register_test_model_action,"register_test_workflow":register_test_workflow_action,"inspect_test_workflow":inspect_test_workflow_action,"register_test_adapter":register_test_adapter_action,"create_model_test_session":create_model_test_session_action,"delete_model_test_session":delete_model_test_session_action,"preflight_model_test_session":preflight_model_test_session_action,"queue_model_test_session":queue_model_test_session_action,"queue_model_test_ai_review":queue_model_test_ai_review_action,"cancel_model_test_ai_review":cancel_model_test_ai_review_action,"model_test_session_results":model_test_session_results_action,"model_test_run_review":model_test_run_review_action,"model_test_comparison":model_test_comparison_action,"model_test_analysis":model_test_analysis_action,"save_model_test_policy":save_model_test_policy_action,"set_model_test_policy_active":set_model_test_policy_active_action,"create_model_test_followup":create_model_test_followup_action,"export_model_tests":export_model_tests_action,"save_model_test_asset":save_model_test_asset_action,"unlink_model_test_asset":unlink_model_test_asset_action,"save_r2v_shared_asset":save_r2v_shared_asset_action,"unlink_r2v_shared_asset":unlink_r2v_shared_asset_action,"model_test_asset_file":model_test_asset_file_action,"settings":lambda d:save_automation_settings(ROOT,d)}[action](data)
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__":main()
