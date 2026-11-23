# Delivery

A good teacher's voice shows the structure of an idea: which word is new, what contrasts with what, where to
wait for the answer. The narration marks that structure with **focus**, **pauses** and **moods**, and the
voice renders it. Each mark carries meaning, so place it by meaning, never for variety.

## Focus: `*word*`

Focus is the one word that carries the new information or the contrast. The voice gives it a pitch accent on
its stressed syllable and a little length, and lets the rest of the clause recede (post-focus compression).

- **Mark only the contrasting word.** "But that is the *departure* date." The contrast is departure vs
  arrival; "date" is shared and already known, so it stays low.
- **A multi-word unit** that is new as a whole (a number, a name, a term) is one span, accented on its last
  word as in natural speech: "*one point nine* seconds", "the *search radius*". `*departure date*` would
  accent "date", the wrong word, so the lint flags every span for a second look.
- **Several accents in a row** for insistence: mark each word: "on *every* *single* frame".
- **Given information never takes focus**: anything already said or already on screen.
- **Contrast pairs** mark the differing word on both sides:
  "Not the *departure* date, but the *arrival* date." / "It took *19* steps, not *140*."
- **Correcting an expectation**: focus the corrected word. "The value is *below* the key, not after it."
- **A new term**, first mention only: focus where speech stresses it. Compound nouns stress their first word,
  so mark it alone: "This is called the *overlap* score." Later mentions are given: unmarked.
- **Numbers**: focus the number being compared, never its unit.
- **Budget**: one focus per clause (two for a contrast pair, more only for insistence); most sentences have none.
- **Word order**: post-focus words recede, so when the point is the last word, end the sentence on it
  ("The arrival is printed *below*.") rather than burying it mid-clause.

## Pauses: punctuation, and `[pause s]` between sentences

The voice pauses naturally at commas and sentence ends, with the right phrase-final intonation; write the
punctuation a teacher would breathe at. A silence inserted mid-sentence sounds unnatural, so `[pause]` goes
only between sentences (the lint enforces it):

- **0.4–0.6 s** after a question, before its answer: "So which box holds the arrival? [pause 0.5] The one *below*."
- **0.4–0.6 s** after a surprising result, to let it land; before the payoff.
- To set a key term apart, give it its own short sentence: "This score has a name. [pause 0.3] The *overlap* score."

## Moods: `[mood]` at the start of a beat

Moods mark the emotional beats of the arc (references/storytelling.md), not decoration:

| Arc moment | Mood |
|---|---|
| the naive attempt fails | `[disappointed]` |
| a hazard, a trap, a gotcha | `[warning]` |
| the question that opens the next need | `[curious]` |
| the moment it works, the payoff | `[triumphant]` (`[excited]` only for a genuine surprise) |
| a definition, a careful claim | `[serious]` |
| a step-by-step walk-through | `[calm]` |

Most beats stay neutral; the lint warns when more than ~35% carry a mood. A mood colors its whole beat, so give
the emotional sentence its own line.

## Voice and picture together

The focused word is where the visual accent lands: put the `@anchor` on it (or on the word before, when the
animation must finish on it), so `mark_wrong` shakes exactly as "*departure*" peaks. A pause between
sentences gives a reveal room to start: `Look below the key. [pause 0.3] @reveal The *arrival* date.`

## Pace

Speed is set per voice in config.yaml (0.92× by default). Slow the content, not the voice: for a definition or
the key mechanism, use shorter sentences; `[calm]` slows slightly.
