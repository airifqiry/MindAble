// ── Nav scroll shadow
window.addEventListener('scroll', () => {
  document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 10);
});

// ── Nav dropdown
const menuBtn = document.getElementById('nav-menu-btn');
const menuPanel = document.getElementById('nav-menu-panel');

function openMenu() {
  menuPanel.hidden = false;
  menuBtn.classList.add('open');
  menuBtn.setAttribute('aria-expanded', 'true');
}
function closeMenu() {
  menuPanel.hidden = true;
  menuBtn.classList.remove('open');
  menuBtn.setAttribute('aria-expanded', 'false');
}
menuBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  menuPanel.hidden ? openMenu() : closeMenu();
});
document.addEventListener('click', (e) => {
  if (!menuPanel.hidden && !menuPanel.contains(e.target)) closeMenu();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeMenu();
});

// ── Dismiss card
function dismissCard(btn) {
  const card = btn.closest('.job-card');
  card.classList.add('dismissed');
  setTimeout(() => {
    card.style.display = 'none';
    updateCount();
    checkEmpty();
  }, 400);
}

function updateCount() {
  const visible = document.querySelectorAll('.job-card:not(.dismissed)').length;
  document.getElementById('results-num').textContent = visible;
}

function checkEmpty() {
  const anyVisible = [...document.querySelectorAll('.job-card')]
    .some(c => !c.classList.contains('dismissed') && c.style.display !== 'none');
  document.getElementById('empty-state').hidden = anyVisible;
  document.getElementById('load-more-wrap').hidden = !anyVisible;
}

// ── Load more (placeholder — replace with fetch() when API is ready)
function loadMore() {
  // TODO: replace this with the real API call when backend is ready
  // Example:
  // const res = await fetch('/api/jobs/?page=2');
  // const data = await res.json();
  // data.jobs.forEach(job => renderJobCard(job));
  const btn = document.querySelector('.btn-load-more');
  btn.textContent = 'No more roles right now';
  btn.disabled = true;
  btn.style.opacity = '.5';
  btn.style.cursor = 'default';
}

