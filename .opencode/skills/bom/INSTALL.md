# Install BOM in Claude Code, Codex, Antigravity or OpenCode

BOM is a standard agent skill: a folder containing a `SKILL.md` with YAML
frontmatter, plus scripts and references. Every harness below reads that same
format; only the directory it scans changes.

## One command

From a fresh clone, at the repository root:

```bash
python install.py --harness all
```

or, from inside the skill folder:

```bash
python scripts/install_skill.py --harness all
```

It links the skill (junction on Windows, symlink elsewhere) into every
user-scope directory that exists for the four harnesses, then runs
`bom.py --version` through each install to prove it works.

| Option | Effect |
|---|---|
| `--harness claude\|codex\|antigravity\|opencode\|all` | choose the target (default `all`) |
| `--project` | install into the current repository instead of the user scope |
| `--copy` | copy the folder instead of linking it |
| `--force` | replace an existing install |
| `--home <dir>` | sandbox root (tests) |
| `--check` | verify what is installed, no writes |
| `--dry-run` | show the plan |

## Where each harness reads

| Harness | User scope | Workspace scope | Invoke |
|---|---|---|---|
| Claude Code | `~/.claude/skills/bom` | `.claude/skills/bom` | automatic, or `/bom` |
| Codex | `~/.agents/skills/bom` (legacy `~/.codex/skills/bom`, also read) | `.agents/skills/bom` | `$bom` or `/skills` |
| Antigravity | `~/.gemini/config/skills/bom` (App and CLI) | `.agents/skills/bom` | `/bom` |
| OpenCode | `~/.config/opencode/skills/bom` | `.opencode/skills/bom` | automatic |

Notes from the harness documentation:

- **Codex** scans `.agents/skills` in the working directory and every parent up
  to the repository root, plus `$HOME/.agents/skills`. It still reads the older
  `$CODEX_HOME/skills` (`~/.codex/skills`). A folder symlink is followed.
  Older builds keep skills behind a flag: `[features] skills = true` in
  `~/.codex/config.toml`, or `codex --enable skills`.
- **Antigravity** defaults to `.agents/skills` and still reads `.agent/skills`.
  The App reads `~/.gemini/config/skills`; the CLI also reads
  `~/.gemini/antigravity-cli/skills` and `~/.gemini/skills`. Every skill also
  becomes a `/bom` command.
- **Claude Code** reads `~/.claude/skills` and `.claude/skills`. A skill is
  selected by its description, and can be called by name.
- **OpenCode** reads the project `.opencode/skills` and the global
  `~/.config/opencode/skills`.

## Verify

```bash
python .opencode/skills/bom/scripts/bom.py --version
python .opencode/skills/bom/scripts/bom.py selftest
python scripts/install_skill.py --check
```

`selftest` runs the whole pipeline offline and asserts the invariants (clusters,
generation, audit, score, exports, LEGO reference case, sub-agent packets). It
must print `PASS`.

Then start a new session in the harness and ask for a name: the skill should be
selected from its description. If it is not:

| Symptom | Fix |
|---|---|
| Codex does not list it | check `~/.agents/skills/bom/SKILL.md` exists; enable `[features] skills = true` on older builds; restart |
| Antigravity does not list it | the folder must sit directly in `skills/`, not one level deeper; restart the workspace |
| Claude does not list it | `SKILL.md` must be at the folder root, not nested |
| Duplicate entry in Codex | a copy exists in both `~/.agents/skills` and `~/.codex/skills`; remove one |

## Link or copy

The default link keeps the repository as the single source of truth: editing
`SKILL.md` updates every harness. `--copy` is for environments where links are
blocked or where the repository will be deleted. Re-run with `--force` after an
update if you copied.

On Windows, the installer uses a directory junction (`mklink /J`): no
administrator rights, and removing it never deletes the source.

## Uninstall

```powershell
Remove-Item "$HOME\.agents\skills\bom"        # Codex / Antigravity workspace
Remove-Item "$HOME\.claude\skills\bom"        # Claude
Remove-Item "$HOME\.gemini\config\skills\bom" # Antigravity
Remove-Item "$HOME\.config\opencode\skills\bom" # OpenCode
```

```bash
rm ~/.agents/skills/bom ~/.claude/skills/bom \
   ~/.gemini/config/skills/bom ~/.config/opencode/skills/bom
```

Removing a junction or a symlink does not delete the repository.

## Legacy scripts

`scripts/install_claude_link.ps1` and `install_claude_link.sh` remain for a
Claude-only install from an older checkout. They are equivalent to
`install_skill.py --harness claude`; prefer the Python installer, which covers
all four harnesses.

## Requirements

- Python 3.9+ (3.12 tested), standard library only.
- No API key. Network is optional; without it, use `--offline`.
- Windows, macOS and Linux. The installer resolves paths relative to the script,
  so the repository can live anywhere.
