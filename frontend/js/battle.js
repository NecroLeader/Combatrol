async function startBattle() {
  const mode  = document.getElementById('mode').value;
  const arena = document.getElementById('arena').value || null;

  try {
    const data = await apiPost('/battle/start', { mode, arena_code: arena });
    State.battleId = data.battle_id;

    document.getElementById('battle-id').textContent = `#${data.battle_id}`;
    document.getElementById('battle-panel').style.display = 'block';
    document.getElementById('log-entries').innerHTML = '';
    document.getElementById('cnt-p1').textContent = '0';
    document.getElementById('cnt-p2').textContent = '0';
    document.getElementById('fx-p1').textContent = '';
    document.getElementById('fx-p2').textContent = '';

    appendLog({
      meta: `Batalla iniciada — ${data.mode} | Arena: ${data.arena || 'random'}`,
      narrative: `${data.p1.name} (${data.p1.weapon}) vs ${data.p2.name} (${data.p2.weapon})`,
    });
  } catch (e) {
    alert('Error al iniciar: ' + e.message);
  }
}

async function simulateTurn() {
  if (!State.battleId) return;
  try {
    const data = await apiPost(`/battle/${State.battleId}/simulate`);
    data.phases.forEach(renderPhase);
    await refreshStatus();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function simulateAll() {
  if (!State.battleId || State.running) return;
  State.running = true;
  try {
    let over = false;
    while (!over) {
      const data = await apiPost(`/battle/${State.battleId}/simulate`);
      data.phases.forEach(renderPhase);
      over = data.phases.some(p => p.battle_over);
      await refreshStatus();
      if (!over) await sleep(300);
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
  State.running = false;
}

async function refreshStatus() {
  const data = await apiGet(`/battle/${State.battleId}`);
  const s1 = data.p1.state;
  const s2 = data.p2.state;

  document.getElementById('cnt-p1').textContent = (s1?.counters ?? 0).toFixed(1);
  document.getElementById('cnt-p2').textContent = (s2?.counters ?? 0).toFixed(1);
  document.getElementById('fx-p1').innerHTML = (data.p1.effects || []).map(tagBadge).join(' ');
  document.getElementById('fx-p2').innerHTML = (data.p2.effects || []).map(tagBadge).join(' ');

  if (data.battle.status === 'FINISHED') {
    const banner = document.createElement('div');
    banner.className = 'winner-banner';
    banner.textContent = `VICTORIA: ${data.battle.winner_side}`;
    document.getElementById('battle-panel').prepend(banner);
  }
}

function renderPhase(p) {
  appendLog({
    meta: `T${p.turn_number}F${p.phase_number} | ${p.action_pair} | ${p.difference_band} / ${p.power_context}`,
    narrative: p.narrative_text,
    dmg: `P1 +${p.counter_dmg_p1} cnt  |  P2 +${p.counter_dmg_p2} cnt  →  ${p.counters_p1.toFixed(1)} vs ${p.counters_p2.toFixed(1)}`,
    outcome: `${p.outcome_code}  |  roll: ${p.effective_p1} vs ${p.effective_p2}  |  winner: ${p.roll_winner}`,
    effects: [p.effect_applied_p1, p.effect_applied_p2].filter(Boolean),
    over: p.battle_over,
    winner: p.winner,
  });
}

function appendLog(entry) {
  const el = document.createElement('div');
  el.className = 'log-entry';
  el.innerHTML = `
    ${entry.meta ? `<div class="meta">${entry.meta}</div>` : ''}
    ${entry.narrative ? `<div class="narrative">"${entry.narrative}"</div>` : ''}
    ${entry.dmg ? `<div class="dmg">${entry.dmg}</div>` : ''}
    ${entry.outcome ? `<div class="outcome">${entry.outcome}</div>` : ''}
    ${(entry.effects || []).map(e => `<span class="tag">${e}</span>`).join('')}
    ${entry.over ? `<div class="dmg" style="color:#c9a84c">⚔ FIN — Ganador: ${entry.winner}</div>` : ''}
  `;
  const log = document.getElementById('log-entries');
  log.prepend(el);
}

function tagBadge(tag) {
  return `<span class="tag">${tag}</span>`;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
