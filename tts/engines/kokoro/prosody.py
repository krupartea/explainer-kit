"""Prosody control for Kokoro: edit the model's own predicted durations, pitch (F0) and energy (N)
before the decoder renders audio, so quality stays that of plain Kokoro.

Focus (contrastive emphasis), modelled on how speakers mark it:
- a pitch accent: F0 rises to a peak on the word's *stressed vowel*, then falls below the baseline by the
  word's end (H* L-). Nothing outside the word is raised.
- lengthening: the focused word a little, its stressed vowel more.
- post-focus compression: from the focused word to the end of the clause, pitch range narrows and drops,
  energy dips, so the words after it ("date" in "the DEPARTURE date") recede.
Pauses inside a sentence are not supported: stretched frames hum and cut-in silence sounds unnatural.
Pauses go between sentences (separate synthesis calls, see kit/markup.py).
Mood: pitch range (around the utterance's mean log-F0), pitch shift (semitones), energy, speed.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import torch

FOCUS = dict(pitch=0.22, fall=0.10, word_dur=0.10, vowel_dur=0.30, energy=0.5,
             pfc_range=0.55, pfc_shift=-1.2, pfc_energy=-0.25)
FRAMES_PER_SEC = 40          # Kokoro duration frames: 600 samples at 24 kHz
VOWELS = set("aeiouæɑɐɒɔəɚɛɜɪʊʌAIOWYQɝᵻᵊ")
CLAUSE_END = set(".,;:!?—…")


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", (w or "").lower())


@dataclass
class Plan:
    ps: str = ""
    focus: list = field(default_factory=list)     # per char: 1 inside a focused word
    peak: list = field(default_factory=list)      # per char: 1 on a focused word's stressed vowel
    pfc: list = field(default_factory=list)       # per char: 1 in the post-focus region


def plan(tokens, focus=()) -> Plan:
    """focus: [{"word", "occ"}] (occ = occurrence index of the word in the sentence)."""
    fset = {(_norm(f["word"]), f["occ"]) for f in focus}
    seen: dict[str, int] = {}
    P, in_pfc = Plan(), False
    for t in tokens:
        ph = t.phonemes or ""
        key = _norm(t.text)
        occ = seen.get(key, 0)
        if key:
            seen[key] = occ + 1
        is_focus = bool(key) and (key, occ) in fset
        if any(c in CLAUSE_END for c in ph + (t.text or "")):
            in_pfc = False
        stress = max(ph.find("ˈ"), 0) if "ˈ" in ph else max(ph.find("ˌ"), 0)
        peak_i = next((i for i in range(stress, len(ph)) if ph[i] in VOWELS), None) if is_focus else None
        for i, c in enumerate(ph):
            P.ps += c
            P.focus.append(1.0 if is_focus else 0.0)
            P.peak.append(1.0 if i == peak_i else 0.0)
            P.pfc.append(1.0 if in_pfc and not is_focus else 0.0)
        if t.whitespace:
            P.ps += " "
            P.focus.append(0.0)
            P.peak.append(0.0)
            P.pfc.append(1.0 if in_pfc else 0.0)
        if is_focus:
            in_pfc = True
    lead = len(P.ps) - len(P.ps.lstrip())
    n = len(P.ps.strip())
    for k in ("focus", "peak", "pfc"):
        setattr(P, k, getattr(P, k)[lead:lead + n])
    P.ps = P.ps.strip()
    return P


def word_times(tokens, P: Plan, vocab, pred_dur) -> list:
    """Exact [text, start_s, end_s] per word token, from the model's own durations."""
    keep = [i for i, c in enumerate(P.ps) if vocab.get(c) is not None]
    pos_of = {i: j + 1 for j, i in enumerate(keep)}                 # char index -> model token index
    st = (torch.cumsum(pred_dur, 0) - pred_dur).tolist()
    d = pred_dur.tolist()
    full = "".join((t.phonemes or "") + (" " if t.whitespace else "") for t in tokens)
    pos = -(len(full) - len(full.lstrip()))                         # P.ps is the stripped string
    out = []
    for t in tokens:
        ph = t.phonemes or ""
        idx = [pos_of[i] for i in range(pos, pos + len(ph)) if i in pos_of]
        if idx and _norm(t.text):
            out.append([t.text, st[idx[0]] / FRAMES_PER_SEC, (st[idx[-1]] + d[idx[-1]]) / FRAMES_PER_SEC])
        pos += len(ph) + (1 if t.whitespace else 0)
    return out


def _accent(n_frames: int, peak_pos: float, fall: float) -> torch.Tensor:
    """Rise 0→1 up to the peak, then 1→-fall by the end (cosine ramps). peak_pos in [0, 1]."""
    x = torch.linspace(0, 1, max(n_frames, 1))
    up = 0.5 - 0.5 * torch.cos(math.pi * (x / max(peak_pos, 1e-3)).clamp(0, 1))
    dx = ((x - peak_pos) / max(1 - peak_pos, 1e-3)).clamp(0, 1)
    down = 1 - (1 + fall) * (0.5 - 0.5 * torch.cos(math.pi * dx))
    return torch.where(x <= peak_pos, up, down)[:n_frames]


@torch.no_grad()
def synth(model, P: Plan, ref_s, speed=1.0, pitch_range=1.0, pitch_shift=0.0, energy=0.0, strength=1.0,
          focus_cfg=FOCUS):
    scaled = ("pitch", "fall", "word_dur", "vowel_dur", "energy")
    cfg = {k: v * (strength if k in scaled else 1.0) for k, v in focus_cfg.items()}
    ids, rows = [], []
    for i, c in enumerate(P.ps):
        v = model.vocab.get(c)
        if v is not None:
            ids.append(v)
            rows.append(i)
    dev = model.device

    def pick(arr):
        return torch.tensor([0.0, *[arr[i] for i in rows], 0.0], device=dev)

    focus, peak, pfc = pick(P.focus), pick(P.peak), pick(P.pfc)
    input_ids = torch.LongTensor([[0, *ids, 0]]).to(dev)
    ref_s = ref_s.to(dev)

    L = input_ids.shape[-1]
    lengths = torch.full((1,), L, device=dev, dtype=torch.long)
    mask = torch.arange(L, device=dev).unsqueeze(0) + 1 > lengths.unsqueeze(1)
    bert_dur = model.bert(input_ids, attention_mask=(~mask).int())
    d_en = model.bert_encoder(bert_dur).transpose(-1, -2)
    s = ref_s[:, 128:]
    d = model.predictor.text_encoder(d_en, s, lengths, mask)
    x, _ = model.predictor.lstm(d)
    dur = torch.sigmoid(model.predictor.duration_proj(x)).sum(axis=-1).squeeze(0) / speed
    dur = dur * (1 + cfg["word_dur"] * focus) * (1 + cfg["vowel_dur"] * peak)
    pred_dur = torch.round(dur).clamp(min=1).long()
    idx = torch.repeat_interleave(torch.arange(L, device=dev), pred_dur)
    aln = torch.zeros((L, idx.shape[0]), device=dev)
    aln[idx, torch.arange(idx.shape[0])] = 1
    aln = aln.unsqueeze(0)
    F0, N = model.predictor.F0Ntrain(d.transpose(-1, -2) @ aln, s)
    up = F0.shape[-1] // idx.shape[0]                    # F0 frames per duration frame (2)

    def per_frame(v):
        r = v[idx].repeat_interleave(up)
        return torch.nn.functional.pad(r, (0, F0.shape[-1] - r.numel()))

    f0, n = F0[0], N[0].clone()
    voiced = f0 > 50
    lf = torch.log(f0.clamp(min=1.0))
    m = lf[voiced].mean() if voiced.any() else lf.mean()
    lf = m + pitch_range * (lf - m) + pitch_shift * math.log(2) / 12          # mood
    pf = per_frame(pfc)                                                         # post-focus compression
    lf = torch.where(pf > 0, m + cfg["pfc_range"] * (lf - m) + cfg["pfc_shift"] * math.log(2) / 12, lf)
    n = n + energy + cfg["pfc_energy"] * pf
    starts = torch.cumsum(pred_dur, 0) - pred_dur                              # pitch accents
    j = 1
    while j < L - 1:
        if focus[j] <= 0:
            j += 1
            continue
        k = j
        while k + 1 < L - 1 and focus[k + 1] > 0:
            k += 1
        a, b = int(starts[j]) * up, int(starts[k] + pred_dur[k]) * up
        pk = next((q for q in range(j, k + 1) if peak[q] > 0), (j + k) // 2)
        p_mid = (int(starts[pk]) + int(pred_dur[pk]) / 2) * up
        shape = _accent(b - a, (p_mid - a) / max(b - a, 1), cfg["fall"] / max(cfg["pitch"], 1e-6)).to(dev)
        lf[a:b] = lf[a:b] + math.log1p(cfg["pitch"]) * shape
        n[a:b] = n[a:b] + cfg["energy"] * shape.clamp(min=0)
        j = k + 1
    f = torch.where(voiced, torch.exp(lf), f0)
    t_en = model.text_encoder(input_ids, lengths, mask)
    audio = model.decoder(t_en @ aln, f.unsqueeze(0), n.unsqueeze(0), ref_s[:, :128]).squeeze()
    return audio.cpu(), pred_dur.cpu()
