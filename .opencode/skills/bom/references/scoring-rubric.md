# Scoring rubric — the 100-point BOM grid

Four pillars, 25 points each. The point of the equal split is political as much
as analytical: a name that wins on SEO but loses on GEO is not "80% good", it is
a trade-off the client must see. Equal weights make that trade-off legible.

| Pillar | Code | 25 pts |
|---|---|---|
| Disponibilite technique & handles | `technique` | .com 7 · TLD secondaires 4 · registres 6 · frappe 4 · clearance 4 |
| Note SEO classique | `seo` | virginite 8 · rankabilite 7 · intention 5 · longue traine 3 · snippet 2 |
| Note GEO / moteurs IA | `geo` | collision 9 · transparence 7 · hallucination 5 · stabilite 4 |
| Potentiel commercial & branding | `commercial` | telephone 3 · FR 3 · EN 3 · longueur 4 · memoire 4 · extensibilite 3 · logo 2 · fit 3 |

Implementation: `scripts/bomlib/score.py`. Every part writes a `note` string that
lands in the report — if a score cannot be explained in one sentence, it is a
bug.

---

## 1. Disponibilite technique & handles (25)

### .com — 7 pts
| Situation | Points |
|---|---|
| RDAP 404, DNS absent | 7 |
| RDAP registered | 0 |
| Unknown / no network | 3.15 (45%) and the run is flagged `provisional` |

Why 7: the `.com` is the only TLD a French SMB owner types by reflex. A name
without it needs a marketing budget the project usually does not have.

### TLD secondaires — 4 pts
Count of free TLDs among `.ai`, `.app`, `.io`, `.fr`, scaled by 3 (three free =
full marks). Unknown TLDs add a small credit (max +0.9) because "unverified" is
not "taken" — but never full marks.

### Registres de code & handles — 6 pts
| Check | Free | Unknown | Taken |
|---|---|---|---|
| GitHub account | 2.0 | 0.8 | 0 |
| npm | 1.5 | 0.6 | 0 |
| PyPI | 1.5 | 0.6 | 0 |
| GitHub repos (0 hits) | 1.0 | 0.3 | 0 |

A taken GitHub account mostly matters if you plan to open-source or if developer
audience is the target. A taken npm/PyPI package matters if you ship a library.

### Resistance aux fautes de frappe — 4 pts
Derived from the phone penalty (B/P, D/T, M/N, letters that must be spelled:
y, w, k, q, h) and global pronounceability. A name that cannot be dictated to a
supplier over the phone loses here, not in branding.

### Pre-filtre de clearance — 4 pts
| Signal | Penalty |
|---|---|
| Bare dictionary noun | -3.0 |
| Common first name | -1.8 |
| Known brand collision | -4.0 (also a hard filter) |
| 4 letters or fewer | -0.6 |

This is a pre-screen, not a clearance. Phase 3 remains mandatory.

---

## 2. Note SEO classique (25)

### Virginite SERP — 8 pts
Proxy before Phase 3: count exact collisions across GitHub account, GitHub
repos, npm, PyPI, App Store.

| Exact collisions | Points | Reading |
|---|---|---|
| 0 | 8 | page 1 is probably empty of homonyms |
| 1 | 5.6 | #1 reachable with content |
| 2 | 3.6 | editorial work required |
| 3+ | 1.6 | exact query not ownable |
| bare dictionary word | 0 | the query belongs to the language |

Phase 3 overrides this proxy: if a search returns a film, a brand or a celebrity
on page 1, virginity goes to 0 regardless of the API count.

### Facilite a ranker #1 — 7 pts
Starts at 7, minus 3 for a dictionary word, minus 2 for a first name, minus 1 per
exact collision (max 2), plus 0.8 if the name is >= 6 letters and not generic.
Rationale: ranking #1 on your own brand is trivial *if* nobody else uses the
string; it is a content war if the string means something else.

### Intention de recherche alignee — 5 pts
Does the name contain a root that carries volume in the corpus? Scored from the
`roots` array produced by `intake`. Two matching roots = full marks; zero =
50%, because a name with no corpus root must create its demand from scratch.

### Potentiel longue traine — 3 pts
Presence of a category morpheme (`rank`, `scan`, `lens`, `deck`…) so that
`brand + metier` queries exist naturally. A pure neologism caps at 1.2.

### Snippet & sitelinks — 2 pts
Length <= 12, no first-name dilution, no knowledge-panel conflict.

> Note: SEO scores are *structural predictions*. Only Phase 3 measures reality.
> Say "prediction" in the report, never "position".

---

## 3. Note GEO / moteurs IA (25)

GEO = Generative Engine Optimization. The question is not "where do I rank" but
"when a model answers *give me a tool that does X*, does it say my name, and does
it say something true?"

### Absence de collision avec des entites connues — 9 pts
Penalties are additive, capped at 14 then inverted:

| Signal | Penalty | Why |
|---|---|---|
| Known brand in the string | 3.0 | model already has a strong prior |
| GitHub account | 2.0 | developer entity exists |
| npm package | 1.5 | package entity exists |
| PyPI package | 1.5 | package entity exists |
| App Store exact match | 2.5 | product entity exists |
| Bare dictionary word | 2.5 | meaning floods the embedding |
| Common first name | 1.5 | person entity wins |
| GitHub repo present | 1.0 | noise |

An LLM with a name it has never seen will hedge. A name it *has* seen attached to
someone else will be confidently wrong. Both are failures, differently.

### Ancrage semantique immediat — 7 pts
Would a model guess the sector from the string alone? Count of category
morphemes present (`scan`, `rank`, `cost`, `menu`, `pilot`, `flow`, `meter`…),
plus a bonus if the candidate carries a `geo_anchor`. Zero morphemes = the model
answers "I don't know what this is" — acceptable for a funded brand with a
content strategy, fatal for a small launch.

### Risque d'hallucination / attribution — 5 pts
Starts at 5. Minus 1.4 per exact collision (max 3), minus 1.5 for a dictionary
word, minus 1.0 for a first name, plus 0.8 if there is a geo anchor. Low scores
mean the model will invent a price, a founder or a launch date — and attribute
them to you.

### Stabilite inter-moteurs — 4 pts
Composite of collision and transparency, plus 0.4 when there are zero exact
collisions. High score = ChatGPT, Perplexity, Gemini and Claude will roughly
agree. Low score = each engine tells a different story; a buyer testing the name
in two tools sees two companies.

Full battery to run in Phase 3: `geo-audit.md`.

---

## 4. Potentiel commercial & branding (25)

### Test du telephone — 3 pts
`3 - 0.3 x phone_penalty`. Models letters that get confused when dictated
(y/w/k/q/h, B/P, D/T, M/N), vulgar triple vowels and doubled letters.

### Prononciation FR — 3 pts
`3 - 0.7 x issues`. Issues: `th` read as `t`, final `-ck`, SaaS `-ly`/`-ify`
after 6 letters, `w` without vowel, initial vowel (elision: "l'app").

### Prononciation EN — 3 pts
`3 - 0.8 x issues`. Issues: silent onsets (`kn`, `gn`, `pn`, `ps`), ambiguous
vowel digraphs, silent final `e`, rare clusters (`zh`, `kh`, `gh`).

### Longueur — 4 pts
| Letters | Points |
|---|---|
| <= 7 | 4.0 |
| 8-9 | 3.4 |
| 10-11 | 2.2 |
| 12-13 | 1.2 |
| 14+ | 0.4 |

### Memorabilite — 4 pts
Base 2, +0.8 if not a first name, +0.8 if not a dictionary word, +0.4 if letter
diversity is high, -0.6 above 11 letters.

### Extensibilite — 3 pts
Can it carry a range (app, API, desktop, add-on) without renaming? Short + a geo
anchor + brief alignment score highest.

### Potentiel de marque visuelle — 2 pts
Short name, clean letters, no FR reading issue → monogram or pictogram possible.

### Fit positionnement / brief — 3 pts
Overlap between the candidate's anchors and the brief tokens. This is the only
subjective part; keep it disciplined — a name that contradicts the tone (gadget
name for a serious B2B tool) loses here and nowhere else.

---

## Worked example

`prixrank` (real run, network audit):

| Pillar | Score | Driver |
|---|---|---|
| Technique | 23.6 | `.com` + `.app` free, GitHub/npm/PyPI free, phone penalty low |
| SEO | 23.9 | zero collisions, 2 corpus roots (`prix`, `rank`), category morpheme |
| GEO | 21.4 | no entity collision, strong anchor, but `prix` is French-only |
| Commercial | 23.3 | 8 letters, 2 syllables, FR/EN readable, test telephone clean |
| **Total** | **92.2** | GREENLIGHT |

What the score does *not* say: `prixrank` is FR-only in meaning, and reads as
"price ranking" to an English buyer. That nuance belongs in the report prose,
next to the number — not inside it.

---

## Calibration rules

1. A perfect name is ~92, not 100. Above 95 means a part is over-credited.
2. Two names within 3 points are tied in practice; break ties with `.com` price,
   then length, then phone test.
3. If every candidate lands 78-82, the audit was offline or the corpus was
   homogeneous. Check `meta.mode` before presenting.
4. If a pillar is identical across all candidates (e.g. TECH 25.0 everywhere),
   the pillar is not discriminating — say which pillar is flat and why.
5. Never re-weight the pillars silently. If the client wants SEO x2, state the
   new weighting in the report header and recompute explicitly.
