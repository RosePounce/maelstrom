"""Build the application icon from `assets/favicon.png`.

The favicon is 64 x 64 pixel art: it is enlarged pixel for pixel (no
smoothing) to 256 x 256, which keeps its edges sharp. Produces
`packaging/icon.png` (AppImage) and, when Pillow is available,
`packaging/icon.ico` (Windows installer and executable).
"""

import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(os.path.dirname(HERE), "assets", "favicon.png")
SIZE = 256


def main():
    img = Image.open(SOURCE).convert("RGBA")
    img = img.resize((SIZE, SIZE), Image.NEAREST)
    png = os.path.join(HERE, "icon.png")
    img.save(png)
    print("written:", png)
    ico = os.path.join(HERE, "icon.ico")
    img.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                         (64, 64), (128, 128), (256, 256)])
    print("written:", ico)
    return 0


if __name__ == "__main__":
    sys.exit(main())
