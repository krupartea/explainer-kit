# Visual devices

The house visual language. **One device, one meaning, every video**: the viewer learns it once and then reads
it for free. Pick each beat's device from this catalog by what the beat must communicate; the kit call
implements it in house style (`import kit`, then `kit.<name>`; see kit/components.py, kit/style.py).

Grounding: Mayer's multimedia principles (signaling, coherence, temporal contiguity, segmenting, pre-training,
redundancy) and Grant Sanderson's practice (concrete before abstract, motivate before define, one persistent
running example).

## Principles that shape every beat

- **Contiguity:** the visual change lands on the word that names it. Put an `@anchor` on that word and time the
  animation with `run_time=self.until("anchor")`. Never show the thing seconds before or after it is said.
- **Signaling:** at any moment one thing is the subject; it is highlighted (`look`, `this_one`) or everything
  else is dimmed (`dim_others`).
- **Coherence:** remove or dim what the current idea doesn't need. A frame holds the running example plus the
  current idea's marks, and little else.
- **Segmenting:** one new element per beat. A beat that introduces three things becomes three beats.
- **Redundancy:** on-screen text is labels, keywords, values and code, never the narration sentence (subtitles
  live in the .srt, toggled by the viewer).
- **Persistent identity:** the same concept is the same mobject in the same color across scenes (move it,
  shrink it, dock it in a corner; don't redraw a new one).

## Color (fixed meanings)

| Color | Meaning | Use |
|---|---|---|
| `BAD` red | fails, wrong, rejected | `mark_wrong`, `strike`, failure titles |
| `GOOD` green | correct, works, accepted | `mark_right`, payoff |
| `FOCUS` yellow | look here *now* (transient) | `look`, `this_one`, `event` |
| `GREY` / `DIM` | context, secondary | captions, axes, background structure |
| `C1`…`C6` | concept identities | assign in the first scene that shows the concept; keep for the whole video |

Write the concept-color mapping as a comment at the top of scenes.py. Two concepts never share a color.

## Catalog: by what the beat must say

### "This is wrong" / "it breaks"
- `mark_wrong(mob)`: red tint + Wiggle shake. The failure moment: a wrong value, a crash, a rejected candidate.
  Land it on the word naming the failure (`@wrong`).
- `strike(mob)`: line through a candidate that is ruled out but still worth reading.
- `badge(False)`: red cross beside a result in a comparison or checklist.
- A failure needs a visible *consequence* (the wrong value lands in the output slot), not only a red tint.

### "This is right" / "it works"
- `mark_right(mob)`, `badge(True)`. Reserve for real success: the payoff and confirmed results.

### "Look here" / "this one among several"
- `look(mob)`: transient pulse, element returns to normal. For "notice this".
- `this_one(mob)`: circle around one item in a crowd (one box among 20).
- `flash_at(point)`: flash at the place something happened (a match, a write, a hit).
- `dim_others(...)`: when the rest of the frame stays but stops being the subject.

### "It flows / it's a process"
- `stage_box(label)`: one component or stage. `pipeline([...])`: stages left to right, arrows between. Data flows left to right, always; time flows left
  to right or top to bottom, always.
- A dot or token moving along the arrows (`MoveAlongPath`) for "this item goes through".
- `step_counter(n)` for algorithms with numbered steps; a log list that grows on the side for history.

### "These are related"
- `label_arrow(a, b, "next")`: a named relation. Curved (`curved=-TAU/6`) when it would cross other content.
- `brace_label(group, "one key")`: grouping several items under one name.

### "Same thing, rewritten" / "this becomes that"
- `becomes(a, b)` (TransformMatchingShapes): equivalence; shared parts stay put. Concrete numbers becoming a
  formula, code becoming its simplified form.
- `replaced_by(a, b)`: a state change (old value replaced by new).

### "This is what the new measure means" (concept sandbox)
- Before applying a new measure or rule to the messy running example, show it alone on a clean, minimal case
  with a dial: two boxes (or two vectors, two distributions) on an empty stage, one of them moving, resizing,
  sliding apart, and the measure's live value updating (`kit.live_readout(measure, a, b, "IoU")`). Say
  what its extremes mean ("1: the same box; 0: they don't touch"). 15–25 s, its own scene; then return to the
  running example and apply it.
- Choose geometry where the quantity is visibly large: overlaps you can see, not slivers.

### "A quantity changes"
- `live_counter(start, label=...)` with `tracker.animate.set_value(x)`: live numbers (cost, reads, latency). Always
  with units or a label.
- Bars growing / shrinking for comparisons of 2–5 magnitudes; a number line or axis when position matters.
- `ghost_of(mob)` of the previous value when the change itself is the point.

### "Without vs with" / "before vs after"
- `split_screen("without X", "with X")`: identical layout on both sides, same running example, so only the
  difference differs. Left = old/BAD, right = new/GOOD.

### "Zoom into a detail"
- `NarratedCameraScene` + `self.camera.frame.animate.scale(0.4).move_to(x)`: the detail grows in place, so
  the viewer keeps track of where it is. Zoom back out when the detail is done.

### "What it looks like in code / data"
- `code_block(src, highlight=[3])`: short excerpts (≤ 12 lines), the relevant line highlighted. Real code from the
  repo, trimmed. `cell_row([...], index=True)` for arrays, buffers, sequences; a grid of `cell_row`s for matrices.

### "A named idea"
- `chip("overlap score", C3)`: concepts and steps as chips. A recap strip of chips docks at the top while the
  mechanism ideas run, the current one highlighted.

## 2D or 3D

Default 2D. Use 3D (`NarratedThreeDScene`) only when the content has three real dimensions *and* the third
dimension carries the point: a surface whose height is a value (loss landscape), geometry in space, a
tensor's three axes, a projection from 3D to 2D that is itself the subject. Then: one slow camera move to
establish depth, then a fixed camera while explaining. Data that is not spatial stays 2D (bars, tables,
graphs), even when a 3D chart would look richer.

## Pacing

- Hold after a reveal: the beat's remaining time (`self.hold()`) is the viewer's thinking time.
- Run times: `RT_FAST` 0.5 s for small changes, `RT_NORMAL` 1 s, `RT_SLOW` 1.6 s for big rearrangements.
- Scene ends: clear the frame (FadeOut) unless the next scene continues the same picture.

## Layout

- Frame 14.2 × 8 units. Keep essentials above `SAFE_BOTTOM` (y = −3): players draw subtitles there.
- Title or recap strip at the top (`to_edge(UP)`); the running example left or center; explanations right.
- Text sizes from the type scale (`FS_TITLE` … `FS_SMALL`); nothing smaller than `FS_SMALL`.

## Manim pitfalls

- House names are reached only as `kit.<name>`, so your names can't collide with them. `vid render`
  rejects what could still collide: rebinding `kit`, module-level names that shadow a Manim name (`frame = …`),
  and rebinding Manim classes or constants anywhere (`UP = …`).
- Don't combine `FadeIn(m)` with an animation on the same mobject in one `play()` (e.g. `mark_right(m)`):
  one of them wins and `m` can end invisible. Fade in first, then mark.
- Two animations on the same submobject in one `play()` fight; the later one wins and positions drift.
  Split them into consecutive plays, or animate the parent once.
- Pulse a labelled box as a whole group (`look(group)`), not its outline alone: the outline is redrawn on top
  and hides the word inside.
- `AnimationGroup` re-stacks its parts on top of the scene in animation order, so a box animated after its
  label covers it. Pass separate animations to `play(*anims)` instead; the kit's helpers return single
  animations or lists for that reason (`self.play(*kit.dim_others(...))`).
- `FadeOut(group)` misses parts that entered the scene separately (e.g. via `TransformFromCopy`): those are no
  longer inside the group. Fade them explicitly, or collect what's on screen with `self.mobjects`.
- Changing one text into a different text: `FadeTransform` or `TransformMatchingShapes`, never `Transform`
  (it morphs letters into unreadable shapes mid-animation).
- Timing: `self.portion(f)` is a fixed share of the beat; `self.left(f)` is a share of what remains, so
  chained `left()` calls shrink. Use `portion()` for planned splits and `left()` for the beat's last animation.
- Inspect any moment, not just beat ends: `vid frame <dir> S05@3.2` or `vid frame <dir> 2:41`.
- Layout bugs are found for you: `vid render` checks every beat's end frame from object bounds (off-frame,
  subtitle band, overlapping text, tiny text). Animating a few letters of a `Text` splits it into loose
  glyphs; the check still sees them. Mark intentional small print on a pictured object with `kit.depicted(m)`.
