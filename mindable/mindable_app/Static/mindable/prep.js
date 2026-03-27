const TOPICS = [
  {
    id: 'about-yourself',
    label: 'Tell me about yourself'
  },
  {
    id: 'strengths-challenges',
    label: 'Strengths & challenges'
  },
  {
    id: 'workplace-needs',
    label: 'Workplace needs'
  }
];

function getEnergy() {
  const energy = window.localStorage.getItem('mindable_energy');
  if (energy === 'low' || energy === 'medium' || energy === 'high') return energy;
  return 'medium';
}

function setActiveTopicUI(topicId) {
  const btns = document.querySelectorAll('.topic-btn[data-topic]');
  btns.forEach(btn => {
    const isActive = btn.dataset.topic === topicId;
    btn.classList.toggle('is-active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });

  const topicEl = document.getElementById('current-topic');
  if (topicEl) {
    const match = TOPICS.find(t => t.id === topicId);
    if (match) topicEl.textContent = match.label;
  }
}

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

let prepJobId = null;
let prepFeedbackByJobId = null;

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

async function ensurePrepJobId() {
  if (prepJobId) return prepJobId;

  const res = await fetch('/api/jobs/?page=1', {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) return null;

  const data = await res.json();
  const jobs = Array.isArray(data) ? data : (data.results || data.jobs || []);
  prepJobId = jobs?.[0]?.id ?? null;
  return prepJobId;
}

async function ensureFeedbackMap(jobId) {
  if (prepFeedbackByJobId) return prepFeedbackByJobId;

  const res = await fetch('/api/feedback/', {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) {
    prepFeedbackByJobId = {};
    return prepFeedbackByJobId;
  }

  const data = await res.json();
  const list = Array.isArray(data) ? data : (data.results || []);
  prepFeedbackByJobId = {};
  list.forEach(item => {
    if (item?.job != null) prepFeedbackByJobId[String(item.job)] = item;
  });
  return prepFeedbackByJobId;
}

// Backend-wired response: saves the user's note via /api/feedback/.
// NOTE: The current backend stores JobFeedback (job + status + note), not an AI-generated response.
async function warmResponse(topicId, userText) {
  const jobId = await ensurePrepJobId();
  if (!jobId) return 'No job context found yet. Please check your job board first.';

  const csrfToken = getCsrfToken();
  const payload = { job: jobId, status: 'saved', note: userText };

  const feedbackMap = await ensureFeedbackMap(jobId);
  const existing = feedbackMap[String(jobId)];

  let res;
  if (existing) {
    res = await fetch(`/api/feedback/${existing.id}/`, {
      method: 'PATCH',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    });
  } else {
    res = await fetch('/api/feedback/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    });
  }

  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    return `Could not save your prep message. (${res.status}) ${txt}`;
  }

  const data = await res.json();
  // Show a simple confirmation using backend response.
  if (data?.note) return `Saved. ${data.note}`;
  return 'Saved.';
}

function initPrep() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const changeLink = document.getElementById('change-topic-link');
  const logout = document.getElementById('logout-action');

  if (logout) {
    logout.addEventListener('click', event => {
      event.preventDefault();
      window.location.href = '/logout/';
    });
  }

  let topicId = window.localStorage.getItem('mindable_prep_topic');
  if (!TOPICS.some(t => t.id === topicId)) topicId = TOPICS[0].id;

  setActiveTopicUI(topicId);

  const btns = document.querySelectorAll('.topic-btn[data-topic]');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      const next = btn.dataset.topic;
      topicId = next;
      window.localStorage.setItem('mindable_prep_topic', next);
      setActiveTopicUI(next);

      const initial = `Great choice. We’ll practice: ${TOPICS.find(t => t.id === next).label}. When you’re ready, send a message.`;
      appendBubble({ role: 'ai', text: initial });
    });
  });

  let isThinking = false;

  form.addEventListener('submit', event => {
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
      const response = await warmResponse(topicId, text);
      appendBubble({ role: 'ai', text: response });
      setTyping(false);
      isThinking = false;
    }, delay);
  });

  if (changeLink) {
    changeLink.addEventListener('click', event => {
      event.preventDefault();
      const sidebar = document.getElementById('topic-sidebar');
      if (sidebar) sidebar.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}

document.addEventListener('DOMContentLoaded', initPrep);

