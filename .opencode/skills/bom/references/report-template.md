# Deliverable template — what the client actually receives

The engine writes `BOM-report.md`. This file describes what it must contain and
how to judge it before sending. If a section is missing, regenerate; do not
improvise around it.

## Structure

```
1. Corpus et clustering      keyword count, 5-cluster map, roots, brief extract
2. Generation des candidats  30, distribution by archetype, seed
3. Tableau comparatif BOM    rank, name, archetype, 4 pillars, total, verdict
4. Podium                     top 3, per-pillar bars, domains, actions
5. Rejets et raisons          hard-filtered names, one reason each
6. Ce qui reste a faire       Phase 3 packs: SERP queries, trademark links, GEO prompts
7. Methode, poids, limites    rubric table + explicit caveats
8. Racines a fort volume      top 20 roots with frequency and volume
+ dossiers/{name}.md          one page per top-5 finalist
+ BOM-scores.csv              spreadsheet export
```

## The comparative table is the deliverable

| Column | Must be true |
|---|---|
| `#` | dense ranking, no ties by number |
| `Nom` | display form, not the slug |
| `Archetype` | one of the five, never blank |
| 4 pillars | one decimal, sums to `Total` |
| `Total` | 0-100, consistent with the pillar sum |
| `Verdict` | GREENLIGHT / FORT / CONDITIONNEL / ECARTE / REJETE |

Anything with `*` next to the verdict is `provisional` (offline audit). A
provisional table must never be presented as a decision.

## Executive summary — 5 lines, no more

When you hand the report over, write this by hand. It is the part the client
actually reads.

```
Gagnant : {name} ({score}/100) — {one sentence why}.
Dauphin : {name} ({score}) — {the one reserve}.
Bloquant : {what must be cleared before any spend}.
A acheter aujourd'hui : {domains + handles}, {amount if known}.
Non verifie : {SERP / stores / trademark / GEO}, par {qui}, avant {date}.
```

Then stop. Do not paraphrase the report; attach it.

## Acceptance criteria

Before sending, verify all of these:

- [ ] `meta.mode` is `network` — or the report is labelled provisional everywhere.
- [ ] The top-10 table sums correctly and matches `BOM-scores.csv`.
- [ ] Every name in the podium has a `.com` status and a TLD list.
- [ ] Every rejected name has a reason in plain French/English.
- [ ] The Phase 3 packs exist for at least 3 finalists.
- [ ] The trademark section says "pre-screen, not clearance" and names the classes.
- [ ] The limits section is present, including the RDAP caveat and the rate-limit
      caveat.
- [ ] No claim of "available" without a date and a method.
- [ ] No invented ranking position, no invented search volume.

## Tone

Write like a consultant who has to defend the number in a meeting:

- **Facts with a date**: "RDAP au 15/11, .com libre".
- **Predictions labelled as such**: "SERP probablement vierge (0 homonyme exact
  detecte)" — never "SERP vierge".
- **Trade-offs stated**: "le nom gagne en GEO ce qu'il perd en distinctivite".
- **No adjectives without evidence**: "memorable" is not a finding; "7 lettres,
  test du telephone sans ambiguite" is.

## Common client objections, and the answer

| Objection | Answer |
|---|---|
| "Il n'y a pas de nom parfait" | True. The table shows the best trade-off, not a perfect name. |
| "Pourquoi .com compte autant ?" | 7/25: without it, every dictation, ad and business card loses traffic. |
| "On peut prendre le .io" | Yes, if you accept a developer-only audience and a recurring price. |
| "L'IA ne connait pas encore la marque" | Correct — that is why the GEO score measures readiness, not visibility. |
| "Ce nom est déjà pris sur GitHub" | A handle is not a brand. Decide whether the developer audience matters. |
| "On deposera plus tard" | Then you are building on land you do not own. File after securing domain and handles. |
