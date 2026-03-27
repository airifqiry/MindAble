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

function warmResponse(topicId, userText) {
  const energy = getEnergy();
  const brief = energy === 'low';
  const detailed = energy === 'high';

  const lead = 'Thanks for sharing. You’re doing a really solid job putting it into words.';

  if (topicId === 'about-yourself') {
    if (brief) {
      return `${lead}\n\nA simple structure: (1) what you do best, (2) how you work, (3) what you’re looking for next.`;
    }
    if (detailed) {
      return `${lead}\n\nTry this flow:\n1) One line on your strengths\n2) A specific example (what you did, what improved)\n3) How you like to work (communication + pace)\n4) What you want next (fit + impact)\n\nIf you want, paste your draft and I’ll help you tighten it gently.`;
    }
    return `${lead}\n\nStructure that usually lands well:\n- Strength\n- Example\n- What you need to thrive (calm pace, clear instructions, etc.)`;
  }

  if (topicId === 'strengths-challenges') {
    if (brief) {
      return `${lead}\n\nKeep challenges framed as “needs” (what makes it easier) rather than “failures.” A calm sentence + a supportive adjustment works well.`;
    }
    if (detailed) {
      return `${lead}\n\nA good interview-ready pattern:\n1) Strength (what you do consistently)\n2) Evidence (a moment it helped)\n3) Challenge (what gets hard)\n4) Adjustment (a clear accommodation)\n5) Result (how it improves)\n\nWant to tell me your biggest strength first?`;
    }
    return `${lead}\n\nFor challenges, aim for: “When X happens, I do best with Y.” That keeps it honest and protective.`;
  }

  if (topicId === 'workplace-needs') {
    if (brief) {
      return `${lead}\n\nTurn needs into interview-friendly priorities: environment, communication style, and scheduling. Keep it concrete and kind.`;
    }
    if (detailed) {
      return `${lead}\n\nLet’s turn your needs into a short “workplace passport”:\n- Environment (quiet/open, noise level)\n- Communication (written vs meetings, response times)\n- Rhythm (start times, predictability, meeting cadence)\n- Boundaries (what you need respected)\n\nReply with one example situation and we’ll polish it.`;
    }
    return `${lead}\n\nA useful way to phrase this: “I thrive when…” then name 2-3 conditions (communication + pace are a great start).`;
  }

  return `${lead}\n\nTell me a bit more, and we’ll shape it into a calm, clear answer.`;
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
    window.setTimeout(() => {
      const response = warmResponse(topicId, text);
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

