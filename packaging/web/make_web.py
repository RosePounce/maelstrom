"""Build the browser version with pygbag and pack it for upload.

pygbag archives the whole folder it is pointed at, and the filters of
`pygbag.ini` only reject a directory one level deep: aimed straight at the
repository it also packs `.venv`, `docs` and `tools/ships`, which no browser
ever loads. So the build runs on a staging copy, `build/maelstrom`, holding
`main.py`, `menu.py`, `maelstrom`, `settings` and `assets` and nothing else.
The soundtrack in that copy is then re-encoded to mono 22 kHz (see
`shrink_audio`), so the repository's full-quality tracks are left untouched.

The result is packed flat into `dist/Maelstrom-<version>-web.zip`:
`index.html` at the root of the zip is what itch.io expects. That page picks
its payload at run time -- the `.apk` on itch.io, the `.tar.gz` anywhere else
-- so both stay in the archive and it uploads to either.

    python packaging/web/make_web.py 1.0.0

Needs pygbag (`pip install pygbag`), and ffmpeg to shrink the soundtrack:
without it the tracks are packed as they are, three times heavier.
"""

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
APP_NAME = "maelstrom"
TITLE = "Maelstrom"

# pygbag names the payload after the folder it builds, whatever `--app_name`
# says, so the staging folder carries the name the page will look for.
STAGE = os.path.join(ROOT, "build", APP_NAME)
WEB = os.path.join(STAGE, "build", "web")
DIST = os.path.join(ROOT, "dist")
# everything the game reads at run time, and nothing else. pygbag.ini comes
# along only to keep pygbag from warning about its absence.
INCLUDE = ("main.py", "menu.py", "maelstrom", "settings", "assets", "pygbag.ini")
# left behind by a former build: pygbag reuses them instead of optimizing again
DROP = ("__pycache__", "*.pyc", "*-pygbag.*")
# audio shrunk to mono 22 kHz before packing (see shrink_audio)
AUDIO_EXT = (".ogg", ".mp3", ".wav", ".flac")

PAYLOADS = ("maelstrom.apk", "maelstrom.tar.gz")
EXPECTED = ("index.html", "favicon.png") + PAYLOADS
# already compressed: storing them costs no space and saves the deflate pass
STORED = PAYLOADS + ("favicon.png",)
# inside a payload every path starts with `assets/`, the home pygbag unpacks to
PREFIX = "assets/"
PACKED = ("main.py", "maelstrom/__init__.py", "settings/balance.py",
          "assets/favicon.png")


def stage():
    """Copies the files the browser build needs into an empty `build/maelstrom`."""
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE)
    for name in INCLUDE:
        source = os.path.join(ROOT, name)
        target = os.path.join(STAGE, name)
        if not os.path.exists(source):
            raise SystemExit(f"not found, cannot build: {source}")
        if os.path.isdir(source):
            shutil.copytree(source, target, ignore=shutil.ignore_patterns(*DROP))
        else:
            shutil.copy2(source, target)
    print("staged:", STAGE)


def shrink_audio():
    """Re-encode the staged soundtrack in place to mono 22 kHz, as pygbag would.

    pygbag only runs its ffmpeg pass when it builds on Linux (`optimizing.py`
    guards it with `sys.platform == "linux"`); on Windows it packs the tracks at
    full size. So we do that same step ourselves on the staging copy -- the very
    command pygbag uses, `ffmpeg -ac 1 -r 22000` -- which roughly halves the
    soundtrack and leaves the repository's assets untouched. Without ffmpeg the
    tracks are packed as they are and the build still works, just heavier.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("WARNING: ffmpeg not found, web soundtrack packed at full size")
        return
    before = after = 0
    for folder, _dirs, files in os.walk(os.path.join(STAGE, "assets")):
        for name in files:
            if not name.lower().endswith(AUDIO_EXT):
                continue
            src = os.path.join(folder, name)
            tmp = os.path.join(folder, name + ".tmp.ogg")
            dst = os.path.splitext(src)[0] + ".ogg"
            before += os.path.getsize(src)
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", src,
                 "-ac", "1", "-r", "22000", tmp],
                check=True,
            )
            os.replace(tmp, dst)
            if dst != src:          # a .mp3/.wav/.flac source became a .ogg
                os.remove(src)
            after += os.path.getsize(dst)
    if before:
        print(f"soundtrack: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")


def build():
    """Runs pygbag on the staging copy. Writes `build/web` inside it.

    The custom synthwave loading page (`loader.tmpl`, beside this script) is
    copied into the staging folder so pygbag, launched there, finds it as a
    local template instead of fetching its generic default from the CDN.
    """
    template = os.path.join(STAGE, "loader.tmpl")
    shutil.copy2(os.path.join(HERE, "loader.tmpl"), template)
    # The default gate (--ume_block 1) is kept on purpose: browsers block audio
    # until a user gesture, so pygbag waits for one before running. The loading
    # page invites that click upfront ("click to play"), so the gesture usually
    # lands while the payload is still downloading -- the menu then appears with
    # its music already unlocked, instead of behind a separate prompt screen.
    subprocess.run(
        [sys.executable, "-m", "pygbag", "--build",
         "--title", TITLE,
         "--template", "loader.tmpl",
         "--icon", "assets/favicon.png", "."],
        cwd=STAGE, check=True,
    )


def verify():
    """Checks the page, its two payloads, and what the payload carries.

    The browser build cannot run itself the way the desktop packages do
    (`main.py --verification`), so this is its self-check: the game modules
    have to be in there, and nothing else -- a `docs` or `.venv` in the list
    would mean the build was pointed at the repository again.
    """
    for name in EXPECTED:
        path = os.path.join(WEB, name)
        if not os.path.isfile(path):
            print("missing from the build:", path, file=sys.stderr)
            return False

    with tarfile.open(os.path.join(WEB, "maelstrom.tar.gz")) as tar:
        names = [name for name in tar.getnames() if name.startswith(PREFIX)]

    packed = {name[len(PREFIX):] for name in names}
    missing = [name for name in PACKED if name not in packed]
    if missing:
        print("missing from the payload:", ", ".join(missing), file=sys.stderr)
        return False

    tops = {name.split("/")[0] for name in packed}
    unwanted = sorted(tops - set(INCLUDE))
    if unwanted:
        print("unexpected in the payload:", ", ".join(unwanted), file=sys.stderr)
        return False

    print(f"payload: {len(names)} files, {', '.join(sorted(tops))}")
    return True


def pack(version):
    """Zips `build/web` flat into `dist`. Returns the archive path."""
    os.makedirs(DIST, exist_ok=True)
    archive = os.path.join(DIST, f"Maelstrom-{version}-web.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(os.listdir(WEB)):
            path = os.path.join(WEB, name)
            if not os.path.isfile(path):
                continue
            method = zipfile.ZIP_STORED if name in STORED else zipfile.ZIP_DEFLATED
            zf.write(path, name, compress_type=method)
            print(f"    {name:20} {os.path.getsize(path) / 1e6:7.1f} MB")
    return archive


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "dev"
    stage()
    shrink_audio()
    build()
    if not verify():
        return 1
    archive = pack(version)
    print(f"web archive: {archive} ({os.path.getsize(archive) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
