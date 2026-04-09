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

async function startBattle(config = null) {
  const nameP1   = (config?.nameP1   ?? document.getElementById('cfg-name-p1').value.trim()) || 'P1';
  const nameP2   = (config?.nameP2   ?? document.getElementById('cfg-name-p2').value.trim()) || 'P2';
  const arena    = (config?.arena    ?? document.getElementById('cfg-arena').value)   || null;
  const weaponP1 = (config?.weaponP1 ?? document.getElementById('cfg-weapon-p1').value) || null;
  const weaponP2 = (config?.weaponP2 ?? document.getElementById('cfg-weapon-p2').value) || null;
  const mode     = config?.mode     ?? State.mode;

  // Guardar config para rematch
  State.lastConfig = { nameP1, nameP2, arena, weaponP1, weaponP2, mode };
  State.mode = mode;
  State.phases = [];

  try {
    const data = await apiPost('/battle/start', {
      mode:       mode,
      arena_code: arena,
      weapon_p1:  weaponP1,
      weapon_p2:  weaponP2,
      name_p1:    nameP1,
      name_p2:    nameP2,
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

    resetCards();
    updateEntorno([]);
    updatePhaseTracker();
    document.getElementById('phase-math-log').innerHTML = '';
    document.getElementById('log-entries').innerHTML = '';
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

    // In PVE/PVP show phases one-by-one as cards; SIMULATION renders directly
    if (State.mode !== 'SIMULATION') {
      await showPhaseCarousel(data.phases);
    }

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
  updateEntorno(data.entorno || []);
}

/* ══════════════════════════════════════
   GLOSARIO DE ESTADOS
══════════════════════════════════════ */

const STATE_GLOSSARY = {
  // Debuffs que bloquean o restringen
  CAIDO:              { label: 'Caído',              tip: 'Pierde la siguiente fase. Solo puede maniobrar (INT). El oponente recibe Hiper Ofensivo si no tiene debuffs.' },
  DESARMADO:          { label: 'Desarmado',          tip: 'Permanente. −3 a todas las tiradas. Sin arma de filo no puede usar ciertos outcomes fatales.' },
  ARMA_ROTA:          { label: 'Arma Rota',          tip: 'Permanente. −2 a todas las tiradas. Improvisa con lo que queda del arma.' },
  DESMEMBRADO:        { label: 'Desmembrado',        tip: 'Permanente. −5 a todas las tiradas. El cap de derrota baja de 15 a 10. Nunca puede superar tirada 20.' },
  FATIGA:             { label: 'Fatiga',              tip: 'Spam de ATK detectado. −3 a tiradas durante 1 fase del próximo turno.' },
  VACILACION:         { label: 'Vacilación',         tip: 'Tiradas bajas consecutivas. −2 a tiradas durante 2 turnos. Duda y retroceso.' },
  PANICO:             { label: 'Pánico',             tip: 'Racha de tiradas muy bajas. −3 a tiradas, no puede atacar durante 1 turno. Solo defiende o maniobra.' },
  POS_DESFAVORABLE:   { label: 'Pos. Desfavorable',  tip: 'Posición débil. −3 a tiradas hasta que cambie la posición.' },
  // Buffs
  POS_FAVORABLE:      { label: 'Pos. Favorable',     tip: 'Posición ventajosa. +3 a tiradas hasta que cambie la posición.' },
  CONTRA_EXITOSO:     { label: 'Contraataque',       tip: '+4 a la siguiente tirada. Momentum de un contraataque perfecto.' },
  HIPEROFFENSIVO:     { label: 'Hiper Ofensivo',     tip: '+5 a la siguiente tirada. Oportunidad ofensiva ante rival caído.' },
  // Entorno
  NIEBLA_EXTREMA:     { label: 'Niebla Extrema',     tip: 'Entorno. Amplifica outcomes de sorpresa y fatales. Visibilidad casi nula.' },
  VACIO:              { label: 'Vacío',               tip: 'Entorno. Borde de un precipicio. Outcomes de caída al vacío son mucho más probables.' },
  VIDRIO_ROTO:        { label: 'Vidrio Roto',        tip: 'Entorno (3 turnos). Peligro de cortes y resbalones. Moverse requiere cuidado.' },
  // Bonos de banda
  BANDA_MODERADA_BONUS: { label: '+1 Banda',         tip: 'Ventaja de diferencia moderada en dados. +1 a la siguiente tirada.' },
  BANDA_REGULAR_BONUS:  { label: '+2 Banda',         tip: 'Ventaja de diferencia regular. +2 a la siguiente tirada.' },
  BANDA_ALTA_BONUS:     { label: '+3 Banda',         tip: 'Dominio claro en el intercambio. +3 a la siguiente tirada.' },
  BANDA_MUY_ALTA_BONUS: { label: '+4 Banda',         tip: 'Diferencia muy alta. +4 a la siguiente tirada.' },
  BANDA_MAXIMA_BONUS:   { label: '+5 Banda',         tip: 'Diferencia máxima. +5 a la siguiente tirada.' },
  BANDA_EXTREMA_BONUS:  { label: '+6 Banda',         tip: 'Diferencia extrema (solo posible con buffs/debuffs). +6 a la siguiente tirada.' },
  // Otros
  MOMENTUM_OVERFLOW:  { label: 'Overflow',           tip: 'Tirada efectiva superó el máximo (25). El exceso pasa como bono a la siguiente fase.' },
  IMPROVISA:          { label: 'Improvisa',           tip: 'Sin arma formal. Improvisa con objeto del entorno o manos.' },
};

function effectTag(code, extraClass = '') {
  const info = STATE_GLOSSARY[code];
  const label = info ? info.label : code;
  const tip   = info ? ` title="${info.tip}"` : '';
  const cls   = `tag${extraClass ? ' ' + extraClass : ''}`;
  return `<span class="${cls}"${tip}>${label}</span>`;
}

function updateEntorno(effects) {
  const strip = document.getElementById('entorno-strip');
  const empty = document.getElementById('entorno-empty');
  if (!effects.length) {
    strip.innerHTML = '';
    empty.style.display = 'block';
  } else {
    strip.innerHTML = effects.map(e => effectTag(e, 'tag-entorno')).join('');
    empty.style.display = 'none';
  }
}

function updatePhaseTracker() {
  const el = document.getElementById('phase-tracker');
  if (!State.phases.length) { el.innerHTML = ''; return; }

  // Group by turn
  const turns = {};
  for (const p of State.phases) {
    if (!turns[p.turn_number]) turns[p.turn_number] = [];
    turns[p.turn_number].push(p);
  }

  el.innerHTML = Object.entries(turns).map(([t, phases]) => {
    const dots = phases.map(p => {
      const w = p.phase_winner;
      const cls = w === 'A' ? 'pt-p1' : w === 'B' ? 'pt-p2' : 'pt-tie';
      const tip = w === 'A' ? State.nameP1 : w === 'B' ? State.nameP2 : '—';
      return `<span class="pt-dot ${cls}" title="F${p.phase_number}: ${tip}">${w === 'A' ? '▲' : w === 'B' ? '▼' : '·'}</span>`;
    }).join('');
    return `<div class="pt-turn"><span class="pt-turn-label">T${t}</span>${dots}</div>`;
  }).join('');
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
  efDiv.innerHTML = effects.map(e => effectTag(e)).join('');
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
  State.phases.push(p);
  updatePhaseTracker();

  const actionLabel = {ATK: '⚔ Ataque', DEF: '🛡 Defensa', INT: '🔀 Maniobra'};
  const nameP1 = State.nameP1;
  const nameP2 = State.nameP2;

  const rollWinnerLabel = p.roll_winner === 'P1' ? nameP1 : p.roll_winner === 'P2' ? nameP2 : '—';
  const phaseWinnerLabel = p.phase_winner === 'A' ? nameP1 : p.phase_winner === 'B' ? nameP2 : '—';
  const ef1 = p.effective_p1.toFixed(1);
  const ef2 = p.effective_p2.toFixed(1);
  const mismatch = p.roll_winner !== 'NONE' && (
    (p.roll_winner === 'P1' && p.phase_winner === 'B') ||
    (p.roll_winner === 'P2' && p.phase_winner === 'A')
  );

  const effectsHtml = [p.effect_applied_p1, p.effect_applied_p2]
    .filter(Boolean)
    .map(e => effectTag(e))
    .join('');

  // ── Entrada narrativa (columna izquierda) ──────────────────────────────────
  const el = document.createElement('div');
  el.className = 'log-entry';
  el.dataset.winner = p.winner || '';
  el.innerHTML = `
    <div class="log-phase-header">
      T${p.turn_number}·F${p.phase_number} &nbsp;|&nbsp;
      ${nameP1}: ${actionLabel[p.action_p1] || p.action_p1} &nbsp;vs&nbsp;
      ${nameP2}: ${actionLabel[p.action_p2] || p.action_p2}
    </div>
    <div class="log-dice">
      <span class="dice-p1">🎲 ${nameP1} <b>${p.roll_p1}</b>${ef1 !== String(p.roll_p1) ? ` <span class="dice-eff">(ef ${ef1})</span>` : ''}</span>
      <span class="dice-vs">vs</span>
      <span class="dice-p2">🎲 ${nameP2} <b>${p.roll_p2}</b>${ef2 !== String(p.roll_p2) ? ` <span class="dice-eff">(ef ${ef2})</span>` : ''}</span>
    </div>
    <div class="log-narrative">"${p.narrative_text}"</div>
    <div class="log-counters">
      <span class="log-cnt-p1">${nameP1} → ${p.counters_p1.toFixed(1)} cnt (+${p.counter_dmg_p1})</span>
      <span class="log-cnt-p2">${nameP2} → ${p.counters_p2.toFixed(1)} cnt (+${p.counter_dmg_p2})</span>
    </div>
    ${effectsHtml ? `<div class="log-effects">${effectsHtml}</div>` : ''}
    ${p.battle_over ? `<div class="log-fin">⚔ FIN — VICTORIA: ${p.winner === 'P1' ? nameP1 : p.winner === 'P2' ? nameP2 : p.winner}</div>` : ''}
  `;
  document.getElementById('log-entries').prepend(el);

  // ── Entrada de análisis (columna derecha) ──────────────────────────────────
  const ma = document.createElement('div');
  ma.className = 'math-entry';
  ma.innerHTML = `
    <div class="math-header">T${p.turn_number}·F${p.phase_number} &nbsp; ${p.action_pair}</div>
    <div class="math-row"><span class="mk">Banda</span><span class="mv">${p.difference_band}</span></div>
    <div class="math-row"><span class="mk">Contexto</span><span class="mv">${p.power_context}</span></div>
    <div class="math-row">
      <span class="mk">Dado</span>
      <span class="mv math-p1">${nameP1} ${p.roll_p1}${ef1 !== String(p.roll_p1) ? ` (${ef1})` : ''} P${p.power_p1}</span>
      <span class="mv math-sep">·</span>
      <span class="mv math-p2">${nameP2} ${p.roll_p2}${ef2 !== String(p.roll_p2) ? ` (${ef2})` : ''} P${p.power_p2}</span>
    </div>
    <div class="math-row"><span class="mk">Diferencia</span><span class="mv">${p.difference.toFixed(1)}</span></div>
    <div class="math-row"><span class="mk">Dado ganó</span><span class="mv ${p.roll_winner === 'P1' ? 'math-p1' : p.roll_winner === 'P2' ? 'math-p2' : ''}">${rollWinnerLabel}</span></div>
    <div class="math-row"><span class="mk">Fase ganó</span><span class="mv ${p.phase_winner === 'A' ? 'math-p1' : p.phase_winner === 'B' ? 'math-p2' : ''}">${phaseWinnerLabel}${mismatch ? ' <span class="math-warn">⚠ discrepancia</span>' : ''}</span></div>
    <div class="math-outcome">${p.outcome_code}</div>
  `;
  document.getElementById('phase-math-log').prepend(ma);
}

/* ══════════════════════════════════════
   WINNER
══════════════════════════════════════ */

function showWinner(side) {
  const name = side === 'P1' ? State.nameP1 : side === 'P2' ? State.nameP2 : side;
  document.getElementById('winner-name').textContent = name;
  document.getElementById('battle-summary').innerHTML = buildSummary(side);
  buildBattleLog();
  document.getElementById('winner-overlay').style.display = 'flex';
  document.getElementById('btn-roll').disabled = true;
  document.getElementById('btn-sim-all').disabled = true;
}

function buildBattleLog() {
  const actionLabel = {ATK: '⚔ Ataque', DEF: '🛡 Defensa', INT: '🔀 Maniobra'};
  const nameP1 = State.nameP1;
  const nameP2 = State.nameP2;

  // Group phases by turn, in chronological order
  const phases = [...State.phases];
  const turns = {};
  for (const p of phases) {
    if (!turns[p.turn_number]) turns[p.turn_number] = [];
    turns[p.turn_number].push(p);
  }

  let html = '';
  for (const [t, tPhases] of Object.entries(turns)) {
    html += `<div style="font-size:0.65rem;color:#3a3a3a;letter-spacing:2px;margin-top:10px;margin-bottom:4px;">TURNO ${t}</div>`;
    for (const p of tPhases) {
      const ef1 = p.effective_p1.toFixed(1);
      const ef2 = p.effective_p2.toFixed(1);
      const phaseWinner = p.phase_winner === 'A' ? nameP1 : p.phase_winner === 'B' ? nameP2 : '—';
      const winCls = p.phase_winner === 'A' ? 'blog-winner-p1' : p.phase_winner === 'B' ? 'blog-winner-p2' : '';
      const effectsHtml = [p.effect_applied_p1, p.effect_applied_p2]
        .filter(Boolean).map(e => effectTag(e)).join(' ');

      html += `
        <div class="blog-entry">
          <div class="blog-header">F${p.phase_number} · ${actionLabel[p.action_p1]||p.action_p1} vs ${actionLabel[p.action_p2]||p.action_p2}</div>
          <div class="blog-dice">
            <span class="dice-p1">🎲 ${nameP1} <b>${p.roll_p1}</b>${ef1 !== String(p.roll_p1) ? ` (ef ${ef1})` : ''}</span>
            <span class="dice-vs">vs</span>
            <span class="dice-p2">🎲 ${nameP2} <b>${p.roll_p2}</b>${ef2 !== String(p.roll_p2) ? ` (ef ${ef2})` : ''}</span>
          </div>
          <div class="blog-narrative">"${p.narrative_text}"</div>
          <div class="blog-outcome">
            <span class="${winCls}">Fase: ${phaseWinner}</span>
            &nbsp;·&nbsp;
            <span class="log-cnt-p1">${nameP1} +${p.counter_dmg_p1}</span>
            &nbsp;·&nbsp;
            <span class="log-cnt-p2">${nameP2} +${p.counter_dmg_p2}</span>
            ${effectsHtml ? `&nbsp;${effectsHtml}` : ''}
          </div>
          ${p.battle_over ? `<div class="blog-fin">⚔ FIN · VICTORIA: ${p.winner === 'P1' ? nameP1 : nameP2}</div>` : ''}
        </div>
      `;
    }
  }

  document.getElementById('battle-log-scroll').innerHTML = html;
  // Reset collapse state
  document.getElementById('battle-log-details').removeAttribute('open');
}

function buildSummary(winningSide) {
  const phases = State.phases;
  if (!phases.length) return '';

  const loserSide = winningSide === 'P1' ? 'P2' : 'P1';
  const loserName = loserSide === 'P1' ? State.nameP1 : State.nameP2;
  const winnerName = winningSide === 'P1' ? State.nameP1 : State.nameP2;

  const turns = phases[phases.length - 1]?.turn_number ?? 1;
  const totalPhases = phases.length;

  // Counters dealt to the loser
  const dmgKey = `counter_dmg_${loserSide.toLowerCase()}`;
  const totalDmg = phases.reduce((s, p) => s + (p[dmgKey] ?? 0), 0);
  const maxHit = Math.max(...phases.map(p => p[dmgKey] ?? 0));
  const finalCounters = phases[phases.length - 1]?.[`counters_${loserSide.toLowerCase()}`]?.toFixed(1) ?? '?';

  // Effects that appeared
  const effectsP1 = phases.map(p => p.effect_applied_p1).filter(Boolean);
  const effectsP2 = phases.map(p => p.effect_applied_p2).filter(Boolean);
  const loserEffects = loserSide === 'P1' ? effectsP1 : effectsP2;
  const uniqueEffects = [...new Set(loserEffects)];

  // Decisive phase
  const finisher = phases.find(p => p.battle_over);
  const finisherPair = finisher?.action_pair ?? '?';

  const row = (label, val, cls = '') =>
    `<div class="summary-row"><span class="summary-label">${label}</span><span class="summary-val ${cls}">${val}</span></div>`;

  return `
    <div class="summary-section-title">Resultado</div>
    ${row('Ganador', winnerName, 'highlight')}
    ${row('Turnos jugados', turns)}
    ${row('Fases totales', totalPhases)}
    <div class="summary-section-title">Daño recibido por ${loserName}</div>
    ${row('Contadores finales', `${finalCounters} / 15`, parseFloat(finalCounters) >= 15 ? 'bad' : '')}
    ${row('Daño total recibido', totalDmg.toFixed(1))}
    ${row('Mayor golpe único', `+${maxHit}`, maxHit >= 3 ? 'bad' : '')}
    ${row('Par de acciones decisivo', finisherPair)}
    ${uniqueEffects.length ? `
    <div class="summary-section-title">Efectos sufridos</div>
    ${uniqueEffects.map(e => {
      const info = STATE_GLOSSARY[e];
      return `<div class="summary-effect-item">${effectTag(e)}${info ? `<span class="summary-effect-desc">${info.tip}</span>` : ''}</div>`;
    }).join('')}` : ''}
  `;
}

async function rematch() {
  document.getElementById('winner-overlay').style.display = 'none';
  await startBattle(State.lastConfig);
}

/* ══════════════════════════════════════
   PHASE CAROUSEL
══════════════════════════════════════ */

let _carouselPhases = [];
let _carouselIdx = 0;
let _carouselResolve = null;

function showPhaseCarousel(phases) {
  return new Promise(resolve => {
    _carouselPhases = phases;
    _carouselIdx = 0;
    _carouselResolve = resolve;

    const dots = document.getElementById('carousel-dots');
    dots.innerHTML = phases.map((_, i) =>
      `<span class="c-dot${i === 0 ? ' active' : ''}"></span>`
    ).join('');

    document.getElementById('carousel-turn-label').textContent =
      `TURNO ${phases[0]?.turn_number ?? '?'}`;

    _renderCarouselCard(0, 'right');
    document.getElementById('phase-carousel').style.display = 'flex';
  });
}

function _renderCarouselCard(idx, direction) {
  const p = _carouselPhases[idx];
  const actionLabel = {ATK: '⚔ Ataque', DEF: '🛡 Defensa', INT: '🔀 Maniobra'};
  const nameP1 = State.nameP1;
  const nameP2 = State.nameP2;

  const ef1 = p.effective_p1.toFixed(1);
  const ef2 = p.effective_p2.toFixed(1);
  const phaseWinner = p.phase_winner === 'A' ? nameP1 : p.phase_winner === 'B' ? nameP2 : 'Empate';
  const winCls = p.phase_winner === 'A' ? 'cwinner-p1' : p.phase_winner === 'B' ? 'cwinner-p2' : 'cwinner-tie';
  const mismatch = p.roll_winner !== 'NONE' && (
    (p.roll_winner === 'P1' && p.phase_winner === 'B') ||
    (p.roll_winner === 'P2' && p.phase_winner === 'A')
  );
  const effectsHtml = [p.effect_applied_p1, p.effect_applied_p2]
    .filter(Boolean).map(e => effectTag(e)).join(' ');

  const track = document.getElementById('carousel-track');
  const slideClass = direction === 'left' ? 'carousel-slide-left' : 'carousel-slide-right';

  track.innerHTML = `
    <div class="carousel-card ${slideClass}">
      <div class="log-phase-header">
        FASE ${p.phase_number} &nbsp;|&nbsp;
        ${nameP1}: ${actionLabel[p.action_p1] || p.action_p1} &nbsp;vs&nbsp;
        ${nameP2}: ${actionLabel[p.action_p2] || p.action_p2}
      </div>
      <div class="log-dice">
        <span class="dice-p1">🎲 ${nameP1} <b>${p.roll_p1}</b>${ef1 !== String(p.roll_p1) ? ` <span class="dice-eff">(ef ${ef1})</span>` : ''}</span>
        <span class="dice-vs">vs</span>
        <span class="dice-p2">🎲 ${nameP2} <b>${p.roll_p2}</b>${ef2 !== String(p.roll_p2) ? ` <span class="dice-eff">(ef ${ef2})</span>` : ''}</span>
      </div>
      <div class="log-narrative">"${p.narrative_text}"</div>
      <div class="log-counters">
        <span class="log-cnt-p1">${nameP1} → ${p.counters_p1.toFixed(1)} <span style="color:#666">(+${p.counter_dmg_p1})</span></span>
        <span class="log-cnt-p2">${nameP2} → ${p.counters_p2.toFixed(1)} <span style="color:#666">(+${p.counter_dmg_p2})</span></span>
      </div>
      ${effectsHtml ? `<div class="log-effects">${effectsHtml}</div>` : ''}
      <div class="carousel-winner ${winCls}">
        ${p.phase_winner !== 'NONE' ? `Fase: <b>${phaseWinner}</b>` : 'Empate de fase'}
        ${mismatch ? ' <span class="math-warn">⚠</span>' : ''}
      </div>
      ${p.battle_over ? `<div class="log-fin">⚔ FIN — VICTORIA: ${p.winner === 'P1' ? nameP1 : p.winner === 'P2' ? nameP2 : p.winner}</div>` : ''}
    </div>
  `;

  // Update dots
  document.querySelectorAll('.c-dot').forEach((d, i) => {
    d.className = 'c-dot' + (i === idx ? ' active' : i < idx ? ' seen' : '');
  });

  // Update nav buttons
  const prevBtn = document.getElementById('carousel-prev');
  const nextBtn = document.getElementById('carousel-next');
  prevBtn.style.visibility = idx === 0 ? 'hidden' : 'visible';

  if (idx === _carouselPhases.length - 1) {
    nextBtn.textContent = 'Continuar ✓';
    nextBtn.className = 'btn-primary';
  } else {
    nextBtn.textContent = 'Siguiente →';
    nextBtn.className = 'btn-primary';
  }
}

function carouselNav(dir) {
  const newIdx = _carouselIdx + dir;

  if (newIdx >= _carouselPhases.length) {
    document.getElementById('phase-carousel').style.display = 'none';
    if (_carouselResolve) { _carouselResolve(); _carouselResolve = null; }
    return;
  }

  if (newIdx < 0) return;

  const direction = dir > 0 ? 'right' : 'left';
  _carouselIdx = newIdx;
  _renderCarouselCard(_carouselIdx, direction);
}

/* ══════════════════════════════════════
   UTILS
══════════════════════════════════════ */

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
