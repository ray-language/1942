# 1942

El clásico matamarcianos vertical de Capcom, de terminal a 30 fps, escrito en
[raylang](https://github.com/ray-language/raylang). Tu caza sobre el Pacífico,
las oleadas de Zeros que bajan en picado, y el icónico **tonel** (el
*loop-the-loop*): un giro que te vuelve invencible un instante para colarte
entre las balas. El avión **dispara solo** hacia arriba; las flechas lo vuelan;
el tonel es el único especial — como en el arcade.

```text
$ 1942              # ← → ↑ ↓ volar · espacio tonel · p pausa · r reinicia · a aspecto · q salir
$ 1942 --seed       # oleadas deterministas (semilla fija)
$ 1942 --no-music   # sin sonido (sin dispositivo de audio, calla solo)
$ 1942 --bench      # coste de frame + jitter de sleep
```

**Música reactiva estilo WSG**, sintetizada en vivo y escrita directo al
dispositivo con `std/audio` (el patrón que estrenó rallyx): 4 voces de
wavetable + ruido LFSR (`src/wsg.ray`, puro y determinista — la partitura se
testea byte a byte), mezcladas a s16le 22050 Hz por una fibra (`src/music.ray`)
con un adelanto de reloj de pared de ~30 ms. El juego le manda eventos por
canal: **chirrido** del cañón en cada ráfaga, **estallido** de ruido al derribar
un enemigo, **barrido** de choque al perder una vida, **whoosh** ascendente en
el tonel, **fanfarria** al subir de fase y la **despedida** en el game over —
todo sobre el **drone del motor**. Con `p` la banda entera **calla** y retoma al
seguir. La melodía es un homenaje a la marcha del arcade (la original es de
Capcom y no se transcribe).

## Las reglas

- **Auto-fuego**: el caza dispara una ráfaga hacia arriba a cadencia fija; tú
  solo pilotas y esquivas. Las balas suben `BULLET_SPEED` celdas por tick, en
  subpasos, así que **nunca atraviesan** a un enemigo sin impactarlo (hay test).
- **El tonel** (`espacio`): si te quedan cargas, el avión gira sobre sí mismo y
  es **intocable** mientras dura (`ROLL_TICKS`). Llevas `ROLL_MAX`; perder una
  vida las recarga y cada nueva fase te da una más.
- **Mejora de arma** (`◇`): de vez en cuando cae un power-up; **vuela por
  encima** para subir el nivel del cañón — de disparo simple a **doble** y
  **triple** (`POW_MAX`). Con el cañón al máximo, cada power-up te da una **vida
  extra** (hasta `LIVES_MAX`); si también vas lleno de vidas, vale `POW_BONUS`
  puntos. **Perder una vida te devuelve al nivel 1**, así que cuidar el avión
  también cuida tu potencia de fuego.
- **Al morir** el mundo se **congela** un instante y estalla una **explosión**
  en el sitio (`DEATH_TICKS`) antes de reaparecer — o del game over si no te
  quedan vidas.
- **Formato de pantalla** (`a`): por defecto el campo es **vertical** (retrato,
  como el arcade original); `a` alterna a un campo **ancho** sin perder la
  partida. Al arrancar se elige el que quepa según la altura del terminal.
- **Enemigos** con tres patrones: el **Zero** que baja recto (`+100`), la
  pareja que **serpentea** rebotando en los bordes (`+200`), y el **líder rojo**
  que te persigue, aguanta 3 impactos y **dispara balas dirigidas** (`+1000`).
- **Fases**: cada `KILLS_PER_STAGE` derribos subes de fase — más enemigos, más
  rojos, spawns más rápidos — y cada 3 fases ganas una vida (hasta 5). Al subir
  parpadea un **banner "STAGE n"** y el **mar cambia de tema** (día del Pacífico
  → atardecer → noche, y vuelta).
- **Formaciones**: además del goteo aleatorio, cada `WAVE_CD` cae una **oleada
  coreografiada** — una línea que baja, una **cuña en V**, o una **columna que
  serpentea**.
- **Jefes**: cada `BOSS_STAGE` fases aparece un **portaaviones** que barre por
  arriba; aguanta mucho (barra de vida en el HUD), su casco y recompensa
  (`BOSS_POINTS`) **crecen** con la fase, y al caer suelta un power-up seguro.
  **Pelea en tres fases que escalan** según el casco que le queda — reactor
  cian → ámbar → magenta: primero un **abanico dirigido**, luego una **cortina
  de cinco balas** que se abre, y en su último tercio un **barrido a bocajarro**
  cada vez más rápido. Y **cierra la fase**: mientras el jefe viva la fase **no
  avanza** por más enemigos que derribes — hay que **derribarlo** para pasar.
- **Impacto**: chocar con un enemigo, el jefe o comer una bala (sin estar en
  tonel ni reapareciendo) cuesta una vida y te reaparece con invencibilidad
  breve. Sin vidas, game over.

## Cómo está hecho

- **Lógica pura y sin reloj** (`src/shmup.ray`): avión, balas, enemigos y sus
  patrones, colisiones con subpasos, tonel, fases y puntuación. Determinista con
  `random.seed` — los tests la ejercitan sin terminal ni tiempo.
- **Dos relojes en un bucle** (`src/app.ray`): el frame (33 ms, repinta si algo
  cambió) y el tick del mundo (`TICK_MS`); el avión vuela en su **propio reloj de
  movimiento** (`MOVE_MS`), desacoplado del auto-repeat del teclado, para que
  cambiar de dirección sea fluido (sin el parón del *typematic delay*). En
  terminales que hablan el **protocolo de teclado kitty** se usan eventos reales
  de pulsar/soltar (el avión frena al instante); en el resto, el rumbo se
  mantiene vivo `HOLD_MS` tras la última tecla. `io.read_timeout` hasta el frame
  es la única espera — la disciplina de raygame apuntada al cielo.
- **Render** (`src/screen.ray`): una rejilla de glifos (mar que scrollea →
  enemigos → balas → fuego enemigo → avión encima) volcada a líneas fijas, con
  **diff por línea** (`ESC[n;1H` + `ESC[2K`) que solo repinta lo que cambió.
  **Aviones direccionales** (triángulos rellenos): tu caza `▲▲` verde, los Zeros
  `▼▼`, el líder rojo `◣◢`; el tonel cicla cuatro actitudes para verse girar. El
  mar es **océano con parallax**: dos capas de olas/espuma que scrollean rápido e
  islas verdes moteadas que derivan más lento. Panel con HUD coloreado y banner
  de **PAUSA**.

## `--bench` (Apple Silicon, VM)

| Métrica | VM |
|---|---|
| Frame completo (lógica + layout + diff), 1000 frames | ~260 µs/frame |
| `sleep(33)` × 60 — media / peor | 33 ms / 35 ms |

El render jamás es el cuello del presupuesto de 33 ms, y el bucle planifica por
instante absoluto (`next_frame += 33`), el patrón sin deriva del MANUAL de
raylang.

## Estado actual

| Capacidad | Estado |
|-----------|--------|
| Shooter vertical: auto-fuego, 3 tipos de enemigo, balas dirigidas | ✅ |
| Tonel (loop-the-loop) con invencibilidad y cargas limitadas | ✅ |
| Power-ups de arma (disparo simple → doble → triple, vidas extra) | ✅ |
| Fases que escalan, vidas extra, high score persistente | ✅ |
| Banner de fase + temas de mar (día → atardecer → noche) | ✅ |
| Formaciones de enemigos (línea, cuña en V, columna que serpentea) | ✅ |
| Jefes cada 3 fases: 3 patrones que escalan + gate de fase + barra de vida | ✅ |
| Muerte con hit-stop + explosión; aspecto retrato/ancho conmutable | ✅ |
| 30 fps con input sin bloqueo + diff mínimo; diagonales (kitty) | ✅ |
| Música reactiva WSG sobre `std/audio` (8 eventos + drone) | ✅ |
| Pausa, reinicio, `--bench`, `--seed`, `--no-music` | ✅ |
| Tests (reglas puras + shape del frame + synth byte a byte) | ✅ 32 |
| Sprites PNG (protocolo gráfico de terminal) | 📋 v2 |

## Desarrollo

```sh
ray test
ray run src/main.ray --bench
ray build --native src/main.ray -o 1942 --release
```

Estructura: `src/main.ray` · `shmup.ray` (reglas puras) · `screen.ray`
(frame + diff) · `app.ray` (bucle + bench + sync de audio) · `wsg.ray` (synth
puro) · `music.ray` (fibra de audio). Los tests de synth corren con
`RAY_AUDIO_SINK=null` para CI.

## Licencia

[Apache License 2.0](LICENSE) — la melodía es un homenaje a la marcha del
arcade; la original es de Capcom y no se transcribe ni se distribuye.
