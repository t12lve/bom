# Cookbook — 12 recettes

Toutes les commandes supposent `cd <skill>` et un shell POSIX ; sous PowerShell,
remplacez `\` par `` ` `` et `python3` par `python`.

## 1. Du brief au rapport, en 3 commandes

```bash
python scripts/bom.py intake  --keywords corpus.csv --brief brief.md --out work/clusters.json
python scripts/bom.py generate --clusters work/clusters.json --count 30 --out work/candidates.json
python scripts/bom.py run --keywords corpus.csv --brief brief.md --out-dir runs/acme
```

La troisième refait tout : utilisez-la seule si vous n'avez pas besoin d'éditer
les candidats entre les étapes.

## 2. Comparer les deux moteurs dans un seul classement

```bash
python scripts/bom.py run --engine archetypes --keywords corpus.csv --brief brief.md \
  --out-dir runs/mix-arch --offline
python scripts/bom.py run --engine lego --keywords corpus.csv --brief brief.md \
  --out-dir runs/mix-lego --offline --langs fr,en,es,de,da
```

```python
# fusion des candidats, sans doublon de nom
import json, pathlib
arch = json.loads(pathlib.Path("runs/mix-arch/work/candidates.json").read_text(encoding="utf-8"))
lego = json.loads(pathlib.Path("runs/mix-lego/work/candidates.json").read_text(encoding="utf-8"))
seen = {c["name"] for c in arch["candidates"]}
cands = arch["candidates"] + [c for c in lego["candidates"] if c["name"] not in seen]
dist = {}
for c in cands:
    dist[c["archetype"]] = dist.get(c["archetype"], 0) + 1
out = {
    "meta": {**arch["meta"], "engine": "mixed", "count": len(cands), "distribution": dist},
    "archetypes": {**arch["archetypes"], **lego["archetypes"]},
    "candidates": cands,
}
pathlib.Path("runs/mix").mkdir(parents=True, exist_ok=True)
pathlib.Path("runs/mix/candidates.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
```

```bash
python scripts/bom.py audit --candidates runs/mix/candidates.json --out runs/mix/audit.json
python scripts/bom.py score --audit runs/mix/audit.json --clusters work/clusters.json --out runs/mix/scores.json
python scripts/bom.py report --scores runs/mix/scores.json --audit runs/mix/audit.json \
  --clusters work/clusters.json --candidates runs/mix/candidates.json --out runs/mix/report
```

## 3. Arbitrer une shortlist en réunion

```bash
python scripts/bom.py check --names "hivelens,prixrank,menuscope" --tlds com,fr,app
```

Pas de corpus, pas de brief : audit + score en une commande, tableau en sortie.
Ajoutez `--offline` si le réseau de la salle est filtré.

## 4. Mode avion (réseau interdit)

```bash
python scripts/bom.py run --keywords corpus.csv --brief brief.md --out-dir runs/off --offline
```

Tout fonctionne sauf les vérifications réseau. Conséquences à annoncer :
domaines `unknown`, scores `provisoire`, SEO/GEO extrapolés. Le rapport le dit
explicitement.

## 5. Accélérer un audit

```bash
python scripts/bom.py audit --candidates work/candidates.json \
  --tlds com,fr --quick --workers 8 --cache-dir runs/acme/.cache
```

- `--quick` : domaines seulement (pas de GitHub/npm/PyPI).
- `--tlds com,fr` : divise le nombre de requêtes RDAP par 2,5.
- `--cache-dir` : partagé entre runs, TTL 7 jours.
- `--workers 8` : au-delà, les hôtes commencent à répondre 429.

## 6. Phase 3 mesurée, avec sous-agents

```bash
# 1. paquets (aucun modèle appelé)
python scripts/bom.py dispatch --phase 3 --scores runs/acme/work/scores.json \
  --top 10 --batch 3 --out runs/acme/packets
```

Demandez l'accord utilisateur, puis lancez un sous-agent `research` par paquet
(`agents/research-analyst.md`), en parallèle. Déposez les JSON dans
`runs/acme/packets/results/`.

```bash
python scripts/bom.py merge --inputs runs/acme/packets/results/*.json \
  --out runs/acme/work/research.json
python scripts/bom.py score --audit runs/acme/work/audit.json \
  --clusters runs/acme/work/clusters.json --research runs/acme/work/research.json \
  --out runs/acme/work/scores.json
python scripts/bom.py report --scores runs/acme/work/scores.json \
  --audit runs/acme/work/audit.json --clusters runs/acme/work/clusters.json \
  --candidates runs/acme/work/candidates.json --out runs/acme/report
```

Les noms vérifiés portent `·m` dans le tableau ; une marque identique passe en
`REJETE`.

## 7. Re-exporter après une retouche manuelle

Vous corrigez un score, une note, un domaine dans `scores.json` :

```bash
python scripts/bom.py export --scores runs/acme/work/scores.json \
  --audit runs/acme/work/audit.json --clusters runs/acme/work/clusters.json \
  --candidates runs/acme/work/candidates.json --out runs/acme/report
```

Régénère Markdown, Excel, JSON et CSV sans refaire l'audit.

## 8. Marché anglophone (ou germanophone)

```bash
python scripts/bom.py run --engine lego --keywords corpus_en.csv --brief brief_en.md \
  --source-lang en --langs en,de,nl,sv,da --out-dir runs/eu
```

`--source-lang` change la langue du corpus (donc les traductions de départ) ;
`--langs` restreint les langues cibles. Le lexique seed couvre en, de, nl, sv,
da, fr, es, it, pt, pl, tr, ru.

## 9. Uniquement la disponibilité des domaines

```bash
python scripts/bom.py audit --candidates work/candidates.json --tlds com,fr --quick
jq '.candidates[] | {name, com: (.domains[] | select(.tld=="com") | .status)}' work/audit.json
```

(`jq` optionnel ; le fichier reste lisible à l'œil.)

## 10. Intégration CI

```yaml
# .github/workflows/bom.yml
name: bom
on: [push]
jobs:
  selftest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: python .opencode/skills/bom/scripts/bom.py selftest
```

Le code de sortie est 0 si les 60 assertions passent, 1 sinon. Aucun réseau
n'est requis : la CI ne dépend d'aucun service externe.

## 11. Deux noms, une décision

```bash
python scripts/bom.py check --names "prixrank,margedeck" --tlds com,app,fr
```

Puis comparer les piliers : un écart < 3 points est un exécution ex aequo.
Départage documenté : `.com` disponible, puis longueur, puis test du téléphone.

## 12. Archiver un run livré

```bash
cat runs/acme/state.json
tar -czf acme-bom-$(date +%F).tgz runs/acme
```

`state.json` contient la carte des fichiers, le mode (`network`/`static-only`),
le moteur, et les prochaines étapes. Conservez `audit.json` : c'est lui qui
permet de rejouer le score à l'identique sans réseau.
