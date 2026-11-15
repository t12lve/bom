# GEO audit — will an AI engine recommend this name, and say something true?

Classic SEO asks: where do I rank? GEO asks: when a model answers *"give me a
tool that does X"*, does my name appear, attached to the right facts, in a stable
way across engines?

For a brand-new name the honest answer is **no, not yet**. GEO for a blank brand
is therefore not a visibility measure — it is a **risk and readiness measure**:

1. **Entity collision** — does the string already belong to someone the model
   knows? (film, person, big brand, open-source project)
2. **Semantic transparency** — can the model infer the category from the name?
3. **Hallucination exposure** — will the model invent facts to fill the gap?
4. **Cross-engine stability** — do ChatGPT, Perplexity, Gemini and Claude tell
   the same story?

Pillar 3 of the BOM score is built on these four. Phase 2 supplies the collision
facts; the prompt battery below supplies the observations.

---

## Part A — Collision facts (from Phase 2, already collected)

| Fact | Where it comes from | Why it matters for GEO |
|---|---|---|
| GitHub account | api.github.com/users | developer entities are well represented in training data |
| npm / PyPI / crates | registry APIs | package entities are quoted verbatim by coding models |
| App Store match | iTunes Search API | consumer products with reviews are strongly anchored |
| Dictionary word | internal lexicon | the common meaning drowns the brand meaning |
| Common first name | internal lexicon | person entities dominate the embedding |
| Known brand substring | internal blocklist | strongest prior of all |

A name with four or more of these is not "hard to rank" — it is **already
someone else**, and the model will confidently attribute their facts to you.

---

## Part B — The 6-prompt battery

Run each prompt verbatim on **ChatGPT, Perplexity, Gemini and Claude**, in a
fresh conversation, with the same user language as the target market. Record the
answer, not your impression.

| # | Prompt | What passes | What fails |
|---|---|---|---|
| 1 | `Sans contexte, que fait l'application {name} ?` | the model guesses the sector, even roughly | "I don't know", or a confident wrong sector |
| 2 | `Quelles sont les meilleures applications pour {need} ?` | `{name}` appears in a long list (5-10) once the brand is live | absent, or replaced by an established competitor |
| 3 | `{name}, est-ce la marque logiciel ou l'autre entité homonyme ?` | the model separates both entities | merges them, or refuses to answer |
| 4 | `Recommande un outil {category} pour {target}.` | the name can be cited without misattribution | cites a homonym, or attaches false facts |
| 5 | `Donne-moi le prix et le fondateur de {name}.` | "I don't have this information" / "check the official site" | invents a price, a founder, a funding round |
| 6 | `Explique la difference entre {name} et {competitor}.` | both entities stay distinct | fusion, confusion, or denial of existence |

`{need}`, `{category}`, `{target}`, `{competitor}` come from the brief and from
the corpus. Fill them with the buyer's own words, not marketing words.

### Recording grid

| Prompt | ChatGPT | Perplexity | Gemini | Claude | Verdict |
|---|---|---|---|---|---|
| 1 category | | | | | |
| 2 discovery | | | | | |
| 3 disambiguation | | | | | |
| 4 recommendation | | | | | |
| 5 hallucination trap | | | | | |
| 6 entity resolution | | | | | |

Use three labels only: **PASS** (as expected), **HEDGE** (refuses / "I'm not
sure"), **FAIL** (wrong entity or invented facts). Count FAILs across 24 cells:

| FAILs | Pillar 3 reading |
|---|---|
| 0-2 | name is GEO-ready |
| 3-6 | workable with a content/entity push |
| 7-12 | the name will be misattributed; change it or fight for months |
| 13+ | disqualifying, whatever the other pillars say |

---

## Part C — Pre-launch GEO remediation (when you keep the name)

Shipping a name and hoping is not a strategy. These are the levers, in order of
impact per hour spent:

1. **One canonical sentence.** Everywhere (site, stores, LinkedIn, GitHub,
   press kit): `{Name} is a {category} for {target} that {outcome}.` Same words
   every time. Models reward consistency, not creativity.
2. **schema.org `Organization` + `SoftwareApplication`** with `name`,
   `description`, `applicationCategory`, `operatingSystem`, `offers`. Machine
   readable beats prose.
3. **Wikidata item** once you have two independent sources (press, registry,
   funding). This is the single strongest disambiguation move; without it, a
   homonym keeps winning.
4. **Structured FAQ** on the site answering the six battery prompts literally.
   Perplexity and Gemini quote it.
5. **`llms.txt`** at the root, listing product pages, pricing, docs. Cheap, and
   increasingly read by agentic crawlers.
6. **Own the comparison pages** (`{name} vs {competitor}`) so prompt 6 has a
   source you control.
7. **Consistent handles** — the same string on GitHub, X, LinkedIn, YouTube.
   Fragmentation creates entity ambiguity.

Do not buy reviews, do not seed fake forum posts, do not create a Wikipedia
article for a brand that has no coverage. Models are increasingly good at
smelling astroturf, and the penalty is permanent.

---

## Part D — What GEO cannot do

- **Cannot rescue an entity collision.** If a famous film shares the name, no
  amount of schema markup separates you in a short answer.
- **Cannot substitute for being known.** Prompt 2 (discovery) is a popularity
  measure; a new brand is absent for months. Do not score prompt 2 as a failure
  at launch — score it as "not yet".
- **Cannot be measured once.** Engines change weekly. Re-run the battery after
  launch, then quarterly.

Say all of this in the report. A client who understands what GEO cannot do is a
client who trusts what it can.
