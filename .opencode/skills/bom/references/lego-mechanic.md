# The LEGO mechanic — contract a phrase into a brand

LEGO comes from the Danish **leg godt**, "play well". The name is not an
acronym and not a truncation: it keeps the *first two letters of each word*,
yielding something short, pronounceable, and apparently meaningless — which is
exactly what makes it registrable. (The Latin coincidence, *lego* = "I
assemble", is a bonus, not the origin.)

BOM generalises the mechanism and then subjects the result to the same audit as
any other candidate.

## Why translate first

`leg godt` is a *Danish* phrase. The brand was not born from an English
brainstorm; it was born from a mother tongue, contracted to fit a European
market. Naming in one language only wastes the space where short, meaningful
words live — Danish, Dutch, Polish, Turkish and Portuguese frequently compress
better than French or English.

So BOM takes each corpus concept and asks for it in the languages with the
largest online presence, then contracts. A French client asking for a food-cost
tool gets candidates built from *precio justo*, *costo chiaro*, *cena szybki*,
*geld klar* — not only *prix juste*.

## Languages

| Usable (romanised) | Listed, not used |
|---|---|
| en, es, fr, de, pt, it, nl, pl, tr, sv, da, no, id, vi, ru (Cyrillic → Latin), el (Greek → Latin) | ar, hi, zh, ja, ko |

The five excluded languages are excluded on purpose: BOM does not invent a
transliteration. A model that transliterates Chinese by feel produces a
plausible-looking string with no relationship to the source. If the client needs
a CJK name, that is a different project with a native speaker.

## Sources of translation

1. **Seed lexicon** (`scripts/bomlib/translate.py`) — ~35 concepts × 12
   languages, curated. Deterministic, offline, never wrong on the words it
   contains.
2. **MyMemory API** — free, keyless, cached 30 days, paced. Used for anything
   outside the lexicon.

A missing translation is reported as missing, never guessed. `translate.stats()`
lands in the report (`api_calls`, `cache_hits`, `failures`).

## The six contraction rules

Given a two-word phrase `w1 w2`:

| Rule | Build | `prix juste` | Shape |
|---|---|---|---|
| `lego2` | `w1[:2] + w2[:2]` | `priju` | the canonical LEGO shape |
| `head2` | first syllable of each | `priju` / `preju` (es) | keeps the sound |
| `head_tail` | first syllable + last syllable | `priuste` → repaired | more distinctive |
| `cvc2` | consonant+vowel of each | `piju` | shortest, least recoverable |
| `blend` | overlap merge | `prixuste` | only when letters overlap |
| `initials` | initials + linking vowel | `pjo` | last resort |

Repair then fixes what the rule breaks: 3+ consonant piles get a neutral vowel,
a final cluster gets a closing vowel, a vowel-poor string gets an opening, triple
letters collapse, length caps at 9.

## Fidelity (0-100)

Fidelity is not the BOM score. It answers: *would a speaker of the source
language recognise the phrase, and does it sound like a brand?*

| Component | Points |
|---|---|
| 2 syllables (3 = 26, 1 = 10, 4 = 12) | 30 |
| each source word still recognisable (2-3 letter trace) | 12 each |
| both source words >= 4 letters (enough material) | 6 |
| cross-language coverage (up to 4 languages) | 16 |
| pronounceability >= 80 | 10 |
| clean phone test | 6 |
| lucky positive meaning in another language | 4 |

Then the candidate enters the normal BOM grid (technique, SEO, GEO, commercial).
Ranking sorts on BOM total, with fidelity as the tie-breaker. The report shows
both columns: a name can be a great brand and a poor contraction, or the
reverse, and the client must see which.

## Selection: why the list is not 30 clones

- **One winner per (concept, qualifier, language)** — kills the
  `bico / bieco / biecou / biecourt` family.
- **Near-duplicate removal** — Levenshtein <= 1 against already selected names.
- **Language cap**: no language above 40% of the list.
- **Rule cap**: no rule above 60%, so the list shows several contractions.
- **Recoverability floor**: a name with zero trace of the phrase is discarded.

## Reference case (regression test)

```
phrase          leg godt        (Danish, "play well")
rule            lego2
contraction     le + go    ->   lego
BOM filter      brand collision: lego  -> REJETE
```

`bom.py selftest` asserts both halves. If a future change makes `leg godt`
produce something else, the mechanic has been broken.

## Limits to state in the report

- **Grammar is approximate.** Qualifiers are stored in one form; French and
  Spanish sometimes need gender agreement (*carte claire*, not *carte clair*).
  The report shows the source phrase so the client can judge; a native speaker
  fixes the wording, not the name.
- **Meaning is not guaranteed.** A contraction can be meaningless in the source
  language and meaningful in another — that is a feature, but it must be
  verified (the `coincidence` field flags the ones the lexicon knows).
- **Translation is not semantics.** "Cost" → *kosten* (German) also means
  "costs" plural; a translator returns a word, not a positioning.
- **A beautiful contraction can still be a bad brand.** That is what Phases 2-4
  are for. Never skip them because the story is good.

## When to prefer LEGO over the 5 archetypes

| Situation | Engine |
|---|---|
| Strong promise, 2-3 word expression, international ambition | `lego` |
| No clear phrase, need broad exploration | `archetypes` |
| Client wants "un nom qui veuille dire quelque chose" | `lego`, then refine |
| Client wants a short invented word, no meaning | `archetypes` (neologism) |

Best practice: run both, merge the shortlists, score once. The strongest
projects usually mix one LEGO name (story + ownability) with one GEO hybrid
(immediate category signal) and let the client choose the trade-off.
