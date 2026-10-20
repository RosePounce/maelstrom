"""Read ship SVGs back into SHIP_SHAPES coordinates.

Reverse of `export_ship_svg.py`: for each `tools/ships/<name>.svg`, it finds the
`hull` and `cockpit` shapes (a `<polygon>` as exported, or a `<path>` once
edited in Inkscape) and prints them as ready-to-paste Python lists in game
coordinates (nose right, +y down). Straight segments only (M/L/H/V/Z, absolute
or relative); a curve command raises, on purpose -- the ship outlines are
polygons.

    python tools/import_ship_svg.py            # all ships
    python tools/import_ship_svg.py krait      # one ship

The SVG keeps the original viewBox with no transform, so its numbers ARE the
SHIP_SHAPES numbers; paste them into `maelstrom/player.py`.
"""

import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SHIPS = os.path.join(HERE, "ships")
_NUM = r"-?\d*\.?\d+(?:[eE][-+]?\d+)?"
_TOKEN = re.compile(r"[MmLlHhVvZz]|" + _NUM)
_CURVES = set("CcSsQqTtAa")


def parse_path(d):
    """A path of straight segments -> [(x, y), ...] in absolute coordinates."""
    toks = _TOKEN.findall(d)
    i, cur, cmd, pts = 0, (0.0, 0.0), None, []
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                continue
        if cmd in _CURVES:
            raise ValueError("curve command %r: the outline must be straight" % cmd)
        if cmd in "Mm":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            if cmd == "m":
                x, y = x + cur[0], y + cur[1]
            cur = (x, y); pts.append(cur)
            cmd = "l" if cmd == "m" else "L"      # implicit linetos follow a moveto
        elif cmd in "Ll":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            if cmd == "l":
                x, y = x + cur[0], y + cur[1]
            cur = (x, y); pts.append(cur)
        elif cmd in "Hh":
            x = float(toks[i]); i += 1
            if cmd == "h":
                x += cur[0]
            cur = (x, cur[1]); pts.append(cur)
        elif cmd in "Vv":
            y = float(toks[i]); i += 1
            if cmd == "v":
                y += cur[1]
            cur = (cur[0], y); pts.append(cur)
        else:
            raise ValueError("unsupported path command %r" % cmd)
    return pts


def parse_polygon(points):
    nums = [float(n) for n in re.findall(_NUM, points)]
    return list(zip(nums[0::2], nums[1::2]))


def shape_points(elem):
    tag = elem.tag.split("}")[-1]
    if tag == "polygon":
        return parse_polygon(elem.get("points", ""))
    if tag == "path":
        return parse_path(elem.get("d", ""))
    raise ValueError("id'd element is a <%s>, not polygon/path" % tag)


def fmt(pts):
    def one(v):
        r = round(v, 1)
        return str(int(r)) if r == int(r) else str(r)
    return "[" + ", ".join("(%s, %s)" % (one(x), one(y)) for x, y in pts) + "]"


def main(names):
    files = ([os.path.join(SHIPS, n + ".svg") for n in names] if names
             else sorted(glob.glob(os.path.join(SHIPS, "*.svg"))))
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        root = ET.parse(path).getroot()
        by_id = {e.get("id"): e for e in root.iter() if e.get("id")}
        print('    "%s": {' % name)
        for key in ("hull", "cockpit"):
            elem = by_id.get(key)
            if elem is None:
                print("        # %s: MISSING" % key)
                continue
            print('        "%s": %s,' % (key, fmt(shape_points(elem))))
        print("    },")


if __name__ == "__main__":
    main(sys.argv[1:])
