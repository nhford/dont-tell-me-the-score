#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/config/local.env" ]]; then
  set -a
  source "$ROOT/config/local.env"
  set +a
fi

exec /usr/bin/python3 "$ROOT/src/checker.py" "$@"
