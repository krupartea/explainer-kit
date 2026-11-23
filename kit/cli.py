"""vid: the explainer-kit command line (scripts/vid wraps this in the kit venv + memory cap).

    vid doctor                         check the toolchain; prints what is missing
    vid new <slug>                     create ~/explainers/<date>-<slug>/ with templates; prints the path
    vid narrate <dir> [--scenes S01,S02]   narration.txt -> audio + timing.json + qa/narration_qa.md
    vid render <dir> [S01 ...] [--preview] render scenes.py; writes qa/sheets/<scene>.png
    vid assemble <dir>                 join scenes -> <dir>/<slug>.mp4 + <slug>.srt (no burned-in subtitles)
    vid frame <dir> <when>... [--preview]  PNG of any moment -> qa/frames/. when: S03@2.5 (scene time) or
                                       1:23 / 83.5 (time in the assembled video)
    vid feedback <slug> "<text>"       append the user's words verbatim to the feedback log
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("EXPLAINER_CACHE", Path.home() / ".cache" / "explainer-kit"))
VIDEOS = Path(os.environ.get("EXPLAINER_VIDEOS", Path.home() / "explainers"))
FEEDBACK = CACHE / "feedback"


def doctor() -> int:
    import yaml

    cfg = yaml.safe_load((KIT / "config.yaml").read_text())
    eng = cfg["engine"]
    checks = [
        ("ffmpeg", shutil.which("ffmpeg") is not None, "sudo apt install ffmpeg"),
        ("kit venv", (CACHE / "venvs/kit/bin/manim").exists(), f"{KIT}/scripts/setup.sh"),
        (f"engine venv ({eng})", (CACHE / f"venvs/{eng}/bin/python").exists(), f"{KIT}/scripts/setup.sh"),
        ("setup done", (CACHE / ".setup-ok").exists(), f"{KIT}/scripts/setup.sh"),
        ("Ubuntu fonts", Path("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf").exists(), "sudo apt install fonts-ubuntu"),
    ]
    soft = [("LaTeX (real math)", shutil.which("latex") is not None and shutil.which("dvisvgm") is not None,
             "sudo apt install texlive-latex-extra texlive-fonts-extra dvisvgm  (until then kit.tex() falls back to mono text)")]
    free = shutil.disk_usage(Path.home()).free / 2**30
    soft.append((f"disk free {free:.0f} GB", free > 5, "free space: a video needs ~1-2 GB while rendering"))
    bad = 0
    for name, ok, fix in checks:
        print(f"{'ok ' if ok else 'MISSING'}  {name}" + ("" if ok else f"   -> {fix}"))
        bad += not ok
    for name, ok, fix in soft:
        print(f"{'ok ' if ok else 'warn'}  {name}" + ("" if ok else f"   -> {fix}"))
    print(f"engine: {eng}   videos: {VIDEOS}   feedback log: {FEEDBACK}")
    return 1 if bad else 0


def new(slug: str) -> int:
    d = VIDEOS / f"{dt.date.today().isoformat()}-{slug}"
    if d.exists():
        print(d)
        return 0
    shutil.copytree(KIT / "templates" / "video", d)
    print(d)
    return 0


def assemble(vdir: Path) -> int:
    from kit.assemble import assemble as join, find_scene_mp4

    vdir = vdir.resolve()
    sids = list(json.loads((vdir / "timing.json").read_text()))
    parts = [(find_scene_mp4(vdir / "media" / s, s), vdir / "logs" / f"{s}.json") for s in sids]
    stem = vdir.name.split("-", 3)[-1] if vdir.name[:4].isdigit() else vdir.name
    total = join(parts, vdir / f"{stem}.mp4", vdir / f"{stem}.srt", vdir / "work")
    shutil.rmtree(vdir / "work", ignore_errors=True)
    print(f"{vdir / (stem + '.mp4')}  ({total / 60:.1f} min)\n{vdir / (stem + '.srt')}")
    return 0


def frame(vdir: Path, whens: list[str], preview: bool) -> int:
    import subprocess
    from kit.assemble import find_scene_mp4

    vdir = vdir.resolve()
    out = vdir / "qa" / "frames"
    out.mkdir(parents=True, exist_ok=True)
    stem = vdir.name.split("-", 3)[-1] if vdir.name[:4].isdigit() else vdir.name
    for w in whens:
        if "@" in w:
            sid, t = w.split("@")
            src = find_scene_mp4(vdir / ("media_preview" if preview else "media") / sid, sid)
        else:
            t = sum(float(x) * 60 ** i for i, x in enumerate(reversed(w.split(":"))))
            src = vdir / f"{stem}.mp4"
        png = out / f"{w.replace(':', 'm').replace('@', '_at_')}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1", str(png)],
                       check=True)
        print(png)
    return 0


def feedback(slug: str, text: str) -> int:
    FEEDBACK.mkdir(parents=True, exist_ok=True)
    f = FEEDBACK / f"{slug}.md"
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(f, "a") as fh:
        if fh.tell() == 0:
            fh.write(f"# Feedback: {slug}\n\nVerbatim user feedback, newest last. Generalized into the kit only "
                     f"in the explainer-kit development chat.\n")
        fh.write(f"\n## {stamp}\n\n{text.strip()}\n")
    print(f)
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "doctor":
        return doctor()
    if cmd == "new":
        return new(rest[0])
    if cmd == "narrate":
        from kit import narrate
        vdir = Path(rest[0]).resolve()
        return narrate.main([str(vdir / "narration.txt"), "--out", str(vdir), *rest[1:]]) or 0
    if cmd == "render":
        from kit import render
        return render.main(rest) or 0
    if cmd == "assemble":
        return assemble(Path(rest[0]))
    if cmd == "frame":
        return frame(Path(rest[0]), [r for r in rest[1:] if r != "--preview"], "--preview" in rest)
    if cmd == "feedback":
        return feedback(rest[0], " ".join(rest[1:]))
    print(f"unknown command {cmd}\n{__doc__}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
