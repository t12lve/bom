# Étendre BOM

Le moteur est volontairement petit et sans dépendance. Chaque extension suit le
même rituel : toucher **un** module de données, **un** module de logique, puis
ajouter une assertion dans `selftest.py`. Une extension sans test est une
régression qui attend son heure.

Avant de modifier : `python scripts/bom.py selftest` doit afficher `PASS: 44`.

---

## 1. Ajouter un archétype de nom

Fichiers : `scripts/bomlib/generate.py`, éventuellement `lexicons.py`.

1. Déclarer le libellé dans `ARCHETYPES` :

```python
ARCHETYPES["compound"] = "Composé savant"
```

2. Écrire un constructeur qui respecte la signature des autres :

```python
def build_compound(roots, taken, limit, leads):
    out = []
    for root in roots[:12]:
        ...
        ok, reason = _accept(name, taken, max_len=13)
        if not ok:
            continue
        taken.add(name)
        leads.take(root["root"])
        out.append(_entry(name, "compound", "…", [root["root"]], [root["dominant_cluster"]], []))
        if len(out) >= limit:
            break
    return out
```

3. L'appeler dans `generate()` et dans `buckets`, avec le même quota
   (`per_archetype`).
4. Vérifier que `source` / `rationale` restent renseignés : le rapport les cite.

Pièges : `_accept` est le **filtre unique** (mots interdits, marques, dictionnaire,
prononçabilité). Ne le contournez pas ; si un nom doit passer malgré un drapeau,
ajoutez un `soft` au lieu d'un `hard`.

## 2. Ajouter une règle de contraction LEGO

Fichier : `scripts/bomlib/lego.py`.

1. Ajouter l'entrée dans `RULES` (le libellé apparaît dans le rapport).
2. Ajouter une branche dans `contract()` ; elle reçoit des mots déjà nettoyés.
3. Retourner `None` si la règle ne s'applique pas (le moteur essaie la suivante).
4. Tester la forme canonique dans `selftest.py` :

```python
check.ok(lego_mod.contract_phrase("leg godt", "lego2") == "lego", "leg godt -> lego")
```

Rappel : `repair()` s'applique après la règle. Une règle qui produit des amas de
consonnes n'est pas fausse, elle sera simplement réparée — vérifiez le résultat
final, pas la sortie brute.

## 3. Ajouter une langue

Fichier : `scripts/bomlib/translate.py`.

1. Ajouter l'entrée dans `LANGUAGES` (`code`, `label`, `latin`, `reach`,
   éventuellement `translit`). `latin: False` = listée mais ignorée.
2. Ajouter la langue aux concepts du lexique : `CONCEPTS["price"]["xx"] = "..."`.
   Ne traduisez que ce dont vous êtes sûr ; le reste passe par l'API.
3. Déclarer l'ordre des mots dans `PHRASE_ORDERS` (`"nq"` = nom puis
   qualificatif, `"qn"` = l'inverse) et, si adjectif antéposé, dans `ADJ_FIRST`.
4. Si l'écriture n'est pas latine mais romanisable, fournir une table de
   translittération (voir `CYRILLIC`, `GREEK`). Sinon, laisser `latin: False`.

Test : `resolve_languages("fr,xx", "fr")` doit renvoyer la langue, et
`translator.translate("price", "xx")` doit produire un `roman` non vide.

## 4. Ajouter un concept au lexique

Même fichier. Un concept est une clé anglaise stable, avec des traductions
courtes (un mot si possible) :

```python
"receipt": {"fr": "recu", "en": "receipt", "es": "recibo", "de": "beleg",
            "it": "ricevuta", "pt": "recibo", "nl": "bon", "da": "kvittering",
            "sv": "kvitto", "pl": "paragon", "tr": "fis", "ru": "чек"},
```

Évitez les homographes ambigus et les mots qui sont déjà des marques. Vérifiez
qu'aucun concept ajouté ne casse le filtre : `bom.py selftest` doit rester vert.

## 5. Ajouter un registre de code

Fichiers : `scripts/bomlib/lexicons.py` (libellé) et `audit.py` (requête).

1. `REGISTRIES` : ajouter `{"id": "packagist", "label": "Packagist"}`.
2. `_reg()` dans `audit.py` : ajouter le libellé au dictionnaire local.
3. Écrire le check dans `check_registries()` :

```python
body = net.fetch(f"https://repo.packagist.org/p2/{name}.json")
if body.get("http") == 404:
    checks.append(_reg("packagist", "libre", "aucun paquet Composer"))
elif body.get("http") == 200:
    checks.append(_reg("packagist", "pris", "paquet Composer existant"))
else:
    checks.append(_reg("packagist", "inconnu", _net_note(body)))
```

Règle d'or : `404` → libre, `200` → pris, tout le reste → `inconnu`. Jamais
l'inverse. Le cache et le pacing sont déjà gérés par `Net`.

## 6. Changer les poids du score

Fichier : `scripts/bomlib/score.py`, dictionnaire `PILLARS`.

```python
"technique": {
    "label": "Disponibilite technique & handles",
    "max": 25,
    "parts": [("com", "Domaine .com", 9), ("tlds", "...", 3), ...],
}
```

Contraintes :

- la somme des `parts` doit égaler `max` (25) ;
- les fonctions `score_*` lisent `maxes[part]`, donc un poids modifié se propage
  aux calculs — vérifiez chaque `_clamp` ;
- mettez à jour `references/scoring-rubric.md` et la ligne correspondante dans
  `docs/DATA-MODEL.md` ;
- `selftest` vérifie `total == somme des piliers` : un poids mal ajusté casse le
  test avant de casser un rapport.

Pour un besoin client ponctuel (SEO ×2), ne modifiez pas le code : documentez la
pondération dans le rapport et recalculez à côté. Le moteur reste la référence.

## 7. Ajouter une colonne au rapport et à l'Excel

1. `export.ranking_rows()` : ajouter la clé calculée.
2. `export.build_sheets()` : ajouter la colonne (`key`, `label`, `width`,
   `kind` ∈ `text|int|float1|float2`).
3. `report.comparative_table()` : ajouter l'en-tête et la cellule, en gardant
   l'alignement du séparateur Markdown.
4. Si la colonne est conditionnelle (comme `Fidélité`), la masquer quand la
   valeur est absente plutôt que d'afficher un tiret partout.

## 8. Ajouter un rôle de sous-agent

Fichiers : `scripts/bomlib/research.py`, `agents/`, `SKILL.md`.

1. `MODEL_TIERS` : ajouter le tier si le rôle ne rentre ni dans `creation` ni
   dans `research` (rare : deux tiers suffisent).
2. Écrire le générateur de paquets (`build_*_packets`) avec un
   `output_schema` fermé et `requires_user_approval: True`.
3. Créer `agents/<role>.md` : rôle, entrée, tâche, schéma, règles absolues,
   auto-contrôle.
4. Ajouter le rôle au tableau d'orchestration de `SKILL.md` et à
   `agents/README.md`.
5. Si le rôle produit des mesures, apprendre à `merge_results()` à les
   normaliser (verdicts fermés) et à `score.py` à les consommer.

## 9. Versionner

- `scripts/bomlib/__init__.py` : `__version__`.
- `docs/CHANGELOG.md` : entrée datée, ajouts, corrections, limites.
- `SKILL.md` : si la surface CLI change, mettre à jour les commandes citées.
- `selftest.py` : toute nouvelle garantie mérite une assertion.

Une version qui change un schéma JSON doit le signaler : les schémas versionnés
(`bom.names/v1`, `bom.research/v1`) portent leur numéro dans le document, pas
dans le nom de fichier. Un changement cassant passe en `/v2` avec une note de
migration.

## 10. Ce qu'il ne faut pas faire

- Ajouter une dépendance Python pour « faire plus simple ». Le stdlib est une
  fonctionnalité, pas un accident.
- Simuler un résultat quand le réseau échoue. `unknown` est une réponse.
- Élargir une allowlist de secrets ou appeler une API payante sans accord.
- Modifier `assets/` pour faire passer un test : le corpus d'exemple est la
  référence de non-régression.
