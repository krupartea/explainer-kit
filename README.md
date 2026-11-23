# explainer-kit

A Claude Code skill (`/vid`) plus its toolkit for 3Blue1Brown-style explainer videos: Manim house style,
engine-neutral narration markup, local TTS, Whisper QA. Everything runs locally.

- `SKILL.md`: the skill (symlinked as `~/.claude/skills/vid`): writes a brief in the requesting chat, then
  hands production to a fresh background agent.
- `references/`: production guide (the producer agent's steps), storytelling arc, delivery rules,
  visual-device catalog, narration markup.
- `kit/`: Python package (style, components, NarratedScene + layout check, narrate, render, assemble, CLI);
  scenes use it as `import kit`.
- `tts/engines/<engine>/`: one isolated venv per TTS engine (`synth.py` + `pyproject.toml`).
- `config.yaml`: default engine + voices. `lexicon.yaml`: pronunciation respellings.

Setup: `scripts/setup.sh` (idempotent). CLI: `scripts/vid --help`.
Cache (venvs, models, logs, feedback): `~/.cache/explainer-kit/`. Videos: `~/explainers/`.
