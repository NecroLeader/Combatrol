/* ══════════════════════════════════════
   SETUP
══════════════════════════════════════ */

// Selección de modo
document.querySelectorAll('.mode-card').forEach(card => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    State.mode = card.dataset.mode;
  });
});

// Botón iniciar
document.getElementById('btn-start').addEventListener('click', startBattle);

// Botón volver
document.getElementById('btn-back').addEventListener('click', () => {
  showView('setup');
  State.battleId = null;
  State.running  = false;
});

async function startBattle() {
  const nameP1   = document.getElementById('cfg-name-p1').value.trim() || 'P1';
  const nameP2   = document.getElementById('cfg-name-p2').value.trim() || 'P2';
  const arena    = document.getElementById('cfg-arena').value   || null;
  const weaponP1 = document.getElementById('cfg-weapon-p1').value || null;
  const weaponP2 = document.getElementById('cfg-weapon-p2').value || null;

  try {
    const data = await apiPost('/battle/start', {
      mode:      State.mode,
      arena_code: arena,
      weapon_p1: weaponP1,
      weapon_p2: weaponP2,
      name_p1:   nameP1,
      name_p2:   nameP2,
    });

    State.battleId = data.battle_id;
    State.nameP1   = data.p1.name;
    State.nameP2   = data.p2.name;

    // Poblar UI de batalla
    document.getElementById('b-id').textContent    = `#${data.battle_id}`;
    document.getElementById('b-mode').textContent  = State.mode;
    document.getElementById('b-arena').textContent = data.arena || 'aleatoria';
    document.getElementById('p1-name').textContent = State.nameP1;
    document.getElementById('p2-name').textContent = State.nameP2;
    document.getElementById('p1-weapon').textContent = data.p1.weapon;
    document.getElementById('p2-weapon').textContent = data.p2.weapon;
    document.getElementById('p2-action-name').textContent = State.nameP2;
    document.getElementById('log-entries').innerHTML = '';

    resetCards();
    setupActionPanel();
    resetActions();
    showView('battle');
    document.getElementById('winner-overlay').style.display = 'none';
  } catch (e) {
    alert('Error al iniciar: ' + e.message);
  }
}

/* ══════════════════════════════════════
   PANEL DE ACCIONES
══════════════════════════════════════ */

function setupActionPanel() {
  const panel = document.getElementById('action-panel');
  const p2panel = document.getElementById('p2-action-panel');
  const rollBtn = document.getElementById('btn-roll');
  const simAllBtn = document.getElementById('btn-sim-all');

  if (State.mode === 'SIMULATION') {
    panel.style.display = 'none';
    rollBtn.disabled = false;
    rollBtn.textContent = '🎲 Tirar Dado (IA)';
    simAllBtn.style.display = 'inline-block';
    p2panel.style.display = 'none';
  } else if (State.mode === 'PVE') {
    panel.style.display = 'block';
    p2panel.style.display = 'none';
    rollBtn.textContent = '🎲 Tirar Dado';
    simAllBtn.style.display = 'none';
  } else { // PVP
    panel.style.display = 'block';
    p2panel.style.display = 'block';
    rollBtn.textContent = '🎲 Tirar Dado';
    simAllBtn.style.display = 'none';
  }
}

// Registrar clicks en botones de acción
document.querySelectorAll('.action-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const phase  = parseInt(btn.dataset.phase);
    const action = btn.dataset.action;
    const isP2   = btn.classList.contains('p2-btn');

    // Deseleccionar los otros de la misma fase y jugador
    const selector = isP2
      ? `.action-btn.p2-btn[data-phase="${phase}"]`
      : `.action-btn:not(.p2-btn)[data-phase="${phase}"]`;

    document.querySelectorAll(selector).forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');

    if (isP2) {
      State.actionsP2[phase] = action;
    } else {
      State.actionsP1[phase] = action;
    }

    updateRollButton();
  });
});

function updateRollButton() {
  if (State.mode === 'SIMULATION') return;
  const p1ready = State.actionsP1.every(a => a !== null);
  const p2ready = State.mode === 'PVP' ? State.actionsP2.every(a => a !== null) : true;
  document.getElementById('btn-roll').disabled = !(p1ready && p2ready);
}

function resetActions() {
  State.actionsP1 = [null, null, null];
  State.actionsP2 = [null, null, null];
  document.querySelectorAll('.action-btn').forEach(b => b.classList.remove('selected'));
  if (State.mode !== 'SIMULATION') {
    document.getElementById('btn-roll').disabled = true;
  }
}

/* ══════════════════════════════════════
   TIRAR DADO — turno completo
══════════════════════════════════════ */

async function doTurn() {
  if (!State.battleId || State.running) return;
  State.running = true;

  try {
    let body = {};
    if (State.mode === 'PVE') {
      body = { p1_actions: [...State.actionsP1] };
    } else if (State.mode === 'PVP') {
      body = { p1_actions: [...State.actionsP1], p2_actions: [...State.actionsP2] };
    }

    const data = await apiPost(`/battle/${State.battleId}/simulate`, body);
    data.phases.forEach(renderPhase);
    await refreshCards();

    if (data.phases.some(p => p.battle_over)) {
      const winner = data.phases.find(p => p.battle_over)?.winner;
      showWinner(winner);
    } else {
      resetActions();
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }

  State.running = false;
}

/* ══════════════════════════════════════
   SIMULAR HASTA EL FINAL (solo SIMULATION)
══════════════════════════════════════ */

async function simulateAll() {
  if (!State.battleId || State.running) return;
  State.running = true;

  document.getElementById('btn-roll').disabled = true;
  document.getElementById('btn-sim-all').disabled = true;

  try {
    let over = false;
    while (!over) {
      const data = await apiPost(`/battle/${State.battleId}/simulate`, {});
      data.phases.forEach(renderPhase);
      over = data.phases.some(p => p.battle_over);
      await refreshCards();
      if (!over) await sleep(280);
    }
    const lastPhases = document.querySelectorAll('.log-entry');
    const winner = [...lastPhases].map(el => el.dataset.winner).find(w => w);
    showWinner(winner);
  } catch (e) {
    alert('Error: ' + e.message);
  }

  State.running = false;
  document.getElementById('btn-sim-all').disabled = false;
}

/* ══════════════════════════════════════
   REFRESH TARJETAS
══════════════════════════════════════ */

async function refreshCards() {
  const data = await apiGet(`/battle/${State.battleId}`);
  const s1 = data.p1.state;
  const s2 = data.p2.state;

  updateCard('p1', s1?.counters ?? 0, data.p1.effects || []);
  updateCard('p2', s2?.counters ?? 0, data.p2.effects || []);
}

function updateCard(side, counters, effects) {
  const pct = Math.min(counters / 15 * 100, 100);
  const bar = document.getElementById(`${side}-bar`);
  bar.style.width = pct + '%';

  if (pct > 66)      bar.style.background = 'var(--red)';
  else if (pct > 40) bar.style.background = 'var(--yellow)';
  else               bar.style.background = 'var(--green)';

  document.getElementById(`${side}-cnt`).textContent = counters.toFixed(1);

  const card = document.getElementById(`card-${side}`);
  card.className = 'player-card';
  if (pct > 80)      card.classList.add('danger');
  else if (pct > 55) card.classList.add('warning');

  const efDiv = document.getElementById(`${side}-effects`);
  efDiv.innerHTML = effects.map(e => `<span class="tag">${e}</span>`).join('');
}

function resetCards() {
  ['p1','p2'].forEach(side => {
    document.getElementById(`${side}-cnt`).textContent = '0.0';
    document.getElementById(`${side}-bar`).style.width = '0%';
    document.getElementById(`${side}-bar`).style.background = 'var(--green)';
    document.getElementById(`${side}-effects`).innerHTML = '';
    document.getElementById(`card-${side}`).className = 'player-card';
  });
}

/* ══════════════════════════════════════
   RENDER FASE EN EL LOG
══════════════════════════════════════ */

function renderPhase(p) {
  const el = document.createElement('div');
  el.className = 'log-entry';
  el.dataset.winner = p.winner || '';

  const actionLabel = {ATK: '⚔ Ataque', DEF: '🛡 Defensa', INT: '🔀 Maniobra'};
  const nameP1 = State.nameP1;
  const nameP2 = State.nameP2;

  const effectsHtml = [p.effect_applied_p1, p.effect_applied_p2]
    .filter(Boolean)
    .map(e => `<span class="tag">${e}</span>`)
    .join('');

  const mathHtml = `
    <div class="log-math${State.showMath ? ' visible' : ''}">
      <b>Turno</b> ${p.turn_number} &nbsp;·&nbsp;
      <b>Fase</b> ${p.phase_number} &nbsp;·&nbsp;
      <b>Par</b> ${p.action_pair}<br>
      <b>Banda</b> ${p.difference_band} &nbsp;·&nbsp;
      <b>Contexto</b> ${p.power_context}<br>
      <b>Dado bruto</b> ${nameP1} ${p.roll_p1} vs ${nameP2} ${p.roll_p2} &nbsp;·&nbsp;
      <b>Efectivo</b> ${p.effective_p1.toFixed(1)} vs ${p.effective_p2.toFixed(1)}<br>
      <b>Poder</b> P${p.power_p1} vs P${p.power_p2} &nbsp;·&nbsp;
      <b>Diferencia</b> ${p.difference.toFixed(1)}<br>
      <b>Outcome</b> ${p.outcome_code} &nbsp;·&nbsp;
      <b>Ganador fase</b> ${p.phase_winner} &nbsp;·&nbsp;
      <b>Ganador dado</b> ${p.roll_winner}
    </div>
  `;

  el.innerHTML = `
    <div class="log-phase-header">
      T${p.turn_number}·F${p.phase_number} &nbsp;|&nbsp;
      ${nameP1}: ${actionLabel[p.action_p1] || p.action_p1} &nbsp;vs&nbsp;
      ${nameP2}: ${actionLabel[p.action_p2] || p.action_p2}
    </div>
    <div class="log-narrative">"${p.narrative_text}"</div>
    <div class="log-counters">
      <span class="log-cnt-p1">${nameP1} → ${p.counters_p1.toFixed(1)} cnt (+${p.counter_dmg_p1})</span>
      <span class="log-cnt-p2">${nameP2} → ${p.counters_p2.toFixed(1)} cnt (+${p.counter_dmg_p2})</span>
    </div>
    ${effectsHtml ? `<div class="log-effects">${effectsHtml}</div>` : ''}
    ${mathHtml}
    ${p.battle_over ? `<div style="margin-top:8px; color:var(--gold); letter-spacing:2px; font-size:0.85rem">
      ⚔ FIN — VICTORIA: ${p.winner === 'P1' ? nameP1 : p.winner === 'P2' ? nameP2 : p.winner}
    </div>` : ''}
  `;

  document.getElementById('log-entries').prepend(el);
}

/* ══════════════════════════════════════
   MATH TOGGLE
══════════════════════════════════════ */

function toggleMath() {
  State.showMath = !State.showMath;
  const btn = document.getElementById('btn-math-toggle');
  btn.textContent = State.showMath ? 'Ocultar math' : 'Mostrar math';

  document.querySelectorAll('.log-math').forEach(el => {
    el.classList.toggle('visible', State.showMath);
  });
}

/* ══════════════════════════════════════
   WINNER
══════════════════════════════════════ */

function showWinner(side) {
  const name = side === 'P1' ? State.nameP1 : side === 'P2' ? State.nameP2 : side;
  document.getElementById('winner-name').textContent = name;
  document.getElementById('winner-overlay').style.display = 'flex';
  document.getElementById('btn-roll').disabled = true;
  document.getElementById('btn-sim-all').disabled = true;
}

/* ══════════════════════════════════════
   UTILS
══════════════════════════════════════ */

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
