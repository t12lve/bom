#!/usr/bin/env python3
"""Install the BOM skill into one or more agent harnesses.

The skill format is the same everywhere (a folder with SKILL.md); only the
directory each harness scans differs. This script knows those directories:

    Claude Code   ~/.claude/skills/bom
    Codex         ~/.agents/skills/bom          (legacy: ~/.codex/skills/bom)
    Antigravity   ~/.gemini/config/skills/bom
    OpenCode      ~/.config/opencode/skills/bom

By default it links the folder (junction on Windows, symlink elsewhere) so the
repository stays the single source of truth. Use --copy if links are not
allowed. Nothing is downloaded, nothing is elevated.

    python scripts/install_skill.py --harness all
    python scripts/install_skill.py --harness codex --project
    python scripts/install_skill.py --copy --harness antigravity
    python scripts/install_skill.py --check
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "bom"
SOURCE = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".bom-cache", "runs", ".git")

HARNESSES = ("claude", "codex", "antigravity", "opencode")

USER_TARGETS = {
    "claude": Path(".claude") / "skills" / SKILL_NAME,
    "codex": Path(".agents") / "skills" / SKILL_NAME,
    "antigravity": Path(".gemini") / "config" / "skills" / SKILL_NAME,
    "opencode": Path(".config") / "opencode" / "skills" / SKILL_NAME,
}

PROJECT_TARGETS = {
    "claude": Path(".claude") / "skills" / SKILL_NAME,
    "codex": Path(".agents") / "skills" / SKILL_NAME,
    "antigravity": Path(".agents") / "skills" / SKILL_NAME,
    "opencode": Path(".opencode") / "skills" / SKILL_NAME,
}

BOTH_AGENTS = " '.agents/skills' is shared by Codex and Antigravity."


def home_dir(override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("HOME") or Path.home()).resolve()


def is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def remove_link(path: Path) -> None:
    if os.name == "nt" and not path.is_symlink():
        os.rmdir(path)  # junction: removes the link, never the target
    else:
        path.unlink()


def link_dir(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    else:
        target.symlink_to(source, target_is_directory=True)


def copy_dir(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=IGNORE)


def install_one(target: Path, mode: str, force: bool, dry_run: bool) -> str:
    target = target.resolve()
    source = SOURCE.resolve()

    if target == source:
        return f"deja en place ({target})"

    if target.exists() or is_link(target):
        if is_link(target):
            if not force:
                return f"lien existant, conserve ({target})"
            if not dry_run:
                remove_link(target)
        elif force:
            if not dry_run:
                shutil.rmtree(target)
        else:
            return f"existe et n'est pas un lien, --force requis ({target})"

    if dry_run:
        return f"[dry-run] {mode} -> {target}"

    if mode == "link":
        try:
            link_dir(source, target)
        except (OSError, RuntimeError):
            copy_dir(source, target)
            return f"copie (lien refuse) -> {target}"
        return f"lien -> {target}"

    copy_dir(source, target)
    return f"copie -> {target}"


def verify(target: Path) -> tuple[bool, str]:
    entry = target / "scripts" / "bom.py"
    if not entry.exists():
        return False, "bom.py absent"
    try:
        result = subprocess.run(
            [sys.executable, str(entry), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, result.stderr.strip()[:120]
    return True, result.stdout.strip()


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def check_spec() -> list[str]:
    problems: list[str] = []
    skill_md = SOURCE / "SKILL.md"
    if not skill_md.exists():
        return [f"SKILL.md introuvable dans {SOURCE}"]
    fields = frontmatter(skill_md)
    name = fields.get("name", "")
    description = fields.get("description", "")
    if name != SKILL_NAME:
        problems.append(f"name attendu '{SKILL_NAME}', trouve '{name}'")
    if not description:
        problems.append("description absente")
    elif len(description) > 500:
        problems.append(f"description trop longue: {len(description)} caracteres (max 500 pour Codex)")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_skill",
        description="Installe le skill BOM dans Claude Code, Codex, Antigravity et OpenCode.",
    )
    parser.add_argument(
        "--harness",
        default="all",
        choices=("all",) + HARNESSES,
        help="harnais cible (defaut: all)",
    )
    parser.add_argument(
        "--project",
        action="store_true",
        help="installe dans le projet courant (.agents/skills ou .opencode/skills)",
    )
    parser.add_argument("--home", default=None, help="racine utilisateur (tests, sandbox)")
    parser.add_argument("--copy", action="store_true", help="copie au lieu d'un lien")
    parser.add_argument("--force", action="store_true", help="remplace une installation existante")
    parser.add_argument("--dry-run", action="store_true", help="affiche sans ecrire")
    parser.add_argument("--check", action="store_true", help="verifie les installations presentes")
    args = parser.parse_args(argv)

    problems = check_spec()
    if problems:
        for problem in problems:
            print(f"[bom] SPEC: {problem}", file=sys.stderr)
        return 1

    harnesses = HARNESSES if args.harness == "all" else (args.harness,)
    base = Path.cwd() if args.project else home_dir(args.home)
    targets = PROJECT_TARGETS if args.project else USER_TARGETS
    mode = "copy" if args.copy else "link"

    if args.check:
        missing = 0
        for harness in harnesses:
            target = (base / targets[harness]).resolve()
            if not target.exists():
                print(f"  manquant  {harness:<12} {target}")
                missing += 1
                continue
            ok, detail = verify(target)
            print(f"  {'ok' if ok else 'casse':<8}  {harness:<12} {target}  {detail}")
            missing += 0 if ok else 1
        return 1 if missing else 0

    print(f"[bom] source: {SOURCE.resolve()}")
    for harness in harnesses:
        target = base / targets[harness]
        result = install_one(target, mode, args.force, args.dry_run)
        print(f"  {harness:<12} {result}")
        if not args.dry_run and target.exists():
            ok, detail = verify(target)
            print(f"  {'':<12} verification: {'ok' if ok else 'ECHEC'} {detail}")

    if args.project and any(h in {"codex", "antigravity"} for h in harnesses):
        print(f"[bom] note:{BOTH_AGENTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
