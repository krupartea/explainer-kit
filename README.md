# explainer-kit

A Claude Code skill (`/vid`) plus its toolkit for 3Blue1Brown-style explainer videos: Manim house style,
engine-neutral narration markup, local TTS, Whisper QA. Everything runs locally.

- `SKILL.md`: the skill (symlinked as `~/.claude/skills/vid`).
- `references/`: storytelling arc, visual-device catalog, narration markup.
- `kit/`: Python package (style, components, NarratedScene, narrate, render, assemble, CLI).
- `tts/engines/<engine>/`: one isolated venv per TTS engine (`synth.py` + `pyproject.toml`).
- `config.yaml`: default engine + voices. `lexicon.yaml`: pronunciation respellings.

Setup: `scripts/setup.sh` (idempotent). CLI: `scripts/vid --help`.
Cache (venvs, models, logs, feedback): `~/.cache/explainer-kit/`. Videos: `~/explainers/`.
