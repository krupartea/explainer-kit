"""Shared job IO for engine synth scripts (each engine runs in its own venv).
Job JSON: {"out_dir": str, "voice": {...}, "items": [{"id": str, "text": str, "params": {...}}]}
Writes <out_dir>/<id>.wav and <out_dir>/durations.json ({id: seconds})."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf


def load():
    job = json.loads(Path(sys.argv[1]).read_text())
    out = Path(job["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    return job, out


def save(out, item_id, audio, sr, durs):
    audio = np.asarray(audio, dtype=np.float32).squeeze()
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.99:
        audio = audio * (0.99 / peak)
    sf.write(out / f"{item_id}.wav", audio, sr)
    durs[item_id] = round(len(audio) / sr, 3)
    print(f"{item_id}\t{durs[item_id]:.2f}s", flush=True)


def finish(out, durs, t0):
    (out / "durations.json").write_text(json.dumps(durs, indent=1))
    print(f"done {len(durs)} items, {sum(durs.values()):.1f}s audio in {time.time() - t0:.0f}s", flush=True)
