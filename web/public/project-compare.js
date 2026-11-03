/* Read-only paired review. Never writes production selections or comparison votes. */
(() => {
  const q = id => document.getElementById(id), section = document.querySelector('[data-view="compare"]');
  if (!section) return;
  const visible = () => !section.hidden;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const natural = (a,b) => a.localeCompare(b, undefined, {numeric:true});
  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } };
  const write = (key,value) => { try { localStorage.setItem(key,JSON.stringify(value)); } catch { status('검토 위치를 이 기기에 저장하지 못했습니다. 노트 저장 상태는 오른쪽에서 확인하세요.'); } };
  const workspace = q('compareWorkspace'), saved = read('h3-project-review', {});
  let rows = [], position = 0, ticket = 0, initialized = false, loading = false, externalTicket = 0, mapping = {};
  let libraryFilters = {};
  const sides = ['left','right'].map((name,i) => {
    const root = q(i ? 'compareRight' : 'compareLeft');
    root.innerHTML = '<div class="compare-video-head"><strong data-role="title">'+(i?'B':'A')+' · 프로젝트 선택</strong><select data-role="set" aria-label="'+(i?'B':'A')+' 생성 묶음"></select><div data-role="candidates" class="compare-candidates"></div></div><video data-role="video" controls playsinline preload="metadata" hidden></video><p data-role="empty">대응 영상 없음</p>';
    return {name,root,q: role => root.querySelector('[data-role="'+role+'"]'),project:String(saved.projects?.[i] || ''),clips:[],jobs:new Map(),current:null,chosen:new Map(),sets:new Map()};
  });
  const playback = new H3DualPlayback(q('comparePlayback'), sides.map(s=>s.q('video')));
  playback.q('audio').options[0].textContent = 'A만'; playback.q('audio').options[1].textContent = 'B만';
  playback.root.querySelector('.dual-settings-panel small').textContent='구간은 위쪽 A 영상 시간 기준입니다. 재생 연결을 켜면 기본 재생기의 재생·정지·탐색도 두 영상에 적용됩니다.';
  q('comparePlay').onclick = () => { if(!loading) playback.q('play').click(); };
  q('comparePause').onclick = () => {playback.stop();status('함께 정지 · '+(rows.length?position+1:0)+' / '+rows.length);};
  function syncPlaybackControls(){q('comparePlay').disabled=loading||!playback.ready();}
  sides.forEach(side=>['loadedmetadata','durationchange','error','emptied'].forEach(name=>side.q('video').addEventListener(name,syncPlaybackControls)));
  new MutationObserver(()=>{const message=playback.q('status').textContent;if(message)status(message);}).observe(playback.q('status'),{childList:true,subtree:true,characterData:true});
  function closeOptions(){q('compareOptions').open=false;q('compareOptions').querySelector('summary').focus({preventScroll:true});}
  q('compareCloseOptions').onclick=closeOptions;
  section.addEventListener('keydown',event=>{if(event.key==='Escape'&&q('compareOptions').open){closeOptions();event.stopPropagation();}});
  q('compareAudio').onchange = () => { playback.q('audio').value=q('compareAudio').value; playback.audio(); };
  playback.q('audio').addEventListener('change',()=>q('compareAudio').value=playback.q('audio').value);
  const identity = (scene,clip) => JSON.stringify([scene || '',clip]);
  const pairKey = () => 'h3-review-mapping:'+JSON.stringify(sides.map(s=>s.project));
  function status(message) { q('compareStatus').textContent=message; }
  function remember() { write('h3-project-review',{projects:sides.map(s=>s.project),row:rows[position]?.id}); }
  function setOptions(select, items, value) {
    select.innerHTML = items.map(([id,label])=>'<option value="'+esc(id)+'">'+esc(label)+'</option>').join('');
    select.value=value;
  }
  async function loadProject(project) {
    const sets = new Map(), jobs = new Map();
    if (!project) return {clips:[],jobs};
    // Every page is indexed. No first-page truncation and no pairing by array index.
    let page=1, pages=1;
    do {
      const out = await api('/api/h3/candidate-page?'+new URLSearchParams({project_id:project,page:String(page),page_size:'50'}));
      pages = out.pagination?.total_pages || 1;
      for (const set of out.candidate_sets || []) sets.set(set.candidate_set_id,set);
      for (const job of out.jobs || []) jobs.set(job.job_id,job);
      page++;
    } while(page<=pages);
    const clips = new Map();
    for(const set of sets.values()) {
      const request = jobs.get(set.candidate_job_ids?.[0])?.request || {};
      const clip = set.source_clip_id || request.source_clip_id || set.candidate_set_id;
      const scene = set.source_scene_id || request.source_scene_id || '';
      const id=identity(scene,clip);
      if(!clips.has(id)) clips.set(id,{id,clip,scene,sets:[]});
      clips.get(id).sets.push(set);
    }
    for(const clip of clips.values()) clip.sets.sort((a,b)=>natural(String(b.created_at || b.candidate_set_id),String(a.created_at || a.candidate_set_id)));
    return {clips:[...clips.values()].sort((a,b)=>natural(a.clip,b.clip)||natural(a.scene,b.scene)),jobs};
  }
  function buildRows(preferred) {
    const right = new Map(sides[1].clips.map(c=>[c.id,c])), used=new Set();
    const reserved=new Set(sides[0].clips.filter(a=>Object.hasOwn(mapping,a.id)).map(a=>mapping[a.id]).filter(id=>right.has(id)));
    rows=sides[0].clips.map(a=>{
      const explicit = Object.hasOwn(mapping,a.id), target=explicit?mapping[a.id]:reserved.has(a.id)?'':a.id;
      const b = used.has(target)?null:right.get(target) || null;
      if(b) used.add(b.id);
      return {id:'A:'+a.id,a,b,unconfirmed:!explicit&&!b};
    });
    for(const b of sides[1].clips) if(!used.has(b.id)) rows.push({id:'B:'+b.id,a:null,b});
    position=Math.max(0,rows.findIndex(r=>r.id===preferred)); renderPosition();
  }
  function renderPosition() {
    const row=rows[position];
    setOptions(q('comparePosition'),rows.length ? rows.map((r,i)=>[String(i),(i+1)+'. '+(r.a?.clip || 'A 없음')+' ↔ '+(r.b?.clip || 'B 없음')]) : [['','클립 없음']],rows.length?String(position):'');
    q('compareFirst').disabled=loading||!rows.length;
    q('comparePrevious').disabled=loading||position===0;
    q('compareNext').disabled=loading||position>=rows.length-1;
    q('comparePosition').disabled=loading||!rows.length;
    setOptions(q('compareMatch'),[['','대응 없음'],...sides[1].clips.map(c=>[c.id,c.clip+' · '+c.scene])],row?.b?.id || '');
    q('compareSaveMatch').disabled=loading||!row?.a;
    sides.forEach((side,i)=>renderVideo(side,i ? row?.b : row?.a));
    if(!loading) status(!rows.length ? '두 프로젝트를 선택하세요.' : (position+1)+' / '+rows.length+(row?.unconfirmed ? ' · B 대응 없음: 이름이 다르면 클립 대응 설정에서 직접 연결하세요.' : !row?.a || !row?.b ? ' · 대응 영상 없음' : ''));
    remember();
  }
  function renderVideo(side,clip) {
    const label=sides.indexOf(side)?'B':'A';
    const set=clip?.sets.find(s=>s.candidate_set_id===side.sets.get(clip.id)) || clip?.sets[0];
    setOptions(side.q('set'),(clip?.sets || []).map(s=>[s.candidate_set_id,(s.created_at || '')+' · '+s.candidate_set_id]),set?.candidate_set_id || '');
    side.q('set').hidden=!clip || clip.sets.length<2;
    const ids=set?.candidate_job_ids || [];
    let id=side.chosen.get(set?.candidate_set_id);
    if(!ids.includes(id) || side.jobs.get(id)?.status?.status!=='completed') {
      const selected=(set?.selected_jobs || [set?.selected_job_id].filter(Boolean)).map(j=>typeof j==='string'?j:j.job_id);
      id=ids.find(j=>selected.includes(j)&&side.jobs.get(j)?.status?.status==='completed') || ids.find(j=>side.jobs.get(j)?.status?.status==='completed');
    }
    side.q('title').textContent=label+' · '+(clip?.clip || '대응 영상 없음')+(id?' (후보 '+(side.jobs.get(id)?.request?.candidate_index || ids.indexOf(id)+1)+')':'');
    side.q('candidates').innerHTML=ids.map((jobId,n)=>{
      const state=side.jobs.get(jobId)?.status?.status, stateLabel=({queued:'대기',running:'생성 중',failed:'실패',cancelled:'취소'})[state] || state || '없음';
      return '<button type="button" data-job="'+esc(jobId)+'" aria-label="'+label+' 후보 '+(n+1)+'" aria-pressed="'+(jobId===id)+'" '+(state!=='completed'?'disabled':'')+'>'+esc(side.jobs.get(jobId)?.request?.candidate_index || n+1)+(state!=='completed'?' · '+esc(stateLabel):'')+'</button>';
    }).join('');
    const video=side.q('video');
    if(side.current!==id) {
      playback.changed(); video.pause();
      if(id) video.src='/api/h3/jobs/'+encodeURIComponent(id)+'/video';
      else { video.removeAttribute('src'); video.load(); }
      side.current=id;
    }
    video.hidden=!id; side.q('empty').hidden=Boolean(id);
    side.q('empty').textContent=clip?'완료된 후보 영상 없음':'대응 영상 없음';
    side.q('set').onchange=()=>{side.sets.set(clip.id,side.q('set').value); renderVideo(side,clip);};
    side.q('candidates').onclick=event=>{const button=event.target.closest('[data-job]');if(!button||button.disabled)return;side.chosen.set(set.candidate_set_id,button.dataset.job);renderVideo(side,clip);};
    playback.update();
    syncPlaybackControls();
  }
  async function refresh(initial=false, preferred, reveal=false) {
    const token=++ticket;
    loading=true; playback.stop(); syncPlaybackControls(); status('전체 클립 목록을 불러오는 중…');
    for(const id of ['compareFirst','comparePrevious','compareNext','comparePosition','compareSaveMatch']) q(id).disabled=true;
    try {
      const metadata=await api('/api/h3/candidate-page?page=1&page_size=1');
      if(token!==ticket) return false;
      libraryFilters=metadata.filters || {};
      sides.forEach((side,i)=>{
        const episode=q(i?'compareEpisodeB':'compareEpisodeA'),projects=libraryFilters.projects || [];
        h3FilterEpisodeProjects(episode,projects,libraryFilters);
        if(reveal && projects.includes(side.project)) episode.value=libraryFilters.episodes_by_project?.[side.project] || h3ProjectEpisode({project_id:side.project});
        const filtered=h3FilterEpisodeProjects(episode,projects,libraryFilters);
        if(!filtered.includes(side.project)) side.project='';
        setOptions(q(i?'compareProjectB':'compareProjectA'),[['','프로젝트 선택'],...filtered.map(p=>[p,p])],side.project);
      });
      const results=await Promise.all(sides.map(side=>loadProject(side.project)));
      if(token!==ticket) return false;
      sides.forEach((side,i)=>Object.assign(side,results[i]));
      mapping=read(pairKey(),{}); loading=false;
      buildRows(preferred || (initial?saved.row:rows[position]?.id)); initialized=true;
      return true;
    } catch(error) { if(token===ticket) { loading=false; syncPlaybackControls(); status('목록 갱신 실패 · '+error.message+' · 갱신 버튼으로 재시도하세요.'); } return false; }
  }
  sides.forEach((side,i)=>q(i?'compareProjectB':'compareProjectA').onchange=event=>{
    externalTicket++; side.project=event.target.value; playback.stop(); renderVideo(side,null); refresh(false,'first');
  });
  sides.forEach((side,i)=>q(i?'compareEpisodeB':'compareEpisodeA').onchange=()=>{
    externalTicket++;
    const filtered=h3FilterEpisodeProjects(q(i?'compareEpisodeB':'compareEpisodeA'),libraryFilters.projects || [],libraryFilters);
    setOptions(q(i?'compareProjectB':'compareProjectA'),[['','프로젝트 선택'],...filtered.map(p=>[p,p])],filtered.includes(side.project)?side.project:'');
    if(side.project && !filtered.includes(side.project)){
      side.project='';playback.stop();renderVideo(side,null);refresh(false,'first');
    }else setOptions(q(i?'compareProjectB':'compareProjectA'),[['','프로젝트 선택'],...filtered.map(p=>[p,p])],side.project);
  });
  q('compareSaveMatch').onclick=()=>{
    const row=rows[position], target=q('compareMatch').value;
    if(!row?.a)return;
    if(target && sides[0].clips.some(a=>a.id!==row.a.id&&mapping[a.id]===target)) return status('이 B 클립은 다른 A 클립에 연결되어 있습니다. 기존 대응을 먼저 해제하세요.');
    const automatic=sides[0].clips.find(c=>c.id===target&&c.id!==row.a.id&&!Object.hasOwn(mapping,c.id));
    if(automatic) return status('이 B 클립은 같은 ID의 A 클립과 연결되어 있습니다. 해당 대응을 먼저 해제하세요.');
    mapping[row.a.id]=target; write(pairKey(),mapping); buildRows(row.id);
  };
  function move(next) { if(loading)return;playback.stop();position=Math.max(0,Math.min(rows.length-1,next));renderPosition(); }
  q('compareFirst').onclick=()=>move(0);q('comparePrevious').onclick=()=>move(position-1);q('compareNext').onclick=()=>move(position+1);
  q('comparePosition').onchange=()=>move(Number(q('comparePosition').value));q('compareRefresh').onclick=()=>refresh();
  function resize(){if(visible()) workspace.style.setProperty('--feedback-workspace-height',Math.max(350,(window.visualViewport?.height||innerHeight)-workspace.getBoundingClientRect().top-12)+'px');}
  function start(){document.body.classList.toggle('compare-page',visible());resize();if(visible()&&!initialized&&!loading)refresh(true);if(!visible())playback.stop();}
  H3CreateSplitter({workspace,handle:q('compareResizer'),range:q('compareSplit'),key:'h3-review-split',labels:['영상','노트']});
  window.addEventListener('h3-page-change',start);window.addEventListener('resize',resize);window.visualViewport?.addEventListener('resize',resize);
  window.addEventListener('h3-screening-compare',async event=>{
    const token=++externalTicket, items=event.detail?.items || [];
    sides.forEach((side,i)=>side.project=items[i]?.project_id || '');
    const loaded=await refresh(false,undefined,true); if(!loaded||token!==externalTicket||!visible())return;
    const clips=items.map((item,i)=>sides[i].clips.find(c=>c.sets.some(s=>s.candidate_job_ids?.includes(item.job_id))));
    // An external exact-job request is one explicit review pair, not a persistent clip mapping.
    rows=[{id:'screening',a:clips[0]||null,b:clips[1]||null}];position=0;
    items.forEach((item,i)=>{const clip=clips[i],side=sides[i],set=clip?.sets.find(s=>s.candidate_job_ids?.includes(item.job_id));if(set){side.sets.set(clip.id,set.candidate_set_id);side.chosen.set(set.candidate_set_id,item.job_id);}});
    renderPosition();status('연속보기에서 선택한 두 후보 · 전체 클립으로 돌아가려면 목록 갱신');
  });
  start();
})();
