# TP2 – Scripts de medición

Scripts para generar las excitaciones, reproducirlas/grabarlas y dejar las grabaciones listas para el notebook (`TP2.ipynb`, que alinea y procesa; no se explica acá).

Todo trabaja a **fs = 48 kHz, mono, float32, 10 s por excitación**.

## Instalación

Además de lo que ya está en `../requirements.txt`, los scripts necesitan:

```bash
pip install sounddevice soundfile
```

(`pandas` lo usa el notebook. Para leer grabaciones `.m4a` del celular hace falta también `ffmpeg`, ver más abajo.)

## Estructura de carpetas

```
tp2/
├── generar_excitaciones.py   # crea las señales de excitación
├── reproducir.py             # reproduce por el parlante (para grabar con el celular)
├── medir.py                  # reproduce y graba a la vez con la PC
├── importar.py               # convierte grabaciones del celular al formato del notebook
├── fuentes/                  # voz.wav y musica.wav propios (los pone el usuario)
├── excitaciones/             # salida de generar_excitaciones.py
├── celular/                  # grabaciones originales del celular (las pone el usuario)
└── grabaciones/              # grabaciones finales (salida de medir.py o importar.py)
```

Las seis señales tienen siempre estos nombres: `voz`, `musica`, `rectangular`, `barrido_lineal`, `barrido_exp`, `ruido`. Los nombres de archivo tienen que coincidir exactamente, porque así los busca el notebook.

## Flujo de trabajo

Hay dos formas de tomar las mediciones. En ambas el primer paso es el mismo.

```
generar_excitaciones.py
        │
        ├── A) PC graba con su micrófono:   medir.py ──────────────────────┐
        │                                                                  ▼
        └── B) Celular graba:  reproducir.py → (celular) → importar.py → grabaciones/ → notebook
```

La consigna recomienda reproducir y grabar con **dispositivos distintos** (opción B). La opción A es más cómoda pero PC-parlante y PC-micrófono comparten reloj de muestreo solo si son de la misma placa; en general son placas distintas y también hay que alinear.

---

## 1. `generar_excitaciones.py`

Genera las excitaciones de 10 s a 48 kHz y las guarda en `excitaciones/*.wav`.

```bash
python generar_excitaciones.py
python generar_excitaciones.py --voz-inicio 12.5 --musica-inicio 30
```

| Señal | Cómo se genera |
|---|---|
| `rectangular` | onda cuadrada de 100 Hz: `sign(sin(2π·100·t))` |
| `barrido_lineal` | $u_l(t)=\sin(2\pi f_0 t + 2\pi k t^2/2)$, con $k=(f_1-f_0)/T$, $f_0=20$ Hz, $f_1=20$ kHz |
| `barrido_exp` | $u_e(t)=\sin\!\big(2\pi f_0 (k^t-1)/\ln k\big)$, con $k=(f_1/f_0)^{1/T}$ |
| `ruido` | ruido blanco gaussiano de media cero (semilla fija, recortado a ±4σ) |
| `voz`, `musica` | se **toman de un archivo tuyo** en `fuentes/` (ver abajo) |

Todas se normalizan a un **pico de 0.5** (constante `PICO` en el script) para que ninguna sature al reproducirla. Se guardan en `FLOAT` (32 bits).

### Voz y música
No se sintetizan. Copiá tus archivos a `fuentes/` con el nombre `voz.*` y `musica.*` (`wav`, `flac`, `mp3`, `ogg`...). El script:

1. los pasa a mono (promedio de canales),
2. los remuestrea a 48 kHz si hace falta,
3. recorta **10 s a partir de `--voz-inicio` / `--musica-inicio`** (en segundos).

Si falta el archivo, avisa y omite esa señal; si no tiene 10 s desde el punto de inicio, da error. Elegir el fragmento es parte del TP (punto 1 a/b): conviene voz continua y música con energía en banda ancha, sin silencios.

---

## 2. Opción B (celular): `reproducir.py` + `importar.py`

### 2.1 `reproducir.py`

Reproduce por el parlante de la PC, **sin grabar**. A cada excitación le agrega **3 s de silencio antes y después** (`--pad`), para que sea fácil arrancar y detener la grabación del celular sin recortar la señal.

```bash
python reproducir.py --listar                  # ver dispositivos de audio
python reproducir.py barrido_lineal --out 4    # una señal
python reproducir.py --todas --out 4           # las seis, una tras otra
python reproducir.py ruido --ganancia 0.8      # escalar la amplitud
```

Para cada señal el script muestra:

```
[barrido_lineal] 1) Empezá a grabar con el celular  2) Apretá Enter aquí ...
```

Secuencia: iniciás la grabación en el celular → apretás Enter en la PC → esperás que termine (10 s + 6 s de silencio) → detenés la grabación y la guardás con el nombre de la señal.

| Opción | Efecto |
|---|---|
| `--out N` | índice del parlante (ver `--listar`). Si se omite usa el dispositivo por defecto |
| `--ganancia G` | multiplica la señal por `G` (se recorta a ±1) |
| `--pad S` | segundos de silencio antes/después (default 3) |
| `--todas` | reproduce las seis |
| `--listar` | lista los dispositivos y sale |

En dispositivos WASAPI se activa la conversión automática de frecuencia de muestreo, por si el parlante trabaja a otra frecuencia.

### 2.2 Cómo tomar las grabaciones con el celular

- **Formato:** grabá sin compresión (WAV/PCM), a 48 kHz si la app lo permite. Evitá WhatsApp y cualquier grabadora de voz con compresión agresiva: el códec altera el contenido en frecuencia, que es justo lo que se mide. Si el celular solo guarda `.m4a`, sirve pero degrada un poco.
- Desactivá cancelación de ruido y control automático de ganancia.
- Modo avión y silencio para que no entren notificaciones.
- Celular **fijo** a 1–2 m del parlante, sin tocarlo durante la medición. Sala en silencio y sin mover nada entre una medición y otra.
- **Nivel:** ajustá el volumen una sola vez (probá con `ruido`) hasta que el pico grabado esté entre ~0.3 y 0.8 sin saturar. Después no lo cambies.
- Guardá cada archivo con el nombre de la señal: `voz`, `musica`, `rectangular`, `barrido_lineal`, `barrido_exp`, `ruido` (opcional: `ambiente`, 5 s de silencio para medir el ruido de fondo).

### 2.3 `importar.py`

Convierte lo que grabó el celular al formato que espera el notebook. Busca archivos en `celular/` cuyo nombre sea el de una señal (cualquier extensión) y escribe `grabaciones/<señal>.wav`.

```bash
python importar.py                                      # importa todo lo que haya en celular/
python importar.py ruta/al/archivo.m4a --como ruido     # un archivo suelto
```

Qué hace con cada archivo:
1. **Lee** el archivo. `wav`, `flac`, `mp3`, `ogg` y `caf` se leen directo; `m4a`, `aac`, `3gp` y `opus` se decodifican con **ffmpeg**, que tiene que estar en el `PATH` (o instalarse con `pip install imageio-ffmpeg`).
2. Pasa a **mono** (promedio de canales).
3. **Remuestrea a 48 kHz** si el celular grabó a otra frecuencia (por ejemplo 44.1 kHz).
4. Guarda en `grabaciones/<señal>.wav` como float32.
5. Imprime frecuencia original, canales, duración y **pico**, y avisa si la grabación está **saturada** (pico > 0.98) o **muy baja** (pico < 0.02); en esos casos hay que repetir la medición.

**No recorta ni alinea.** La sincronización (retardo, deriva de reloj) la hace el notebook; por eso la grabación conserva el silencio del principio y del final.

---

## 3. Opción A (micrófono de la PC): `medir.py`

Reproduce por el parlante y graba por el micrófono **al mismo tiempo** desde la misma PC. Guarda directamente en `grabaciones/`. Agrega 1 s de silencio (`--pad`) antes y después.

```bash
python medir.py --listar                         # dispositivos disponibles
python medir.py --calibrar --in 1 --out 4        # chequear niveles, no guarda nada
python medir.py --ruido --in 1 --out 4           # 5 s de ruido ambiente -> grabaciones/ambiente.wav
python medir.py --todas --in 1 --out 4           # las seis excitaciones
python medir.py voz musica --in 1 --out 4        # solo algunas
python medir.py --todas --ganancia 0.8
```

| Opción | Efecto |
|---|---|
| `--in N` / `--out N` | índices del micrófono y del parlante (ver `--listar`). Usar dispositivos de la **misma API** (todos MME o todos WASAPI) |
| `--ganancia G` | factor sobre la excitación (default 1) |
| `--pad S` | segundos de silencio antes/después (default 1) |
| `--espera S` | cuenta regresiva antes de cada medición (default 3 s) |
| `--calibrar` | reproduce 3 s de ruido a bajo nivel y muestra el pico grabado |
| `--ruido` | graba 5 s de silencio para caracterizar el ruido de fondo |
| `--todas` | mide las seis señales |

Después de cada grabación imprime pico y nivel RMS en dBFS, con el mismo aviso de saturación / nivel bajo.

**Antes de medir:** corré `--calibrar` y ajustá `--ganancia` (o el volumen de la placa) hasta que el pico grabado de la excitación real quede entre 0.3 y 0.8.

---

## Comparación rápida

| | `medir.py` (A) | `reproducir.py` + `importar.py` (B) |
|---|---|---|
| Dispositivos | PC reproduce y graba | PC reproduce, celular graba |
| Pasos manuales | ninguno | iniciar/detener grabación, copiar archivos |
| Pad de silencio | 1 s | 3 s |
| Salida | `grabaciones/` directo | `celular/` → `grabaciones/` |
| Recomendado por la consigna | no (mismo equipo) | **sí** (dispositivos distintos) |

## Notas y problemas comunes

- **"la grabación no alcanza" en el notebook:** el celular arrancó tarde o cortó antes. Repetí esa medición dejando margen.
- **Pico saturado o muy bajo:** repetir con otro volumen. No mezclar mediciones con volúmenes distintos.
- **No lee `.m4a`:** falta ffmpeg (`pip install imageio-ffmpeg` o instalarlo en el sistema).
- **Sin audio / error de dispositivo:** correr `--listar` y pasar `--in`/`--out` explícitos; en Windows evitá mezclar APIs (MME, DirectSound, WASAPI) entre entrada y salida.
- No muevas la PC, el celular ni objetos de la habitación entre mediciones, y no cambies el volumen: la respuesta estimada tiene que corresponder a **un solo** sistema.
