function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

let jobsPage = 1;
let jobsLoading = false;
let jobsHasMore = true;
const loadedJobIds = new Set();
const loadedDedupeKeys = new Set();
const dismissedJobIds = new Set();

function normalizeJobType(value) {
  const v = String(value || '').trim().toLowerCase();
  if (!v) return '';
  if (v === 'full-time') return 'Full-time';
  if (v === 'part-time') return 'Part-time';
  if (v === 'remote') return 'Remote';
  if (v === 'hybrid') return 'Hybrid';
  return value;
}

function safeText(value, fallback = '') {
  const v = String(value || '').trim();
  return v || fallback;
}

function updateCount() {
  const visible = [...document.querySelectorAll('.job-card')]
    .filter(c => !c.classList.contains('dismissed') && c.style.display !== 'none').length;
  const el = document.getElementById('results-num');
  if (el) el.textContent = String(visible);
}

function checkEmpty() {
  const anyVisible = [...document.querySelectorAll('.job-card')]
    .some(c => !c.classList.contains('dismissed') && c.style.display !== 'none');

  const emptyState = document.getElementById('empty-state');
  const loadMoreWrap = document.getElementById('load-more-wrap');
  if (emptyState) emptyState.hidden = anyVisible || jobsHasMore;
  if (loadMoreWrap) loadMoreWrap.hidden = !jobsHasMore;
}

async function dismissCard(btn) {
  const card = btn.closest('.job-card');
  const jobId = Number(card?.dataset?.jobId);
  if (!card || !jobId) return;

  dismissedJobIds.add(jobId);
  const csrfToken = getCsrfToken();
  try {
    const res = await fetch(`/api/jobs/${jobId}/not-interested/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': csrfToken
      }
    });
    if (!res.ok) {
      const message = await res.text().catch(() => '');
      throw new Error(`Dismiss failed (${res.status}): ${message}`);
    }
  } catch (err) {
    console.error('Dismiss API failed:', err);
  }

  card.classList.add('dismissed');
  setTimeout(() => {
    card.style.display = 'none';
    updateCount();
    checkEmpty();
  }, 250);
}

async function toggleExpand(card, viewBtn) {
  const jobId = Number(card?.dataset?.jobId);
  if (!jobId) return;

  const detail = card.querySelector('.card-detail');
  const detailsLoaded = card.dataset.detailsLoaded === 'true';
  const isExpanded = card.classList.contains('expanded');

  if (isExpanded) {
    card.classList.remove('expanded');
    viewBtn.textContent = 'View details';
    return;
  }

  if (!detailsLoaded && detail) {
    detail.innerHTML = '<div class="detail-text">Loading details...</div>';
    try {
      const res = await fetch(`/api/jobs/${jobId}/`, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const reason = safeText(errData.detail, `Detail request failed (${res.status})`);
        throw new Error(reason);
      }
      const data = await res.json();
      const tasks = Array.isArray(data.translated_tasks) ? data.translated_tasks.filter(Boolean) : [];
      const warnings = Array.isArray(data.toxicity_warnings) ? data.toxicity_warnings.filter(Boolean) : [];
      const skills = Array.isArray(data.required_skills) ? data.required_skills.filter(Boolean) : [];
      const applyUrl = safeText(data.external_url, '#');
      const accessibleSummary = safeText(data.accessible_summary, '');

      detail.innerHTML = `
        <div class="detail-divider"></div>
        ${warnings.length ? `<div class="toxicity-flag">${warnings[0]}</div>` : ''}
        <div class="detail-section">
          <div class="detail-label">Plain language overview</div>
          <pre class="detail-pre">${accessibleSummary || 'Detailed rewrite is not available yet.'}</pre>
        </div>
        <div class="detail-section">
          <div class="detail-label">What you would do</div>
          ${tasks.length
            ? `<ul class="detail-list">${tasks.slice(0, 5).map(t => `<li>${t}</li>`).join('')}</ul>`
            : `<p class="detail-text">No detailed tasks yet. Open the role link for full info.</p>`
          }
        </div>
        <div class="detail-section">
          <div class="detail-label">Skills mentioned</div>
          <p class="detail-text">${skills.length ? skills.slice(0, 8).join(', ') : 'Not provided'}</p>
        </div>
        <a class="btn-apply" href="${applyUrl}" target="_blank" rel="noopener noreferrer">Apply</a>
      `;
      card.dataset.detailsLoaded = 'true';
    } catch (err) {
      console.error(err);
      detail.innerHTML = '<div class="detail-text">Could not load details right now.</div>';
    }
  }

  card.classList.add('expanded');
  viewBtn.textContent = 'Hide details';
}

function renderJobCard(job) {
  const card = document.createElement('div');
  card.className = 'job-card';
  card.dataset.jobId = String(job.id);

  const company = safeText(job.company_name || job.company_label, 'Unknown company');
  const displayTitle = safeText(job.display_title || job.translated_title || job.title, 'Untitled role');
  const location = safeText(job.location, 'Location not listed');
  const jobType = normalizeJobType(job.job_type);
  const score = typeof job.match_score === 'number' ? `${Math.round(job.match_score * 100)}% fit` : '';

  const preview = document.createElement('div');
  preview.className = 'card-preview';

  const logo = document.createElement('div');
  logo.className = 'card-logo';
  logo.style.background = 'linear-gradient(135deg, #5B7FFF 0%, #8B5CF6 100%)';
  logo.textContent = company.charAt(0).toUpperCase();

  const summary = document.createElement('div');
  summary.className = 'card-summary';

  const title = document.createElement('div');
  title.className = 'card-title';
  title.textContent = displayTitle;

  const meta = document.createElement('div');
  meta.className = 'card-meta';
  meta.textContent = `${company} • ${location}`;

  const explain = document.createElement('div');
  explain.className = 'card-meta';
  explain.style.marginTop = '0.3rem';
  explain.style.fontSize = '0.78rem';
  explain.style.color = 'var(--muted)';
  explain.textContent = safeText(job.match_explanation || job.match_reason, '');

  const tags = document.createElement('div');
  tags.className = 'card-tags';
  if (jobType) {
    const t = document.createElement('span');
    t.className = 'tag tag-blue';
    t.textContent = jobType;
    tags.appendChild(t);
  }
  if (score) {
    const s = document.createElement('span');
    s.className = 'tag tag-green';
    s.textContent = score;
    tags.appendChild(s);
  }

  summary.appendChild(title);
  summary.appendChild(meta);
  if (safeText(job.match_explanation || job.match_reason, '').length) {
    summary.appendChild(explain);
  }
  summary.appendChild(tags);
  preview.appendChild(logo);
  preview.appendChild(summary);

  const viewBtn = document.createElement('a');
  viewBtn.className = 'btn-view';
  viewBtn.href = '#';
  viewBtn.textContent = 'View details';
  viewBtn.addEventListener('click', e => {
    e.preventDefault();
    toggleExpand(card, viewBtn);
  });

  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'btn-dismiss';
  dismissBtn.type = 'button';
  dismissBtn.title = 'Not interested';
  dismissBtn.innerHTML = `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18"></path>
    </svg>
  `;
  dismissBtn.addEventListener('click', () => dismissCard(dismissBtn));

  const detail = document.createElement('div');
  detail.className = 'card-detail';

  preview.appendChild(viewBtn);
  card.appendChild(preview);
  card.appendChild(detail);
  card.appendChild(dismissBtn);
  return card;
}

async function loadMore() {
  console.log('Fetching jobs...');
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
    console.log('Response:', data);
    // Prefer `jobs`; do not use `a || b` — an empty `results: []` is truthy and would hide `jobs`.
    let jobs = Array.isArray(data) ? data : (data.jobs ?? data.results ?? []);
    console.log('Jobs parsed for rendering:', jobs.length);
    jobs = jobs.filter(job => {
      const id = Number(job.id);
      const dk = String(job.dedupe_key || job.link || '').trim() || `id:${id}`;
      return (
        id
        && !loadedJobIds.has(id)
        && !loadedDedupeKeys.has(dk)
        && !dismissedJobIds.has(id)
      );
    });

    const next = Array.isArray(data) ? null : (data.next || null);
    jobsHasMore = Array.isArray(data) ? jobs.length > 0 : Boolean(next);

    jobs.forEach(job => {
      const id = Number(job.id);
      const dk = String(job.dedupe_key || job.link || '').trim() || `id:${id}`;
      loadedJobIds.add(id);
      loadedDedupeKeys.add(dk);
      feed.appendChild(renderJobCard(job));
    });
    jobsPage += 1;
    updateCount();
    checkEmpty();

    if (!jobsHasMore) {
      btn.textContent = 'No more roles right now';
      btn.disabled = true;
      btn.style.opacity = '.5';
      btn.style.cursor = 'default';
      return;
    }

    btn.textContent = 'Load more roles';
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
  const feed = document.getElementById('job-feed');
  if (!feed || feed.dataset.initialized === '1') return;
  feed.dataset.initialized = '1';
  loadMore();
});

