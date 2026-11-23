# explainer-kit

A Claude Code skill (`/vid`) plus its toolkit for 3Blue1Brown-style explainer videos: Manim house style,
engine-neutral narration markup, local TTS, Whisper QA. Everything runs locally.

- `SKILL.md`: the skill (symlinked as `~/.claude/skills/vid`): writes a brief in the requesting chat, then
  hands production to a fresh background agent.
- `references/`: guidance is `principles.md` (seven principles and how to judge a video as a whole) and
  `toolbox.md` (optional techniques), together under ~300 lines: feedback revises them, never adds rules.
  Technical facts: `production.md` (the producer's steps), `narration-markup.md`, `manim.md`.
- `kit/`: Python package (style, components, NarratedScene + layout check, narrate, render, assemble, CLI);
  a video is one continuous scene in `video.py` that uses it as `import kit`.
- `benchmarks/`: fixed briefs for comparing kit versions (NMS: training topic; SIFT descriptor: validation).
- `tts/engines/<engine>/`: one isolated venv per TTS engine (`synth.py` + `pyproject.toml`).
- `config.yaml`: default engine + voices. `lexicon.yaml`: pronunciation respellings.

Setup: `scripts/setup.sh` (idempotent). CLI: `scripts/vid --help`.
Cache (venvs, models, logs, feedback): `~/.cache/explainer-kit/`. Videos: `~/explainers/`.
