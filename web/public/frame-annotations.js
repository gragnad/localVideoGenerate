/* Frame review stays in memory while editing; persisted exclusively on the server. */
(() => {
  const dialog = document.querySelector('#frameAnnotationDialog');
  const canvas = dialog.querySelector('canvas');
  const stage = dialog.querySelector('.frame-annotation-stage');
  const ctx = canvas.getContext('2d');
  const q = selector => dialog.querySelector(selector);
  let session = null, timer = null, pending = null, busy = false;
  let scale = 1, pan = {x: 0, y: 0}, fit = 1;
  const pointers = new Map();
  const copy = value => JSON.parse(JSON.stringify(value));
  const status = value => { q('[data-status]').textContent = value; };
  const endpoint = (s, frame) => `/api/h3/jobs/${encodeURIComponent(s.jobId)}/frames/${encodeURIComponent(s.tag)}/${encodeURIComponent(frame.filename)}/annotation`;
  async function request(url, options) {
    const response = await fetch(url, {cache: 'no-store', ...options});
    const body = await response.json();
    if (!response.ok) throw Error(body.error || '서버 요청 실패');
    return body;
  }
  function controls() {
    q('[data-prev]').disabled = busy || !session || session.index === 0;
    q('[data-next]').disabled = busy || !session || session.index === session.frames.length - 1;
    q('[data-undo]').disabled = busy || !session?.undo.length;
    q('[data-redo]').disabled = busy || !session?.redo.length;
    q('[data-save]').disabled = busy || !session?.image;
    q('[data-close]').disabled = busy;
    q('[data-server-version]').hidden = !session?.conflict;
    q('[data-image]').hidden = !session?.imageUrl;
    q('[data-image]').href = session?.imageUrl || '#';
  }
  function transform() {
    if (!session?.image) return;
    fit = Math.min(stage.clientWidth / canvas.width, stage.clientHeight / canvas.height);
    canvas.style.width = `${canvas.width * fit}px`;
    canvas.style.height = `${canvas.height * fit}px`;
    canvas.style.transform = `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${scale})`;
  }
  function draw() {
    if (!session?.image) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(session.image, 0, 0);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const stroke of session.strokes) {
      ctx.strokeStyle = ctx.fillStyle = stroke.color;
      ctx.lineWidth = Math.max(1, Math.round(stroke.width * canvas.width));
      ctx.beginPath();
      stroke.points.forEach(([x, y], i) => {
        const px = Math.round(x * (canvas.width - 1)), py = Math.round(y * (canvas.height - 1));
        if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py);
      });
      ctx.stroke();
      for (const [x, y] of [stroke.points[0], stroke.points.at(-1)]) {
        ctx.beginPath(); ctx.arc(Math.round(x * (canvas.width - 1)), Math.round(y * (canvas.height - 1)), ctx.lineWidth / 2, 0, Math.PI * 2); ctx.fill();
      }
    }
  }
  function checkpoint() {
    session.undo.push(copy(session.strokes));
    if (session.undo.length > 100) session.undo.shift();
    session.redo = [];
  }
  function changed() {
    session.version++;
    status('미저장 · 자동 저장 대기'); controls();
    clearTimeout(timer); timer = setTimeout(() => save().catch(() => {}), 900);
  }
  async function save() {
    clearTimeout(timer);
    if (pending) { await pending; return save(); }
    if (!session || session.version === session.savedVersion) return;
    if (session.active != null) throw Error('펜을 뗀 뒤 저장하세요.');
    const s = session, version = s.version, strokes = copy(s.strokes);
    status('서버 저장 중…');
    pending = (async () => {
      try {
        const out = await request(endpoint(s, s.frames[s.index]), {method: 'PUT', headers: {'content-type': 'application/json'}, body: JSON.stringify({strokes, expected_revision: s.revision})});
        s.revision = out.revision; s.savedVersion = version; s.imageUrl = out.image_url;
        if (session === s) {
          status(s.active != null ? '그리는 중 · 미저장' : s.version === version ? `서버 저장 완료 · ${new Date(out.saved_at).toLocaleTimeString()}` : '미저장 · 추가 변경 저장 대기');
          window.dispatchEvent(new CustomEvent('h3-frame-annotation-saved', {detail: {jobId: s.jobId, filename: s.frames[s.index].filename}}));
          controls();
        }
      } catch (error) {
        if (session === s) {
          s.conflict = error.message.includes('다른 화면');
          status(`미저장 · ${error.message} · 서버 저장 버튼으로 재시도`); controls();
        }
        throw error;
      } finally { pending = null; }
    })();
    await pending;
    if (session === s && s.version !== s.savedVersion) return save();
  }
  function loadImage(url) {
    return new Promise((resolve, reject) => {
      const image = new Image(); image.onload = () => resolve(image);
      image.onerror = () => reject(Error('프레임 이미지를 열지 못했습니다.'));
      image.src = url;
    });
  }
  async function loadFrame(index) {
    busy = true; controls(); status('프레임과 서버 검수 기록을 불러오는 중…');
    const s = session, frame = s.frames[index];
    try {
      const base = `/api/h3/jobs/${encodeURIComponent(s.jobId)}/frames/${encodeURIComponent(s.tag)}/`;
      const [record, image] = await Promise.all([
        request(endpoint(s, frame)), loadImage(base + encodeURIComponent(frame.labeled_filename || frame.filename)),
      ]);
      s.index = index; s.image = image; s.strokes = record.strokes; s.revision = record.revision;
      s.version = s.savedVersion = 0; s.undo = []; s.redo = []; s.imageUrl = record.image_url; s.conflict = false;
      canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
      scale = 1; pan = {x: 0, y: 0}; pointers.clear();
      q('[data-title]').textContent = frame.label_text || `${s.title} · ${Number(frame.time_seconds).toFixed(2)}초 · f${frame.frame_index}`;
      q('[data-position]').textContent = `${index + 1} / ${s.frames.length}`;
      draw(); transform(); status(record.revision ? '서버 검수 기록 불러옴' : '표시할 부분을 펜슬로 그리세요.');
    } finally { busy = false; controls(); }
  }
  async function navigate(delta) {
    if (busy || session.active != null) return;
    busy = true; controls();
    try { await save(); await loadFrame(session.index + delta); }
    catch (error) { status(`이동하지 않았습니다 · ${error.message}`); }
    finally { busy = false; controls(); }
  }
  async function close() {
    if (busy || session?.active != null) return;
    busy = true; controls();
    try { await save(); dialog.close(); session = null; pointers.clear(); }
    catch (error) { status(`닫지 않았습니다 · ${error.message}`); }
    finally { busy = false; controls(); }
  }
  function point(event) {
    const rect = canvas.getBoundingClientRect();
    return [Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))];
  }
  function erase(at) {
    const radius = 14 / (fit * scale);
    const px = at[0] * canvas.width, py = at[1] * canvas.height;
    session.strokes = session.strokes.filter(stroke => {
      const points = stroke.points.map(([x,y]) => [x*canvas.width,y*canvas.height]);
      for (let i = 0; i < points.length; i++) {
        const a = points[i], b = points[Math.min(i+1, points.length-1)];
        const dx=b[0]-a[0],dy=b[1]-a[1],len=dx*dx+dy*dy;
        const t=len ? Math.max(0,Math.min(1,((px-a[0])*dx+(py-a[1])*dy)/len)) : 0;
        if (Math.hypot(px-a[0]-t*dx,py-a[1]-t*dy) <= radius + stroke.width*canvas.width/2) return false;
      }
      return true;
    });
  }
  function zoom(next, x, y) {
    next = Math.max(1, Math.min(8, next));
    const rect = stage.getBoundingClientRect(), factor = next / scale;
    pan.x = (x - rect.left - rect.width/2) * (1-factor) + pan.x*factor;
    pan.y = (y - rect.top - rect.height/2) * (1-factor) + pan.y*factor;
    scale = next; transform();
  }
  stage.addEventListener('pointerdown', event => {
    if (busy || !session?.image) return;
    event.preventDefault(); stage.setPointerCapture(event.pointerId);
    const drawInput = event.pointerType !== 'touch' || q('[data-finger]').checked;
    if (drawInput && q('[data-tool]').value !== 'move' && session.active == null && (event.pointerType === 'pen' || pointers.size === 0)) {
      pointers.clear(); checkpoint(); session.active = event.pointerId; status('그리는 중 · 미저장');
      const at = point(event);
      if (q('[data-tool]').value === 'erase') { session.drawing = null; erase(at); }
      else {
        session.drawing = {color: q('[data-color]').value, width: Number(q('[data-width]').value)/1000, points: [at]};
        session.strokes.push(session.drawing);
      }
      clearTimeout(timer); draw();
    } else if (session.active == null) pointers.set(event.pointerId, {x:event.clientX, y:event.clientY});
  });
  stage.addEventListener('pointermove', event => {
    if (busy || !session?.image) return;
    if (session.active === event.pointerId) {
      const samples = event.getCoalescedEvents?.() || [];
      for (const sample of samples.length ? samples : [event]) {
        const at = point(sample);
        if (session.drawing) {
          const last = session.drawing.points.at(-1);
          if (Math.hypot(at[0]-last[0],at[1]-last[1]) > .0003) session.drawing.points.push(at);
        } else erase(at);
      }
      draw(); return;
    }
    if (!pointers.has(event.pointerId)) return;
    const before = [...pointers.values()];
    pointers.set(event.pointerId, {x:event.clientX, y:event.clientY});
    const after = [...pointers.values()];
    if (before.length === 1) {pan.x += after[0].x-before[0].x;pan.y += after[0].y-before[0].y;}
    else {
      const mid = p => ({x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2});
      const a=mid(before),b=mid(after),distance=p=>Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y);
      zoom(scale*distance(after)/Math.max(1,distance(before)),a.x,a.y);
      pan.x += b.x-a.x;pan.y += b.y-a.y;
    }
    transform();
  });
  function finish(event) {
    pointers.delete(event.pointerId);
    if (session?.active === event.pointerId) {session.active = null; session.drawing = null; changed();}
  }
  stage.addEventListener('pointerup', finish); stage.addEventListener('pointercancel', finish);
  stage.addEventListener('lostpointercapture', finish);
  stage.addEventListener('wheel', event => {
    if (!session?.image || busy) return;
    event.preventDefault();zoom(scale*Math.exp(-event.deltaY*.002),event.clientX,event.clientY);
  }, {passive: false});
  new ResizeObserver(transform).observe(stage);
  q('[data-prev]').onclick = () => navigate(-1);
  q('[data-next]').onclick = () => navigate(1);
  q('[data-save]').onclick = () => save().catch(() => {});
  q('[data-close]').onclick = close;
  q('[data-fit]').onclick = () => {scale=1;pan={x:0,y:0};transform();};
  q('[data-server-version]').onclick = async () => {
    if (!confirm('현재 미저장 표시를 버리고 서버에 저장된 기록을 불러올까요?')) return;
    clearTimeout(timer);
    try {await loadFrame(session.index);} catch(error) {status(error.message);}
  };
  for (const [selector, from, to] of [['[data-undo]','undo','redo'],['[data-redo]','redo','undo']]) {
    q(selector).onclick = () => {
      if (busy || session.active != null || !session[from].length) return;
      session[to].push(copy(session.strokes));session.strokes=session[from].pop();draw();changed();
    };
  }
  dialog.addEventListener('cancel', event => {event.preventDefault();close();});
  window.addEventListener('beforeunload', event => {
    if (session && (session.active != null || session.version !== session.savedVersion)) {event.preventDefault();event.returnValue='';}
  });
  window.addEventListener('online', () => {if(session && !session.conflict) save().catch(()=>{});});
  document.addEventListener('visibilitychange', () => {if(document.hidden && session && session.active == null) save().catch(()=>{});});
  window.H3FrameAnnotator = {
    async open(options) {
      if (dialog.open) return;
      session = {...options, index: 0, strokes: [], undo: [], redo: [], version: 0, savedVersion: 0};
      dialog.showModal();
      try {await loadFrame(options.index);} catch(error) {status(error.message);}
    },
  };
})();
