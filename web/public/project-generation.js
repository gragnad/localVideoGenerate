/* Project-wide generation shares the existing scene settings, never the manual prompt form. */
(() => {
  const q=id=>document.getElementById(id);
  const sceneControls=q('queueH3SceneCandidates')?.closest('.h3-scene-candidate-controls');
  if(!sceneControls)return;
  const panel=document.createElement('section');
  panel.id='h3ProjectCandidateControls';panel.className='h3-project-candidate-controls';
  panel.setAttribute('aria-label','선택 프로젝트 전체 후보 생성');
  panel.innerHTML='<div><b>선택한 프로젝트 전체 클립 생성</b><small>위의 씬 생성 워크플로우·해상도·클립당 후보 설정을 공유합니다. 씬 선택 없이 프로젝트 전체를 등록합니다.</small><small id="h3ProjectCandidateMeta" role="status">프로젝트를 먼저 선택하세요.</small></div><button type="button" id="queueH3ProjectCandidates" class="primary alt" disabled>Windows PC에서 프로젝트 전체 후보 생성</button><button type="button" id="queueH3ProjectCandidatesLocal" class="primary" disabled>로컬 프로젝트 전체 후보 생성</button>';
  sceneControls.after(panel);
  let pending=false;
  const buttons=[q('queueH3ProjectCandidates'),q('queueH3ProjectCandidatesLocal')];
  function selection(){
    const project=q('h3Project')?.value || '',scenes=h3ProjectScenes || [];
    const clips=scenes.flatMap(scene=>scene.clips || []),ready=clips.filter(clip=>clip.ready).length;
    return {project,scenes,clips,ready,adapter:q('h3SceneAdapter')?.value || '',
      count:Number(q('h3SceneCandidateCount')?.value || 3),resolution:q('h3SceneResolution')?.value || '608x352'};
  }
  function sync(){
    const s=selection(),available=Boolean(s.project&&s.clips.length&&s.ready===s.clips.length&&s.adapter);
    q('h3ProjectCandidateMeta').textContent=s.project
      ? s.project+' · '+s.scenes.length+'씬 · 준비 '+s.ready+'/'+s.clips.length+'클립 · 총 '+s.clips.length*s.count+'개 작업 · '+s.resolution.replace('x',' × ')
      : '프로젝트를 먼저 선택하세요.';
    buttons.forEach(button=>button.disabled=pending||!available);
  }
  const sceneSync=syncH3SceneCandidateControls;
  syncH3SceneCandidateControls=function(...args){const out=sceneSync(...args);sync();return out;};
  for(const id of ['h3SceneAdapter','h3SceneResolution','h3SceneCandidateCount'])q(id).addEventListener('change',sync);
  async function enqueue(lane){
    if(pending)return;
    const s=selection();
    if(!s.project||!s.adapter||!s.clips.length||s.ready!==s.clips.length)return;
    const [width,height]=s.resolution.split('x').map(Number),local=lane==='local_generation';
    const target=local?'로컬 ComfyUI':'Windows ComfyUI';
    if(!confirm(s.project+'\n프로젝트 전체 '+s.scenes.length+'개 씬 · '+s.clips.length+'개 클립 × 후보 '+s.count+'개 = 총 '+s.clips.length*s.count+'개 작업을 '+width+' × '+height+'로 '+target+'에 등록할까요?'))return;
    pending=true;sync();
    try{
      const out=await api('/api/h3/projects/candidate-sets',{method:'POST',headers:{'content-type':'application/json'},
        body:JSON.stringify({project_id:s.project,adapter_id:s.adapter,generation_mode:'r2v',candidate_count:s.count,width,height,seed:-1,queue_lane:lane})});
      await refreshH3State();
      note(target+' 프로젝트 전체 후보 등록 완료: '+out.scene_count+'씬 · '+out.clip_count+'클립 · 작업 '+out.job_count+'개');
    }catch(error){note(error.message,true);}
    finally{pending=false;sync();}
  }
  buttons[0].onclick=()=>enqueue('windows_candidate');buttons[1].onclick=()=>enqueue('local_generation');
  sync();
})();
