#!/usr/bin/env bash
# Link (default) or copy the BOM skill into a skills directory.
#
#   bash install_claude_link.sh
#   bash install_claude_link.sh --target ~/.config/opencode/skills/bom
#   bash install_claude_link.sh --copy --force
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="${HOME}/.claude/skills/bom"
MODE="link"
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --copy)   MODE="copy"; shift ;;
    --force)  FORCE=1; shift ;;
    -h|--help)
      sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "option inconnue: $1" >&2; exit 2 ;;
  esac
done

if [ ! -f "$SOURCE/SKILL.md" ]; then
  echo "SKILL.md introuvable dans $SOURCE" >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET")"

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  if [ "$FORCE" -ne 1 ]; then
    echo "$TARGET existe deja. Relancer avec --force pour le remplacer." >&2
    exit 1
  fi
  if [ -L "$TARGET" ]; then
    rm "$TARGET"          # link only, source untouched
  else
    rm -rf "$TARGET"
  fi
  echo "existant remplace"
fi

if [ "$MODE" = "copy" ]; then
  cp -R "$SOURCE" "$TARGET"
  echo "copie    : $SOURCE -> $TARGET"
else
  ln -s "$SOURCE" "$TARGET"
  echo "symlink  : $SOURCE -> $TARGET"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 "$TARGET/scripts/bom.py" --version
elif command -v python >/dev/null 2>&1; then
  python "$TARGET/scripts/bom.py" --version
else
  echo "python introuvable : verifier l'installation manuellement" >&2
fi

echo "PASS. Relancer une session pour que le skill soit charge."
