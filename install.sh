#!/usr/bin/env bash
# Install the pack: node deps, python deps check, tool check, skill symlink.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
(cd "$HERE/scripts" && npm install --silent) && echo "node: docx $(node -e "console.log(require('$HERE/scripts/node_modules/docx/package.json').version)" 2>/dev/null || echo installed)"
python3 - <<'PY' || echo "python: run  pip3 install python-docx matplotlib Pillow"
import docx, matplotlib, PIL; print("python: python-docx, matplotlib, Pillow ok")
PY
for t in soffice pdftoppm pdffonts pdfinfo pandoc; do command -v "$t" >/dev/null 2>&1 && echo "tool: $t ok" || echo "tool: $t MISSING (brew install libreoffice poppler pandoc)"; done
[ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ] && echo "tool: LibreOffice.app ok" || true
SK="$HOME/.claude/skills/house-docx"
mkdir -p "$HOME/.claude/skills"
if [ -e "$SK" ] && [ ! -L "$SK" ]; then echo "skill: $SK exists and is not a symlink; leaving it"; else ln -sfn "$HERE" "$SK" && echo "skill: $SK -> $HERE"; fi
echo "done. Try: node scripts/build_docx.js --spec house/silvertree.style-spec.json --content examples/acme-content.json --out /tmp/acme.docx"
