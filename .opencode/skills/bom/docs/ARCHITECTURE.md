# Architecture

## Vue d'ensemble

BOM est un pipeline de fichiers, pas un service. Chaque étape lit un JSON, écrit
un JSON, et peut être rejouée isolément. Cette contrainte est volontaire : elle
rend le résultat auditable, reproductible et testable sans réseau.

```
                 ┌──────────────┐
 keywords.csv ──▶│   keywords   │──▶ clusters.json
 brief.md        └──────────────┘         │
                                          ▼
                        ┌────────────┬────────────┐
                        │  generate  │    lego    │──▶ candidates.json
                        │ (5 familles)│ (contrat.) │
                        └────────────┴────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │    audit    │──▶ audit.json
                                   │  RDAP/DNS/  │
                                   │  registries │
                                   └─────────────┘
                                          │
        research.json ◀── merge ◀── sub-agents (phase 3)
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │    score    │──▶ scores.json
                                   └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │   report    │──▶ report.md / xlsx / json
                                   └─────────────┘
```

## Modules

| Module | Rôle | Dépend de |
|---|---|---|
| `bomlib/keywords.py` | ingestion, tokenisation, clustering 5 classes, extraction de racines | `lexicons`, `text` |
| `bomlib/generate.py` | 5 archétypes, filtres durs, diversité des attaques | `lexicons`, `text` |
| `bomlib/translate.py` | langues, lexique seed, MyMemory, romanisation | `text` |
| `bomlib/lego.py` | construction d'expressions, 6 règles de contraction, fidélité | `lexicons`, `text`, `translate`, `generate.accept_name` |
| `bomlib/audit.py` | filtrage statique, RDAP+DNS, registres, stores, packs Phase 3 | `lexicons`, `text` |
| `bomlib/research.py` | paquets de sous-agents, fusion, normalisation des verdicts | `lexicons`, `text` |
| `bomlib/score.py` | 4 piliers × 25, piliers GEO, tiers, actions | `lexicons`, `text` |
| `bomlib/export.py` | XLSX (OOXML stdlib), JSON consolidé, lignes de classement | `lexicons`, `score` |
| `bomlib/report.py` | rapport Markdown, CSV, dossiers, orchestration des exports | `lexicons`, `score`, `export`, `text` |
| `bomlib/text.py` | slug, phonétique, Levenshtein, filtres de mots | — |
| `bomlib/lexicons.py` | données statiques : clusters, morphèmes, blocklists | — |
| `scripts/bom.py` | CLI, orchestration, état de run | tous |

Acyclic : `score` ne connaît pas `report`, `audit` ne connaît pas `score`.
`lego` est le seul module à importer une fonction d'un autre générateur
(`accept_name`), pour garantir un filtre unique.

## Flux de données

```
clusters.json ──┐
                ├──▶ candidates.json ──▶ audit.json ──▶ scores.json ──▶ report/
brief.md ───────┘                              ▲
                                               │
                        research.json ─────────┘  (optionnel, Phase 3 mesurée)
```

Chaque fichier porte son `meta` : mode, paramètres, horodatage, et pour
`audit.json` les caveats. Un JSON sans `meta` est considéré comme corrompu.

## Invariants (vérifiés par `selftest`)

1. `total == technique + seo + geo + commercial` (± 0.05).
2. `0 ≤ total ≤ 100` pour tout candidat non rejeté.
3. `hard_fail ⇒ tier == "REJETE"`.
4. Un candidat `measured` possède un bloc `research` non vide.
5. Les noms sont uniques, ASCII, alphabétiques.
6. Chaque candidat porte une `rationale` non vide.
7. Chaque candidat LEGO porte `source_phrase` et `fidelity`.
8. Le classeur XLSX contient `[Content_Types].xml`, `xl/workbook.xml`,
   `xl/worksheets/sheet1.xml`, `xl/styles.xml`.
9. Le JSON `bom.names/v1` contient tout le classement, même si le rapport est
   tronqué à `--top`.

## Déterminisme

- Générateurs : `random.Random(seed)` — défaut 7. Aucun `random` global.
- Tri : `(-total, -fidelity, name)` ; à score égal, l'ordre alphabétique tranche.
- Audit : résultats réordonnés selon l'ordre d'entrée, malgré le parallélisme.
- Score : fonction pure des entrées (`audit`, `clusters`, `research`).
- Aucune dépendance à la date, sauf les horodatages de `meta`.

Conséquence : un run peut être rejoué à l'identique pour un rapport client, à
condition de conserver `audit.json` (les statuts réseau, eux, changent).

## Réseau : concurrence, cache, échecs

| Aspect | Implémentation |
|---|---|
| Parallélisme | `ThreadPoolExecutor`, `--workers` (défaut 6) |
| Politesse | pacing par hôte : 0.25 s (audit), 0.35 s (traduction) |
| Timeout | 8 s par requête (`--timeout`) |
| Retries | 2, backoff linéaire ; `429` traité à part |
| Cache audit | `<cache-dir>/*.json`, TTL 7 j (ok) / 24 h (erreur) |
| Cache traduction | `<cache-dir>/translate/*.json`, TTL 30 j |
| User-Agent | `bom-skill/1.0` — identifiable, honnête |

**Sémantique d'échec.** Une réponse inattendue devient `unknown` / `inconnu`,
jamais `available`. Un `403` GitHub est un quota, pas une absence. Un `404` RDAP
est un signal fort, pas une garantie contractuelle.

## Pourquoi pas de dépendances

| Besoin | Solution retenue | Alternative écartée |
|---|---|---|
| HTTP | `urllib` | `requests` (dépendance) |
| XLSX | OOXML écrit à la main + `zipfile` | `openpyxl` (dépendance, 2 Mo) |
| JSON | stdlib | — |
| Traduction | lexique + MyMemory | DeepL (clé, coût) |
| WHOIS/RDAP | RDAP + DNS | `python-whois` (parsing fragile) |

Le coût est un peu de code ; le bénéfice est un skill qui tourne partout, hors
ligne, sans `pip install`, y compris dans un environnement d'entreprise verrouillé.

## Frontière jugement / lecture

Le moteur ne fait aucun choix esthétique : il produit du matériau et des
mesures. Les décisions de goût sont déléguées au modèle de création, les
lectures au modèle de recherche, la cohérence au rapport. Cette séparation est
la raison d'être des sous-agents (voir `agents/README.md`) — et la raison pour
laquelle le moteur reste testable.

## Performance observée

| Opération | Ordre de grandeur |
|---|---|
| `intake` sur 148 mots-clés | < 100 ms |
| `generate` 30 noms | < 100 ms |
| `lego` 24 noms, 864 expressions, hors ligne | ~ 0.5 s |
| `audit` 30 noms × 5 TLD + registres | 2-4 min (réseau, `--workers 6`) |
| `score` + `report` + xlsx | < 300 ms |

Le cache divise les audits suivants par 5 à 10.

## Ce que l'architecture interdit

- Écrire dans `assets/` ou dans le corpus : les entrées sont en lecture seule.
- Acheter un domaine, déposer une marque ou appeler une API payante.
- Lancer un sous-agent sans accord utilisateur (voir `dispatch`).
- Présenter un `unknown` comme un feu vert.
