#!/bin/bash
# One-time (idempotent) setup: venvs, models, checks. Re-run any time; it only fills what is missing.
#   scripts/setup.sh                 kit + the configured engine
#   scripts/setup.sh --all-engines   kit + every engine in tts/engines (for bake-offs)
set -euo pipefail
KIT=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
CACHE="$HOME/.cache/explainer-kit"
mkdir -p "$CACHE"/{venvs,models/piper,feedback,logs}

miss=0
for c in uv ffmpeg ffprobe pkg-config; do command -v $c >/dev/null || { echo "MISSING $c"; miss=1; }; done
pkg-config --exists cairo pangocairo || { echo "MISSING cairo/pango dev headers -> sudo apt install libcairo2-dev libpango1.0-dev"; miss=1; }
[ -f /usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf ] || { echo "MISSING Ubuntu fonts -> sudo apt install fonts-ubuntu"; miss=1; }
[ $miss = 0 ] || exit 1

echo "== kit venv (manim, faster-whisper)"
UV_PROJECT_ENVIRONMENT="$CACHE/venvs/kit" uv sync -q --project "$KIT" --python 3.12

ENGINE=$(sed -n 's/^engine: *//p' "$KIT/config.yaml")
if [ "${1:-}" = "--all-engines" ]; then ENGINES=$(ls "$KIT/tts/engines" | grep -v '^_'); else ENGINES=$ENGINE; fi
for e in $ENGINES; do
  [ -f "$KIT/tts/engines/$e/pyproject.toml" ] || continue
  echo "== engine venv: $e"
  UV_PROJECT_ENVIRONMENT="$CACHE/venvs/$e" uv sync -q --project "$KIT/tts/engines/$e" --python 3.12
done

if echo "$ENGINES" | grep -qw piper && [ ! -f "$CACHE/models/piper/en_US-lessac-high.onnx" ]; then
  echo "== piper voice"
  for f in en_US-lessac-high.onnx en_US-lessac-high.onnx.json; do
    curl -sSL -o "$CACHE/models/piper/$f" "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/$f"
  done
fi

echo "== whisper model (QA + alignment)"
"$CACHE/venvs/kit/bin/python" -c "from huggingface_hub import snapshot_download as s; s('Systran/faster-whisper-large-v3')" >/dev/null

echo "== engine warm-up ($ENGINE): downloads its weights on first run"
W="$CACHE/logs/warmup"; rm -rf "$W"; mkdir -p "$W"
printf '# S00\nSetup check: the narrator is ready.\n' > "$W/narration.txt"
( cd "$KIT" && HF_HUB_OFFLINE=0 PYTHONPATH="$KIT" "$CACHE/venvs/kit/bin/python" -m kit.narrate "$W/narration.txt" --out "$W" ) | tail -1

command -v latex >/dev/null && command -v dvisvgm >/dev/null || \
  echo "warn: no LaTeX; kit.tex() falls back to mono text. For real math: sudo apt install texlive-latex-extra texlive-fonts-extra dvisvgm"
touch "$CACHE/.setup-ok"
echo "setup ok"
