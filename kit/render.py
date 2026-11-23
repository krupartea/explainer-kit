"""Render a video's scenes (scenes.py) in parallel, then build per-scene contact sheets for visual QA.

    python -m kit.render <video dir> [S01 S02 ...] [--preview] [--jobs 4]

--preview: 854x480 @15 fps into media_preview/ (fast layout check). Default: 1920x1080 @30 fps into media/.
Contact sheets: qa/sheets/<scene>.png, one frame at the end of every beat (2 columns), so each
beat's final layout can be inspected as an image.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE = Path(os.environ.get("EXPLAINER_CACHE", Path.home() / ".cache" / "explainer-kit"))
MANIM = CACHE / "venvs" / "kit" / "bin" / "manim"
KIT = Path(__file__).resolve().parent.parent


def manim_star_names() -> set[str]:
    ns: dict = {}
    exec("from manim import *", ns)
    return {n for n in ns if not n.startswith("_")}


def lint_scenes(path: Path) -> list[str]:
    """Name-clash rules for scenes.py, checked statically (so a clash can't render silently):
    1. the kit is used as `import kit` (kit.<name>); `from kit import *`, `import kit as x`, and rebinding
       `kit` anywhere are errors;
    2. no module-level name may shadow a name `from manim import *` brought in (it would change every scene);
    3. Manim classes and constants (CamelCase / UPPER: Line, UP) may not be rebound anywhere.
    Local lowercase names may shadow Manim utilities (frame, color, smooth): that stays inside one function."""
    import ast
    star = manim_star_names()
    tree = ast.parse(path.read_text())
    hits = []

    def bad(name, line, why):
        hits.append(f"{path.name}:{line}: '{name}' {why}")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "kit" and any(a.name == "*" for a in node.names):
            bad("from kit import *", node.lineno, "is not allowed; use `import kit` and kit.<name>")
        if isinstance(node, ast.Import) and any(a.name == "kit" and a.asname for a in node.names):
            bad("import kit as ...", node.lineno, "is not allowed; use `import kit` (a short alias is clash-prone)")
    for stmt in tree.body:                                              # rule 2: module level
        names = []
        if isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            names = [stmt.name]
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            names = [(a.asname or a.name).split(".")[0] for a in stmt.names if a.name != "*"]
        else:
            names = [n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)]
        for n in names:
            if n in star and not (isinstance(stmt, ast.Import) and n in ("np", "numpy")):
                bad(n, stmt.lineno, "at module level shadows a Manim name; rename it")
    for node in ast.walk(tree):                                         # rules 1 and 3: anywhere
        bound = []
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound = [node.id]
        elif isinstance(node, ast.arg):
            bound = [node.arg]
        for n in bound:
            if n == "kit":
                bad(n, node.lineno, "rebinds the kit namespace")
            elif n in star and (n[0].isupper()):
                bad(n, node.lineno, "rebinds a Manim class/constant")
    return sorted(set(hits))


def scene_ids(vdir: Path) -> list[str]:
    return list(json.loads((vdir / "timing.json").read_text()))


def render_one(vdir: Path, sid: str, preview: bool) -> tuple[str, int, Path]:
    media = vdir / ("media_preview" if preview else "media") / sid
    shutil.rmtree(media, ignore_errors=True)
    q = ["-r", "854,480", "--fps", "15"] if preview else ["-r", "1920,1080", "--fps", "30"]
    log = vdir / "logs" / f"render_{sid}{'_preview' if preview else ''}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, VID_DIR=str(vdir), PYTHONPATH=f"{KIT}:{os.environ.get('PYTHONPATH', '')}")
    with open(log, "w") as fh:
        rc = subprocess.run([str(MANIM), *q, "--disable_caching", "--media_dir", str(media), str(vdir / "scenes.py"),
                             sid], cwd=vdir, env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
    for pm in media.glob("**/partial_movie_files"):
        shutil.rmtree(pm, ignore_errors=True)
    return sid, rc, log


def contact_sheet(vdir: Path, sid: str, preview: bool) -> Path:
    from kit.assemble import find_scene_mp4

    mp4 = find_scene_mp4(vdir / ("media_preview" if preview else "media") / sid, sid)
    beats = json.loads((vdir / "logs" / f"{sid}.json").read_text())["beats"]
    out = vdir / "qa" / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for k, b in enumerate(beats):
        t = b["start"] + b["dur"] + 0.25
        f = out / f"_{sid}_{k}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", "-vf",
                        f"scale=640:360,drawtext=fontfile=/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf:"
                        f"text='{sid} beat {k}':x=8:y=8:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6",
                        str(f)], check=True)
        frames.append(f)
    if len(frames) % 2:
        frames.append(frames[-1])
    rows = len(frames) // 2
    inputs = sum([["-i", str(f)] for f in frames], [])
    layout = "|".join(f"{(i % 2) * 640}_{(i // 2) * 360}" for i in range(len(frames)))
    sheet = out / f"{sid}.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex",
                    f"xstack=inputs={len(frames)}:layout={layout}" if len(frames) > 1 else "null", str(sheet)],
                   check=True)
    for f in set(frames):
        f.unlink()
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("vdir", type=Path)
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    vdir = a.vdir.resolve()
    clash = lint_scenes(vdir / "scenes.py")
    if clash:
        sys.exit("scenes.py lint failed:\n" + "\n".join(clash))
    sids = a.scenes or scene_ids(vdir)
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda s: render_one(vdir, s, a.preview), sids))
    failed = [(s, log) for s, rc, log in results if rc]
    for s, log in failed:
        tail = log.read_text().splitlines()[-25:]
        print(f"--- {s} FAILED ({log})\n" + "\n".join(tail), file=sys.stderr)
    warn = [l for s, rc, log in results if not rc for l in log.read_text().splitlines() if l.startswith("WARNING S")]
    sheets = [contact_sheet(vdir, s, a.preview) for s, rc, _ in results if not rc]
    issues = []
    for s, rc, _ in results:
        lf = vdir / "logs" / f"{s}.layout.json"
        if rc or not lf.exists():
            continue
        spans: dict[str, list[int]] = {}                   # an issue that persists is reported once, with its beats
        for beat, msgs in json.loads(lf.read_text()).items():
            for msg in msgs:
                spans.setdefault(msg, []).append(int(beat))
        for msg, beats in spans.items():
            b = sorted(beats)
            where = f"{b[0]}" if len(b) == 1 else f"{b[0]}-{b[-1]}" if b == list(range(b[0], b[-1] + 1)) else \
                ",".join(map(str, b))
            issues.append(f"{s}:{where} {msg}")
    (vdir / "qa").mkdir(exist_ok=True)
    (vdir / "qa" / "layout.md").write_text("# Layout check (end of each beat)\n\n" +
                                           ("\n".join(f"- {i}" for i in issues) or "No issues.") + "\n")
    print("\n".join(warn))
    print(f"layout issues: {len(issues)}" + "".join(f"\n  {i}" for i in issues))
    print("contact sheets (look once per scene, to judge the picture):\n" + "\n".join(str(p) for p in sheets))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
