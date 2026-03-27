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
let jobsPage = 1;
let jobsLoading = false;
let jobsHasMore = true;

function renderJobCard(job) {
  const card = document.createElement('div');
  card.className = 'job-card';
  card.dataset.jobId = String(job.id);

  const logo = document.createElement('div');
  logo.className = 'job-logo';
  const company = job.company ? String(job.company) : '';
  logo.textContent = company ? company.trim().charAt(0).toUpperCase() : 'M';

  const body = document.createElement('div');
  body.className = 'job-body';

  const top = document.createElement('div');
  top.className = 'job-top';

  const title = document.createElement('div');
  title.className = 'job-title';
  title.textContent = job.translated_title ? String(job.translated_title) : '';

  const companyEl = document.createElement('div');
  companyEl.className = 'job-company';
  companyEl.textContent = company;

  top.appendChild(title);
  top.appendChild(companyEl);

  const desc = document.createElement('div');
  desc.className = 'job-desc';
  const location = job.location ? String(job.location) : '';
  const jobType = job.job_type ? String(job.job_type) : '';
  desc.textContent = [location, jobType].filter(Boolean).join(' · ');

  const tags = document.createElement('div');
  tags.className = 'job-tags';
  if (job.job_type) {
    const t = document.createElement('span');
    t.className = 'job-tag blue';
    t.textContent = job.job_type;
    tags.appendChild(t);
  }
  if (job.location) {
    const t = document.createElement('span');
    t.className = 'job-tag muted';
    t.textContent = job.location;
    tags.appendChild(t);
  }

  if (Array.isArray(job.toxicity_warnings) && job.toxicity_warnings.length) {
    const firstWarn = document.createElement('span');
    firstWarn.className = 'toxicity-flag';
    firstWarn.textContent = job.toxicity_warnings[0];
    tags.appendChild(firstWarn);
  }

  const footer = document.createElement('div');
  footer.className = 'job-footer';

  const viewBtn = document.createElement('a');
  viewBtn.className = 'btn-view';
  viewBtn.href = '#';
  viewBtn.textContent = 'View';
  viewBtn.addEventListener('click', e => e.preventDefault());

  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'btn-dismiss';
  dismissBtn.type = 'button';
  dismissBtn.textContent = 'Not interested';
  dismissBtn.addEventListener('click', () => dismissCard(dismissBtn));

  footer.appendChild(viewBtn);
  footer.appendChild(dismissBtn);

  body.appendChild(top);
  body.appendChild(desc);
  body.appendChild(tags);
  body.appendChild(footer);

  card.appendChild(logo);
  card.appendChild(body);
  return card;
}

async function loadMore() {
  if (jobsLoading || !jobsHasMore) return;
  const btn = document.querySelector('.btn-load-more');
  const feed = document.getElementById('job-feed');
  if (!feed || !btn) return;

  jobsLoading = true;
  btn.disabled = true;
  btn.textContent = 'Loading...';
  btn.style.opacity = '.7';

  try {
    const res = await fetch(`/api/jobs/?page=${jobsPage}`, {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    });

    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = '/login/';
        return;
      }
      const txt = await res.text().catch(() => '');
      throw new Error(`Request failed (${res.status}): ${txt}`);
    }

    const data = await res.json();
    const jobs = Array.isArray(data)
      ? data
      : (data.results || data.jobs || []);

    if (!jobs.length) {
      jobsHasMore = false;
      btn.textContent = 'No more roles right now';
      btn.disabled = true;
      btn.style.opacity = '.5';
      btn.style.cursor = 'default';
      return;
    }

    jobs.forEach(job => feed.appendChild(renderJobCard(job)));
    jobsPage += 1;
    updateCount();
    checkEmpty();
  } catch (e) {
    console.error(e);
    btn.textContent = 'Could not load roles';
    btn.style.opacity = '1';
  } finally {
    jobsLoading = false;
    // If we still have more, allow clicks again.
    if (jobsHasMore) {
      btn.disabled = false;
      btn.style.cursor = 'pointer';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Load initial page so the job feed isn't empty.
  if (document.getElementById('job-feed')) loadMore();
});

