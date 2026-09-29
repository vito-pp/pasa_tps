"""Importa grabaciones hechas con el celular y las deja en ./grabaciones/<nombre>.wav
(mono, float32, 48 kHz), listas para el notebook. NO recorta ni alinea: eso se hace en el notebook.

Espera archivos del celular en ./celular/ con nombre <señal>.<ext>
(voz, musica, rectangular, barrido_lineal, barrido_exp, ruido; opcional: ambiente).

Uso:
    python importar.py                       # importa todo lo que haya en ./celular
    python importar.py ruta/al/archivo.wav --como barrido_lineal

Formatos: wav/flac/mp3/ogg/caf se leen directo. m4a/aac/3gp/opus requieren ffmpeg
(en PATH, o `pip install imageio-ffmpeg`). Lo mejor es grabar WAV sin compresión.
"""
import argparse
import subprocess
import tempfile
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

FS = 48_000
RAIZ = Path(__file__).parent
DIR_CEL = RAIZ / "celular"
DIR_REC = RAIZ / "grabaciones"
NOMBRES = ["voz", "musica", "rectangular", "barrido_lineal", "barrido_exp", "ruido", "ambiente"]


def _ffmpeg():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def leer(ruta):
    try:
        return sf.read(ruta, dtype="float64", always_2d=True)
    except Exception:
        exe = _ffmpeg()
        if exe is None:
            raise SystemExit(f"No puedo leer {ruta.name}: instalá ffmpeg (o `pip install imageio-ffmpeg`) "
                             "o grabá/exportá en WAV.")
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "x.wav"
            subprocess.run([exe, "-y", "-i", str(ruta), "-c:a", "pcm_f32le", str(wav)],
                           check=True, capture_output=True)
            return sf.read(wav, dtype="float64", always_2d=True)


def importar(ruta, nombre):
    x, fs = leer(ruta)
    canales = x.shape[1]
    x = x.mean(axis=1)                       # a mono
    if fs != FS:
        g = gcd(FS, fs)
        x = resample_poly(x, FS // g, fs // g)
    DIR_REC.mkdir(exist_ok=True)
    sf.write(DIR_REC / f"{nombre}.wav", x.astype(np.float32), FS, subtype="FLOAT")
    pico = np.max(np.abs(x))
    aviso = "  <-- SATURADA (pico ~1): repetir con menos volumen" if pico > 0.98 else (
            "  <-- muy baja: acercar el celular o subir volumen" if pico < 0.02 else "")
    print(f"OK {ruta.name}: {fs} Hz, {canales} canal(es), {len(x) / FS:.1f} s -> "
          f"grabaciones/{nombre}.wav  pico={pico:.3f}{aviso}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo", nargs="?", type=Path)
    ap.add_argument("--como", choices=NOMBRES, help="nombre de señal (si se pasa un archivo)")
    args = ap.parse_args()

    if args.archivo:
        if not args.como:
            ap.error("con un archivo hay que indicar --como <señal>")
        importar(args.archivo, args.como)
        return

    DIR_CEL.mkdir(exist_ok=True)
    hallados = [(n, p) for n in NOMBRES for p in sorted(DIR_CEL.glob(f"{n}.*"))]
    if not hallados:
        print(f"No hay archivos en {DIR_CEL}. Copiá ahí las grabaciones como voz.wav, ruido.m4a, etc.")
    for n, p in hallados:
        importar(p, n)


if __name__ == "__main__":
    main()
