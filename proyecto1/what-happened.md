# Qué pasó: primera sesión con datos del Proyecto 1 (NLMS para EEG)

> Registro de la sesión del 2026-10-18 (Pedro + Claude Code). Está pensado para que el resto del grupo, y sus LLMs, sepan qué se hizo, qué se encontró en los datos y **por qué** se terminó haciendo lo que se hizo. Todo lo que se dice acá se puede reproducir con `proyecto1/proyecto1_g4.ipynb`.

---

## 1. Punto de partida

- **Tema:** denoising de EEG. La idea es sacarle al EEG el ruido de los ojos (EOG) y de los músculos (EMG) con un cancelador adaptativo de ruido. El algoritmo principal es NLMS; LMS y VS-LMS quedan para comparar.
- **Modelo (el de la design review):**
  - lo que mide el electrodo es `y(n) = s(n) + λ₁·η_EOG(n) + λ₂·η_EMG(n)`, donde `s(n)` es el EEG limpio;
  - hay una referencia por fuente de ruido, `x₁ ≈ EOG` y `x₂ ≈ EMG`;
  - dos FIR cortos apilados, `w = [w₁; w₂]`;
  - la salida es `e(n) = y(n) − ŷ(n)`, con `ŷ = wᵀx`.
- **Dataset elegido:** OpenNeuro **ds008701** ("MET – Music-Induced Emotion EEG Dataset", v1.0.4, licencia CC0, DOI `10.18112/openneuro.ds008701.v1.0.4`).
  - 20 sujetos; cada uno escuchó 20 canciones, y cada carpeta `ses-tXX` es *una canción*, no una sesión en el tiempo.
  - Grabaciones de 130 s a 1000 Hz, con 66 canales EEG + 1 EOG y **0 canales EMG**.
- **Lo que se pidió en la sesión:**
  1. programar el NLMS y el diagrama en bloques completo, hasta obtener `e(n)`;
  2. discutir cómo estimar el EMG con `T9, T10, TP9, TP10, FT9, FT10`;
  3. ver **cómo saber si los resultados son confiables cuando no hay ground truth**.

---

## 2. Aclaraciones conceptuales que salieron en la discusión

Están acá porque son fáciles de confundir y conviene que el grupo las tenga presentes.

1. **Hay una sola señal de error.** EOG y EMG no son "dos errores": son dos *fuentes de ruido*, cada una con su referencia. Un único `e(n)` ajusta los coeficientes de todas las referencias a la vez.
2. **`e(n)` no es "EEG puro".** Es el EEG, más lo que las referencias no pueden explicar, menos el EEG que se cuele por las referencias.
3. **Por qué el filtro no borra el EEG:** solo puede armar `ŷ` a partir de las referencias. Si las referencias no tienen EEG, no puede restar EEG (principio de ortogonalidad, `6. LMS.pdf`). **Si las referencias traen EEG, sí lo resta.** Este resultó ser el problema principal con la referencia de EMG (§6).
4. **Que el MSE sea chico no quiere decir que el EEG esté limpio.** Con μ̃ grande, `J(n)` queda *por debajo* de `J_min` (Wiener), porque el filtro persigue la no estacionariedad y se come EEG. Por eso todo se evalúa contra `s` y no solo con el MSE.
5. **`J_min` no es 0.** El piso es el error de Wiener, `E{|y − w_oᵀx|²}`, y es aproximadamente la potencia del EEG, porque `e` *debe* contener a `s`.

---

## 3. Obstáculo 1: el clone de GitHub no trae las señales

- `git clone https://github.com/OpenNeuroDatasets/ds008701` solo baja **punteros de git-annex**. Los `.set` (las señales) son symlinks rotos a `.git/annex/objects/...`: la carpeta `sub-01` pesaba 804 KB, cuando cada `.set` pesa ~35 MB.
- No hay `git-annex` ni `datalad` instalados, así que se bajaron directo del bucket público de OpenNeuro y se verificó el SHA256 contra la clave del annex que está en el nombre del symlink.

```bash
cd proyecto1/datasets-presentacion-PASA/ds008701
for f in sub-01/*/eeg/*_eeg.set; do
  key=$(basename "$(readlink "$f")"); sha=${key#*--}; sha=${sha%.set}
  rm "$f" && curl -sfL -o "$f" "https://s3.amazonaws.com/openneuro.org/ds008701/$f"
  [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$sha" ] && echo "OK $f" || echo "MAL $f"
done
```

- Resultado: las 20 grabaciones de `sub-01` bajadas y verificadas (672 MB). **Para otro sujeto, cambiar `sub-01` en el loop.**
- **El dataset no está en el repo** (pesa ~690 MB y tiene su propio `.git`). Cada uno lo tiene que bajar así.

---

## 4. Lo que mostraron los datos y cómo cambió el plan

Este es el centro del registro. Antes de tocar el filtro se inspeccionaron las 20 canciones de sub-01 (§2 del notebook). Cada hallazgo forzó una decisión.

| Hallazgo | Evidencia | Decisión que provocó |
|---|---|---|
| **Los bordes de cada grabación tienen derivas de varios mV** en todos los canales (después de ~113 s y en los primeros segundos). | Series temporales: el EOG y Fp1 llegan a ±3–5 mV al final. Al principio esto inflaba el desvío del EOG a ~190 µV, cuando en el tramo bueno es ~30–60 µV, y hacía parecer que el EOG no correlacionaba con nada. | **Recortar a 10–110 s** (no 5–125 s, como decía el plan). |
| **La grabación no tiene nada arriba de ~80 Hz, y la línea es de 50 Hz y ya viene con notch.** | PSD: caída de millones de veces en ~80 Hz y un valle (no un pico) en 50 Hz. | **Submuestrear 1000 → 250 Hz** (Nyquist 125 > 80; 4 veces menos cuentas) y **no aplicar notch**. Además, **del EMG solo vemos la parte de 20–80 Hz**: el EMG real llega a cientos de Hz. |
| **No hay parpadeos típicos ni en el EEG ni en el EOG.** | No aparecen picos de 100–300 µV. En el promedio sincronizado, Fp1 se ve igual que Oz. El README dice "after preprocessing": probablemente los sacaron con ICA. | El caso de parpadeos reales **no se puede validar con este sujeto**. La parte cuantitativa del EOG **tiene que salir del experimento semi-sintético**. |
| **Sí quedan movimientos oculares horizontales.** | El EOG correlaciona hasta **+0.6 con F7 y −0.6 con F8**; los signos opuestos de cada lado son la firma del EOG horizontal. En Oz da ≈ 0. Promedio sincronizado: a F7/F8/Fp1 llega ~10 % del EOG. La mejor canción es **t17**. | En datos reales, el EOG se evalúa en **F7/F8 de t17**, con **Oz como control negativo**. |
| **Hay EMG en ráfagas solo en 4 de 20 canciones** (t04, t07, t15, t25), **a la vez de los dos lados**. | Curtosis de la envolvente > 30 Hz mucho mayor que 3 en esas canciones (≈ 3 en el resto); correlación izquierda/derecha de las envolventes hasta 1.0 (mandíbula o tragar). En t15, la envolvente en T8 sube de ~2 a ~25 y en Oz solo a ~7. | La referencia de EMG con los temporales bajos **es viable**. El EMG en datos reales se evalúa en **T8 de t15**. Para el semi-sintético, `η_EMG` se toma de esas 4 canciones. |
| **Fuera de las ráfagas, las referencias de EMG no son cero.** | ±10 µV de ruido parejo todo el tiempo: es EEG de alta frecuencia + ruido del equipo, porque T9, T10, etc. también son electrodos de EEG. | Se anticipó como riesgo, y efectivamente es el problema principal (§6). |
| **Oz casi no tiene ninguno de los dos ruidos y tiene un α claro (~10 Hz).** | PSD con bulto en α; correlación con el EOG ≈ 0; poca energía de EMG. | **Oz es el "EEG limpio" `s` del semi-sintético** y el control negativo en datos reales. |

### Cómo se armó la referencia de EMG (pregunta 2 de la sesión)
- **Dos referencias, una por lado:** izquierda = promedio de `T9, TP9, FT9`; derecha = promedio de `T10, TP10, FT10`.
  - **Por qué por lado:** los músculos (temporal, masetero) actúan localmente.
  - **Por qué promediar:** promediar tres canales baja el EEG y el ruido no correlacionados entre ellos.
- **Pasa-altos en 25 Hz:** el EMG está arriba de 20 Hz, así que el pasa-altos saca de la referencia el EEG de δ a α y el filtro no lo puede restar. **Lo que no saca es el EEG β/γ**, y por eso se cuela.
- En total quedan **3 referencias** apiladas: `[EOG, EMG izq, EMG der]`, cada una con M = 3 coeficientes (9 en total).

---

## 5. Cómo se responde "¿está bien el resultado?" sin ground truth (pregunta 3)

En datos reales nadie conoce `s(n)`, así que no se puede medir directamente qué tan cerca está `e` de `s`. Se adoptaron **dos caminos complementarios**:

- **Camino A, semi-sintético (cuantitativo).** Armamos `y = s + λ₁η_EOG + λ₂η_EMG` con:
  - `s` = un tramo de Oz;
  - `η` = ruido real de *otra* canción;
  - referencias imperfectas, `x = h∗η + ruido`, con `h₁ = [1, 0.5]`, `h₂ = [1, −0.4]` y ruido de medición 20 dB por debajo. Si `x = η` exacto, el problema es trivial.
  - Monte Carlo con 30 realizaciones (canciones y tramos al azar).

  Como conocemos `s`, se miden las métricas de la design review: `J(n)`, `J_min`, desajuste, velocidad, bias, RRMSE temporal y espectral, y correlación.
- **Camino B, datos reales (cualitativo).** Se corre el filtro sobre canales crudos y se comprueban consecuencias de "si `e` fuera `s`, entonces…":
  1. el evento ocular desaparece en el promedio sincronizado sobre `e`;
  2. la potencia de 30–80 Hz baja en las ráfagas;
  3. la de 30–80 Hz **no** cambia fuera de las ráfagas;
  4. α (8–13 Hz) no cambia;
  5. Oz casi no cambia;
  6. la potencia removida baja con la distancia a la fuente;
  7. `w(N)` de NLMS queda cerca de `w_o` de Wiener;
  8. `e` no correlaciona con las referencias. Esta es la más débil: solo prueba que el filtro convergió.

  Ninguna prueba alcanza sola: tienen que coincidir.

---

## 6. Resultados

### 6.1 El código está bien (chequeos de cordura)
- **Caso de libro** (referencias blancas, camino conocido): `w(N) ≈ w_o`. Por ejemplo, `[0.79, −0.32, 0.10, 0.49, 0.20, −0.02]` contra `[0.80, −0.30, 0.10, 0.50, 0.20, 0.00]`.
- **μ̃ = 2.5 diverge**, como se espera para μ̃ > 2.

### 6.2 El spread de autovalores manda (hallazgo importante)
- Con **referencia perfecta pero con el EOG real**, Wiener limpia casi del todo (`J_min/P_s ≈ 1`), pero NLMS no llega en 20 s (RRMSE 0.74).
- **Causa:** el EOG es muy lento, así que `EOG(n) ≈ EOG(n−1) ≈ EOG(n−2)` y la matriz `R` queda mal condicionada.
  - **Spread ≈ 300 con el EOG solo, y ≈ 14 000 al apilar EOG + EMG.**
  - Las referencias tienen potencias muy distintas. NLMS divide por la potencia *total* (que domina el EOG), así que **los coeficientes de EMG reciben pasos chiquitos y aprenden lento**.
- Esto confirma lo dicho en la presentación: **NLMS normaliza la potencia, pero no arregla el spread.**
- **Barrido de M:** `J_min` casi no baja después de M = 3, y el spread crece de ~10³ a ~10⁶. Se elige **M = 3** (como He et al. 2004).

### 6.3 Semi-sintético (M = 3, SNR_EOG = −5 dB, SNR_EMG = 0 dB, 30 realizaciones)

| μ̃ | J(∞)/J_min | desajuste | RRMSE(e,s) | CC(e,s) |
|---|---|---|---|---|
| 0.003 | 1.82 | 0.82 | 0.94 | 0.72 |
| 0.01 | 1.49 | 0.49 | 0.80 | 0.76 |
| **0.03** | **1.08** | **0.08** | **0.67** | **0.78** |
| 0.1 | 0.81 | −0.19 | 0.69 | 0.74 |
| 0.3 | 0.61 | −0.39 | 0.87 | 0.55 |
| 1.0 | 0.58 | −0.42 | 1.10 | 0.24 |

(Sin filtrar, RRMSE(y, s) = 2.01.)

- **μ̃ ≈ 0.03 es el mejor compromiso:** llega a `J_min` hacia los 11–12 s.
- **Con μ̃ ≥ 0.1, `J(∞) < J_min`**: el desajuste da negativo, pero el RRMSE sube y la correlación cae. El filtro persigue las ráfagas y se come EEG. Es el ejemplo concreto de "el MSE solo no alcanza".
- **Barrido de SNR (μ̃ = 0.03):**
  - con mucho ruido (−10 dB) mejora muchísimo: RRMSE 4.4 → 1.4;
  - con poco ruido (+10 dB) queda **apenas peor que no filtrar** (0.53 contra 0.45), porque el error propio del filtro pesa más que lo que limpia.

### 6.4 Datos reales (μ̃ = 0.03, M = 3, referencias `[EOG, EMG izq, EMG der]`)

Cambio de potencia de `e` respecto de `y`, en dB (negativo = se sacó potencia):

| | t17 F7 | t17 F8 | t17 Oz | t15 T8 | t15 F8 | t15 Oz |
|---|---|---|---|---|---|---|
| total | −3.8 | −3.9 | −0.4 | −3.8 | −3.9 | −1.0 |
| 0.5–4 Hz | −1.6 | −1.5 | −0.6 | −1.4 | −1.4 | −1.5 |
| α (8–13 Hz) | −0.05 | −0.03 | +0.08 | +0.21 | +0.33 | +0.08 |
| 30–80 Hz en ráfagas | −8.8 | −9.9 | −0.6 | **−18.6** | −18.9 | −3.2 |
| 30–80 Hz fuera de ráfagas | **−7.6** | **−9.3** | −0.5 | **−8.0** | −8.3 | −0.1 |
| ‖w(N) − w_o‖/‖w_o‖ | 0.46 | 0.46 | 0.52 | 0.49 | 0.53 | 0.60 |

**Lo que funciona ✔**
- **α intacto** en todos los casos (|cambio| < 0.4 dB).
- **El EMG de las ráfagas se va:** −18.6 dB en T8. En la PSD durante las ráfagas, 20–80 Hz baja unas 10 veces y lo de debajo de 15 Hz no cambia.
- **Oz casi no cambia en t17** (−0.4 dB).
- **La potencia removida por la referencia EOG baja con la distancia a los ojos** (~2 dB adelante, ~0 dB en la nuca), así que parece ruido ocular de verdad.
- `e` deja de correlacionar con las referencias: antes, `y` llegaba a 0.6 con el EOG; después, `e` queda < 0.1.

**Lo que no funciona ✘**
1. **El evento ocular no desaparece: queda invertido.** En el promedio sincronizado de t17, F7 pasa de +20 µV a −15 µV y F8 de −20 µV a +18 µV: el filtro **resta de más**.
   - También **crea artefactos**: en F8, a los ~70.5 s, `ŷ_EOG` mete +125 µV y `e` queda con un pico de −110 µV que no existía. Coincide con un salto brusco del EOG (−240 µV).
   - **Wiener (el mejor filtro fijo) tampoco saca bien el evento**, y su `w_o` tiene taps con signos alternados `[0.20, 0.19, −0.27]`. Eso parece una forma tipo derivada, no una simple ganancia de propagación.
   - **Interpretación:** con **un solo canal EOG**, un único `w` no puede ajustar movimientos distintos (horizontal, vertical, …), que llegan a cada electrodo por caminos diferentes. Es la limitación de "un solo canal EOG" que ya estaba en la lista de riesgos. En la literatura se usan dos referencias (VEOG y HEOG).
2. **La referencia de EMG saca alta frecuencia donde no hay músculo:** −8 dB en 30–80 Hz *fuera* de las ráfagas, en F7/F8/T8. En t17, que no tiene ráfagas, `ŷ_EMG` en F8 es ±10 µV de ruido parejo todo el tiempo. **Lo más probable es que estemos restando EEG β/γ**, que también está en los temporales.
   - La prueba espacial lo confirma: la referencia EMG derecha saca lo mismo en AF3/AF7 (a 17 cm, del otro lado) que en T8. No es una fuente localizada.
3. **Durante las "ráfagas de EMG" hay un pico fuerte en 50 Hz**, en T8 y en Oz. El EMG es de banda ancha, así que probablemente **parte de las ráfagas es interferencia de línea por movimiento de electrodos** (al apretar la mandíbula o moverse). El filtro la saca igual, pero hay que decirlo en el informe.
4. **`w(N)` de NLMS queda a ~50 % de `w_o`**, por los modos lentos (spread) y porque la relación ruido → electrodo cambia con el tiempo.

### 6.5 Conclusión de la sesión
- **El filtro funciona y está bien implementado.** En el semi-sintético limpia (RRMSE 2.0 → 0.67, CC 0.78) y cumple la teoría: el límite de μ̃, que `J(n)` llegue a `J_min` y el efecto del spread.
- **En los datos reales de sub-01 no podemos afirmar todavía que `e(n)` sea EEG limpio.** El EOG se cancela a medias y a veces se pasa, y la referencia de EMG también resta EEG de alta frecuencia.
- Estos "fracasos" **son resultados**: explican por qué el diseño de referencias importa tanto como el algoritmo, y entran en el informe.

---

## 7. Decisiones pendientes para discutir en el grupo

1. **μ̃:** quedó `MU_ELEGIDO = 0.03` (sale del barrido de §4.1 del notebook). ¿Lo mantenemos?
2. **Referencia de EMG:** ¿cómo evitamos que reste EEG β/γ? Ideas:
   - un pasa-altos más alto;
   - que el filtro de EMG solo aprenda durante las ráfagas (μ̃ variable según la envolvente);
   - usar EMG sintético (estrategia B de `context.md` §8.4) para el semi-sintético.
3. **Spread al apilar:** probar **normalizar cada referencia por separado** (un NLMS "por bloque"). Es una variante concreta que ataca el problema medido. ¿Y comparar con LMS y VS-LMS, como se prometió en la presentación?
4. **EOG real:** buscar entre los otros sujetos alguno que **sí tenga parpadeos** (no todos tienen por qué estar igual de limpios). Si ninguno tiene, el EOG real queda solo como validación cualitativa y lo declaramos.
5. **Otros sujetos:** repetir la inspección (§2 del notebook) en otros sujetos para ver si se repite lo de sub-01 (datos preprocesados, EMG en pocas canciones). Hay que bajar sus `.set` con el loop de §3.

---

## 8. Cómo reproducir

1. **Entorno** (en la raíz del repo):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt   # se agregaron mne y pymatreader
   ```
   - Si renombran o mueven la carpeta del repo, **el venv se rompe** (guarda rutas absolutas). Hay que borrarlo y volver a crearlo.
   - En VS Code: abrir la carpeta raíz del repo, y en "Select Kernel" elegir `.venv`. El diálogo de archivos oculta las carpetas con punto: `Ctrl+H` las muestra, o se puede pegar la ruta a `.venv/bin/python`.
2. **Datos:** clonar ds008701 dentro de `proyecto1/datasets-presentacion-PASA/` y bajar los `.set` con el loop de §3.
3. **Notebook:** abrir `proyecto1/proyecto1_g4.ipynb` y hacer "Run All" (tarda ~1 min). Arranca con una explicación larga del problema, y cada gráfico tiene abajo un "Qué mirar" que explica por qué se dibujó y qué conclusión sale.

### Estructura del notebook
| § | Qué hace |
|---|---|
| 1 | Carga los `.set` con MNE, pasa a µV, recorta a 10–110 s y submuestrea a 250 Hz |
| 2 | Inspección: correlación EOG–EEG, eventos del EOG, curtosis del EMG, PSD; arma las referencias de EMG |
| 3 | `nlms()` (fórmula de la teórica línea por línea, con comentario por línea), `wiener()`, métricas |
| 4 | Semi-sintético: chequeos de cordura, barrido de μ̃, M y SNR |
| 5 | Datos reales: t17 (EOG) y t15 (EMG) |
| 6 | Validación sin ground truth (las 8 pruebas de §5 de este archivo) |
| 7 | Conclusiones y tabla de problemas, causas e ideas |

### Archivos
- `proyecto1/proyecto1_g4.ipynb`: el notebook.
- `proyecto1/what-happened.md`: este archivo.
- `requirements.txt`: se agregaron `mne` y `pymatreader`.
- **No están en el repo:** el dataset (~690 MB; se baja como en §3) y las figuras exportadas (las genera el notebook).
