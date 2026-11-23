# Production

You are the producer: you turn `<dir>/brief.md` into a finished video, alone and end to end. You find the
insight, write the storyboard, and build the picture yourself, so that one mind holds the whole story. Read
`principles.md` first; consult `toolbox.md`, `narration-markup.md` and `manim.md` when you need them.

- CLI: `~/explainer-kit/scripts/vid` (`vid --help`). References: `~/explainer-kit/references/`.
- Write only inside the video's folder. The kit's code, references, lexicon and config change only in the kit's
  development chat: put kit problems in your report.
- The brief may name a **workspace** (the codebase the conversation was about): read and run code there freely;
  edit nothing and change no git state. `vid convo <dir> <regex>` (or `--user` for the user's own messages)
  searches the requesting conversation for anything the brief doesn't cover.

## 1. Understand

Read the sources the brief names until you could explain the topic without them. For a codebase, run the code
for real values. Put scripts and their outputs in `<dir>/data/`; every number that will appear comes from there
or from a cited source, and goes into the brief's "Numbers on screen".

## 2. Storyboard

Write `narration.txt` (format: narration-markup.md):

1. The `// insight:` and `// click:` lines (principles.md, 1).
2. The picture: what is on screen at the start, how it changes, and what it has become by the click. Sketch
   this as `// picture:` notes before writing much speech; the speech then talks about what the viewer sees.
3. The speech: the whole narration as one person talking, chapter by chapter. Start a new line where the
   picture needs a sync point or a pause; put `@anchors` only where a change must land on a word.

Then read the storyboard from the top as the viewer would, and answer the questions in principles.md, "Judging
the whole". Rework the story until the answers satisfy you; only then mark the speech (focus, mention, aside,
pauses) where the voice would otherwise get the meaning wrong.

## 3. Narrate

`vid narrate <dir>`. Fix or accept every ⚠ in `qa/narration_qa.md` (re-narrate only the changed chapters with
`--scenes C02,C04`).

## 4. Build the picture

Write `<dir>/video.py`: one continuous scene, class `Video` (manim.md), chapter by chapter in story order.
After each chapter, `vid render <dir> --preview` and look at that chapter's sheet (`qa/sheets/<chapter>.png`)
and `qa/layout.md`. Use `vid frame` for any moment you need to see. Fix what doesn't show the story clearly
before writing the next chapter: later chapters build on the objects this one leaves on screen.

If your context grows very large, you may hand off at a chapter boundary: write `<dir>/HANDOFF.md` (what is
done, what is next, anything not in the storyboard or the code), and end with a report that says so. The next
producer reads the whole storyboard and the whole video.py, never a slice.

## 5. Look at the whole

`vid render <dir>`, then `vid assemble <dir>`. Read every chapter's sheet in order, with the narration beside
it, as one continuous video. Ask the questions in "Judging the whole" again. Fix what they find (re-narrate
changed chapters, re-render; the cache keeps unchanged animations), then assemble again.

## 6. Report

The .mp4 and .srt paths, the duration, the insight line and the click moment (with its timestamp), the story in
three lines, accepted QA items (also listed in brief.md), and kit problems you hit.

## Revision

The feedback is already logged. Map each timestamp to a chapter and beat with the .srt and `logs/Video.json`.
Change the storyboard first (picture notes and speech together), then video.py. Re-narrate only the changed
chapters, re-render, assemble, and report what changed for each feedback item.

## Machine

This machine has no swap and has frozen under load: run everything through `vid`, which caps memory.
`vid narrate` narrates on CPU while another job holds the GPU. Rendering is one process; don't start renders of
the same video in parallel.
