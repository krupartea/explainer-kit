# Narration markup

narration.txt is the storyboard and the script in one file. `vid narrate` compiles its spoken lines for the
configured TTS engine (config.yaml); `//` lines are never spoken.

```
// insight: one sentence the viewer leaves with
// click: the moment it should click, and what is on screen then
# C01 the-shelf                    <- chapter header: "# <chapter id> [free comment]"
// picture: a shelf of a thousand numbered books; one of them hides the number
Somebody hid a number on this shelf, and you may ask one question at a time: higher, or lower?
// picture: the shelf splits at its middle book; the left half dims
Ask about the middle book, and whatever the answer, @half half the shelf is gone. [pause 0.8]
```

- `# <id>` starts a chapter; `video.py` marks it with `self.chapter("<id>")`. `vid narrate --scenes C02,C05`
  re-narrates only those chapters.
- Each spoken line is one **beat**: one `self.say()`, one subtitle cue (split when long). A line can be several
  sentences: start a new line where the picture needs a sync point, a pause, or a new subtitle.
- `//` lines are comments: the insight and click lines, and picture notes that say what the picture does while
  the next line is spoken.

| Syntax | Meaning |
|---|---|
| `{shown\|spoken}` | subtitles show `shown`, the voice says `spoken` (a respelling) |
| `{shown\|/ipa/}` | misaki IPA, used by engines that take phonemes (kokoro); others say `shown` |
| `{shown\|spoken\|/ipa/}` | both |
| `*word*` | focus: the voice accents this word and lets the rest of the clause recede |
| `"words"` | mention: level, slightly raised, lengthened; subtitles keep the quotes |
| `((words))` | aside: lower, narrower, faster, quieter, set off by short breaks |
| `@name` | sync anchor on the next spoken word; video.py uses `self.until("name")` |
| `[pause 0.6]` | silence (seconds) after `.` `?` `!` `:` `;`, never mid-sentence (lint error). At the end of a line: extra silence after the beat while the picture keeps moving |

A `*span of words*` is one focus unit, accented on its last word; mark a single word when only it contrasts.
The engines also understand delivery tags (`[curious]`, `[new]`, …), `**contrast**` and `~given~`; the
guidance doesn't use them, and the lint lists any tags it finds.

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
`vid narrate <dir> --scenes <chapters>`. Whisper hears words, not vowels, so it misses a wrong vowel in a heteronym:
that is what the lint is for.

## Engine capabilities

| engine | respelling | IPA | delivery tags | emphasis | nonverbals |
|---|---|---|---|---|---|
| piper | ✓ | | | | |
| kokoro | ✓ | ✓ | ✓ (pitch range/shift, energy, speed) | ✓ (pitch accent + lengthening) | |
| chatterbox | ✓ | | intensity only | | |
| qwen | ✓ | | ✓ (instruction) | ✓ (instruction) | |
| maya1 | ✓ | | partial (tags) | | ✓ |

Unsupported markup is dropped silently, so a script stays valid across engines.
