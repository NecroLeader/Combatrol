-- Narrativas v3: pool_tags de outcome_matrix_seed_v2.csv sin cobertura previa
-- Ejecutar después de seed_narratives_v2.sql

INSERT OR IGNORE INTO narrative_templates (pool_tag, template_text, required_tags, excluded_tags, extra_effects, weight) VALUES

-- ═══════════════════════════════════════════════
--  ATK_ATK
-- ═══════════════════════════════════════════════
('ATK_ATK_APLASTA_GUARDIA_A',       'El primero baja el arma con tanta fuerza que aplasta la guardia del segundo.',           '[]','[]','[]',1.0),
('ATK_ATK_APLASTA_GUARDIA_B',       'La guardia del primero cede bajo el impacto. El segundo lo aprovecha al instante.',       '[]','[]','[]',1.0),
('ATK_ATK_CHOQUE_DESPROLIJO_A',     'El primero ataca sin cuidado. Conecta, pero a un costo visible.',                        '[]','[]','[]',1.0),
('ATK_ATK_CHOQUE_DESPROLIJO_B',     'El segundo golpea sin técnica. La fuerza bruta suple la forma por un instante.',         '[]','[]','[]',1.0),
('ATK_ATK_CORTE_DE_LINEA_A',        'El primero traza una línea limpia. El segundo la recibe en el costado.',                 '[]','[]','[]',1.0),
('ATK_ATK_CORTE_DE_LINEA_B',        'El segundo dibuja un arco preciso. El primero no logra cerrarlo a tiempo.',              '[]','[]','[]',1.0),
('ATK_ATK_DERRIBO_POR_PRESION_A',   'El primero no para de presionar. El segundo se rompe y cae.',                            '[]','[]','[]',1.0),
('ATK_ATK_DERRIBO_POR_PRESION_B',   'La presión del segundo acumula hasta que el primero pierde el equilibrio.',              '[]','[]','[]',1.0),
('ATK_ATK_ESTOCADA_DE_VENTANA_A',   'El primero encuentra la ventana exacta y la atraviesa.',                                 '[]','[]','[]',1.0),
('ATK_ATK_ESTOCADA_DE_VENTANA_B',   'El segundo identifica la apertura y clava la estocada en el momento justo.',             '[]','[]','[]',1.0),
('ATK_ATK_QUIEBRE_DE_RITMO_A',      'El primero cambia el ritmo de golpe. El segundo pierde el paso.',                       '[]','[]','[]',1.0),
('ATK_ATK_QUIEBRE_DE_RITMO_B',      'El segundo rompe la cadencia. El primero ataca en el vacío.',                           '[]','[]','[]',1.0),
('ATK_ATK_REMATE_INCOMPLETO_A',     'El primero intenta cerrar el intercambio, pero el segundo aguanta lo suficiente.',       '[]','[]','[]',1.0),
('ATK_ATK_REMATE_INCOMPLETO_B',     'El segundo busca el remate pero le falta un milímetro. El primero sigue en pie.',        '[]','[]','[]',1.0),
('ATK_ATK_VENTAJA_SOSTENIDA_A',     'El primero mantiene la presión en cada intercambio. El segundo va cediendo.',            '[]','[]','[]',1.0),
('ATK_ATK_VENTAJA_SOSTENIDA_B',     'El segundo sostiene la ventaja turno a turno. El primero no encuentra respuesta.',       '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  ATK_DEF
-- ═══════════════════════════════════════════════
('ATK_DEF_APLASTA_GUARDIA',         'El ataque aplasta la guardia del defensor. La defensa se derrumba.',                     '[]','[]','[]',1.0),
('ATK_DEF_BRECHA_CONTROLADA',       'El atacante abre una brecha controlada. El defensor la tapa pero paga el precio.',       '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_CORTA_PRECISA',    'El defensor responde con una contra corta y precisa. El atacante recibe justo donde duele.','[]','[]','[]',1.0),
('ATK_DEF_CONTRA_DESESPERADA',      'El defensor lanza una contra sin margen. Funciona por un pelo.',                        '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_DE_MAESTRIA',      'El defensor convierte el ataque en una lección. La contra es perfecta.',                '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_DE_PURATECNICA',   'Sin espacio, el defensor se apoya en la técnica pura. La contra es impecable.',         '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_DE_RESPUESTA',     'El defensor lee el ataque y responde con exactitud. No sobra ni falta.',                '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_IMPOSIBLE',        'El defensor hace lo que no debería ser posible: para el ataque y contraataca.',          '[]','[]','[]',1.0),
('ATK_DEF_CONTRA_TORPE',            'El defensor intenta una contra pero le sale mal. El atacante lo siente pero no colapsa.',  '[]','[]','[]',1.0),
('ATK_DEF_GUARDIA_REVENTADA',       'La guardia del defensor estalla. El golpe pasa entero.',                                 '[]','[]','[]',1.0),
('ATK_DEF_GUARDIA_SUPERADA',        'El atacante supera la guardia. El defensor absorbe el impacto sin tiempo para reaccionar.','[]','[]','[]',1.0),
('ATK_DEF_IMPACTO_AJUSTADO',        'El atacante ajusta el ángulo en el último momento. El defensor lo absorbe apenas.',     '[]','[]','[]',1.0),
('ATK_DEF_PARADA_PRECISA',          'El defensor para en el punto exacto. El ataque no pasa.',                               '[]','[]','[]',1.0),
('ATK_DEF_QUIEBRA_DEFENSA',         'El atacante quiebra la defensa con persistencia. La postura del defensor cede.',        '[]','[]','[]',1.0),
('ATK_DEF_REMATE_INCOMPLETO',       'El atacante busca el remate pero el defensor aguanta la línea.',                        '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  ATK_INT
-- ═══════════════════════════════════════════════
('ATK_INT_AMAGA_Y_ROMPE_RITMO',     'El atacante amaga y rompe el ritmo. La maniobra del segundo se deshace.',               '[]','[]','[]',1.0),
('ATK_INT_ARRUINA_PREPARACION',     'El ataque llega antes de que la maniobra tome forma. La preparación se arruina.',       '[]','[]','[]',1.0),
('ATK_INT_CAMBIO_DE_PLANO',         'El atacante cambia el plano de ataque. La maniobra no puede seguirlo.',                  '[]','[]','[]',1.0),
('ATK_INT_CASTIGO_ABIERTO',         'El atacante castiga la apertura que deja la maniobra. El segundo lo paga caro.',        '[]','[]','[]',1.0),
('ATK_INT_CORTA_MANIOBRA',          'El ataque corta la maniobra antes de que termine. El segundo queda expuesto.',          '[]','[]','[]',1.0),
('ATK_INT_ESQUIVA_Y_ABRE_ESPACIO',  'El atacante esquiva la maniobra y abre espacio propio. El segundo pierde el control.',   '[]','[]','[]',1.0),
('ATK_INT_INTERRUPCION_LIMPIA',     'El ataque interrumpe la maniobra de forma limpia. Sin fricción, sin margen.',           '[]','[]','[]',1.0),
('ATK_INT_MANIOBRA_IMPOSIBLE',      'La maniobra del segundo era imposible de ejecutar. El atacante lo demuestra.',           '[]','[]','[]',1.0),
('ATK_INT_SENTENCIA_MANIOBRA',      'El ataque sentencia la maniobra antes de que empiece. Lectura perfecta.',               '[]','[]','[]',1.0),
('ATK_INT_SENTENCIA_PREPARACION',   'El atacante sentencia la preparación del segundo. Lo que iba a pasar, no pasa.',        '[]','[]','[]',1.0),
('ATK_INT_TRAMPA_PRECISA',          'El atacante tiende una trampa y el segundo cae exactamente donde debía.',               '[]','[]','[]',1.0),
('ATK_INT_TRAMPA_TOTAL',            'La trampa es total. El segundo no tiene escapatoria desde que inicia la maniobra.',      '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  DEF_ATK
-- ═══════════════════════════════════════════════
('DEF_ATK_APLASTA_GUARDIA_RECIBIDA','El ataque del segundo aplasta la guardia del defensor. La postura se destruye.',         '[]','[]','[]',1.0),
('DEF_ATK_ATAQUE_SE_CUELA',         'El ataque se cuela por la guardia. El defensor lo recibe sin poder hacer nada.',        '[]','[]','[]',1.0),
('DEF_ATK_BLOQUEO_CON_VUELTA',      'El defensor para el golpe y da vuelta el intercambio. La contra sale sola.',            '[]','[]','[]',1.0),
('DEF_ATK_BLOQUEO_TORPE',           'El bloqueo es torpe pero alcanza. El ataque se desvía con esfuerzo.',                   '[]','[]','[]',1.0),
('DEF_ATK_BRECHA_CONTROLADA_RECIBIDA','El segundo abre una brecha controlada. El defensor paga el precio.',                  '[]','[]','[]',1.0),
('DEF_ATK_CONTRA_DESESPERADA',      'El defensor contraataca sin margen. Funciona justo antes del colapso.',                 '[]','[]','[]',1.0),
('DEF_ATK_CONTRA_DE_MAESTRIA',      'El defensor convierte el momento en una lección. La contra es impecable.',             '[]','[]','[]',1.0),
('DEF_ATK_CONTRA_DE_PURATECNICA',   'Técnica pura. El defensor anula el ataque y devuelve el daño con precisión.',           '[]','[]','[]',1.0),
('DEF_ATK_CONTRA_IMPOSIBLE',        'El defensor para lo imparable y contraataca. Nadie entendió cómo lo hizo.',             '[]','[]','[]',1.0),
('DEF_ATK_GUARDIA_REVENTADA_RECIBIDA','La guardia del defensor no aguanta. El ataque la revienta.',                          '[]','[]','[]',1.0),
('DEF_ATK_GUARDIA_SUPERADA_RECIBIDA','El atacante supera la guardia. El defensor absorbe el golpe sin defensa.',             '[]','[]','[]',1.0),
('DEF_ATK_PARADA_CORTA',            'El defensor para a corta distancia. El margen era mínimo pero alcanzó.',               '[]','[]','[]',1.0),
('DEF_ATK_PARADA_PRECISA',          'El defensor para en el punto exacto. El ataque no logra pasar.',                       '[]','[]','[]',1.0),
('DEF_ATK_QUIEBRA_DEFENSA_RECIBIDA','El segundo quiebra la defensa con insistencia. La postura del defensor cede.',          '[]','[]','[]',1.0),
('DEF_ATK_REMATE_INCOMPLETO_RECIBIDO','El segundo busca el remate. El defensor aguanta por pura determinación.',             '[]','[]','[]',1.0),
('DEF_ATK_ROCE_FILOSO_RECIBIDO',    'El filo roza al defensor. No es un golpe limpio, pero duele.',                         '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  DEF_DEF
-- ═══════════════════════════════════════════════
('DEF_DEF_BLOQUEA_CARRIL_A',        'El primero bloquea el carril. El segundo no puede avanzar por esa línea.',              '[]','[]','[]',1.0),
('DEF_DEF_BLOQUEA_CARRIL_B',        'El segundo cierra el carril con su guardia. El primero debe buscar otra vía.',          '[]','[]','[]',1.0),
('DEF_DEF_CIERRA_ANGULO_A',         'El primero cierra el ángulo de ataque. El segundo pierde la línea de entrada.',         '[]','[]','[]',1.0),
('DEF_DEF_CIERRA_ANGULO_B',         'El segundo cierra el ángulo justo. El primero se queda sin apertura.',                  '[]','[]','[]',1.0),
('DEF_DEF_DOMINIO_DE_LINEA_A',      'El primero domina la línea de contacto. El segundo apenas mantiene la posición.',       '[]','[]','[]',1.0),
('DEF_DEF_DOMINIO_DE_LINEA_B',      'El segundo controla la línea. El primero cede milímetro a milímetro.',                  '[]','[]','[]',1.0),
('DEF_DEF_DOMINIO_TACTICO_A',       'El primero toma control táctico sin atacar. El espacio se reorganiza a su favor.',      '[]','[]','[]',1.0),
('DEF_DEF_DOMINIO_TACTICO_B',       'El segundo impone su lectura táctica. El primero se repliega sin ataque.',              '[]','[]','[]',1.0),
('DEF_DEF_ENCIERRO_DEFENSIVO_A',    'El primero encierra al segundo en su propia guardia. Sin salida visible.',              '[]','[]','[]',1.0),
('DEF_DEF_ENCIERRO_DEFENSIVO_B',    'El segundo envuelve la posición del primero. El encierro es defensivo pero total.',     '[]','[]','[]',1.0),
('DEF_DEF_TOMA_COBERTURA_A',        'El primero toma cobertura. El segundo tiene que reevaluar el terreno.',                 '[]','[]','[]',1.0),
('DEF_DEF_TOMA_COBERTURA_B',        'El segundo busca cobertura. El primero pierde el ángulo de presión.',                  '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  DEF_INT
-- ═══════════════════════════════════════════════
('DEF_INT_ACTIVA_ZONA_PELIGROSA',   'La maniobra activa una zona peligrosa del entorno. El defensor lo nota tarde.',         '[]','[]','[]',1.0),
('DEF_INT_ANULA_PREPARACION',       'El defensor anula la preparación antes de que tome forma. Anticipa todo.',              '[]','[]','[]',1.0),
('DEF_INT_ANULA_Y_ROMPE_RITMO',     'El defensor anula la maniobra y rompe el ritmo del segundo. La cadencia se pierde.',    '[]','[]','[]',1.0),
('DEF_INT_CAMBIA_ESCENARIO',        'La maniobra del segundo cambia el escenario. El defensor tiene que adaptarse.',         '[]','[]','[]',1.0),
('DEF_INT_CIERRE_DEL_ESCENARIO',    'El defensor cierra el escenario antes de que la maniobra lo abra.',                     '[]','[]','[]',1.0),
('DEF_INT_CORTA_PREPARATIVO',       'El defensor corta el preparativo en el momento exacto. Sin preparación, sin maniobra.','[]','[]','[]',1.0),
('DEF_INT_LEE_LA_MANIOBRA',         'El defensor lee la maniobra completa antes de que empiece. No hay sorpresa.',           '[]','[]','[]',1.0),
('DEF_INT_LEE_Y_CASTIGA',           'El defensor lee la maniobra y castiga la apertura que deja. Lectura perfecta.',         '[]','[]','[]',1.0),
('DEF_INT_LOGRA_APERTURA',          'La maniobra logra abrir una brecha en la defensa. El segundo tiene un camino.',         '[]','[]','[]',1.0),
('DEF_INT_NEUTRALIZA_Y_PRESIONA',   'El defensor neutraliza la maniobra y presiona de inmediato. Sin respiro.',              '[]','[]','[]',1.0),
('DEF_INT_PREPARA_CIERRE',          'El defensor prepara el cierre mientras el segundo ejecuta. La maniobra queda atrapada.','[]','[]','[]',1.0),
('DEF_INT_TRAMPA_TOTAL',            'La maniobra era una trampa. El defensor cae en ella desde el inicio.',                  '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  INT_ATK
-- ═══════════════════════════════════════════════
('INT_ATK_AMAGA_Y_ROMPE_RITMO',     'La maniobra amaga y quiebra el ritmo del atacante. El golpe sale en el momento equivocado.','[]','[]','[]',1.0),
('INT_ATK_ARRUINA_PREPARACION_RECIBIDA','El ataque del segundo arruina la preparación antes de que cuaje.',                  '[]','[]','[]',1.0),
('INT_ATK_CAMBIO_DE_PLANO',         'La maniobra cambia el plano. El atacante no puede seguir el movimiento.',               '[]','[]','[]',1.0),
('INT_ATK_CASTIGO_ABIERTO_RECIBIDO','El atacante castiga la apertura que deja la maniobra. El primero paga caro.',           '[]','[]','[]',1.0),
('INT_ATK_CORTA_MANIOBRA_RECIBIDA', 'El ataque corta la maniobra antes de que llegue. El primero queda expuesto.',           '[]','[]','[]',1.0),
('INT_ATK_ESQUIVA_Y_ABRE_ESPACIO',  'La maniobra esquiva el ataque y abre espacio. El primero pierde el control.',           '[]','[]','[]',1.0),
('INT_ATK_INTERRUPCION_LIMPIA_RECIBIDA','El ataque interrumpe la maniobra de forma limpia. El primero no puede completarla.','[]','[]','[]',1.0),
('INT_ATK_MANIOBRA_IMPOSIBLE',      'La maniobra era imposible de ejecutar bajo ese ataque. El primero lo aprende.',         '[]','[]','[]',1.0),
('INT_ATK_SENTENCIA_MANIOBRA_RECIBIDA','El ataque sentencia la maniobra del primero antes de que empiece.',                  '[]','[]','[]',1.0),
('INT_ATK_SENTENCIA_PREPARACION_RECIBIDA','El atacante sentencia la preparación. Lo que el primero planeaba, no sucede.',    '[]','[]','[]',1.0),
('INT_ATK_TRAMPA_PRECISA',          'La trampa del segundo es precisa. El primero cae exactamente donde debía.',             '[]','[]','[]',1.0),
('INT_ATK_TRAMPA_TOTAL',            'Trampa total. El primero no tiene escapatoria una vez que inicia la maniobra.',          '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  INT_DEF
-- ═══════════════════════════════════════════════
('INT_DEF_ACTIVA_ZONA_PELIGROSA',   'La maniobra activa una zona peligrosa. El defensor llega tarde a leerlo.',              '[]','[]','[]',1.0),
('INT_DEF_ANULA_PREPARACION_RECIBIDA','El defensor anula la preparación del primero antes de que madure.',                   '[]','[]','[]',1.0),
('INT_DEF_ANULA_Y_ROMPE_RITMO_RECIBIDO','El defensor anula la maniobra y rompe el ritmo. El primero pierde el paso.',       '[]','[]','[]',1.0),
('INT_DEF_CAMBIA_ESCENARIO',        'La maniobra cambia el escenario. El defensor tiene que reorganizarse.',                 '[]','[]','[]',1.0),
('INT_DEF_CIERRE_DEL_ESCENARIO',    'El defensor cierra el escenario antes de que la maniobra del primero lo modifique.',    '[]','[]','[]',1.0),
('INT_DEF_CORTA_PREPARATIVO_RECIBIDO','El defensor interrumpe el preparativo. El primero no llega a completar la maniobra.', '[]','[]','[]',1.0),
('INT_DEF_LEE_LA_MANIOBRA_RECIBIDA','El defensor lee la maniobra completa del primero. No hay nada que lo sorprenda.',       '[]','[]','[]',1.0),
('INT_DEF_LEE_Y_CASTIGA_RECIBIDO',  'El defensor lee la maniobra del primero y castiga la apertura que deja.',               '[]','[]','[]',1.0),
('INT_DEF_LOGRA_APERTURA',          'La maniobra logra abrir una brecha. El primero tiene un camino hacia adelante.',        '[]','[]','[]',1.0),
('INT_DEF_NEUTRALIZA_Y_PRESIONA_RECIBIDA','El defensor neutraliza la maniobra y presiona. Sin respiro para el primero.',     '[]','[]','[]',1.0),
('INT_DEF_PREPARA_CIERRE',          'El defensor prepara el cierre antes de que la maniobra abra espacio.',                  '[]','[]','[]',1.0),
('INT_DEF_TRAMPA_TOTAL',            'La maniobra del primero era la trampa. El defensor lo entiende demasiado tarde.',       '[]','[]','[]',1.0),

-- ═══════════════════════════════════════════════
--  INT_INT
-- ═══════════════════════════════════════════════
('INT_INT_ACTIVA_RUTA_A',           'El primero activa una ruta táctica que el segundo no preveía.',                         '[]','[]','[]',1.0),
('INT_INT_ACTIVA_RUTA_B',           'El segundo abre una ruta que el primero no puede cerrar a tiempo.',                     '[]','[]','[]',1.0),
('INT_INT_ACTIVA_ZONA_ROTA_A',      'El primero activa una zona del entorno que ya estaba comprometida. El terreno cede.',   '[]','[]','[]',1.0),
('INT_INT_ACTIVA_ZONA_ROTA_B',      'El segundo activa la zona rota. El terreno trabaja en su contra del primero.',          '[]','[]','[]',1.0),
('INT_INT_CIERRA_TABLERO_A',        'El primero reorganiza el tablero completo. El segundo pierde las rutas que tenía.',     '[]','[]','[]',1.0),
('INT_INT_CIERRA_TABLERO_B',        'El segundo cierra el tablero. El primero se queda sin opciones táticas claras.',        '[]','[]','[]',1.0),
('INT_INT_GANA_TERRITORIO_A',       'El primero gana territorio sin atacar. La posición se inclina a su favor.',             '[]','[]','[]',1.0),
('INT_INT_GANA_TERRITORIO_B',       'El segundo gana terreno de forma sistemática. El primero retrocede.',                   '[]','[]','[]',1.0),
('INT_INT_IMPONE_ESCENARIO_A',      'El primero impone el escenario que quería. La batalla pasa a jugarse en sus términos.', '[]','[]','[]',1.0),
('INT_INT_IMPONE_ESCENARIO_B',      'El segundo impone el escenario. El primero tiene que adaptarse o perder.',              '[]','[]','[]',1.0),
('INT_INT_ROMPE_EL_ESCENARIO_A',    'El primero rompe el escenario establecido. El tablero se redistribuye de raíz.',        '[]','[]','[]',1.0),
('INT_INT_ROMPE_EL_ESCENARIO_B',    'El segundo destruye el escenario previo. Todo lo que el primero había construido, cae.','[]','[]','[]',1.0),
('INT_INT_SE_ADUEÑA_DEL_ESPACIO_A', 'El primero se adueña del espacio central. El segundo pierde movilidad.',               '[]','[]','[]',1.0),
('INT_INT_SE_ADUEÑA_DEL_ESPACIO_B', 'El segundo toma control del espacio. El primero queda comprimido.',                    '[]','[]','[]',1.0),
('INT_INT_SUPERIORIDAD_TACTICA_A',  'El primero demuestra superioridad táctica sin discusión. El segundo lo sabe.',          '[]','[]','[]',1.0),
('INT_INT_SUPERIORIDAD_TACTICA_B',  'El segundo impone su lectura táctica. El primero no puede responder a la escala.',      '[]','[]','[]',1.0);
