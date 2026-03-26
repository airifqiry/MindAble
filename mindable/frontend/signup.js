// ── Tab switch ──
function switchTab(t) {
  ['login','signup'].forEach(id => {
    document.getElementById('panel-'+id).classList.toggle('visible', id===t);
    document.getElementById('tab-'+id).classList.toggle('active', id===t);
  });
}
 
// ── Password toggle ──
function togglePw(id, btn) {
  const inp = document.getElementById(id);
  const show = inp.type==='password';
  inp.type = show ? 'text' : 'password';
  btn.innerHTML = show
    ? `<svg viewBox="0 0 24 24" style="width:17px;height:17px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M6.71 6.71A10 10 0 001 12s4 8 11 8a9.9 9.9 0 005.29-1.53"/><path d="M10.37 10.37a3 3 0 004.26 4.26"/><path d="M17.57 17.57A10 10 0 0023 12s-4-8-11-8a9.9 9.9 0 00-4.27.96"/></svg>`
    : `<svg viewBox="0 0 24 24" style="width:17px;height:17px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
}
 
// ── Energy slider ──
const eLabels = ['Very low','Low','Moderate','High','Full capacity'];
function updateEnergy(el) {
  document.getElementById('e-label').textContent = eLabels[el.value-1];
  const pct = ((el.value-1)/4)*100;
  el.style.setProperty('--pct', pct+'%');
  el.style.background = `linear-gradient(90deg, var(--purple) ${pct}%, rgba(139,92,246,.15) ${pct}%)`;
}
// init slider gradient
window.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('energy');
  if(el) updateEnergy(el);
});
 
// ── Preset buttons ──
function setPre(btn, val) {
  document.querySelectorAll('.preset').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('contrib').value = val;
}
 
// ── Multi-step ──
let step = 0;
function goStep(n) {
  if (n===1) {
    const fn = document.getElementById('su-fn').value.trim();
    const ln = document.getElementById('su-ln').value.trim();
    const em = document.getElementById('su-em').value.trim();
    const pw = document.getElementById('su-pw').value;
    const err = document.getElementById('s0-err');
    if (!fn||!ln||!em||pw.length<8) { err.classList.add('on'); return; }
    err.classList.remove('on');
  }
  document.getElementById('s'+step).classList.remove('active');
  document.getElementById('d'+step).classList.remove('active');
  step = n;
  document.getElementById('s'+step).classList.add('active');
  document.getElementById('d'+step).classList.add('active');
}
 
// ── Login ──
function handleLogin() {
  const em = document.getElementById('l-email').value.trim();
  const pw = document.getElementById('l-pw').value;
  const err = document.getElementById('l-err');
  if (!em||!pw) { err.classList.add('on'); return; }
  err.classList.remove('on');
  alert('Login submitted! Connect to your backend here.');
}
 
// ── Signup final ──
function handleSignup() {
  const amt = parseFloat(document.getElementById('contrib').value);
  const err = document.getElementById('s2-err');
  if (isNaN(amt)||amt<0.50) { err.classList.add('on'); return; }
  err.classList.remove('on');
  document.getElementById('s2').classList.remove('active');
  document.getElementById('d2').classList.remove('active');
  document.getElementById('success').classList.add('on');
}