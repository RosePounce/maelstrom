"""Export each ship silhouette to an editable SVG, one file per ship.

The SVG keeps the GAME coordinates (nose to the RIGHT, +x forward, +y down),
so a point you move here maps 1:1 back into `player.SHIP_SHAPES`. A light grid
(5 units) and the x/y axes through the origin (the ship centre / hitbox) make
hand-editing easy.

    python tools/export_ship_svg.py        # writes tools/ships/*.svg

After editing an SVG, copy its `<polygon ... id="hull">` / `id="cockpit"`
points back into `SHIP_SHAPES` in `maelstrom/player.py` (same numbers), or send
the files back and they can be re-imported.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # project root, for imports

from maelstrom.player import SHIP_SHAPES            # noqa: E402

OUT = os.path.join(HERE, "ships")
VIEW = (-32, -28, 64, 56)                           # x, y, w, h: fits every ship
CYAN, PINK, FILL, BG, GRID, AXIS = (
    "#54ecf6", "#ff48ac", "#120a1e", "#0a0612", "#201734", "#3a2b52")


def points(poly):
    return " ".join("%g,%g" % (x, y) for x, y in poly)


def build(name, shape):
    x0, y0, w, h = VIEW
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%d %d %d %d" '
        'width="%d" height="%d">' % (x0, y0, w, h, w * 8, h * 8),
        '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x0, y0, w, h, BG),
        '<g stroke="%s" stroke-width="0.12">' % GRID,
    ]
    for gx in range(x0, x0 + w + 1, 5):
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d"/>' % (gx, y0, gx, y0 + h))
    for gy in range(y0, y0 + h + 1, 5):
        out.append('<line x1="%d" y1="%d" x2="%d" y2="%d"/>' % (x0, gy, x0 + w, gy))
    out += [
        '</g>',
        '<!-- origin = ship centre (hitbox); +x is forward, nose to the right -->',
        '<line x1="%d" y1="0" x2="%d" y2="0" stroke="%s" stroke-width="0.3"/>'
        % (x0, x0 + w, AXIS),
        '<line x1="0" y1="%d" x2="0" y2="%d" stroke="%s" stroke-width="0.3"/>'
        % (y0, y0 + h, AXIS),
        '<!-- hull of "%s": edit these points, they are SHIP_SHAPES coords -->' % name,
        '<polygon id="hull" points="%s" fill="%s" stroke="%s" '
        'stroke-width="1.1" stroke-linejoin="round"/>' % (points(shape["hull"]), FILL, CYAN),
        '<polygon id="cockpit" points="%s" fill="%s" stroke="none"/>'
        % (points(shape["cockpit"]), PINK),
        '<circle cx="0" cy="0" r="0.7" fill="#ffffff"/>',
        '</svg>',
        '',
    ]
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, shape in SHIP_SHAPES.items():
        path = os.path.join(OUT, name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(name, shape))
        print(path)


if __name__ == "__main__":
    main()
