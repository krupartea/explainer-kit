# Delivery: writing for the ear

The listener hears each sentence once and can't re-read it. Prose written for the eye (dense, every clause equal
weight, logic left implicit) becomes a flow of words when spoken: the listener has to guess what the point is,
what it is compared to, and how one sentence follows from the last. A good teacher makes all three **audible**.
This catalog is the spoken counterpart of visual-devices.md: pick devices by what the line must do, and mark
them in narration.txt (syntax in narration-markup.md).

## The five audibility rules

Every line passes all five; the cold read (production.md) checks them.

1. **The point is audible.** Each sentence has one nucleus, the new or contrasting information. It sits at
   the end of its clause (end-weight) and carries the focus mark. Commas never split the nucleus off from what
   it completes.
2. **The logic is audible.** A sentence that answers, explains, contradicts or concludes says so with a
   connective: *because*, *so*, *but*, *instead*, *which means*, *no:*. A question is answered by a line that
   starts by answering it.
3. **The yardstick is audible.** A number, count or result is said next to what it should be or what it beats:
   "five words, from a line that has *two*", "*19* steps instead of *140*".
4. **Mentions are audible.** A string, word, value or label from the example is introduced by its kind,
   "the word TOTAL", "the score 0.92", "the box at 0.64", so it can't be heard as part of the sentence.
5. **The words fit only one picture.** Each step or claim is worded so it can't be heard as a different,
   familiar operation. "Keep the best" sounds like keeping only the top box (thresholding); "take the
   highest-scoring box and remove its duplicates" can only mean NMS's step.

## The prosodic palette

Each mark below makes the voice do something a listener already understands without being told, the way the
Wiggle means "wrong" on screen. Pick the mark by what the listener should understand at that moment.
Grounding: new vs shared information is carried by falling ("proclaiming") vs fall-rise ("referring") tones
(Brazil's discourse intonation); a low-then-high accent (L+H*) evokes the alternative being contrasted;
parentheticals are spoken lower, narrower, quieter and faster; a new topic starts with a pitch reset.
Kokoro realizes each one by editing its own predicted pitch, timing and energy (tts/engines/kokoro/prosody.py).

| The listener should understand | Mark | What the voice does |
|---|---|---|
| this word is the point (new information) | `*word*` | accent peaking on the stressed syllable; the rest of the clause recedes |
| this, as opposed to that; better vs worse | `**word**` on each side | a dip, then a steep, higher rise; longer; the alternative is heard |
| you already know this one (a callback) | `~words~` | lower pitch over the span, a fall-rise on its last word: "as you know" |
| this exact word or value (a quotation) | `"words"` | level, slightly raised, lengthened; subtitles show the quotes |
| a side note you can skip | `((words))` | lower, narrower, faster, 4 dB quieter, set off by short breaks |
| a new topic starts here | `[new]` at line start | pitch reset (~2.5 semitones) that settles over the first second |
| a new concept is being defined | `[define]` | ~10% slower, wider pitch range; put the term last and mark it `*…*` |
| here is a puzzle: think | `[curious]` | rising, wider range; follow with `[pause 0.5]` before the answer |
| being confused here is normal | `[reassure]` | lower, narrower, softer, slower; name the confusion in words |
| here is the answer / a surprise | `[reveal]` | higher and wider; set it up with a colon |
| this fails / is worse | `[disappointed]` | lower, narrower, slower |
| this works / is better | `[triumphant]` | higher, wider |
| careful, a trap | `[warning]` | lower, firm, slower |
| summing up | `[recap]` | lower, steady, compressed, slightly slower |
| a calm step-by-step walk-through | `[calm]` | narrower, slightly slower |
| let it land / watch the picture | trailing `[pause s]` | silence after the line while the animation plays |

Combining: a line can carry one structural tag and one feeling, `[new] [curious] So how do we…?`.
Marks inside a line combine freely: `Remember ~the price box~? It reads the word "TOTAL" **four** times.`

## Devices

### Focus: `*word*` (rule 1)
Mark the one word that carries the contrast or the new information; the voice puts a pitch accent on its
stressed syllable and lets the rest of the clause recede.
- Mark only the contrasting word: "the *departure* date" (departure vs arrival; "date" is shared).
- A unit that is new as a whole is one span, accented on its last word: "*one point nine* seconds".
  `*departure date*` would accent "date", the wrong word; the lint flags every span for a second look.
- Compound terms stress their first word: "the *overlap* score".
- Given information (already said, already on screen) never takes focus.
- Budget: one focus per clause, two for a contrast pair; many sentences have none.

### End-weight: the point last (rule 1)
Put the nucleus at the end, in the same clause as what it completes.
- ✗ "We want to read this receipt line, one word at a time." (the comma splits the point off; it sounds like
  an afterthought)
- ✓ "We want to read this line *one word at a time*."

### Question → answer (rule 2)
A question opens the next need; the answer starts by answering, after a pause.
- ✗ "So why not raise the score threshold? The duplicates score high too."
- ✓ "So why not raise the score threshold? [pause 0.5] *Because* the duplicates score high too."
- Give the question `[curious]`; give the answer no mood unless it is the payoff.

### Expected vs actual (rule 3)
Say the yardstick right next to the result. Two short sentences hit harder than one long one.
- ✗ "Count the words, and you get five."
- ✓ "Count the words: *five*. [pause 0.3] The line has *two*."

### Use–mention (rule 4)
- ✗ "The recognizer reads TOTAL four times." (TOTAL sounds like the adjective "total")
- ✓ "The recognizer reads the word TOTAL *four* times."
- On screen and in subtitles the mentioned item is shown as itself (a chip, quotes); in speech, its kind
  carries the quotation marks.

### Precise verbs (rule 5)
Name each step by what it does to what, in words that rule out the nearby wrong idea.
- ✗ "Keep the best." (heard as: keep only the top box)
- ✓ "Take the highest-scoring box. Keep it, and remove every box that overlaps it too much."
- Check each step name against familiar operations the viewer might confuse it with (thresholding, sorting,
  averaging, top-k) and reword until only one reading is left.

### Kill the obvious fix (the leitmotif)
Before X appears, try the fix a smart viewer would try first, on a counterexample designed to break it, and
let it fail with numbers. This is what makes the need for X felt (storytelling.md).
- "So why not just raise the score threshold? [pause 0.5] Because the duplicates score high too: at
  *zero point seven*, the word TOTAL still comes back three times, and the price, at 0.64, is *gone*."
- Choose the example's numbers so the obvious fix fails *and* costs something real.

### Setup → punch → breath
A longer setup sentence, then a short punch line, then silence to let it land.
- "Every box above the threshold gets read. [pause 0.3] Five boxes. [pause 0.3] *Five* words."
- End the beat with a trailing pause when the picture needs watching: `... is *gone*. [pause 1.0]`

### Signposts
Short openers make the structure audible: "First, the problem." "Now, the algorithm." "Step two."
A new chapter starts with a signpost line of its own.

### Rhythm
Vary sentence length; fragments are fine for punches ("Five boxes."). Lists of steps come in threes or fours,
each step a parallel phrase. The payoff repeats the opening's words, so the viewer hears the loop close.

## Pauses: punctuation, `[pause s]` between sentences, trailing `[pause s]` for breath

The voice pauses naturally at commas and sentence ends with the right phrase-final intonation; write the
punctuation a teacher would breathe at. A silence inserted mid-sentence sounds unnatural, so `[pause]` goes
only after `.` `?` `!` `:` `;` (the lint enforces it).

| Where | Length |
|---|---|
| after a question, before its answer | 0.4–0.6 s |
| after a punch line or a surprising number | 0.3–0.6 s |
| end of a beat whose animation must be watched (trailing `[pause s]`) | 0.6–1.5 s |
| between chapters (trailing pause on the chapter's last beat) | 1.0–1.5 s |

**Room to breathe:** narration fills at most ~80% of a scene's time. The rest is pictures moving without
words: after "Watch.", during a step-by-step trace, after the payoff.

## How often

Marks carry meaning only when they are rare. Most lines have one focus at most and no tag; the lint warns when
more than ~35% of lines carry a feeling. A tag colors its whole line, so give the emotional or structural
sentence a line of its own.

## Voice and picture together

The focused word is where the visual accent lands: put the `@anchor` on it, so `mark_wrong` shakes exactly as
"*departure*" peaks. A trailing pause gives an animation room to play after its sentence.

## Pace

Speed is set per voice in config.yaml (0.92× by default). Slow the content, not the voice: shorter sentences,
pauses after punches, silent holds for pictures.
