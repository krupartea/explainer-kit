"""Engine-neutral narration markup -> per-engine TTS input, subtitles and sync anchors.

A narration file is plain text:

    # S02 wrong-date                      <- scene header: "# <scene id> [free comment]"
    Now the gate. Look for {GATE|gate}, then a number.
    [disappointed] But @wrong that is the {old|old} gate.

Each non-empty line under a header is one *beat*: one TTS call and one subtitle cue (split if long).

Inline syntax (full spec in references/narration-markup.md):
    {shown|spoken}          subtitles show `shown`, TTS speaks `spoken` (a respelling)
    {shown|/ipa/}           IPA in misaki notation, used by engines that take phonemes (kokoro);
                            other engines speak `shown`
    {shown|spoken|/ipa/}    both
    [mood]                  at the start of a beat: delivery for the whole beat (see MOODS)
    [sigh] [laugh] [chuckle] [gasp]   nonverbal events, where the engine supports them
    *word*                  emphasis
    @name                   sync anchor on the next spoken word (time is found by forced alignment)
    [pause 0.6]             silence of 0.6 s between two sentences (each side is its own TTS call);
                            at the end of a line: extra silence after the beat, while the pictures keep moving
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ENGINES = ("piper", "kokoro", "chatterbox", "qwen", "maya1")

# delivery presets -> what each engine can do with them
MOODS = {  # kokoro: prosody edits (pitch range x, pitch shift semitones, log-energy +, speed x)
    "neutral": dict(qwen="", maya1="", chatterbox=0.5, kokoro={}),
    "calm": dict(qwen="Speak calmly and unhurriedly, in a relaxed explanatory tone.", maya1="", chatterbox=0.35,
                 kokoro=dict(pitch_range=0.85, speed=0.96)),
    "curious": dict(qwen="Ask it with genuine curiosity and a rising, wondering intonation.", maya1="<curious>",
                    chatterbox=0.6, kokoro=dict(pitch_range=1.25, pitch_shift=0.7)),
    "excited": dict(qwen="Say it with excitement and energy.", maya1="<excited>", chatterbox=0.85,
                    kokoro=dict(pitch_range=1.4, pitch_shift=1.5, energy=0.3, speed=1.05)),
    "triumphant": dict(qwen="Say it with a satisfied, triumphant tone, as a payoff.", maya1="<excited>", chatterbox=0.8,
                       kokoro=dict(pitch_range=1.3, pitch_shift=1.0, energy=0.2)),
    "serious": dict(qwen="Say it in a serious, measured tone.", maya1="", chatterbox=0.4,
                    kokoro=dict(pitch_range=0.85, pitch_shift=-0.8, speed=0.96)),
    "warning": dict(qwen="Say it as a firm, cautionary warning, slightly slower.", maya1="", chatterbox=0.6,
                    kokoro=dict(pitch_range=0.9, pitch_shift=-1.0, energy=0.1, speed=0.94)),
    "disappointed": dict(qwen="Say it in a disappointed, deflated tone.", maya1="<disappointed>", chatterbox=0.7,
                         kokoro=dict(pitch_range=0.65, pitch_shift=-1.5, energy=-0.3, speed=0.94)),
    "sad": dict(qwen="Say it in a sad, subdued tone.", maya1="<disappointed>", chatterbox=0.6,
                kokoro=dict(pitch_range=0.6, pitch_shift=-2.0, energy=-0.4, speed=0.92)),
    "playful": dict(qwen="Say it playfully, with a light smile in the voice.", maya1="<mischievous>", chatterbox=0.7,
                    kokoro=dict(pitch_range=1.35, pitch_shift=1.0)),
    "whisper": dict(qwen="Whisper it softly.", maya1="<whisper>", chatterbox=0.3,
                    kokoro=dict(pitch_range=0.8, energy=-0.6)),
    # structural deliveries (can combine with one mood: "[new] [curious] ...")
    "new": dict(qwen="Start a new topic: a fresh, slightly higher voice.", maya1="", chatterbox=0.5,
                kokoro=dict(onset=2.5)),
    "define": dict(qwen="Introduce this definition slowly and clearly.", maya1="", chatterbox=0.4,
                   kokoro=dict(speed=0.9, pitch_range=1.1)),
    "recap": dict(qwen="Sum it up in a steady, settled tone.", maya1="", chatterbox=0.35,
                  kokoro=dict(pitch_range=0.8, pitch_shift=-0.7, speed=0.95)),
    "reassure": dict(qwen="Say it warmly and reassuringly, a little slower.", maya1="", chatterbox=0.4,
                     kokoro=dict(pitch_range=0.85, pitch_shift=-0.8, energy=-0.25, speed=0.93)),
    "reveal": dict(qwen="Reveal it with a lift of interest, as the answer.", maya1="<excited>", chatterbox=0.7,
                   kokoro=dict(pitch_range=1.3, pitch_shift=1.0, energy=0.15)),
}
NONVERBAL = {"sigh", "laugh", "chuckle", "gasp", "exhale"}
NONVERBAL_TAGS = {"maya1": "<{}>"}  # other engines drop nonverbals

# Vowel-changing heteronyms that TTS engines get wrong: every occurrence must be annotated, e.g. {read|red}.
HETERONYMS = {
    "read", "reread", "misread", "proofread", "lead", "leads", "live", "lives", "wind", "winds", "tear", "tears",
    "close", "closes", "wound", "bow", "bows", "bass", "minute", "desert", "dove", "polish", "sow",
}  # stress-only pairs (record, present, object, use…) are left to the engine; add here if one gets them wrong

STRUCTURAL = {"new", "define", "recap", "calm", "neutral"}

TOKEN = re.compile(
    r"\{(?P<shown>[^|{}]+)\|(?P<a>[^|{}]*)(?:\|(?P<b>[^|{}]*))?\}"  # {shown|spoken} / {shown|/ipa/} / both
    r"|\*\*(?P<strong>[^*]+)\*\*"                                     # **contrast**
    r"|~(?P<given>[^~]+)~"                                            # ~given~ (referring back)
    r"|\(\((?P<aside>.+?)\)\)"                                        # ((aside))
    r'|"(?P<mention>[^"]+)"'                                          # "mention"
    r"|\[(?P<tag>[a-z]+)(?: (?P<arg>[0-9.]+))?\]"                     # [mood] [sigh] [pause 0.6]
    r"|\*(?P<emph>[^*]+)\*"                                           # *emphasis*
    r"|@(?P<anchor>[A-Za-z_][\w-]*)\s*"                                # @anchor
)
ANNOT = re.compile(r"\{([^|{}]+)\|([^|{}]*)(?:\|([^|{}]*))?\}")
WORD = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9'’./-]*[A-Za-z0-9])?")
NV = re.compile(r"\s*\x00(\d+)\x00\s*")


@dataclass
class Part:
    """One TTS call (beats split by [pause])."""
    shown: str = ""
    spoken: str = ""        # plain spoken text (respellings applied)
    kokoro: str = ""        # spoken text with misaki IPA links
    emph: list = field(default_factory=list)        # emphasized words (instruction-driven engines)
    marks: list = field(default_factory=list)       # [{word, occ, kind}] on the kokoro text (prosody engines)
    nonverbal: list = field(default_factory=list)   # names; spoken text holds \x00<i>\x00 placeholders
    pause_after: float = 0.0


@dataclass
class Beat:
    scene: str
    index: int
    raw: str
    mood: str = "neutral"
    moods: list = field(default_factory=list)       # all leading tags, e.g. ["new", "curious"]
    parts: list = field(default_factory=list)
    anchors: dict = field(default_factory=dict)  # name -> (part index, spoken word index)
    extra_gap: float = 0.0                        # trailing [pause s]: silence after the beat (pictures keep moving)

    @property
    def shown(self):
        return " ".join(p.shown.strip() for p in self.parts).strip()


class MarkupError(ValueError):
    pass


def load_lexicon(path: Path | None) -> dict:
    if not path or not Path(path).exists():
        return {}
    data = yaml.safe_load(Path(path).read_text()) or {}
    return data.get("terms", {}) or {}


def _apply_lexicon(text: str, lex: dict, engine: str) -> str:
    """Whole-word replacement of lexicon terms in plain (non-annotated) text."""
    for term, say in sorted(lex.items(), key=lambda kv: -len(kv[0])):
        if isinstance(say, dict):
            say = say.get(engine, say.get("default"))
        if say is None:
            continue
        text = re.sub(rf"(?<![\w/]){re.escape(term)}(?![\w/])", say, text)
    return text


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def _occurrences(text: str, word: str) -> int:
    return sum(1 for x in WORD.findall(text) if _norm(x) == _norm(word))


def parse_beat(scene: str, index: int, line: str, lex: dict, engine: str) -> Beat:
    beat = Beat(scene, index, line)
    body = line.strip()
    while (m := re.match(r"\[([a-z]+)\]\s*", body)) and m.group(1) in MOODS:
        beat.moods.append(m.group(1))
        body = body[m.end():]
    if beat.moods:
        beat.mood = next((x for x in reversed(beat.moods) if x not in STRUCTURAL), beat.moods[-1])
    part, pos = Part(), 0

    def plain(seg: str) -> str:
        """Append plain text; return what kokoro's tokenizer will see for it."""
        part.shown += seg
        s = _apply_lexicon(seg, lex, engine)
        part.spoken += s
        part.kokoro += s
        return s

    def annotate(shown: str, a: str | None, b: str | None) -> str:
        """Append a {shown|spoken|/ipa/} annotation; return the word(s) kokoro's tokenizer will see."""
        ipa = next((x[1:-1] for x in (a, b) if x and len(x) > 1 and x.startswith("/") and x.endswith("/")), None)
        resp = next((x for x in (a, b) if x and not (x.startswith("/") and x.endswith("/"))), None)
        said = resp if resp is not None else shown
        part.shown += shown
        part.spoken += said
        part.kokoro += f"[{shown}](/{ipa}/)" if ipa else said
        return shown if ipa else said

    for t in TOKEN.finditer(body):
        plain(body[pos:t.start()])
        pos = t.end()
        if t.group("shown") is not None:
            annotate(t.group("shown"), t.group("a"), t.group("b"))
        elif t.group("tag") is not None:
            tag, arg = t.group("tag"), t.group("arg")
            if tag == "pause":
                part.pause_after = float(arg or 0.5)
                beat.parts.append(part)
                part = Part()
            elif tag in NONVERBAL:
                mark = f" \x00{len(part.nonverbal)}\x00 "
                part.nonverbal.append(tag)
                part.spoken += mark
                part.kokoro += mark
            elif tag in MOODS:
                raise MarkupError(f"{scene}:{index}: mood [{tag}] must start the beat")
            else:
                raise MarkupError(f"{scene}:{index}: unknown tag [{tag}]")
        elif any(t.group(g) is not None for g in ("emph", "strong", "given", "aside", "mention")):
            kind = next(g for g in ("emph", "strong", "given", "aside", "mention") if t.group(g) is not None)
            w = t.group(kind)
            kind = "focus" if kind == "emph" else kind
            if kind in ("focus", "strong"):
                part.emph.append(ANNOT.sub(lambda m: m.group(1), w))
            before = part.kokoro
            if kind == "aside":            # set off like a speaker does: short breaks around it
                part.shown += "("
                part.spoken += ", "
                part.kokoro += ", "
            if kind == "mention":
                part.shown += '"'
            seen, k = "", 0
            for m in ANNOT.finditer(w):
                seen += plain(w[k:m.start()]) + " " + annotate(m.group(1), m.group(2), m.group(3)) + " "
                k = m.end()
            seen += plain(w[k:])
            if kind == "aside":
                part.shown += ")"
                part.spoken += ", "
                part.kokoro += ", "
            if kind == "mention":
                part.shown += '"'
            said = WORD.findall(seen)
            # focus/strong: one unit, accented on its last word (nuclear stress); given/mention/aside: every word
            targets = said[-1:] if kind in ("focus", "strong") else said
            for n_, x in enumerate(said):
                if x in targets and (kind not in ("focus", "strong") or n_ == len(said) - 1):
                    part.marks.append({"word": x, "occ": _occurrences(before, x) + said[:n_].count(x), "kind": kind})
        elif t.group("anchor") is not None:
            name = t.group("anchor")
            if name in beat.anchors:
                raise MarkupError(f"{scene}:{index}: duplicate anchor @{name}")
            beat.anchors[name] = (len(beat.parts), len(WORD.findall(spoken_plain(part.spoken))))
    plain(body[pos:])
    beat.parts.append(part)
    for p in beat.parts:
        for k in ("shown", "spoken", "kokoro"):
            v = re.sub(r"\s+", " ", getattr(p, k)).strip()
            v = re.sub(r"\s*,\s*(?=[,.?!;:])", "", v)          # an aside next to punctuation: no doubled marks
            v = re.sub(r"\s+,", ",", v)
            v = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", v))
            setattr(p, k, re.sub(r"^,\s*", "", v))
    if len(beat.parts) > 1 and not spoken_plain(beat.parts[-1].spoken):   # trailing [pause s] = breath after the beat
        beat.extra_gap = beat.parts[-2].pause_after
        beat.parts[-2].pause_after = 0.0
        beat.parts.pop()
    return beat


def lint_beat(beat: Beat) -> list[str]:
    """Errors: unannotated heteronyms (annotated ones sit inside {...}); a [pause] inside a phrase."""
    stripped = re.sub(r"\{[^{}]*\}", " ", beat.raw)
    hits = sorted({w.lower() for w in WORD.findall(stripped) if w.lower() in HETERONYMS})
    errs = [f"{beat.scene}:{beat.index}: annotate heteronym '{h}', e.g. {{{h}|<respelling>}} or {{{h}|/ipa/}}"
            for h in hits]
    for m in re.finditer(r"\[pause[^\]]*\]", beat.raw):
        before = beat.raw[:m.start()].rstrip()
        if before and before[-1] not in ".?!…:;":
            errs.append(f"{beat.scene}:{beat.index}: [pause] inside a phrase sounds unnatural; pause after . ? ! : ; "
                        f"or let a comma do it")
    return errs


def lint_warnings(scenes: dict) -> list[str]:
    """Advisory: multi-word focus spans (check the accent word), and delivery tags (the engine supports them,
    the guidance doesn't use them: feeling belongs in the words and the picture)."""
    beats = [b for bs in scenes.values() for b in bs]
    warns = []
    for b in beats:
        for e in re.findall(r"\*([^*]+)\*", b.raw):
            if len(e.split()) > 1:
                warns.append(f"{b.scene}:{b.index}: *{e}* is one focus unit, accented on '{e.split()[-1]}'. "
                             f"If only one of its words contrasts, mark that word alone (references/narration-markup.md)")
    tagged = [f"{b.scene}:{b.index}" for b in beats if b.moods]
    if tagged:
        warns.append(f"delivery tags on {', '.join(tagged)}: write the feeling into the words instead "
                     f"(references/toolbox.md)")
    return warns


def parse_file(path: Path, engine: str, lexicon: Path | dict | None = None) -> dict[str, list[Beat]]:
    lex = lexicon if isinstance(lexicon, dict) else load_lexicon(lexicon)
    scenes: dict[str, list[Beat]] = {}
    cur = None
    for ln in Path(path).read_text().splitlines():
        if not ln.strip() or ln.lstrip().startswith("//"):
            continue
        if ln.startswith("#"):
            cur = ln[1:].split()[0]
            scenes[cur] = []
            continue
        if cur is None:
            raise MarkupError(f"{path}: text before the first '# <scene>' header")
        scenes[cur].append(parse_beat(cur, len(scenes[cur]), ln, lex, engine))
    return scenes


def spoken_plain(text: str) -> str:
    """Spoken text without nonverbal placeholders (for QA / alignment)."""
    return NV.sub(" ", text).strip()


def compile_part(beat: Beat, part: Part, engine: str) -> tuple[str, dict]:
    """-> (text for the engine, engine params)."""
    mood = MOODS[beat.mood]

    def nonverbals(text, fmt):
        return re.sub(r"\s+", " ", NV.sub(lambda m: f" {fmt.format(part.nonverbal[int(m.group(1))])} " if fmt else " ",
                                          text)).strip()

    if engine == "kokoro":
        params = {}
        for tag in beat.moods or ["neutral"]:
            params.update(MOODS[tag]["kokoro"])
        if part.marks:
            params["marks"] = part.marks
        return nonverbals(part.kokoro, None), params
    if engine == "piper":
        return nonverbals(part.spoken, None), {}
    if engine == "chatterbox":
        return nonverbals(part.spoken, None), {"exaggeration": mood["chatterbox"]}
    if engine == "qwen":
        ins = mood["qwen"]
        if part.emph:
            ins = (ins + " " if ins else "") + " ".join(f"Stress the word '{w}'." for w in part.emph)
        return nonverbals(part.spoken, None), {"instruct": ins}
    if engine == "maya1":
        text = nonverbals(part.spoken, "<{}>")
        return (f"{mood['maya1']} {text}" if mood["maya1"] else text), {}
    raise MarkupError(f"unknown engine {engine}")


if __name__ == "__main__":  # quick check: python -m kit.markup narration.txt [engine] [lexicon.yaml]
    import sys

    eng = sys.argv[2] if len(sys.argv) > 2 else "qwen"
    sc = parse_file(Path(sys.argv[1]), eng, Path(sys.argv[3]) if len(sys.argv) > 3 else None)
    problems = [p for bs in sc.values() for b in bs for p in lint_beat(b)]
    for sid, beats in sc.items():
        for b in beats:
            for i, p in enumerate(b.parts):
                print(sid, b.index, i, b.mood, "|", compile_part(b, p, eng), "| shown:", p.shown, "| anchors:", b.anchors)
    print("\n".join(problems) or "lint: ok")
