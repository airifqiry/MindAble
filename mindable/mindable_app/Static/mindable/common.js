function setupNavDropdown() {
  const wrapper = document.getElementById('nav-wrapper');
  const trigger = document.getElementById('nav-menu-trigger');
  const panel = document.getElementById('nav-menu-panel');
  if (!wrapper || !trigger || !panel) return;

  const activePage = document.body.dataset.activePage || '';

  const links = panel.querySelectorAll('a[data-page]');
  links.forEach(link => {
    link.classList.toggle('is-active', link.dataset.page === activePage);
  });

  function setOpen(isOpen) {
    panel.hidden = !isOpen;
    trigger.setAttribute('aria-expanded', String(isOpen));
    if (isOpen) {
      const first = panel.querySelector('a');
      if (first) first.focus({ preventScroll: true });
    }
  }

  trigger.addEventListener('click', event => {
    event.preventDefault();
    const isOpen = panel.hidden;
    setOpen(isOpen);
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setOpen(false);
  });

  document.addEventListener('click', event => {
    const target = event.target;
    if (wrapper.contains(target)) return;
    if (!panel.hidden) setOpen(false);
  });

  links.forEach(link => {
    link.addEventListener('click', () => setOpen(false));
  });
}

function setupScrollReveal() {
  const elements = document.querySelectorAll('.reveal:not([data-reveal-bound="1"])');
  if (!elements.length) return;

  if (!('IntersectionObserver' in window)) {
    elements.forEach(el => {
      el.classList.add('in-view');
      el.dataset.revealBound = '1';
    });
    return;
  }

  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('in-view');
      entry.target.dataset.revealBound = '1';
      io.unobserve(entry.target);
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -10% 0px'
  });

  elements.forEach(el => {
    el.dataset.revealBound = '1';
    io.observe(el);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupNavDropdown();
  setupScrollReveal();
});

