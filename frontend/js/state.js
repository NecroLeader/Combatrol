const State = {
  battleId:   null,
  running:    false,
  mode:       'SIMULATION',
  nameP1:     'P1',
  nameP2:     'P2',
  showMath:   false,
  actionsP1:  [null, null, null],
  actionsP2:  [null, null, null],
  // Guardado para rematch
  lastConfig: null,
  // Acumulador de fases para el resumen
  phases:     [],
};
