"""Render a video (video.py: one continuous scene, class Video), then build contact sheets for visual QA.

    python -m kit.render <video dir> [--preview]

--preview: 854x480 @15 fps into media_preview/. Default: 1920x1080 @30 fps into media/.
Manim's cache is on: an edit re-renders only the animations whose picture changed (kit/manim.cfg).
Contact sheets: qa/sheets/<chapter>.png, a frame every SAMPLE_EVERY seconds of the chapter (2 columns).
Older videos with one file per scene (scenes/<id>.py or scenes.py) still render scene by scene.
"""
from __future__ import annotations

import argparse
import json
import os
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
    """Name-clash rules for a scene file, checked statically (so a clash can't render silently):
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
    if (vdir / "video.py").exists():
        return ["Video"]
    return list(json.loads((vdir / "timing.json").read_text()))


def scene_file(vdir: Path, sid: str) -> Path:
    """video.py (one continuous scene); older videos: scenes/<id>.py per scene, or a single scenes.py."""
    if (vdir / "video.py").exists():
        return vdir / "video.py"
    per = vdir / "scenes" / f"{sid}.py"
    if per.exists():
        return per
    if (vdir / "scenes.py").exists():
        return vdir / "scenes.py"
    raise FileNotFoundError(f"no scene file for {sid}: expected {per}")


def render_one(vdir: Path, sid: str, preview: bool) -> tuple[str, int, Path]:
    media = vdir / ("media_preview" if preview else "media") / sid
    q = ["-r", "854,480", "--fps", "15"] if preview else ["-r", "1920,1080", "--fps", "30"]
    log = vdir / "logs" / f"render_{sid}{'_preview' if preview else ''}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, VID_DIR=str(vdir),
               PYTHONPATH=f"{KIT}:{vdir / 'scenes'}:{os.environ.get('PYTHONPATH', '')}")
    with open(log, "w") as fh:
        rc = subprocess.run([str(MANIM), "-c", str(KIT / "kit" / "manim.cfg"), *q, "--media_dir", str(media),
                             str(scene_file(vdir, sid)), sid], cwd=vdir, env=env, stdout=fh,
                            stderr=subprocess.STDOUT).returncode
    return sid, rc, log


def _sheet(frames: list[Path], sheet: Path) -> Path:
    if len(frames) % 2:
        frames = frames + [frames[-1]]
    inputs = sum([["-i", str(f)] for f in frames], [])
    layout = "|".join(f"{(i % 2) * 640}_{(i // 2) * 360}" for i in range(len(frames)))
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex",
                    f"xstack=inputs={len(frames)}:layout={layout}" if len(frames) > 1 else "null", str(sheet)],
                   check=True)
    return sheet


def contact_sheets(vdir: Path, sid: str, preview: bool) -> list[Path]:
    """One sheet per chapter: a frame every SAMPLE_EVERY seconds, plus the chapter's last moment."""
    from kit.assemble import find_scene_mp4
    from kit.scene import SAMPLE_EVERY

    mp4 = find_scene_mp4(vdir / ("media_preview" if preview else "media") / sid, sid)
    log = json.loads((vdir / "logs" / f"{sid}.json").read_text())
    spans: dict[str, list[float]] = {}
    for b in log["beats"]:
        spans.setdefault(b.get("chapter", sid), [b["start"], b["start"]])
    order = list(spans)
    for i, c in enumerate(order):
        spans[c][1] = spans[order[i + 1]][0] if i + 1 < len(order) else log["end"]
    out = vdir / "qa" / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    sheets = []
    for c, (t0, t1) in spans.items():
        times = [t0 + 0.5 + k * SAMPLE_EVERY for k in range(int(max(0.0, t1 - t0 - 1.0) // SAMPLE_EVERY) + 1)]
        if t1 - 0.2 - times[-1] > 1.0:                       # the chapter's last moment, unless just sampled
            times.append(t1 - 0.2)
        frames = []
        for k, t in enumerate(times):
            f = out / f"_{c}_{k}.png"
            mm, ss = divmod(int(t), 60)
            label = f"{c} +{t - t0:.0f}s   video {mm}m{ss:02d}s"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(mp4), "-frames:v", "1", "-vf",
                            f"scale=640:360,drawtext=fontfile=/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf:"
                            f"text='{label}':x=8:y=8:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6",
                            str(f)], check=True)
            frames.append(f)
        sheets.append(_sheet(frames, out / f"{c}.png"))
        for f in set(frames):
            f.unlink()
    return sheets


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("vdir", type=Path)
    ap.add_argument("scenes", nargs="*", help="older per-scene videos only: which scenes")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--jobs", type=int, default=4, help="older per-scene videos only: scenes rendered at once")
    a = ap.parse_args(argv)
    vdir = a.vdir.resolve()
    sids = scene_ids(vdir) if (vdir / "video.py").exists() else (a.scenes or scene_ids(vdir))
    files = sorted({scene_file(vdir, s) for s in sids} | ({vdir / "scenes" / "common.py"}
                                                          if (vdir / "scenes" / "common.py").exists() else set()))
    clash = [c for f in files for c in lint_scenes(f)]
    if clash:
        sys.exit("scene lint failed:\n" + "\n".join(clash))
    with ThreadPoolExecutor(a.jobs) as ex:
        results = list(ex.map(lambda s: render_one(vdir, s, a.preview), sids))
    failed = [(s, log) for s, rc, log in results if rc]
    for s, log in failed:
        tail = log.read_text().splitlines()[-25:]
        print(f"--- {s} FAILED ({log})\n" + "\n".join(tail), file=sys.stderr)
    warn = [l for s, rc, log in results if not rc for l in log.read_text().splitlines() if l.startswith("WARNING ")]
    sheets = [p for s, rc, _ in results if not rc for p in contact_sheets(vdir, s, a.preview)]
    issues = []
    for s in scene_ids(vdir):
        lf = vdir / "logs" / f"{s}.layout.json"
        if not lf.exists():
            continue
        spans: dict[str, list[str]] = {}                  # an issue that persists is reported once, with where
        for where, msgs in json.loads(lf.read_text()).items():
            for msg in msgs:
                spans.setdefault(msg, []).append(str(where))
        for msg, ws in spans.items():
            where = ws[0] if len(ws) == 1 else f"{ws[0]} … {ws[-1]} ({len(ws)} checks)"
            issues.append(f"{where} {msg}")
    (vdir / "qa").mkdir(exist_ok=True)
    (vdir / "qa" / "layout.md").write_text("# Layout check (beat ends and every few seconds)\n\n" +
                                           ("\n".join(f"- {i}" for i in issues) or "No issues.") + "\n")
    print("\n".join(warn))
    print(f"layout issues: {len(issues)}" + "".join(f"\n  {i}" for i in issues))
    print("contact sheets (one per chapter):\n" + "\n".join(str(p) for p in sheets))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
