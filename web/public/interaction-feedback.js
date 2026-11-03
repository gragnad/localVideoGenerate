/* Delegated feedback also covers buttons created by candidate/result rendering. */
(() => {
  const selector = 'button, .button-link, [role="button"], summary';
  const actions = new WeakMap();
  const pressTimers = new WeakMap();
  let currentAction = null, pressed = null, origin = null;
  let contextTimer, noticeTimer, notice, announcementVersion = 0;

  function control(event) {
    const element = event.target?.closest?.(selector);
    return element && !element.disabled && element.getAttribute('aria-disabled') !== 'true'
      ? element : null;
  }
  function show(message, kind = 'pending') {
    if (!notice) {
      notice = document.createElement('div');
      notice.className = 'interaction-notice';
      notice.setAttribute('role', 'status');
      notice.setAttribute('aria-live', 'polite');
      notice.setAttribute('aria-atomic', 'true');
    }
    // A body toast would be hidden behind Safari's modal top layer.
    const host = document.querySelector('dialog[open]') || document.body;
    if (notice.parentNode !== host) host.append(notice);
    clearTimeout(noticeTimer);
    notice.dataset.kind = kind;
    notice.textContent = message;
    notice.hidden = false;
    if (kind !== 'pending') noticeTimer = setTimeout(() => { notice.hidden = true; }, 4000);
  }
  function announce(message, bad = false) {
    announcementVersion++;
    show(message, bad ? 'error' : 'success');
  }
  function release(immediate = false) {
    const element = pressed;
    pressed = null;
    origin = null;
    if (element) {
      clearTimeout(pressTimers.get(element));
      if (immediate) element.classList.remove('interaction-pressed');
      else pressTimers.set(element, setTimeout(() => element.classList.remove('interaction-pressed'), 180));
    }
  }
  function activate(event, element) {
    if (!element) return;
    if (actions.get(element)?.pending) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    release(true);
    pressed = element;
    clearTimeout(pressTimers.get(element));
    element.classList.add('interaction-pressed');
    release();
    currentAction = {
      element, label: (element.getAttribute('aria-label') || element.textContent || '요청').trim(),
      pending: 0, failed: false, version: announcementVersion,
      previousBusy: element.getAttribute('aria-busy'),
    };
    clearTimeout(contextTimer);
    // Only requests initiated by this event belong to its control. Polling does not.
    contextTimer = setTimeout(() => { currentAction = null; }, 0);
  }
  async function track(task) {
    const action = currentAction;
    if (!action) return task();
    const {element} = action;
    action.pending++;
    actions.set(element, action);
    element.classList.add('interaction-busy');
    element.setAttribute('aria-busy', 'true');
    show(`${action.label} · 처리 중…`);
    try {
      return await task();
    } catch (error) {
      action.failed = true;
      announce(error.message || '요청을 처리하지 못했습니다.', true);
      throw error;
    } finally {
      action.pending--;
      if (!action.pending) {
        actions.delete(element);
        element.classList.remove('interaction-busy');
        if (action.previousBusy === null) element.removeAttribute('aria-busy');
        else element.setAttribute('aria-busy', action.previousBusy);
        setTimeout(() => {
          if (!action.failed && action.version === announcementVersion) {
            show(`${action.label} · 요청 응답을 받았습니다.`, 'success');
          }
        }, 0);
      }
    }
  }
  document.addEventListener('pointerdown', event => {
    if (event.isPrimary === false || (event.button != null && event.button !== 0)) return;
    release(true);
    pressed = control(event);
    if (pressed) {
      clearTimeout(pressTimers.get(pressed));
      origin = {x: event.clientX, y: event.clientY};
      pressed.classList.add('interaction-pressed');
    }
  }, {capture: true, passive: true});
  document.addEventListener('pointermove', event => {
    if (origin && Math.hypot(event.clientX - origin.x, event.clientY - origin.y) > 12) release(true);
  }, {capture: true, passive: true});
  document.addEventListener('pointerup', () => release(), {capture: true, passive: true});
  document.addEventListener('pointercancel', () => release(true), {capture: true, passive: true});
  document.addEventListener('click', event => activate(event, control(event)), true);
  document.addEventListener('submit', event => activate(event, event.submitter), true);
  window.addEventListener('blur', () => release(true));
  window.addEventListener('pagehide', () => release(true));
  window.h3InteractionFeedback = {track, announce};
})();
