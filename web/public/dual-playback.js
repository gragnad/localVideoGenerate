/* Explicit pair controls. Native independent playback remains available when linking is off. */
window.H3DualPlayback = class {
  constructor(root, videos) {
    this.root = root; this.videos = videos; this.running = false; this.guard = false; this.ticket = 0; this.pendingSeeks = new WeakMap();
    this.resetSync();
    root.innerHTML = `<div class="dual-main"><label><input type="checkbox" data-dual="link"> 재생 연결</label>
      <button type="button" data-dual="play">▶ 함께 재생</button><button type="button" data-dual="pause">함께 정지</button>
      <label>소리<select data-dual="audio"><option value="0">왼쪽만</option><option value="1">오른쪽만</option><option value="none">모두 끄기</option></select></label>
      <span data-dual="time">양쪽 후보를 선택하세요.</span></div>
      <input type="range" data-dual="seek" min="0" max="1000" value="0" aria-label="양쪽 영상 같은 위치로 이동">
      <details><summary>시간 기준 · 구간 반복</summary><div class="dual-settings-panel"><div class="dual-options">
      <label>시간 기준<select data-dual="mode"><option value="seconds">같은 초 (짧은 영상까지)</option><option value="ratio">전체 길이 대비 같은 위치</option></select></label>
      <label>시작(초)<input data-dual="from" type="number" min="0" step="0.1" value="0"></label>
      <label>끝(초)<input data-dual="to" type="number" min="0" step="0.1" placeholder="영상 끝"></label>
      <button type="button" data-dual="markFrom">현재 위치 → 시작</button><button type="button" data-dual="markTo">현재 위치 → 끝</button>
      <label><input type="checkbox" data-dual="loop"> 구간 반복</label></div><small>구간은 왼쪽 영상 시간 기준입니다. 연결을 켜면 기본 재생기의 재생·정지·탐색도 양쪽에 적용됩니다.</small></div></details>
      <p data-dual="status" role="status" aria-live="polite"></p>`;
    this.q = name => root.querySelector(`[data-dual="${name}"]`);
    this.q('play').onclick = () => { this.q('link').checked = true; this.play(); };
    this.q('pause').onclick = () => this.stop();
    this.q('seek').oninput = () => this.seek(Number(this.q('seek').value) / 1000 * this.limit());
    this.q('mode').onchange = () => { this.stop(); this.seek(0); this.update(); };
    this.q('audio').onchange = () => this.audio();
    this.q('link').onchange = () => this.stop();
    this.q('markFrom').onclick = () => { this.q('from').value = videos[0].currentTime.toFixed(1); };
    this.q('markTo').onclick = () => { this.q('to').value = videos[0].currentTime.toFixed(1); };
    for (const [index, video] of videos.entries()) {
      for (const name of ['loadedmetadata', 'durationchange', 'error']) video.addEventListener(name, () => {
        if (video.error) { this.stop(); this.message('한쪽 영상을 불러오지 못했습니다. 후보를 다시 선택하세요.'); }
        this.update();
      });
      video.addEventListener('emptied', () => { this.stop(); this.update(); });
      video.addEventListener('play', () => {
        if (!this.active()) { video.pause(); return; }
        if (video.paused) return; // Ignore a queued play event delivered after a newer stop.
        if (!this.guard && !this.running && this.q('link').checked && this.ready()) { this.seek(this.leftTime(index)); this.play(); }
      });
      video.addEventListener('pause', () => { if (!this.guard && this.running && video.paused && !video.ended) this.stop(); });
      video.addEventListener('seeking', () => {
        const pending = this.pendingSeeks.get(video);
        // A queued programmatic event can arrive after playback has advanced slightly, but a new
        // user scrub during that seek must still propagate. "seeking" alone cannot distinguish them.
        const tolerance = pending ? .08 + Math.min(.25, Math.max(0, performance.now() - pending.at) / 1000 * Math.max(1, video.playbackRate)) : 0;
        if (pending && Math.abs(video.currentTime - pending.time) < tolerance) return;
        this.pendingSeeks.delete(video);
        if (this.q('link').checked && this.ready() && !this.guard) this.seek(this.leftTime(index), index);
      });
      video.addEventListener('seeked', () => this.pendingSeeks.delete(video));
      video.addEventListener('ended', () => {
        if (!this.running) return;
        if (this.q('loop').checked && this.range()) { this.seek(this.range()[0]); this.play(); }
        else this.stop();
      });
      video.addEventListener('timeupdate', () => { if (!this.running) this.update(); });
      video.addEventListener('volumechange', () => this.audio());
      video.addEventListener('waiting', () => {
        if (this.running && !video.seeking && video.readyState < 3) { this.stop(); this.message('한쪽 영상이 버퍼링 중이라 양쪽을 정지했습니다. 준비 후 함께 재생을 누르세요.'); }
      });
    }
    this.audio(); this.update();
  }
  active() { return !document.hidden && !this.root.closest('[data-view]')?.hidden; }
  ready() { return this.active() && this.videos.every(v => !v.hidden && v.getAttribute('src') && v.readyState >= 1 && Number.isFinite(v.duration) && v.duration > 0 && !v.error); }
  limit() { return this.ready() ? (this.q('mode').value === 'ratio' ? this.videos[0].duration : Math.min(...this.videos.map(v => v.duration))) : 0; }
  leftTime(index) { return index && this.q('mode').value === 'ratio' ? this.videos[1].currentTime / this.videos[1].duration * this.videos[0].duration : this.videos[index].currentTime; }
  target(time, index) { return index && this.q('mode').value === 'ratio' ? time / this.videos[0].duration * this.videos[1].duration : time; }
  message(text) { this.q('status').textContent = text; }
  range() {
    const start = Number(this.q('from').value), end = this.q('to').value === '' ? this.limit() : Number(this.q('to').value);
    return Number.isFinite(start) && Number.isFinite(end) && start >= 0 && end <= this.limit() + .01 && end > start + .05 ? [start, Math.min(end, this.limit())] : null;
  }
  seek(time, source = -1) {
    if (!this.ready()) return;
    time = Math.max(0, Math.min(this.limit(), time));
    this.guard = true;
    this.videos.forEach((v, i) => {
      const target = this.target(time, i);
      if (i !== source && Math.abs(v.currentTime - target) > .06) { this.pendingSeeks.set(v, {time: target, at: performance.now()}); v.currentTime = target; }
    });
    this.guard = false; this.update();
    this.driftSince = null; this.lastSyncAt = -Infinity;
  }
  resetSync() {
    this.lastSyncAt = -Infinity; this.lastUiAt = -Infinity;
    this.lastHardSeekAt = -Infinity; this.driftSince = null;
  }
  syncFollower(time, now) {
    // currentTime writes flush the decoder. A small drift must not become a seek/stall feedback loop.
    if (now - this.lastSyncAt < 250 || this.videos.some(v => v.seeking || v.readyState < 2)) return;
    this.lastSyncAt = now;
    const [leader, follower] = this.videos;
    const scale = this.q('mode').value === 'ratio' ? follower.duration / leader.duration : 1;
    const drift = (this.target(time, 1) - follower.currentTime) / scale;
    if (Math.abs(drift) > 1) {
      if (this.driftSince === null) this.driftSince = now;
      // Only a sustained, large error justifies a discontinuity. Never re-seek on each frame.
      if (now - this.driftSince >= 1000 && now - this.lastHardSeekAt >= 3000) {
        this.seek(time, 0); this.lastHardSeekAt = now;
      }
    } else this.driftSince = null;
    const correction = Math.abs(drift) > .08 ? Math.max(-.05, Math.min(.05, drift * .25)) : 0;
    const rate = Math.max(.0625, Math.min(16, leader.playbackRate * scale * (1 + correction)));
    if (Math.abs(follower.playbackRate - rate) > .002) follower.playbackRate = rate;
  }
  audio() {
    if (this.audioGuard) return;
    this.audioGuard = true;
    this.videos.forEach((video, i) => { const muted = this.q('audio').value !== String(i); if (video.muted !== muted) video.muted = muted; });
    this.audioGuard = false;
  }
  async play() {
    if (!this.ready()) return this.message('양쪽 영상이 준비된 뒤 함께 재생을 눌러주세요.');
    const range = this.range();
    if (this.q('loop').checked && !range) { this.stop(); return this.message('반복 시작·끝을 확인하세요. 왼쪽 기준 0초부터 ' + this.limit().toFixed(1) + '초 사이여야 합니다.'); }
    const ticket = ++this.ticket;
    this.running = true; this.audio();
    const current = this.videos[0].currentTime;
    this.seek(range && this.q('loop').checked && (current < range[0] || current >= range[1]) ? range[0] : current >= this.limit() - .05 ? 0 : current);
    this.guard = true;
    const promises = this.videos.map(v => v.play()); // Same user gesture, including iPad inline video.
    this.guard = false;
    try {
      await Promise.all(promises);
      if (ticket !== this.ticket) { if (!this.running) this.videos.forEach(v => v.pause()); return; }
      this.message('연결 재생 중'); this.tick();
    } catch {
      if (ticket !== this.ticket) return;
      this.stop(); this.message('브라우저가 재생을 허용하지 않았습니다. 양쪽 영상 준비 후 함께 재생을 다시 누르세요.');
    }
  }
  tick() {
    cancelAnimationFrame(this.frame);
    if (!this.running) return;
    if (document.hidden || !this.ready()) { this.stop(); return; }
    const time = this.videos[0].currentTime, range = this.range();
    if (this.q('loop').checked && !range) { this.stop(); this.message('반복 구간을 확인하세요.'); return; }
    if (time >= (this.q('loop').checked ? range[1] : this.limit()) - .04) {
      if (this.q('loop').checked) this.seek(range[0]); else { this.stop(); return; }
    } else this.syncFollower(time, performance.now());
    // Keep the frame loop for range boundaries, but do not rewrite controls/rates at display FPS.
    const now = performance.now();
    if (now - this.lastUiAt >= 100) { this.update(); this.lastUiAt = now; }
    this.frame = requestAnimationFrame(() => this.tick());
  }
  stop() {
    this.running = false; this.ticket++; cancelAnimationFrame(this.frame); this.guard = true;
    this.videos.forEach(v => { v.pause(); if (v.playbackRate !== 1) v.playbackRate = 1; }); this.guard = false;
    this.resetSync();
  }
  changed() { this.stop(); this.pendingSeeks = new WeakMap(); this.q('from').value = '0'; this.q('to').value = ''; this.q('loop').checked = false; this.message(''); this.update(); }
  update() {
    const ready = this.ready();
    for (const name of ['play', 'seek', 'markFrom', 'markTo']) this.q(name).disabled = !ready;
    if (ready) {
      const time = this.videos[0].currentTime, max = this.limit();
      this.q('seek').value = String(Math.round(time / max * 1000));
      this.q('time').textContent = `${time.toFixed(1)} / ${max.toFixed(1)}초 (왼쪽 기준)`;
    } else this.q('time').textContent = '양쪽 후보를 선택하세요.';
  }
};
