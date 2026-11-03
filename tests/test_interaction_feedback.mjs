import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

function setup() {
  const listeners = new Map(), timers = new Map();
  let nextTimer = 0, openDialog = null;
  function element(label = '') {
    const classes = new Set(), attributes = new Map();
    return {
      textContent: label, disabled: false, dataset: {}, children: [], parentNode: null,
      classList: {add: x => classes.add(x), remove: x => classes.delete(x), contains: x => classes.has(x)},
      getAttribute: x => attributes.get(x) ?? null,
      setAttribute: (x, y) => attributes.set(x, y), removeAttribute: x => attributes.delete(x),
      closest() { return this; },
      append(child) { child.parentNode = this; this.children.push(child); },
    };
  }
  const body = element(), window = {addEventListener() {}};
  const document = {
    body, createElement: () => element(), querySelector: () => openDialog,
    addEventListener: (name, fn) => listeners.set(name, fn),
  };
  const context = vm.createContext({document, window,
    setTimeout: (fn, ms) => { const id = ++nextTimer; timers.set(id, {fn, ms}); return id; },
    clearTimeout: id => timers.delete(id),
  });
  vm.runInContext(readFileSync(new URL('../web/public/interaction-feedback.js', import.meta.url), 'utf8'), context);
  return {
    body, element, feedback: window.h3InteractionFeedback,
    modal(value) { openDialog = value; },
    tick(ms = 0) { for (const [id, t] of [...timers]) if (t.ms === ms) { timers.delete(id); t.fn(); } },
    event(name, button, extra = {}) {
      const event = {target: button, button: 0, isPrimary: true, clientX: 10, clientY: 10,
        prevented: false, stopped: false,
        preventDefault() { this.prevented = true; }, stopImmediatePropagation() { this.stopped = true; }, ...extra};
      listeners.get(name)(event);
      return event;
    },
  };
}

// A finger sees feedback on contact, including dynamically created controls.
{
  const ui = setup(), a = ui.element('선택'), b = ui.element('다음');
  ui.event('pointerdown', a); assert(a.classList.contains('interaction-pressed'));
  ui.event('pointerup', a); assert(a.classList.contains('interaction-pressed'));
  ui.event('pointerdown', b); ui.tick(180);
  assert(!a.classList.contains('interaction-pressed'));
  assert(b.classList.contains('interaction-pressed'));
  ui.event('pointermove', b, {clientY: 40}); assert(!b.classList.contains('interaction-pressed'));
  ui.event('pointerdown', b); ui.event('pointercancel', b);
  assert(!b.classList.contains('interaction-pressed'));
  b.disabled = true; ui.event('pointerdown', b); assert(!b.classList.contains('interaction-pressed'));
}
// Processing preserves existing disabled state and blocks duplicate clicks/submits.
{
  const ui = setup(), button = ui.element('생성'), modal = ui.element();
  ui.modal(modal); ui.event('submit', button, {submitter: button});
  let done;
  const request = ui.feedback.track(() => new Promise(resolve => { done = resolve; }));
  assert.equal(button.getAttribute('aria-busy'), 'true');
  assert(button.classList.contains('interaction-busy'));
  assert.equal(button.disabled, false);
  assert.equal(modal.children.at(-1).textContent, '생성 · 처리 중…');
  assert(ui.event('click', button).stopped);
  assert(ui.event('submit', button, {submitter: button}).prevented);
  ui.tick(); done({queued: true}); assert.deepEqual(await request, {queued: true});
  ui.feedback.announce('후보가 큐에 등록됐습니다.'); ui.tick();
  assert.equal(button.getAttribute('aria-busy'), null);
  assert(!button.classList.contains('interaction-busy'));
  assert.equal(modal.children.at(-1).textContent, '후보가 큐에 등록됐습니다.');
}
// Failed requests remain failed, with retry possible and visible error feedback.
{
  const ui = setup(), button = ui.element('저장');
  button.setAttribute('aria-busy', 'false'); ui.event('click', button);
  await assert.rejects(ui.feedback.track(async () => { throw Error('저장 실패'); }), /저장 실패/);
  assert.equal(button.getAttribute('aria-busy'), 'false');
  assert.equal(ui.body.children.at(-1).dataset.kind, 'error');
  ui.tick(); assert(!ui.event('click', button).stopped);
}
// Background polling is not attributed to the user's previous tap.
{
  const ui = setup(), button = ui.element('페이지');
  ui.event('click', button); ui.tick();
  await ui.feedback.track(async () => 42);
  assert.equal(ui.body.children.length, 0);
  assert(!button.classList.contains('interaction-busy'));
}
console.log('터치 피드백: 눌림·스크롤 취소·처리 중·중복 방지·성공·실패·모달·백그라운드 구분 통과');
