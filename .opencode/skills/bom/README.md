# BOM — Brand, Optimization & Market-readiness

Un skill de naming commercial : d'un corpus de 100 à 500+ mots-clés, il produit
des noms d'application ou de marque, les audite (domaines, registres de code,
stores, antériorité), les note sur 100 — moitié SEO classique, moitié GEO
(moteurs IA) — et rend un rapport exploitable.

Le nom du skill est un private joke : **BOM** = *Burger au Miel*. Ne le dites
pas au client.

## En 60 secondes

```bash
# 1. pipeline complet (5 archétypes)
python scripts/bom.py run --keywords assets/keywords.example.csv \
  --brief assets/brief.example.md --out-dir runs/demo

# 2. moteur LEGO (leg godt -> LEGO)
python scripts/bom.py run --engine lego --keywords assets/keywords.example.csv \
  --brief assets/brief.example.md --langs fr,en,es,de,da --out-dir runs/lego

# 3. vérifier que tout fonctionne, hors ligne
python scripts/bom.py selftest
```

Sorties : `report/BOM-report.md`, `BOM-names.xlsx`, `BOM-names.json`,
`BOM-scores.csv`, `dossiers/`.

Aucune dépendance à installer, aucune clé API. Python 3.9+.

## Les deux moteurs

| Moteur | Ce qu'il produit | Quand |
|---|---|---|
| `archetypes` | 30 noms sur 5 familles : descriptif hybride, mot-valise, métaphorique, néologisme ≤ 7, hybride GEO | exploration large, pas d'expression forte |
| `lego` | contraction d'une expression traduite en 10+ langues, 2-3 syllabes, avec fidélité /100 | promesse nommable, nom « qui veut dire quelque chose » |

## La note sur 100

| Pilier | Points | Mesure |
|---|---|---|
| Disponibilité technique & handles | 25 | `.com`, TLD secondaires, GitHub/npm/PyPI, frappe, pré-filtre marque |
| SEO classique | 25 | virginité SERP, rankabilité, intention, longue traîne, snippet |
| GEO / moteurs IA | 25 | collision d'entités, ancrage sémantique, hallucination, stabilité |
| Commercial & branding | 25 | téléphone, FR/EN, longueur, mémoire, extensibilité, logo, fit |

`GREENLIGHT ≥ 88`, `FORT ≥ 78`, `CONDITIONNEL ≥ 62`, `ECARTE < 62`, `REJETE`
(filtre dur). La **fidélité LEGO** est une colonne séparée, utilisée comme
départage — elle ne dilue pas le score.

## Cartographie de la documentation

| Document | Pour qui | Contenu |
|---|---|---|
| [SKILL.md](SKILL.md) | l'agent | le mode d'emploi opératoire, phase par phase |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | développeur | modules, flux, invariants, concurrence, décisions |
| [docs/CLI-REFERENCE.md](docs/CLI-REFERENCE.md) | utilisateur avancé | chaque commande, chaque option, chaque défaut |
| [docs/DATA-MODEL.md](docs/DATA-MODEL.md) | intégrateur | schémas JSON, vocabulaires de statuts, exemples |
| [docs/COOKBOOK.md](docs/COOKBOOK.md) | praticien | 12 recettes prêtes à copier |
| [docs/EXTENDING.md](docs/EXTENDING.md) | mainteneur | ajouter un archétype, une langue, un check, un poids |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | tous | versions, limites connues, feuille de route |
| [references/](references/) | l'agent | le fond métier : scoring, GEO, archétypes, légal, LEGO |
| [agents/](agents/) | l'orchestrateur | prompts des sous-agents + porte de consentement |
| [INSTALL.md](INSTALL.md) | ops | jonction/symlink vers `~/.claude/skills/bom` |

## Principes de conception

1. **Déterministe.** Même corpus + même seed = mêmes noms, même ordre, mêmes
   scores. Aucun appel de modèle dans le moteur.
2. **Zéro dépendance.** stdlib uniquement, y compris l'écriture du `.xlsx`
   (OOXML à la main).
3. **L'incertitude est un statut.** `unknown`, `inconnu`, `?`, `not_checked`
   existent et ne sont jamais arrondis en succès.
4. **Jugement ≠ lecture.** Créer un nom et vérifier un SERP ne méritent pas le
   même modèle : d'où les sous-agents, avec accord explicite de l'utilisateur.
5. **Le rapport se défend.** Chaque point est justifié par une phrase dans
   `evidence` ; chaque rejet a un motif.

## État

Version 1.1.1 — 54 assertions `selftest`, audit réseau réel (RDAP, DNS, GitHub,
npm, PyPI, crates.io, iTunes), exports Markdown/Excel/JSON/CSV. Voir
[docs/CHANGELOG.md](docs/CHANGELOG.md) pour les limites assumées.
