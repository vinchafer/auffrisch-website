#!/usr/bin/env bash
# translate.sh — Workflow reminder for updating language versions of index.html
#
# USAGE: ./translate.sh
#
# This script reminds you of the manual steps needed to keep FR/IT/EN in sync
# with the German index.html after changes. Full automated translation would
# require an AI API key (e.g. DeepL or OpenAI).
#
# For automated translation, set DEEPL_API_KEY and uncomment the curl sections.

set -e

LANGS=("fr" "it" "en")
SOURCE="index.html"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          auffrisch.ch — Translation Sync Helper          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check source file exists
if [ ! -f "$SOURCE" ]; then
  echo "❌  Error: $SOURCE not found. Run this script from the /code directory."
  exit 1
fi

# Check language directories
for lang in "${LANGS[@]}"; do
  if [ ! -f "$lang/index.html" ]; then
    echo "⚠️   Missing: $lang/index.html"
  else
    echo "✓  Found: $lang/index.html"
  fi
done

echo ""
echo "──────────────────────────────────────────────────────────"
echo "  SYNC CHECKLIST after editing index.html:"
echo "──────────────────────────────────────────────────────────"
echo ""
echo "  1. Meta tags (title, description, keywords)"
echo "     → Update manually in fr/, it/, en/ with correct translation"
echo ""
echo "  2. Hero section (h1, hero-sub, hero-badge, hero-checks)"
echo "     → Translate and update in each language file"
echo ""
echo "  3. Section headings (h2, h3, section-label)"
echo "     → Update across all 3 files"
echo ""
echo "  4. Body text (p, li, FAQ answers, CTA text)"
echo "     → Update across all 3 files"
echo ""
echo "  5. Hreflang tags"
echo "     → Must be identical on ALL pages (de + fr + it + en)"
echo "     → Check: grep -n 'hreflang' index.html fr/index.html it/index.html en/index.html"
echo ""
echo "  6. Language switcher active state"
echo "     → DE:  lang-active on href='/'"
echo "     → FR:  lang-active on href='/fr/'"
echo "     → IT:  lang-active on href='/it/'"
echo "     → EN:  lang-active on href='/en/'"
echo ""
echo "  7. Anchor links (href='#prozess' etc.)"
echo "     → These work as-is — IDs are language-neutral"
echo ""
echo "  8. Paths: technologie.html → /technologie.html in subdirs"
echo ""
echo "──────────────────────────────────────────────────────────"
echo ""

# Show diff summary between source and each language
echo "  Last modified timestamps:"
for lang in "${LANGS[@]}"; do
  if [ -f "$lang/index.html" ]; then
    src_time=$(date -r "$SOURCE" "+%Y-%m-%d %H:%M" 2>/dev/null || stat -c "%y" "$SOURCE" 2>/dev/null | cut -c1-16)
    lang_time=$(date -r "$lang/index.html" "+%Y-%m-%d %H:%M" 2>/dev/null || stat -c "%y" "$lang/index.html" 2>/dev/null | cut -c1-16)
    echo "  index.html : $src_time"
    echo "  $lang/index.html: $lang_time"
    echo ""
  fi
done

echo "  TIP: After updating all language files, run:"
echo "  git add fr/index.html it/index.html en/index.html index.html"
echo "  git commit -m 'Update translations to match DE changes'"
echo ""
echo "  Then deploy: vercel --prod"
echo ""
