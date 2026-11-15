# Burger au Miel

**BOM — Brand, Optimization & Market-readiness.**  
Un skill de naming commercial : d'un corpus de 100 à 500+ mots-clés, il produit
des noms d'applications, les vérifie, les note sur 100 en SEO et en GEO, et rend
un rapport qui dit quoi acheter.

[La page](https://t12lve.github.io/bom/) · [Le mode d'emploi](.opencode/skills/bom/SKILL.md) · [La documentation](.opencode/skills/bom/docs/) · [Le skill](.opencode/skills/bom/)

> Le vrai nom complet, c'est *Burger au Miel*. Ne le dites pas au client.

## Ce qu'il fait

| Phase | Sortie |
|---|---|
| 1. Ingestion et clustering | 5 familles sémantiques, racines classées par volume et intention |
| 2. Génération | 30 noms sur 5 archétypes, ou contraction LEGO multilingue |
| 3. Audit | domaines (RDAP + DNS), GitHub, npm, PyPI, crates.io, App Store |
| 4. Score | 100 points : technique 25, SEO 25, GEO 25, commerce 25 |
| 5. Rapport | Markdown, Excel, JSON, CSV, dossiers individuels |

Chaque point est justifié par une phrase, chaque rejet a un motif, chaque
incertitude reste visible (`unknown`, `inconnu`, `not_checked`).

## La mécanique LEGO

`leg godt` (« jouer bien », danois) donne **LE + GO**, donc LEGO. BOM
généralise : le mot-clé est traduit dans les langues les plus utilisées, associé
à un qualificatif, puis contracté en deux ou trois syllabes. Six règles, une
réparation phonétique FR/EN, une fidélité sur 100, et la provenance complète
(langue, expression, règle, traductions).

```bash
python scripts/bom.py run --engine lego \
  --keywords assets/keywords.example.csv --brief assets/brief.example.md \
  --langs fr,en,es,de,da --out-dir runs/lego
```

## Démarrage

```bash
git clone https://github.com/t12lve/bom.git
cp -r bom/.opencode/skills/bom ~/.claude/skills/
python ~/.claude/skills/bom/scripts/bom.py selftest
```

Sous Windows, `scripts/install_claude_link.ps1` crée une jonction, sans droits
administrateur. Python 3.9+, aucune dépendance, aucune clé API.

```bash
python .opencode/skills/bom/scripts/bom.py run \
  --keywords .opencode/skills/bom/assets/keywords.example.csv \
  --brief .opencode/skills/bom/assets/brief.example.md \
  --out-dir runs/demo
```

## Le score

| Pilier | Points | Ce qu'il mesure |
|---|---:|---|
| Disponibilité technique | 25 | `.com`, TLD secondaires, registres, handles, fautes de frappe |
| SEO classique | 25 | virginité SERP, facilité à ranker, intention, longue traîne |
| GEO / moteurs IA | 25 | collision d'entités, ancrage sémantique, hallucination, stabilité |
| Commercial | 25 | téléphone, FR/EN, longueur, mémoire, extensibilité |

`GREENLIGHT ≥ 88`, `FORT ≥ 78`, `CONDITIONNEL ≥ 62`, `REJETE` pour les noms
filtrés. La fidélité LEGO est une colonne séparée, utilisée comme départage.

## Le dépôt

```
.opencode/skills/bom/   le skill (SKILL.md, scripts, références, agents, docs)
site/                   la page burger, servie par GitHub Pages
```

La documentation avancée est dans [`.opencode/skills/bom/docs/`](.opencode/skills/bom/docs/).

## Le menu secret

Sur [la page](https://t12lve.github.io/bom/), cliquez sur le burger. Ou tapez
`miel` au clavier. Le son est inclus dans `site/assets/` (fichier fourni par
l'auteur, 2020).

## Licence

MIT. Voir [LICENSE](LICENSE).
