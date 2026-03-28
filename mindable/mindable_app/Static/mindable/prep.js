function appendBubble({ role, text }) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  const bubble = document.createElement('div');
  bubble.className = role === 'user' ? 'bubble bubble--user' : 'bubble bubble--ai';
  bubble.textContent = text;
  messages.appendChild(bubble);

  messages.scrollTop = messages.scrollHeight;
}

function setTyping(isTyping) {
  const indicator = document.getElementById('typing-indicator');
  if (!indicator) return;
  indicator.hidden = !isTyping;
}

const PREP_JOB_STORAGE_KEY = 'prep_selected_job_id';

let prepJobId = null;
let jobsLoadPromise = null;

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function parseJobIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  for (const key of ['job_id', 'job']) {
    const raw = params.get(key);
    if (raw && /^\d+$/.test(String(raw).trim())) {
      return parseInt(raw.trim(), 10);
    }
  }
  return null;
}

function readStoredJobId() {
  try {
    const raw = sessionStorage.getItem(PREP_JOB_STORAGE_KEY);
    if (raw && /^\d+$/.test(String(raw).trim())) {
      return parseInt(raw.trim(), 10);
    }
  } catch (_) {
    
  }
  return null;
}

function writeStoredJobId(id) {
  try {
    if (id) {
      sessionStorage.setItem(PREP_JOB_STORAGE_KEY, String(id));
    }
  } catch (_) {
    
  }
}

async function fetchJobsForPrep() {
  const res = await fetch('/api/jobs/?page=1&page_size=50', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) return [];
  const data = await res.json();
  const jobs = Array.isArray(data) ? data : data.results || data.jobs || [];
  return Array.isArray(jobs) ? jobs : [];
}

function populateJobSelect(jobs) {
  const sel = document.getElementById('prep-job-select');
  if (!sel) return;

  sel.innerHTML = '';
  if (!jobs.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No listings yet — open the job board first';
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }

  jobs.forEach((j) => {
    const opt = document.createElement('option');
    opt.value = String(j.id);
    const title = j.display_title || j.translated_title || j.title || 'Role';
    const company = j.company_name || j.company_label || j.company || '';
    opt.textContent = company ? `${title} — ${company}` : title;
    sel.appendChild(opt);
  });
  sel.disabled = false;
}

function pickInitialJobId(jobs, preferredId) {
  if (!jobs.length) return null;
  const ids = new Set(jobs.map((j) => j.id));
  if (preferredId != null && ids.has(preferredId)) {
    return preferredId;
  }
  return jobs[0].id;
}

function loadPrepJobsOnce() {
  if (!jobsLoadPromise) {
    jobsLoadPromise = fetchJobsForPrep()
      .then((jobs) => {
        populateJobSelect(jobs);
        const fromUrl = parseJobIdFromUrl();
        const fromStore = readStoredJobId();
        prepJobId = pickInitialJobId(jobs, fromUrl ?? fromStore);
        const sel = document.getElementById('prep-job-select');
        if (sel && prepJobId) {
          sel.value = String(prepJobId);
          writeStoredJobId(prepJobId);
        }
        const hint = document.getElementById('prep-job-hint');
        if (hint && jobs.length > 1) {
          hint.hidden = false;
        }
        return jobs;
      })
      .catch((err) => {
        console.error('prep: failed to load jobs', err);
        jobsLoadPromise = null;
        throw err;
      });
  }
  return jobsLoadPromise;
}

async function ensurePrepJobId() {
  if (prepJobId) return prepJobId;
  await loadPrepJobsOnce();
  return prepJobId;
}

async function warmResponse(userText) {
  const jobId = await ensurePrepJobId();
  if (!jobId) {
    return 'No job context found yet. Add listings from the job board, then pick a role above.';
  }

  const csrfToken = getCsrfToken();
  const payload = {
    message: userText,
    topic: 'general-interview',
    job_id: jobId,
  };

  const res = await fetch('/chat/api/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    return `Interview coach unavailable. (${res.status}) ${txt}`;
  }

  const data = await res.json();
  if (data?.job_id) {
    prepJobId = data.job_id;
    const sel = document.getElementById('prep-job-select');
    if (sel) sel.value = String(prepJobId);
    writeStoredJobId(prepJobId);
  }
  const assistant = String(data?.assistant_message || '').trim();
  return assistant || 'Let us continue. Tell me your next answer.';
}

async function loadHistory() {
  const res = await fetch('/chat/history/', {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

function initPrep() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const logout = document.getElementById('logout-action');
  const sel = document.getElementById('prep-job-select');

  if (logout) {
    logout.addEventListener('click', (event) => {
      event.preventDefault();
      window.location.href = '/logout/';
    });
  }

  if (sel) {
    sel.addEventListener('change', () => {
      const v = parseInt(sel.value, 10);
      prepJobId = Number.isFinite(v) ? v : null;
      if (prepJobId) {
        writeStoredJobId(prepJobId);
        const url = new URL(window.location.href);
        url.searchParams.set('job_id', String(prepJobId));
        window.history.replaceState({}, '', url.toString());
      }
    });
  }

  loadPrepJobsOnce().catch(() => {
    const selEl = document.getElementById('prep-job-select');
    if (selEl) {
      selEl.innerHTML = '<option value="">Could not load listings</option>';
      selEl.disabled = true;
    }
  });

  loadHistory().then((rows) => {
    if (!rows.length) {
      appendBubble({
        role: 'assistant',
        text: 'Hi. I am your interview coach. Pick which listing you want to practice for above, then share a first answer and we will go step by step.',
      });
      return;
    }
    rows.forEach((row) => appendBubble({ role: row.role, text: row.content }));
  });

  let isThinking = false;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (isThinking) return;

    const text = input.value.trim();
    if (!text) {
      input.focus({ preventScroll: true });
      return;
    }

    isThinking = true;
    setTyping(true);
    appendBubble({ role: 'user', text });
    input.value = '';

    const delay = 850 + Math.random() * 650;
    window.setTimeout(async () => {
      const response = await warmResponse(text);
      appendBubble({ role: 'ai', text: response });
      setTyping(false);
      isThinking = false;
    }, delay);
  });
}

document.addEventListener('DOMContentLoaded', initPrep);
