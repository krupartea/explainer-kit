---
name: vid
description: Video explainer. Makes a 3Blue1Brown-style narrated animation (Manim, local TTS voiceover, .srt) explaining a concept, codebase, algorithm or ML idea, or revises one from feedback. Use when the user asks for a video ("make a video about X", "/vid X") or comments on a video this skill made.
argument-hint: "<what to explain>  |  feedback on <video>"
context: fork
background: true
---

You make one explainer video, or revise one. The conversation you were forked from is the brief: what the
user asked about, what they already know, which code or docs were read. Everything runs locally.

- Kit (this folder): `~/explainer-kit`. CLI: `~/explainer-kit/scripts/vid` (`vid --help` lists commands).
- Videos: `~/explainers/<date>-<slug>/` (narration.txt, scenes.py, audio, renders, qa/, `<slug>.mp4`, `<slug>.srt`).
- Write only inside the video's folder and through `vid feedback`. The kit's code, references, lexicon and
  config change only in the kit's own development chat.

If the request is feedback on an existing video, go to **Revision**.

## 1. Toolchain

Run `vid doctor`. For MISSING items with a `setup.sh` fix, run `~/explainer-kit/scripts/setup.sh` (downloads
models; minutes). For apt fixes, stop and report the exact command for the user. Done when doctor exits 0.

## 2. Brief

`vid new <slug>` prints the video folder. Fill its brief.md from the conversation and from evidence: for a
codebase, read the relevant code and run it to get real values for the running example. Done when every field
of brief.md is filled and every number you plan to show has a source listed.

## 3. Script

Read `references/storytelling.md`, `references/delivery.md` and `references/narration-markup.md`, then
write narration.txt. Check the storytelling gate (X named only after the need is felt), then mark delivery:
every contrast has its focus word, every pause sits between sentences, every mood an arc moment that earns it.
Then `vid narrate <dir>`.
Done when the lint passes and every ⚠ row in qa/narration_qa.md is fixed or explained in brief.md.

## 4. Scenes

Read `references/visual-devices.md`. For each beat choose a device and write it as a comment above that
beat's `self.say()`. Write scenes.py with `from manim import *` and `import kit` (house names as
`kit.<name>`), one `kit.NarratedScene` per scene header.
`vid render <dir> --preview`, then Read every `qa/sheets/<scene>.png` (one frame per beat end); for a
mid-beat moment use `vid frame <dir> S05@3.2 --preview`.
Fix overlaps, text off-frame or below `SAFE_BOTTOM`, unreadable sizes, beats whose frame shows nothing new.
Then `vid render <dir>` and check the sheets once more.
Done when every beat's frame shows its chosen device clearly at 1080p.

## 5. Deliver

`vid assemble <dir>`. Report: the .mp4 and .srt paths, duration, the arc in three lines (need → X → payoff),
and any QA item you accepted rather than fixed.

## Revision

1. `vid feedback <slug> "<the user's words, verbatim>"`, before any change.
2. Map each timestamp to a scene and beat with the video's .srt and `logs/<scene>.json`.
3. Change only the affected scenes: narration.txt lines → `vid narrate <dir> --scenes S03,S05`;
   scenes.py → `vid render <dir> S03 S05` (preview first if the layout changed), check their sheets.
4. `vid assemble <dir>`; report what changed per feedback item.

## Machine

This machine has no swap and has frozen under load; run everything through `vid`, which caps memory.
`vid narrate` checks the GPU first: when another job holds it, it narrates on CPU instead (slower, never
competing). Renders are CPU-only; keep `--jobs` at 4 or fewer.
