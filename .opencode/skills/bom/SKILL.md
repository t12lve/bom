---
name: bom
description: "Use when the user wants to find, generate, audit, score, shortlist or validate an application, product or brand name from a list of keywords (100-500+) or a product brief. Runs a full naming pipeline: semantic clustering, 30 candidates across 5 archetypes, a LEGO-style engine that contracts a translated phrase into a 2-3 syllable name (leg godt -> LEGO), automated domain/registry/store audit, trademark pre-screening, and a 100-point BOM score split between classic SEO and GEO (ChatGPT, Perplexity, Gemini, Claude) plus commercial branding, exported as Markdown, Excel and JSON. Uses consent-gated sub-agents: strong reasoning models for name creation, cheap fast models for SERP/store/trademark research. Also use for bulk domain availability checks (.com/.app/.ai/.io/.fr), GitHub/npm/PyPI collision checks, or comparing two name shortlists. French and English markets."
license: MIT
---

# BOM — Brand, Optimization & Market-readiness

BOM turns a keyword corpus into a defensible naming decision. It is not a name
generator that stops at a list: every candidate is audited against the open web,
scored on four 25-point pillars, and delivered as an executive report that says
what to buy, what to file, and what is still unverified.

`BOM` = **B**rand, **O**ptimization & **M**arket-readiness (the acronym also
carries *Burger au Miel*, the internal nickname — never ship that name).

## When to use

- The user has a keyword list (or exports one) and wants names for an app,
  SaaS, product, plugin, shop or service.
- The user asks whether a name is "available", "taken", "good for SEO",
  "good for AI search", or "worth trademarking".
- The user wants a shortlist compared, or an existing name audited.
- The user says *naming*, *domain availability*, *brand audit*, *trouver un nom*,
  *nom d'application*, *disponibilité de domaine*, *scoring de marque*.
- The user wants a short name built from a phrase, like **LEGO** from *leg godt*
  ("play well") — the LEGO engine contracts a translated expression into 2-3
  syllables. Keywords can be in any language, translated into the most-used
  ones, and checked like any other candidate.

## When not to use

- Logo, visual identity, palette, typography → design skills.
- Copywriting, tagline, positioning strategy → strategy/copy work.
- Legal advice. BOM pre-screens; a trademark attorney clears.

## Non-negotiables

1. **Never present an unmeasured signal as measured.** RDAP is a strong signal,
   not a contract; a `?` status is not a green light; SERP, stores and trademarks
   are Phase 3 work that the agent must actually perform.
2. **Never invent availability.** If the network is blocked, run `--offline` and
   label every result `provisoire`.
3. **Never buy anything.** No domain purchase, no trademark filing, no paid API.
   Produce the action list; the human executes.
4. **Always state the confidence level** and the remaining manual checks at the
   end of the deliverable.
5. **Answer in the user's language.** The engine's internals are FR/EN; the
   report voice follows the user.

## Prerequisites

- Python 3.9+ (stdlib only — no `pip install`).
- Network access for Phase 2. Without it, use `--offline` and say so.
- Optional: `websearch` for Phase 3 (SERP, stores, trademark).

Resolve the skill directory once per session:

```bash
# Linux / macOS
BOM=~/.claude/skills/bom
# Windows
BOM="$HOME/.claude/skills/bom"
```

All commands below are relative to `$BOM`. `scripts/bom.py` is the only entry
point; `--help` on any subcommand is authoritative.

## Pipeline

```
intake → generate → audit → score → report
   P1        P1b       P2      P4       P5
                          ↑
                    Phase 3 (sub-agents, see below)
```

## Two generation engines

| Engine | Command | What it produces | Use when |
|---|---|---|---|
| `archetypes` (default) | `run --engine archetypes` | 30 names across 5 families (descriptif, blend, métaphore, néologisme, hybride GEO) | broad exploration, no strong phrase |
| `lego` | `run --engine lego` | contractions of a **translated phrase** into 2-3 syllables, LEGO-style | the product has a nameable promise, or the client asks for "un nom court qui veuille dire quelque chose" |

### How the LEGO engine works

`leg godt` (Danish, "play well") → `LE + GO` → **LEGO**. BOM reproduces the
mechanism:

1. Take the corpus concepts (price, cost, menu, team…) and translate them into
   10+ languages, online (MyMemory, no key) or from the offline seed lexicon.
2. Pair each concept with a qualifier (*fast, simple, clear, true, new, smart,
   easy, better, well*) in the same language → a short, meaningful phrase.
3. Contract the phrase with six rules: `lego2` (2 letters per word), `head2`
   (first syllable per word), `head_tail`, `cvc2`, `blend`, `initials`.
4. Repair the result for FR/EN phonotactics, then hard-filter it.
5. Score **fidelity /100**: syllables, how much of the phrase survives,
   cross-language coverage, pronounceability, lucky coincidence.

Each name keeps its provenance (`source_phrase`, `source_language`, `rule`,
`fidelity`, all translations), so the client can judge *why* it exists.

The reference case is also the regression test: `leg godt` must contract to
`lego`, and `lego` must then be rejected as a known brand. `bom.py selftest`
asserts exactly that.

```bash
python scripts/bom.py run --engine lego \
  --keywords assets/keywords.example.csv --brief assets/brief.example.md \
  --langs fr,en,es,de,it,pt,nl,da,sv,pl \
  --out-dir runs/acme-lego --count 24 --top 10
```

`--translator offline` keeps everything local (lexicon only, fewer languages).
Non-romanisable languages (Arabic, Hindi, Chinese, Japanese, Korean) are listed
but skipped: BOM refuses to invent a transliteration.

Full method and limits: `references/lego-mechanic.md`.

## Orchestration by sub-agents (only with explicit consent)

BOM separates **judgement** from **reading**, because they do not deserve the
same model:

| Work | Tier | Why | Parallelism |
|---|---|---|---|
| Creation (Phase 1: names, arbitrations, LEGO refinement) | strongest reasoning model available | taste, trade-offs, rejecting plausible-but-bad names | 1 per cluster, max 5 |
| Research (Phase 3: SERP, stores, trademarks, GEO battery) | fastest cheapest model | counting results, copying mark numbers, quoting sources | 1 per batch of 2-3 names, in parallel |
| Scoring & report (Phase 4-5) | the orchestrator itself | deterministic scripts, no judgement needed | n/a |

**Consent gate — non-negotiable.** Sub-agents are never spawned silently.
Before dispatching, ask the user and wait for an explicit yes:

> "Cette étape peut tourner en solo (plus lent, un seul modèle) ou en
> sous-agents : N agents de création sur le modèle le plus fort, M agents de
> recherche sur le modèle le plus rapide. Ça consomme plus de tokens et lance
> des agents en parallèle. Je pars en sous-agents ?"

If the user declines, or the harness has no sub-agent tool, run the same phases
sequentially with the current model — the scripts and packet schemas are
identical.

```bash
# 1. build the task packets (no model is called)
python scripts/bom.py dispatch --phase 1 --clusters runs/acme/work/clusters.json --out runs/acme/packets
python scripts/bom.py dispatch --phase 3 --scores runs/acme/work/scores.json --top 10 --batch 3 --out runs/acme/packets

# 2. the orchestrator spawns one sub-agent per packet, with the tier named in
#    the packet; each returns JSON matching packet["output_schema"]

# 3. merge the returned files, then rescore with measured evidence
python scripts/bom.py merge --inputs runs/acme/packets/results/*.json --out runs/acme/work/research.json
python scripts/bom.py score --audit runs/acme/work/audit.json --research runs/acme/work/research.json --out runs/acme/work/scores.json
```

When spawning, resolve the tier to a real model in the harness (list models,
pick the strongest reasoning model for `creation`, the cheapest fast one for
`research`) and tell the user which models you picked. Do not hardcode a model
name in this skill: availability changes.

Rules for the sub-agents (also in `agents/*.md`):

- one packet = one job, JSON in / JSON out, no prose;
- never invent a source, a ranking or a trademark number: `not_checked` exists;
- a research agent may not score, a creation agent may not check availability;
- if a packet cannot be completed, return the schema with `not_checked` and one
  factual reason — silence is a failure, a declared gap is a result.

`dispatch`, `merge` and the packet schemas live in `scripts/bomlib/research.py`.
The prompts are in `agents/`.


### Phase 0 — Intake

Ask for, or reconstruct, three things:

| Input | Required | Notes |
|---|---|---|
| Keyword corpus | yes | 100-500+ lines; `keyword` or `keyword,volume` |
| Product brief | strongly recommended | what it does, for whom, tone, market |
| Constraints | optional | TLDs, forbidden words, FR-only, budget |

If the user gives fewer than 100 keywords, say so and offer to expand from the
brief before running — clustering below ~100 items is noise. If the user has no
list, generate one from the brief yourself (their own words, competitor SERPs,
store search suggestions) and keep it in `work/keywords.csv` as evidence.

```bash
python scripts/bom.py intake \
  --keywords assets/keywords.example.csv \
  --brief assets/brief.example.md \
  --out runs/acme/work/clusters.json \
  --csv runs/acme/work/keywords.csv
```

Output: `clusters.json` with five clusters (Benefice / Action / Tech-Mecanique /
Cible / Metaphore), ranked roots with frequency and volume, intent distribution,
and the number of keywords assigned by lexical fallback.

**Check before moving on:** all five clusters populated? If a cluster is at zero,
the corpus is biased — add keywords from that family (see
`references/keyword-intake.md`) instead of accepting a 4-cluster map. Report the
fallback share; above ~40% the clustering is weak and must be said out loud.

### Phase 1 — 30 candidates across 5 archetypes (or LEGO contractions)

```bash
python scripts/bom.py generate \
  --clusters runs/acme/work/clusters.json \
  --count 30 --seed 7 \
  --out runs/acme/work/candidates.json
```

Switch to the LEGO engine with `run --engine lego` (see above) or by calling
`bomlib.lego.generate_lego` from the pipeline; the rest of the chain (audit,
score, report) is identical and the report gains a Fidélité column.

Six per archetype, each with a rationale, its roots, its clusters, a
pronounceability score and a phone-test penalty:

| Archetype | What it is | Why it exists |
|---|---|---|
| Descriptif hybride | root + product morpheme (`prixrank`, `margedeck`) | zero learning cost |
| Mot-valise / Blend | two roots welded (`cuisicost`, `brassemap`) | two category signals at once |
| Metaphorique | image + decodability morpheme (`beaconpath`, `forgeworks`) | memorable + still guessable |
| Neologisme <= 7 | invented, legal FR/EN phonotactics (`foorix`, `regouzi`) | ownable, free SERP |
| Hybride GEO | sector morpheme + mechanics morpheme (`menuscope`, `platsignal`) | an LLM infers the category |

The generator is *seed material*, not the deliverable. Read the 30 names and
**refine**: tighten vowels, remove suffixes that are already everywhere
(`-ly`, `-ify`, `-ai`), fix FR/EN homographs. If a name reads badly in French,
replace it — you are the editor, the seed is the raw material. Keep the
generator's rationale for anything you keep; invent one for anything you add.

### Phase 2 — Automated technical audit

```bash
# Full audit (network, ~30 candidates x 5 TLDs)
python scripts/bom.py audit \
  --candidates runs/acme/work/candidates.json \
  --tlds com,app,ai,io,fr \
  --out runs/acme/work/audit.json \
  --cache-dir runs/acme/.cache --workers 6

# Fast pass: domains only, no code registries
python scripts/bom.py audit ... --quick

# No network at all
python scripts/bom.py audit ... --offline
```

Hard filters run before any request and eliminate a name outright:
profanity, unambiguous hate/adult terms, bare dictionary noun, known brand
collision, non-ASCII, 4+ consonant pile-up, unpronounceable.

What is checked, per candidate:

| Check | Source | Status values |
|---|---|---|
| `name.tld` for each TLD | RDAP (rdap.org / rdap.nic.fr) + DNS | available / registered / unknown |
| GitHub account and repos | api.github.com | libre / pris / ambigu / inconnu |
| npm, PyPI, crates.io | registry APIs | libre / pris / inconnu |
| App Store | iTunes Search API (FR) | libre / ambigu / pris |
| Google Play, Product Hunt | no public API | manuel + link |

**Read the modes, not just the flags.** `unknown` means "could not verify" —
never round it up to available. `--offline` output is a structural pre-screen,
not an audit.

Select the **10 best survivors** for Phase 3: `.com` available first, then most
TLDs free, then fewest registry collisions, then shortest. The `survivors` array
already applies this order.

### Phase 3 — SERP, stores, trademark (agent work, no free API)

Phase 2 emits a ready-to-run query pack per candidate
(`audit.json → candidates[].serp`, `.trademarks`). This phase is where the report
earns its credibility — do it, do not fake it.

Preferred route: generate packets and hand them to cheap research sub-agents
(see the orchestration section), then merge their answers. Manual route: do the
same checks yourself, in the same order, and write them into a results file.

```bash
python scripts/bom.py dispatch --phase 3 --scores runs/acme/work/scores.json \
  --top 10 --batch 3 --out runs/acme/packets
# ... sub-agents return JSON ...
python scripts/bom.py merge --inputs runs/acme/packets/results/*.json \
  --out runs/acme/work/research.json
```

For each of the 10 finalists:

1. **SERP** — run the 5 queries with `websearch` (or the browser). Record:
   - number of organic results on page 1,
   - any dominant entity (film, celebrity, big brand) → disqualifying,
   - dictionary-only results → the exact query is not ownable,
   - whether `name.com` already ranks with unrelated content.
2. **Stores** — App Store (search link), Google Play (manual), Product Hunt
   (manual). An existing app with the same name in the same category is a hard
   stop; a different category is a warning.
3. **Trademarks** — INPI, EUIPO, USPTO, TMview, WIPO BrandDB, **classes 9**
   (software) and **42** (SaaS, technical services). Look for identical or
   near-identical signs in those classes, not the whole register. Record the
   mark number, owner, class, status. BOM only pre-screens: a human attorney
   clears. See `references/legal-and-registries.md`.
4. **GEO prompt battery** — run the 6 prompts of
   `references/geo-audit.md` on ChatGPT, Perplexity, Gemini and Claude. Record
   verbatim whether the model (a) infers the category, (b) confuses the name
   with an existing entity, (c) invents facts. Instability across engines is a
   finding, not a nuisance.

Update the candidate records with what you find (edit the JSON, or keep a
`notes` column in your working file) — Phase 4 must be able to point at evidence.

### Phase 4 — BOM score (100 points, 4 x 25)

```bash
python scripts/bom.py score \
  --audit runs/acme/work/audit.json \
  --clusters runs/acme/work/clusters.json \
  --out runs/acme/work/scores.json
```

| Pillar | 25 pts | What it actually measures |
|---|---|---|
| Disponibilite technique & handles | 25 | `.com` (7), secondary TLDs (4), code registries (6), typo resistance (4), trademark pre-screen (4) |
| Note SEO classique | 25 | SERP virginity (8), brand rankability (7), intent alignment with the corpus (5), long-tail (3), snippet/sitelinks (2) |
| Note GEO / moteurs IA | 25 | no collision with LLM-known entities (9), immediate semantic anchoring (7), hallucination/attribution risk (5), cross-engine stability (4) |
| Potentiel commercial & branding | 25 | phone test (3), FR (3), EN (3), length (4), memorability (4), extensibility (3), logo potential (2), brief fit (3) |

Tiers: **GREENLIGHT >= 88** (buy and file now), **FORT >= 78** (clear the last
reserves), **CONDITIONNEL >= 62**, **ECARTE < 62**, **REJETE** (hard filter).
`provisional: true` (offline audit) means the SEO and GEO pillars are
extrapolated — the report must say it.

Full anchors, worked example and calibration rules:
`references/scoring-rubric.md`.

### Phase 5 — Executive restitution

```bash
python scripts/bom.py report \
  --scores runs/acme/work/scores.json \
  --audit runs/acme/work/audit.json \
  --clusters runs/acme/work/clusters.json \
  --candidates runs/acme/work/candidates.json \
  --top 10 --out runs/acme/report
```

Produces:

```
runs/acme/report/
  BOM-report.md      # the deliverable (markdown)
  BOM-names.xlsx     # the deliverable (Excel: Classement, Provenances, Méthode)
  BOM-names.json     # machine-readable, schema bom.names/v1
  BOM-scores.csv     # spreadsheet fallback (semicolon separated)
  dossiers/*.md      # top 5, one page each
```

The Excel workbook is the format clients actually reuse: frozen header,
autofilter, numeric pillar cells, a provenance sheet for LEGO names, and a
method sheet with the rubric. Regenerate it without re-auditing:

```bash
python scripts/bom.py export --scores work/scores.json --audit work/audit.json --out report
```

The report contains: corpus and cluster map, candidate distribution, the
comparative table, the podium with per-pillar bars, the rejection list and
reasons, the Phase 3 packs (SERP queries, trademark links, GEO prompts), the
method with weights, and the limits. Do not rewrite it into prose — hand over
the file, then summarise in 5 lines: winner, runner-up, the one blocking
reserve, what to buy today, what remains unverified.

Template and acceptance criteria: `references/report-template.md`.

## One-shot

```bash
python scripts/bom.py run \
  --keywords assets/keywords.example.csv \
  --brief assets/brief.example.md \
  --out-dir runs/acme \
  --tlds com,app,ai,fr --count 30 --top 10
```

Runs Phases 1-2-4-5 and writes `runs/acme/state.json` with the file map and the
Phase 3 to-do list. Phase 3 remains yours.

## Ad-hoc check

For a shortlist the user already has:

```bash
python scripts/bom.py check --names "rankly,hivelens,menuscope" --offline
python scripts/bom.py check --names "rankly,hivelens" --tlds com,fr,ai
```

## Decision rules

- `.com` taken + no `.fr`/`.app` + strong registry collisions → drop, unless the
  name scores >= 88 on the other three pillars and the `.com` is parked.
- A known entity (film, brand, celebrity) on page 1 of the exact query → drop.
  GEO cannot fix an entity collision; it compounds it.
- Same name in the same App Store category → drop.
- Identical mark in class 9 or 42 → stop and send to an attorney before any
  spend.
- Two names within 3 points → the cheaper `.com` wins; then the shorter one;
  then the one whose FR pronunciation survives a phone call.
- No candidate above 62 → do not ship. Return to Phase 1 with a new seed and
  more metaphor/target keywords; say that the corpus or the positioning is the
  bottleneck, not the names.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `?` on every domain | RDAP throttled or offline | rerun later, add `--cache-dir`, or verify at a registrar |
| `403` on GitHub checks | unauthenticated rate limit | wait, or audit fewer names per run (`--workers 2`) |
| All five clusters exist but one is thin | corpus bias | add that family of keywords, rerun intake |
| 30 names, none usable | brief too narrow or seed unlucky | new `--seed`, add metaphor keywords, hand-write 10 names |
| Scores compressed 78-82 | offline audit | rerun online before ranking |
| Report says `provisoire` | `--offline` was used | expected; state it in your summary |

## References

- `references/scoring-rubric.md` — the 100-point grid, anchors, calibration.
- `references/geo-audit.md` — GEO logic, the 6-prompt battery, entity seeding.
- `references/archetypes.md` — how each archetype is built, FR/EN phonetics.
- `references/keyword-intake.md` — corpus formats, clustering, root extraction.
- `references/legal-and-registries.md` — classes 9/42, INPI/EUIPO/USPTO, costs.
- `references/report-template.md` — deliverable structure and acceptance.
- `references/lego-mechanic.md` — contraction rules, languages, fidelity, limits.
- `agents/` — sub-agent prompts (creation + research) with output schemas.
- `INSTALL.md` — symlink/copy into `~/.claude/skills/bom`.

Advanced documentation (read on demand, not at every run):

- `README.md` — entry point and 60-second tour.
- `docs/ARCHITECTURE.md` — modules, data flow, invariants, determinism.
- `docs/CLI-REFERENCE.md` — every command, option, default, exit code.
- `docs/DATA-MODEL.md` — JSON schemas, status vocabularies, invariants.
- `docs/COOKBOOK.md` — 12 copy-paste recipes.
- `docs/EXTENDING.md` — add a rule, a language, a check, a weight.
- `docs/CHANGELOG.md` — versions, known limits, roadmap.
