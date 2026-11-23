---
name: vid
description: Video explainer. Makes a 3Blue1Brown-style narrated animation (Manim, local TTS voiceover, .srt) explaining a concept, codebase, algorithm or ML idea, or revises one from feedback. Use when the user asks for a video ("make a video about X", "/vid X") or comments on a video this skill made.
argument-hint: "<what to explain>  |  feedback on <video>"
---

You start an explainer video, or a revision, from this conversation. A fresh background agent (the
**producer**) does the production from a written brief, so this conversation is not re-read at every one of
its hundreds of steps. Your job here is the hand-off: the brief carries everything the producer needs.

CLI: `~/explainer-kit/scripts/vid` (`vid --help`). Videos live in `~/explainers/<date>-<slug>/`.

## New video

1. **Toolchain.** `vid doctor`. For MISSING items with a `setup.sh` fix, run `~/explainer-kit/scripts/setup.sh`;
   for apt fixes, stop and give the user the exact command.
2. **Brief.** `vid new <slug>` prints the folder; then `vid link-chat <dir>` records this conversation's
   transcript and workspace, so the producer can search it (`vid convo`) and read the codebase. Fill `brief.md`. The producer never sees this
   conversation, so the brief holds everything from it that shapes the video: what the user asked and why, what
   they already understand and where they got confused, facts, numbers and file paths established here (each
   with its source), and anything the user said about how this video should go. Facts, not a story: the
   producer finds the insight and tells it. Done when the brief alone, plus the sources it names, is enough to
   make the right video.
   Feedback on earlier videos never enters a brief, not even for a remake of the same topic: it changes the
   kit (in the kit's development chat), and each new video must earn its fixes from the kit alone. A remake to
   compare kit versions uses the fixed brief in `~/explainer-kit/benchmarks/<topic>.md` as is (copy it, skip
   `link-chat`); the brief names nothing from the earlier video.
3. **Producer.** Launch a general-purpose agent in the background with this prompt (fill in the folder):
   > Produce the explainer video in `<dir>`. Read `~/explainer-kit/references/production.md` first and follow
   > it. The brief is `<dir>/brief.md`.
4. Tell the user in one line that it is in production and where. When the producer reports, relay its report:
   paths, duration, the insight and the click moment, the story in three lines, accepted QA items, kit
   problems. If it handed off at a chapter boundary (HANDOFF.md), launch a fresh producer with: "Continue the
   explainer video in `<dir>` from `<dir>/HANDOFF.md`. Read `~/explainer-kit/references/production.md` first."

## Revision (feedback on a video this skill made)

1. `vid feedback <slug> "<the user's words, verbatim>"`.
2. Launch the producer in the background with:
   > Revise the video in `<dir>`. Feedback, verbatim: «…». Follow the Revision section of
   > `~/explainer-kit/references/production.md`.
3. As step 4 above.
