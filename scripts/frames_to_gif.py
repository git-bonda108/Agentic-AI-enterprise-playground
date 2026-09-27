"""Encodes the PNG frames captured by scripts/render-gifs.mjs into looping GIFs in docs/images.

Run through uvx so Pillow needs no project dependency:  uvx --with pillow python scripts/frames_to_gif.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "docs" / "images" / "frames"
FPS = 6
WIDTH = 900  # embedded in the guides; keep each file around a megabyte

for folder in sorted(p for p in FRAMES.iterdir() if p.is_dir()):
    files = sorted(folder.glob("*.png"))
    if not files:
        continue
    # One palette for every frame, and frames that keep the previous pixels (disposal 1), so the encoder stores only the
    # region the beam changed. A moving light on a static diagram is then a fraction of the size of full frames.
    images = []
    for f in files:
        im = Image.open(f).convert("RGB")
        images.append(im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.Resampling.LANCZOS))
    palette = images[0].quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    out = ROOT / "docs" / "images" / f"{folder.name}.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True, disposal=1)
    print(f"{out.name}: {len(frames)} frames, {out.stat().st_size // 1024} KB")

shutil.rmtree(FRAMES, ignore_errors=True)
