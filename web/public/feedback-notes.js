/* The candidate browser and the notebook have intentionally separate lifecycles. */
(() => {
  const q = id => document.getElementById(id);
  const section = document.querySelector('[data-view="feedback"]');
  if (!section) return;
  const DRAFT = 'h3-independent-note-draft:', LAST = 'h3-independent-note-last';
  let active = null, notes = [], preview = false, started = false, opening = 0;
  let videoPage = 1, videoRevision = 0, videoTimer, lastFilters = {}, currentVideo = null;
  const pendingSelections = new Set();
  function selectionBusy(setId, busy) {
    q('feedbackCandidateList').querySelectorAll('[data-feedback-select-set]').forEach(button => {
      if (button.dataset.feedbackSelectSet === setId) button.disabled = busy || button.dataset.ready !== 'true';
    });
  }
  async function changeSelection(setId, jobId, selected) {
    if (pendingSelections.has(setId)) return;
    if (selected && !confirm('이 후보의 선택만 취소할까요? 생성 영상과 재생성 기록은 그대로 유지됩니다.')) return;
    pendingSelections.add(setId); selectionBusy(setId, true);
    ++videoRevision;
    const message = q('feedbackCandidateStatus');
    message.textContent = '후보 선택 저장 중…'; message.dataset.state = '';
    try {
      const base = `/api/h3/candidate-sets/${encodeURIComponent(setId)}`;
      await api(selected ? `${base}/selection/${encodeURIComponent(jobId)}` : `${base}/select`, selected ? {method: 'DELETE'} : {
        method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify({job_id: jobId})
      });
      await refreshVideos();
      message.textContent = selected ? '해당 후보 선택을 취소했습니다.' : '후보 선택 완료 · 04 후보 선택·05 결과 확인에 반영됩니다.';
    } catch (error) {
      message.textContent = error.message; message.dataset.state = 'error';
    } finally {
      pendingSelections.delete(setId); selectionBusy(setId, false);
    }
  }
  let historyRecord = null, historyNote = null, initialBookmark = true;
  const documents = new Map();
  const visible = () => !section.hidden;
  const notebook = q('feedbackNotebook');
  const notesVisible = () => visible() || !document.querySelector('[data-view="compare"]').hidden;
  function mountNotebook() {
    const host = visible() ? q('feedbackWorkspace') : notesVisible() ? q('compareNotebookHost') : null;
    if (host && notebook.parentElement !== host) host.append(notebook);
  }
  const dirty = doc => doc && doc.version !== doc.savedVersion;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const newId = () => 'note_' + [...crypto.getRandomValues(new Uint8Array(16))].map(x => x.toString(16).padStart(2, '0')).join('');
  const titleOf = doc => doc.title.trim() || '제목 없는 노트';
  const date = value => value ? new Date(value).toLocaleString('ko-KR') : '';
  function storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
  function status(message, state = '') {
    q('feedbackSaveStatus').textContent = message;
    q('feedbackSaveStatus').dataset.state = state;
  }
  function editorControls() {
    const writable = active && !active.archived && !active.locked;
    notebook.querySelectorAll('[data-feedback-prefix]').forEach(button => { button.disabled = !writable; });
    q('feedbackSave').disabled = !writable || Boolean(active?.conflict);
    q('feedbackPreview').disabled = !active;
    q('feedbackHistory').disabled = !active?.revision;
    q('feedbackExport').disabled = !active;
    q('feedbackArchive').disabled = !active || Boolean(active.locked);
    q('feedbackReadOnly').hidden = !active?.archived;
    q('feedbackEditArchived').disabled = !active || Boolean(active.locked);
    for (const id of ['feedbackNoteTitle', 'feedbackNoteBody']) {
      q(id).setAttribute('aria-readonly', String(Boolean(active?.archived || active?.locked)));
      if (active?.archived) q(id).setAttribute('aria-describedby', 'feedbackReadOnly');
      else q(id).removeAttribute('aria-describedby');
    }
    q('feedbackInsertReference').disabled = !currentVideo || !writable;
  }
  function persist(doc) {
    try {
      localStorage.setItem(DRAFT + doc.note_id, JSON.stringify({note_id: doc.note_id, title: doc.title, body: doc.body,
        revision: doc.revision, archived: doc.archived, draft_at: new Date().toISOString()}));
      doc.draftSafe = true;
    } catch { doc.draftSafe = false; }
    return doc.draftSafe;
  }
  function drafts() {
    const out = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key.startsWith(DRAFT)) continue;
        try { const doc = JSON.parse(localStorage.getItem(key)); if (/^note_[a-f0-9]{32}$/.test(doc.note_id)) out.push(doc); } catch {}
      }
    } catch {}
    return out;
  }
  function forgetDraft(doc) { try { localStorage.removeItem(DRAFT + doc.note_id); } catch {} }
  function remember(id) { try { localStorage.setItem(LAST, id); } catch {} }
  function markStatus(doc = active) {
    if (doc !== active || !doc) return;
    editorControls();
    if (doc.conflict) status('수정 충돌 · 내 초안 보존 · 서버 버전을 확인하세요.', 'conflict');
    else if (doc.error) status(`${doc.error} · ${doc.draftSafe ? '이 기기에 초안 보존 · 연결 후 재시도' : '임시 저장 불가 · 화면을 닫지 말고 본문을 복사하세요.'}`, 'error');
    else if (doc.saving) status('서버 저장 중…');
    else if (dirty(doc)) status(doc.draftSafe ? '미저장 변경 · 이 기기에 임시 저장 · 서버 저장 대기' : '임시 저장 불가 · 서버 저장 대기', doc.draftSafe ? '' : 'error');
    else if (doc.archived) status('보관된 노트 · 읽기 전용', 'saved');
    else status('서버 저장 완료', 'saved');
    q('feedbackConflict').hidden = !doc.conflict;
    q('feedbackUpdatedAt').textContent = doc.updated_at ? `마지막 서버 저장 ${date(doc.updated_at)}` : '';
  }
  function renderLibrary() {
    const all = new Map(notes.map(n => [n.note_id, n]));
    for (const d of drafts()) all.set(d.note_id, {...all.get(d.note_id), ...d, local: true});
    for (const d of documents.values()) if (dirty(d) || d === active) all.set(d.note_id, {...d, local: dirty(d)});
    const search = q('feedbackNoteSearch').value.toLowerCase(), archived = q('feedbackShowArchived').checked;
    const rows = [...all.values()].filter(n => (Boolean(n.archived) === archived && titleOf(n).toLowerCase().includes(search)) || n.note_id === active?.note_id)
      .sort((a, b) => String(b.updated_at || b.draft_at || '').localeCompare(String(a.updated_at || a.draft_at || '')));
    const html = '<option value="">노트를 선택하세요</option>' + rows.map(n => `<option value="${n.note_id}">${escape(titleOf(n))}${n.local ? ' · 임시 초안' : ''}${n.archived ? ' · 보관' : ''}</option>`).join('');
    h3UpdateMarkup(q('feedbackNoteList'), html);
    q('feedbackNoteList').value = active?.note_id || '';
  }
  async function refreshLibrary() {
    const out = await api('/api/feedback-notes?archived=' + (q('feedbackShowArchived').checked ? '1' : '0'));
    notes = out.notes || [];
    renderLibrary();
  }
  function applyDocument(doc) {
    active = doc; documents.set(doc.note_id, doc); remember(doc.note_id);
    q('feedbackNoteTitle').value = doc.title;
    q('feedbackNoteBody').value = doc.body;
    q('feedbackNoteTitle').disabled = false; q('feedbackNoteBody').disabled = false;
    q('feedbackNoteTitle').readOnly = doc.archived; q('feedbackNoteBody').readOnly = doc.archived;
    q('feedbackArchive').textContent = doc.archived ? '보관 해제' : '노트 보관';
    q('feedbackNoteBody').scrollTop = 0;
    renderPreview(); renderLibrary(); markStatus();
  }
  function asDocument(record, local = false) {
    return {...record, version: local ? 1 : 0, savedVersion: 0, revision: record.revision || null,
      archived: Boolean(record.archived), conflict: null, error: null, saving: null};
  }
  async function protectCurrent() {
    if (!active || !dirty(active)) return;
    persist(active);
    try { await save(active); } catch {}
    if (dirty(active) && !active.draftSafe) throw Error('현재 노트를 보존하지 못했습니다. 지금 저장하거나 본문을 복사한 뒤 이동하세요.');
  }
  async function openNote(id) {
    if (!id || id === active?.note_id) return;
    const ticket = ++opening;
    await protectCurrent();
    if (ticket !== opening) return;
    let draft;
    try { draft = JSON.parse(storageGet(DRAFT + id) || 'null'); } catch {}
    let server = null, error = null;
    try { server = await api('/api/feedback-notes/' + id); } catch (e) { error = e; }
    if (ticket !== opening) return;
    if (!draft && !server) { renderLibrary(); throw error || Error('노트를 불러오지 못했습니다.'); }
    const doc = draft ? asDocument(draft, true) : asDocument(server);
    doc.draftSafe = Boolean(draft);
    if (draft && server) {
      if (server.title === titleOf(doc) && server.body === doc.body && server.archived === doc.archived) {
        Object.assign(doc, asDocument(server)); forgetDraft(doc);
      } else if (server.revision !== doc.revision) doc.conflict = server;
    }
    if (error && !(draft && !draft.revision && error.status === 404)) doc.error = '서버 연결 실패';
    documents.set(id, doc); applyDocument(doc);
    if (dirty(doc) && !doc.conflict && !doc.error) scheduleSave(doc);
  }
  async function createNote(copy = null) {
    ++opening;
    await protectCurrent();
    const doc = asDocument({note_id: newId(), title: copy ? titleOf(copy).slice(0, 190) + ' · 내 초안' : '제목 없는 노트', body: copy?.body || '', revision: null}, true);
    persist(doc); applyDocument(doc);
    q('feedbackFileMenu').open = true;
    q('feedbackNoteTitle').focus({preventScroll: true});
    scheduleSave(doc);
  }
  function changed() {
    if (!active || active.archived || active.locked) return;
    active.title = q('feedbackNoteTitle').value; active.body = q('feedbackNoteBody').value;
    active.version++; active.error = null;
    persist(active); markStatus(); renderLibrary();
    scheduleSave(active);
  }
  function scheduleSave(doc) {
    clearTimeout(doc.timer);
    doc.timer = setTimeout(() => save(doc).catch(() => {}), 1100);
  }
  async function save(doc = active) {
    if (!doc || !dirty(doc) || doc.conflict) return;
    clearTimeout(doc.timer);
    if (doc.saving) { await doc.saving; return save(doc); }
    const version = doc.version, payload = {title: doc.title, body: doc.body, expected_revision: doc.revision, archived: doc.archived};
    doc.error = null;
    doc.saving = (async () => {
      try {
        let record;
        try { record = await api('/api/feedback-notes/' + doc.note_id, {method: 'PUT', headers: {'content-type': 'application/json'}, body: JSON.stringify(payload)}); }
        catch (error) {
          if (error.status !== 409) throw error;
          const current = error.body?.current;
          // A lost response may already have committed this exact snapshot.
          if (current && current.title === (payload.title.trim() || '제목 없는 노트') && current.body === payload.body && current.archived === payload.archived) record = current;
          else { doc.conflict = current || {}; persist(doc); return; }
        }
        doc.revision = record.revision; doc.updated_at = record.updated_at; doc.created_at = record.created_at;
        doc.savedVersion = version;
        notes = [record, ...notes.filter(n => n.note_id !== doc.note_id)];
        if (doc.version === version) forgetDraft(doc); else persist(doc);
      } catch (error) { doc.error = error.message || '서버 저장 실패'; persist(doc); throw error; }
      finally { doc.saving = null; renderLibrary(); markStatus(doc); }
    })();
    markStatus(doc);
    await doc.saving;
    if (dirty(doc) && !doc.conflict) return save(doc);
  }
  function inline(text) {
    return escape(text).replace(/\[([^\]]+)\]\(([^\s)]+)\)/g, (whole, label, raw) => {
      try {
        const url = new URL(raw.replace(/&amp;/g, '&'), location.href);
        if (!['https:', 'http:'].includes(url.protocol)) return whole;
        return `<a href="${escape(url.href)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
      } catch { return whole; }
    }).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }
  function renderPreview() {
    const body = active?.body || '';
    q('feedbackNotePreview').innerHTML = body.split('\n').map((line, index) => {
      const check = line.match(/^\s*- \[([ xX])\] (.*)$/);
      if (check) return `<label class="feedback-check"><input type="checkbox" data-feedback-check="${index}" ${check[1].toLowerCase() === 'x' ? 'checked' : ''} ${active?.archived ? 'disabled' : ''}><span>${inline(check[2])}</span></label>`;
      const heading = line.match(/^(#{1,3}) (.*)$/);
      if (heading) return `<h${heading[1].length + 1}>${inline(heading[2])}</h${heading[1].length + 1}>`;
      return `<p${/^\s*[-*] /.test(line) ? ' class="feedback-bullet"' : ''}>${inline(line) || '<br>'}</p>`;
    }).join('');
  }
  function insertText(text, prefix = false) {
    if (!active || active.archived || active.locked) { status('편집 가능한 노트를 먼저 선택하세요.'); return; }
    const editor = q('feedbackNoteBody'), start = prefix ? editor.value.lastIndexOf('\n', editor.selectionStart - 1) + 1 : editor.selectionStart;
    const end = prefix ? start : editor.selectionEnd, scroll = editor.scrollTop;
    editor.setRangeText(text, start, end, 'end');
    preview = false; togglePreview(); editor.focus({preventScroll: true}); editor.scrollTop = scroll;
    changed();
  }
  function togglePreview() {
    q('feedbackPreview').setAttribute('aria-pressed', String(preview));
    q('feedbackPreview').textContent = preview ? '편집하기' : '미리보기';
    q('feedbackNoteBody').hidden = preview; q('feedbackNotePreview').hidden = !preview;
    if (preview) renderPreview();
  }
  function options(select, values, label) {
    const current = select.value;
    h3UpdateMarkup(select, `<option value="">${label}</option>` + values.map(value => `<option value="${escape(value)}">${escape(value === '__direct__' ? '직접 입력' : value === '__none__' ? '씬 정보 없음' : value)}</option>`).join(''));
    if (values.includes(current)) select.value = current;
  }
  function updateFilters(filters = lastFilters) {
    lastFilters = filters;
    const projects = h3FilterEpisodeProjects(q('feedbackEpisode'), filters.projects || [], filters);
    options(q('feedbackProject'), projects, '전체 프로젝트');
    const project = q('feedbackProject').value;
    const scenes = project ? filters.scenes_by_project?.[project] || [] : [...new Set(projects.flatMap(id => filters.scenes_by_project?.[id] || []))];
    options(q('feedbackScene'), scenes, '전체 씬');
    const scene = q('feedbackScene').value, mapping = filters.clips_by_project_scene?.[project] || {};
    options(q('feedbackClip'), project ? (scene ? mapping[scene] || [] : [...new Set(Object.values(mapping).flat())]).sort() : [], '전체 클립');
    q('feedbackClip').disabled = !project;
  }
  async function refreshVideos() {
    if (!visible()) return;
    const revision = ++videoRevision;
    const query = new URLSearchParams({page: String(videoPage), page_size: '10'});
    for (const [key, id] of [['episode', 'feedbackEpisode'], ['project_id', 'feedbackProject'], ['scene_id', 'feedbackScene'], ['clip_id', 'feedbackClip']]) if (q(id).value) query.set(key, q(id).value);
    const out = await api('/api/h3/candidate-page?' + query);
    if (revision !== videoRevision || !visible()) return;
    updateFilters(out.filters || {});
    const jobs = new Map((out.jobs || []).map(job => [job.job_id, job]));
    const list = q('feedbackCandidateList'), scroll = list.scrollTop;
    const anchor = [...list.children].find(el => el.getBoundingClientRect().bottom > list.getBoundingClientRect().top);
    const offset = anchor?.getBoundingClientRect().top;
    const html = (out.candidate_sets || []).map(set => `<article class="feedback-candidate-set" data-feedback-set="${escape(set.candidate_set_id)}"><b>${escape(set.source_clip_id || set.candidate_set_id)}</b><small>${escape(set.source_scene_id || '')} · ${escape(set.candidate_set_id)}</small><div class="feedback-candidate-buttons">${(set.candidate_job_ids || []).map(id => {
      const job = jobs.get(id), done = job?.status?.status === 'completed';
      const selected = h3SelectedJobs(set).some(item => item.job_id === id);
      return `<div class="feedback-candidate ${selected ? 'is-selected' : ''}" data-feedback-candidate="${escape(id)}"><button type="button" data-feedback-job="${escape(id)}" class="${currentVideo?.job_id === id ? 'is-current' : ''}" ${done ? '' : 'disabled'}>${done ? `<img src="/api/h3/jobs/${encodeURIComponent(id)}/video-thumbnail" loading="lazy" alt="후보 ${escape(job.request?.candidate_index || '')}">` : ''}<span>후보 ${escape(job?.request?.candidate_index || '')} · ${done ? '재생' : escape(job?.status?.status || '대기')}</span></button><button type="button" class="feedback-select-candidate" data-feedback-select-set="${escape(set.candidate_set_id)}" data-feedback-select-job="${escape(id)}" data-ready="${done}" aria-pressed="${selected}" ${done && !pendingSelections.has(set.candidate_set_id) ? '' : 'disabled'}>${selected ? '선택됨 · 선택 취소' : '이 후보 선택'}</button></div>`;
    }).join('')}</div></article>`).join('') || '<p class="muted">해당 조건의 후보군이 없습니다.</p>';
    h3UpdateMarkup(list, html);
    if (anchor?.isConnected) list.scrollTop += anchor.getBoundingClientRect().top - offset; else list.scrollTop = scroll;
    const page = out.pagination || {}; videoPage = page.page || 1;
    q('feedbackPageStatus').textContent = `${videoPage} / ${page.total_pages || 1} · 후보군 ${page.total || 0}개`;
    q('feedbackPrevious').disabled = videoPage <= 1; q('feedbackNext').disabled = videoPage >= (page.total_pages || 1);
    list.querySelectorAll('[data-feedback-job]').forEach(button => button.onclick = () => {
      const job = jobs.get(button.dataset.feedbackJob);
      if (job) play(job);
    });
    list.querySelectorAll('[data-feedback-select-job]').forEach(button => button.onclick = () => {
      changeSelection(button.dataset.feedbackSelectSet, button.dataset.feedbackSelectJob, button.getAttribute('aria-pressed') === 'true');
    });
  }
  function play(job, time = null) {
    if (job.status?.status !== 'completed') { status('완료된 영상만 재생할 수 있습니다.'); return; }
    const player = q('feedbackVideo'), same = currentVideo?.job_id === job.job_id;
    currentVideo = job; player.hidden = false; q('feedbackVideoEmpty').hidden = true;
    q('feedbackVideoTitle').textContent = `${job.request?.source_clip_id || '영상'} (후보 ${job.request?.candidate_index || '-'})`;
    q('feedbackVideoMeta').textContent = [job.request?.source_project_id, job.request?.source_scene_id, job.request?.source_clip_id, `후보 ${job.request?.candidate_index || '-'}`, `Seed ${job.request?.seed ?? '-'}`, job.job_id].filter(Boolean).join(' · ');
    editorControls();
    if (!same) {
      player.pause(); player.src = `/api/h3/jobs/${encodeURIComponent(job.job_id)}/video`;
      player.onloadedmetadata = () => { player.currentTime = Math.max(0, Math.min(Number(time) || 0, player.duration || 0)); };
    } else if (time !== null) player.currentTime = Math.max(0, Math.min(time, player.duration || time));
    player.play().catch(() => {});
    q('feedbackCandidateList').querySelectorAll('[data-feedback-job]').forEach(el => el.classList.toggle('is-current', el.dataset.feedbackJob === job.job_id));
  }
  async function openBookmark(url) {
    const id = url.searchParams.get('feedback_job');
    if (!id) return;
    const context = await api(`/api/h3/jobs/${encodeURIComponent(id)}/feedback-context`);
    play(context, Number(url.searchParams.get('feedback_time')) || 0);
  }
  async function start() {
    mountNotebook();
    document.body.classList.toggle('feedback-page', visible()); resize();
    if (!notesVisible()) return;
    const tab = document.querySelector('nav button[data-page="feedback"]'), nav = tab?.parentElement;
    if (nav && nav.scrollWidth > nav.clientWidth) nav.scrollLeft += tab.getBoundingClientRect().left - nav.getBoundingClientRect().left - (nav.clientWidth - tab.offsetWidth) / 2;
    if (visible()) await refreshVideos().catch(error => { q('feedbackPageStatus').textContent = error.message; });
    await refreshLibrary().catch(error => { renderLibrary(); status(error.message + ' · 이 기기의 임시 초안도 확인할 수 있습니다.', 'error'); });
    if (!started) {
      started = true;
      const id = storageGet(LAST);
      if (id) await openNote(id).catch(error => status(error.message, 'error'));
    }
    if (initialBookmark && visible()) { initialBookmark = false; await openBookmark(new URL(location.href)).catch(error => status(error.message, 'error')); }
  }
  function resize() {
    if (!visible()) return;
    const height = window.visualViewport?.height || innerHeight;
    q('feedbackWorkspace').style.setProperty('--feedback-workspace-height', Math.max(350, height - q('feedbackWorkspace').getBoundingClientRect().top - 12) + 'px');
  }
  function handler(fn) { return (...args) => { try { return Promise.resolve(fn(...args)).catch(error => status(error.message, 'error')); } catch (error) { status(error.message, 'error'); } }; }
  q('feedbackNew').onclick = handler(() => createNote());
  q('feedbackNoteList').onchange = handler(event => openNote(event.target.value));
  q('feedbackNoteSearch').oninput = renderLibrary;
  q('feedbackShowArchived').onchange = handler(refreshLibrary);
  q('feedbackNoteTitle').oninput = changed; q('feedbackNoteBody').oninput = changed;
  q('feedbackSave').onclick = handler(async () => { await save(); markStatus(); });
  q('feedbackPreview').onclick = () => { preview = !preview; togglePreview(); };
  notebook.querySelectorAll('[data-feedback-prefix]').forEach(button => button.onclick = () => insertText(button.dataset.feedbackPrefix, true));
  q('feedbackNotePreview').onchange = event => {
    if (!event.target.matches('[data-feedback-check]') || !active || active.archived) return;
    if (active.locked) { renderPreview(); return; }
    const lines = active.body.split('\n'), index = Number(event.target.dataset.feedbackCheck);
    lines[index] = lines[index].replace(/\[([ xX])\]/, event.target.checked ? '[x]' : '[ ]');
    q('feedbackNoteBody').value = lines.join('\n'); changed();
  };
  q('feedbackNotePreview').onclick = handler(async event => {
    const link = event.target.closest('a');
    if (!link) return;
    const url = new URL(link.href);
    if (url.origin === location.origin && url.searchParams.has('feedback_job')) { event.preventDefault(); if (!visible()) goPage('feedback'); await openBookmark(url); }
  });
  for (const id of ['feedbackEpisode', 'feedbackProject', 'feedbackScene', 'feedbackClip']) q(id).onchange = handler(async () => {
    if (id === 'feedbackEpisode') q('feedbackProject').value = '';
    if (id === 'feedbackEpisode' || id === 'feedbackProject') { q('feedbackScene').value = ''; q('feedbackClip').value = ''; }
    if (id === 'feedbackScene') q('feedbackClip').value = '';
    updateFilters(); videoPage = 1; await refreshVideos();
  });
  q('feedbackRefreshVideos').onclick = handler(refreshVideos);
  q('feedbackPrevious').onclick = handler(() => { videoPage = Math.max(1, videoPage - 1); return refreshVideos(); });
  q('feedbackNext').onclick = handler(() => { videoPage++; return refreshVideos(); });
  const fontSize = q('feedbackFontSize');
  function setFontSize() {
    const value = Number(fontSize.value);
    const size = Number.isInteger(value) && value >= 10 && value <= 24 ? String(value) : '20';
    fontSize.value = size;
    q('feedbackWorkspace').style.setProperty('--feedback-font-size', size + 'px');
    notebook.style.setProperty('--feedback-font-size', size + 'px');
    try { localStorage.setItem('h3-feedback-font-size', size); } catch {}
  }
  fontSize.value = storageGet('h3-feedback-font-size') || '20';
  fontSize.onchange = setFontSize; setFontSize();
  const menus = [...notebook.querySelectorAll('.feedback-menu')];
  function closeMenus(except = null) { menus.forEach(menu => { if (menu !== except) menu.open = false; }); }
  for (const menu of menus) {
    menu.querySelector('summary').addEventListener('click', () => closeMenus(menu));
    menu.addEventListener('click', event => {
      if (event.target.closest('button')) closeMenus();
    });
  }
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('.feedback-menu')) closeMenus();
  }, {passive: true});
  document.addEventListener('focusin', event => {
    if (!event.target.closest('.feedback-menu')) closeMenus();
  });
  notebook.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const open = menus.find(menu => menu.open);
    if (open) { closeMenus(); open.querySelector('summary').focus({preventScroll: true}); event.stopPropagation(); }
  });
  q('feedbackInsertReference').onclick = () => {
    if (!currentVideo) return;
    const time = Number(q('feedbackVideo').currentTime || 0).toFixed(2), request = currentVideo.request || {};
    const url = new URL(location.pathname, location.origin);
    url.searchParams.set('feedback_job', currentVideo.job_id); url.searchParams.set('feedback_time', time); url.hash = 'feedback';
    insertText(`[${[request.source_project_id, request.source_scene_id, request.source_clip_id, `후보 ${request.candidate_index || '-'}`, `${time}초`].filter(Boolean).join(' / ')}](${url.pathname + url.search + url.hash})\n`);
  };
  q('feedbackExport').onclick = () => {
    if (!active) return;
    const blob = new Blob([`# ${active.title}\n\n${active.body}`], {type: 'text/markdown;charset=utf-8'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = titleOf(active).replace(/[\\/:*?"<>|]/g, '_') + '.md';
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  async function toggleArchive(editAfter = false) {
    if (!active) return;
    const doc = active;
    if (!confirm(doc.archived ? '이 노트를 보관 해제할까요?' : '노트를 보관할까요? 본문과 수정 이력은 유지됩니다.')) return;
    await save(doc);
    if (dirty(doc) || doc.conflict) throw Error('저장 충돌을 해결한 뒤 보관 상태를 변경하세요.');
    doc.locked = true;
    editorControls();
    if (active === doc) { q('feedbackNoteTitle').readOnly = true; q('feedbackNoteBody').readOnly = true; }
    try {
      const out = await api('/api/feedback-notes/' + doc.note_id, {method: 'PUT', headers: {'content-type': 'application/json'}, body: JSON.stringify({expected_revision: doc.revision, archived: !doc.archived})});
      Object.assign(doc, asDocument(out)); if (active === doc) applyDocument(doc); await refreshLibrary();
    } catch (error) {
      if (error.status === 409) { doc.conflict = error.body?.current || {}; persist(doc); markStatus(doc); }
      throw error;
    } finally {
      doc.locked = false;
      editorControls();
      if (active === doc) { q('feedbackNoteTitle').readOnly = doc.archived; q('feedbackNoteBody').readOnly = doc.archived; }
    }
    if (editAfter && active === doc && !doc.archived) {
      preview = false; renderPreview();
      q('feedbackNoteBody').focus({preventScroll: true});
      status('편집 가능 · 입력 내용은 자동 저장됩니다.');
    }
  }
  q('feedbackArchive').onclick = handler(() => toggleArchive());
  q('feedbackEditArchived').onclick = handler(() => active?.archived && toggleArchive(true));
  q('feedbackCopyConflict').onclick = handler(() => createNote(active));
  q('feedbackReloadServer').onclick = handler(async () => {
    if (!active || !confirm('현재 초안 대신 서버에 저장된 내용을 불러올까요? 내 초안을 남기려면 먼저 새 노트로 저장하세요.')) return;
    const record = await api('/api/feedback-notes/' + active.note_id); forgetDraft(active); applyDocument(asDocument(record));
  });
  async function showRecord(record, noteId, canRestore) {
    historyRecord = record; historyNote = noteId;
    q('feedbackRevisionBody').textContent = `${record.title}\n\n${record.body}`;
    q('feedbackRestoreRevision').hidden = !canRestore;
  }
  q('feedbackShowServer').onclick = handler(async () => {
    if (!active) return;
    const record = await api('/api/feedback-notes/' + active.note_id);
    q('feedbackRevisionList').hidden = true;
    await showRecord(record, active.note_id, false); q('feedbackHistoryDialog').showModal();
  });
  q('feedbackHistory').onclick = handler(async () => {
    if (!active) return;
    const doc = active;
    await save(doc);
    if (active !== doc) return;
    const id = doc.note_id, out = await api('/api/feedback-notes/' + id + '/history');
    if (active !== doc) return;
    q('feedbackRevisionList').hidden = false;
    q('feedbackRevisionList').innerHTML = (out.revisions || []).map(r => `<option value="${r.revision}">${escape(date(r.updated_at))} · ${escape(r.title)}</option>`).join('');
    historyNote = id;
    const record = await api(`/api/feedback-notes/${id}/revisions/${q('feedbackRevisionList').value}`);
    await showRecord(record, id, !active.archived && !active.conflict); q('feedbackHistoryDialog').showModal();
  });
  q('feedbackRevisionList').onchange = handler(async () => {
    const record = await api(`/api/feedback-notes/${historyNote}/revisions/${q('feedbackRevisionList').value}`);
    await showRecord(record, historyNote, !active?.archived && !active?.conflict);
  });
  q('feedbackRestoreRevision').onclick = handler(async () => {
    if (!historyRecord || active?.note_id !== historyNote || !confirm('선택한 내용으로 새 버전을 저장할까요? 기존 이력은 유지됩니다.')) return;
    q('feedbackNoteTitle').value = historyRecord.title; q('feedbackNoteBody').value = historyRecord.body;
    changed(); await save(); if (!active.conflict) q('feedbackHistoryDialog').close();
  });
  q('feedbackHistoryClose').onclick = () => q('feedbackHistoryDialog').close();
  q('feedbackVideo').addEventListener('error', () => {
    if (currentVideo) q('feedbackVideoMeta').textContent = '영상을 불러올 수 없습니다. 생성 기록을 확인하세요. 노트 내용은 유지됩니다.';
  });
  window.addEventListener('h3-page-change', () => { document.body.classList.toggle('feedback-page', visible()); start().catch(error => status(error.message, 'error')); });
  window.addEventListener('h3-feedback-refresh', () => { clearTimeout(videoTimer); if (visible()) videoTimer = setTimeout(() => refreshVideos().catch(error => { q('feedbackPageStatus').textContent = error.message; }), 600); });
  window.addEventListener('resize', resize); window.visualViewport?.addEventListener('resize', resize);
  window.addEventListener('online', () => { for (const doc of documents.values()) if (dirty(doc) && !doc.conflict) save(doc).catch(() => {}); if (notesVisible()) refreshLibrary().catch(() => {}); });
  window.addEventListener('beforeunload', event => { if ([...documents.values()].some(dirty)) { event.preventDefault(); event.returnValue = ''; } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) for (const doc of documents.values()) if (dirty(doc)) { persist(doc); save(doc).catch(() => {}); } });
  editorControls();
  start().catch(error => status(error.message, 'error'));
})();
