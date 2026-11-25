"""Build the PeaceCon kit's image downloads from the brand's own masters.

  python3 mkassets.py <handoff/media> <kit/downloads>

1. VEIL STILLS. veil-dove.mp4 and veil-glass.mp4 are already dithered, 1-bit,
   with a 2px cell. A frame is binarised, reduced to its cell grid, cropped to
   the subject and written as:
     - PNG, ink on transparent, 10px per cell (print and slides)
     - PNG, paper on transparent, for dark backgrounds
     - SVG, one path, so it scales to any size with no loss
2. DITHERED PICTURES. The plain greyscale cut-outs (pic-*.png) are small.
   They are mapped through the brand's 7-stop ramp with the 8x8 Bayer matrix,
   the same treatment as .vmap--still, so they can be enlarged with nearest
   neighbour and stay crisp.
"""
import os, sys, subprocess, tempfile
import numpy as np
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
INK = (0x14, 0x13, 0x10)
PAPER = (0xFC, 0xFC, 0xFB)
PAPER_WARM = (0xF3, 0xEF, 0xE7)

def frame(video, t):
    tmp = tempfile.mktemp(suffix=".png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video,
                    "-frames:v", "1", tmp], check=True)
    g = np.asarray(Image.open(tmp).convert("L"))
    os.remove(tmp)
    return g

def cells(g, cell=2):
    """Binary mask on the cell grid: True where the dither cell is dark."""
    on = g < 128
    h, w = on.shape
    on = on[: h - h % cell, : w - w % cell]
    # A cell is dark when most of its pixels are; this undoes compression blur.
    blk = on.reshape(h // cell, cell, w // cell, cell).mean(axis=(1, 3))
    return blk > 0.5

def crop(mask, pad=6):
    ys, xs = np.nonzero(mask)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, mask.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, mask.shape[1])
    return mask[y0:y1, x0:x1]

def png(mask, colour, scale, path, ground=None):
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), np.uint8)
    if ground:
        rgba[...] = (*ground, 255)
    rgba[mask] = (*colour, 255)
    im = Image.fromarray(rgba, "RGBA").resize((w * scale, h * scale), Image.NEAREST)
    im.save(path, optimize=True, dpi=(300, 300))

def svg(mask, colour, path):
    h, w = mask.shape
    parts = []
    for y in range(h):
        row = mask[y]
        x = 0
        while x < w:
            if row[x]:
                s = x
                while x < w and row[x]:
                    x += 1
                parts.append(f"M{s} {y}h{x - s}v1h{s - x}z")
            else:
                x += 1
    fill = "#%02X%02X%02X" % colour
    with open(path, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                f'width="{w * 10}" height="{h * 10}" shape-rendering="crispEdges">'
                f'<path fill="{fill}" d="{"".join(parts)}"/></svg>\n')

BAYER = None
def bayer8():
    global BAYER
    if BAYER is None:
        m = np.array([[0, 2], [3, 1]])
        for _ in range(2):
            m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
        BAYER = m
    return BAYER

def ramp(ground):
    mix = [0, .08, .20, .36, .55, .76, 1.0]
    return [tuple(round(ground[i] * (1 - t) + INK[i] * t) for i in range(3)) for t in mix]

def dither(path, cells_wide, out_base, scale):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    ch = round(h * cells_wide / w)
    im = im.resize((cells_wide, ch), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    alpha = a[..., 3] / 255
    lum = (a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114) / 255
    lum = lum * alpha + (1 - alpha)                  # transparent reads as white ground
    dark = 1 - lum                                    # 0 = ground, 1 = ink
    f = dark * 6
    k = np.floor(f).astype(int)
    frac = f - k
    k = np.clip(k, 0, 6)
    b = bayer8()
    thr = b[np.arange(ch)[:, None] % 8, np.arange(cells_wide)[None, :] % 8] / 64
    k = np.where((k < 6) & (thr < frac), k + 1, k)
    for name, ground, transparent in (("paper", PAPER, False), ("transparent", PAPER, True)):
        pal = np.array(ramp(ground), np.uint8)
        rgb = pal[k]
        rgba = np.dstack([rgb, np.full(k.shape, 255, np.uint8)])
        if transparent:
            rgba[(k == 0) | (alpha < .5)] = 0
        Image.fromarray(rgba, "RGBA").resize((cells_wide * scale, ch * scale), Image.NEAREST) \
            .save(f"{out_base}-dither-{name}.png", optimize=True, dpi=(300, 300))

os.makedirs(f"{OUT}/doves/veil", exist_ok=True)
os.makedirs(f"{OUT}/doves/illustrations", exist_ok=True)

for clip, picks in (("veil-dove.mp4", {"dove-olive-branch": 0.0, "dove-wings-raised": 3.7}),
                    ("veil-glass.mp4", {"magnifying-glass": 0.0})):
    for name, t in picks.items():
        m = crop(cells(frame(f"{SRC}/{clip}", t)))
        base = f"{OUT}/doves/veil/{name}"
        png(m, INK, 10, f"{base}-ink.png")
        png(m, PAPER_WARM, 10, f"{base}-paper-for-dark.png")
        png(m, INK, 10, f"{base}-on-paper.png", ground=PAPER)
        svg(m, INK, f"{base}-ink.svg")
        svg(m, PAPER_WARM, f"{base}-paper-for-dark.svg")
        print(name, m.shape)

for src in sorted(os.listdir(SRC)):
    if src.startswith("pic-") and src.endswith(".png"):
        stem = src[4:-4]
        dst = f"{OUT}/doves/illustrations/{stem}"
        Image.open(f"{SRC}/{src}").save(f"{dst}-original.png", optimize=True)
        dither(f"{SRC}/{src}", 240, dst, 12)
        print(stem)
