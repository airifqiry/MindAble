
function switchTab(t) {
  ['login','signup'].forEach(id => {
    document.getElementById('panel-'+id).classList.toggle('visible', id===t);
    document.getElementById('tab-'+id).classList.toggle('active', id===t);
  });
}
 

function togglePw(id, btn) {
  const inp = document.getElementById(id);
  const show = inp.type==='password';
  inp.type = show ? 'text' : 'password';
  btn.innerHTML = show
    ? `<svg viewBox="0 0 24 24" style="width:17px;height:17px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M6.71 6.71A10 10 0 001 12s4 8 11 8a9.9 9.9 0 005.29-1.53"/><path d="M10.37 10.37a3 3 0 004.26 4.26"/><path d="M17.57 17.57A10 10 0 0023 12s-4-8-11-8a9.9 9.9 0 00-4.27.96"/></svg>`
    : `<svg viewBox="0 0 24 24" style="width:17px;height:17px;stroke:currentColor;stroke-width:2;fill:none;stroke-linecap:round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
}


function validateSignupSubmit(e) {
  const fn = document.getElementById('su-fn').value.trim();
  const ln = document.getElementById('su-ln').value.trim();
  const em = document.getElementById('su-em').value.trim();
  const pw = document.getElementById('su-pw').value;
  const pw2 = document.getElementById('su-pw-confirm').value;
  const err = document.getElementById('s0-err');
  document.getElementById('su-username').value = em;
  if (!fn || !ln || !em || pw.length < 8 || pw !== pw2) {
    err.classList.add('on');
    e.preventDefault();
    return false;
  }
  err.classList.remove('on');
  return true;
}
