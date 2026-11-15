# AGENTS.md

This repository ships **BOM** (*Burger au Miel*): a naming skill that turns a
keyword corpus into audited, scored brand names. It also ships the landing page
served at https://t12lve.github.io/bom/.

## Where things are

| Path | What |
|---|---|
| `.opencode/skills/bom/` | the skill (canonical source) |
| `.opencode/skills/bom/SKILL.md` | entry point, five-phase workflow |
| `.opencode/skills/bom/scripts/bom.py` | CLI, stdlib only |
| `.opencode/skills/bom/scripts/selftest.py` | offline regression suite |
| `.opencode/skills/bom/docs/` | architecture, CLI, data model, cookbook |
| `site/` | static landing page, no build step |
| `.github/workflows/pages.yml` | deploys `site/` to GitHub Pages |

## Working on it

- Python 3.9+ only, **no third-party dependency**. Do not add one to the engine.
- Run `python .opencode/skills/bom/scripts/bom.py selftest` before claiming a
  change is done. It must print `PASS`.
- The page is plain HTML/CSS/JS. There is no bundler: edit `site/` and push.
- Install into every harness with `python install.py --harness all` from the
  repository root.

## Rules that matter

1. **Never fake a check.** `unknown`, `inconnu` and `not_checked` are valid
   answers; a guessed domain status is not.
2. **Determinism.** Generators are seeded; do not introduce global randomness.
3. **One filter.** `generate.accept_name` is the single gate for profanity,
   brands, dictionary words and pronounceability. Do not bypass it.
4. **Equal pillars.** The 100-point score is 4 x 25 (technique, SEO, GEO,
   commercial). Rebalancing is a documented client decision, not a code edit.
5. **Sub-agents need consent.** Packets are generated offline; ask the user
   before spawning any model.

## Where to read more

- `SKILL.md` for the workflow.
- `docs/ARCHITECTURE.md` for invariants and data flow.
- `docs/EXTENDING.md` before adding a rule, a language or a registry check.
- `docs/CHANGELOG.md` for known limits.
