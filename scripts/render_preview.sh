#!/usr/bin/env bash
# Render a .docx (or a .pptx) to PDF and page JPEGs so the pages can be looked at (Read tool) before sending.
#
# Usage: bash scripts/render_preview.sh out.docx [outdir] [dpi]
# Prints: page count, the JPEG paths, and a font-substitution warning when LibreOffice
# replaced a font the document asks for (the preview then differs from Word).
#
# Font aliases: LibreOffice on macOS does not map Microsoft names such as "Gill Sans MT" to the
# Apple "Gill Sans" family; without an alias it falls back to a serif and the preview lies.
# Aliases live in fonts/aliases.conf next to this script; add a <match> block per font.
set -euo pipefail
DOC="${1:?usage: render_preview.sh file.docx [outdir] [dpi]}"
OUT="${2:-$(dirname "$DOC")/preview}"
DPI="${3:-80}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"
STEM="$(basename "${DOC%.*}")"

# fontconfig: include the system config, add our aliases
CONF="$OUT/fonts.conf"
cat > "$CONF" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/opt/homebrew/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">/usr/local/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <include ignore_missing="yes">$HERE/fonts/aliases.conf</include>
  <cachedir>$OUT/.fc-cache</cachedir>
</fontconfig>
EOF
export FONTCONFIG_FILE="$CONF"

SOFFICE="$(command -v soffice || echo /Applications/LibreOffice.app/Contents/MacOS/soffice)"
"$SOFFICE" --headless --convert-to pdf --outdir "$OUT" "$DOC" >/dev/null 2>&1 || { echo "soffice failed"; exit 1; }
PDF="$OUT/$STEM.pdf"
rm -f "$OUT/$STEM"-page-*.jpg
pdftoppm -jpeg -r "$DPI" "$PDF" "$OUT/$STEM-page"
PAGES=$(pdfinfo "$PDF" | awk '/^Pages:/{print $2}')
echo "pages: $PAGES"
echo "pdf:   $PDF"
ls "$OUT/$STEM"-page-*.jpg

# Font check: what the document asks for vs what the PDF embeds. It reads Word XML, so it runs on .docx only.
case "$DOC" in *.docx|*.dotx) ;; *) echo "font check: skipped (not a .docx)"; exit 0 ;; esac
WANT=$(unzip -p "$DOC" word/styles.xml word/document.xml 2>/dev/null | grep -o 'w:ascii="[^"]*"' | sort | uniq -c | sort -rn | head -3 | sed 's/.*w:ascii="\([^"]*\)"/\1/' | paste -sd ',' -)
GOT=$(pdffonts "$PDF" 2>/dev/null | tail -n +3 | awk '{print $1}' | sed 's/^[A-Z]*+//' | sed 's/[-,].*//' | sort -u | paste -sd ',' -)
echo "fonts requested: $WANT"
echo "fonts in pdf:    $GOT"
for f in $(echo "$WANT" | tr ',' ' '); do
  key=$(echo "$f" | tr -d ' ' | sed 's/MT$//')
  echo "$GOT" | tr -d ' ' | grep -qi "$key" || echo "WARNING: '$f' not embedded; LibreOffice substituted a different font. Add an alias in fonts/aliases.conf or install the font before judging typography."
done
