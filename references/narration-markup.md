# Narration markup

narration.txt is engine-neutral; `vid narrate` compiles it for the configured TTS engine (config.yaml).

```
// comment
# S03 failure-modes            <- scene header: id = the Scene class name in scenes.py
That gives {14/07|fourteen, slash oh seven}. [pause 0.3] But @wrong that is the *departure* date.
[curious] So why does sorting by height break when the label tilts?
```

Each line under a header is one **beat**: one `self.say()` in the scene, one subtitle cue.

| Syntax | Meaning |
|---|---|
| `{shown\|spoken}` | subtitles show `shown`, the voice says `spoken` (a respelling) |
| `{shown\|/ipa/}` | misaki IPA, used by engines that take phonemes (kokoro); others say `shown` |
| `{shown\|spoken\|/ipa/}` | both |
| `[mood]` at line start | delivery for the beat: `neutral calm curious excited triumphant serious warning disappointed sad playful whisper` |
| `[sigh] [laugh] [chuckle] [gasp] [exhale]` | nonverbal sound, where the engine has one |
| `*word*` | focus on one word (where and why: references/delivery.md) |
| `@name` | sync anchor on the next spoken word; scenes use `self.until("name")` |
| `[pause 0.6]` | silence (seconds) between two sentences; never mid-sentence (lint error) |

## Pronunciation

The voice reads `spoken`; subtitles read `shown`. Three layers, cheapest first:

1. **Heteronyms (lint-enforced).** `vid narrate` refuses unannotated vowel-changing heteronyms (`read`,
   `lead`, `live`, `close`, `wind`, `tear`, `minute`, …; list in kit/markup.py). Annotate each by its meaning in that
   sentence: `{read|red}` (past), `{read|reed}` (present); `{lead|led}` (metal) / `{lead|leed}` (guide);
   `{live|liv}` / `{live|/lˈIv/}`.
2. **Lexicon.** Recurring terms (acronyms, names, `regex`) live in a lexicon: kit-wide `lexicon.yaml`, plus an
   optional `lexicon.yaml` in the video folder for this video's terms (it wins on conflicts). Add a term to the
   video's lexicon the first time QA shows it misread.
3. **Inline respelling** for one-offs: identifiers, numbers with units, dates
   (`{AB12345|A B, one two three four five}`, `{0.58 s|zero point five eight seconds}`).

Spell acronyms that are said letter by letter with spaces (`S D K`); acronyms said as words stay as is (`JSON`,
`NASA`). Code identifiers become words: `{std::vector|standard vector}`, `{PageParser|page parser}`.

## QA

`vid narrate` transcribes every beat with Whisper (without showing it the script) and writes
qa/narration_qa.md: expected vs heard text, a character error rate (spaces and spellings normalized, each
`{shown|spoken}` compared in whichever form Whisper wrote), and flags (⚠): error rate above 0.12, the first or
last word missing, or an anchor not found. Fix each ⚠ (respell, split the sentence, move the anchor) and re-run
`vid narrate <dir> --scenes <ids>`. Whisper hears words, not vowels, so it misses a wrong vowel in a heteronym:
that is what the lint is for.

## Engine capabilities

| engine | respelling | IPA | moods | emphasis | nonverbals |
|---|---|---|---|---|---|
| piper | ✓ | | | | |
| kokoro | ✓ | ✓ | ✓ (pitch range/shift, energy, speed) | ✓ (pitch accent + lengthening) | |
| chatterbox | ✓ | | intensity only | | |
| qwen | ✓ | | ✓ (instruction) | ✓ (instruction) | |
| maya1 | ✓ | | partial (tags) | | ✓ |

Unsupported markup is dropped silently, so a script stays valid across engines.
