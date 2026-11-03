/* Preserve the reader's place during synchronous UI updates, not during requests. */
(() => {
  function key(node) {
    if (node.nodeType !== 1) return null;
    if (node.id) return `id:${node.id}`;
    for (const name of ['data-h3-candidate-set', 'data-h3-selected-job', 'data-h3-candidate-play', 'data-feedback-set', 'data-feedback-job']) {
      if (node.hasAttribute(name)) return `${name}:${node.getAttribute(name)}`;
    }
    return null;
  }
  function compatible(left, right) {
    return left.nodeType === right.nodeType && left.nodeName === right.nodeName && key(left) === key(right)
      && (left.nodeType !== 1 || key(left) || left.classList[0] === right.classList[0]);
  }
  function patch(old, fresh) {
    if (old.nodeType !== 1) {
      if (old.nodeValue !== fresh.nodeValue) old.nodeValue = fresh.nodeValue;
      return;
    }
    const open = old.tagName === 'DETAILS' ? old.open : null;
    const value = old.tagName === 'SELECT' ? old.value : null;
    const transient = ['interaction-busy', 'interaction-pressed'].filter(x => old.classList.contains(x));
    const busy = old.getAttribute('aria-busy');
    // These controls are mounted after the base candidate markup is rendered.
    // Retain their nodes too, including modal openers and in-flight requeue buttons.
    if (old.hasAttribute('data-h3-candidate-set')) {
      const visuals = old.querySelector(':scope > .h3-candidate-storyboards');
      if (visuals && !fresh.querySelector(':scope > .h3-candidate-storyboards')) {
        fresh.querySelector('.h3-candidate-grid')?.before(visuals.cloneNode(true));
      }
    }
    if (old.hasAttribute('data-h3-candidate-actions')) {
      const requeue = old.querySelector('[data-h3-requeue-candidate-set]');
      if (requeue && !fresh.querySelector('[data-h3-requeue-candidate-set]')) {
        fresh.insertBefore(requeue.cloneNode(true), fresh.querySelector('[data-h3-force-candidate-set]'));
      }
    }
    for (const attr of [...old.attributes]) {
      if (!fresh.hasAttribute(attr.name) && attr.name !== 'open' && attr.name !== 'aria-busy') old.removeAttribute(attr.name);
    }
    for (const attr of fresh.attributes) {
      if (old.getAttribute(attr.name) !== attr.value) old.setAttribute(attr.name, attr.value);
    }
    for (const name of transient) old.classList.add(name);
    if (transient.includes('interaction-busy') && busy !== null) old.setAttribute('aria-busy', busy);
    reconcile(old, fresh);
    if (open !== null) old.open = open;
    if (value !== null && [...old.options].some(option => option.value === value)) old.value = value;
  }
  function reconcile(parent, fresh) {
    const previous = [...parent.childNodes];
    const keyed = new Map(previous.map(node => [key(node), node]).filter(([id]) => id));
    const used = new Set();
    let cursor = parent.firstChild;
    for (const next of [...fresh.childNodes]) {
      const id = key(next);
      let existing = id ? keyed.get(id) : previous.find(node => !used.has(node) && !key(node) && compatible(node, next));
      if (existing && !compatible(existing, next)) existing = null;
      if (existing) {
        used.add(existing);
        if (existing !== cursor) parent.insertBefore(existing, cursor);
        patch(existing, next);
      } else {
        existing = next.cloneNode(true);
        parent.insertBefore(existing, cursor);
      }
      cursor = existing.nextSibling;
    }
    while (cursor) { const next = cursor.nextSibling; cursor.remove(); cursor = next; }
  }
  const updateMarkup = (element, html) => {
    const template = document.createElement('template');
    template.innerHTML = html;
    reconcile(element, template.content);
  };
  const preserveViewport = update => {
    const x = window.scrollX, y = window.scrollY, focused = document.activeElement;
    let focusSelector = focused?.id ? `#${CSS.escape(focused.id)}` : null;
    for (const name of ['data-h3-candidate-play', 'data-h3-requeue-candidate-set']) {
      if (focused?.hasAttribute(name)) focusSelector = `[${name}="${CSS.escape(focused.getAttribute(name))}"]`;
    }
    if (focused?.dataset.h3Select) {
      const [set, job] = focused.dataset.h3Select.split(':');
      focusSelector = `[data-h3-clear-selection="${CSS.escape(set)}"][data-h3-clear-selection-job="${CSS.escape(job)}"]`;
    } else if (focused?.dataset.h3ClearSelectionJob) {
      focusSelector = `[data-h3-select="${CSS.escape(focused.dataset.h3ClearSelection + ':' + focused.dataset.h3ClearSelectionJob)}"]`;
    }
    const anchors = [...document.querySelectorAll('main [id], main [data-h3-candidate-set], main [data-h3-selected-job]')]
      .map(element => ({element, top: element.getBoundingClientRect().top, rect: element.getBoundingClientRect()}))
      .filter(item => item.rect.height && item.rect.bottom > 0 && item.top < window.innerHeight)
      .sort((a, b) => Math.abs(a.top) - Math.abs(b.top));
    const result = update();
    const targetFocus = focused?.isConnected ? focused : focusSelector && document.querySelector(focusSelector);
    if (targetFocus && targetFocus !== document.activeElement && !document.querySelector('dialog[open]')) {
      targetFocus.focus({preventScroll: true});
    }
    const anchor = anchors.find(item => item.element.isConnected && item.element.getBoundingClientRect().height);
    const target = anchor ? window.scrollY + anchor.element.getBoundingClientRect().top - anchor.top : y;
    if (Math.abs(window.scrollY - target) > .5 || window.scrollX !== x) {
      window.scrollTo({left: x, top: Math.max(0, target), behavior: 'instant'});
    }
    return result;
  };
  window.H3ViewStability = {updateMarkup, preserveViewport};
})();
