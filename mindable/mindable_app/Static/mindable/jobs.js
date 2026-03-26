const JOBS = [
  {
    id: 'job-1',
    title: 'Frontend Accessibility Specialist',
    company: 'CalmStack',
    description: 'Design interfaces that feel safe, clear, and low-friction for everyone.',
    mode: 'Remote',
    demand: 'low',
    tags: ['Async-first', 'No cold calls', 'Clear specs'],
    flagged: false
  },
  {
    id: 'job-2',
    title: 'UX Research Coordinator',
    company: 'NeuroWorks',
    description: 'Support studies with structured questions and predictable timelines.',
    mode: 'Hybrid',
    demand: 'medium',
    tags: ['Written comms', 'Flexible schedule', 'Quiet sessions'],
    flagged: false
  },
  {
    id: 'job-3',
    title: 'Content Ops (Editorial)',
    company: 'Gentle Media',
    description: 'Keep publishing smooth with templates, review checklists, and calm workflows.',
    mode: 'Remote',
    demand: 'medium',
    tags: ['Templates', 'No multitasking spikes', 'Low meetings'],
    flagged: true
  },
  {
    id: 'job-4',
    title: 'Customer Support (Structured)',
    company: 'Baseline Care',
    description: 'Answer tickets with calm scripts, clear escalation paths, and consistent hours.',
    mode: 'Hybrid',
    demand: 'low',
    tags: ['W-2 hours', 'Step-by-step', 'No phone queue'],
    flagged: false
  },
  {
    id: 'job-5',
    title: 'Product Analyst (Decision Support)',
    company: 'Steady Metrics',
    description: 'Turn data into simple recommendations without high-pressure dashboards.',
    mode: 'Remote',
    demand: 'high',
    tags: ['Deep work', 'Small team', 'No last-minute pivots'],
    flagged: false
  },
  {
    id: 'job-6',
    title: 'Operations Assistant (Private Office)',
    company: 'Focus Harbor',
    description: 'Coordinate schedules and materials in a low-noise environment.',
    mode: 'In-person',
    demand: 'low',
    tags: ['Private space', 'Clear routines', 'Low noise'],
    flagged: false
  },
  {
    id: 'job-7',
    title: 'Marketing Coordinator (Async Campaigns)',
    company: 'Soft Launch Co.',
    description: 'Write and schedule content using shared calendars and review steps.',
    mode: 'Remote',
    demand: 'medium',
    tags: ['Async campaigns', 'No cold outreach', 'Rough drafts welcome'],
    flagged: false
  },
  {
    id: 'job-8',
    title: 'Engineering QA (Scripted Testing)',
    company: 'TrustWorks',
    description: 'Run checklists and log results with predictable processes.',
    mode: 'Hybrid',
    demand: 'low',
    tags: ['Checklists', 'Documented process', 'Low escalation'],
    flagged: false
  },
  {
    id: 'job-9',
    title: 'Project Coordinator (Structured Delivery)',
    company: 'CalmBuild',
    description: 'Coordinate tasks with timelines, agendas, and documented handoffs.',
    mode: 'In-person',
    demand: 'medium',
    tags: ['Written updates', 'Agenda every meeting', 'No chaos sprints'],
    flagged: true
  },
  {
    id: 'job-10',
    title: 'Technical Writer (Knowledge Base)',
    company: 'Clarity Docs',
    description: 'Turn complex features into approachable, consistent documentation.',
    mode: 'Remote',
    demand: 'low',
    tags: ['Single-source docs', 'Clear drafts', 'Quiet review'],
    flagged: false
  },
  {
    id: 'job-11',
    title: 'Data Support Assistant (Office Hours)',
    company: 'Study Lane',
    description: 'Help teams with lightweight analysis during scheduled office hours.',
    mode: 'In-person',
    demand: 'high',
    tags: ['Office hours', 'Predictable rhythm', 'Small prompts'],
    flagged: false
  },
  {
    id: 'job-12',
    title: 'Community Moderator (Warm, Structured)',
    company: 'Kind Forums',
    description: 'Moderate conversations using written guidelines and calm escalation.',
    mode: 'Hybrid',
    demand: 'medium',
    tags: ['Guidelines', 'Low toxicity handling', 'Clear steps'],
    flagged: false
  },
  {
    id: 'job-13',
    title: 'Operations Coordinator (Low-noise)',
    company: 'Quiet Logistics',
    description: 'Coordinate shipments with checklists and fewer interruptions.',
    mode: 'In-person',
    demand: 'low',
    tags: ['Checklists', 'Low interruptions', 'Clear ownership'],
    flagged: false
  },
  {
    id: 'job-14',
    title: 'Design Systems Intern (Guided Work)',
    company: 'Glass Palette',
    description: 'Build consistent components with clear constraints and review loops.',
    mode: 'Remote',
    demand: 'medium',
    tags: ['Mentored tasks', 'No rapid pivots', 'Review checklists'],
    flagged: false
  },
  {
    id: 'job-15',
    title: 'Training Coordinator (Written Materials)',
    company: 'Gentle Onboarding',
    description: 'Prepare training packets with step-by-step learning paths.',
    mode: 'Remote',
    demand: 'low',
    tags: ['Written training', 'Small group sessions', 'Predictable pace'],
    flagged: true
  },
  {
    id: 'job-16',
    title: 'QA Analyst (Calm Release Cycles)',
    company: 'Steady Quality',
    description: 'Validate releases with calm cadence and documented test cases.',
    mode: 'Hybrid',
    demand: 'high',
    tags: ['Release windows', 'Clear tests', 'No heroics'],
    flagged: false
  },
  {
    id: 'job-17',
    title: 'Administrative Support (Calendar-first)',
    company: 'Calendar Harbor',
    description: 'Support scheduling with consistent templates and clear handoffs.',
    mode: 'In-person',
    demand: 'medium',
    tags: ['Calendar-first', 'Structured tasks', 'Low noise'],
    flagged: false
  },
  {
    id: 'job-18',
    title: 'Product Support (Async Tickets)',
    company: 'Slow & Steady',
    description: 'Handle support tickets with async responses and predictable workflows.',
    mode: 'Remote',
    demand: 'medium',
    tags: ['Async tickets', 'No phone', 'Clear escalation'],
    flagged: false
  }
];

const PAGE_SIZE = 6;

let dismissedIds = new Set();
let filtered = [];
let nextIndex = 0;
let targetCount = PAGE_SIZE;
let renderedIds = new Set();

function getSelectedModes() {
  const selected = new Set();
  document.querySelectorAll('input[name="mode"]:checked').forEach(input => {
    selected.add(input.value);
  });
  return selected;
}

function getSelectedDemand() {
  const input = document.querySelector('input[name="demand"]:checked');
  return input ? input.value : 'medium';
}

function getDefaultDemandFromEnergy() {
  const energy = window.localStorage.getItem('mindable_energy');
  if (energy === 'low' || energy === 'medium' || energy === 'high') return energy;
  return 'medium';
}

function createTagChip(tag) {
  const el = document.createElement('span');
  el.className = 'tag-chip';
  el.textContent = tag;
  el.setAttribute('aria-hidden', 'true');
  return el;
}

function createJobCard(job) {
  const card = document.createElement('article');
  card.className = 'job-card reveal';
  card.dataset.jobId = job.id;
  card.tabIndex = 0;

  const head = document.createElement('div');
  head.className = 'job-head';

  const main = document.createElement('div');
  main.className = 'job-main';

  const title = document.createElement('h2');
  title.className = 'job-title';
  title.textContent = job.title;

  const company = document.createElement('div');
  company.className = 'job-company';
  company.textContent = job.company;

  const desc = document.createElement('div');
  desc.className = 'job-desc';
  desc.textContent = job.description;

  main.appendChild(title);
  main.appendChild(company);
  main.appendChild(desc);

  const actions = document.createElement('div');
  actions.className = 'job-actions';

  const viewBtn = document.createElement('button');
  viewBtn.type = 'button';
  viewBtn.className = 'btn-primary';
  viewBtn.textContent = 'View role';
  viewBtn.addEventListener('click', () => {
    window.alert(`Viewing: ${job.title} at ${job.company}`);
  });

  const dismissBtn = document.createElement('button');
  dismissBtn.type = 'button';
  dismissBtn.className = 'btn-ghost';
  dismissBtn.textContent = 'Not for me';
  dismissBtn.addEventListener('click', () => {
    card.classList.add('is-fading');
    window.setTimeout(() => {
      dismissedIds.add(job.id);
      renderedIds.delete(job.id);
      card.remove();
      renderUpToTarget();
    }, 220);
  });

  actions.appendChild(viewBtn);
  actions.appendChild(dismissBtn);

  head.appendChild(main);
  head.appendChild(actions);

  const tags = document.createElement('div');
  tags.className = 'job-tags';
  job.tags.forEach(t => tags.appendChild(createTagChip(t)));

  card.appendChild(head);

  if (job.flagged) {
    const tox = document.createElement('div');
    tox.className = 'toxicity-pill';
    tox.textContent = 'Content flagged';
    card.appendChild(tox);
  }

  card.appendChild(tags);

  return card;
}

function renderUpToTarget() {
  const feed = document.getElementById('job-feed');
  if (!feed) return;

  let safety = 0;
  while (renderedIds.size < targetCount && nextIndex < filtered.length) {
    safety += 1;
    if (safety > 1000) break;

    const job = filtered[nextIndex];
    nextIndex += 1;
    if (dismissedIds.has(job.id)) continue;
    if (renderedIds.has(job.id)) continue;

    renderedIds.add(job.id);
    feed.appendChild(createJobCard(job));
  }

  // Let the reveal observer bind any newly added cards.
  if (typeof window.setupScrollReveal === 'function') window.setupScrollReveal();

  const loadMore = document.getElementById('load-more');
  if (loadMore) {
    if (nextIndex >= filtered.length) loadMore.style.display = 'none';
    else loadMore.style.display = 'inline-flex';
  }
}

function resetResults() {
  const feed = document.getElementById('job-feed');
  if (!feed) return;
  feed.innerHTML = '';
  renderedIds = new Set();
  nextIndex = 0;
  targetCount = PAGE_SIZE;

  const modes = getSelectedModes();
  const demand = getSelectedDemand();
  filtered = JOBS.filter(job => modes.has(job.mode) && job.demand === demand);

  renderUpToTarget();
}

function initFilters() {
  const defaultDemand = getDefaultDemandFromEnergy();
  document.querySelectorAll('input[name="demand"]').forEach(input => {
    if (input.value === defaultDemand) input.checked = true;
  });

  document.querySelectorAll('input[name="mode"], input[name="demand"]').forEach(input => {
    input.addEventListener('change', () => resetResults());
  });

  const loadMore = document.getElementById('load-more');
  if (loadMore) {
    loadMore.addEventListener('click', () => {
      targetCount += PAGE_SIZE;
      renderUpToTarget();
    });
  }

  const logout = document.getElementById('logout-action');
  if (logout) {
    logout.addEventListener('click', event => {
      event.preventDefault();
      window.location.href = '/logout/';
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initFilters();
  resetResults();
});

