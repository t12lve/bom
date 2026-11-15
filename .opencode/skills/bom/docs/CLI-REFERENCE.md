# Référence CLI

Point d'entrée unique : `scripts/bom.py`. Toutes les commandes écrivent du JSON
sauf `report` (Markdown + Excel + CSV + JSON), `merge` (JSON) et `export`.

```
bom {intake,generate,audit,lego,dispatch,merge,export,score,report,check,run,selftest}
bom --version
bom <commande> --help
```

## Options transverses

| Option | Défaut | S'applique à | Effet |
|---|---|---|---|
| `--tlds` | `com,app,ai,io,fr` | audit, check, lego, run | liste séparée par virgules, sans point |
| `--offline` | faux | audit, check, lego, run | aucun appel réseau ; scores marqués `provisoire` |
| `--quick` | faux | audit, check, lego, run | domaines seulement, pas de registres de code |
| `--workers` | `6` | audit, check, lego, run | threads réseau |
| `--timeout` | `8.0` | audit, check, lego, run | secondes par requête |
| `--cache-dir` | `.bom-cache` | audit, check, lego, run | cache HTTP et traductions |
| `--count` | `30` | generate, lego, run | nombre de candidats demandés |
| `--seed` | `7` | generate, lego, run | graine du générateur |
| `--top` | `10` | report, dispatch, lego, run | lignes du tableau / candidats audités en Phase 3 |
| `--langs` | 10 premières langues latines | lego, run | ex. `fr,en,es,de,da` |
| `--source-lang` | `fr` | lego, run | langue du corpus |
| `--translator` | `mymemory` | lego, run | `mymemory` (sans clé) ou `offline` (lexique seul) |

## Variables d'environnement

| Variable | Effet |
|---|---|
| `GITHUB_TOKEN` ou `GH_TOKEN` | authentifie les appels `api.github.com` (5 000 req/h au lieu de 60). Sans token, un `403` déclenche un disjoncteur : les vérifications restantes passent en `inconnu` au lieu de marteler l'API. |
| `PYTHONIOENCODING` | forcé à `utf-8` par le CLI ; utile seulement si vous importez `bomlib` directement. |

Aucune autre variable n'est lue. Aucun fichier `.env` n'est chargé
implicitement : exportez la variable dans le shell.

---

## `intake` — Phase 1

```bash
bom intake --keywords corpus.csv --brief brief.md --out work/clusters.json --csv work/keywords.csv
```

| Option | Requis | Défaut | Note |
|---|---|---|---|
| `--keywords` | oui | — | `.txt`, `.csv`, `.tsv`, `.md` |
| `--brief` | non | — | texte libre, alimente les ancrages |
| `--out` | non | `clusters.json` | |
| `--csv` | non | — | export lisible du clustering |

Sortie : 5 clusters, racines classées, intentions, `assigned_by_fallback`.
Erreur si aucun mot-clé lisible (code 1).

## `generate` — Phase 1b, 5 archétypes

```bash
bom generate --clusters work/clusters.json --count 30 --seed 7 --out work/candidates.json
```

Aucune option obligatoire au-delà de `--clusters`. Le résultat contient
`meta.distribution` (répartition par archétype).

## `lego` — Phase 1b, contraction multilingue

```bash
bom lego --keywords corpus.csv --brief brief.md \
  --langs fr,en,es,de,da --count 24 --out-dir runs/lego
```

Pipeline complet en une commande (intake → LEGO → audit → score → report).
Options supplémentaires : voir `--langs`, `--translator`, `--source-lang`.
`--offline` coupe la traduction **et** l'audit : le lexique seed reste utilisé.

## `audit` — Phase 2

```bash
bom audit --candidates work/candidates.json --tlds com,app,ai --out work/audit.json
```

| Option | Défaut | Note |
|---|---|---|
| `--candidates` | requis | |
| `--quick` | faux | saute GitHub/npm/PyPI/crates/iTunes |
| `--offline` | faux | filtrage statique uniquement |

Écrit aussi les *packs Phase 3* dans chaque candidat (`serp`, `trademarks`),
immédiatement exploitables par un sous-agent ou à la main.

## `score` — Phase 4

```bash
bom score --audit work/audit.json --clusters work/clusters.json \
  --research work/research.json --out work/scores.json
```

`--research` est optionnel : avec, les mesures Phase 3 remplacent les
extrapolations ; sans, le score reste prévisionnel. `--limit N` tronque après
tri (le classement complet est préférable).

## `report` — Phase 5

```bash
bom report --scores work/scores.json --audit work/audit.json \
  --clusters work/clusters.json --candidates work/candidates.json \
  --top 10 --out report
```

Produit `BOM-report.md`, `BOM-names.xlsx`, `BOM-names.json`, `BOM-scores.csv`,
`dossiers/*.md`. `--top` ne tronque **que** le tableau du rapport : les exports
contiennent tout le classement.

## `dispatch` — paquets de sous-agents

```bash
bom dispatch --phase 1 --clusters work/clusters.json --out packets
bom dispatch --phase 3 --scores work/scores.json --top 10 --batch 3 --out packets
```

| Phase | Requis | Produit |
|---|---|---|
| `1` | `--clusters` | un paquet par cluster, tier `creation` |
| `3` | `--scores` | un paquet par `--batch` candidats, tier `research` |

Chaque paquet est autonome : contexte, instructions, schéma de sortie,
critères d'acceptation, `requires_user_approval: true`. Aucun modèle n'est
appelé par cette commande.

## `merge` — fusion des résultats

```bash
bom merge --inputs packets/results/*.json --out work/research.json
```

Normalise les verdicts, ignore les noms inconnus, conserve la première mesure en
cas de conflit, signale les marques non vérifiées. Ne lève pas d'erreur sur un
fichier illisible : il l'annonce dans `meta.warnings`.

## `export` — Excel + JSON sans re-audit

```bash
bom export --scores work/scores.json --audit work/audit.json \
  --clusters work/clusters.json --candidates work/candidates.json --out report
```

Idempotent. Utile après une correction manuelle des notes ou pour régénérer un
livrable après `merge`.

## `check` — shortlist ad hoc

```bash
bom check --names "rankly,hivelens,menuscope" --tlds com,fr --offline
```

Les noms sont slugifiés, audités, notés, affichés. Aucun corpus, aucun brief.
Pratique pour arbitrer deux finalistes en réunion.

## `run` — pipeline complet

```bash
bom run --keywords corpus.csv --brief brief.md --out-dir runs/acme \
  --engine archetypes --top 10 --tlds com,app,ai,fr
```

`--engine lego` bascule sur la contraction multilingue. `--research` réinjecte
un `research.json` déjà fusionné. Écrit `state.json` (carte des fichiers, mode,
prochaines étapes).

## `selftest` — non-régression

```bash
bom selftest
```

60 assertions hors ligne : pipeline complet, invariants de score, exports,
mécanique LEGO (`leg godt → lego`, puis rejet de `lego`), paquets et fusion.
Code de sortie 0 si tout passe, 1 sinon. À lancer avant toute livraison et en CI.

---

## Codes de sortie

| Code | Cause |
|---|---|
| `0` | succès |
| `1` | fichier absent, JSON invalide, `--names` vide, selftest en échec |
| `2` | argument invalide (argparse) |

## Pièges courants

| Symptôme | Cause | Correctif |
|---|---|---|
| `--tlds .com` | point inclus | `--tlds com` |
| 0 candidat LEGO | `--translator offline` + corpus sans concept du lexique | retirer `--offline`, ou ajouter les concepts |
| Tous les scores à 78-82 | audit hors ligne | relancer sans `--offline` |
| `?` partout | RDAP/API muets ou quota | attendre, `--workers 2`, vérifier à la main |
| Rapport tronqué à 10 lignes | `--top` | c'est voulu ; les exports restent complets |
| `ModuleNotFoundError: xml` | un fichier `xml.py` traîne dans le dossier courant | exécuter depuis un dossier propre |
