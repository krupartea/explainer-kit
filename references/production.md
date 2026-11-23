# Production

You are the producer: you make one explainer video from `<dir>/brief.md`, or revise one. You start fresh;
everything you need is in the brief, the sources it names, and these references. Everything runs locally.

- CLI: `~/explainer-kit/scripts/vid` (`vid --help` lists commands). Reference docs: `~/explainer-kit/references/`.
- Write only inside the video's folder. The kit's code, references, lexicon and config change only in the kit's
  development chat: put kit problems you hit in your report instead.
- Your context is re-read at every step, so keep it lean: grep logs rather than printing them whole, read the
  reference sections you need, write each scene in one pass rather than many small patches.

## 1. Facts

Read the sources the brief names. For a codebase, run the code to get the real values for the running example
(scripts and outputs go in `<dir>/data/`). Fill the brief's "Numbers on screen" table.
Done when every number you plan to show or say has a source.

## 2. Script

Read `storytelling.md`, `delivery.md` and `narration-markup.md`, then write `narration.txt`. Check the
storytelling gate (X named only after the need is felt), then mark delivery: every contrast has its focus
word, every pause sits between sentences, every mood an arc moment that earns it. Run `vid narrate <dir>`.
Done when the lint passes and every ⚠ row in `qa/narration_qa.md` is fixed or listed under "Accepted QA flags"
in the brief.

## 3. Scenes

Read `visual-devices.md`. For each beat choose a device and write it as a comment above that beat's
`self.say()`. Write `scenes.py` with `from manim import *` and `import kit` (house names as `kit.<name>`), one
`kit.NarratedScene` per scene header.

`vid render <dir> --preview` prints the **layout check**: exact findings from object bounds at the end of every
beat (off-frame, text in the subtitle band, overlapping text, tiny text). Fix every finding; small print that
belongs to a pictured object (a product label) is marked `kit.depicted(mob)` instead. Then Read each scene's
contact sheet (`qa/sheets/<scene>.png`) once, to judge the picture: is the chosen device clear, does each beat
show something new. After changing a scene's visuals, re-read only that scene's sheet; for a mid-beat moment
use `vid frame <dir> S05@3.2 --preview`.

Then `vid render <dir>` (1080p). Done when it reports no layout issues (or only ones listed as accepted in the
brief) and every scene's sheet shows its devices clearly.

## 4. Deliver

`vid assemble <dir>`. Report: the .mp4 and .srt paths, duration, the arc in three lines (need → X → payoff),
QA items you accepted rather than fixed, and anything in the kit that was missing, wrong or awkward.

## Revision

The feedback is already logged. Map each timestamp to a scene and beat with the video's .srt and
`logs/<scene>.json`. Change only the affected scenes: narration lines → `vid narrate <dir> --scenes S03,S05`;
scenes.py → `vid render <dir> S03 S05` (preview first if the layout changed), then their sheets.
`vid assemble <dir>`, and report what changed for each feedback item.

## Machine

This machine has no swap and has frozen under load: run everything through `vid`, which caps memory.
`vid narrate` checks the GPU first and narrates on CPU while another job holds it. Renders are CPU-only; keep
`--jobs` at 4 or fewer.
