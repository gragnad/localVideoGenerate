(() => {
  const sidebar = document.getElementById('studioSidebar');
  const toggle = document.getElementById('sidebarToggle');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (!sidebar || !toggle || !backdrop) return;
  const originalHeader = toggle.parentElement;
  const feedbackNavigation = document.getElementById('feedbackNavigation');
  const compareNavigation = document.getElementById('compareNavigation');
  let page = location.hash.slice(1), feedback = ['feedback', 'compare'].includes(page);
  const storageKey = () => 'h3-sidebar-collapsed' + (feedback ? '-' + page : '');
  function preferred() {
    try { const value = localStorage.getItem(storageKey()); return value === null ? feedback : value === '1'; }
    catch { return feedback; }
  }
  let collapsed = preferred();
  function remember() { try { localStorage.setItem(storageKey(), collapsed ? '1' : '0'); } catch {} }
  function render() {
    if (page === 'compare' && compareNavigation) compareNavigation.append(toggle);
    else if (feedback && feedbackNavigation) feedbackNavigation.append(toggle);
    else originalHeader.prepend(toggle);
    document.body.classList.toggle('studio-sidebar-collapsed', collapsed);
    document.body.classList.toggle('studio-feedback-layout', feedback);
    sidebar.inert = collapsed;
    sidebar.setAttribute('aria-hidden', String(collapsed));
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.textContent = collapsed ? '☰ 메뉴 열기' : '‹ 메뉴 접기';
    backdrop.hidden = collapsed || !feedback;
    window.dispatchEvent(new Event('resize'));
  }
  function close() { collapsed = true; remember(); render(); toggle.focus({preventScroll: true}); }
  toggle.onclick = () => {
    collapsed = !collapsed;
    remember();
    render();
  };
  backdrop.onclick = close;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && feedback && !collapsed && !document.querySelector('dialog[open]')) close();
  });
  window.addEventListener('h3-page-change', event => {
    page = event.detail.page;
    feedback = ['feedback', 'compare'].includes(page);
    collapsed = preferred();
    render();
  });
  render();
})();
