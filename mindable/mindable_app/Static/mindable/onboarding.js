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
    const filled = document.getElementById(id).value.trim().length > 0;
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
 
function submitProfile(){
  if(!document.getElementById('f-skills').value.trim()){
    const card=document.getElementById('card1');
    card.classList.add('error');
    jumpTo(0);
    setTimeout(()=>card.classList.remove('error'),2000);
    return;
  }
  document.getElementById('overlay').classList.add('show');
}
 
updateProgress();
