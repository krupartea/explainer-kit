"""Prosody control for Kokoro: edit the model's own predicted durations, pitch (F0) and energy (N) before the
decoder renders audio, so quality stays that of plain Kokoro.

Word-level marks (from the narration markup), each a known intonational meaning:
- focus    `*w*`   new information: H* accent, peak on the stressed vowel, fall after; the rest of the clause
                   recedes (post-focus compression)
- strong   `**w**` contrast with an alternative: L+H*, a low onset then a steep, higher rise, longer
- given    `~w~`   referring back to something already covered: lower key over the span, a fall-rise
                   (referring tone) on its last word
- mention  `"w"`   a quoted word or value: level, slightly raised, lengthened, so it is heard as a quotation
- aside    `((w))` a parenthetical: lower, compressed, quieter and faster
Beat-level: pitch range / shift / energy / speed (moods), and `onset`: a pitch reset at the start of a new topic
that decays over its first second (paratone).
Pauses inside a sentence are not supported (stretched frames hum; cut-in silence sounds unnatural); pauses go
between sentences (separate synthesis calls, kit/markup.py).
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
ST = math.log(2) / 12        # one semitone in log-F0
KINDS = ("focus", "strong", "given", "mention", "aside")


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", (w or "").lower())


@dataclass
class Plan:
    ps: str = ""
    kind: list = field(default_factory=list)      # per char: mark kind of its word, or ""
    word: list = field(default_factory=list)      # per char: index of its word token, or -1 (spaces, punctuation)
    peak: list = field(default_factory=list)      # per char: 1 on a marked word's stressed vowel
    pfc: list = field(default_factory=list)       # per char: 1 in a post-focus region
    last_given: set = field(default_factory=set)  # word indices that end a given span (get the fall-rise)


def plan(tokens, marks=()) -> Plan:
    """marks: [{"word", "occ", "kind"}]; occ = occurrence index of the word in the sentence.
    A mark without "kind" is focus (older jobs)."""
    mk = {(_norm(f["word"]), f["occ"]): f.get("kind", "focus") for f in marks}
    seen: dict[str, int] = {}
    P, in_pfc, wkinds = Plan(), False, []
    for ti, t in enumerate(tokens):
        ph = t.phonemes or ""
        key = _norm(t.text)
        occ = seen.get(key, 0)
        if key:
            seen[key] = occ + 1
        kind = mk.get((key, occ), "") if key else ""
        if any(c in CLAUSE_END for c in ph + (t.text or "")):
            in_pfc = False
        stress = max(ph.find("ˈ"), 0) if "ˈ" in ph else max(ph.find("ˌ"), 0)
        peak_i = next((i for i in range(stress, len(ph)) if ph[i] in VOWELS), None) if kind else None
        if key:
            wkinds.append((ti, kind))
        for i, c in enumerate(ph):
            P.ps += c
            P.kind.append(kind)
            P.word.append(ti if key else -1)
            P.peak.append(1.0 if i == peak_i else 0.0)
            P.pfc.append(1.0 if in_pfc and kind not in ("focus", "strong") else 0.0)
        if t.whitespace:
            P.ps += " "
            P.kind.append("")
            P.word.append(-1)
            P.peak.append(0.0)
            P.pfc.append(1.0 if in_pfc else 0.0)
        if kind in ("focus", "strong"):
            in_pfc = True
    for (ti, k), nxt in zip(wkinds, wkinds[1:] + [(None, "")]):
        if k == "given" and nxt[1] != "given":
            P.last_given.add(ti)
    lead = len(P.ps) - len(P.ps.lstrip())
    n = len(P.ps.strip())
    for k in ("kind", "word", "peak", "pfc"):
        setattr(P, k, getattr(P, k)[lead:lead + n])
    P.ps = P.ps.strip()
    return P


def word_times(tokens, P: Plan, vocab, pred_dur, with_index=False) -> list:
    """Exact [text, start_s, end_s] per word token, from the model's own durations
    (with_index: [token index, text, start, end])."""
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
            row = [t.text, st[idx[0]] / FRAMES_PER_SEC, (st[idx[-1]] + d[idx[-1]]) / FRAMES_PER_SEC]
            out.append([tokens.index(t)] + row if with_index else row)
        pos += len(ph) + (1 if t.whitespace else 0)
    return out


def aside_gain(audio, sr, tokens, P: Plan, vocab, pred_dur, db=-4.0, ramp=0.02):
    """Asides are spoken quieter: lower the gain over their exact word span (energy edits barely move loudness)."""
    import numpy as np
    aside_words = {P.word[i] for i, k in enumerate(P.kind) if k == "aside"}
    spans = [(s0, e0) for ti, _, s0, e0 in word_times(tokens, P, vocab, pred_dur, with_index=True) if ti in aside_words]
    if not spans:
        return audio
    g = np.ones(len(audio), dtype=np.float32)
    lo, hi = int(min(s for s, _ in spans) * sr), int(max(e for _, e in spans) * sr)
    r = int(ramp * sr)
    k = 10 ** (db / 20)
    g[lo:hi] = k
    g[max(lo - r, 0):lo] = np.linspace(1, k, lo - max(lo - r, 0))
    g[hi:hi + r] = np.linspace(k, 1, len(g[hi:hi + r]))
    return audio * g


def _ramp(x, a, b):
    """0 at a, 1 at b (cosine), clamped."""
    return 0.5 - 0.5 * torch.cos(math.pi * ((x - a) / max(b - a, 1e-3)).clamp(0, 1))


def _shape(kind: str, n: int, p: float, cfg: dict) -> torch.Tensor:
    """Log-F0 offset over one word's frames; p = stressed-vowel position in [0, 1]."""
    x = torch.linspace(0, 1, max(n, 1))
    if kind == "focus":           # H*: rise to the peak, fall a little below by the end
        amp, fall = math.log1p(cfg["pitch"]), cfg["fall"] / max(cfg["pitch"], 1e-6)
        up, down = _ramp(x, 0, p), 1 - (1 + fall) * _ramp(x, p, 1)
        return amp * torch.where(x <= p, up, down)
    if kind == "strong":          # L+H*: dip first, then a steep, higher rise; fall after
        amp = math.log1p(cfg["pitch"] * 1.45)
        low = -0.35 * (1 - _ramp(x, 0, max(p * 0.5, 0.05)))
        rise = _ramp(x, p * 0.5, p) * 1.35
        down = 1 - 1.25 * _ramp(x, p, 1)
        return amp * torch.where(x <= p, low + rise, down)
    if kind == "given_last":      # referring tone: fall on the stressed vowel, rise at the end (fall-rise)
        return 2.0 * ST * (-_ramp(x, 0, p) + 1.6 * _ramp(x, p + (1 - p) * 0.3, 1))
    return torch.zeros(n)


@torch.no_grad()
def synth(model, P: Plan, ref_s, speed=1.0, pitch_range=1.0, pitch_shift=0.0, energy=0.0, strength=1.0,
          onset=0.0, focus_cfg=FOCUS):
    scaled = ("pitch", "fall", "word_dur", "vowel_dur", "energy")
    cfg = {k: v * (strength if k in scaled else 1.0) for k, v in focus_cfg.items()}
    ids, rows = [], []
    for i, c in enumerate(P.ps):
        v = model.vocab.get(c)
        if v is not None:
            ids.append(v)
            rows.append(i)
    dev = model.device
    kinds = [""] + [P.kind[i] for i in rows] + [""]
    words = [-1] + [P.word[i] for i in rows] + [-1]

    def pick(arr):
        return torch.tensor([0.0, *[arr[i] for i in rows], 0.0], device=dev)

    def where(*ks):
        return torch.tensor([1.0 if k in ks else 0.0 for k in kinds], device=dev)

    peak, pfc = pick(P.peak), pick(P.pfc)
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
    accented = where("focus") + 1.6 * where("strong")
    dur = dur * (1 + cfg["word_dur"] * accented) * (1 + cfg["vowel_dur"] * peak * accented.clamp(max=1) * (1 + 0.6 * where("strong")))
    dur = dur * (1 + 0.12 * where("mention")) * (1 - 0.12 * where("aside")) * (1 - 0.04 * where("given"))
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
    lf = m + pitch_range * (lf - m) + pitch_shift * ST                         # mood
    if onset:                                                                  # paratone: reset, then decay
        t = torch.arange(lf.numel(), device=dev) / (FRAMES_PER_SEC * up)
        lf = lf + onset * ST * (1 - t / 1.2).clamp(min=0)
    pf = per_frame(pfc)                                                        # post-focus compression
    lf = torch.where(pf > 0, m + cfg["pfc_range"] * (lf - m) + cfg["pfc_shift"] * ST, lf)
    n = n + energy + cfg["pfc_energy"] * pf
    asd = per_frame(where("aside"))                                            # parenthetical register
    lf = torch.where(asd > 0, m + 0.6 * (lf - m) - 2.5 * ST, lf)                # (quieter: aside_gain)
    gvn = per_frame(where("given"))                                            # referring: lower key
    lf = lf - 1.0 * ST * gvn
    men = per_frame(where("mention"))                                          # quotation: level, a bit high
    lf = torch.where(men > 0, m + 0.35 * (lf - m) + 1.5 * ST, lf)
    n = n + 0.15 * men
    starts = torch.cumsum(pred_dur, 0) - pred_dur                             # per-word accents
    j = 1
    while j < L - 1:
        k_ = kinds[j]
        w = words[j]
        kind = k_ if k_ in ("focus", "strong") else ("given_last" if k_ == "given" and w in P.last_given else "")
        if not kind or w < 0:
            j += 1
            continue
        k = j
        while k + 1 < L - 1 and words[k + 1] == w:
            k += 1
        a, b = int(starts[j]) * up, int(starts[k] + pred_dur[k]) * up
        pk = next((q for q in range(j, k + 1) if peak[q] > 0), (j + k) // 2)
        p_mid = (int(starts[pk]) + int(pred_dur[pk]) / 2) * up
        shape = _shape(kind, b - a, (p_mid - a) / max(b - a, 1), cfg).to(dev)
        lf[a:b] = lf[a:b] + shape
        if kind in ("focus", "strong"):
            n[a:b] = n[a:b] + cfg["energy"] * (1.4 if kind == "strong" else 1.0) * (shape / max(shape.max(), 1e-6)).clamp(min=0)
        j = k + 1
    f = torch.where(voiced, torch.exp(lf), f0)
    t_en = model.text_encoder(input_ids, lengths, mask)
    audio = model.decoder(t_en @ aln, f.unsqueeze(0), n.unsqueeze(0), ref_s[:, :128]).squeeze()
    return audio.cpu(), pred_dur.cpu()
