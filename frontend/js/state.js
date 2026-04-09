const State = {
  battleId:   null,
  running:    false,
  mode:       'SIMULATION',
  nameP1:     'P1',
  nameP2:     'P2',
  showMath:   false,
  // Acciones seleccionadas por fase (índices 0-2), null = sin seleccionar
  actionsP1:  [null, null, null],
  actionsP2:  [null, null, null],
};
