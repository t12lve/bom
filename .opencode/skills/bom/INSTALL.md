# Install BOM as a Claude/OpenCode skill

BOM is a folder. Installation is linking or copying that folder into the skills
directory your agent reads, then checking that the entry point runs.

## Where the skill lives now

```
<repo>/.opencode/skills/bom/
  README.md            entry point + 60-second tour
  SKILL.md             the agent's operating manual
  references/          seven domain documents
  docs/                architecture, CLI, data model, cookbook, extending
  scripts/bom.py       CLI entry point
  scripts/bomlib/      engine (stdlib only)
  scripts/selftest.py  54 assertions, offline
  agents/              sub-agent prompts (creation + research)
  assets/              example corpus, brief, report
```

## Target directories

| Harness | Directory |
|---|---|
| Claude Code | `~/.claude/skills/bom` |
| OpenCode (project) | `<repo>/.opencode/skills/bom` |
| OpenCode (global) | `~/.config/opencode/skills/bom` |

The folder is already in an OpenCode project path. For Claude, add a link.

## Windows — junction (no admin rights needed)

```powershell
pwsh -File .opencode\skills\bom\scripts\install_claude_link.ps1
```

Default: source = this skill folder, target = `$HOME\.claude\skills\bom`.
Add `-Force` to replace an existing link, `-Copy` to copy instead of linking.

A junction (`New-Item -ItemType Junction`) works without elevated rights and is
followed by every tool that reads the folder. A symbolic link needs Developer
Mode or admin, which is why the script defaults to a junction.

## macOS / Linux — symlink

```bash
bash .opencode/skills/bom/scripts/install_claude_link.sh
```

Default: source = this skill folder, target = `~/.claude/skills/bom`.
Add `--copy` to copy, `--force` to replace.

## Verify

```bash
python .opencode/skills/bom/scripts/bom.py --version
python .opencode/skills/bom/scripts/bom.py selftest
```

`selftest` runs the whole pipeline offline on the bundled example and checks the
invariants (5 clusters, 30 candidates, 4 pillars summing to 100, report
generated). It must print `PASS`.

Then, in a new agent session, ask something like *"trouve-moi un nom pour une app
de gestion de food cost"* — the `bom` skill should be selected. If it is not,
check that `SKILL.md` sits at the root of the linked folder (not nested one level
deeper).

## Updating

Because the install is a link, editing the repo is enough. If you installed with
`--copy`, re-run the script with `--force`.

## Uninstalling

```powershell
Remove-Item "$HOME\.claude\skills\bom"          # junction: removes the link only
```

```bash
rm ~/.claude/skills/bom                          # symlink: removes the link only
```

Deleting a junction or symlink does not delete the source folder.

## Requirements

- Python 3.9+ (3.12 tested), standard library only.
- No API keys. Network is optional; without it, use `--offline`.
- Windows, macOS and Linux are supported; paths in the scripts are resolved
  relative to the script location, so the repo can live anywhere.
