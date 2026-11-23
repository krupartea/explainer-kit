# Brief

<!-- Benchmark brief: the fixed input for every NMS video, so videos made by different kit versions can be
     compared. Copied from the first NMS video's brief (2026-11-23); never add feedback on earlier videos. -->

- **Topic:** Why object and text detectors need non-maximum suppression (NMS), how NMS works, and the
  trade-off of its IoU threshold.
- **Viewer:** an ML/OCR engineer. Knows a detector outputs boxes with confidence scores and has used
  detection outputs, but has never looked closely at NMS: why the raw output is full of duplicates, what IoU
  is exactly, why the threshold matters.
- **The need (felt before the name):** run a detector on an image and keep every box above a score threshold:
  one word or object comes back as a cluster of 5–10 heavily overlapping boxes. Counting objects, cropping
  words for a recognizer, or drawing results all break (one word gets read 7 times). Raising the score
  threshold doesn't fix it: the duplicates have high scores too, and a weaker true object disappears first.
- **Running example:** a short line of text (or a few objects) where the detector fires a cluster of
  overlapping boxes on each item. Use concrete, consistent box coordinates and scores (e.g. one cluster with
  scores 0.92, 0.88, 0.85, 0.71 and a neighbouring, separate word at 0.64). Invent them deliberately and keep
  them consistent across scenes; compute every IoU you show from those coordinates (a small script in
  `data/`), so the numbers on screen are exact.
- **Payoff:** the viewer can run greedy NMS by hand on a cluster, explain why it keeps one box per object,
  and predict what a lower or higher IoU threshold does (too low merges real neighbours, e.g. two adjacent
  words or two overlapping people; too high leaves duplicates).
- **Target length:** about 2 minutes (a clip: one failure, one idea, one payoff; keep the problem-first order).

## From the conversation

Workspace (codebase the conversation was about, read-only; empty if none):
Anything this section doesn't cover can be searched with `vid convo <dir> <regex>` / `--user`.

- What the user asked, in their words, and why they want it: a benchmark run: the same topic and brief
  are produced by successive kit versions to see whether the videos get better. The video should be a
  proper, finished clip.
- What they already understand; where they were confused: n/a. Assume the viewer profile above.
- Facts and numbers established in the conversation, each with its source: none; derive every number from
  the running example's coordinates.
- How they want this video to go: problem first (raw detector output → duplicates → why a score threshold
  can't fix it → the need: keep one box per object), then IoU as the measure of "same object", then greedy NMS
  step by step on the cluster (sort by score, keep the best, suppress boxes with IoU above the threshold,
  repeat), then the threshold trade-off on two adjacent words, then the payoff (clean
  output, one box per item).

## Sources

General knowledge of greedy NMS (sort by score; keep the top box; drop remaining boxes whose IoU with it
exceeds the threshold; repeat until none remain). IoU = area of intersection / area of union. No
repository is involved.

## Numbers on screen

<!-- Filled by the producer. -->

| number | where (scene:beat) | source (file / command output) |
|---|---|---|

## Accepted QA flags

<!-- Filled by the producer: one line per narration ⚠ or layout finding left as is, and why it is fine. -->
