"""Piper (CPU). voice: {"model": "<path to .onnx>"}; params: length_scale."""
import io, time, wave
import numpy as np
from piper import PiperVoice
from piper.config import SynthesisConfig
import _job

job, out = _job.load()
t0, durs = time.time(), {}
v = PiperVoice.load(job["voice"]["model"])
for it in job["items"]:
    p = it.get("params", {})
    cfg = SynthesisConfig(length_scale=p.get("length_scale", 1.06), noise_scale=0.6, noise_w_scale=0.7)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        v.synthesize_wav(it["text"], wf, syn_config=cfg)
    buf.seek(0)
    with wave.open(buf) as wf:
        sr = wf.getframerate()
        a = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    _job.save(out, it["id"], a, sr, durs)
_job.finish(out, durs, t0)
