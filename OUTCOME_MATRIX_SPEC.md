# OUTCOME_MATRIX_SPEC — Combatrol
**Versión:** 1.0 — Para llenado con GPT en paralelo a implementación
**Fecha:** 2026-04-08

Este documento es la especificación completa para generar el contenido de la tabla `outcome_matrix` del engine de Combatrol. Está diseñado para ser entregado a GPT (u otro LLM) como contexto completo, para que llene los ~40 entries del MVP más los fallbacks.

---

## 1. CONTEXTO DEL ENGINE

Combatrol es un simulador de batalla por fases (battle idle). Cada fase del combate:
1. Ambos jugadores eligen acción simultáneamente: `ATK`, `DEF`, o `INT`
2. Ambos tiran 1d20 + modificadores activos (rango efectivo: -4 a 25)
3. El engine calcula `difference_band` y `power_context`
4. Consulta `outcome_matrix` para elegir qué pasa
5. Aplica efectos y genera narrativa

**Condición de fin:** Llegar a 15 contadores = derrota. Los contadores son el equivalente a HP (no HP numérico — acumulación de impacto de batalla).

**Filosofía:** Siempre pasa algo. No hay fases vacías. ATK presiona, DEF contraataca, INT modifica el campo.

---

## 2. ESTRUCTURA DE LA TABLA

```sql
CREATE TABLE outcome_matrix (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    action_pair       TEXT NOT NULL,   -- ej: ATK_ATK
    difference_band   TEXT NOT NULL,   -- ej: BAJA, o DEFAULT para fallback
    power_context     TEXT NOT NULL,   -- ej: BOTH_HIGH, o DEFAULT para fallback
    outcome_code      TEXT NOT NULL UNIQUE,
    phase_winner      TEXT NOT NULL,   -- A | B | NONE
    counter_dmg_A     REAL DEFAULT 0,  -- daño al jugador A (acción izquierda del par)
    counter_dmg_B     REAL DEFAULT 0,  -- daño al jugador B (acción derecha del par)
    effect_A          TEXT DEFAULT NULL, -- código de estado aplicado a A (o NULL)
    effect_B          TEXT DEFAULT NULL, -- código de estado aplicado a B (o NULL)
    base_weight       REAL DEFAULT 1.0,  -- peso base para selección ponderada
    narrative_pool_tag TEXT NOT NULL,    -- tag para buscar template de narrativa
    is_fatal          INTEGER DEFAULT 0  -- 1 si puede terminar la batalla directamente
);
```

### Convención de "A" y "B"

En cada par `X_Y`:
- **A** = jugador que eligió la acción `X` (la de la izquierda)
- **B** = jugador que eligió la acción `Y` (la de la derecha)

Ejemplo: `ATK_DEF` → A es el atacante, B es el defensor.
Ejemplo: `DEF_INT` → A eligió DEF, B eligió INT.

`phase_winner` = quién se beneficia del outcome: `A`, `B`, o `NONE` (daño/beneficio simétrico o neutro).

---

## 3. VALORES VÁLIDOS POR CAMPO

### action_pair (9 posibles)
```
ATK_ATK  ATK_DEF  ATK_INT
DEF_ATK  DEF_DEF  DEF_INT
INT_ATK  INT_DEF  INT_INT
```

> **Nota:** `ATK_DEF` y `DEF_ATK` son pares distintos. En `ATK_DEF`: A ataca, B defiende. En `DEF_ATK`: A defiende, B ataca. El engine asigna a cada jugador su posición antes de consultar la tabla.

### difference_band (7 + fallback)
| Código | Diferencia de tiradas efectivas | Bono al ganador |
|--------|----------------------------------|-----------------|
| `BAJA` | 0-3 | +0 |
| `MODERADA` | 4-7 | +1 |
| `REGULAR` | 8-10 | +2 |
| `ALTA` | 11-13 | +3 |
| `MUY_ALTA` | 14-16 | +4 |
| `MAXIMA` | 17-19 | +5 |
| `EXTREMA` | ≥20 | +6 |
| `DEFAULT` | Fallback de par (sin banda específica) | — |

### power_context (4 + fallback)
| Código | Condición |
|--------|-----------|
| `BOTH_HIGH` | Ambos ≥ P5 (tirada 17+) |
| `BOTH_LOW` | Ambos ≤ P2 (tirada ≤ 9) |
| `MIXED_EXTREME` | Diferencia de potencia ≥ 4 niveles |
| `BALANCED` | El resto (ninguna de las anteriores) |
| `DEFAULT` | Fallback de par (sin contexto específico) |

### Niveles de Potencia (referencia)
| Tirada efectiva | Potencia | Label |
|----------------|----------|-------|
| ≤ 0 | P0 | COLAPSO |
| 1-5 | P1 | |
| 6-9 | P2 | |
| 10-13 | P3 | |
| 14-16 | P4 | |
| 17-19 | P5 | |
| 20 | P6 | |
| 21-22 | P7 | LÍMITE |
| 23-25 | P8 | TRANSCENDENTE |

### phase_winner
```
A     → el jugador A (acción izquierda) gana la fase
B     → el jugador B (acción derecha) gana la fase
NONE  → empate, simétrico, o nadie gana (ambos reciben igual, o es puramente posicional)
```

### counter_dmg_A y counter_dmg_B
Valores posibles (en contadores, paso de 0.5):
```
0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 15.0 (KO inmediato, rarísimo)
```
**Referencia de daño:**
| Tipo | Contadores |
|------|-----------|
| Sin daño | 0 |
| Roce / daño leve | 0.5 |
| Golpe normal | 1.0 |
| Golpe sólido | 1.5 |
| Golpe fuerte | 2.0 |
| Crítico | 3.0 |
| Crítico devastador | 4.0 |
| Fatal / KO | 15.0 (solo con is_fatal=1 y peso muy bajo) |

> El daño final se modifica por el tamaño del arma equipada (PEQUEÑA/MEDIANA/GRANDE). El valor en la matriz es el daño *base del outcome*. El engine lo multiplica por el factor del arma cuando corresponde. Para el llenado, usá los valores de la tabla como daño con arma MEDIANA de referencia.

### effect_A y effect_B (códigos de estado disponibles)

```
NULL              → sin efecto
CAIDO             → pierde siguiente fase. Oponente recibe HIPEROFFENSIVO si no tiene debuff.
DESARMADO         → permanente, -3 a tiradas
ARMA_ROTA         → permanente, -2 a tiradas, INT→IMPROVISA
DESMEMBRADO       → permanente, -5 a tiradas, bloquea over-20
CONTRA_EXITOSO    → +4 a próxima tirada (1 fase)
POS_FAVORABLE     → +3 hasta removido
POS_DESFAVORABLE  → -3 hasta removido
FATIGA            → -3 a primera fase del turno siguiente (ATK spam)
VACILACION        → -2 por 2 turnos (low streak automático, no para matrix)
PANICO            → -3, bloquea ATK 1 turno (low streak automático, no para matrix)
HIPEROFFENSIVO    → +5, 1 fase (se aplica automáticamente por CAIDO del oponente)
VIDRIO_ROTO       → estado de entorno, 3 turnos, peligro posicional
MOMENTUM_OVERFLOW → carry de overflow de cap 25 (se aplica automáticamente, no para matrix)
```

> Para el llenado de la matrix: usá principalmente `CAIDO`, `DESARMADO`, `ARMA_ROTA`, `DESMEMBRADO`, `CONTRA_EXITOSO`, `POS_FAVORABLE`, `POS_DESFAVORABLE`, `FATIGA`. Los estados `HIPEROFFENSIVO`, `VACILACION`, `PANICO`, y `MOMENTUM_OVERFLOW` se aplican automáticamente por otras reglas del engine.

### base_weight
Peso relativo para selección ponderada entre outcomes del mismo (pair, band, context).
- Suma de pesos dentro de un grupo no necesita ser 1.0 — el engine normaliza.
- El engine multiplica estos pesos por `state_outcome_weights` activos antes de seleccionar.
- Convención sugerida: outcomes comunes = 0.5-1.0 / raros = 0.05-0.2 / fatales = 0.01-0.05

### narrative_pool_tag
String tag que el engine usa para buscar templates en `narrative_templates`. Convención:
```
{PAR}_{RESULTADO}_{CALIFICADOR}

Ejemplos:
  ATK_DEF_BLOQUEO_SOLIDO
  ATK_ATK_CHOQUE_EPICO
  INT_DEF_CASTER_ACTIVADO
  FATAL_ESTOCADA
  DEF_DEF_REPOSICIONAMIENTO
```
Puede incluir calificadores adicionales con underscore: `ATK_DEF_GUARDIA_ROTA_BOTH_HIGH`

### is_fatal
```
0 → outcome normal
1 → puede terminar la batalla. El engine verifica contadores después de aplicarlo.
```

---

## 4. SISTEMA DE FALLBACK EN CASCADA

El engine busca en este orden:
1. **Exacto**: `action_pair + difference_band + power_context` (las 252 combinaciones posibles)
2. **Par + banda**: `action_pair + difference_band + power_context=DEFAULT`
3. **Par default**: `action_pair + difference_band=DEFAULT + power_context=DEFAULT`
4. **Genérico**: `action_pair=GENERIC + difference_band=DEFAULT + power_context=DEFAULT`

**Para el MVP, se necesitan obligatoriamente:**
- 9 entradas "par default" (una por par, con `difference_band=DEFAULT, power_context=DEFAULT`)
- 1 entrada genérica (`action_pair=GENERIC, difference_band=DEFAULT, power_context=DEFAULT`)
- ~30-40 entradas específicas priorizadas (las más dramáticas / importantes)

**Las 252 entradas específicas se completan iterativamente durante testing, sin tocar código.**

---

## 5. FILOSOFÍA POR PAR DE ACCIÓN

### ATK_ATK — Choque frontal
Ambos atacan al mismo tiempo. Nadie se cuida. La diferencia determina quién conecta más duro.
- **BAJA**: Ambos golpean. Daño leve mutuo. Narrativa de intercambio rápido.
- **MODERADA/REGULAR**: El que saca más golpea con ventaja. El otro también algo.
- **ALTA+**: Dominio claro del de mayor tirada. El otro puede caer o perder arma.
- **EXTREMA+MIXED_EXTREME**: Casi KO. El de menor tirada puede quedar en COLAPSO.
- **BOTH_HIGH**: Mismo patrón pero con más narrativa épica — ambos son peligrosos.
- **BOTH_LOW**: Torpe, sin energía. Daño mínimo. Posible caída de alguno.
- **ATK spam penalty**: En 3+ ATKs consecutivos, la lógica de FATIGA se activa automáticamente (fuera de la matrix). La matrix NO necesita penalizar el spam — eso lo hace el engine.

### ATK_DEF — Ataque vs Defensa
El par más asimétrico. A presiona, B absorbe o contraataca.
- **BAJA**: La defensa aguanta parcialmente. Daño reducido a B. Posible CONTRA_EXITOSO a A.
- **MODERADA**: Defensa sólida o ataque que pasa justo. Según quién saque más.
- **ALTA**: Si A saca más → guardia rota, B cae o recibe daño alto. Si B saca más → CONTRA devastador.
- **EXTREMA**: Si A domina → DESARMADO o CAIDO en B. Si B domina → contraataque épico con daño alto a A.
- **BOTH_HIGH**: La defensa es perfecta o el ataque es imparable. Poca tierra intermedia.
- **BOTH_LOW**: Torpe por ambos lados. El ataque raspa, la defensa es irregular.

### DEF_ATK — Defensa vs Ataque
Igual que ATK_DEF pero con roles A/B invertidos. A defiende, B ataca.
> En la table, son entradas separadas porque A y B tienen roles distintos (las columnas dmg_A y dmg_B refieren a jugadores con acciones distintas). Si usás el mismo outcome_code para ATK_DEF y DEF_ATK, debés invertir quién recibe qué.

**Consejo de llenado:** Los outcomes de DEF_ATK son los mirrors de ATK_DEF pero con A=defensor y B=atacante. Podés referenciar la lógica de ATK_DEF y adaptar los campos A/B.

### DEF_DEF — Ambos defienden
El par más neutro. Nadie ataca. El combate se pausa tácticamente.
- **BAJA/MODERADA**: Reposicionamiento. Ninguno recibe daño. Uno puede ganar POS_FAVORABLE.
- **ALTA+**: El que sacó mucho más logró maniobrar mejor. Gana posición clara.
- **BOTH_HIGH**: Duelo táctico de alto nivel. Reposicionamiento épico. Potencial setup para lo que sigue.
- **BOTH_LOW**: Desorientación mutua. Ninguno sabe bien dónde está. Posible POS_DESFAVORABLE para ambos.
- **Daño:** Nunca daño alto en DEF_DEF. Máximo 0.5 (un roce mientras ambos se reposicionan).

### DEF_INT — Defensa vs Interacción
A defiende, B trata de modificar el campo.
- Si B (INT) supera ampliamente: B logra POS_FAVORABLE o activa efecto de entorno. A recibe POS_DESFAVORABLE.
- Si A (DEF) supera: La maniobra de INT falló, B quedó expuesto. A puede contraatacar (CONTRA_EXITOSO).
- **BAJA**: La INT parcialmente funciona — algún cambio menor sin coste grande.
- **BOTH_HIGH**: La INT de B es brillante. Transición de estado significativa.

### INT_DEF — Interacción vs Defensa
A intenta modificar el campo, B defiende. Mirror de DEF_INT con roles invertidos.

### ATK_INT — Ataque vs Interacción
A ataca, B intenta maniobrar en vez de defenderse. Riesgoso para B.
- B apostó a cambiar el campo en vez de bloquearse. Si A domina: B recibe daño sin defensa.
- Si B supera (INT brillante + mala tirada de A): B evitó + logró algo del entorno.
- **Alta diferencia a favor de A**: B recibe daño alto + posiblemente CAIDO (sin defensa).
- **Alta diferencia a favor de B**: El ataque de A falló por distracción propia. B logra reposicionamiento.

### INT_ATK — Interacción vs Ataque
A maniobra, B ataca. Mirror de ATK_INT con roles A/B invertidos.

### INT_INT — Ambos intentan modificar el campo
El par más impredecible. Nadie ataca ni defiende. Todo es maniobra.
- **BAJA**: Ambos logran algo menor. Posición levemente modificada.
- **ALTA+**: El que dominó logró su maniobra. El otro quedó expuesto o fallido.
- **BOTH_HIGH**: Ambos son tácticos de alto nivel. La que prevalece es brillante.
- **BOTH_LOW**: Caos. Nadie sabe qué está haciendo. Posible situación cómica narrativamente.
- **EXTREMA**: La INT dominante puede activar CASTER si el entorno lo permite (efecto narrativo, el engine lo decide aparte).
- **Daño:** Raramente hay daño en INT_INT — es un par posicional. Si hay daño, es colateral (0.5 máximo en la mayoría de casos, salvo outcomes muy específicos).

---

## 6. OUTCOMES FATALES — REGLAS ESPECIALES

Los outcomes fatales (`is_fatal=1`) tienen:
- `base_weight` muy bajo (0.01 a 0.05)
- `counter_dmg` que puede llevar directamente a 15 contadores
- Se amplifican por `state_outcome_weights` activos (ej: CAIDO×2.5, VACIO×3.0)

**Outcomes fatales base disponibles (narrative_pool_tag sugeridos):**
```
FATAL_ESTOCADA         → requires tag: filo (desactivado si BOTH_DESARMADO)
FATAL_HACHAZO          → requires tag: filo / arma pesada
FATAL_DEGÜELLO         → requires tag: filo + diferencia extrema
FATAL_REMATE           → receptor CAIDO, atacante cierra
FATAL_CAIDA_VACIO      → entorno VACIO activo
FATAL_ESTRANGULACION   → unarmed_combat (activo si BOTH_DESARMADO)
FATAL_IMPACTO_CRANEAL  → unarmed_combat
FATAL_ENTORNO          → env_available (vidrios, precipicio, etc.)
```

Los fatales **SOLO aplican en pares donde tiene sentido:**
- `ATK_DEF` (ataque domina con diferencia EXTREMA)
- `ATK_ATK` (choque con MIXED_EXTREME extremo)
- `INT_DEF` / `INT_ATK` (si es INT de entorno + oponente expuesto)
- **Nunca en DEF_DEF, ni en ATK_INT cuando INT domina.**

---

## 7. FORMATO CSV PARA LLENADO

```csv
action_pair,difference_band,power_context,outcome_code,phase_winner,counter_dmg_A,counter_dmg_B,effect_A,effect_B,base_weight,narrative_pool_tag,is_fatal
```

**Reglas de llenado:**
1. `outcome_code` debe ser único en toda la tabla. Convención: `{PAR}_{BAND}_{CTX}_{NOMBRE}` para específicos, `{PAR}_DEFAULT_{NOMBRE}` para fallbacks.
2. Si `effect_A` o `effect_B` es NULL, escribir `NULL` (sin comillas).
3. Los decimales usan punto: `1.0` no `1,0`.
4. `is_fatal`: solo `0` o `1`.
5. Se pueden tener múltiples filas con el mismo `(action_pair, difference_band, power_context)` — el engine elige por peso ponderado.
6. Para fallbacks de par: `difference_band=DEFAULT, power_context=DEFAULT`.
7. Para el fallback genérico: `action_pair=GENERIC, difference_band=DEFAULT, power_context=DEFAULT`.

---

## 8. EJEMPLOS COMPLETOS (10 filas trabajadas)

```csv
action_pair,difference_band,power_context,outcome_code,phase_winner,counter_dmg_A,counter_dmg_B,effect_A,effect_B,base_weight,narrative_pool_tag,is_fatal
```

### Ejemplo 1: ATK_ATK + BAJA + BOTH_HIGH
Dos luchadores de alto nivel se golpean simultáneamente con tiradas parecidas. Choque épico, ambos reciben algo.
```csv
ATK_ATK,BAJA,BOTH_HIGH,ATK_ATK_BAJA_BH_CHOQUE_EPICO,NONE,0.5,0.5,NULL,NULL,0.7,ATK_ATK_CHOQUE_EPICO,0
```
*Ambos reciben 0.5 contadores. Nadie gana la fase. Narrativa: intercambio brutal de dos fuerzas iguales.*

### Ejemplo 2: ATK_ATK + EXTREMA + MIXED_EXTREME
Un luchador de P8 vs uno de P1. Dominio absoluto.
```csv
ATK_ATK,EXTREMA,MIXED_EXTREME,ATK_ATK_EXT_MX_DOMINIO_ABSOLUTO,A,0.0,3.0,NULL,CAIDO,0.5,ATK_ATK_DOMINIO_ABSOLUTO,0
ATK_ATK,EXTREMA,MIXED_EXTREME,ATK_ATK_EXT_MX_FATAL_CHOQUE,A,0.0,15.0,NULL,NULL,0.03,FATAL_REMATE,1
```
*Entrada principal: B cae y recibe 3 contadores (crítico). Entry fatal paralela: posibilidad baja de terminar la batalla.*

### Ejemplo 3: ATK_DEF + BAJA + BALANCED
Ataque leve, defensa aguanta. El defensor logra parcialmente lo suyo.
```csv
ATK_DEF,BAJA,BALANCED,ATK_DEF_BAJA_BAL_BLOQUEO_PARCIAL,B,0.0,0.5,NULL,NULL,0.6,ATK_DEF_BLOQUEO_PARCIAL,0
ATK_DEF,BAJA,BALANCED,ATK_DEF_BAJA_BAL_CONTRA_PARCIAL,B,0.5,0.0,POS_DESFAVORABLE,CONTRA_EXITOSO,0.3,ATK_DEF_CONTRA_PARCIAL,0
```
*Opción 1: El ataque roza pero la defensa aguanta, B mantiene posición.*
*Opción 2: La defensa fue tan sólida que B ganó posición y tiene bono para la siguiente fase.*

### Ejemplo 4: ATK_DEF + ALTA + BOTH_HIGH
Ataque fuerte vs defensa sólida. Si A supera: guardia rota. Aquí A saca más (ambos en P5+, diferencia 11-13).
```csv
ATK_DEF,ALTA,BOTH_HIGH,ATK_DEF_ALTA_BH_GUARDIA_ROTA,A,0.0,2.0,NULL,CAIDO,0.5,ATK_DEF_GUARDIA_ROTA,0
ATK_DEF,ALTA,BOTH_HIGH,ATK_DEF_ALTA_BH_CONTRA_EPICO,B,1.5,0.0,POS_DESFAVORABLE,CONTRA_EXITOSO,0.4,ATK_DEF_CONTRA_EPICO,0
```
*Dos outcomes posibles para el mismo slot: ¿rompió la guardia o contraatacó épicamente?*

### Ejemplo 5: DEF_DEF + MODERADA + BOTH_HIGH
Dos defensores de alto nivel. El que sacó más logra reposicionarse mejor.
```csv
DEF_DEF,MODERADA,BOTH_HIGH,DEF_DEF_MOD_BH_REPOSICIONAMIENTO,A,0.0,0.0,POS_FAVORABLE,POS_DESFAVORABLE,0.6,DEF_DEF_REPOSICIONAMIENTO,0
DEF_DEF,MODERADA,BOTH_HIGH,DEF_DEF_MOD_BH_ESPERA,NONE,0.0,0.0,NULL,NULL,0.4,DEF_DEF_ESPERA_TACTICA,0
```
*A sacó más (diferencia MODERADA) → gana posición. Alternativa: puro tanteo táctico.*

### Ejemplo 6: INT_ATK + ALTA + BALANCED
A intenta INT, B ataca. B supera en diferencia ALTA: A está expuesto.
```csv
INT_ATK,ALTA,BALANCED,INT_ATK_ALTA_BAL_INT_FALLIDA_GOLPE,B,2.0,0.0,CAIDO,NULL,0.5,INT_ATK_INT_FALLIDA,0
INT_ATK,ALTA,BALANCED,INT_ATK_ALTA_BAL_INT_FALLIDA_LEVE,B,1.0,0.0,POS_DESFAVORABLE,NULL,0.4,INT_ATK_INT_FALLIDA_LEVE,0
```
*A intentó modificar el campo y B la castigó con diferencia amplia. CAIDO en A en el outcome más severo.*

### Ejemplo 7: INT_INT + BAJA + BOTH_LOW
Ambos intentan INT con tiradas bajas. Caos torpe, nadie logra nada claro.
```csv
INT_INT,BAJA,BOTH_LOW,INT_INT_BAJA_BL_CAOS_TORPE,NONE,0.0,0.0,NULL,NULL,0.5,INT_INT_CAOS_TORPE,0
INT_INT,BAJA,BOTH_LOW,INT_INT_BAJA_BL_TROPIEZO_MUTUO,NONE,0.5,0.5,POS_DESFAVORABLE,POS_DESFAVORABLE,0.4,INT_INT_TROPIEZO_MUTUO,0
```
*Opción 1: narrativa cómica/caótica, sin consecuencias mecánicas.*
*Opción 2: ambos se estorban y pierden posición.*

### Ejemplo 8: ATK_INT + BAJA + BALANCED
A ataca, B intenta INT con tirada parecida. La INT logra parcialmente su objetivo.
```csv
ATK_INT,BAJA,BALANCED,ATK_INT_BAJA_BAL_INT_PARCIAL,B,0.5,0.0,NULL,POS_FAVORABLE,0.5,ATK_INT_INT_PARCIAL,0
ATK_INT,BAJA,BALANCED,ATK_INT_BAJA_BAL_ATAQUE_ROZA,A,0.0,0.5,NULL,NULL,0.4,ATK_INT_ATAQUE_ROZA,0
```
*Con diferencia mínima, cualquiera puede "ganar" este intercambio.*

### Ejemplo 9: Fallback de par — ATK_DEF (sin banda ni contexto específico)
```csv
ATK_DEF,DEFAULT,DEFAULT,ATK_DEF_DEFAULT_BLOQUEO,B,0.0,0.5,NULL,NULL,0.5,ATK_DEF_BLOQUEO_GENERICO,0
ATK_DEF,DEFAULT,DEFAULT,ATK_DEF_DEFAULT_IMPACTO,A,0.0,1.0,NULL,NULL,0.4,ATK_DEF_IMPACTO_GENERICO,0
ATK_DEF,DEFAULT,DEFAULT,ATK_DEF_DEFAULT_CONTRA,B,0.5,0.0,POS_DESFAVORABLE,CONTRA_EXITOSO,0.1,ATK_DEF_CONTRA_GENERICO,0
```
*Este fallback aplica a cualquier (ATK_DEF, cualquier banda, cualquier contexto) que no tenga entrada específica.*

### Ejemplo 10: Fallback genérico global
```csv
GENERIC,DEFAULT,DEFAULT,GENERIC_INTERCAMBIO_NEUTRO,NONE,0.5,0.5,NULL,NULL,0.7,GENERIC_INTERCAMBIO,0
GENERIC,DEFAULT,DEFAULT,GENERIC_VENTAJA_LEVE,A,0.0,0.5,NULL,NULL,0.3,GENERIC_VENTAJA_LEVE,0
```
*Último recurso si ningún otro fallback existe. Siempre debe haber algo.*

---

## 9. LISTA DE ENTRIES PRIORITARIAS PARA MVP (~40 filas)

### Obligatorias: 9 fallbacks de par + 1 genérico (10 filas)
Para cada uno de los 9 pares, una entrada DEFAULT. Más la genérica.
```
ATK_ATK / DEFAULT / DEFAULT
ATK_DEF / DEFAULT / DEFAULT
DEF_ATK / DEFAULT / DEFAULT
DEF_DEF / DEFAULT / DEFAULT
ATK_INT / DEFAULT / DEFAULT
INT_ATK / DEFAULT / DEFAULT
DEF_INT / DEFAULT / DEFAULT
INT_DEF / DEFAULT / DEFAULT
INT_INT / DEFAULT / DEFAULT
GENERIC / DEFAULT / DEFAULT
```

### Específicas prioritarias (~30 filas recomendadas)

**ATK_ATK (6 específicas):**
- BAJA + BOTH_HIGH (choque épico)
- BAJA + BOTH_LOW (torpeza mutua)
- EXTREMA + MIXED_EXTREME (dominio absoluto, incluye fatal)
- MODERADA + BALANCED (intercambio normal)
- ALTA + BALANCED (uno domina, caída posible)
- BAJA + MIXED_EXTREME (una tirada altísima, otra muy baja, pero fue ATK+ATK — raro)

**ATK_DEF (6 específicas):**
- BAJA + BALANCED (bloqueo parcial, posible contra)
- ALTA + BOTH_HIGH (guardia rota o contra épico)
- EXTREMA + MIXED_EXTREME (puede incluir fatal)
- BAJA + BOTH_LOW (ataque torpe, defensa irregular)
- MODERADA + BALANCED (el más común)
- ALTA + BALANCED (diferencia clara)

**DEF_ATK (4 específicas — mirror de ATK_DEF con A/B invertidos):**
- BAJA + BALANCED
- ALTA + BOTH_HIGH
- MODERADA + BALANCED
- EXTREMA + MIXED_EXTREME

**DEF_DEF (4 específicas):**
- BAJA + BOTH_HIGH (duelo táctico épico)
- BAJA + BOTH_LOW (desorientación)
- ALTA + BALANCED (uno reposiciona con ventaja clara)
- MODERADA + BALANCED (reposicionamiento normal)

**INT_INT (4 específicas):**
- BAJA + BOTH_HIGH (INT brillante de ambos, narrativa especial)
- BAJA + BOTH_LOW (caos torpe)
- ALTA + MIXED_EXTREME (uno logra su maniobra, el otro falla)
- MODERADA + BALANCED (estándar)

**ATK_INT / INT_ATK (3 específicas cada uno):**
- ALTA + BALANCED (INT expuesto / ATK expuesto)
- BAJA + BALANCED
- EXTREMA + MIXED_EXTREME (consecuencias extremas)

**DEF_INT / INT_DEF (3 específicas cada uno):**
- MODERADA + BALANCED
- ALTA + BOTH_HIGH (INT brillante vs defensa)
- BAJA + BALANCED

---

## 10. INSTRUCCIONES PARA GPT

### Qué hacer
1. Generar las 10 entradas obligatorias primero (9 fallbacks de par + 1 genérico).
2. Luego generar las ~30 específicas prioritarias listadas en la sección 9.
3. Para cada entrada específica, generar entre 2 y 4 outcomes alternativos para el mismo slot (mismo pair+band+ctx), con diferentes base_weight sumando a un total relativo consistente. Incluir al menos 1 outcome con is_fatal=1 en los casos donde la diferencia es EXTREMA o MIXED_EXTREME.
4. Usar los narrative_pool_tag siguiendo la convención del punto 3.
5. Respetar la filosofía de cada par (sección 5).

### Qué NO hacer
- No generar daños altos (≥2.0) en DEF_DEF o INT_INT a menos que la banda sea ALTA+ y MIXED_EXTREME.
- No usar `DESMEMBRADO` como efecto en la matrix (se activa solo por state_outcome_weights, no directamente).
- No inventar effect codes fuera de la lista del punto 3.
- No poner `is_fatal=1` en pares DEF_DEF, DEF_INT, INT_DEF (esos no son pares de cierre).
- No asignar `FATIGA` como efecto: se activa automáticamente por ATK spam count, no por la matrix.

### Formato de entrega
Entregar el archivo CSV completo con encabezado, listo para importar. El archivo se llamará `outcome_matrix_seed.csv` y se dejará en la raíz del proyecto.

### Orden sugerido de generación
1. Fallbacks de par (10 filas) → probablemente 2-3 outcomes cada uno = ~25 filas
2. ATK_ATK específicas → ~15 filas
3. ATK_DEF específicas → ~18 filas
4. DEF_ATK específicas → ~12 filas
5. DEF_DEF específicas → ~12 filas
6. ATK_INT / INT_ATK → ~18 filas
7. DEF_INT / INT_DEF → ~18 filas
8. INT_INT específicas → ~12 filas

Total estimado: **~130 filas** (múltiples outcomes por slot, fallbacks incluidos). Esto cubre MVP con margen, sin completar las 252 combinaciones específicas completas.

---

## 11. CONTEXTO ADICIONAL PARA GPT

### El engine selecciona así
```python
# Pseudocódigo del engine
candidates = query(pair, band, context)  # puede tener múltiples filas
if not candidates:
    candidates = query(pair, band, DEFAULT)
if not candidates:
    candidates = query(pair, DEFAULT, DEFAULT)
if not candidates:
    candidates = query(GENERIC, DEFAULT, DEFAULT)

# Aplicar multiplicadores de estado activos
for candidate in candidates:
    if candidate.effect_A in active_states or candidate.effect_B in active_states:
        candidate.base_weight *= state_outcome_weights[state][candidate.outcome_code]

# Selección ponderada
outcome = weighted_random(candidates)
```

### Los estados amplifican outcomes compatibles
Cuando `CAIDO` está activo en el receptor, `state_outcome_weights` multiplica el peso de outcomes fatales automáticamente. Eso ya está en otra tabla. La `outcome_matrix` define los pesos base; el estado los amplifica.

### La narrativa es mecánica
El `narrative_pool_tag` no es solo estético. El engine busca en `narrative_templates` por ese tag, y los templates pueden incluir activaciones adicionales de estado. Un template "el golpe lo derriba contra la pared — *crepita el vidrio*" puede activar `VIDRIO_ROTO` como efecto de entorno aunque no esté en `effect_A/B` de la matrix.

### Referencia cruzada con GDD
El GDD completo está en `GDD.md` en la raíz del proyecto. La sección 14 tiene ejemplos parciales de la matrix. La sección 9 tiene la tabla de verdad de estados completa.

---

*Este documento fue generado como spec para llenado paralelo en: 2026-04-08*
*Engine: Python + FastAPI + SQLite | Proyecto: Combatrol*
