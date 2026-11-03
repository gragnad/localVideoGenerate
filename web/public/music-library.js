(() => {
  const section = document.querySelector('[data-view="music"]');
  if (!section) return;
  const q = id => document.getElementById('music' + id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  let page = 1, pages = 1, ticket = 0;
  const visible = () => !section.hidden;
  let intendedAudio = null;
  const previewError = '미리듣기를 불러오지 못했습니다. 파일이 없거나 이 브라우저가 지원하지 않는 형식일 수 있습니다. 원본 다운로드를 확인하세요.';
  const players = () => [...q('List').querySelectorAll('audio')];
  function previewState(audio) {
    const button = audio.closest('.music-card')?.querySelector('[data-music-preview]');
    if (button) { button.textContent = audio.paused ? '▶ 미리듣기' : 'Ⅱ 일시정지'; button.setAttribute('aria-pressed', String(!audio.paused)); }
    if (audio.error) audio.closest('.music-card').querySelector('.music-preview-status').textContent = previewError;
  }
  function stopPreviews() { intendedAudio = null; players().forEach(audio => { audio.pause(); previewState(audio); }); }
  q('List').addEventListener('play', event => {
    const audio = event.target;
    if (audio.tagName !== 'AUDIO' || audio.paused) return;
    if (!visible() || document.hidden) { audio.pause(); return; }
    intendedAudio = audio;
    players().forEach(other => { if (other !== audio) { other.pause(); previewState(other); } });
    audio.closest('.music-card').querySelector('.music-preview-status').textContent = '';
    previewState(audio);
  }, true);
  for (const event of ['pause', 'ended']) q('List').addEventListener(event, event => { if (event.target.tagName === 'AUDIO') previewState(event.target); }, true);
  q('List').addEventListener('error', event => {
    if (event.target.tagName === 'AUDIO') event.target.closest('.music-card').querySelector('.music-preview-status').textContent = previewError;
  }, true);
  q('List').addEventListener('click', event => {
    const button = event.target.closest('[data-music-preview]');
    if (!button) return;
    const audio = button.closest('.music-card').querySelector('audio');
    if (!audio.paused) { intendedAudio = null; audio.pause(); return; }
    intendedAudio = audio;
    players().forEach(other => { if (other !== audio) other.pause(); });
    if (audio.error) audio.load();
    audio.play().then(() => { if (!audio.isConnected || !visible() || document.hidden || intendedAudio !== audio) audio.pause(); }).catch(error => {
      if (error.name === 'AbortError') return;
      if (audio.isConnected && visible() && intendedAudio === audio) audio.closest('.music-card').querySelector('.music-preview-status').textContent = '재생하지 못했습니다. 미리듣기를 다시 누르거나 원본 다운로드를 이용하세요.';
    });
  });
  const row = (label, value) => value === '' || value == null ? '' : `<div><dt>${escape(label)}</dt><dd>${escape(value)}</dd></div>`;
  function card(track) {
    const meta = track.metadata, audio = track.audio, seconds = Number(audio.duration_seconds), length = `${Math.floor(seconds / 60)}분 ${Math.floor(seconds % 60).toString().padStart(2, '0')}초`;
    const format = String(audio.filename).split('.').pop().toUpperCase();
    return `<article class="panel music-card" id="${escape(track.track_id)}"><div class="music-card-head"><h3>${escape(meta.title)}</h3><span class="pill">${escape(format)} · ${length}</span></div>
      <p class="music-description">${escape(meta.description)}</p>
      <div class="music-tags">${(meta.tags || []).map(tag => `<span>${escape(tag)}</span>`).join('')}</div>
      <dl class="music-info">${row('분위기', meta.mood)}${row('장르', meta.genre)}${row('악기', meta.instruments)}${row('사용 장면', meta.use_case)}${row('보컬', meta.instrumental === true ? '무보컬로 제작' : meta.instrumental === false ? '보컬 포함으로 제작' : '미기록')}${row('설정 BPM', meta.bpm)}</dl>
      <details><summary>제작 · 파일 상세 정보</summary><dl class="music-info">${row('모델', meta.model || '미기록')}${row('시드', meta.seed || '미기록')}${row('워크플로우', meta.workflow)}${row('생성일', meta.generated_at || '미기록')}${row('라이브러리 등록일', new Date(track.created_at).toLocaleString('ko-KR'))}${row('파일', `${format} · ${(audio.size_bytes / 1024 / 1024).toFixed(1)} MB · ${audio.sample_rate} Hz · ${audio.channels}채널`)}${row('라이선스 메모', meta.license_note)}</dl>${meta.prompt ? `<h4>생성 프롬프트</h4><pre>${escape(meta.prompt)}</pre>` : ''}<small>분위기·BPM·무보컬 여부는 제작자가 기록한 정보이며 자동 분석 결과가 아닙니다.</small></details>
      ${track.available ? `<div class="music-preview"><button type="button" data-music-preview="${escape(track.track_id)}" aria-pressed="false">▶ 미리듣기</button><audio id="music-preview-${escape(track.track_id)}" controls preload="none" src="/api/music-library/${encodeURIComponent(track.track_id)}/audio" aria-label="${escape(meta.title)} 미리듣기"></audio><p class="music-preview-status" role="status" aria-live="polite"></p></div><a class="music-download" href="/api/music-library/${encodeURIComponent(track.track_id)}/download" download>↓ 원본 다운로드 (${escape(format)})</a>` : '<p class="music-missing">등록된 원본 파일이 없습니다. 제작 세션에서 등록 상태를 확인하세요.</p>'}</article>`;
  }
  async function refresh() {
    if (!visible()) return;
    const current = ++ticket;
    q('Status').textContent = '음악 목록을 불러오는 중…'; q('Status').dataset.error = 'false';
    q('Previous').disabled = q('Next').disabled = true;
    try {
      const out = await api('/api/music-library?' + new URLSearchParams({q: q('Search').value.trim(), sort: q('Sort').value, page: String(page)}));
      if (current !== ticket || !visible()) return;
      page = out.pagination.page; pages = out.pagination.total_pages;
      const retained = new Set(out.tracks.filter(track => track.available).map(track => track.track_id));
      players().forEach(audio => { if (!retained.has(audio.closest('.music-card').id)) { if (intendedAudio === audio) intendedAudio = null; audio.pause(); } });
      h3UpdateMarkup(q('List'), out.tracks.map(card).join('') || '<div class="panel music-empty">' + (q('Search').value.trim() ? '검색 조건에 맞는 음악이 없습니다.' : '아직 등록된 음악이 없습니다. 다른 제작 세션에서 완성된 음악과 설명을 등록하면 여기에 표시됩니다.') + '</div>');
      players().forEach(previewState);
      q('Page').textContent = `${page} / ${pages} · ${out.pagination.total}곡`;
      q('Previous').disabled = page <= 1; q('Next').disabled = page >= pages;
      q('Status').textContent = `음악 ${out.pagination.total}곡 · 미리듣기와 원본 다운로드를 제공합니다.${out.invalid_count ? ` 읽을 수 없는 등록 정보 ${out.invalid_count}건이 있습니다. 원본은 보존되어 있으며 등록 파일 확인이 필요합니다.` : ''}`;
      q('Status').dataset.error = String(out.invalid_count > 0);
    } catch (error) {
      if (current !== ticket || !visible()) return;
      q('Status').textContent = '목록 조회 실패 · 이전 목록이 있다면 유지됩니다. 새로고침해 다시 확인하세요. ' + error.message;
      q('Status').dataset.error = 'true';
    }
  }
  q('SearchForm').onsubmit = event => { event.preventDefault(); page = 1; refresh(); };
  q('Sort').onchange = () => { page = 1; refresh(); };
  q('Refresh').onclick = refresh;
  q('Previous').onclick = () => { page = Math.max(1, page - 1); refresh(); };
  q('Next').onclick = () => { page = Math.min(pages, page + 1); refresh(); };
  window.addEventListener('h3-page-change', () => { if (visible()) refresh(); else { ticket++; stopPreviews(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopPreviews(); });
  window.addEventListener('pagehide', stopPreviews);
  refresh();
})();
