function getStoredString(key, fallback) {
  const val = window.localStorage.getItem(key);
  if (!val) return fallback;
  return String(val);
}

function getEnergy() {
  const energy = window.localStorage.getItem('mindable_energy');
  if (energy === 'low' || energy === 'medium' || energy === 'high') return energy;
  return 'medium';
}

function updateEnergyUI(energy) {
  const note = document.getElementById('energy-note');
  if (!note) return;

  if (energy === 'low') {
    note.textContent = 'Low-energy mode is on. Expect calmer suggestions and easier next steps.';
  } else if (energy === 'high') {
    note.textContent = 'High-energy mode is on. You can handle more intensity today.';
  } else {
    note.textContent = 'Medium-energy mode is on. Balanced matches, steady pacing.';
  }
}

function initDashboard() {
  const nameEl = document.getElementById('user-name');
  if (nameEl) {
    nameEl.textContent = getStoredString('mindable_user_name', 'Alex');
  }

  const completionEl = document.getElementById('profile-percent');
  const fillEl = document.getElementById('profile-progress-fill');
  if (completionEl && fillEl) {
    const raw = window.localStorage.getItem('mindable_profile_completion');
    let pct = Number(raw);
    if (!Number.isFinite(pct)) pct = 0.65;
    pct = Math.max(0, Math.min(1, pct));

    const shown = Math.round(pct * 100);
    completionEl.textContent = `${shown}%`;
    fillEl.style.width = `${shown}%`;
  }

  const energy = getEnergy();
  document.body.dataset.energy = energy;

  const energyInputs = document.querySelectorAll('input[name="energy"]');
  energyInputs.forEach(input => {
    if (input.value === energy) input.checked = true;
  });
  updateEnergyUI(energy);

  energyInputs.forEach(input => {
    input.addEventListener('change', () => {
      const nextEnergy = input.value;
      window.localStorage.setItem('mindable_energy', nextEnergy);
      document.body.dataset.energy = nextEnergy;
      updateEnergyUI(nextEnergy);
    });
  });

  const logout = document.getElementById('logout-action');
  if (logout) {
    logout.addEventListener('click', event => {
      event.preventDefault();
      window.location.href = '/logout/';
    });
  }
}

document.addEventListener('DOMContentLoaded', initDashboard);

