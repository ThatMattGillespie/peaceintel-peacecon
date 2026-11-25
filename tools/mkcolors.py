"""Colour downloads: an Adobe swatch file (.ase), a CSV, and the CMYK values the
kit page prints. CMYK comes from ColorSync's GRACoL 2006 Coated profile,
relative colorimetric, so it is a sound starting point for a US coated job."""
import json, struct, sys
from PIL import Image, ImageCms

OUT = sys.argv[1]
COLOURS = [
    # name, hex, role
    ("Paper", "#FCFCFB", "Page background. The ground of everything."),
    ("Paper Warm", "#F3EFE7", "Callouts and highlighted notes only. Also the light text colour on dark."),
    ("Ink", "#141310", "Headlines, body text, the logo. The strongest emphasis the brand has."),
    ("Ink 70", "#4B463E", "Secondary body text."),
    ("Ink 55", "#706B63", "Captions, labels, muted text. The lightest grey allowed for text."),
    ("Ink 35", "#8C877F", "Icons and rules only, never text."),
    ("Dark Band", "#1C1A16", "Dark sections: the closing call to action, a single claim, the footer."),
    ("Dark Ink 70", "#B9B3A9", "Secondary text on a dark band."),
    ("Orange", "#D9481C", "The one accent. Graphics, fills, rules, and type 24px and above."),
    ("Orange Text", "#C04019", "Orange text smaller than 24px on light backgrounds."),
    ("Orange Light", "#F77524", "The accent on a dark band."),
]

srgb = ImageCms.createProfile("sRGB")
cmyk = ImageCms.getOpenProfile("/Library/ColorSync/Profiles/GRACoL2006_Coated1v2.icc")
xf = ImageCms.buildTransform(srgb, cmyk, "RGB", "CMYK", renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC)

rows = []
for name, hx, role in COLOURS:
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    px = ImageCms.applyTransform(Image.new("RGB", (1, 1), (r, g, b)), xf).getpixel((0, 0))
    c, m, y, k = (round(v / 255 * 100) for v in px)
    rows.append({"name": name, "hex": hx, "rgb": [r, g, b], "cmyk": [c, m, y, k], "role": role})

def ase_block(name, rgb):
    nm = (name + "\0").encode("utf-16-be")
    body = struct.pack(">H", len(name) + 1) + nm + b"RGB " + struct.pack(">fff", *[v / 255 for v in rgb]) + struct.pack(">H", 0)
    return struct.pack(">HI", 0x0001, len(body)) + body

def group(name, start):
    nm = (name + "\0").encode("utf-16-be")
    body = struct.pack(">H", len(name) + 1) + nm
    return struct.pack(">HI", 0xC001, len(body)) + body if start else struct.pack(">HI", 0xC002, 0)

blocks = [group("Peace Intel", True)] + [ase_block("PI " + r["name"], r["rgb"]) for r in rows] + [group("", False)]
with open(f"{OUT}/peaceintel-colours.ase", "wb") as f:
    f.write(b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks)) + b"".join(blocks))

with open(f"{OUT}/peaceintel-colours.csv", "w") as f:
    f.write("Name,HEX,R,G,B,C,M,Y,K,Use\n")
    for r in rows:
        f.write(f'{r["name"]},{r["hex"]},{",".join(map(str, r["rgb"]))},{",".join(map(str, r["cmyk"]))},"{r["role"]}"\n')

print(json.dumps(rows))
