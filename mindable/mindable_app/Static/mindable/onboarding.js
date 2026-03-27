const fields  = ['f-skills','f-values','f-neurotype','f-disadvantages','f-enablers'];
const pillIds = ['sp1','sp15','sp2','sp3','sp4'];
const cardIds = ['card1','card15','card2','card3','card4'];
const NAV_H   = 62 + 58; // nav + sticky progress strip
 
function jumpTo(i){
  const card = document.getElementById(cardIds[i]);
  const top  = card.getBoundingClientRect().top + window.scrollY - NAV_H - 16;
  window.scrollTo({top, behavior:'smooth'});
 
  // flash the card border after scroll lands
  setTimeout(()=>{
    card.classList.add('flash');
    const ta = card.querySelector('textarea');
    if(ta) setTimeout(()=>ta.focus({preventScroll:true}), 250);
    setTimeout(()=>card.classList.remove('flash'), 1200);
  }, 380);
}
 
function updateProgress(){
  let firstEmpty = -1;
  fields.forEach((id,i)=>{
    const el = document.getElementById(id);
    const filled = el && el.value.trim().length > 0;
    const pill = document.getElementById(pillIds[i]);
    pill.classList.remove('done','active');
    if(filled) pill.classList.add('done');
    else if(firstEmpty===-1) firstEmpty = i;
  });
  if(firstEmpty > -1) document.getElementById(pillIds[firstEmpty]).classList.add('active');
}
 
// update active pill as user scrolls
const io = new IntersectionObserver(entries=>{
  entries.forEach(e=>{
    if(e.isIntersecting){
      const idx = cardIds.indexOf(e.target.id);
      if(idx > -1){
        pillIds.forEach(p=>document.getElementById(p).classList.remove('active'));
        const filled = document.getElementById(fields[idx]).value.trim().length > 0;
        if(!filled) document.getElementById(pillIds[idx]).classList.add('active');
      }
    }
  });
},{threshold:0.4, rootMargin:'-70px 0px -35% 0px'});
cardIds.forEach(id=>{ const el=document.getElementById(id); if(el) io.observe(el); });
 
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function submitProfile(){
  const skillsEl = document.getElementById('f-skills');
  const valuesEl = document.getElementById('f-values');
  const neurotypeEl = document.getElementById('f-neurotype');
  const disadvantagesEl = document.getElementById('f-disadvantages');
  const enablersEl = document.getElementById('f-enablers');

  const skills = skillsEl ? skillsEl.value.trim() : '';
  if(!skills){
    const card=document.getElementById('card1');
    card.classList.add('error');
    jumpTo(0);
    setTimeout(()=>card.classList.remove('error'),2000);
    return;
  }

  // Read optional fields (they can be empty).
  const payload = {
    skills: skills,
    values: valuesEl ? valuesEl.value.trim() : '',
    neurotype: neurotypeEl ? neurotypeEl.value.trim() : '',
    disadvantages: disadvantagesEl ? disadvantagesEl.value.trim() : '',
    enablers: enablersEl ? enablersEl.value.trim() : '',
  };

  const overlay = document.getElementById('overlay');
  const overlayTitle = overlay?.querySelector('h2');
  const overlayMsg = overlay?.querySelector('p');
  if (overlay) overlay.classList.add('show');
  if (overlayTitle) overlayTitle.textContent = 'Saving your profile...';
  if (overlayMsg) overlayMsg.textContent = 'One moment while we configure your Workplace Passport.';

  const csrfToken = getCsrfToken();
  fetch('/api/profile/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(payload)
  }).then(async (res) => {
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const detail = data && data.detail ? data.detail : 'Unknown error';
      throw new Error(`Save failed (${res.status}): ${detail}`);
    }
    // User instruction: redirect to /jobs/ after POST.
    window.location.href = '/jobs/';
  }).catch((err) => {
    console.error(err);
    if (overlayTitle) overlayTitle.textContent = 'Could not save your profile';
    if (overlayMsg) overlayMsg.textContent = err.message || 'Please try again in a moment.';
  });
}

// Some onboarding HTML variants used a static `.html` redirect.
// Force the "Enter the Job Board" button to always go to our Django route.
document.addEventListener('DOMContentLoaded', () => {
  updateProgress();
  const btn = document.querySelector('.btn-enter');
  if (!btn) return;
  btn.onclick = () => {
    window.location.href = '/jobs/';
  };
});
