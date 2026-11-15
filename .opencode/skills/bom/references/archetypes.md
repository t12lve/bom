# The five archetypes

Names fail for two reasons: nobody can spell them, or nobody can remember why
they exist. Each archetype trades one for the other. BOM generates six of each so
the client can see the trade-off instead of arguing about taste.

| Archetype | Learning cost | Ownability | GEO transparency | Best when |
|---|---|---|---|---|
| Descriptif hybride | none | low-medium | high | category is crowded and buyers search literally |
| Mot-valise / Blend | low | medium | medium-high | two concepts must coexist (margin + tracking) |
| Metaphorique | medium | medium | medium | the product is complex, the promise is simple |
| Neologisme <= 7 | high | very high | none | budget exists to teach the name |
| Hybride GEO | low | medium | very high | AI discovery is the main acquisition channel |

---

## 1. Descriptif hybride

**Construction** : `root` (3-7 letters, taken from the corpus) + one product
morpheme.

Banks (in `lexicons.py`): `-base -kit -lab -deck -flow -rank -signal -scope
-pilot -bridge -nest -forge -loop -peak -craft -wise -ly -ify -io -ai`.

```
prix    + rank   -> prixrank
marge   + deck   -> margedeck
recette + deck   -> recettedeck
fourni  + meter  -> fournimeter
```

**Rules**

- The root must come from the corpus, not from your imagination. If it has no
  search volume, the compound is just a longer neologism.
- 13 characters maximum. Beyond that the domain label gets hyphenated in speech.
- Avoid `-ly`, `-ify`, `-ai` unless the client explicitly wants the 2021 SaaS
  look. They are free, and that is exactly the problem.
- Never `root + root` without a morpheme (`restaurantcarte`) — it reads as a
  keyword, not a brand, and trademark offices treat it as descriptive.

---

## 2. Mot-valise / Blend

**Construction** : two corpus roots welded at a pronounceable seam — longest
shared letters first, otherwise a head/tail cut that leaves a legal French or
English syllable at the junction.

```
cuisine + cost  -> cuisicost      (head 'cuisi' + tail 'cost')
brasserie + map -> brassemap
food + dose     -> foodose        (overlap on 'do')
```

**Rules**

- The seam must be V-C or C-V, or a legal cluster (`tr`, `br`, `pl`…). A seam
  like `rt` + `st` produces a stutter nobody can say twice.
- Both clusters must remain visible. If the second half is 2 letters, it is not
  a blend, it is a truncation.
- Reject anything that lands on an existing common word (`reste`, `cuite`,
  `salade`) — you inherit its meaning and lose the trademark.
- Test aloud in French *and* English before keeping it.

---

## 3. Metaphorique

**Construction** : a concrete image + one decodability morpheme. The image gives
memory, the morpheme gives the model a chance.

```
beacon + path  -> beaconpath
forge  + works -> forgeworks
hive   + deck  -> hivedeck
```

**Rules**

- One image only. `anchorprismforge` is a mood board, not a name.
- The morpheme is what keeps it out of the pure-metaphor graveyard. `Beacon`
  alone is taken everywhere and means nothing specific; `beaconpath` is ownable.
- Choose the image by *mechanism*, not by vibe: `loom` for weaving data into a
  product, `compass` for decision support, `forge` for building, `hive` for
  collective intelligence. If you cannot explain the link in one sentence, the
  client's customers will not either.
- Metaphors age well but translate badly. Check the image in the second market
  before committing (`tide` works in EN, `marée` is clumsy in a brand).

---

## 4. Neologisme <= 7 lettres

**Construction** : 2-3 open syllables, legal onsets, no coda except a single
`n/r/l/s/x` in two-syllable forms.

```
fo + rix        -> foorix
re + gou + zi   -> regouzi
na + grir       -> nagrir
```

**Rules**

- Must be readable on first sight by a 45-year-old French SMB owner. If they
  hesitate, it fails, however elegant it looks on a slide.
- No accidental meaning in FR or EN. The generator screens profanity, but you
  must also screen *derision*: `bite`, `cul`, `con`, `pet`, `queue`, `zizi` and
  their English cousins.
- Avoid three vowels in a row, doubled letters, and final clusters.
- The whole point is a free SERP and a clear trademark. Verify both before
  falling in love — a short invented name is also the one most likely to be
  squatted on `.com` by a domainer.

---

## 5. Hybride GEO

**Construction** : sector morpheme + mechanics morpheme, both decodable without
context. Built to be understood by a model that has never seen the brand.

```
menu  + scope -> menuscope
plat  + signal -> platsignal
marge + deck  -> margedeck
```

**Rules**

- One half says *what domain*, the other says *how it works*. Never two domain
  words (no mechanics) or two mechanics words (no domain).
- Prefer words the buyer actually types. The generator ranks roots that appear in
  the brief first, because those are the words a person puts into ChatGPT.
- Watch the second market: a French sector word (`prix`, `marge`, `plat`) is
  opaque to an English buyer. If the plan is FR → UK/DE, either pick an
  international root or accept a two-name strategy.
- This archetype scores highest on GEO and lowest on distinctiveness. It is the
  right choice for a search-driven acquisition, the wrong one for a design-led
  brand.

---

## Anti-patterns (all of them are hard-filtered by the engine)

| Pattern | Example | Why it dies |
|---|---|---|
| Bare dictionary noun | `restaurant`, `marge` | unregistrable, unrankable, GEO-invisible |
| Known brand + suffix | `excelboard` | trademark collision, model prior |
| First name | `lucas`, `jade` | person entity wins the SERP |
| 4+ consonant run | `krxtz` | nobody can say it |
| Triple letter | `foorrix` | typo magnet |
| Vowel soup | `aieou` | unreadable in both languages |
| `-ai` suffix on a French word | `cuisineai` | reads as "cuisine AI", dated and generic |

---

## Editing pass (do this after `generate`)

1. Read the 30 names aloud, FR then EN. Cut anything you stumble on.
2. Delete duplicates in sound, not just in spelling (`prixrank` / `prixrankly`).
3. Keep at most 2 names ending in the same morpheme.
4. Replace weak seeds by hand; keep the rationale format.
5. Verify each kept name against the brief's tone in one sentence. If you cannot
   write that sentence, the name is wrong.
