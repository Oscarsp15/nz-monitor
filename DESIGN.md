# DESIGN.md — sistema de diseño de nz-monitor

> Guía visual obligatoria. Si un componente nuevo no respeta esto, se ajusta o se justifica aquí.
> Objetivo: que se sienta como un **instrumento de ingeniería serio**, no como un SaaS genérico
> hecho por IA.

---

## 1. Concepto: "instrumento de sala de control"

nz-monitor es ddenso en datos, técnico, de uso interno para DBAs. No es marketing. La estética es
la de un **panel de instrumentación**: graphite oscuro, datos en monoespaciada, líneas finas (hairlines),
**el color solo aparece cuando significa algo** (severidad de skew, estado de conexión).

**Personalidad:** preciso · denso · silencioso · técnico. Confía en el usuario experto.
**Anti-personalidad:** nada "amigable-corporativo", nada de degradados morados, nada de tarjetas
flotantes redondeadas con sombras suaves por todos lados.

### Guiño contextual (lo que lo hace propio)
Tipografía **IBM Plex** — IBM fabrica Netezza. Es una decisión con raíz en el dominio, no un default.

---

## 2. Tipografía

| Uso | Fuente | Por qué |
|---|---|---|
| **Datos, números, tablas, código** (la estrella) | **IBM Plex Mono** | tabular, alineación perfecta de cifras; carácter técnico |
| **UI, texto, botones** | **IBM Plex Sans** | legible, neutra pero con personalidad (no es Inter/Roboto) |
| **Etiquetas densas, encabezados de tabla** | **IBM Plex Sans Condensed** | mete más info por pixel sin ruido |

```css
/* @fontsource/ibm-plex-mono, /ibm-plex-sans, /ibm-plex-sans-condensed
   o Google Fonts: IBM+Plex+Mono, IBM+Plex+Sans, IBM+Plex+Sans+Condensed */
--font-data:  "IBM Plex Mono", ui-monospace, SFMono-Regular, monospace;
--font-ui:    "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
--font-dense: "IBM Plex Sans Condensed", var(--font-ui);
```

**Reglas:**
- Toda **cifra** va en `--font-data`, `font-variant-numeric: tabular-nums`, alineada a la **derecha**.
- Encabezados de tabla en `--font-dense`, `text-transform: uppercase`, `letter-spacing: .04em`, tamaño chico.
- **Prohibido**: Inter, Roboto, Arial, Space Grotesk, fuentes del sistema como look principal.
- Escala (rem): 0.6875 (11 micro) · 0.75 (12 label) · 0.8125 (13 body) · 0.875 (14) · 1.125 (18) · 1.75 (28 KPI) · 2.25 (36 KPI grande).
- Pesos: 400 body, 500 medio, 600 títulos/cifras destacadas. Nada de 700+ salvo un dato crítico.

---

## 3. Color — "el color solo significa"

La UI es **casi monocroma** (graphite). La saturación se **reserva** para estado y severidad.
Eso es lo que la hace ver de ingeniería y no de IA.

```css
/* Lienzo / superficies (graphite frío) */
--bg-0: #0A0C10;   /* fondo app */
--bg-1: #0F131A;   /* panel */
--bg-2: #151A23;   /* panel elevado / hover */
--line: #1F2630;   /* hairline (bordes 1px) */
--line-strong: #2B3340;

/* Tinta / texto */
--ink-0: #E7EAF0;  /* principal */
--ink-1: #9BA6B4;  /* secundario */
--ink-2: #5E6878;  /* terciario / deshabilitado */

/* SEMÁNTICO (única fuente de saturación) */
--ok:    #3FB950;  /* sano / conectado */
--warn:  #D8A23A;  /* atención */
--crit:  #E5484D;  /* crítico */
--info:  #5BA2C9;  /* informativo neutro (no es azul SaaS genérico) */

/* Acento de marca / "en vivo" — fósforo, usado MUY poco */
--live:  #36E0C5;  /* logo, foco, pulso de "modo en vivo", links activos */
```

**Reglas de color (no negociables):**
- Fondo, paneles, texto = solo grises de la rampa graphite.
- Verde/ámbar/rojo = **exclusivamente** estado y severidad de skew. Nunca decorativo.
- `--live` (teal fósforo) solo en: marca, anillo de foco, indicador de tiempo real, enlace activo.
- **Cero degradados** salvo un sutil top-highlight en paneles (1px). **Nada de morado.** Nada de glassmorphism.

---

## 4. Espaciado, bordes, densidad

Herramienta **densa**: rejilla base de **4px**. Preferir hairlines a sombras.

```css
--s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px;
--radius: 6px;        /* sutil; NADA de 16-24px "blandito" */
--radius-pill: 999px;
--border: 1px solid var(--line);
--shadow: none;       /* por defecto sin sombra; separar con hairlines */
--shadow-pop: 0 8px 24px rgba(0,0,0,.45);  /* solo menús/popover */
```
- Filas de tabla compactas: `padding: 6px 10px`. Sin zebra; separar con hairline inferior.
- Densidad de datos alta (estilo Tufte): maximizar data-ink, minimizar cromo.

---

## 5. Componentes

### KPI / "instrumento"
- Panel `--bg-1`, borde hairline, `--radius`, top-highlight 1px (`box-shadow: inset 0 1px 0 #ffffff0a`).
- Estructura: **label** (Condensed, uppercase, `--ink-2`) → **valor** (Plex Mono, 28–36, `--ink-0`) → **unidad/sublínea** (`--ink-2`).
- Si el KPI tiene estado, una barra/punto semántico de 2px; nada de iconos grandes de colores.

### Tabla de datos (el corazón)
- Encabezado: Condensed uppercase, `--ink-1`, hairline inferior `--line-strong`, sticky.
- Cifras a la derecha en Plex Mono tabular. Texto a la izquierda.
- Hover de fila: fondo `--bg-2`. Sin bordes verticales.
- **Flash de cambio**: cuando un valor cambia (modo en vivo), animar el fondo de la celda 600ms
  (verde si bajó/mejoró, rojo si subió/empeoró) → feedback de tiempo real real.

### Pill de estado
- `--radius-pill`, 11px, Plex Mono. Punto de 6px + texto. Color = semántico.
- `conectado` (ok), `degradado` (warn), `caído` (crit). Fondo = color a 12% alpha, texto = color.

### Badge de skew (severidad)
- No solo número: número Plex Mono + **mini-barra** de 3–4 segmentos que se llena según severidad.
- Umbrales: `< 8` neutro (`--ink-1`), `8–25` `--warn`, `> 25` `--crit`. La fila entera puede teñir
  su borde izquierdo 2px con el color de severidad.

### Sello de frescura
- `--font-data`, `--ink-2`, 11px: `actualizado hace 12s`. Junto a un punto que **pulsa en `--live`**
  cuando el modo en vivo está activo.

---

## 6. Movimiento (escaso y con propósito)

- **Carga**: entrada escalonada de KPIs y filas (`animation-delay` 30–50ms por elemento), sutil.
- **Tiempo real**: pulso del punto `--live` (1.6s) y el *flash* de celda al cambiar un dato.
- **Foco**: anillo `--live` 2px. Transiciones 120–160ms `ease-out`. **Nada** de bounce/spring lúdico.
- Respetar `prefers-reduced-motion`.

---

## 9. Adaptativo: móvil, tablet y escritorio

La densidad de §4 es una virtud en un monitor de 27" y un problema en un móvil. Esta sección manda
sobre §4 cuando la pantalla es pequeña: **la densidad se negocia, la legibilidad y el pulgar no**.

### 9.1 Puntos de corte (los de Tailwind que ya usa el proyecto)

| Rango | Dispositivo típico | Disposición |
|---|---|---|
| `< 640px` | móvil vertical | una columna · navegación inferior · tabla en fichas |
| `640–1023px` | móvil apaisado y tablet vertical | dos columnas de KPI · tabla con columnas prioritarias |
| `≥ 1024px` (`lg`) | tablet apaisada y escritorio | barra lateral fija · tabla completa |

El salto a "escritorio" lo decide el **ancho**, no el tipo de aparato: una tablet en horizontal con
1024px o más se sirve como escritorio, sin caso especial.

### 9.2 El pulgar manda (táctil)

- **Área tocable mínima 44×44px** para todo lo accionable (botones, filas clicables, casillas,
  paginación), con al menos 8px de separación entre dos objetivos. La fila de tabla puede seguir
  midiendo 28px de alto *visual* en escritorio, pero en táctil crece a 44px.
- **Nada vive solo en `hover`.** Si un dato o una acción solo aparece al pasar el ratón, en táctil
  no existe: necesita equivalente visible o accesible al tocar.
- Las acciones que se usan de pie frente al servidor —**"Actualizar ahora"** y **"Modo en vivo"**—
  quedan alcanzables con el pulgar (mitad inferior o barra fija), no solo en la esquina superior.
- Destructivo (borrar usuario, resetear contraseña) **nunca** al alcance accidental del pulgar sin
  confirmación explícita.

### 9.3 Tablas densas en pantallas pequeñas

La tabla es el corazón (§5) y es donde más duele. Por orden de preferencia:

1. **`≥ 1024px`**: tabla completa, como está.
2. **`640–1023px`**: se ocultan las columnas de menor prioridad, no se encoge la tipografía.
   Prioridad de columnas en Tablas: `TABLA > ESPACIO > SKEW > BASE > ESQUEMA > OWNER > DISTRIBUCIÓN`.
3. **`< 640px`**: **ficha por fila**, no scroll horizontal. Cada ficha: nombre de la tabla en
   `--font-data` a ancho completo, y debajo las dos o tres cifras que importan con su etiqueta
   Condensed. El scroll horizontal en una tabla de 7 columnas es inusable con una mano.

El **orden** (clic en encabezado) se mantiene en móvil como un selector explícito de "ordenar por",
porque sin encabezados no hay dónde pulsar.

### 9.4 Tipografía y espacio por pantalla

- La escala micro de 11px (§2) es **solo para `≥ 1024px`**. En móvil el mínimo es **12px**, y los
  datos principales no bajan de 14px.
- Márgenes laterales: 16px en móvil, 24px en tablet, 32px en escritorio.
- Los KPI pasan de fila de 4 a rejilla de 2×2 en tablet y a columna en móvil, **sin** encoger la
  cifra: el número es el dato, se sacrifica el espacio en blanco antes que el tamaño.

### 9.5 Ventanas, notch y PWA

- Respetar el área segura (`env(safe-area-inset-*)`) arriba y abajo: la barra inferior de navegación
  sin eso queda bajo la barra de gestos del teléfono.
- Instalable (manifest + iconos) y utilizable en modo `standalone`, donde no hay barra de direcciones
  ni botón "atrás" del navegador: **toda pantalla necesita su propia vuelta atrás**.
- El color del `html` acompaña al tema para que el rebote del scroll no muestre una franja blanca.

### 9.6 Cómo se comprueba (obligatorio antes de dar por buena una pantalla)

Se verifica en **seis combinaciones**, en tema claro y oscuro:

| Viewport | Representa |
|---|---|
| 390 × 844 | móvil vertical (iPhone 14 / Pixel) |
| 820 × 1180 | tablet vertical (iPad Air) |
| 1280 × 800 | portátil / tablet apaisada |
| 1920 × 1080 | escritorio |

Y en todas: sin scroll horizontal, sin texto truncado sin remedio, sin objetivo táctil por debajo de
44px, y la navegación inferior sin solaparse con el área segura. No basta con encoger la ventana del
navegador: hay que mirarlo con emulación táctil (o en un aparato real) porque `hover` engaña.

---

## 7. Para que NO parezca hecho por IA (checklist)

❌ Evitar | ✅ Hacer
---|---
Degradados morados / azul→violeta | Graphite monocromo + color semántico
Inter / Roboto / system-ui como look | IBM Plex (Mono/Sans/Condensed)
Tarjetas muy redondeadas con sombra blanda | Hairlines, radio 6px, sin sombra
Glassmorphism / blur por todos lados | Superficies sólidas, capas por valor de gris
Emojis como iconos de UI | Iconografía lineal fina (1.5px) o ninguna
Hero centrado con texto gigante | Layout denso, alineado a rejilla, info-first
Color decorativo | Color = significado (estado/severidad)
Números en fuente proporcional | Plex Mono tabular, alineados a la derecha
Todo centrado y espacioso | Densidad controlada, jerarquía por tipografía

---

## 8. Tokens listos para usar (resumen copiable)

```css
:root{
  --font-data:"IBM Plex Mono",ui-monospace,monospace;
  --font-ui:"IBM Plex Sans",system-ui,sans-serif;
  --font-dense:"IBM Plex Sans Condensed",var(--font-ui);
  --bg-0:#0A0C10; --bg-1:#0F131A; --bg-2:#151A23;
  --line:#1F2630; --line-strong:#2B3340;
  --ink-0:#E7EAF0; --ink-1:#9BA6B4; --ink-2:#5E6878;
  --ok:#3FB950; --warn:#D8A23A; --crit:#E5484D; --info:#5BA2C9; --live:#36E0C5;
  --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;
  --radius:6px; --radius-pill:999px;
}
```
