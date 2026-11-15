#!/usr/bin/env python3
"""Install the BOM skill into Claude Code, Codex, Antigravity or OpenCode.

Thin entry point for a fresh clone:

    python install.py --harness all
    python install.py --harness codex --project
    python install.py --check

The implementation lives in the skill itself
(.opencode/skills/bom/scripts/install_skill.py), so an already-installed copy
can be updated without this file.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent
    / ".opencode"
    / "skills"
    / "bom"
    / "scripts"
    / "install_skill.py"
)

if not SCRIPT.exists():
    raise SystemExit(f"[bom] installateur introuvable: {SCRIPT}")

sys.argv[0] = str(SCRIPT)
runpy.run_path(str(SCRIPT), run_name="__main__")
