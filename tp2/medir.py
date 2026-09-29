"""Reproduce cada excitación por el parlante y la graba con el micrófono de la PC.

Guarda en ./grabaciones/<nombre>.wav (float32, 48 kHz, mono, sin compresión) una
grabación más larga que la excitación (con silencio de --pad segundos antes y
después) para poder sincronizar por software (correlación cruzada) en el notebook.

Uso:
    python medir.py --listar                     # ver dispositivos
    python medir.py --calibrar --in 1 --out 4    # verificar niveles (sin guardar)
    python medir.py --ruido --in 1 --out 4       # grabar 5 s de ruido ambiente
    python medir.py --todas --in 1 --out 4       # las 6 excitaciones
    python medir.py voz musica --in 1 --out 4    # sólo algunas
    python medir.py --todas --ganancia 0.8       # escala la amplitud de reproducción

IMPORTANTE: no muevan la PC, el micrófono ni los objetos de la habitación, y
mantengan el volumen del sistema/parlante fijo durante TODAS las mediciones.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

FS = 48_000
RAIZ = Path(__file__).parent
DIR_EXC = RAIZ / "excitaciones"
DIR_REC = RAIZ / "grabaciones"
NOMBRES = ["voz", "musica", "rectangular", "barrido_lineal", "barrido_exp", "ruido"]


def listar():
    print(sd.query_devices())
    print("\nPor defecto (in, out):", sd.default.device)
    print("Tip: usá dispositivos de la misma API (ej. todos MME o todos WASAPI).")


def reproducir_y_grabar(x, dev_in, dev_out, pad):
    relleno = np.zeros(int(pad * FS), dtype=np.float32)
    salida = np.concatenate([relleno, x, relleno])[:, None]
    extra = {}
    if dev_out is not None and "WASAPI" in sd.query_hostapis(sd.query_devices(dev_out)["hostapi"])["name"]:
        extra["extra_settings"] = sd.WasapiSettings(auto_convert=True)
    rec = sd.playrec(salida, samplerate=FS, channels=1, dtype="float32",
                     device=(dev_in, dev_out), blocking=True, **extra)
    return rec[:, 0]


def informe_nivel(y, nombre):
    pico = np.max(np.abs(y))
    rms_db = 20 * np.log10(np.sqrt(np.mean(y**2)) + 1e-12)
    msg = f"    pico={pico:.3f}  RMS={rms_db:.1f} dBFS"
    if pico >= 0.98:
        msg += "  <-- SATURADO: bajá --ganancia o el volumen de la placa"
    elif pico < 0.02:
        msg += "  <-- muy bajo: subí --ganancia o el volumen (¿micrófono correcto?)"
    print(msg)
    return pico


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("señales", nargs="*", choices=NOMBRES, default=[])
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--calibrar", action="store_true", help="ruido a bajo nivel para chequear niveles")
    ap.add_argument("--ruido", action="store_true", help="graba 5 s de ruido ambiente (sin reproducir)")
    ap.add_argument("--in", dest="dev_in", type=int, default=None, help="índice del micrófono")
    ap.add_argument("--out", dest="dev_out", type=int, default=None, help="índice del parlante")
    ap.add_argument("--ganancia", type=float, default=1.0, help="factor sobre la excitación (default 1)")
    ap.add_argument("--pad", type=float, default=1.0, help="segundos de silencio antes/después")
    ap.add_argument("--espera", type=float, default=3.0, help="segundos de cuenta regresiva")
    args = ap.parse_args()

    if args.listar:
        listar()
        return

    if args.ruido:
        print("Grabando 5 s de ruido ambiente... (silencio, por favor)")
        y = sd.rec(5 * FS, samplerate=FS, channels=1, dtype="float32", device=args.dev_in, blocking=True)[:, 0]
        DIR_REC.mkdir(exist_ok=True)
        sf.write(DIR_REC / "ambiente.wav", y, FS, subtype="FLOAT")
        informe_nivel(y, "ambiente")
        return

    if args.calibrar:
        x = (0.1 * args.ganancia * np.random.default_rng(1).standard_normal(3 * FS)).astype(np.float32)
        y = reproducir_y_grabar(x, args.dev_in, args.dev_out, 0.2)
        informe_nivel(y, "calibración")
        print("    Objetivo: pico de la grabación de la excitación real ~0.3-0.8, sin llegar a 1.")
        return

    nombres = NOMBRES if args.todas else args.señales
    if not nombres:
        ap.error("indicá qué señales medir (o --todas / --listar / --calibrar / --ruido)")

    DIR_REC.mkdir(exist_ok=True)
    for nombre in nombres:
        ruta = DIR_EXC / f"{nombre}.wav"
        if not ruta.exists():
            print(f"[!] No existe {ruta}. Corré generar_excitaciones.py (y poné voz/música en ./fuentes)")
            continue
        x, fs = sf.read(ruta, dtype="float32")
        assert fs == FS, f"{ruta} está a {fs} Hz, se esperaba {FS}"
        x = np.clip(x * args.ganancia, -1, 1).astype(np.float32)

        print(f"\n>> {nombre}: reproduciendo y grabando {len(x) / FS + 2 * args.pad:.1f} s ...")
        import time
        for i in range(int(args.espera), 0, -1):
            print(f"   {i}...", end="\r", flush=True)
            time.sleep(1)
        y = reproducir_y_grabar(x, args.dev_in, args.dev_out, args.pad)
        sf.write(DIR_REC / f"{nombre}.wav", y, FS, subtype="FLOAT")
        print(f"   guardado grabaciones/{nombre}.wav")
        informe_nivel(y, nombre)


if __name__ == "__main__":
    sys.exit(main())
