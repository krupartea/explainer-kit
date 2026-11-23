"""vid: the explainer-kit command line (scripts/vid wraps this in the kit venv + memory cap).

    vid doctor                         check the toolchain; prints what is missing
    vid new <slug>                     create ~/explainers/<date>-<slug>/ with templates; prints the path
    vid narrate <dir> [--scenes S01,S02]   narration.txt -> audio + timing.json + qa/narration_qa.md
    vid render <dir> [S01 ...] [--preview] render scenes.py; writes qa/sheets/<scene>.png
    vid assemble <dir>                 join scenes -> <dir>/<slug>.mp4 + <slug>.srt (no burned-in subtitles)
    vid frame <dir> <when>... [--preview]  PNG of any moment -> qa/frames/. when: S03@2.5 (scene time) or
                                       1:23 / 83.5 (time in the assembled video)
    vid feedback <slug> "<text>"       append the user's words verbatim to the feedback log
    vid link-chat <dir>                record which conversation (and workspace) requested this video
    vid convo <dir> <regex> | --user   search that conversation's messages (no tool output), compactly
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


def _slug(vdir: Path) -> str:
    return vdir.name.split("-", 3)[-1] if vdir.name[:4].isdigit() else vdir.name


def link_chat(vdir: Path) -> int:
    """Find the transcript of the conversation that ran `vid new <slug>` for this folder."""
    vdir = vdir.resolve()
    needle = f"vid new {_slug(vdir)}"
    hits = []
    for f in (Path.home() / ".claude" / "projects").glob("*/*.jsonl"):
        try:
            if needle in f.read_text(errors="ignore"):
                hits.append(f)
        except OSError:
            pass
    if not hits:
        print(f"no transcript contains '{needle}'")
        return 1
    tr = max(hits, key=lambda p: p.stat().st_mtime)
    cwd = None
    for line in tr.read_text(errors="ignore").splitlines()[::-1]:
        try:
            cwd = json.loads(line).get("cwd")
        except ValueError:
            continue
        if cwd:
            break
    (vdir / "chat.json").write_text(json.dumps({"transcript": str(tr), "workspace": cwd}, indent=1))
    print(f"transcript: {tr}\nworkspace: {cwd}")
    return 0


def _messages(tr: Path):
    """(index, role, text) for the user's own words and the assistant's prose; tool traffic is skipped."""
    i = 0
    for line in tr.read_text(errors="ignore").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") not in ("user", "assistant") or d.get("isSidechain"):
            continue
        c = d.get("message", {}).get("content")
        texts = [c] if isinstance(c, str) else [x.get("text", "") for x in (c or [])
                                                 if isinstance(x, dict) and x.get("type") == "text"]
        for t in texts:
            if not t.strip() or t.lstrip().startswith(("<system-reminder", "Base directory for this skill",
                                                        "<command-", "[SYSTEM NOTIFICATION", "<task-notification")):
                continue
            i += 1
            yield i, d["type"], t


def convo(vdir: Path, args: list[str]) -> int:
    import re
    meta = vdir.resolve() / "chat.json"
    if not meta.exists():
        print("no chat.json: the requesting conversation wasn't linked (vid link-chat)")
        return 1
    tr = Path(json.loads(meta.read_text())["transcript"])
    out = []
    if args and args[0] == "--user":
        out = [f"[#{i}] {t.strip()[:500]}" for i, role, t in _messages(tr) if role == "user"]
    elif args:
        rx = re.compile(" ".join(args), re.I)
        for i, role, t in _messages(tr):
            for m in rx.finditer(t):
                a, b = max(0, m.start() - 200), min(len(t), m.end() + 200)
                out.append(f"[#{i} {role}] …{t[a:b].strip()}…")
                if len(out) >= 12:
                    break
            if len(out) >= 12:
                break
    else:
        print("usage: vid convo <dir> <regex> | --user")
        return 2
    text = "\n".join(out)
    print(text[:9000] + ("\n[truncated: narrow the pattern]" if len(text) > 9000 else "") if out else "no matches")
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
    if cmd == "link-chat":
        return link_chat(Path(rest[0]))
    if cmd == "convo":
        return convo(Path(rest[0]), rest[1:])
    if cmd == "feedback":
        return feedback(rest[0], " ".join(rest[1:]))
    print(f"unknown command {cmd}\n{__doc__}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
