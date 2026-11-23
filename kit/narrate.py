"""Narration file -> per-beat WAVs + timing.json (with sync anchors) + QA report.

    python -m kit.narrate <narration.txt> --out <video dir> [--engine qwen] [--scenes S01,S02] [--no-lint]

Steps: parse + lint markup -> synthesize with the engine in its own venv (one GPU process) ->
join [pause] parts, trim, loudness-match -> faster-whisper word timestamps (anchors + QA diff).
Outputs in <out>: audio/<scene>_<beat>.wav, timing.json, qa/narration_qa.md
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from kit import markup

KIT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("EXPLAINER_CACHE", Path.home() / ".cache" / "explainer-kit"))
SR = 48000
GAP = 0.45          # silence after each beat, seconds
ERR_FLAG = 0.12     # QA: flag beats whose character error rate (spaces ignored) exceeds this


def config() -> dict:
    return yaml.safe_load((KIT / "config.yaml").read_text())


def _resample(a: np.ndarray, sr: int) -> np.ndarray:
    if sr == SR:
        return a
    n = int(round(len(a) * SR / sr))
    return np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)


def _trim(a: np.ndarray, thr_db=-45.0, keep=0.06) -> tuple[np.ndarray, float]:
    """Trim leading/trailing silence, keeping `keep` seconds of margin. -> (audio, seconds cut at the start)."""
    win = int(0.01 * SR)
    if len(a) < win * 3:
        return a, 0.0
    frames = a[: len(a) // win * win].reshape(-1, win)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)
    on = np.where(db > thr_db)[0]
    if not len(on):
        return a, 0.0
    s = max(0, on[0] * win - int(keep * SR))
    e = min(len(a), (on[-1] + 1) * win + int(keep * SR))
    return a[s:e], s / SR


def _match_loudness(a: np.ndarray, target_db=-20.0) -> np.ndarray:
    rms = np.sqrt(np.mean(a[np.abs(a) > 1e-4] ** 2)) if np.any(np.abs(a) > 1e-4) else 0
    if rms <= 0:
        return a
    a = a * (10 ** (target_db / 20) / rms)
    peak = np.max(np.abs(a))
    return a * (0.97 / peak) if peak > 0.97 else a


def synthesize(scenes, engine: str, out: Path, voice: dict) -> None:
    eng_dir = KIT / "tts" / "engines" / engine
    venv_py = CACHE / "venvs" / engine / "bin" / "python"
    raw = out / "audio" / "raw" / engine
    job = {"out_dir": str(raw), "voice": voice, "items": []}
    for beats in scenes.values():
        for b in beats:
            for i, p in enumerate(b.parts):
                text, params = markup.compile_part(b, p, engine)
                job["items"].append({"id": f"{b.scene}_{b.index:02d}_{i}", "text": text, "params": params})
    raw.mkdir(parents=True, exist_ok=True)
    jf = raw / "job.json"
    jf.write_text(json.dumps(job, indent=1))
    cmd = [str(venv_py), "synth.py", str(jf)]
    safe = KIT / "scripts" / "safe_run.sh"
    env = dict(os.environ, MEM=os.environ.get("MEM", "12G"))
    subprocess.run([str(safe), *cmd], cwd=eng_dir, check=True, env=env)
    for beats in scenes.values():
        for b in beats:
            chunks, words, t = [], [], 0.0
            for i, p in enumerate(b.parts):
                stem = raw / f"{b.scene}_{b.index:02d}_{i}"
                a, sr = sf.read(stem.with_suffix(".wav"), dtype="float32")
                a, cut = _trim(_resample(a if a.ndim == 1 else a.mean(1), sr))
                wf = stem.with_suffix(".words.json")
                if wf.exists():  # exact word times from the engine (kokoro), shifted into the beat's timeline
                    words.append([[w, t + s0 - cut, t + s1 - cut] for w, s0, s1 in json.loads(wf.read_text())])
                chunks += [a, np.zeros(int(p.pause_after * SR), np.float32)]
                t += (len(a) + int(p.pause_after * SR)) / SR
            dst = out / "audio" / f"{b.scene}_{b.index:02d}"
            sf.write(dst.with_suffix(".wav"), _match_loudness(np.concatenate(chunks)), SR)
            if len(words) == len(b.parts):
                dst.with_suffix(".words.json").write_text(json.dumps(words))
            else:
                dst.with_suffix(".words.json").unlink(missing_ok=True)


# ---------------- alignment + QA ----------------
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _num(n: int) -> str:
    """Number words; tens join ("twentyfive") so "25" and "twenty-five" normalize alike."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _num(n % 100))
    is_year = (1100 <= n < 2000 and n % 100 != 0) or 2010 <= n < 2100  # nineteen fifty, twenty twentyeight
    if is_year:
        return _num(n // 100) + " " + _num(n % 100)
    if n < 1_000_000:
        return _num(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + _num(n % 1000))
    return " ".join(_ONES[int(d)] for d in str(n))


_SPELLING = {"centre": "center", "colour": "color", "behaviour": "behavior", "neighbour": "neighbor",
             "labelled": "labeled", "modelled": "modeled", "travelled": "traveled", "optimise": "optimize"}


def norm_words(text: str) -> list[str]:
    """Normalize so a script line and Whisper's spelling of the same speech compare equal:
    'AB12345' ~ 'A B, one two three four five'; 'SDK' ~ 'S D K'; '0 .58' ~ 'zero point five eight';
    'twenty-five' ~ '25'; 'reg-ex' ~ 'regex'; 'oh four' ~ '04'; centre ~ center."""
    text = text.replace("’", "'")
    text = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", text)       # AB12345 -> AB 12345
    text = re.sub(r"(\d)\s+\.(\d)", r"\1.\2", text)                          # whisper's "0 .58"
    text = re.sub(r"(\d+)\.(\d+)", lambda m: f" {_num(int(m.group(1)))} point "
                  f"{' '.join(_ONES[int(d)] for d in m.group(2))} ", text)
    text = re.sub(r"\d+", lambda m: " " + (" ".join(_ONES[int(d)] for d in m.group())   # IDs digit by digit
                                           if m.group()[0] == "0" or len(m.group()) >= 5
                                           else _num(int(m.group()))) + " ", text)
    text = text.lower().replace("/", " slash ")
    text = re.sub(r"[^a-z' ]+", " ", text)
    words = [_SPELLING.get(w, w) for w in (w.strip("'") for w in text.split()) if w]
    words = ["zero" if w == "oh" else w for w in words]
    out, run = [], []
    for w in words + [""]:                                                       # S D K / A B -> sdk / ab
        if len(w) == 1:
            run.append(w)
            continue
        if len(run) >= 2:
            out.append("".join(run))
        else:
            out += run
        run = []
        if w:
            out.append(w)
    return out


def _preload_cuda_libs():
    """CTranslate2 dlopens libcublas/libcudnn by soname; load the pip-installed copies first."""
    import ctypes
    import glob
    import nvidia.cublas.lib
    import nvidia.cudnn.lib
    for d in (nvidia.cublas.lib.__path__[0], nvidia.cudnn.lib.__path__[0]):
        for so in sorted(glob.glob(f"{d}/lib*.so.*")):
            try:
                ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


def _engine_anchor(engine_words, parts, pi, wi):
    """Start time of the wi-th spoken word of part pi, matched by text + occurrence in the engine's word list."""
    if pi >= len(parts) or pi >= len(engine_words):
        return None
    said = markup.WORD.findall(markup.spoken_plain(parts[pi].spoken))
    if wi >= len(said):
        return None
    target = markup._norm(said[wi])
    occ = sum(1 for w in said[:wi] if markup._norm(w) == target)
    hits = [w for w in engine_words[pi] if markup._norm(w[0]) == target]
    return hits[occ][1] if occ < len(hits) else None


def gpu_busy(min_mb=300) -> bool:
    """True when another process holds GPU compute memory (the display server is not a compute app)."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    me = os.getpid()
    return any(int(pid) != me and int(mb) >= min_mb
               for pid, mb in (l.split(", ") for l in out.strip().splitlines() if ", " in l))


def pick_device(cfg: dict) -> str:
    """config.yaml `gpu` (or $EXPLAINER_GPU): auto (default) uses CPU while another job holds the GPU; always; never."""
    mode = os.environ.get("EXPLAINER_GPU") or str(cfg.get("gpu", "auto"))
    if mode == "never":
        return "cpu"
    if mode == "auto" and gpu_busy():
        print("GPU busy with another job: narrating on CPU (slower, but nothing competes for the GPU)")
        return "cpu"
    return "cuda"


def _diff(ref: list[str], heard: list[str]):
    """Character error rate with spaces removed (so 'reg ex' ~ 'regex', 'speed up' ~ 'speed-up'), and whether
    the first and last expected words were heard (a dropped edge word barely moves the rate)."""
    r, h = "".join(ref), "".join(heard)
    sm = difflib.SequenceMatcher(a=r, b=h, autojunk=False)
    ops = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal")
    hit = [False] * len(r)
    for blk in sm.get_matching_blocks():
        hit[blk.a:blk.a + blk.size] = [True] * blk.size

    def covered(a, b):
        return b <= a or sum(hit[a:b]) / (b - a) >= 0.6

    edges_ok = not ref or (covered(0, len(ref[0])) and covered(len(r) - len(ref[-1]), len(r)))
    return ops / max(1, len(r)), edges_ok


_ANN = re.compile(r"\{([^|{}]+)\|([^|{}]*)(?:\|([^|{}]*))?\}")


def _lexicon_as_annotations(body: str, lex: dict) -> str:
    """Plain-text lexicon terms become {term|respelling} so QA can match either form."""
    parts = re.split(r"(\{[^{}]*\})", body)
    for term, say in sorted(lex.items(), key=lambda kv: -len(kv[0])):
        say = say.get("default") if isinstance(say, dict) else say
        if not say:
            continue
        pat = re.compile(rf"(?<![\w/{{|]){re.escape(term)}(?![\w/|}}])")
        parts = [p if p.startswith("{") else pat.sub(f"{{{term}|{say}}}", p) for p in parts]
        parts = re.split(r"(\{[^{}]*\})", "".join(parts))
    return "".join(parts)


def best_reference(raw: str, heard: list[str], lex: dict | None = None):
    """Whisper writes some annotated words in their on-screen form (AB12345, read) and others as spoken
    (zero point five eight seconds). Pick, per {shown|spoken} annotation, whichever form the transcript is
    closer to (greedy), and return (error rate, edges ok) for the best mix."""
    body = re.sub(r"\[[a-z]+(?: [0-9.]+)?\]|@[A-Za-z_][\w-]*\s*|\*", " ", raw)
    body = _lexicon_as_annotations(body, lex or {})
    anns = list(_ANN.finditer(body))

    def spoken(m):
        alts = [x for x in (m.group(2), m.group(3)) if x and not (x.startswith("/") and x.endswith("/"))]
        return alts[0] if alts else m.group(1)

    def text(choice):
        out, pos = [], 0
        for m, use_shown in zip(anns, choice):
            out += [body[pos:m.start()], m.group(1) if use_shown else spoken(m)]
            pos = m.end()
        return "".join(out + [body[pos:]])

    choice = [False] * len(anns)
    best = _diff(norm_words(text(choice)), heard)
    for k in range(len(anns)):
        trial = choice[:k] + [True] + choice[k + 1:]
        r = _diff(norm_words(text(trial)), heard)
        if r[0] < best[0]:
            choice, best = trial, r
    return (*best, word_changes(norm_words(text(choice)), heard))


def word_changes(ref: list[str], heard: list[str]) -> list[str]:
    """Word-level differences that are more than spacing ('left box' -> 'lift box', missing 'joined')."""
    out = []
    sm = difflib.SequenceMatcher(a=ref, b=heard, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a, b = " ".join(ref[i1:i2]), " ".join(heard[j1:j2])
        if tag == "equal" or re.sub("[ ']", "", a) == re.sub("[ ']", "", b):
            continue
        if max(len(w) for w in (ref[i1:i2] or heard[j1:j2])) < 3:   # a / the / of: whisper noise
            continue
        out.append(f"'{a}' heard as '{b}'" if a and b else (f"missing '{a}'" if a else f"extra '{b}'"))
    return out


def align_and_qa(scenes, out: Path, device="cuda", lex: dict | None = None, model_size="large-v3") -> dict:
    if device == "cuda":
        _preload_cuda_libs()
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type="float16" if device == "cuda" else "int8",
                         cpu_threads=8)
    timing, report = {}, ["# Narration QA", "", "Expected = what the voice was told to say. Flags: character error "
                          f"rate > {ERR_FLAG} (vs the closer of spoken / on-screen text, spellings normalized), "
                          "first or last word missing, anchor not found.", "",
                          "| beat | err | issues | expected | heard |", "|---|---|---|---|---|"]
    for sid, beats in scenes.items():
        timing[sid] = []
        for b in beats:
            wav = out / "audio" / f"{b.scene}_{b.index:02d}.wav"
            dur = round(sf.info(wav).duration, 3)
            pcm, sr = sf.read(wav, dtype="float32")  # pass PCM: manim pins an older PyAV than faster-whisper expects
            pcm16 = np.interp(np.arange(0, len(pcm), sr / 16000), np.arange(len(pcm)), pcm).astype(np.float32)
            segs, _ = model.transcribe(pcm16, language="en", word_timestamps=True, beam_size=5,
                                       condition_on_previous_text=False)  # no script prompt: it masks errors
            words = [w for s in segs for w in (s.words or [])]
            heard = " ".join(w.word.strip() for w in words)
            # expected spoken words with an index back to each part's word list (for anchors)
            exp, exp_key = [], []
            for pi, p in enumerate(b.parts):
                for wi, w in enumerate(markup.WORD.findall(markup.spoken_plain(p.spoken))):
                    for nw in norm_words(w) or [""]:
                        exp.append(nw)
                        exp_key.append((pi, wi))
            hw, h_idx = [], []
            for k, w in enumerate(words):
                for nw in norm_words(w.word):
                    hw.append(nw)
                    h_idx.append(k)
            sm = difflib.SequenceMatcher(a=exp, b=hw, autojunk=False)   # word alignment, for whisper anchors
            err, edges_ok, changes = best_reference(b.raw, norm_words(heard), lex)  # whole string: "0 .36" spans words
            err = round(err, 3)
            e2h = {}
            for blk in sm.get_matching_blocks():
                for j in range(blk.size):
                    e2h[blk.a + j] = h_idx[blk.b + j]
            anchors = {}
            ew = wav.with_suffix(".words.json")
            engine_words = json.loads(ew.read_text()) if ew.exists() else None
            for name, (pi, wi) in b.anchors.items():
                t_exact = _engine_anchor(engine_words, b.parts, pi, wi) if engine_words else None
                if t_exact is not None:
                    anchors[name] = round(t_exact, 3)
                    continue
                cands = [i for i, k in enumerate(exp_key) if k >= (pi, wi)]
                hit = next((e2h[i] for i in cands if i in e2h), None)
                anchors[name] = round(words[hit].start, 3) if hit is not None else None
            issues = ([f"err {err:.2f}"] if err > ERR_FLAG else []) + ([] if edges_ok else ["first/last word missing"]) \
                + changes[:4] \
                + [f"anchor @{k} not found" for k, v in anchors.items() if v is None]
            timing[sid].append({"wav": str(wav), "dur": dur, "gap": GAP, "text": b.shown, "mood": b.mood,
                                "anchors": anchors, "err": err, "issues": issues, "heard": heard})
            flag = " ⚠" if issues else ""
            spoken = " / ".join(markup.spoken_plain(p.spoken) for p in b.parts)
            report.append(f"| {sid}:{b.index}{flag} | {err:.2f} | {'; '.join(issues)} | {spoken} | {heard} |")
    (out / "qa").mkdir(exist_ok=True)
    (out / "qa" / "narration_qa.md").write_text("\n".join(report) + "\n")
    return timing


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("narration", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--engine", default=None)
    ap.add_argument("--voice", default=None, help="JSON overriding the engine's default voice settings")
    ap.add_argument("--scenes", default=None, help="comma list: only (re)synthesize these scenes")
    ap.add_argument("--lexicon", type=Path, default=KIT / "lexicon.yaml")
    ap.add_argument("--no-lint", action="store_true")
    ap.add_argument("--skip-tts", action="store_true", help="re-run alignment/QA only")
    a = ap.parse_args(argv)
    cfg = config()
    engine = a.engine or cfg["engine"]
    voice = dict(cfg["voices"][engine])
    voice.update(json.loads(a.voice) if a.voice else {})
    for k, v in voice.items():
        if isinstance(v, str) and v.startswith("~"):
            voice[k] = str(Path(v).expanduser())
    lex = markup.load_lexicon(a.lexicon)
    lex.update(markup.load_lexicon(a.out / "lexicon.yaml"))  # the video's own terms win
    scenes = markup.parse_file(a.narration, engine, lex)
    order = list(scenes)                                     # timing.json follows narration.txt, nothing stale
    problems = [p for bs in scenes.values() for b in bs for p in markup.lint_beat(b)]
    if problems and not a.no_lint:
        sys.exit("markup lint failed:\n" + "\n".join(problems))
    for w in markup.lint_warnings(scenes):
        print("lint warning:", w)
    if a.scenes:
        keep = set(a.scenes.split(","))
        scenes = {k: v for k, v in scenes.items() if k in keep}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "audio").mkdir(exist_ok=True)
    if (CACHE / ".setup-ok").exists():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")         # models are cached: no network (setup.sh sets 0)
    device = pick_device(cfg)
    os.environ["EXPLAINER_DEVICE"] = device
    if not a.skip_tts:
        synthesize(scenes, engine, a.out, voice)
    tpath = a.out / "timing.json"
    timing = json.loads(tpath.read_text()) if tpath.exists() else {}
    timing.update(align_and_qa(scenes, a.out, device, lex))
    timing = {k: timing[k] for k in order if k in timing}
    tpath.write_text(json.dumps(timing, indent=1))
    flagged = [f"{s}:{i}" for s, bs in timing.items() for i, b in enumerate(bs) if b.get("issues")]
    total = sum(b["dur"] + b["gap"] for bs in timing.values() for b in bs)
    print(f"narration: {total:.1f}s across {len(timing)} scenes; QA flagged: {', '.join(flagged) or 'none'}")


if __name__ == "__main__":
    main()
