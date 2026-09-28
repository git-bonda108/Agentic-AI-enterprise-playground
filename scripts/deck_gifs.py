"""Encodes the frames from scripts/render-deck-gifs.mjs as looping GIFs at native size (docs/images/deck/<name>.gif) and
keeps frame 0 as <name>-still.png. Run through uvx so Pillow needs no project dependency:
    uvx --with pillow python scripts/deck_gifs.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

DECK = Path(__file__).resolve().parents[1] / "docs" / "images" / "deck"
FRAMES = DECK / "frames"
FPS = 8

for folder in sorted(p for p in FRAMES.iterdir() if p.is_dir()):
    files = sorted(folder.glob("*.png"))
    if not files:
        continue
    images = [Image.open(f).convert("RGB") for f in files]
    images[0].save(DECK / f"{folder.name}-still.png")
    # One palette drawn from several frames so the beam's colours are in it, and frames that keep the previous pixels
    # (disposal 1) so only the region the light changed is stored.
    sample = Image.new("RGB", (images[0].width, images[0].height * 4))
    for k, idx in enumerate(range(0, len(images), max(len(images) // 4, 1))):
        if k < 4:
            sample.paste(images[idx], (0, images[0].height * k))
    palette = sample.quantize(colors=200, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    out = DECK / f"{folder.name}.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True, disposal=1)
    print(f"{out.name}: {len(frames)} frames, {out.stat().st_size // 1024} KB")

shutil.rmtree(FRAMES, ignore_errors=True)
