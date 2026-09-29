"""Genera las 6 excitaciones del TP2 (10 s, fs = 48 kHz, mono, float32) en ./excitaciones

Voz y música no se sintetizan: se toman de archivos propios en ./fuentes
(voz.wav / musica.wav, o cualquier formato que lea soundfile) y se recorta un
fragmento de 10 s a partir de --voz-inicio / --musica-inicio (en segundos).

Uso:
    python generar_excitaciones.py
    python generar_excitaciones.py --voz-inicio 12.5 --musica-inicio 30
"""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd

FS = 48_000
T = 10.0
F0, F1 = 20.0, 20_000.0
PICO = 0.5  # amplitud pico común (la ganancia final se ajusta en medir.py)

RAIZ = Path(__file__).parent
DIR_EXC = RAIZ / "excitaciones"
DIR_SRC = RAIZ / "fuentes"


def normalizar(x, pico=PICO):
    return (pico * x / np.max(np.abs(x))).astype(np.float32)


def rectangular(t, f=100.0):
    return np.sign(np.sin(2 * np.pi * f * t))


def barrido_lineal(t):
    k = (F1 - F0) / T
    return np.sin(2 * np.pi * F0 * t + 2 * np.pi * k * t**2 / 2)


def barrido_exponencial(t):
    k = (F1 / F0) ** (1 / T)
    return np.sin(2 * np.pi * F0 * (k**t - 1) / np.log(k))


def ruido_blanco(n, seed=0):
    x = np.random.default_rng(seed).standard_normal(n)
    return np.clip(x, -4, 4)  # recorte de colas extremas para no saturar


def cargar_fragmento(nombre, inicio):
    """Busca fuentes/<nombre>.* , lo pasa a mono, remuestrea a FS y recorta T s."""
    candidatos = sorted(DIR_SRC.glob(f"{nombre}.*"))
    if not candidatos:
        return None
    x, fs = sf.read(candidatos[0], always_2d=True)
    x = x.mean(axis=1)
    if fs != FS:
        g = gcd(FS, fs)
        x = resample_poly(x, FS // g, fs // g)
    i0 = int(inicio * FS)
    seg = x[i0:i0 + int(T * FS)]
    if len(seg) < int(T * FS):
        raise SystemExit(f"'{candidatos[0].name}' no tiene {T:.0f} s a partir de {inicio} s")
    return seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voz-inicio", type=float, default=0.0)
    ap.add_argument("--musica-inicio", type=float, default=0.0)
    args = ap.parse_args()

    DIR_EXC.mkdir(exist_ok=True)
    DIR_SRC.mkdir(exist_ok=True)
    n = int(T * FS)
    t = np.arange(n) / FS

    señales = {
        "rectangular": rectangular(t),
        "barrido_lineal": barrido_lineal(t),
        "barrido_exp": barrido_exponencial(t),
        "ruido": ruido_blanco(n),
    }
    for nombre, inicio in (("voz", args.voz_inicio), ("musica", args.musica_inicio)):
        seg = cargar_fragmento(nombre, inicio)
        if seg is None:
            print(f"[!] Falta fuentes/{nombre}.wav (o .mp3/.flac): se omite '{nombre}'")
        else:
            señales[nombre] = seg

    for nombre, x in señales.items():
        sf.write(DIR_EXC / f"{nombre}.wav", normalizar(x), FS, subtype="FLOAT")
        print(f"OK  excitaciones/{nombre}.wav  ({len(x) / FS:.1f} s, fs={FS})")


if __name__ == "__main__":
    main()
