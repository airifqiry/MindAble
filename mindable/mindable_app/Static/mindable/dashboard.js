// Nav scroll shadow
window.addEventListener('scroll', () => {
  document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 10);
});

// Nav dropdown menu
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

// Scroll reveal
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

