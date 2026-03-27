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

async function warmResponse(userText) {
  const jobId = await ensurePrepJobId();
  if (!jobId) return 'No job context found yet. Please check your job board first.';

  const csrfToken = getCsrfToken();
  const payload = {
    message: userText,
    topic: 'general-interview',
    job_id: jobId
  };

  const res = await fetch('/chat/api/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    return `Interview coach unavailable. (${res.status}) ${txt}`;
  }

  const data = await res.json();
  prepJobId = data?.job_id || prepJobId;
  const assistant = String(data?.assistant_message || '').trim();
  return assistant || 'Let us continue. Tell me your next answer.';
}

async function loadHistory() {
  const res = await fetch('/chat/history/', {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

function initPrep() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const logout = document.getElementById('logout-action');

  if (logout) {
    logout.addEventListener('click', event => {
      event.preventDefault();
      window.location.href = '/logout/';
    });
  }

  loadHistory().then(rows => {
    if (!rows.length) {
      appendBubble({
        role: 'assistant',
        text: 'Hi. I am your interview coach. Share a first answer, and we will practice step by step.'
      });
      return;
    }
    rows.forEach(row => appendBubble({ role: row.role, text: row.content }));
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
      const response = await warmResponse(text);
      appendBubble({ role: 'ai', text: response });
      setTyping(false);
      isThinking = false;
    }, delay);
  });
}

document.addEventListener('DOMContentLoaded', initPrep);

