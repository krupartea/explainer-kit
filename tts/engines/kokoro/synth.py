"""Kokoro-82M with prosody control (prosody.py).
voice: {"name": "af_heart", "speed": 1.0, "focus_strength": 1.0, "pitch_shift": 0.0}  (a* American, b* British)
item params: focus [{word, occ}], pitch_range, pitch_shift (semitones),
energy (log, additive), speed (x voice speed). Inline IPA: [word](/ipa/)."""
import json
import os
import time
import numpy as np
import torch
from kokoro import KPipeline
import _job
import prosody

job, out = _job.load()
t0, durs = time.time(), {}
voice = job["voice"].get("name", "af_heart")
base_speed = job["voice"].get("speed", 1.0)
strength = job["voice"].get("focus_strength", 1.0)
voice_shift = job["voice"].get("pitch_shift", 0.0)   # semitones, whole voice (formants unchanged)
device = os.environ.get("EXPLAINER_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
pipe = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M", device=device)
pack = pipe.load_voice(voice).to(pipe.model.device)
for it in job["items"]:
    p = it.get("params", {})
    _, tokens = pipe.g2p(it["text"])
    chunks, words, offset = [], [], 0.0
    for _, _, tks in pipe.en_tokenize(tokens):
        P = prosody.plan(tks, p.get("focus", []))
        if not P.ps:
            continue
        audio, pd = prosody.synth(pipe.model, P, pack[min(len(P.ps), 510) - 1], speed=base_speed * p.get("speed", 1.0),
                                 pitch_range=p.get("pitch_range", 1.0), pitch_shift=voice_shift + p.get("pitch_shift", 0.0),
                                 energy=p.get("energy", 0.0), strength=p.get("focus_strength", strength))
        wt = prosody.word_times(tks, P, pipe.model.vocab, pd)
        chunks.append(audio.numpy())
        words += [[w, a + offset, b + offset] for w, a, b in wt]
        offset += len(chunks[-1]) / 24000
    _job.save(out, it["id"], np.concatenate(chunks), 24000, durs)
    (out / f"{it['id']}.words.json").write_text(json.dumps(words))
_job.finish(out, durs, t0)
