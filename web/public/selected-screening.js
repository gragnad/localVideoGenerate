/* Continuous viewing is a reference playlist, never an edit/export or a candidate-selection write. */
(() => {
  const openButton = document.getElementById('openSelectedScreening');
  if (!openButton) return;
  const dialog = document.createElement('dialog');
  dialog.id = 'screeningDialog';
  dialog.setAttribute('aria-label', '선택 클립 연속 시청과 연결 검수');
  dialog.innerHTML = `<div class="screening-head"><h2>선택 클립 연속 시청</h2><button type="button" id="screeningClose">닫기</button></div>
    <details id="screeningProjectPicker" class="screening-project-picker"><summary id="screeningProjectSummary">프로젝트 선택</summary>
      <div id="screeningProjects" class="screening-projects" role="group" aria-label="연속 시청에 포함할 프로젝트"></div>
      <div class="screening-actions"><button type="button" id="screeningApplyProjects" disabled>선택 프로젝트 모아 보기</button><small>여러 프로젝트는 전체 씬의 선택 영상을 모두 포함합니다. 같은 클립도 생략하지 않습니다.</small></div>
    </details>
    <p id="screeningScope"></p><p id="screeningStatus" role="status" aria-live="polite"></p>
    <div class="screening-actions"><button type="button" id="screeningReload">목록 다시 불러오기</button><button type="button" id="screeningSortName" title="클립 이름 기준으로 숫자를 인식해 오름차순 정렬" disabled>이름순 정렬</button><button type="button" id="screeningSave">검수 기록 저장</button><button type="button" id="screeningRestoreDraft" hidden>이 기기 임시 기록 복구</button></div>
    <div class="screening-layout"><div><h3 id="screeningTitle">선택한 클립 없음</h3>
      <video id="screeningVideo" controls playsinline preload="metadata"></video>
      <div class="screening-actions"><button type="button" id="screeningPrevious">이전 클립</button><button type="button" id="screeningPlay">▶ 연속 재생</button><button type="button" id="screeningPause">정지</button><button type="button" id="screeningNext">다음 클립</button></div>
      <div class="screening-actions"><label>연결 구간 길이(각 영상)<select id="screeningBoundarySeconds"><option value="1">1초</option><option value="2" selected>2초</option><option value="3">3초</option></select></label><button type="button" id="screeningBoundary">현재 끝 ↔ 다음 시작 반복</button></div>
      <p id="screeningEdge"></p><label><input type="checkbox" id="screeningFlag"> 이 연결에 문제 표시</label>
      <label>연결 메모<textarea id="screeningIssue" maxlength="4000" placeholder="조명, 시선, 동작, 캐릭터 위치 등 연결 문제를 기록하세요."></textarea></label>
      <div class="screening-actions"><button type="button" id="screeningCompare">현재·다음 후보 비교 / 선택 열기</button></div>
      <p class="muted">포함한 프로젝트의 선택된 원본 후보 전체를 불러옵니다. 프로젝트가 다르거나 같은 클립의 여러 선택 결과도 생략하지 않습니다. 순서·제외·연결 메모는 프로젝트 조합별로 별도 저장하며 후보 채택이나 독립 노트를 변경하지 않습니다. 파일 전환 시 짧은 로딩이 있을 수 있습니다.</p>
    </div><ol id="screeningList" aria-label="재생 순서와 포함 여부"></ol></div>`;
  document.body.append(dialog);
  const q = id => document.getElementById('screening' + id), video = q('Video');
  let items = [], review = null, current = null, edgeSource = null, mode = 'paused', phase = 0;
  let ticket = 0, sourceTicket = 0, saving = false, dirty = false, editVersion = 0, conflicted = false, loaded = false;
  let scope = {}, draft = null;
  let entryProject = '', entryScene = '', lastEntryProject = null, lastProjects = [];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const label = item => `${item.project_id === '__direct__' ? '직접 입력' : item.project_id || '-'} / ${item.scene_id || '-'} / ${item.clip_id || '-'} (후보 ${item.candidate_index || '-'}, ${item.job_id})`;
  const draftKey = () => 'h3-screening-draft:' + JSON.stringify(scope);
  const nameOrder = new Intl.Collator('ko', {numeric: true, sensitivity: 'base'});
  const ordered = () => { const map = new Map(items.map(item => [item.job_id, item])); return review ? [...new Set([...review.order, ...items.map(i => i.job_id)])].map(id => map.get(id)).filter(Boolean) : []; };
  const active = () => ordered().filter(item => !review.excluded.includes(item.job_id));
  const edge = () => { const list = active(), index = list.findIndex(i => i.job_id === edgeSource); return index >= 0 && index < list.length - 1 ? [list[index], list[index + 1]] : null; };
  const edgeKey = () => edge()?.map(i => i.job_id).join('\n');
  const selectedProjects = () => [...q('Projects').querySelectorAll('[data-screen-project]:checked')].map(input => input.dataset.screenProject).sort();
  function updateProjectPicker() {
    const count = selectedProjects().length;
    q('ProjectSummary').textContent = '프로젝트 선택 · ' + count + '개';
    q('ApplyProjects').disabled = saving || count === 0;
  }
  q('Projects').onchange = updateProjectPicker;
  function status(message, bad = false) { q('Status').textContent = message; q('Status').dataset.error = String(bad); }
  function stop() { mode = 'paused'; sourceTicket++; video.pause(); }
  function keepDraft() {
    try { localStorage.setItem(draftKey(), JSON.stringify({...review, saved_revision: review.revision})); }
    catch { status('이 기기에 임시 기록을 저장하지 못했습니다. 검수 기록 저장 버튼으로 서버 저장을 확인하세요.', true); }
  }
  function changed() { dirty = true; editVersion++; keepDraft(); status('변경사항이 있습니다. 검수 기록 저장을 눌러주세요.'); }
  function renderEdge() {
    const pair = edge(), key = edgeKey();
    q('Edge').textContent = pair ? `연결 검수: ${label(pair[0])} → ${label(pair[1])}` : '마지막 클립이거나 연결할 다음 클립이 없습니다.';
    q('Flag').checked = Boolean(key && Object.hasOwn(review.issues, key));
    q('Issue').value = key ? review.issues[key] || '' : '';
    q('Flag').disabled = q('Issue').disabled = q('Boundary').disabled = !pair;
    q('Compare').disabled = !current;
  }
  function render() {
    const rows = ordered(), counts = new Map();
    for (const item of rows) { const key = item.scene_id + '\n' + item.clip_id; counts.set(key, (counts.get(key) || 0) + 1); }
    q('List').innerHTML = rows.map((item, index) => `<li class="screening-item ${item.job_id === current ? 'is-current' : ''} ${review.excluded.includes(item.job_id) ? 'is-excluded' : ''}"><b>${index + 1}. ${escape(item.clip_id || item.job_id)}</b><small>${escape(label(item))}${counts.get(item.scene_id + '\n' + item.clip_id) > 1 ? ' · 동일 클립 복수 결과' : ''}${item.available ? '' : ' · 원본 영상 없음'}</small>
      <small>${Object.keys(review.issues).some(key => key.startsWith(item.job_id + '\n')) ? '⚑ 연결 문제 기록 있음' : ''}</small><button type="button" data-screen-play="${escape(item.job_id)}" ${item.available ? '' : 'disabled'}>이 클립 보기</button>
      <button type="button" data-screen-up="${escape(item.job_id)}" ${index ? '' : 'disabled'} aria-label="${escape(item.clip_id)} 위로">↑</button><button type="button" data-screen-down="${escape(item.job_id)}" ${index < rows.length - 1 ? '' : 'disabled'} aria-label="${escape(item.clip_id)} 아래로">↓</button>
      <button type="button" data-screen-exclude="${escape(item.job_id)}" aria-pressed="${review.excluded.includes(item.job_id)}">${review.excluded.includes(item.job_id) ? '재생에 포함' : '재생에서 제외'}</button></li>`).join('') || '<li>선택된 클립이 없습니다.</li>';
    const list = active(), index = list.findIndex(i => i.job_id === current);
    q('Previous').disabled = index <= 0; q('Next').disabled = index < 0 || index >= list.length - 1;
    q('Play').disabled = !list.length;
    q('SortName').disabled = !loaded || rows.length < 2;
    renderEdge();
  }
  function show(item, autoplay = false, boundary = false) {
    if (!item) { stop(); return; }
    if (!item.available) {
      stop(); current = item.job_id; if (!boundary) edgeSource = current;
      q('Title').textContent = label(item); video.removeAttribute('src'); video.load(); render();
      status('재생할 원본 영상이 없습니다. 누락된 클립을 확인하거나 재생에서 제외하세요.', true); return;
    }
    const token = ++sourceTicket;
    current = item.job_id;
    if (!boundary) edgeSource = current;
    q('Title').textContent = label(item);
    video.pause(); video.src = `/api/h3/jobs/${encodeURIComponent(item.job_id)}/video`;
    video.onloadedmetadata = () => {
      if (token !== sourceTicket || !dialog.open) return;
      if (boundary && phase === 0) video.currentTime = Math.max(0, video.duration - Number(q('BoundarySeconds').value));
    };
    render();
    if (autoplay) {
      video.play().catch(() => { if (token === sourceTicket) { stop(); status('재생이 중단되었습니다. 연속 재생을 다시 눌러주세요.', true); } });
    }
  }
  function advance() {
    if (mode === 'boundary') {
      const pair = edge(); if (!pair) return stop();
      phase = 1 - phase; show(pair[phase], true, true); return;
    }
    if (mode !== 'continuous') return;
    const list = active(), index = list.findIndex(i => i.job_id === current);
    if (index < 0 || index + 1 >= list.length) { stop(); status('선택한 클립의 연속 시청을 마쳤습니다.'); return; }
    show(list[index + 1], true);
  }
  video.onended = advance;
  video.ontimeupdate = () => { if (mode === 'boundary' && phase === 1 && video.currentTime >= Math.min(Number(q('BoundarySeconds').value), video.duration) - .04) advance(); };
  video.onerror = () => { stop(); status('원본 영상을 불러오지 못했습니다. 누락을 확인한 후 직접 다음 클립을 선택하세요.', true); };
  async function save() {
    if (!loaded || !review || saving || conflicted) { if (conflicted) status('다른 화면의 변경이 있습니다. 임시 기록은 보존했습니다. 다시 불러와 비교한 뒤 저장하세요.', true); return false; }
    saving = true; q('Save').disabled = true; updateProjectPicker();
    const version = editVersion, snapshot = JSON.parse(JSON.stringify(review));
    try {
      const out = await api('/api/h3/selected-screening', {method: 'PUT', headers: {'content-type': 'application/json'}, body: JSON.stringify({...snapshot, ...scope})});
      review.revision = out.revision;
      dirty = editVersion !== version;
      if (dirty) keepDraft(); else { try { localStorage.removeItem(draftKey()); } catch {} }
      status(dirty ? '저장 중 추가 수정이 있습니다. 다시 저장하세요.' : '서버에 검수 기록을 저장했습니다.');
      return !dirty;
    } catch (error) { conflicted = error.status === 409; keepDraft(); status('저장 실패 · 입력 내용은 유지됩니다. ' + error.message, true); return false; }
    finally { saving = false; q('Save').disabled = false; updateProjectPicker(); }
  }
  async function load() {
    if (saving) return;
    if (dirty && !confirm('저장하지 않은 변경이 있습니다. 이 기기의 임시 기록은 보존하고 서버 기록을 다시 불러올까요?')) return;
    const token = ++ticket; stop(); loaded = false; q('Save').disabled = true; q('Reload').disabled = true; q('SortName').disabled = true;
    status('포함한 프로젝트의 선택 후보 전체를 불러오는 중…');
    try {
      const query = new URLSearchParams({scene_id: scope.scene_id || ''});
      for (const project of scope.project_ids || [scope.project_id]) query.append('project_id', project);
      const out = await api('/api/h3/selected-screening?' + query);
      if (token !== ticket || !dialog.open) return;
      items = out.items; review = out.review; dirty = false; conflicted = false; loaded = true;
      try {
        draft = JSON.parse(localStorage.getItem(draftKey()) || 'null');
        if (draft && (!Array.isArray(draft.order) || !Array.isArray(draft.excluded) || !draft.issues || typeof draft.issues !== 'object')) draft = null;
      } catch { draft = null; }
      q('RestoreDraft').hidden = !draft;
      const first = active()[0]; current = edgeSource = null;
      if (first) show(first); else { video.removeAttribute('src'); video.load(); q('Title').textContent = '재생에 포함된 선택 클립 없음'; render(); }
      const missing = items.filter(i => !i.available).length;
      status(`선택 후보 ${items.length}개 전체 · 클립 이름의 숫자 순서가 기본이며 순서는 직접 조정할 수 있습니다.${missing ? ` 원본 없는 후보 ${missing}개를 확인하세요.` : ''}${draft ? ' 이 기기에 복구 가능한 임시 기록이 있습니다.' : ''}`, missing > 0);
    } catch (error) { if (token === ticket) status('불러오기 실패 · ' + error.message, true); }
    finally { if (token === ticket) { q('Save').disabled = !loaded; q('Reload').disabled = false; } }
  }
  function applyProjects() {
    if (saving) return;
    const projects = selectedProjects();
    if (!projects.length) return;
    if (dirty && !confirm('저장하지 않은 변경이 있습니다. 이 기기의 임시 기록은 보존하고 다른 프로젝트 목록을 불러올까요?')) return;
    lastEntryProject = entryProject; lastProjects = projects;
    const scene = projects.length === 1 && projects[0] === entryProject ? entryScene : '';
    scope = projects.length === 1 ? {project_id: projects[0], scene_id: scene} : {project_ids: projects, scene_id: ''};
    q('Scope').textContent = projects.map(p => p === '__direct__' ? '직접 입력' : p).join(' + ') + ' / ' + (scope.scene_id || '전체 씬');
    stop(); video.removeAttribute('src'); video.load();
    review = null; items = []; dirty = false; current = edgeSource = null; loaded = false; render();
    q('ProjectPicker').open = false;
    load();
  }
  q('ApplyProjects').onclick = applyProjects;
  openButton.onclick = () => {
    entryProject = document.getElementById('h3ResultProjectFilter').value;
    entryScene = document.getElementById('h3ResultSceneFilter').value;
    const options = [...document.getElementById('h3ResultProjectFilter').options].filter(option => option.value);
    const preferred = lastEntryProject === entryProject ? lastProjects : entryProject ? [entryProject] : [];
    q('Projects').innerHTML = options.map(option => `<label><input type="checkbox" data-screen-project="${escape(option.value)}" ${preferred.includes(option.value) ? 'checked' : ''}><span>${escape(option.textContent)}</span></label>`).join('');
    updateProjectPicker();
    review = null; items = []; dirty = false; current = edgeSource = null; loaded = false; render();
    dialog.showModal();
    if (selectedProjects().length) applyProjects();
    else {
      scope = {}; q('Save').disabled = true; q('Reload').disabled = true; q('SortName').disabled = true;
      q('ProjectPicker').open = true; q('Scope').textContent = '함께 볼 관련 프로젝트를 선택하세요.';
      status('위에서 하나 이상의 프로젝트를 체크한 뒤 모아 보기를 누르세요.');
    }
  };
  function close() {
    if (saving) { status('저장이 진행 중입니다. 완료 후 닫아주세요.'); return; }
    if (dirty && !confirm('아직 서버에 저장하지 않은 변경이 있습니다. 이 기기 임시 기록만 보존하고 닫을까요?')) return;
    ticket++; stop(); video.removeAttribute('src'); video.load(); dialog.close();
  }
  q('Close').onclick = close;
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  q('Save').onclick = save; q('Reload').onclick = load;
  q('SortName').onclick = () => {
    if (!loaded || !review) return;
    stop();
    review.order = [...items].sort((a, b) =>
      nameOrder.compare(a.clip_id || a.job_id, b.clip_id || b.job_id) ||
      nameOrder.compare(a.scene_id || '', b.scene_id || '') ||
      nameOrder.compare(a.project_id || '', b.project_id || '') ||
      nameOrder.compare(String(a.candidate_index ?? ''), String(b.candidate_index ?? '')) ||
      nameOrder.compare(a.job_id, b.job_id)
    ).map(item => item.job_id);
    changed();
    const first = active()[0];
    if (first) show(first); else render();
    status('클립 이름순으로 정렬했습니다 (1, 2, 10 순). 검수 기록 저장을 누르면 이 순서가 유지됩니다.');
  };
  q('RestoreDraft').onclick = () => {
    if (!loaded || !draft || saving) return;
    if (draft.saved_revision !== review.revision && !confirm('서버 기록과 다른 시점의 임시 기록입니다. 현재 화면에 복구할까요? 서버에는 저장 버튼을 눌러야 반영됩니다.')) return;
    stop(); review = {...review, order: draft.order, excluded: draft.excluded, issues: draft.issues};
    changed(); render(); q('RestoreDraft').hidden = true;
  };
  q('Play').onclick = () => {
    const list = active(), item = list.find(i => i.job_id === current) || list[0];
    mode = 'continuous'; show(item, true);
  };
  q('Pause').onclick = stop;
  for (const [id, delta] of [['Previous', -1], ['Next', 1]]) q(id).onclick = () => {
    const list = active(), index = list.findIndex(i => i.job_id === current); stop(); show(list[index + delta]);
  };
  q('Boundary').onclick = () => { const pair = edge(); if (pair) { mode = 'boundary'; phase = 0; show(pair[0], true, true); status('현재 클립 끝과 다음 클립 시작을 반복 확인 중입니다.'); } };
  q('BoundarySeconds').onchange = () => { if (mode === 'boundary') q('Boundary').click(); };
  q('Flag').onchange = () => { const key = edgeKey(); if (!key) return; if (q('Flag').checked) review.issues[key] = q('Issue').value; else { delete review.issues[key]; q('Issue').value = ''; } changed(); };
  q('Issue').oninput = () => { const key = edgeKey(); if (key) { review.issues[key] = q('Issue').value; q('Flag').checked = true; changed(); } };
  q('List').onclick = event => {
    const button = event.target.closest('button'); if (!button || button.disabled || !loaded) return;
    const id = Object.values(button.dataset)[0];
    if (button.dataset.screenPlay) { stop(); show(items.find(i => i.job_id === id)); return; }
    stop();
    if (button.dataset.screenExclude) {
      review.excluded = review.excluded.includes(id) ? review.excluded.filter(value => value !== id) : [...review.excluded, id];
    } else {
      const ids = ordered().map(i => i.job_id), index = ids.indexOf(id), next = index + (button.dataset.screenUp ? -1 : 1);
      [ids[index], ids[next]] = [ids[next], ids[index]]; review.order = ids;
    }
    changed(); render();
  };
  q('Compare').onclick = () => {
    const pair = edge() || [items.find(i => i.job_id === current)].filter(Boolean);
    close(); if (dialog.open) return;
    goPage('compare'); window.dispatchEvent(new CustomEvent('h3-screening-compare', {detail: {items: pair}}));
  };
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
})();
