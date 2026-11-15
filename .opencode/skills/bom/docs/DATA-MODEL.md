# Modèle de données

Six fichiers JSON traversent le pipeline. Tous portent un `meta` ; aucun n'est
rétro-compatible par accident — les schémas versionnés sont signalés.

```
clusters.json → candidates.json → audit.json → scores.json → research.json
                                                            ↗
                                              BOM-names.json (livrable)
```

## Vocabulaires fermés

| Contexte | Valeurs autorisées |
|---|---|
| Domaine | `available` · `registered` · `unknown` |
| Confiance domaine | `high` · `medium` · `low` · `none` |
| Registre de code | `libre` · `pris` · `ambigu` · `inconnu` · `manuel` |
| Store | `free` · `taken` · `ambiguous` · `manual` · `not_checked` |
| SERP (Phase 3) | `virgin` · `ambiguous` · `blocked` · `not_checked` |
| Marque | `clear` · `risk` · `blocked` · `not_checked` |
| Palier BOM | `GREENLIGHT` · `FORT` · `CONDITIONNEL` · `ECARTE` · `REJETE` |

Un statut inconnu n'est jamais converti : il reste `unknown`/`inconnu`/`?`.

---

## 1. `clusters.json` — Phase 1

```json
{
  "meta": {
    "total_keywords": 148,
    "clusters_used": 5,
    "unclassified": 51,
    "assigned_by_fallback": 51
  },
  "intents": { "informational": 114, "commercial": 15, "transactional": 18, "navigational": 1 },
  "clusters": {
    "benefit": {
      "id": "benefit",
      "label": "Benefice",
      "count": 30,
      "share": 0.2027,
      "roots": ["marge", "cout", "rentabilite"],
      "keywords": [
        {
          "text": "marge brute restaurant",
          "normalized": "marge brute restaurant",
          "volume": 620,
          "declared_intent": null,
          "tokens": ["marge", "brute", "restaurant"],
          "cluster": "benefit",
          "cluster_confidence": "high",
          "matched_terms": ["marge"],
          "intent": "informational"
        }
      ]
    }
  },
  "roots": [
    {
      "root": "marge",
      "phrase": "marge",
      "freq": 9,
      "volume": 4300,
      "score": 12.6,
      "clusters": { "benefit": 9 },
      "dominant_cluster": "benefit",
      "multiword": false
    }
  ],
  "per_cluster_roots": { "benefit": ["marge"] },
  "brief": { "raw": "...", "tokens": ["saas", "food", "cost"] },
  "sources": { "keywords": "corpus.csv", "brief": "brief.md" }
}
```

Notes : `assigned_by_fallback` compte les mots-clés sans signal lexical,
répartis par équilibrage ; au-delà de 40 %, le clustering doit être signalé
comme structurel.

## 2. `candidates.json` — Phase 1b

```json
{
  "meta": {
    "count": 30, "requested": 30, "seed": 7,
    "distribution": { "descriptive": 6, "blend": 6, "metaphor": 6, "neologism": 6, "geo": 6 },
    "roots_used": 18, "leads_used": { "prix": 2 },
    "engine": "lego",
    "languages_requested": ["fr", "en", "es"],
    "phrases_evaluated": 864,
    "translator": { "provider": "mymemory", "api_calls": 0, "cache_hits": 12, "failures": 0 }
  },
  "archetypes": { "lego": "Contraction LEGO" },
  "candidates": [
    {
      "name": "cosmo",
      "display": "Cosmo",
      "archetype": "lego",
      "archetype_label": "Contraction LEGO",
      "rationale": "'cost smart' (en) -> 2 premieres lettres de chaque mot : 3 provenances dans 2 langues.",
      "roots": ["cost", "smart"],
      "clusters": ["lego", "cost"],
      "geo_anchor": ["cost", "smart"],
      "length": 5, "syllables": 2,
      "pronounceability": 100, "phone_penalty": 0,
      "flags": { "soft_bad": [], "first_name": false, "dictionary_noun": false, "cliche_suffix": false },
      "generation_score": 92,
      "fidelity": 92,
      "source_language": "en",
      "source_phrase": "cost smart",
      "translations": { "en": "cost smart", "fr": "cout malin", "es": "coste listo" },
      "rule": "lego2",
      "provenance": [
        { "phrase": "cost smart", "language": "en", "rule": "lego2",
          "rule_label": "2 premieres lettres de chaque mot (regle LEGO)",
          "order": "natural", "concept": "cost", "qualifier": "smart", "fidelity": 92 }
      ]
    }
  ]
}
```

Champs spécifiques au moteur LEGO : `fidelity`, `source_phrase`,
`source_language`, `translations`, `rule`, `provenance`. Absents pour les 5
archétypes, où `generation_score` joue le même rôle de tri interne.

## 3. `audit.json` — Phase 2

```json
{
  "meta": {
    "mode": "network",
    "tlds": ["com", "app", "ai", "io", "fr"],
    "audited": 30, "hard_failed": 2, "survivors": 28,
    "generated_at": "2026-11-15T14:48:00",
    "caveats": ["RDAP 404 = probablement libre, pas une garantie"]
  },
  "candidates": [
    {
      "name": "prixrank",
      "static": {
        "hard_fail": false,
        "hard_fail_reasons": [],
        "warnings": [],
        "checks": {
          "length": 8, "syllables": 2, "pronounceability": 100,
          "phone_penalty": 0, "vowel_ratio": 0.38,
          "fr_issues": [], "en_issues": []
        }
      },
      "domains": [
        { "tld": "com", "domain": "prixrank.com", "status": "available",
          "confidence": "high", "detail": "RDAP: aucune inscription trouvee (404)",
          "registrar": null, "created": null, "url": "https://prixrank.com" }
      ],
      "registries": [
        { "id": "npm", "label": "npm", "status": "libre", "detail": "aucun paquet npm",
          "url": null }
      ],
      "stores": [
        { "id": "itunes", "label": "App Store", "status": "libre",
          "detail": "0 app(s) remontent pour 'prixrank'", "url": "https://apps.apple.com/fr/search?term=prixrank" }
      ],
      "serp": {
        "status": "pending_web_search",
        "queries": ["\"prixrank\"", "\"prixrank\" app"],
        "urls": { "google": "https://www.google.fr/search?q=%22prixrank%22" },
        "acceptance": { "serp_virgin": "0-2 resultats organiques hors dictionnaire" }
      },
      "trademarks": {
        "status": "manual_screen_required",
        "classes": [9, 42],
        "urls": { "inpi": "https://data.inpi.fr/search?q=prixrank" },
        "note": "Aucune API publique gratuite..."
      },
      "summary": {
        "domains_available": ["com", "app"], "domains_registered": [],
        "domains_unknown": ["ai", "io", "fr"],
        "com_available": true,
        "registries_free": ["github_user", "npm", "pypi"],
        "registries_taken": [], "registries_ambiguous": []
      }
    }
  ],
  "survivors": ["prixrank"],
  "hard_failed": ["restaurant"]
}
```

`mode` vaut `network` ou `static-only`. En `static-only`, tous les domaines sont
`unknown` et le score sera `provisional`.

## 4. `scores.json` — Phase 4

```json
{
  "meta": {
    "scored": 30, "greenlight": 4, "strong": 6, "measured": 0,
    "rubric": { "technique": { "label": "Disponibilite technique & handles", "max": 25 } },
    "weights": "4 piliers de 25 points: technique, SEO, GEO, commercial"
  },
  "ranking": [
    {
      "rank": 1, "name": "prixrank", "display": "Prixrank",
      "tier": "GREENLIGHT", "provisional": false, "measured": false,
      "verdict": "A acheter et deposer maintenant",
      "total": 92.9, "max": 100,
      "pillars": {
        "technique": {
          "score": 24.3, "max": 25,
          "parts": {
            "com": { "score": 7.0, "max": 7, "note": ".com libre (RDAP) : actif principal disponible" },
            "tlds": { "score": 4.0, "max": 4, "note": "3 TLD secondaire(s) libre(s): app, io, fr" }
          }
        },
        "seo": { "score": 23.9, "max": 25, "parts": { "virginity": { "score": 8.0, "max": 8, "note": "..." } } },
        "geo": { "score": 21.4, "max": 25, "parts": { "collision": { "score": 8.2, "max": 9, "note": "..." } },
                 "prompt_battery": [ { "id": "category", "engine_agnostic": "...", "status": "a_executer_en_phase_3" } ] },
        "commercial": { "score": 23.3, "max": 25, "parts": { "phone": { "score": 3.0, "max": 3, "note": "..." } } }
      },
      "evidence": { "technique": ["..."], "seo": ["..."], "geo": ["..."], "commercial": ["..."] },
      "open_actions": ["Reserver prixrank.com sous 24 h", "..."],
      "research": null
    }
  ],
  "podium": ["prixrank", "cuisicost", "fournimeter"]
}
```

Un `part` peut porter `"measured": true` lorsque la Phase 3 a fourni la valeur.

## 5. `research.json` — Phase 3 fusionnée (`bom.research/v1`)

```json
{
  "meta": {
    "schema": "bom.research/v1",
    "generated_at": "2026-11-15T15:20:00",
    "sources": ["packets/results/batch-1.json"],
    "names": 10, "measured": 9, "unknown": 1,
    "warnings": ["prixrank: marque non verifiee (classes 9/42)"]
  },
  "by_name": {
    "prixrank": {
      "name": "prixrank",
      "serp": { "verdict": "virgin", "organic_results": 1, "dominant_entity": null,
                "notes": "...", "sources": ["https://..."] },
      "stores": { "app_store": "free", "play_store": "free", "product_hunt": "free" },
      "trademark": { "verdict": "clear", "matches": [], "notes": "..." },
      "geo": { "fails": 0, "hedges": 1, "passes": 6, "notes": "...", "engines": { "chatgpt": "..." } },
      "measured": true
    }
  }
}
```

Effets sur le score : `serp.verdict` remplace la virginité estimée ;
`geo.fails` pondère la collision GEO ; `trademark.verdict = blocked` force
`REJETE` ; un store `taken` ajoute une réserve au verdict.

## 6. `BOM-names.json` — livrable (`bom.names/v1`)

Vue aplatie, destinée à l'intégration : `audit` (mode, TLD, caveats), `rubric`,
`corpus`, et `ranking[]` avec `pillars` (scores seuls), `domains`, `registries`,
`stores`, `warnings`, `actions`. Contient **tout** le classement, quelle que
soit la valeur de `--top`.

## Invariants à respecter si vous produisez ces fichiers vous-même

1. `total` = somme des quatre piliers (± 0.05).
2. `tier` cohérent avec `total` (seuils 88/78/62) sauf `REJETE`.
3. `name` en minuscules ASCII, unique.
4. `meta.mode` présent dans `audit.json`.
5. Aucun statut hors vocabulaire : préférez `not_checked` à une valeur inventée.
