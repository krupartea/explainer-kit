"""Qwen3-TTS CustomVoice. voice: {"model": repo, "speaker": "Aiden"}; params: instruct (natural-language style)."""
import time
import torch
from qwen_tts import Qwen3TTSModel
import _job

job, out = _job.load()
t0, durs = time.time(), {}
torch.manual_seed(job["voice"].get("seed", 7))
model = Qwen3TTSModel.from_pretrained(job["voice"].get("model", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"),
                                      device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")
spk = job["voice"].get("speaker", "Aiden")
for it in job["items"]:
    ins = it.get("params", {}).get("instruct") or None
    wavs, sr = model.generate_custom_voice(text=it["text"], language="English", speaker=spk, instruct=ins)
    _job.save(out, it["id"], wavs[0], sr, durs)
_job.finish(out, durs, t0)
