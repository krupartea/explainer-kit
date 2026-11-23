# Toolbox

Techniques that often help. Reach for one when a principle (principles.md) is hard to meet at a specific place
in the story. Using a technique because it is listed here is the failure this file must not cause: a video
built from every tool is a template, and viewers sense templates.

## Story

- **Problem first.** A common shape, not a required one: a concrete goal on the running example, the way you'd
  try first, where it breaks, the need in words the viewer could have said, the idea named, how it works (each
  part motivated by the one before), and the opening problem solved. Compress, reorder or drop parts to fit
  the topic.
- **Kill the obvious fix.** When a smart viewer would genuinely try some fix first, try it on screen and let it
  fail with a visible cost. It makes the real idea feel necessary. Skip it when no fix is tempting: a straw man
  is worse than none. If you use it, design the example's numbers so the failure is real.
- **Isolate, then apply.** A new measure or rule shown alone on a clean, minimal case (two shapes, one dial, a
  live value) before it meets the messy example. Choose geometry where the quantity is visibly large.
- **Running example.** One concrete instance carried through the video, so attention goes to the idea rather
  than to new setups. For a codebase: real data from running the code.
- **Concrete before abstract.** Real values first, symbols after; a formula's terms morph out of numbers the
  viewer already watched.
- **A question as the bridge.** The next idea arrives as the answer to a question the last one raised.
- **Close the loop.** The ending returns to the opening picture, now understood.

## Speech

- One idea per sentence, most under ~20 words, and the logic between sentences said out loud (because, so,
  but, instead): it is what a listener most often misses.
- The point of a sentence goes at its end, not after a comma as an afterthought.
- A result is said next to what it is compared with: "nineteen steps, instead of a hundred and forty".
- A mentioned string or value is introduced by its kind ("the key `id`", "the value 0.92"), so it can't be
  heard as part of the sentence.
- A step is named by what it does to what, in words that can't be heard as a nearby familiar operation
  (sorting, thresholding, averaging, keeping the top k).
- One term per concept, the same in speech, on screen and in code.
- About 140 words per minute. Narration fills at most ~80% of the time; the rest is the picture moving without
  words.
- Marks (syntax: narration-markup.md), each only where the voice would otherwise get it wrong:
  - `*word*`: the one word that carries the new or contrasting information.
  - `"words"`: a quoted string or value.
  - `((words))`: a side remark, said lower and quicker.
  - `[pause s]` after a sentence: 0.4–0.6 s after a question; 0.6–1.5 s at the end of a line whose animation
    must be watched.

## Picture

- **Persistent identity.** The same concept is the same object in the same color for the whole video: move it,
  shrink it, dock it; don't redraw it.
- **Contiguity.** A change lands on the word that names it: an `@anchor` on that word and
  `run_time=self.until("anchor")`. Anchor only what must land; everything else flows with the speech.
- **Signaling.** At any moment one thing is the subject: highlight it, or dim the rest.
- **Coherence.** What the current idea doesn't need is dimmed or removed.
- **One new element at a time.**
- **Colors keep one meaning across videos.** `BAD` red: fails. `GOOD` green: works. `FOCUS` yellow: look here
  now (transient). `GREY`/`DIM`: context. `C1`…`C6`: concept identities, assigned when a concept first appears;
  two concepts never share one.
- **Devices** (kit calls; API in manim.md):
  - it breaks / it works: `mark_wrong`, `mark_right`, `strike`. A failure needs a visible consequence (the
    wrong value lands in the output), not only a red tint.
  - look here: `look`, `this_one`, `flash_at`, `dim_others`.
  - a quantity changes: `live_counter`, `live_readout`, bars, `ghost_of` the previous value.
  - the same thing rewritten: `becomes`; a state change: `replaced_by`.
  - related or grouped: `label_arrow`, `brace_label`.
  - a detail: zoom the camera in place (`NarratedCameraScene`), and back out when done.
  - code or data: `code_block` (≤ 12 lines of real code, one line highlighted), `cell_row`.
- **2D unless the third dimension carries the point** (a surface whose height is a value, geometry in space).
  Then one slow camera move to establish depth, and a fixed camera while explaining.
- **Pacing.** After a reveal, hold: the remaining time is the viewer's thinking time. Small changes `RT_FAST`,
  most `RT_NORMAL`, big rearrangements `RT_SLOW`.

## Length

About 5 minutes by default (~700 words); a single narrow question is a 1–2 minute clip; "explain the whole
system" up to ~10. The insight sets the real length: stop when it has landed.
