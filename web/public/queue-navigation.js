/* Queue links are navigation only: no submission, adoption, seed or prompt-input changes. */
(() => {
  const q=id=>document.getElementById(id);
  let revision=0, internalPageChange=false, resultFocus=null;
  const jobs=()=>h3State.jobs || [];
  const findJob=id=>jobs().find(job=>job.job_id===id);
  function destination(job){
    const r=job.request || {};
    if(r.render_purpose==='resolution_rerender' || r.job_type==='h3_video_upscale') return 'results';
    if(['h3_r2v_benchmark','h3_model_benchmark'].includes(r.job_type)) return 'tests';
    return r.source_project_id ? r.generation_mode==='i2v'?'i2v-create':'create' : 'record';
  }
  function label(job){return ({results:'결과 확인으로 이동',tests:'테스트 작업으로 이동',record:'작업 상세 보기'})[destination(job)] || '프로젝트·클립으로 이동';}
  function navigation(job){
    const r=job.request || {},size=r.width&&r.height?r.width+' × '+r.height:'';
    return '<div class="queue-job-navigation"><button type="button" data-queue-open-job="'+esc(job.job_id)+'">'+label(job)+'</button><small>'+esc([r.source_project_id,size].filter(Boolean).join(' · '))+'</small></div>';
  }
  const originalCard=h3QueueJobCard;
  h3QueueJobCard=function(job,...args){
    const html=originalCard(job,...args),end='</div></details>';
    return html.endsWith(end)?html.slice(0,-end.length)+navigation(job)+end:html;
  };
  const originalDashboard=renderH3QueueDashboard;
  renderH3QueueDashboard=function(...args){
    const out=originalDashboard(...args);
    document.querySelectorAll('#activeBatch [data-queue-lane]').forEach(panel=>{
      const lane=panel.dataset.queueLane,worker=h3State.workers?.[lane] || (lane==='local_generation'?h3State.worker:{}) || {};
      const active=jobs().filter(job=>h3JobQueueLane(job)===lane&&h3QueueActiveStatuses.has(job.status?.status));
      const job=active.find(job=>job.job_id===worker.current_job_id) || active[0];
      if(job) panel.insertAdjacentHTML('beforeend','<button type="button" class="queue-current-navigation" data-queue-open-job="'+esc(job.job_id)+'">'+label(job)+'</button>');
    });
    return out;
  };
  function changePage(page){internalPageChange=true;try{goPage(page);}finally{internalPageChange=false;}}
  window.addEventListener('h3-page-change',()=>{if(!internalPageChange){revision++;resultFocus=null;}});
  async function record(job,message='',token=revision){
    let detail=job;
    try{const loaded=await api('/api/h3/jobs/'+encodeURIComponent(job.job_id)+'/feedback-context');if(loaded.request)detail=loaded;}
    catch{message=(message?message+' ':'')+'상세 요청을 불러오지 못해 큐의 요약 기록을 표시합니다.';}
    if(token!==revision)return;
    let dialog=q('queueJobRecord');
    if(!dialog){dialog=document.createElement('dialog');dialog.id='queueJobRecord';dialog.setAttribute('aria-label','큐 작업 기록');document.body.append(dialog);}
    dialog.innerHTML='<h2>큐 작업 기록</h2><p>'+esc(message || '직접 입력 작업입니다. 제출 당시 요청과 현재 상태를 확인할 수 있습니다.')+'</p><pre>'+esc(JSON.stringify({job_id:detail.job_id,status:detail.status,request:detail.request},null,2))+'</pre><button type="button">닫기</button>';
    dialog.querySelector('button').onclick=()=>dialog.close();if(!dialog.open)dialog.showModal();
  }
  function options(select,rows,value){
    select.replaceChildren(...rows.map(([id,text])=>new Option(text,id)));
    select.value=value;
  }
  function focusElement(element,token){
    if(!element)return;
    element.classList.add('queue-navigation-target');
    element.setAttribute('tabindex','-1');
    requestAnimationFrame(()=>{if(token!==revision)return;element.focus({preventScroll:true});element.scrollIntoView({behavior:'smooth',block:'center'});});
  }
  async function openProject(job,token){
    const r=job.request || {},mode=destination(job),i2v=mode==='i2v-create',project=r.source_project_id;
    const base='/api/h3/projects/'+encodeURIComponent(project);
    // Preflight in local variables; leaving the page while waiting cannot overwrite another view.
    const [library,contents,clip]=await Promise.all([api('/api/h3/projects'),api(base+'/clips'),r.source_clip_id?api(base+'/clips/'+encodeURIComponent(r.source_clip_id)):null]);
    if(token!==revision)return;
    const available=(library.projects || []).filter(p=>(p.generation_mode==='i2v')===i2v);
    if(!available.some(p=>p.project_id===project))return record(job,'원본 프로젝트가 삭제되었거나 작업 유형과 다릅니다. 제출 당시 작업 기록을 표시합니다.');
    const scenes=contents.scenes || [],group=scenes.find(s=>s.scene_id===(r.source_scene_id || clip?.scene_id));
    if(!group || (clip&&!group.clips?.some(c=>c.clip_id===clip.clip_id)))return record(job,'원본 씬·클립을 찾지 못했습니다. 다른 클립으로 이동하지 않고 작업 기록을 표시합니다.');
    const prefix=i2v?'i2v':'h3';
    options(q(prefix+'Project'),[['',i2v?'I2V 프로젝트 선택':'프로젝트 선택'],...available.map(p=>[p.project_id,p.title || p.project_id])],project);
    if(i2v){i2vProjects=available;i2vProjectScenes=scenes;renderI2VProjectScenes();}
    else {h3ProjectSelectionRevision++;h3Projects=available;renderH3ProjectOptions(project);h3ProjectScenes=scenes;renderH3ProjectScenes();syncH3ProjectDeleteButton();const button=q('createH3ProjectTestSet');if(button)button.disabled=false;}
    q(prefix+'Scene').value=group.scene_id;
    if(i2v)renderI2VProjectClips();else renderH3ProjectClips();
    if(clip){
      q(prefix+'Clip').value=clip.clip_id;
      if(i2v){i2vSelectedClip=clip;renderI2VSceneImagePreview();renderI2VProjectPreview();}
      else {h3SelectedClip=clip;renderH3ProjectPreview();}
    }
    changePage(mode);
    focusElement(q(prefix+'ProjectPreview'),token);
    note('큐 작업의 프로젝트·씬·클립을 열었습니다. 입력 중인 프롬프트는 변경하지 않았습니다.');
  }
  function ensureFilter(id,value){
    const select=q(id);
    if(![...select.options].some(o=>o.value===value))select.add(new Option(value,value));
    select.value=value;
  }
  function highlightResult(){
    if(!resultFocus)return null;
    const card=[...document.querySelectorAll('#h3SelectedResults [data-h3-selected-job]')].find(el=>el.dataset.h3SelectedJob===resultFocus.source);
    if(!card)return null;
    card.classList.add('queue-navigation-target');
    let banner=card.querySelector('.queue-navigation-context');
    if(!banner){banner=document.createElement('p');banner.className='queue-navigation-context';banner.setAttribute('role','status');card.prepend(banner);}
    const job=findJob(resultFocus.job.job_id) || resultFocus.job,r=job.request || {};
    banner.textContent='큐에서 연 작업 · '+(r.source_clip_id || job.job_id)+' · '+(r.width || '-')+' × '+(r.height || '-')+' · '+(job.status?.stage || job.status?.status || '상태 확인 중');
    const row=[...card.querySelectorAll('[data-h3-rerender-job]')].find(el=>el.dataset.h3RerenderJob===(r.source_rerender_job_id || job.job_id))?.closest('.h3-rerender-history-row');
    if(row)row.classList.add('queue-navigation-target');
    return row || card;
  }
  const originalResults=renderH3Results;
  renderH3Results=function(...args){const out=originalResults(...args);highlightResult();return out;};
  async function openResults(job,token){
    const r=job.request || {},source=r.source_selected_job_id;
    if(!source)return record(job,'이 작업에는 원본 후보 연결 정보가 없습니다. 작업 기록을 표시합니다.');
    const project=r.source_project_id || '__direct__',scene=r.source_scene_id || '__none__';
    const query=new URLSearchParams({project_id:project,scene_id:scene,focus_job_id:source,page_size:String(H3_RESULTS_PAGE_SIZE)});
    const data=await api('/api/h3/results-page?'+query);
    if(token!==revision)return;
    if(!data.focus?.found)return record(job,'원본 후보가 선택 해제되었거나 삭제되어 결과 확인 목록에 없습니다. 제출 당시 작업 기록을 표시합니다.');
    // Invalidate earlier paged responses before installing the exact target page.
    h3PagedRefreshRevision.results++;
    h3ResultsPageData=data;h3ResultsPage=data.pagination.page;
    if(q('h3ResultEpisodeFilter'))q('h3ResultEpisodeFilter').value='';
    if(q('h3ResultSort'))q('h3ResultSort').value=data.sort_by||'recent';
    if(q('h3ResultRerenderCountFilter'))q('h3ResultRerenderCountFilter').value='';
    ensureFilter('h3ResultProjectFilter',project);ensureFilter('h3ResultSceneFilter',scene);
    resultFocus={source,job};renderH3Results();
    changePage('results');
    focusElement(highlightResult(),token);
    note('원본 후보와 해당 고해상도/업스케일 작업 기록을 열었습니다.');
  }
  async function openTests(job,token){
    const r=job.request || {},sessionId=r.test_session_id;
    if(!sessionId)return record(job,'테스트 세션 연결 정보가 없습니다.');
    const out=await api('/api/model-tests/sessions/'+encodeURIComponent(sessionId)+'/results');
    if(token!==revision)return;
    modelTestActiveResults=out;
    const run=(out.runs || []).find(run=>run.job_id===job.job_id);
    changePage(isR2VSession(out.session)?'r2v-tests':'model-tests');
    renderModelTestResults(new Set(run?[String(run.run_id)]:[]));
    focusElement(run?[...document.querySelectorAll('[data-model-test-run]')].find(el=>el.dataset.modelTestRun===String(run.run_id)):modelTestResultsBox(out.session),token);
  }
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-queue-open-job]');
    if(!button || button.disabled)return;
    const job=findJob(button.dataset.queueOpenJob);
    if(!job)return note('작업 기록을 찾지 못했습니다. 큐를 새로고침하세요.',true);
    const token=++revision,old=button.textContent;
    button.disabled=true;button.textContent='이동 준비 중…';
    try{
      const target=destination(job);
      if(target==='results')await openResults(job,token);
      else if(target==='tests')await openTests(job,token);
      else if(target==='record')await record(job);
      else await openProject(job,token);
    }catch(error){if(token===revision){note('이동할 원본을 불러오지 못했습니다. '+error.message,true);await record(job,'원본을 불러오지 못했습니다. 큐 작업은 변경되지 않았습니다.');}}
    finally{button.disabled=false;button.textContent=old;}
  });
  if(currentPage==='queue')renderH3QueueDashboard();
})();
