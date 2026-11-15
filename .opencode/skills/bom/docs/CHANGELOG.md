# Changelog

## 1.1.3 — 2026-11-15

### Corrigé — le son ne se lançait pas sur GitHub Pages

Le fichier est un MP3 standard (MPEG-1 Layer III, 44,1 kHz, 192 kb/s) et il
jouait dans Chromium. Le problème venait du déclenchement et du type MIME, pas
du fichier.

- **Type explicite** : `<source type="audio/mpeg">` au lieu d'un `src` nu.
  GitHub Pages sert le fichier en `audio/mp3`, que certains navigateurs
  (Safari en tête) refusent de négocier.
- **Chargement au geste** : `preload="metadata"`, `playsinline`,
  `webkit-playsinline`, et `audio.load()` avant `play()` pour les navigateurs
  qui refusent un premier `play()` sur un élément vide.
- **Bouton visible** : « Écouter le menu secret » sous le burger, avec un état
  « Le son joue » et trois barres animées. Le burger et le mot `miel` restent
  des déclencheurs.
- **Autoplay puis premier clic** : le son est tenté au chargement ; si le
  navigateur le refuse (cas normal pour l'audio non muet), le tout premier clic
  ou la première touche, n'importe où sur la page, lance la lecture. Les
  déclencheurs explicites restent prioritaires pour éviter un double départ.
- **Lien de secours** : si la lecture est bloquée, un lien « Ouvrir le son dans
  le navigateur » apparaît, avec un message explicite. Le son reste accessible
  même sans JavaScript (`<noscript>` à venir côté lecteur natif).
- **Cache** : `styles.css?v=3` et `app.js?v=3` pour forcer le rechargement après
  déploiement.

Vérifié localement : lecture (2,0 s, `readyState 4`, zéro erreur console),
état `aria-pressed`, repli sur source absente, et rendu mobile 390 px sans
débordement.

## 1.1.2 — 2026-11-15

### Compatibilité multi-harnais

Le skill était écrit au format ouvert `SKILL.md` mais documenté et installé
comme un skill Claude/OpenCode. Il est désormais explicitement pris en charge
par **Claude Code, Codex, Antigravity et OpenCode**.

- **`scripts/install_skill.py`** : installe le skill dans les quatre harnais,
  avec les bons chemins, en lien (jonction Windows) ou en copie. Options
  `--harness`, `--project`, `--copy`, `--check`, `--dry-run`, `--home`.
  Vérifie chaque installation en exécutant `bom.py --version` à travers elle.
- **Chemins officiels** : `~/.claude/skills/bom`, `~/.agents/skills/bom`
  (Codex, et `.agents/skills` partagé avec Antigravity), `~/.gemini/config/skills/bom`
  (Antigravity), `~/.config/opencode/skills/bom`.
- **Frontmatter compatible Codex** : description ramenée à moins de 500
  caractères, sur une ligne, sans perdre les déclencheurs.
- **`AGENTS.md`** à la racine : instructions lues automatiquement par Codex et
  Antigravity (emplacement du skill, tests, invariants).
- **`SKILL.md`** : section « Install (any harness) », tableau des chemins et des
  invocations, section « Harness differences » (sous-agents, recherche, modèles,
  shell, chemins). Plus aucune hypothèse `~/.claude` ni `websearch`.
- **`INSTALL.md`** réécrit pour les quatre harnais, avec le dépannage propre à
  chacun.
- Page et README : la liste des harnais et la commande d'installation sont à jour.

### Vérification

- 6 assertions `selftest` supplémentaires (60 au total) : frontmatter, limite
  Codex, présence de l'installateur, installation dans un HOME de test et
  présence de `bom.py` dans les quatre chemins.
- Installation réelle vérifiée sur la machine : Claude (jonction existante),
  Codex (`~/.agents/skills/bom`), Antigravity
  (`~/.gemini/config/skills/bom`), OpenCode
  (`~/.config/opencode/skills/bom`), toutes en `bom 1.1.2`.

## 1.1.1 — 2026-11-15

Optimisation et durcissement, sans changement de schéma.

### Corrigé

- **En-tête CSV compté comme mot-clé** : `mot-cle,volume` n'entre plus dans le
  corpus (148 → 147 sur l'exemple). Détection par noms de colonnes + absence de
  volume, sans jamais confondre un vrai mot-clé.
- **`report --top` tronquait les exports** : le tableau est limité, mais
  `BOM-names.json`, `BOM-names.xlsx` et `BOM-names.csv` contiennent désormais
  tout le classement.
- **Faux positifs du filtre de mots** : `compute` n'est plus bloqué par `pute`,
  `analytics` ne déclenche plus `anal`, `skillhub` plus `kill`. Les mots courts
  (≤ 4 lettres) ne matchent plus qu'en début/fin de nom, avec une liste de mots
  bénins (`asset`, `chief`, `analysis`…).
- **Ancrage GEO du moteur LEGO** : `geo_anchor` utilise les mots réels de
  l'expression traduite, plus les clés internes du lexique ; le pilier SEO
  (intention de recherche) ne sous-note plus les noms LEGO.
- **`score_all`** : un audit dont tous les noms sont rejetés ne produit plus un
  classement de noms invalides.
- **Cache empoisonné par les quotas** : les réponses `401/403/429` ne sont plus
  mises en cache ; un disjoncteur par hôte arrête les appels GitHub après le
  premier refus, au lieu de marteler l'API.
- **RDAP** : parsing `vcardArray` tolérant (plus de risque d'`IndexError` sur une
  réponse atypique), détection DNS tri-état explicite.
- **Traduction** : plus d'adresse e-mail factice envoyée à MyMemory, compteur de
  cache correct.
- **Clustering** : les pluriels sont reconnus (`recettes` → `recette`), les
  marqueurs d'intention multi-mots aussi. Le taux de rattachement lexical passe
  de 51 à 50 mots-clés non classés sur 147 ; le reste est du vocabulaire métier
  absent des lexiques génériques, et reste signalé comme tel.

### Performance

| Opération | Avant | Après |
|---|---:|---:|
| `generate` 30 noms (3 passes) | 0,023 s · 109 942 appels | 0,003 s · 9 967 appels |
| `lego` 24 noms / 576 expressions | 0,160 s | ≈ 0,075 s |
| `score` 30 noms | 0,007 s | 0,003 s |

Mise en cache (`lru_cache`) des fonctions pures de `text.py` (slug, phonétique,
filtres, distance) et calcul unique des faits de collision par candidat.

### Ajouté

- `GITHUB_TOKEN` / `GH_TOKEN` : si présent, l'audit GitHub est authentifié
  (5 000 req/h au lieu de 60) et les quotas ne polluent plus les résultats.
- Règle explicite : un nom **généré** ne peut pas contenir de chiffre
  (`500px` reste auditable via `check`, mais n'est jamais produit par le moteur).
- 10 assertions `selftest` supplémentaires (54 au total) : en-tête CSV, exports
  non tronqués, faux positifs, ancrage LEGO.

## 1.1.0 — 2026-11-15

### Ajouté

- **Moteur LEGO** : contraction d'une expression traduite en 2-3 syllabes
  (`leg godt` → `lego`), 6 règles, réparation phonétique FR/EN, fidélité /100,
  provenance complète (langue, expression, règle, traductions).
- **Traduction multilingue** : lexique seed de 35 concepts × 12 langues +
  MyMemory sans clé, cache 30 jours, romanisation cyrillique/grec, refus explicite
  des écritures non romanisables (ar, hi, zh, ja, ko).
- **Sous-agents** : `dispatch` (paquets de tâches), `merge` (fusion des mesures),
  `score --research` (les mesures remplacent les extrapolations), prompts dans
  `agents/`, porte de consentement obligatoire.
- **Exports** : `BOM-names.xlsx` (OOXML écrit sans dépendance, 3 onglets, en-tête
  figé, filtre), `BOM-names.json` (`bom.names/v1`), `export` pour régénérer.
- **Documentation avancée** : `README.md`, `docs/ARCHITECTURE.md`,
  `docs/CLI-REFERENCE.md`, `docs/DATA-MODEL.md`, `docs/COOKBOOK.md`,
  `docs/EXTENDING.md`, `references/lego-mechanic.md`.
- Colonne `Fidélité` dans le rapport et l'Excel, `·m` pour les noms mesurés en
  Phase 3, rejet automatique sur marque bloquée.

### Modifié

- `report` accepte `--top` sans tronquer les exports.
- Typographie française du livrable (accents) et libellés de registres.
- `score_all` trie par total puis fidélité.
- Seuils de palier recalibrés : 88 / 78 / 62.
- Filtre de marque renforcé (correspondance de sous-chaîne pour les marques
  distinctives : `excelboard`, `legobase`…).

### Corrigé

- Warnings de disponibilité hors ligne désormais explicites (`provisional`).
- Familles de contractions quasi identiques fusionnées (`bico`/`bieco`/`biecou`).
- Actions erronées du type « réserver un dépôt GitHub ».

## 1.0.0 — 2026-11-15

- Pipeline 5 phases : clustering (5 classes), 30 candidats sur 5 archétypes,
  audit technique, score 100 points (4 × 25), rapport exécutif.
- Audit réseau : RDAP + DNS (`.com`, `.app`, `.ai`, `.io`, `.fr`), GitHub
  compte/repos, npm, PyPI, crates.io, iTunes Search.
- Filtrage dur : mots interdits, marques connues, noms communs, prénoms,
  prononçabilité, amas consonantiques.
- Score SEO (virginité SERP, rankabilité, intention, longue traîne, snippet) et
  GEO (collision d'entités, ancrage, hallucination, stabilité) + commercial.
- Batterie GEO de 6 prompts, packs SERP et marques prêts à exécuter.
- `selftest` hors ligne, rapports Markdown/CSV, 5 dossiers individuels.

## Limites connues

| Limite | Impact | Contournement |
|---|---|---|
| Accord grammatical approximatif en FR/ES/IT | expressions parfois bancales (`carte clair`) | afficher l'expression source ; un locuteur corrige le libellé, pas le nom |
| Écritures non latines exclues du LEGO | pas de nom dérivé du chinois, japonais, arabe, hindi, coréen | projet séparé avec locuteur natif |
| Pas d'API SERP | virginité estimée par collisions, pas mesurée | `dispatch` + sous-agent de recherche |
| Pas d'API marques | pas de recherche INPI/EUIPO/USPTO automatisée | Phase 3 humaine, classes 9 et 42 |
| Google Play / Product Hunt sans API | vérification manuelle | liens fournis dans le pack |
| MyMemory rate-limité | traductions partielles sur gros volumes | lexique seed, cache, `--translator offline` |
| RDAP non contractuel | un domaine « libre » peut être réservé | confirmer chez le registrar avant paiement |
| Fichiers uniquement, pas de base | pas d'historique inter-runs | archiver `runs/<projet>` |

## Feuille de route

- Export `.docx` du rapport (OOXML, même approche que le `.xlsx`).
- Historique de runs et comparaison de deux campagnes.
- Fournisseur de traduction optionnel (DeepL) derrière le même `Translator`.
- Recherche de marques via une source publique documentée (TMview export).
- Détection de similarité phonétique entre candidats (Soundex FR/EN).
- Mode « brief only » : générer le corpus depuis le brief sans keywords.

Rien de tout cela n'est promis : la feuille de route indique la direction, pas un
engagement.
