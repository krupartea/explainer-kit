"""Maya1 (Llama-style LM -> SNAC 24 kHz codes). voice: {"description": "..."}.
Inline tags in text: <excited> <curious> <disappointed> <sigh> <laugh> <whisper> ... (see tokenizer inventory)."""
import time
import torch
from snac import SNAC
from transformers import AutoModelForCausalLM, AutoTokenizer
import _job

CODE_START, CODE_END, OFF = 128257, 128258, 128266
SOH, EOH, SOA, TEXT_EOT = 128259, 128260, 128261, 128009

job, out = _job.load()
t0, durs = time.time(), {}
torch.manual_seed(job["voice"].get("seed", 7))
repo = job["voice"].get("model", "maya-research/maya1")
model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=torch.bfloat16, device_map="cuda")
tok = AutoTokenizer.from_pretrained(repo)
snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().to("cuda")
desc = job["voice"]["description"]


def prompt(text):
    d = tok.decode
    return d([SOH]) + tok.bos_token + f'<description="{desc}"> {text}' + d([TEXT_EOT]) + d([EOH]) + d([SOA]) + d([CODE_START])


for it in job["items"]:
    ids = tok(prompt(it["text"]), return_tensors="pt", add_special_tokens=False).to("cuda")
    with torch.inference_mode():
        o = model.generate(**ids, max_new_tokens=4096, min_new_tokens=28, temperature=0.4, top_p=0.9,
                           repetition_penalty=1.1, do_sample=True, eos_token_id=CODE_END, pad_token_id=tok.pad_token_id)
    g = o[0, ids["input_ids"].shape[1]:].tolist()
    g = g[:g.index(CODE_END)] if CODE_END in g else g
    c = [t for t in g if OFF <= t <= 156937]
    n = len(c) // 7
    l1, l2, l3 = [], [], []
    for i in range(n):
        s = [(x - OFF) % 4096 for x in c[i * 7:(i + 1) * 7]]
        l1.append(s[0]); l2 += [s[1], s[4]]; l3 += [s[2], s[3], s[5], s[6]]
    codes = [torch.tensor(l, dtype=torch.long, device="cuda").unsqueeze(0) for l in (l1, l2, l3)]
    with torch.inference_mode():
        audio = snac.decoder(snac.quantizer.from_codes(codes))[0, 0].float().cpu().numpy()
    _job.save(out, it["id"], audio, 24000, durs)
_job.finish(out, durs, t0)
