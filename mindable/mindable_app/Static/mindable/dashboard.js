// Menu open/close: common.js. Nav scroll shadow: common.js.

// Home dashboard: scroll reveal uses .reveal.visible (not common .in-view)
const observer = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
