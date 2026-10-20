# Contexto para Claude Code: Proyecto 1 (LMS) de 22.46 — Denoising de EEG con el dataset ds008701

> Escrito por Claude (Sonnet 5.5) el 2026-10-18. Es la continuación de `contexto_proyecto1_EEG_LMS.md` (el handoff anterior, que resumía la design review). Este archivo **lo reemplaza como punto de partida para trabajar con datos**: repite lo esencial del modelo, el algoritmo y los criterios (condensado), y agrega **todo lo que se sabe del dataset elegido** y **cómo armar el programa**. Si algo de acá contradice a Pedro o a la consigna (`Proyecto 1.pdf`), mandan ellos.
>
> Etiquetas que uso: **[verificado]** = lo leí en README / archivos del dataset; **[hipótesis]** = lo pienso pero no lo comprobé; **[a chequear]** = lo tenés que mirar vos en los archivos locales antes de asumir nada.

---

## 0. Cómo trabajar con Pedro (leer primero)

Rol: ayudante y tutor de Pedro para **hacer el TP en sí** (implementación, experimentos, informe). La design review ya se presentó (2026-10-09); ahora hay que ejecutar lo prometido, pero **el profesor dio libertad para apartarse de la presentación**, así que el plan de abajo es un punto de partida flexible, no un contrato.

Preferencias de Pedro (dichas por él, aplicalas siempre):
- **Menos verborragia.** Lo más importante primero, el detalle después.
- **En ejercicios de la facultad prefiere recibir la información y el razonamiento para sacar él la conclusión**, no el código resuelto. Si pide código: **legible, al nivel que él podría haberlo escrito, siguiendo la fórmula de la teórica tal cual** (nada de versiones optimizadas o "astutas"), **con un comentario al final de cada línea**. Esto aplica sobre todo a los algoritmos adaptativos (LMS, NLMS, VS-LMS). Para infraestructura (leer archivos, graficar, inspeccionar) podés escribir código directo, sin pedirle permiso, pero igual claro y comentado.
- **Si comete un error conceptual, marcáselo explicando el porqué**, no solo la corrección. (Los agradece.)
- **Referencias concretas**: archivo y sección (por ejemplo "`6. LMS.pdf`, Convergencia, 2º supuesto").
- **Si redactás texto que él va a entregar**, usá su registro coloquial y su vocabulario (dice "bias", no "sesgo"; no uses "plateau").
- **Español rioplatense (voseo).** Estudiante de Ingeniería Electrónica en ITBA; sabe DSP, control y electrónica analógica; **no tiene formación en EEG** ni en procesar datasets BIDS/EEGLAB; no sabe de antemano cómo debería verse el programa. Explicale cada concepto nuevo una vez, corto, y avanzá.
- **Notación del curso (Ressl), no la de Haykin**: `x(n)` datos de entrada (referencias), `y(n)` respuesta deseada, `ŷ = wᴴx`, `e = y − ŷ`. No uses `d(n)` sin aclarar: lo confundió.
- Proponé **pasos cortos y concretos**; que cada paso termine con algo que Pedro pueda mirar (un gráfico, un número).

Archivos del Project "Examen PASA" en claude.ai (si el chat está dentro del Project): `1. Introducción.pdf` … `7. Variantes de LMS.pdf` (los relevantes son `3. Filtrado lineal óptimo`, `5. Descenso por gradiente`, `6. LMS`, `7. Variantes de LMS`). Si vas a afirmar algo del curso, buscalo ahí. **Pedile a Pedro `Proyecto 1.pdf`** (la consigna completa): no tengo su texto, solo lo que él pegó.

**Primera tanda de preguntas cortas para Pedro** (hacelas en el primer mensaje, no más de 4):
1. ¿Qué carpeta `sub-XX` descargaste exactamente? (Yo asumo `sub-01`; confirmalo mirando el disco.)
2. ¿Python o MATLAB? (Yo propongo Python + MNE + numpy/scipy; no me contestó.)
3. ¿Fecha de entrega y formato del TP final (informe, código, notebook)? ¿Hay defensa?
4. ¿Podés adjuntar `Proyecto 1.pdf`?

---

## 1. La consigna (lo que sé)

Materia **22.46 Procesamiento Adaptativo de Señales Aleatorias (ITBA)**. Proyecto 1 = LMS. Tema del grupo: **"Denoising de señales EEG: eliminar el ruido EOG y EMG del EEG"**. Grupo: Pedro Stefoni Rey Iraola, Vito Pensa Piccolo, Javier Pérez Baltasar Loasada.

Núcleo de la consigna (pegado por Pedro):
> "Deben justificar todas las decisiones que tomen: enfoque al problema, algoritmos, meta-parámetros, criterios de calidad (velocidad de convergencia, desajuste, curva de aprendizaje, bias de coeficientes, modos, noise amplification, etc.), y comparaciones entre alternativas. Aprovechen las variantes vistas en clase. Pueden investigar otras variantes de LMS."

Los datos se sacan de **OpenNeuro** (https://openneuro.org/search/eeg) "como dice la consigna". Desconocido: fecha, formato, pesos de cada parte.

---

## 2. Estado actual

- Design review hecha; deck de 18 slides en https://claude.ai/artifact/FMnxJAY7d5Ww9oqW78hYLJ (privado). La slide de datos todavía dice "PENDIENTE: dataset"; **ya está decidido: ds008701**.
- Plan original de la design review: 1) elegir dataset (**hecho**), 2) armar la mezcla, 3) implementar NLMS, LMS y VS-LMS, 4) Monte Carlo y métricas.
- **Todavía no hay código.** Pedro bajó una parte mínima del dataset (sección 7) para empezar a explorar.
- Pendientes menores: bibliografía incompleta (tesis IISc y comparación SCITEPRESS 2013 tomadas de resúmenes), verificar nombres de métricas contra EEGdenoiseNet, unificar "artefacto" vs "ruido".

---

## 3. Modelo del problema (central; no cambiar sin avisar a Pedro)

### Esquema (cancelación adaptativa de ruido con dos referencias)
- Dos fuentes de ruido: `η_EOG(n)` (ojos) y `η_EMG(n)` (músculos). Cada una la ven **dos sensores**.
- **Electrodo de EEG** mide la deseada: `y(n) = s(n) + λ₁·η_EOG(n) + λ₂·η_EMG(n)`, con `s(n)` = EEG limpio.
- **Canales de referencia**: `x₁(n) = h₁ ∗ η_EOG(n) + ruido de medición` (canal de EOG), `x₂(n) = h₂ ∗ η_EMG(n) + ruido de medición` (canal de EMG). Pueden traer algo de fuga de EEG.
- Dos FIR cortos: `ŷ₁ = w₁ᴴx₁`, `ŷ₂ = w₂ᴴx₂`. Salida: `e(n) = y(n) − ŷ₁(n) − ŷ₂(n) ≈ s(n)`.
- Para el algoritmo se **apilan**: `w = [w₁; w₂]`, `x(n) = [x₁(n), …, x₁(n−M+1), x₂(n), …, x₂(n−M+1)]ᵀ` (largo `2M`). **Un único `e(n)` ajusta los dos filtros.**

### Por qué así (errores conceptuales previos de Pedro; no repetir)
- La **deseada `y` NO es el EEG limpio ni el ruido solo**: es lo que mide el electrodo (EEG + ruido). El EEG entra al sistema **solo por `y`**; lo que los filtros no pueden armar desde `x₁, x₂` queda en `e(n)`.
- **El filtro va en el camino de la referencia, no sobre `y`**: solo se modifica una copia del ruido; el EEG de `y` no pasa por ningún filtro. El filtro aprende la ganancia/retardo relativo referencia→electrodo.
- **A qué se adapta:** el algoritmo minimiza `E{|e|²}`. Como el EEG no está correlacionado con las referencias, `E{|e|²} = E{|s|²} + E{|ruido − ŷ|²}` ⇒ minimizar es acercar `ŷ` al ruido tal como llega al electrodo (**principio de ortogonalidad**; `6. LMS.pdf`, Convergencia, 2º supuesto: `y = w_oᴴx + e_o`, y **acá `e_o` es el EEG**).
- **Matiz:** si la referencia trae fuga de EEG, el filtro también resta EEG bueno ⇒ el MSE solo no alcanza; se evalúa contra el EEG limpio.
- **`w_o` = solución de Wiener `R⁻¹p`**, NO "≈ λ" (depende de `h`, ruido de medición y fuga). Se usa para el bias de coeficientes.
- **EMG:** solo se cancela si hay un canal que lo mida. Sin canal EMG no existe `w₂` y el EMG queda en `e(n)`; hay que decirlo.
- **Referencia fabricada:** como en datos reales no hay referencia con relación conocida, **armamos `x₁, x₂` degradando `η`** (camino corto + ruido de medición + fuga de EEG). Si `x = η` exacto, el problema es trivial. Hay que justificar y **barrer** esos parámetros.

### Corrección respecto de las slides (importante)
En las slides se dijo "el piso de la curva de aprendizaje es `Jo` = potencia del EEG". **Es solo una cota inferior.** El piso correcto es **`J_min = E{|y − w_oᴴx|²}`** (error de Wiener con `x` imperfecto: incluye ruido de medición de la referencia y cualquier ruido no explicable). El desajuste es `ℳ = (J(∞) − J_min)/J_min = Jex/J_min`. Usá `J_min` calculado desde Wiener, no la potencia del EEG. Cuando la referencia es exacta y sin fuga, `J_min → potencia del EEG`.

---

## 4. Las señales (órdenes de magnitud, no mediciones)

- **EEG:** ~10–100 µV; útil ~0,5–40 Hz; banda ancha, **coloreado** (no blanco). Bandas: δ 0,5–4, θ 4–8, α 8–13, β 13–30, γ 30+ Hz.
- **EOG (parpadeos y movimientos oculares):** cientos de µV; baja frecuencia (~0–15 Hz) ⇒ se pisa con δ/θ; máximo en electrodos frontales; camino ojos→electrodo casi instantáneo ⇒ `w_o` corto (`M ≈ 3`, He et al.).
- **EMG (cara, mandíbula, cuello):** banda muy ancha (~20 Hz a cientos de Hz) ⇒ se pisa con β/γ; en **ráfagas** (no estacionario).
- **Consecuencias para el filtro:**
  - EOG pasa-bajos ⇒ `R` con **spread de autovalores grande** ⇒ `μ < 2/λmax` y **modos lentos** (`τ_k ≈ 1/(μλ_k)`).
  - La potencia de la referencia cambia muchísimo ⇒ `ℳ = (μ/2)tr R` se mueve con la potencia (**noise amplification** en LMS).
  - EEG no blanco ⇒ la teoría de `ℳ` y `τ` vale solo aproximada ⇒ **todo con Monte Carlo**.
  - Las bandas se pisan ⇒ un filtro fijo se lleva EEG; hace falta un filtro adaptativo con referencia.

---

## 5. Algoritmos (decididos) y criterios

**Decisión de Pedro:** NLMS es el elegido; LMS y VS-LMS se implementan para comparar; el resto se descarta con argumentos. Es una **hipótesis de diseño a verificar**, no un resultado.

Fórmulas (de `7. Variantes de LMS.pdf`; verificá `D(n)` en el PDF antes de usar la cota de estabilidad):
- **LMS:** `w(n+1) = w(n) + μ x(n) e*(n)`; `0 < μ < 2/λmax`; `τ_k ≈ 1/(μλ_k)`; `ℳ = (μ/2) tr R`. Metaparámetros: μ, w(0).
- **NLMS:** `w(n+1) = w(n) + μ̃ x(n) e*(n) / (‖x(n)‖² + δ)`; `0 < μ̃ < 2·D(n)·E{‖x‖²}/E{|e|²}`. Equivale a LMS con `μ(n) = μ̃/‖x(n)‖²`. Metaparámetros: μ̃, δ, w(0). Saca la dependencia de la **potencia de `x`**; **no arregla el spread de autovalores**.
- **VS-LMS (Harris 1986):** paso variable por coeficiente. Metaparámetros: α, m0, m1, μmin, μmax, w(0), μ(0) (7).

Argumentos para NLMS: (1) la potencia de `x` cambia todo el tiempo (parpadeos, ráfagas); (2) `δ` cubre `‖x‖² ≈ 0`; (3) 3 metaparámetros contra 7.

**Hipótesis ("qué esperamos ver"):** con potencia de `x` constante LMS ≈ NLMS; con un parpadeo `ℳ` de LMS sube y el de NLMS queda ~constante; la curva `J(n)` converge a `J_min` (no a 0); VS-LMS podría converger más rápido con menos desajuste a costa de 7 metaparámetros. **Si no se cumple, se explica por qué: eso también es resultado.**

**Descartadas:** sign-error (normaliza por `e`, no ataca la potencia de `x`), sign-data/sign-sign (ahorran multiplicaciones; con `M` chico no hace falta), Block/Fast Block LMS (ganan con filtros largos; con `M≈3` no ahorran y agregan latencia), RLS (fuera del curso, `O(M²)`, trabajo a futuro; ojo: en la literatura es de los mejores para EOG), Normalized Fast Block LMS (solo si `M` fuera grande: iguala modos dividiendo por la potencia de cada bin de la FFT). Candidatos extra si piden "investigar otras variantes": leaky LMS, VSS-LMS, APA, RLS.

**Criterios de calidad (aprobados por Pedro):**

| Criterio | Cómo se mide |
|---|---|
| Modos | Autovalores de `R` estimada (spread `λmax/λmin`; fija `μmax`) |
| Velocidad de convergencia | Muestras hasta `J(∞) + x %` |
| Desajuste | `ℳ = (J(∞) − J_min)/J_min` por Monte Carlo |
| Curva de aprendizaje | `J(n)` = promedio de `|e(n)|²` sobre N realizaciones |
| Bias de coeficientes | `‖E{w(n)} − w_o‖`, `w_o` de Wiener |
| Noise amplification | `ℳ` contra potencia de `x`, LMS vs NLMS |

**Métricas de limpieza** (contra el EEG limpio `s`, con `ŝ = e`): RRMSE temporal `RMS(ŝ−s)/RMS(s)`; RRMSE espectral (sobre la PSD); correlación de Pearson; complejidad (multiplicaciones/muestra; costo de simulación `N·n·M`). *Nombres tomados de memoria de EEGdenoiseNet (Zhang 2021), no verificados.*

---

## 6. Idea de datos: cómo se conectan los datos con el modelo

En datos reales **no existe el EEG limpio**, así que no se puede medir qué tan bien se limpia. Por eso:
1. **EEG limpio** (tramos sin artefactos) = ground truth `s(n)`.
2. **Ruido** (EOG real del mismo dataset; EMG según estrategia, ver 8.4) escalado a un **SNR conocido**.
3. **Mezcla** `y = s + λ₁η_EOG + λ₂η_EMG` y **referencias fabricadas** `x₁, x₂` degradando `η`.
Solo la suma es sintética; el EEG y el EOG son registros reales. Los datos reales sin tocar (EEG con parpadeos tal cual) se usan **solo para validación cualitativa**: el pico de parpadeo debe desaparecer de `e(n)` y `e(n)` debe dejar de correlacionar con el canal de EOG.

**Dificultad central de este dataset:** el EEG grabado **ya puede traer artefactos** (parpadeos en Fp1/Fp2, etc.), así que "EEG limpio" hay que *buscarlo* (canales/tramos sin parpadeos, o canales lejos de los ojos) y no se puede asumir. Ver 7.4.

---

## 7. El dataset: ds008701

### 7.1 Qué es [verificado]
- **OpenNeuro ds008701, versión 1.0.4**, "MET – Music-Induced Emotion EEG Dataset". URL: https://openneuro.org/datasets/ds008701/versions/1.0.4
- **20 participantes**. Cada uno escuchó **20 canciones de un pool de 30**, y a cada canción corresponde una carpeta `ses-tXX`.
- **Lo que significa `ses-tXX`: no es una sesión temporal, es el índice de la canción.** El `XX` va de `t01` a `t30` según qué canción del pool sea; cada sujeto tiene solo 20 de las 30 (así que **no hay 30 `ses-t` por sujeto**; si ves 30, avisale a Pedro, porque entonces algo de lo que leí está mal).
- Cada registro dura **130 s = 5 s pre + 120 s de música + 5 s post**.
- **fs = 1000 Hz**. **66 canales EEG + 1 canal EOG**. **0 canales EMG.**
- Banda de grabación 0,5–70 Hz (hardware/filtro informado en `eeg.json`). Unidades: **voltios** (hay que pasar a µV).
- Referencia del EEG y frecuencia de línea eléctrica: **desconocidas** (leer `eeg.json`/README; Argentina sería 50 Hz pero el dataset no necesariamente es de acá).
- `events.tsv` solo marca **"bad"** en el borde (en 0 s y en 127–130 s aprox.): sirve para saber qué recortar, no para detectar parpadeos.
- `ratings.tsv` (en el root) trae las puntuaciones de las canciones; **la columna se llama mal escrita `Song Catergory`** (typo del dataset, no lo "arregles" al leer), y hay una nota de que **"0 = data missing"**.
- El README no declara licencia ni cita del dataset: mirá `dataset_description.json` y `datacite.yml` (están en lo que bajó Pedro) y citalos bien en el informe.

### 7.2 Qué tiene Pedro en disco (y qué NO) [a chequear]
El repo completo son **3198 archivos y 13,06 GB**. Pedro **no** lo bajó. Tiene:
- En el root: `CHANGES`, `README`, `dataset_description.json`, `.bidsignore`, `.gitattributes`, `datacite.yml`, `participants.json`, `participants.tsv`, `ratings.json`, `ratings.tsv`, `.datalad/config`.
- **Un solo sujeto** `sub-XX/` (yo creo que `sub-01`, **confirmalo**) con las **20 carpetas `ses-tYY/`** de las canciones que ese sujeto escuchó. Dentro de cada una:
  - `sub-XX_ses-tYY_scans.tsv`
  - `eeg/sub-XX_ses-tYY_task-music_eeg.set` (la señal)
  - `eeg/..._channels.tsv` (nombre, tipo y unidad de cada canal)
  - `eeg/..._eeg.json` (fs, filtros, referencia, nº de canales…)
  - `eeg/..._events.tsv` y `..._events.json`
  - `eeg/..._electrodes.tsv` y `..._coordsystem.json` (posiciones, sistema CapTrak)

**Reglas:**
- **No intentes bajar los 13 GB.** Todo el desarrollo se hace con este sujeto (20 grabaciones ≈ 43 min de EEG a 1 kHz). Con eso alcanza para armar y justificar el pipeline.
- Los `.set` pesados están gestionados por git-annex/DataLad: si ves un `.set` de 0 bytes o un link roto, avisale a Pedro, no inventes datos.
- La **generalización a otros sujetos** (Monte Carlo entre sujetos) queda como limitación o como mejora si Pedro baja más sujetos. Con un solo sujeto, las realizaciones del Monte Carlo salen de **distintos tramos y distintas canciones**, no de distintas personas: decilo en el informe.
- Pedro tiene `participants.tsv`/`ratings.tsv` completos: sirven para ubicar qué canciones oyó su sujeto y, si interesa, para elegir canciones "tranquilas" vs "movidas" (más o menos parpadeos/actividad muscular) [hipótesis, no verificada].

### 7.3 Formatos de archivo (Pedro preguntó qué son)
- **`.set`** = archivo de **EEGLAB** (MATLAB `.mat` con otro nombre): una estructura con la matriz de señal (canales × muestras), `srate`, `chanlocs`, eventos, etc. En este dataset **no hay `.fdt` aparte**, así que la señal está dentro del `.set`. En Python: `mne.io.read_raw_eeglab(path, preload=True)`. En MATLAB: `pop_loadset` (EEGLAB).
- **`.tsv`** = tabla en texto separada por tabulaciones. En Python `pandas.read_csv(path, sep="\t")`; en MATLAB `readtable(path, 'FileType','text','Delimiter','\t')`.
- **`.json`** = metadatos clave-valor (fs, filtros, nº de canales…). `json.load`.
- En BIDS: `channels.tsv` dice el **tipo** de cada canal (EEG/EOG/…); `events.tsv` los eventos; `scans.tsv` la lista de archivos de la sesión.

### 7.4 Incógnitas que hay que resolver mirando los datos (en este orden)
1. **¿Cómo se llama el canal EOG y qué tipo declara `channels.tsv`?** ¿Es realmente EOG o solo una etiqueta? ¿Está bipolar (vertical) o referido a algo? Un solo canal EOG: no distingue vertical de horizontal (comparalo con Fp1/Fp2 para ver qué parpadeos capta).
2. **¿El EEG ya está limpiado de artefactos?** Chequeo clave: ¿se ven parpadeos como deflexiones grandes (cientos de µV) en `Fp1/Fp2/AF*` coincidentes con picos del canal EOG? Si **no hay parpadeos en el EEG** (ya fue limpiado con ICA, por ejemplo), el dataset sigue sirviendo igual como **EEG limpio + EOG real para mezclar**, pero **no sirve para validar sobre artefactos reales**. Si **sí hay**, el EEG no es ground truth en frontales y hay que usar canales posteriores (`Oz`, `O1/O2`, `POz`…) como "limpios" para la mezcla.
3. **¿Cuánta fuga de EEG tiene el canal EOG?** (correlación del EOG con canales posteriores, PSD del EOG: ¿pasa potencia de α a 10 Hz?).
4. **¿Hay EMG en los canales temporales bajos?** Candidatos: `T9, T10, TP9, TP10, FT9, FT10` (cerca de mandíbula/cuello). Prueba: cociente de potencia 30–70 Hz vs 8–12 Hz, envolvente en ráfagas, simultaneidad entre canales laterales. **El dataset registra hasta 70 Hz**, o sea solo la parte baja del espectro del EMG (que llega a cientos de Hz): el EMG disponible es parcial. Es **hipótesis mía** que haya EMG utilizable ahí; hay que comprobarlo y, si no, usar otra estrategia (8.4).
5. **Línea eléctrica:** pico a 50 o 60 Hz en la PSD (hay que notchear o dentro de 0,5–70 Hz queda el pico).
6. **Canales planos/malos, referencia, saturaciones, escala:** ¿están en V? ¿algún canal con amplitud 0?
7. **Qué hay en los bordes marcados "bad":** descartarlos; la ventana útil recomendada es **5 s a 125 s** (los 120 s de música) [a chequear contra `events.tsv`].
8. **¿Cuántos parpadeos por registro?** (detección por umbral sobre el EOG pasa-bajos). Determina cuántos tramos con artefacto real hay para validar.

---

## 8. Cómo armar el programa (flexible)

### 8.1 Primer script de inspección (hacerlo YA, antes de cualquier algoritmo)
Cargar **una** grabación (por ejemplo la primera `ses-t??`) y sacar, con gráficos guardados a archivo:
1. Lista de canales, tipos (de `channels.tsv`), unidad, fs, duración (de `eeg.json` y de MNE), y confirmación de que el nº de canales coincide con lo declarado (66+1).
2. Serie temporal de 130 s de: EOG, `Fp1`, `Fp2`, `Oz`, `T9`, `T10` (en µV).
3. PSD (Welch) de esos canales y del EOG, 0–70 Hz (escala log): ver pico de línea y forma espectral.
4. Detección simple de parpadeos en el EOG (umbral sobre un pasa-bajos de ~10 Hz) y su cantidad; correlación EOG–`Fp1` y EOG–`Oz`.
5. Prueba de EMG en `T9/T10/TP9/TP10/FT9/FT10` (cociente 30–70 Hz / 8–12 Hz; envolvente).
6. Repetir 2–5 sobre un par más de canciones para ver variabilidad.
Con eso Pedro y vos deciden la estrategia de la sección 8.4. Guardar los resultados en `docs/inspeccion.md` con figuras.

### 8.2 Módulos del programa (propuesta; ajustar con Pedro)
Estructura sugerida del repo:
```
proyecto1_lms_eeg/
  data/                  # el sujeto bajado + root (solo lectura, no tocar)
  src/
    io_eeg.py            # carga .set, channels.tsv; devuelve señales en µV y metadatos
    segmentos.py         # recorte 5-125 s, filtrado básico, división en tramos
    fuentes.py           # arma s(n) (EEG limpio) y η_EOG / η_EMG
    mezcla.py            # y = s + λ1 η_EOG + λ2 η_EMG ; referencias x1, x2 fabricadas
    nucleos.py           # LMS, NLMS, VS-LMS (fórmula de la teórica, literal)
    wiener.py            # R, p, w_o = R^{-1}p, autovalores, J_min, μmax
    montecarlo.py        # N realizaciones, promedia J(n), E{w(n)}, ℳ, tiempo de convergencia
    metricas.py          # RRMSE temporal/espectral, correlación, complejidad
    validacion_real.py   # datos sin tocar: e(n) vs canal EOG, picos de parpadeo
  experimentos/          # un script por experimento (barridos)
  docs/                  # inspección, decisiones y justificaciones (alimenta el informe)
  figuras/
```
Responsabilidades:
1. **Cargador** (`io_eeg`): `.set` → arreglo `canales × muestras` en µV + lista de nombres + tipo; usar `channels.tsv` para tipos; no depender de que MNE adivine.
2. **Preprocesado mínimo** (`segmentos`): recorte a la ventana útil; filtrado pasa-banda moderado (documentar corte), eventualmente notch de línea; **decidir y justificar si se submuestrea** (p. ej. 1000 → 250 Hz reduce costo; el EMG hasta 70 Hz exigiría fs ≥ 200 Hz, o sea ≥ 250 Hz).
3. **Fuentes** (`fuentes`): `s(n)` = EEG de un canal "limpio" (tramo/canal sin parpadeos) ; `η_EOG(n)` = canal EOG real (centrado, quizá pasa-bajos); `η_EMG(n)` según 8.4.
4. **Mezcla** (`mezcla`): elegir `λ₁, λ₂` por **SNR objetivo** (definir SNR por potencia: `λ = sqrt(P_s / (P_η · 10^{SNR/10}))`); fabricar `x₁ = h₁∗η_EOG + ruido`, `x₂ = h₂∗η_EMG + ruido` (+ fuga de EEG opcional).
5. **Núcleos adaptativos** (`nucleos`): LMS, NLMS, VS-LMS tal cual la teórica (ver 0: **código lo escribe Pedro con guía, salvo que pida que lo hagas**).
6. **Wiener** (`wiener`): `R = E{xxᵀ}`, `p = E{x y}`, `w_o = R⁻¹p`, autovalores, `J_min = E{|y − w_oᵀx|²}`; `μmax = 2/λmax`.
7. **Monte Carlo** (`montecarlo`): N tramos distintos (distintas canciones y posiciones dentro de los 120 s); promedia `|e(n)|²`, `w(n)`; calcula `ℳ`, velocidad, bias.
8. **Métricas** y **validación real**.

### 8.3 Decisiones de diseño que hay que justificar en el informe (cada una)
- Longitud de tramo `N` (por ejemplo 2–10 s) y nº de realizaciones.
- Rango de SNR (barrer, p. ej. de −10 a +10 dB) y por qué.
- Largo y forma de `h₁`, `h₂` (camino ruido→referencia), ruido de medición en `x`, fuga de EEG en `x`.
- `M` (He et al.: 3; barrer 2–16 y ver si cambia algo).
- `μ`, `μ̃` (barrido en escala logarítmica hasta cerca del límite), `δ` (relativo a la potencia típica de `x`), `w(0)` (ceros).
- Parámetros de VS-LMS (α, m0, m1, μmin, μmax, μ(0)) y cómo se eligieron.
- Frecuencia de muestreo y filtrado previo.
- Canal "limpio" elegido para `s(n)` y por qué.
- Cómo se define el ground truth si el EEG ya trae algo de ruido residual (limitación).

### 8.4 Estrategias para el EMG (no hay canal EMG en ds008701)
Decisión pendiente con Pedro, a partir de lo que muestre la inspección. Opciones (ordenadas por mi preferencia):
- **A. Proxy real:** `x₂` = canales temporales bajos (`T9/T10/TP9/TP10/FT9/FT10`) filtrados > ~20 Hz, solo si 8.1-5 muestra EMG real. Honesto y todo con datos del dataset. Limitación: hasta 70 Hz y con EEG mezclado.
- **B. EMG sintético:** ruido filtrado (20–70 Hz) modulado en amplitud por ráfagas (envolvente tipo on/off), como `η_EMG`; la referencia `x₂` se fabrica igual. Control total del SNR; hay que declarar que es sintético.
- **C. EMG externo:** segmentos musculares de EEGdenoiseNet (Zhang 2021; 5598 segmentos de 2 s, sin referencia medida) para `η_EMG`. Requiere traerlo (no es OpenNeuro).
- **D. Declarar la limitación:** el caso "EMG" se omite, el EMG queda en `e(n)`, y se analiza cómo afecta.
Recomendación de trabajo: **primero el caso solo-EOG con el EOG real** (es el más sólido y ya cubre todo el análisis de LMS vs NLMS vs VS-LMS), **después agregar EMG** por A o B para el caso de dos referencias.

### 8.5 Orden de trabajo sugerido
1. Inspección (8.1) + resultados a `docs/`. Decidir 7.4(2) y 7.4(4).
2. `io_eeg` + `segmentos` + `fuentes` + `mezcla` con **un** caso (solo-EOG, SNR fijo, `M=3`). Chequeo visual: `y`, `s`, `x₁`.
3. `wiener`: calcular `w_o`, `J_min`, autovalores y **spread**. Mostrarle a Pedro el spread: es lo que explica por qué `μ` debe ser chico.
4. `nucleos`: LMS primero (Pedro lo escribe), luego NLMS, luego VS-LMS. Cada uno con su curva `J(n)` contra `J_min`.
5. `montecarlo` + barridos de `μ̃`, `M`, SNR.
6. Caso con potencia no constante: tramos con y sin parpadeos para mostrar `ℳ` contra la potencia de `x` (LMS vs NLMS).
7. Agregar EMG (8.4).
8. Métricas de limpieza.
9. Validación real.
10. Contrastar con la hipótesis de la sección 5 y escribir el informe: justificar **cada** decisión.

---

## 9. Conceptos que a Pedro le costaron

- `d(n)` vs `y(n)`; qué es `x(n)` (sección 3).
- Pensó que la deseada podía ser el EEG limpio, o solo el ruido (sección 3: errores 1 y 2).
- **Ground truth:** el EEG limpio conocido contra el que se compara; solo existe porque armamos la mezcla.
- **Artefacto** = ruido EOG/EMG (nombre del campo); Pedro prefiere "ruido".
- **Por qué NLMS no arregla el spread de autovalores** (divide por la potencia total, reescala todos los modos igual).
- **Qué es un `.set` / `.tsv`** (7.3), y qué es cada `ses-t` (7.1).
- Ya sabe bien: LMS, NLMS, sign-*, Block LMS, Fast Block LMS, LS; razonó correctamente que el EOG da `R` mal condicionada y por eso `μ` chico.

---

## 10. Riesgos y limitaciones (no esconderlos en el informe)

1. **EEG coloreado:** ℳ y τ de la teoría son aproximadas; se mide con Monte Carlo.
2. **Referencia fabricada:** el resultado depende de cómo la armemos; barrer y justificar. `x = η` exacto es trivial.
3. **Fuga de EEG en `x`:** el filtro resta EEG bueno; se mide con RRMSE y correlación.
4. **Spread de autovalores:** NLMS no lo arregla.
5. **Sin canal EMG en el dataset:** ver 8.4; el EMG disponible es parcial (≤ 70 Hz).
6. **Un solo canal EOG:** no separa vertical/horizontal.
7. **Un solo sujeto bajado:** no hay variabilidad entre personas.
8. **El "EEG limpio" puede no estar limpio:** ground truth aproximado.
9. **Datos reales sin ground truth:** solo validación cualitativa.
10. **Dataset sin licencia/cita declarada en el README:** revisar `dataset_description.json` / `datacite.yml`.

---

## 11. Antecedentes (para el informe)

- Croft & Barry (2000), "Removal of ocular artifact from the EEG: a review", *Neurophysiol. Clin.* 30.
- He, Wilson & Russell (2004), *Med. Biol. Eng. Comput.*: VEOG+HEOG, FIR M=3 cada uno.
- Fariborzi et al. (2007), ICIAS: HEOG, VEOG y EMG como tres referencias en LMS multicanal.
- Tesis IISc, "Adaptive Noise Cancellation (ANC) for EOG Artefact Minimization": una referencia de EOG alcanza (de un resumen; faltan datos).
- SCITEPRESS 2013, "Performance Evaluation of Methods for Correcting Ocular Artifacts in EEG Recordings": LMS y RLS entre los mejores (de un resumen; faltan datos).
- Zhang et al. (2021), EEGdenoiseNet, *J. Neural Eng.* 18 (https://arxiv.org/abs/2009.11662).
- Bismor, Czyz & Ogonowski (2015), VSS-LMS review.
- Klados & Bamidis (2016), dataset semi-simulado EEG/EOG (Mendeley, DOI 10.17632/wb6yvr725d.3; detalles sin verificar).
- Haykin, *Adaptive Filter Theory*; apuntes de Ressl (`6. LMS`, `7. Variantes de LMS`).
- Dataset ds008701 (OpenNeuro): citarlo con lo que figure en `dataset_description.json`.

---

## 12. Cosas no verificadas

- Métricas (RRMSE, correlación): de memoria de EEGdenoiseNet.
- Detalles de la tesis IISc y de la comparación SCITEPRESS 2013: de resúmenes.
- Klados & Bamidis: solo el abstract.
- Rangos de frecuencia y amplitud de EEG/EOG/EMG: órdenes de magnitud.
- Normalized Fast Block LMS (desacople por FFT): teoría general, no del PDF.
- Del dataset: que el EEG ya esté (o no) limpiado de parpadeos; qué mide exactamente el canal EOG; presencia de EMG en temporales; referencia del EEG; frecuencia de línea; cuál `sub` bajó Pedro.
- La nota de "0 = data missing" en `ratings.tsv` y el typo `Song Catergory`: leídos del README, no inspeccionados en el archivo.
- Descargar los `.set` por fuera de OpenNeuro/DataLad no se probó; el espejo de GitHub (`raw.githubusercontent.com/OpenNeuroDatasets/ds008701/main/<path>`) sirve texto/TSV/JSON pero no los `.set` pesados.

---

## 13. Checklist del primer día con Claude Code

- [ ] Listar el árbol local y confirmar qué `sub` hay y cuántas `ses-t` (esperado: 20).
- [ ] Leer README, `dataset_description.json`, `datacite.yml`, un `channels.tsv` y un `eeg.json`.
- [ ] Cargar un `.set` con MNE, confirmar 66 EEG + 1 EOG, fs 1000 Hz, unidades.
- [ ] Hacer el script de inspección (8.1) y guardar figuras.
- [ ] Responder 7.4 (1–8) con evidencia.
- [ ] Con Pedro: elegir estrategia de EMG (8.4), lenguaje (Python/MATLAB), y confirmar plazos y formato del TP.
