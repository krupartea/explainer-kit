"""Join rendered scenes into one MP4 (audio padded to each scene's video length) plus an SRT sidecar.

    python -m kit.assemble <video dir> S00 S01 ...     # scenes rendered by kit.render into <video dir>/media/<S>

Subtitles are NOT burned in; the .srt sits next to the .mp4 with the same stem, so players pick it up.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-2000:]}")


def vdur(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_cue(text: str, start: float, end: float, width: int = 62):
    """One cue of <= 2 lines; longer text is split at a sentence break into time-proportional cues."""
    if len(text) <= width:
        return [(start, end, text)]
    if len(text) <= 2 * width:
        spaces = [i for i, ch in enumerate(text) if ch == " "]
        cut = min(spaces, key=lambda i: abs(i - len(text) / 2))
        return [(start, end, text[:cut] + "\n" + text[cut + 1:])]
    cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in ".:;?!," and text[i + 1] == " "]
    cut = min(cuts, key=lambda i: abs(i - len(text) / 2)) if cuts else len(text) // 2
    a, b = text[:cut].strip(), text[cut:].strip()
    mid = start + (end - start) * len(a) / (len(a) + len(b))
    return split_cue(a, start, mid, width) + split_cue(b, mid, end, width)


def find_scene_mp4(media: Path, sid: str) -> Path:
    hits = sorted(media.glob(f"**/{sid}.mp4"), key=lambda p: p.stat().st_mtime)
    hits = [h for h in hits if "partial_movie_files" not in h.parts]
    if not hits:
        raise FileNotFoundError(f"no render for {sid} under {media}")
    return hits[-1]


def assemble(parts: list[tuple[Path, Path]], out_mp4: Path, out_srt: Path, work: Path,
             overlays: list[tuple[str, float, float]] | None = None) -> float:
    """parts: [(scene mp4, beat log json)]. overlays: [(text, t0, t1)] drawn bottom-right (re-encodes video)."""
    work.mkdir(parents=True, exist_ok=True)
    cues, offset, norm = [], 0.0, []
    for mp4, logf in parts:
        d = vdur(mp4)
        n = work / f"norm_{mp4.stem}.mp4"
        run(["ffmpeg", "-y", "-i", str(mp4), "-filter_complex", "[0:a]aresample=48000,apad[a]", "-map", "0:v",
             "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{d:.3f}", str(n)])
        for b in json.loads(Path(logf).read_text())["beats"]:
            s0 = offset + b["start"]
            cues += split_cue(b["text"], s0, s0 + b["dur"])
        norm.append(n)
        offset += d
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    out_srt.write_text("".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues)))
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in norm))
    if not overlays:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart",
             str(out_mp4)])
        return offset
    font = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
    draws = ",".join(
        f"drawtext=fontfile={font}:text='{t}':x=w-tw-36:y=h-th-28:fontsize=28:fontcolor=white@0.85:"
        f"box=1:boxcolor=0x000000@0.45:boxborderw=12:enable='between(t,{a:.2f},{b:.2f})'"
        for t, a, b in overlays)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", draws, "-c:v", "libx264", "-crf", "18",
         "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out_mp4)])
    return offset


if __name__ == "__main__":
    vdir = Path(sys.argv[1])
    sids = sys.argv[2:]
    parts = [(find_scene_mp4(vdir / "media" / s, s), vdir / "logs" / f"{s}.json") for s in sids]
    stem = vdir.name
    total = assemble(parts, vdir / f"{stem}.mp4", vdir / f"{stem}.srt", vdir / "work")
    print(f"{vdir / (stem + '.mp4')}: {total:.1f}s")
