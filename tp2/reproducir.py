"""Reproduce las excitaciones por el parlante de la PC (sin grabar) para grabarlas con el celular.

Cada excitación se reproduce con --pad segundos de silencio antes y después (default 3 s),
para que sea fácil arrancar/parar la grabación del celular sin recortar la señal.

Uso:
    python reproducir.py --listar
    python reproducir.py barrido_lineal --out 4
    python reproducir.py --todas --out 4          # una tras otra; pausa hasta que apretes Enter
    python reproducir.py ruido --ganancia 0.8
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

FS = 48_000
DIR_EXC = Path(__file__).parent / "excitaciones"
NOMBRES = ["voz", "musica", "rectangular", "barrido_lineal", "barrido_exp", "ruido"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("señales", nargs="*", choices=NOMBRES, default=[])
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--out", type=int, default=None, help="índice del parlante")
    ap.add_argument("--ganancia", type=float, default=1.0)
    ap.add_argument("--pad", type=float, default=3.0, help="segundos de silencio antes/después")
    args = ap.parse_args()

    if args.listar:
        print(sd.query_devices())
        return
    nombres = NOMBRES if args.todas else args.señales
    if not nombres:
        ap.error("indicá qué señales reproducir (o --todas / --listar)")

    for nombre in nombres:
        ruta = DIR_EXC / f"{nombre}.wav"
        if not ruta.exists():
            print(f"[!] No existe {ruta}; corré generar_excitaciones.py")
            continue
        x, fs = sf.read(ruta, dtype="float32")
        assert fs == FS
        x = np.clip(x * args.ganancia, -1, 1)
        pad = np.zeros(int(args.pad * FS), dtype=np.float32)
        y = np.concatenate([pad, x, pad])[:, None]

        input(f"\n[{nombre}] 1) Empezá a grabar con el celular  2) Apretá Enter aquí ... ")
        extra = {}
        if args.out is not None and "WASAPI" in sd.query_hostapis(sd.query_devices(args.out)["hostapi"])["name"]:
            extra["extra_settings"] = sd.WasapiSettings(auto_convert=True)
        sd.play(y, FS, device=args.out, blocking=True, **extra)
        print(f"    Listo ({len(y) / FS:.0f} s). Detené la grabación y guardala como '{nombre}'.")


if __name__ == "__main__":
    sys.exit(main())
