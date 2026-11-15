# Keyword intake and clustering

The corpus is the real brief. A naming project that starts from a slogan produces
a slogan; one that starts from 300 search queries produces a name people already
know how to ask for.

## 1. Accepted formats

`intake` reads `.txt`, `.csv`, `.tsv` and markdown lists. One keyword per line.

```
logiciel food cost,1900
logiciel restaurant,14800
"comment calculer food cost"
- meilleur logiciel restaurant ; 880
```

Parsing rules:

- CSV/TSV: first column = keyword, a numeric column becomes `volume`, an intent
  word (`commercial`, `transactional`…) becomes `declared_intent`.
- TXT/MD: bullets, numbering (`1.`, `-`, `*`) and trailing `, 1200` are stripped.
- Accents are normalised, duplicates removed on the normalised form.
- Lines starting with `#` are comments; URLs are ignored.

## 2. What a good corpus contains

| Family | Share | Examples |
|---|---|---|
| Benefit | 20-30% | `reduire cout matiere`, `gagner du temps cuisine` |
| Action | 20-30% | `calculer prix de revient`, `suivre food cost` |
| Tech / mechanism | 15-25% | `logiciel food cost`, `ocr facture fournisseur` |
| Target | 10-20% | `restaurateur independant`, `chef restaurant` |
| Metaphor | 5-15% | `miel`, `ruche`, `boussole`, `tour de main` |

Add the three layers that make a corpus usable:

1. **Head terms** (high volume, generic): `logiciel restaurant`.
2. **Long-tail with intent**: `comment calculer food cost` — these reveal the
   buyer's exact words, which is what GEO needs.
3. **Adjacent vocabulary**: competitor names, tool categories, job titles,
   store search suggestions.

Below 100 keywords the clusters are anecdotal. Above 500, deduplicate: the extra
rows do not add signal, they add runtime.

## 3. How clustering works

`scripts/bomlib/keywords.py`:

1. Tokenise, drop stopwords, keep FR/EN word forms.
2. Score each keyword against five lexicons (`CLUSTER_LEXICONS`), with a
   multiplier for phrase matches (`tableau de bord` counts 1.5).
3. Assign the best cluster; confidence is `high` at >= 2.5, `medium` at >= 1.5.
4. Keywords with zero lexical signal are spread evenly across the five clusters
   and flagged `confidence: none`. The count is reported as
   `meta.assigned_by_fallback`.
5. Root extraction ranks 1-2 grams by `frequency x intent bonus x volume`.

### Reading the output

```json
{
  "meta": { "total_keywords": 148, "clusters_used": 5, "assigned_by_fallback": 51 },
  "clusters": { "benefit": { "count": 30, "roots": ["marge", "cout"] }, ... },
  "roots": [ { "root": "prix", "freq": 9, "volume": 4300, "dominant_cluster": "tech" } ]
}
```

- **fallback > 40%** → the lexicons do not know this industry. Either add domain
  terms to `lexicons.py` (they are generic business words, keep them so) or
  accept a structural clustering and say it.
- **one cluster < 8%** → corpus bias. Add 10-15 keywords from that family before
  generating; otherwise the generator will produce five variations of the same
  idea.
- **top root is a generic word** (`restaurant`) → the corpus is too head-heavy.
  Add long-tail queries; a generic root produces generic names.

## 4. Root selection for naming

Not every high-frequency root is nameable. Keep a root only if:

- 3-9 letters, ASCII, pronounceable alone;
- not a bare dictionary noun (`restaurant`, `menu`) — it will be filtered later;
- not a stopword or an intent marker (`gratuit`, `meilleur`, `avis`);
- it says something to a buyer, not only to a search engine.

The generator applies these rules, but you should sanity-check the `roots` array
before generating. Five good roots beat forty noisy ones.

## 5. Multi-market corpora

If the client targets FR then EN:

- Tag rows with a market column (`keyword,volume,market`); run two intakes, or
  keep one corpus and note which roots are FR-only (`prix`, `marge`, `plat`).
- A name built on a FR-only root will not travel. Either accept a two-name
  strategy or weight the corpus toward international roots (`cost`, `menu`,
  `pilot`, `scan`).
- Never machine-translate the corpus: translated keywords have no volume. Use the
  English terms buyers actually type.

## 6. Refresh

Search behaviour drifts. Re-run intake quarterly with fresh query exports
(Search Console, store search suggestions, competitor ad copy). A corpus older
than 12 months produces names for a market that no longer exists.
