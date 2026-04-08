# GDD — Combatrol: Simulador de Batalla
**Versión:** 0.7 — Design freeze total
**Estado:** Listo para implementar — sin open questions pendientes

---

## 1. VISIÓN Y FILOSOFÍA

Un simulador de combate por fases donde el resultado de cada intercambio depende de **tres ejes simultáneos**:

1. **¿Qué tan extrema fue la tirada?** — el valor efectivo (dado + modificadores)
2. **¿Qué acción eligió cada uno?** — el par define qué outcomes son posibles
3. **¿En qué estado está la batalla?** — estados activos, entorno, posición, acumuladores — NO el número de turno

### Principios no negociables

- Siempre pasa algo. No hay fases vacías.
- El valor absoluto importa tanto como la diferencia.
- Una diferencia mínima entre tiradas altas ≠ una diferencia mínima entre tiradas bajas.
- Los eventos raros existen: un KO en el turno 1 es posible. Improbable, no imposible.
- La narrativa no es cosmética: **tiene propiedades mecánicas**.
- Todo lo configurable vive en tablas. El código no hardcodea reglas.
- Las 3 acciones (ATK/DEF/INT) tienen roles mecánicos distintos. Ninguna domina siempre.
- El engine no sabe si los inputs vienen de humano o IA. Solo procesa acciones.

### Filosofía de balance

Las tres acciones se necesitan entre sí:

| Acción | Rol mecánico real |
|--------|-------------------|
| **ATK** | Presión y acumulación de daño. Spam → FATIGA automática. |
| **DEF** | Bloquea outcomes fatales. Exitosa → contraataque. Fallida → exposición. |
| **INT** | Modifica el campo. Brilla en desventaja (CAÍDO, DESARMADO). Única opción válida cuando ambos están CAÍDOS. |

El spam de ATK está penalizado por diseño (FATIGA). Si ATK fuera siempre óptimo, DEF e INT no existirían como decisión real.

---

## 1b. MODOS DE JUEGO Y ARQUITECTURA DE INPUTS

El engine es agnóstico a la fuente de decisiones. Solo procesa acciones.

```python
BattleConfig(
    arena="sala_armeria",           # de pool o manual
    weapon_p1="espada",             # de pool o elección
    weapon_p2="daga",
    mode="PVP" | "PVE" | "SIMULATION",
    progression_enabled=False,      # False siempre en PVP
    input_source_p1="human" | "ai",
    input_source_p2="human" | "ai"
)
```

| Modo | input_p1 | input_p2 | Progresión | Descripción |
|------|----------|----------|------------|-------------|
| SIMULATION | ai | ai | no | El engine corre solo. Vos mirás. |
| PVE | human | ai | opcional | Jugás vos contra el engine. Roguelike posible. |
| PVP | human | human | no | Dos humanos. Siempre desde 0. |

**PVP**: misma batalla, mismo engine, sin carry-over de progresión. Cada batalla es una pizarra limpia. El progreso roguelike es exclusivo de PVE.

---

## 2. ESTRUCTURA DE UN COMBATE

```
BATALLA
└── N TURNOS
    └── 3 FASES por turno
        └── 1 RESOLUCIÓN por fase
            ├── Ambos eligen acción (simultáneo)
            ├── Ambos tiran d20
            ├── Se aplican modificadores activos
            ├── Se calcula power_context + difference_band
            ├── Se consulta outcome_matrix
            ├── Se aplican efectos y estados
            ├── Se actualizan acumuladores
            └── Se genera narrativa
```

**Condición de fin:** un jugador llega a 15 contadores → pierde.
**Duración estimada:** 1 turno (rarísimo, KO) a 20+ turnos (batalla pareja con mucha recuperación).

---

## 3. EL DADO Y LA TIRADA EFECTIVA

### d20 base + modificadores

```
tirada_efectiva = d20 + suma_modificadores_activos
```

Los modificadores van de **-5 a +5**, lo que da un rango efectivo de **-4 a 25**.

Los valores por fuera del rango 1-20 son **excepcionales** y solo ocurren con buffs/debuffs acumulados. Ahí viven los eventos más extremos.

### Tabla de Potencia (FUENTE: Excel, columnas A-B)

| Dado (valor efectivo) | Potencia | Label |
|----------------------|----------|-------|
| 1 – 5 | 1 | Muy baja |
| 6 – 9 | 2 | Baja |
| 10 – 13 | 3 | Media |
| 14 – 16 | 4 | Buena |
| 17 – 19 | 5 | Alta |
| 20 | 6 | Extrema |
| 21 – 22 | 7 | Límite *(solo con buff)* |
| 23 – 25 | 8 | Transcendente *(solo con buff máximo)* |
| ≤ 0 | 0 | Colapso *(solo con debuff)* |

> ⚠️ CONFLICTO A RESOLVER: el seed SQL del starter usa rangos distintos (1-3/4-6/7-10/11-14/15-17/18-20). **El Excel tiene precedencia.** Actualizar `seed_core.sql`.

---

## 4. BANDAS DE DIFERENCIA

La diferencia es `ABS(tirada_efectiva_p1 - tirada_efectiva_p2)`.

### Tabla de Diferencia (FUENTE: Excel, columnas C-E)

| Banda | Rango de diferencia | Bono/Pen al ganador |
|-------|--------------------|--------------------|
| Baja | 0 – 3 | 0 |
| Moderada | 4 – 7 | 1 |
| Regular | 8 – 10 | 2 |
| Alta | 11 – 13 | 3 |
| Muy alta | 14 – 16 | 4 |
| Máxima | 17 – 19 | 5 |
| Extrema | ≥ 20 *(solo con mods)* | 6 |

El **bono** se aplica al ganador de la fase como modificador temporal para la siguiente fase. La **penalización** equivalente se puede aplicar al perdedor (configurable en tabla).

> La banda Extrema (diff ≥ 20) es matemáticamente imposible en un d20 limpio. Solo ocurre si un jugador tiene buff máximo y el otro debuff máximo. Es el escenario más raro del sistema.

---

## 5. EL POWER CONTEXT — LA SEGUNDA DIMENSIÓN

Cada fase tiene dos dimensiones de resolución independientes: **diferencia** (quién ganó y cuánto) y **power_context** (qué tan fuertes fueron ambos en términos absolutos).

```
power_context = f(potencia_p1, potencia_p2)
```

| power_context | Condición | Narrativa base |
|---------------|-----------|----------------|
| `BOTH_HIGH` | ambos ≥ potencia 5 | Choque épico, intensidad máxima |
| `BOTH_LOW` | ambos ≤ potencia 2 | Tropiezo mutuo, torpeza |
| `MIXED_EXTREME` | diferencia de potencia ≥ 4 | Uno dominó en calidad absoluta |
| `BALANCED` | resto de casos | Intercambio técnico |

### Por qué esto importa

```
Ejemplo A: P1 saca 19, P2 saca 20 → diferencia = 1 (Baja), power_context = BOTH_HIGH
Ejemplo B: P1 saca 2,  P2 saca 3  → diferencia = 1 (Baja), power_context = BOTH_LOW
```

**El mismo resultado de diferencia produce outcomes completamente distintos.**

- Ejemplo A: CHOQUE ÉPICO — dos gladiadores al límite, el choque de aceros sacude el entorno, algo debe pasar aunque la diferencia sea mínima. Ambos pueden recibir efectos.
- Ejemplo B: TROPIEZO MUTUO — dos combatientes agotados o sin coordinación, se tambalean, alguno puede perder posición.

**La narrativa y los efectos son radicalmente diferentes aunque la banda de diferencia sea idéntica.**

---

## 6. ACCIONES Y EL PAR DE ACCIONES

Cada jugador elige una de tres acciones por fase:

| Acción | Descripción | Riesgo |
|--------|-------------|--------|
| **ATAQUE** | Presión directa, daño más plano | Bajo — pero si choca con otro ATK, ambos pueden sufrir |
| **DEFENSA** | Alto riesgo / alta recompensa | Alto — si falla, queda muy expuesto |
| **INTERACCIÓN** | Manipula entorno, usa ítem, cambia posición | Variable — puede ser interrumpida |

### El par de acciones como "puerta de posibilidades"

El par determina **qué outcomes son posibles** en esa fase. No todos los outcomes existen para todos los pares.

#### ATK vs ATK
- Ambos pueden recibir daño (intercambio)
- Diferencia mínima + BOTH_HIGH → choque de espadas, posible daño mutuo
- Diferencia alta + MIXED_EXTREME → uno aplastó al otro, daño unilateral
- Extremo: ambos caen (pierden siguiente fase), ambos se desarman
- **NO puede haber decapitación limpia** — el impacto mutuo "absorbe" lo más letal

#### ATK vs DEF
- Bloquea los outcomes más letales (alguien se preparó para defenderse)
- ATK gana extremo → tumba, desarma, rompe arma (permanente)
- DEF gana → contraataque con buff de posición
- DEF gana extremo (TRANSCENDENTE vs COLAPSO del ATK) → desmembramiento posible al revés
- **No puede haber daño mutuo** — uno estaba atacando, el otro defendiendo

#### DEF vs DEF
- **No puede haber daño directo**
- Solo: reposicionamiento, ventaja táctica, recuperación, evento de entorno
- Extremo (BOTH_HIGH): uno logra posición perfecta, el otro queda en mala postura
- Extremo (BOTH_LOW): ambos fallan la defensa y quedan expuestos

#### INT vs ATK
- Si ATK > INT: la interacción se interrumpe, el atacante puede haber cortado el intento
- La INT puede dejar efecto parcial aunque pierda (la trampa quedó a medias)
- Si INT > ATK extremo: el atacante cayó en la trampa o cambio de entorno

#### INT vs DEF
- Permite montar ventaja táctica sin riesgo de daño directo
- Puede dejar estados de preparación que afectan los siguientes turnos

#### INT vs INT
- El entorno evoluciona sin daño directo
- Crea riesgos, recursos o modificadores de entorno persistentes

---

## 7. CONTEXTO DE BATALLA — SISTEMA DE PESOS POR ESTADO

### El turno no es el gate. El estado sí.

Los outcomes extremos (FATAL, DESMEMBRAMIENTO) no están bloqueados ni habilitados por el número de turno. Su probabilidad de ocurrir depende del **peso acumulado de los estados activos** en ese momento.

```
peso_outcome = base_weight(outcome_code)
             × ∏ state_multiplier(estado_activo, outcome_code)
```

Cada estado activo tiene una tabla de multiplicadores para cada outcome posible. El engine calcula el peso de todos los outcomes candidatos y selecciona uno de forma ponderada.

### Multiplicadores de estado sobre OUTCOME_FATAL

| Estado activo | Afecta a | Multiplicador sobre FATAL |
|---------------|----------|--------------------------|
| `NIEBLA_EXTREMA` (entorno) | ambos | ×2.0 |
| `CAIDO` | receptor | ×2.5 |
| `DESARMADO` | receptor | ×3.0 |
| `PANICO` | receptor | ×2.0 |
| `POS_FAVORABLE` | atacante | ×1.5 |
| `POS_DESFAVORABLE` | receptor | ×1.5 |
| `DESMEMBRADO` | receptor | ×1.8 (ya herido = más vulnerable) |
| ningún estado especial | — | ×1.0 (solo base, rarísimo) |

**Ejemplos:**

```
Turno 1, sin estados especiales:
  peso_fatal = base_weight (muy bajo) × 1.0 = rarísimo

Turno 1, NIEBLA_EXTREMA + receptor con POS_DESFAVORABLE:
  peso_fatal = base_weight × 2.0 × 1.5 = 3× más probable → posible pero no garantizado

Turno 8, receptor CAIDO + DESARMADO:
  peso_fatal = base_weight × 2.5 × 3.0 = 7.5× más probable → muy probable si la tirada acompaña

Turno 20, sin estados especiales (ambos resistieron todo):
  peso_fatal = base_weight × 1.0 = igual de raro que turno 1
```

Un KO en turno 1 es raro pero posible. Un KO en turno 20 sin contexto especial es igual de raro. La diferencia la hacen los estados, no el tiempo.

### DESMEMBRAMIENTO — mecánica exacta

**Cómo se llega:**
- No requiere crítico ni tirada específica.
- Puede ocurrir por combate, por interacción o por evento de entorno.
- Su probabilidad también está regulada por el sistema de pesos de estado.

**Qué aplica:**
- Modificador permanente de **-5** a todas las tiradas del jugador desmembrado.
- Esto reduce el techo de tirada efectiva máxima de 25 a 20 (sin buffs).
- Con buffs máximos activos el techo sube a 20, pero **nunca genera LÍMITE ni TRANSCENDENTE**.
- El jugador desmembrado no puede hacer over-20 bajo ninguna circunstancia.

**Qué NO aplica:**
- No modifica directamente el contador de daño (el daño del golpe que causa el desmembramiento es el daño normal de ese outcome).
- No bloquea acciones por sí solo (puede combinarse con CAIDO si el desmembramiento viene de una caída).

```python
# En tabla combat_effects:
DESMEMBRADO = {
    "code": "DESMEMBRADO",
    "duration_phases": -1,          # permanente
    "applies_to": "LOSER",
    "power_mod": -5,                # modificador permanente a tiradas
    "blocks_over_20": True,         # jamás genera Límite ni Transcendente
    "blocks_recovery": False,
    "narrative_tags": ["herida_grave", "agonia", "limitado", "vulnerable"]
}
```

### Tabla de outcomes fatales con sus gates de estado

| Outcome | base_weight | Multiplicadores clave | Narrativa posible |
|---------|-------------|----------------------|-------------------|
| `FATAL_ESTOCADA` | 0.02 | DESARMADO ×3, CAIDO ×2.5 | weapon=ESPADA/DAGA |
| `FATAL_HACHAZO` | 0.02 | CAIDO ×2.5, PANICO ×2 | weapon=MANDOBLE |
| `FATAL_CAIDA_VACIO` | 0.01 | env=VACIO ×5, CAIDO ×3 | env=VACIO |
| `FATAL_ENTORNO` | 0.015 | VIDRIO_ROTO ×3, CAIDO ×2 | env=cualquiera |
| `FATAL_REMATE` | 0.03 | CAIDO ×4, DESARMADO ×3 | receptor sin defensa |
| `DESMEMBRADO` | 0.04 | DESMEMBRADO ×1.8, CAIDO ×2 | herida grave, no letal |

Los base_weights son orientativos — se ajustan en testing.

---

## 8. SISTEMA DE CONTADORES (WIN CONDITION)

En lugar de HP numérico, el combate se mide en **contadores de impacto**.

```
Cada jugador arranca en 0.
Llegar a 15 = derrota.
```

### Valores de daño base

| Tipo de golpe | Contadores |
|---------------|-----------|
| Golpe leve | +0.5 |
| Golpe normal | +1.0 |
| Golpe fuerte | +2.0 |
| Crítico | +3.0 |
| Desmembramiento | reduce el cap de 15 a 10 (permanente) |

Los contadores pueden tener decimales. Se muestran redondeados al 0.5 más cercano en UI.

### Mecánica de recuperación

Simula el "respiro de batalla" y la adaptación al dolor:

```
Cada 3 turnos completos (automático, sin condición):
  → cada jugador recupera -0.5 contadores
  → SALVO que ese jugador haya recibido un crítico en esos últimos 3 turnos
      → su recuperación se omite ese ciclo

Si se recibió un crítico:
  → bloquea el próximo ciclo de recuperación de ese jugador (no todos los futuros)
  → narrativa: el dolor del crítico impide normalizar
```

Efecto real: los críticos son "dobles" en impacto — daño directo (+3 contadores) + pérdida de una recuperación (-0.5 que no ocurre). En una batalla de 9 turnos sin recuperación, un jugador recupera 1.5 contadores. Con dos críticos recibidos, recupera 0.5. La diferencia es real pero no exagerada.

---

## 9. SISTEMA DE ESTADOS — TABLA DE VERDAD

Los estados son la memoria de la batalla. Cada efecto tiene una fila en la tabla `combat_effects`. La narrativa lee los estados activos para generar texto, y el texto puede activar estados adicionales.

### Estados base

| Código | Aplica a | Duración | mod_poder | Bloquea acción | Bloquea recovery | Tags narrativa |
|--------|----------|----------|-----------|----------------|-----------------|----------------|
| `CAIDO` | P1/P2 | 1 fase | 0 | ✓ (pierde fase) | — | suelo, vulnerable, sin_accion |
| `DESARMADO` | P1/P2 | permanente | -3 | — | — | sin_arma, desesperado |
| `ARMA_ROTA` | P1/P2 | permanente | -2 | — | — | improvisa, fragil |
| `DESMEMBRADO` | P1/P2 | permanente | -5 | — | ✓ | herida_grave, agonia |
| `CONTRA_EXITOSO` | P1/P2 | 1 fase | +4 | — | — | momentum, contraataque |
| `POS_FAVORABLE` | P1/P2 | hasta removido | +3 | — | — | ventaja_posicional |
| `POS_DESFAVORABLE` | P1/P2 | hasta removido | -3 | — | — | mala_posicion |
| `FATIGA` | P1/P2 | 1 fase (1ra fase del turno siguiente) | -3 | — | — | agotado, lento |
| `VIDRIO_ROTO` | ENTORNO | 3 turnos | variable | — | — | peligro_entorno, cautela |
| `VACILACION` | P1/P2 | 2 turnos | -2 | — | — | miedo, duda, retroceso |
| `PANICO` | P1/P2 | 1 turno | -3 | bloquea ATAQUE | — | panico, supervivencia |
| `HIPEROFFENSIVO` | P1/P2 | 1 fase | +5 | — | — | rabia, impulso, oportunidad |

### Regla de CAÍDO + fase siguiente

Si un jugador cae en F2 de un turno:
- No tiene acción en F3
- El oponente recibe `HIPEROFFENSIVO` en F3 **solo si no tiene ningún debuff activo**
- Si el oponente tiene debuff → no recibe el bonus (está en igual o peor condición)

### Regla especial: AMBOS CAÍDOS

| Situación | Efecto |
|-----------|--------|
| Solo receptor CAÍDO | Multiplicador ×2.5 sobre FATAL aplica completo |
| Ambos CAÍDOS | Multiplicadores se anulan. Vuelve a base_weight. |
| Ambos CAÍDOS + uno elige INT exitosa | INT player recibe ×1.8 situacional sobre outcomes severos |
| Ambos CAÍDOS + uno elige ATK | ATK sin ventaja posicional. No hay amplificación. |

La INTERACCIÓN es la única acción con lógica cuando ambos están en el suelo. ATK y DEF desde el suelo no tienen ventaja posicional. INT convierte la situación en asimétrica.

### Regla especial: AMBOS DESARMADOS

Sin "filo" activo, el pool de narrativa fatal cambia completamente:

```
DESARMADO (ambos):
  → DESACTIVA outcomes: FATAL_ESTOCADA, FATAL_HACHAZO, DESMEMBRAMIENTO_CORTE
     (requieren tag: requires_filo)
  → ACTIVA outcomes: FATAL_ESTRANGULACION, FATAL_IMPACTO_CRANEAL, FATAL_ENTORNO
     (requieren tag: unarmed_combat o env_available)
  → El engine filtra el pool de narrativa por tags automáticamente
  → No necesita lógica especial: los tags lo resuelven
```

### Duración de estados — tres categorías

| Categoría | Duración | Ejemplos |
|-----------|----------|---------|
| **Intra-turno** | Entre fases del mismo turno | Bono de diferencia (momentum), CONTRA_EXITOSO, HIPEROFFENSIVO |
| **Multi-turno** | N turnos configurables en tabla | FATIGA, VACILACION, POS_FAVORABLE, POS_DESFAVORABLE |
| **Permanente** | Resto del combate (`duration = -1`) | DESMEMBRADO, ARMA_ROTA, IMPROVISA |

Los skills pueden extender la duración de estados que normalmente serían temporales. Un skill RARO puede hacer que `POS_FAVORABLE` dure 3 turnos en vez de 1.

---

## 9b. ARENA — POOL DE ESCENARIOS

Las arenas se seleccionan igual que las armas: de un pool configurable, o manual.

Cada arena define:
- **Estados pre-batalla**: multiplicadores de outcomes desde el turno 1
- **Oportunidades de INT**: qué puede hacer la interacción en ese escenario
- **Tags de narrativa**: cómo se describe el entorno en el texto

### Arenas base (ejemplos)

| Arena | Estado pre-batalla | INT habilitada | Multiplicador fatal base |
|-------|-------------------|----------------|--------------------------|
| Campo abierto | ninguno | crear posición | ×1.0 |
| Sala con armas colgadas | ARMAS_COLGADAS | tomar arma del entorno | ×1.2 |
| Borde de un precipicio | VACIO | empujar | ×3.0 |
| Sala con niebla extrema | NIEBLA_EXTREMA | emboscada | ×2.0 |
| Bodega con vidrios | — | romper vidrio | ×1.3 |
| Espacio reducido | ESPACIO_REDUCIDO | arrinconar | ×1.5 |

### INT desde arena: tomar arma del entorno

```
Arena = "sala_armeria" + ARMAS_COLGADAS activo
  → INT exitosa: jugador puede intentar agarrar arma colgada
  → Si tiene éxito: equipa arma del entorno (random del pool de armas)
  → Posibilidad de DUAL_WIELD si ya tenía arma equipada
  → Si falla: POS_DESFAVORABLE (quedó expuesto intentándolo)
```

### Estilos de combate — reglas y origen

**DEFAULT siempre: ONE_HANDED para ambos jugadores.**

Los estilos cambian únicamente por:
1. **Pre-batalla** (customización manual o pool de arena)
2. **INT exitosa durante la batalla** (agarrás algo del entorno)
3. **Narrativa** (un outcome puede forzar cambio de estilo)

Los estilos modifican **multiplicadores de peso en la outcome_matrix**, no agregan nuevos inputs. El engine lee `combat_style` activo y aplica los modificadores correspondientes desde tabla.

| Estilo | Origen | ATK | DEF | INT |
|--------|--------|-----|-----|-----|
| `ONE_HANDED` | default | base | base | base |
| `DUAL` | pre-batalla o INT (agarrar segunda arma) | +hits, -potencia por golpe, mayor chance CAIDO oponente | más difícil, falla = peor outcome | +chance de éxito |
| `SHIELD` | pre-batalla o INT (agarrar escudo del entorno) | -daño, +chance CAIDO oponente (shield bash) | mucho más confiable, CONTRA a threshold menor | controla espacio, POS_DESFAVORABLE al oponente |
| `UNARMED` | DESARMADO permanente o elección | más hits, -daño, sin filo | más esquive, menos bloqueo | necesita entorno (CASTER siempre disponible si hay lanzables) |

**No implementar mecánicas internas de estilo en MVP.** Solo dejar `combat_style` en tabla de estado del combatiente y pool de narrativa por estilo. Las mecánicas de peso se agregan post-MVP sin tocar el engine core.

---

### CASTER — estado especial de INT

Cuando INT tiene éxito y el entorno tiene lanzables disponibles, puede activar el estado **CASTER** en lugar de (o además de) un cambio de posición/estilo.

**CASTER activa una PRE_PHASE** que se ejecuta ANTES de la siguiente fase regular.

```
F2 → P1 elige INT → resultado: CASTER activado
  ↓
PRE_F3 → P1 lanza objeto (se resuelve)
F3     → fase normal con estados que dejó PRE_F3

Si CASTER se activa en F3:
PRE_F1(T+1) → se ejecuta antes de la primera fase del turno siguiente
```

La simultaneidad del sistema se preserva: el reactor también tira.

#### Resolución de PRE_PHASE

- **Thrower**: usa el roll efectivo del INT que activó CASTER (ya calculado, no tira de nuevo)
- **Reactor**: tira 1 d20 sin modificadores — reacción pura

El tipo de objeto determina qué outcomes son posibles:

| Tipo | Ejemplos | Atrapa-ble |
|------|---------|-----------|
| LIGERO | botella, daga, piedra | Sí |
| MEDIO | pata de silla, antorcha | Difícil |
| PESADO | silla, barril | No — cambia entorno |

| Diferencia thrower−reactor | LIGERO | MEDIO | PESADO |
|---------------------------|--------|-------|--------|
| Thrower >7 | 1 cnt + debuff -2 próx fase | 1 cnt + debuff -2 | 2 cnt o rompe entorno |
| Thrower 3-7 | 0.5 cnt + debuff -1 | 0.5 cnt | 1 cnt leve |
| Empate / 0-2 | Sin daño — narrativa | Sin daño | Leve cambio entorno |
| Reactor 3-7 | Desviado | Esquivado + POS_FAV | Entorno cambia |
| Reactor >7 + LIGERO | **ATRAPA → counter-throw**: roles invertidos, nueva micro-resolución | Esquivado + POS_FAV | — |
| Reactor >7 + MEDIO/PESADO | Esquivado + POS_FAV | Esquivado + POS_FAV | Impacta entorno → nuevo estado |

#### Caso especial: AMBOS CASTER simultáneamente

```
Misma fase: P1 INT → CASTER, P2 INT → CASTER
↓
PRE_PHASE: ambos lanzan al mismo tiempo
  → cada uno usa su INT roll como thrower
  → cada uno usa su INT roll como reactor al del otro
  → ambas resoluciones ocurren en paralelo
  → estados se aplican simultáneamente
```

Dos objetos cruzándose. Ambos pueden impactar o no. La narrativa de esto es única.

#### Pool de lanzables por arena

Cada arena define qué objetos están disponibles. Sin pool → CASTER no puede activarse.

| Arena | Lanzables |
|-------|-----------|
| Campo abierto | piedras (LIGERO), ramas (MEDIO) |
| Sala de armería | dagas (LIGERO), espadas (MEDIO) |
| Bodega | botellas (LIGERO), cajones (PESADO) |
| Precipicio | piedras (LIGERO) |
| Espacio reducido | pool reducido según lo que haya |

#### Tabla en DB

```sql
arena_throwables (arena_code, object_code, type, weight_ligero_medio_pesado)
-- type: LIGERO / MEDIO / PESADO
-- El engine sortea del pool disponible en esa arena cuando CASTER se activa
```

---

## 10. ARMAS — SISTEMA POR TAMAÑO

Las armas del Excel (Espada, Mandoble, Daga) son **ejemplos de categoría**, no armas definitivas. La mecánica la define el **tamaño**. El nombre del arma define los tags de narrativa.

Las armas se asignan al inicio del combate. **Modo simulación:** random del pool. **Modo arcade:** elección del jugador.

### Categorías de tamaño

| Tamaño | Hits/fase | Dmg/hit | Dmg crítico/hit | Dual | Shield | Ejemplos narrativos |
|--------|-----------|---------|-----------------|------|--------|---------------------|
| PEQUEÑA | 2 | 0.5 | 1.0 | ✓ | ✓ | daga, cuchillo, navaja, puñal |
| MEDIANA | 1 | 1.0 | 2.0 | ✓ (con cualquiera) | ✓ | espada, estoque, machete, chafarrote |
| GRANDE | 1 | 1.5 | 4.0 | ✗ | ✗ | mandoble, hacha de guerra, martillo |

GRANDE requiere ambas manos → no puede dual ni usar escudo. Puede defender, pero sin el bonus de SHIELD.

### Daño en contadores por outcome × tamaño

| Outcome | PEQUEÑA | MEDIANA | GRANDE |
|---------|---------|---------|--------|
| Golpe leve | 1 hit: 0 ó 0.5 (el otro falla) | 0.5 (roza) | 0.5 ó miss |
| Golpe normal | 2 hits: 1.0 (crits independientes) | 1.0 | 1.5 |
| Golpe fuerte | 2 hits alta crit: 1.0–1.5 | 1.5 | 2.5 |
| Crítico | 2 hits crit + bonus: **2.5** | **2.0** | **4.0** |

### Pequeña — 7 outcomes posibles (el más variado)

Cada hit resuelve su crit de forma independiente:

```
miss + miss              = 0
hit  + miss              = 0.5
crit + miss              = 1.0
hit  + hit               = 1.0
crit + hit               = 1.5
crit + crit              = 2.0
crit + crit + bonus doble = 2.5  ← doble crítico simultáneo, rarísimo
```

### DUAL — techo igual a GRANDE por distinto camino

| Combinación | Crítico máximo | Sabor |
|-------------|----------------|-------|
| PEQUEÑA + PEQUEÑA | 4.0 (4 crits simultáneos, 0.3⁴ ≈ 1%) | Vendaval de golpes |
| PEQUEÑA + MEDIANA | 3.0 | Velocidad + contundencia |
| MEDIANA + MEDIANA | **4.0** (2 crits) | Mismo techo que GRANDE |

GRANDE = 1 swing todo o nada. DUAL MEDIANA+MEDIANA = 2 pasos al mismo techo. Flavores distintos, ceiling igual. Balanceado.

### Overflow de modificadores → siguiente fase

Cuando la tirada efectiva supera 25 (TRANSCENDENTE máximo):

```
tirada_efectiva = 27 → capeada a 25
overflow = 27 - 25 = +2 → guardado como MOMENTUM_OVERFLOW
→ próxima fase: modificador activo +2, se consume al usarse
→ si en esa fase también genera overflow, se acumula
```

Narrativa: la racha no se frena. Implementado como estado en `combat_effects` con `duration = next_phase, source = overflow`.

### Definición de ganador de fase (dos trackers independientes)

```
roll_winner   = quien sacó el número efectivo más alto (SIEMPRE determinado)
phase_winner  = a quien beneficia el outcome (lo dice la outcome_matrix)
```

Ambos se guardan en `battle_log`. Pueden no coincidir: el atacante saca 18 vs defensor 15, el atacante "ganó la tirada" pero el defensor ejecutó una defensa perfecta y "ganó la fase". `turns_won` usa `roll_winner`. Skills y narrativa secundaria usan ambos.

### Tablas en DB

```sql
CREATE TABLE weapon_sizes (
    size_code      TEXT PRIMARY KEY,  -- PEQUEÑA / MEDIANA / GRANDE
    hits           INTEGER,
    dmg_per_hit    REAL,
    crit_dmg       REAL,
    dual_allowed   BOOLEAN,
    shield_allowed BOOLEAN
);

CREATE TABLE weapons (
    code           TEXT PRIMARY KEY,
    name           TEXT,
    size_code      TEXT,             -- FK a weapon_sizes
    narrative_tags TEXT,             -- JSON: ["filo","rapido","pesado",...]
    FOREIGN KEY (size_code) REFERENCES weapon_sizes(size_code)
);
```

Agregar una espada nueva = 1 fila en `weapons` con `size_code = 'MEDIANA'`. Sin tocar código.

---

## 10b. TURNOS GANADOS — REGLA EXACTA

**Un turno ganado** = ganar 2 de 3 fases (mayoría).

```
fases_ganadas_p1 = 2, fases_ganadas_p2 = 1  → turnos_ganados_p1 += 1
fases_ganadas_p1 = 1, fases_ganadas_p2 = 2  → turnos_ganados_p2 += 1
fases_ganadas_p1 = 1, fases_ganadas_p2 = 1, empate = 1 → EMPATE DE TURNO: 0 para ambos
```

El empate de turno no suma a nadie. Es el resultado más "neutro" posible y narrativamente se puede jugar como una ronda pareja sin vencedor claro.

---

## 11. ACUMULADORES (FUENTE: Excel, columnas Q-R)

Seis acumuladores por jugador, registrados durante toda la batalla:

| Acumulador | Descripción | Uso mecánico |
|------------|-------------|--------------|
| `roll_sum` | Suma de todas las tiradas efectivas | Desbloquea skills por threshold |
| `roll_sum_opp` | Suma de tiradas del oponente | Referencia comparativa / narrativa |
| `twenties_count` | Cantidad de 20s sacados | Desbloquea skills especiales |
| `low_streak` | Tiradas consecutivas ≤ 4 | Activa VACILACION / PANICO |
| `turns_won` | Turnos ganados (mayoría de fases) | Desbloquea mejoras de dominancia |
| `consecutive_high` | Tiradas consecutivas ≥ 17 | Calidad de skill desbloqueada |

### Ejemplo del Excel (batalla de 6 turnos ~18 fases)

```
Suma tiradas P1: 224  (promedio ~12.4 por fase)
Suma tiradas P2: 189  (promedio ~10.5 por fase)
20s P1: 3
20s P2: 1
Turnos ganados P1: 3
Turnos ganados P2: 3
```

---

## 12. SISTEMA DE SKILLS — THRESHOLDS POR roll_sum

### Tabla de thresholds

| Threshold roll_sum | Tier de skill | Pool de skills |
|---------------------|---------------|----------------|
| 40 | COMÚN | 8-10 opciones, mecánica menor |
| 70 | POCO COMÚN | 5-6 opciones, mecánica moderada |
| 90 | RARA | 3-4 opciones, mecánica fuerte |
| 100 | LEGENDARIA | 1-2 opciones, game-changing |
| 120+ | ÉPICA | Solo en batalla muy larga y dominante |

Cada threshold se puede alcanzar una sola vez por batalla. Tras desbloquearse, el siguiente threshold se activa.

### Modificador de calidad por velocidad de acumulación

```
¿Llegaste al threshold 40 en ≤ 2 turnos (racha de 20s)?
  → tier_bonus = +1 (obtenés skill POCO COMÚN en vez de COMÚN)

¿Llegaste al threshold 40 en ≥ 8 turnos?
  → tier_bonus = 0 (COMÚN, te costó llegar)
```

La calidad de lo que desbloqueás depende de cómo lo conseguiste, no solo de cuándo.

### Thresholds por turnos_ganados (dominancia)

| Turnos ganados consecutivos | Efecto |
|----------------------------|--------|
| 3 seguidos | +1 modificador pasivo (dominio táctico) |
| 5 seguidos | Skill RARA guaranteed (presión aplastante) |
| Llegar a 8 ganados total | Desbloquea narrativa de "rendición posible" |

### Punición por racha baja (low_streak)

```
low_streak ≥ 3 tiradas consecutivas ≤ 4:
  → activa VACILACION
  → -2 a tiradas por 2 turnos
  → narrativa: duda, miedo instintivo

low_streak ≥ 5 tiradas consecutivas ≤ 4:
  → activa PANICO
  → -3 y bloquea acción ATAQUE por 1 turno
  → narrativa: modo supervivencia pura
```

---

## 13. NARRATIVA — PROPIEDADES MECÁNICAS

La narrativa no es texto decorativo. Funciona así:

```
1. El engine resuelve el outcome
2. Lee los estados activos (combat_effects)
3. Lee los acumuladores y skills activos
4. Combina los tags de todo lo activo
5. Selecciona template de narrativa filtrado por esos tags
6. El template puede incluir "activaciones adicionales" de estado
7. Esas activaciones se procesan y se persisten
```

### Ejemplo de cadena narrativa → mecánica

```
Outcome: ATK vs DEF, ATK gana con BOTH_HIGH + diferencia ALTA
Tags activos: [potencia_alta, defensa_fallida, momentum_atacante]
Template seleccionado: "El golpe rompe la guardia — [receptor] pierde el equilibrio"
Activación adicional: → POS_DESFAVORABLE en receptor (próximo turno -3)
```

La narrativa "decidió" que el receptor perdió el equilibrio. Eso tiene efecto real.

---

## 14. OUTCOME MATRIX — ESTRUCTURA

La tabla central del engine. Cada entrada resuelve una combinación de:

```
(par_acción, difference_band, power_context, battle_context) → outcome_code
```

### Ejemplo parcial (los 6 casos más importantes)

| Par | Diff band | Power context | Battle context | Outcome |
|-----|-----------|---------------|----------------|---------|
| ATK/ATK | Baja | BOTH_HIGH | cualquiera | CHOQUE_EPICO: daño mutuo leve, ambos -0.5 contador, narrativa intensa |
| ATK/ATK | Baja | BOTH_LOW | cualquiera | TROPIEZO_MUTUO: ambos pierden posición, narrativa torpe |
| ATK/ATK | Extrema | MIXED_EXTREME | turno < 3 | DOMINIO_ABSOLUTO: KO posible si TRANSCENDENTE vs COLAPSO |
| ATK/DEF | Baja | BOTH_HIGH | cualquiera | BLOQUEO_SOLIDO: defensa aguanta, contraataque parcial |
| ATK/DEF | Alta | MIXED_EXTREME | cualquiera | GUARDIA_ROTA: receptor cae, pierde siguiente fase |
| DEF/DEF | cualquiera | BOTH_HIGH | cualquiera | REPOSICIONAMIENTO_EPICO: ventaja táctica para uno, no hay daño |

> Esta tabla se completa iterativamente. El MVP necesita cubrir los 6 pares × 3-4 bandas clave = ~24 entradas base. Las entradas restantes se agregan durante testing.

---

## 15. MODOS DE JUEGO

### Modo Simulación
- Armas: random al inicio
- Sin intervención del jugador (el engine corre solo)
- Ideal para ver narrativa emergente
- Se pueden correr múltiples batallas y comparar

### Modo Arcade
- Jugador elige arma
- Jugador elige acción por fase (o uno de los dos, PvE)
- Narrativa más enfocada en decisiones del jugador

**Ambos modos usan el mismo engine.** La diferencia es quién provee los inputs de acción.

---

## 16. BASE DE DATOS — TABLAS CLAVE

```sql
-- Potencia (actualizar con rangos del Excel)
core_dice_power (min_value, max_value, power_level, label)

-- Bandas de diferencia (7 niveles del Excel)
core_difference_band (min_diff, max_diff, band_name, bono_value)

-- Modificadores
core_modifiers (code, name, modifier_value, duration_scope, applies_to, source_type)

-- Efectos / estados (tabla de verdad de la batalla)
combat_effects (code, name, duration_phases, applies_to, power_mod,
                blocks_next_action, blocks_recovery, narrative_tags)

-- Armas (del Excel hoja 2)
core_weapons (code, name, damage_base, hits_per_phase, crit_chance, crit_damage_bonus)

-- Pool de skills
skill_pool (code, name, tier, duration_phases, effect_type, power_mod, special_tags)

-- Configuración de batalla (modo, condición de victoria)
battle_config (win_condition, max_counters, recovery_enabled,
               recovery_amount, recovery_interval_turns, crit_block_turns)

-- Outcomes posibles
outcome_matrix (action_pair, difference_band, power_context,
                outcome_code, base_weight, effects_to_apply, narrative_pool_tag)

-- Multiplicadores de estado sobre outcomes (el corazón del sistema de pesos)
-- Cada fila dice: "cuando ESTADO X está activo, el outcome Y multiplica su peso por Z"
state_outcome_weights (state_code, outcome_code, multiplier, applies_to)
-- Ejemplo: ('CAIDO', 'FATAL_ESTOCADA', 2.5, 'RECEPTOR')
-- Ejemplo: ('NIEBLA_EXTREMA', 'FATAL_CAIDA_VACIO', 5.0, 'BOTH')

-- Runtime: acumuladores por batalla
battle_accumulators (battle_id, player, roll_sum, consecutive_high,
                     low_streak, twenties_count, turns_won, last_threshold)

-- Runtime: skills activas en batalla
battle_skills (battle_id, player, skill_code, activated_at_turn, expires_at_phase)

-- Log de batalla (ya existe en el starter)
battle_log (battle_id, turn, phase, action_p1, action_p2, roll_p1, roll_p2,
            effective_p1, effective_p2, power_p1, power_p2, difference,
            difference_band, power_context, outcome_code, narrative_text,
            counters_p1, counters_p2, states_applied)
```

---

## 17. FLUJO DEL ENGINE (resolve_phase)

```
1. Recibir: battle_id, action_p1, action_p2

2. Calcular tiradas
   d1 = random(1,20) + sum(active_mods_p1)
   d2 = random(1,20) + sum(active_mods_p2)

3. Clasificar
   power_p1 = get_power_level(d1)        ← tabla core_dice_power
   power_p2 = get_power_level(d2)        ← tabla core_dice_power
   difference = abs(d1 - d2)
   diff_band = get_diff_band(difference)  ← tabla core_difference_band
   power_context = get_power_context(power_p1, power_p2)

4. Determinar gates
   action_pair = (action_p1, action_p2)
   battle_ctx = get_battle_context(battle_state)  ← turno, debuffs, estados

5. Consultar outcome
   outcome = query outcome_matrix(action_pair, diff_band, power_context, battle_ctx)

6. Aplicar efectos
   apply_effects(outcome.effects_to_apply)  → actualiza combat_effects

7. Actualizar contadores
   update_counters(outcome)  → usando weapon stats si aplica

8. Actualizar acumuladores
   update_accumulators(battle_id, d1, d2, turn_winner)
   check_skill_thresholds()  → activa skills si corresponde
   check_low_streak()        → activa VACILACION/PANICO si corresponde
   check_turns_won_bonus()   → activa mejora de dominancia si corresponde

9. Generar narrativa
   active_tags = get_all_active_tags(battle_state)
   narrative = select_narrative_template(outcome.narrative_pool_tag, active_tags)
   process_narrative_activations(narrative)  → estados adicionales si corresponde

10. Verificar condición de fin
    if counters_p1 >= 15 or counters_p2 >= 15: end_battle()

11. Persistir log completo
```

---

## 18. DECISIONES CERRADAS

| # | Decisión | Resultado |
|---|----------|-----------|
| 1 | Turnos ganados | Mayoría (2/3 fases). Empate de turno = +0 para ambos. |
| 2 | Recuperación de contadores | Automática: -0.5 cada 3 turnos. Bloqueada en el ciclo siguiente a recibir un crítico. |
| 3 | Desmembramiento | Modificador permanente -5 a todas las tiradas. No toca el cap de contadores. Bloquea over-20 permanentemente incluso con buff máximo. El daño del golpe causante es el daño normal del outcome (no es crítico obligatorio). Puede venir de INT o entorno, no solo de combate. |
| 4 | Gates de KO por turno | **ELIMINADOS.** Reemplazados por sistema de pesos por estado activo. Un KO es posible en cualquier turno — la probabilidad la determinan los estados activos (entorno, posición, debuffs), no el tiempo transcurrido. |
| 5 | Narrativa fatal | Pool `OUTCOME_FATAL` con múltiples expresiones seleccionadas por tags activos (weapon, env, position, power_context). No hay un único "KO" — hay estocadas, hachazos, caídas al vacío, remates, degüellos, según el contexto de estados. |

## 18b. DECISIONES CERRADAS — SEGUNDA RONDA

| # | Decisión | Resultado |
|---|----------|-----------|
| 1 | ARMA_ROTA | Permanente. INT exitosa → `IMPROVISA` (±0). No recupera bono original. |
| 2 | Skills pool | Pool predefinido por tier, selección random al desbloquear. |
| 3 | Modos | SIMULATION + PVE en MVP. PVP = mismo engine, inputs humanos, sin progresión. Roguelike solo PVE. |
| 4 | Bono de diferencia | Siguiente fase como modificador activo (momentum). Solo al ganador. Se consume al usarse. |
| 5 | Entornos | Pre-batalla (arena) + dinámicos mid-battle por INT. |
| 6 | CAÍDO×2 | Multiplicadores FATAL se anulan. INT exitosa → ×1.8 situacional. |
| 7 | DESARMADO×2 | Filtra pool de narrativa: desactiva `requires_filo`, activa `unarmed_combat`. |
| 8 | Estilos de combate | MVP: solo narrativa (tags). Mecánicas de peso post-MVP. |

## 18c. DECISIONES CERRADAS — TERCERA RONDA

| # | Decisión | Resultado |
|---|----------|-----------|
| 1 | Ganador de fase | Dos trackers independientes: `roll_winner` (quién sacó más) y `phase_winner` (quién beneficia el outcome). `turns_won` usa `roll_winner`. Skills/narrativa secundaria usan ambos. Editable sin refactor. |
| 2 | Cap de modificadores + overflow | Cap en 25 (TRANSCENDENTE). Overflow se guarda como `MOMENTUM_OVERFLOW` y aplica como modificador en la siguiente fase (se consume al usarse, acumulable). |
| 3 | Duración de buffs | Tres categorías: intra-turno (next_phase), multi-turno (N turnos en tabla), permanente (duration=-1). Skills pueden extender categoría de cualquier estado. |
| 4 | outcome_matrix | No requiere 252 filas para MVP. Fallback en cascada: exacto → par+banda → par default → genérico. Se completa durante testing sin tocar código. |
| 5 | Sistema de armas | Por tamaño (PEQUEÑA/MEDIANA/GRANDE). El tamaño define mecánica. El arma específica define tags narrativos. Agregar arma = 1 fila en tabla. |
| 6 | Daño PEQUEÑA | 2 hits independientes, cada uno resuelve crit propio. 7 outcomes posibles. Doble crit simultáneo = 2.5 (bonus especial). |
| 7 | Daño GRANDE | 1 hit: leve=0.5, normal=1.5, fuerte=2.5, crítico=4.0. Sin dual ni shield. Puede defender (sin bonus de shield). |
| 8 | DUAL ceiling | MEDIANA+MEDIANA: crítico 4.0 (igual que GRANDE). Mismo techo, distinto camino (2 pasos vs 1). Balanceado. |

---

## 19. CRITERIO DE MVP

El MVP está completo cuando:

1. Se puede iniciar una batalla (con weapon assignment)
2. Ambos jugadores/el sistema eligen acción por fase
3. El engine resuelve con **tirada + potencia + power_context + difference_band**
4. Se aplican estados de la tabla combat_effects
5. Se actualiza contador de cada jugador
6. Se detecta condición de fin (contador ≥ 15)
7. Se genera narrativa con tags de estado
8. Se registra log completo
9. Los acumuladores se trackean (aunque los skills lleguen en v2)
10. Las tablas base son editables desde `bases.html`

---

## 20. LO QUE VIENE DESPUÉS DEL MVP

- Sistema completo de skills con pool por tier
- Punición por low_streak (VACILACION / PANICO)
- Múltiples armas (expandir tabla)
- Modo simulación: correr N batallas y mostrar estadísticas
- Progresión PVM (experiencia entre batallas)
- Frontend de combate animado (eventos paso a paso)
- Entorno dinámico (VIDRIO_ROTO y similares)

---

*Última actualización: 2026-04-08*
*Basado en: SPEC.md, GAME_RULES.md del starter + Excel "Roll and Fight.xlsx" + sesión de diseño.*
