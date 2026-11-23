"""Chatterbox (original, built-in voice). params: exaggeration (0.25..1.0, emotion intensity), cfg_weight (pacing)."""
import time
import torch
from chatterbox.tts import ChatterboxTTS
import _job

job, out = _job.load()
t0, durs = time.time(), {}
torch.manual_seed(job["voice"].get("seed", 7))
m = ChatterboxTTS.from_pretrained(device="cuda")
ref = job["voice"].get("ref_wav")
for it in job["items"]:
    p = it.get("params", {})
    wav = m.generate(it["text"], audio_prompt_path=ref, exaggeration=p.get("exaggeration", 0.5),
                     cfg_weight=p.get("cfg_weight", 0.5), temperature=0.7)
    _job.save(out, it["id"], wav.cpu().numpy(), m.sr, durs)
_job.finish(out, durs, t0)
