/* Resize existing panes without replacing the editor or the video player. */
(() => {
 function createSplitter({workspace, handle, range, key = 'h3-feedback-split', labels = ['영상', '노트']}) {
  if (!workspace || !handle || !range) return;
  const stacked = matchMedia('(max-width:600px)');
  const gutter = 16, minimumPane = 300;
  let preferred = 50, drag = null;
  try {
    const saved = Number(localStorage.getItem(key));
    if (Number.isFinite(saved) && saved >= 30 && saved <= 70) preferred = saved;
  } catch {}
  function limits() {
    const available = workspace.clientWidth - gutter;
    const min = available > 0 && !stacked.matches ? Math.min(50, Math.max(30, Math.ceil(minimumPane / available * 100))) : 30;
    return {min, max: 100 - min, available};
  }
  function apply() {
    const {min, max} = limits();
    const value = Math.max(min, Math.min(max, preferred));
    workspace.style.setProperty('--feedback-video-share', value + 'fr');
    workspace.style.setProperty('--feedback-note-share', (100 - value) + 'fr');
    range.min = min; range.max = max; range.value = value;
    handle.setAttribute('aria-valuemin', String(min));
    handle.setAttribute('aria-valuemax', String(max));
    handle.setAttribute('aria-valuenow', String(value));
    handle.setAttribute('aria-valuetext', `${labels[0]} ${value}% · ${labels[1]} ${100 - value}%`);
    handle.setAttribute('aria-disabled', String(stacked.matches));
    handle.tabIndex = stacked.matches ? -1 : 0;
  }
  function remember() { try { localStorage.setItem(key, String(preferred)); } catch {} }
  function set(value, persist = true) {
    const {min, max} = limits();
    preferred = Math.max(min, Math.min(max, Math.round(value)));
    apply();
    if (persist) remember();
  }
  function finish(event) {
    if (!drag || event && event.pointerId !== drag.id) return;
    const id = drag.id;
    drag = null;
    workspace.classList.remove('is-resizing');
    if (handle.hasPointerCapture(id)) handle.releasePointerCapture(id);
    remember();
  }
  handle.addEventListener('pointerdown', event => {
    if (stacked.matches || drag || !event.isPrimary || event.button !== 0) return;
    // Prevent only the handle's native selection/focus; text fields keep normal touch behavior.
    event.preventDefault();
    const center = handle.getBoundingClientRect().left + gutter / 2;
    drag = {id: event.pointerId, offset: event.clientX - center};
    handle.setPointerCapture(event.pointerId);
    workspace.classList.add('is-resizing');
  });
  handle.addEventListener('pointermove', event => {
    if (!drag || event.pointerId !== drag.id) return;
    const {available} = limits();
    if (available > 0) set((event.clientX - drag.offset - workspace.getBoundingClientRect().left - gutter / 2) / available * 100, false);
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) handle.addEventListener(type, finish);
  handle.addEventListener('keydown', event => {
    if (stacked.matches) return;
    const {min, max} = limits(), current = Number(range.value), step = event.shiftKey ? 5 : 1;
    const value = {ArrowLeft: current - step, ArrowRight: current + step, Home: min, End: max}[event.key];
    if (value === undefined) return;
    event.preventDefault(); set(value);
  });
  range.addEventListener('input', () => set(Number(range.value)));
  function refresh() { finish(); apply(); }
  new ResizeObserver(refresh).observe(workspace);
  stacked.addEventListener('change', refresh);
  window.addEventListener('h3-page-change', refresh);
  window.addEventListener('blur', () => finish());
  apply();
  return {refresh};
 }
 window.H3CreateSplitter = createSplitter;
 createSplitter({workspace: document.getElementById('feedbackWorkspace'), handle: document.getElementById('feedbackResizer'), range: document.getElementById('feedbackSplit')});
})();
