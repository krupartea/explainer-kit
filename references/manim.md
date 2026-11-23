# Manim with the kit (technical reference)

Facts about the code, not advice about style (that is principles.md and toolbox.md).

## video.py

One file, one continuous scene, class `Video`. Chapters follow narration.txt's `# C01 …` headers; objects on
screen carry over from one chapter into the next.

```python
from manim import *
import kit


class Video(kit.NarratedScene):          # or kit.NarratedCameraScene to zoom, kit.NarratedThreeDScene for 3D
    def construct(self):
        self.chapter("C01")              # raises if the next beat isn't C01's first: code and narration in step
        self.say()                       # the next beat's audio starts now
        self.play(FadeIn(a), run_time=self.portion(0.3))
        self.play(Create(b), run_time=self.until("overlap"))   # ends exactly on the word after @overlap
        self.hold()                      # wait out the beat and its pause
        ...
```

- `say()` starts the next beat (one narration line); `hold()` waits until it and its trailing pause end.
- `portion(f)`: a fixed share of the whole beat. `left(f)`: a share of what remains, so chained calls shrink;
  use it for a beat's last animation. `until("name")`: time until the `@name` word; `wait_until("name")`.
- Helper functions and data live in video.py itself (or a module next to it). Keep the running example's data
  in one place (e.g. a dict at the top, or `data/*.json` written by your scripts).

## Render and inspect

- `vid render <dir> --preview` (854×480, 15 fps) while working; `vid render <dir>` (1080p) before
  `vid assemble <dir>`. Manim's cache is on: an edit re-renders only the animations whose picture changed, but
  a change early in the scene can change everything after it.
- Each render writes `qa/sheets/<chapter>.png` (a frame every 4 s of the chapter, plus its last moment) and
  `qa/layout.md`. The layout check runs at every beat end and every 4 s: off-frame, subtitle band, overlapping
  text, tiny text. Mark intentional small print on a pictured object with `kit.depicted(m)`.
- `vid frame <dir> C03@12.5 [--preview]`: any moment, 12.5 s into chapter C03; `vid frame <dir> 2:41`: a moment
  of the assembled video.

## Kit names

Reached only as `kit.<name>`. Text: `T(text, size, color)`, `mono`, `rich` (Pango markup with `span`), `tex`
(LaTeX if installed, else mono), `live_number`, `centered_text`, `fit_to`, `depicted`. Data: `cell_row`,
`code_block`. Relations: `label_arrow`, `brace_label`. Animations: `mark_wrong`, `mark_right`, `look`,
`this_one`, `flash_at`, `dim_others`, `live_readout`, `strike`, `becomes`, `replaced_by`, `live_counter`,
`ghost_of`. Docstrings in kit/components.py.

Style constants: colors `INK GREY DIM BAD GOOD FOCUS C1…C6`; type scale `FS_TITLE 56, FS_HEAD 40, FS_BODY 32,
FS_LABEL 26, FS_SMALL 20, FS_CODE 26` (nothing smaller than `FS_SMALL`); run times `RT_FAST 0.5, RT_NORMAL 1.0,
RT_SLOW 1.6`. Frame 14.2 × 8 units; keep essentials above `SAFE_BOTTOM` (y = −3), where players draw
subtitles, and within `SAFE_X` 6.6 / `SAFE_TOP` 3.55.

## Pitfalls

- `vid render` rejects names that could collide with the kit or Manim: rebinding `kit`, module-level names that
  shadow a Manim name (`frame = …`), rebinding Manim classes or constants anywhere (`UP = …`).
- Don't combine `FadeIn(m)` with another animation on the same mobject in one `play()` (e.g. `mark_right(m)`):
  one wins and `m` can end invisible. Fade in first, then mark.
- Two animations on the same submobject in one `play()` fight; the later wins and positions drift. Split them,
  or animate the parent once.
- Pulse a labelled box as a whole group (`look(group)`), not its outline alone: the outline is redrawn on top of
  the word inside.
- `AnimationGroup` re-stacks its parts on top in animation order, so a box animated after its label covers it.
  Pass separate animations to `play(*anims)`; kit helpers return single animations or lists for that reason.
- `FadeOut(group)` misses parts that entered separately (e.g. via `TransformFromCopy`). Fade them explicitly,
  or collect what's on screen with `self.mobjects`.
- Changing one text into a different text: `FadeTransform` or `TransformMatchingShapes`, never `Transform`
  (letters morph into unreadable shapes mid-animation).
- `set_opacity` on an outline-only shape also fills it; dim outlines with `set_stroke(opacity=…)`.
- `.move_to(p)` centers an object's bounding box on p; to place an arrow so it starts at a point, use
  `put_start_and_end_on` or shift by the offset of its start.
- Animating a few letters of a `Text` splits it into loose glyphs; the layout check still sees them.
