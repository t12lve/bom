"""Phase 1b - candidate generation across the five BOM archetypes.

The generator is deliberately deterministic (seeded) and explainable: every
candidate carries the roots and clusters it came from, so the executive
report can justify why it exists. It produces *seed material*: the agent
refines the shortlist in Phase 3-4, it never ships names blind.

Quality gates applied to every candidate before it is emitted:
  * ASCII slug, 4-14 chars (7 for the short neologism archetype)
  * pronounceable, no 3+ consonant pile-up, no triple letter
  * no profanity, no known brand, no bare dictionary noun
  * no two candidates sharing the same leading morpheme more than twice
"""

from __future__ import annotations

import random
import re

from . import lexicons as lx
from . import text as tx

ARCHETYPES: dict[str, str] = {
    "descriptive": "Descriptif hybride",
    "blend": "Mot-valise / Blend",
    "metaphor": "Metaphorique",
    "neologism": "Neologisme court (<= 7 lettres)",
    "geo": "Hybride sémantique optimise GEO",
}

FALLBACK_ROOTS: tuple[str, ...] = (
    "hive", "scan", "rank", "lens", "flow", "menu", "recipe", "honey",
    "signal", "atlas", "pilot", "nest",
)

# Neo-classical morphemes used to rescue the blend archetype when two roots
# do not merge cleanly. They read as "professional product" in FR and EN.
NEO_SUFFIXES: tuple[str, ...] = (
    "metry", "scope", "logic", "nomix", "vore", "labs", "trix", "dex",
    "nova", "vista", "pilot", "costo", "gastro", "culin",
)

METHOD_WORDS: tuple[str, ...] = (
    "scan", "rank", "lens", "meter", "signal", "deck", "pilot", "board",
    "list", "map", "track", "watch", "guard", "radar", "scope",
)


def _pool(document: dict) -> list[dict]:
    roots = [r for r in document.get("roots", []) if tx.is_ascii_slug(r["root"])]
    if not roots:
        return [
            {"root": r, "dominant_cluster": "tech", "score": 1.0, "freq": 1}
            for r in FALLBACK_ROOTS
        ]
    return roots


def _join(left: str, right: str) -> str:
    if left and right and left[-1] == right[0]:
        right = right[1:]
    return left + right


def _head(word: str, maximum: int = 6) -> str:
    """Longest prefix ending on a vowel group (a pronounceable cut)."""
    matches = list(re.finditer(r"[aeiouy]+", word))
    if not matches:
        return word[:maximum]
    for match in reversed(matches):
        if match.end() <= maximum and match.end() >= 2:
            return word[: match.end()]
    return word[:maximum]


def _tail(word: str, minimum: int = 3) -> str:
    """Shortest suffix starting just before the last vowel group."""
    matches = list(re.finditer(r"[aeiouy]+", word))
    if not matches:
        return word[-minimum:]
    last = matches[-1]
    start = max(0, last.start() - 1)
    if len(word) - start < minimum:
        start = max(0, len(word) - minimum)
    return word[start:]


def _seam_ok(left: str, right: str) -> bool:
    seam = (left[-1] if left else "") + (right[0] if right else "")
    if not seam:
        return False
    if len(seam) < 2:
        return True
    vowel = set("aeiouy")
    a, b = seam[0], seam[1]
    if a in vowel or b in vowel:
        return True
    return seam in {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr", "vr"}


def _accept(name: str, taken: set[str], max_len: int = 14) -> tuple[bool, str]:
    slug = tx.slugify(name)
    if re.search(r"[^a-z]", slug):
        return False, "caracteres non alphabetiques (chiffres refuses dans un nom genere)"
    if not (4 <= len(slug) <= max_len):
        return False, "longueur hors bornes"
    if slug in taken:
        return False, "doublon"
    hard, _soft = tx.bad_word_hits(slug)
    if hard:
        return False, f"mot interdit: {','.join(hard)}"
    if tx.has_generic_word(slug) or slug in lx.DICTIONARY_NOUNS:
        return False, "mot de dictionnaire"
    if tx.brand_collision(slug):
        return False, "collision de marque connue"
    if tx.pronounceability(slug) < 58:
        return False, "prononcabilite insuffisante"
    if tx.max_consonant_run(slug) > 3:
        return False, "amas consonantique"
    if re.search(r"(.)\1\1", slug):
        return False, "lettre triplee"
    return True, ""


def _entry(
    name: str,
    archetype: str,
    rationale: str,
    roots: list[str],
    clusters: list[str],
    geo_anchor: list[str],
    extra_flags: dict | None = None,
) -> dict:
    slug = tx.slugify(name)
    _hard, soft = tx.bad_word_hits(slug)
    flags = {
        "soft_bad": soft,
        "first_name": tx.is_common_first_name(slug),
        "cliche_suffix": any(
            slug.endswith(s["s"]) and s["cliche"] == "high" for s in lx.SUFFIXES
        ),
        "dictionary_noun": slug in lx.DICTIONARY_NOUNS,
    }
    if extra_flags:
        flags.update(extra_flags)
    generation = (
        tx.pronounceability(slug) * 0.55
        + (18 if geo_anchor else 0)
        + (8 if not flags["cliche_suffix"] else 0)
        + (6 if len(slug) <= 9 else 0)
        + (4 if not soft else -12)
    )
    return {
        "name": slug,
        "display": tx.display_form(slug),
        "archetype": archetype,
        "archetype_label": ARCHETYPES[archetype],
        "rationale": rationale,
        "roots": roots,
        "clusters": sorted(set(clusters)),
        "geo_anchor": geo_anchor[:2],
        "length": len(slug),
        "syllables": tx.syllable_count(slug),
        "pronounceability": tx.pronounceability(slug),
        "phone_penalty": tx.phone_test_penalty(slug),
        "flags": flags,
        "generation_score": round(generation, 2),
    }


def accept_name(name: str, taken: set[str], max_len: int = 14) -> tuple[bool, str]:
    """Public wrapper used by other archetype engines (LEGO)."""
    return _accept(name, taken, max_len)


class _Leads:
    """Caps how often the same leading morpheme can carry a candidate."""

    def __init__(self, cap: int = 2):
        self.cap = cap
        self.count: dict[str, int] = {}

    def allow(self, lead: str) -> bool:
        return self.count.get(lead, 0) < self.cap

    def take(self, lead: str) -> None:
        self.count[lead] = self.count.get(lead, 0) + 1


# --------------------------------------------------------------------------
# Archetype builders
# --------------------------------------------------------------------------


def build_descriptive(
    roots: list[dict], taken: set[str], limit: int, leads: _Leads
) -> list[dict]:
    """Root (already meaningful) + product morpheme: zero learning cost."""
    out: list[dict] = []
    suffixes = sorted(lx.SUFFIXES, key=lambda s: s["cliche"])
    for round_index in range(3):
        for index, root in enumerate(roots[:14]):
            if len(out) >= limit:
                return out
            base = root["root"]
            if not (3 <= len(base) <= 7):
                continue
            if not leads.allow(base):
                continue
            suffix = suffixes[(index + round_index * 7) % len(suffixes)]["s"]
            name = _join(base, suffix)
            ok, _ = _accept(name, taken, max_len=13)
            if not ok:
                continue
            taken.add(name)
            leads.take(base)
            meta = next(s for s in suffixes if s["s"] == suffix)
            out.append(
                _entry(
                    name,
                    "descriptive",
                    f"'{base}' (racine {root['dominant_cluster']}) + '-{suffix}' ({meta['tags']}) : "
                    "categorie lisible sans baseline, aucun coût d'apprentissage.",
                    [base],
                    [root["dominant_cluster"]],
                    [base, suffix],
                )
            )
    return out


def build_blend(
    roots: list[dict], taken: set[str], limit: int, leads: _Leads
) -> list[dict]:
    """Two roots welded at a pronounceable seam, overlap first."""
    out: list[dict] = []
    ordered = sorted(roots, key=lambda r: -r["score"])
    for index, left in enumerate(ordered[:16]):
        if len(out) >= limit:
            return out
        for offset in range(2, 8):
            if len(out) >= limit:
                return out
            right = ordered[(index + offset) % len(ordered)]
            if right["root"] == left["root"]:
                continue
            if not (leads.allow(left["root"]) and leads.allow(right["root"])):
                continue
            overlap = tx.longest_overlap(left["root"], right["root"], minimum=2)
            if overlap >= 2:
                name = left["root"] + right["root"][overlap:]
                how = f"fusion sur {overlap} lettres communes"
            else:
                head = _head(left["root"], 5)
                tail = _tail(right["root"], 3)
                name = _join(head, tail)
                how = f"couture prononcable ('{head}' + '{tail}')"
            if not _seam_ok(head if overlap < 2 else left["root"], right["root"]):
                continue
            ok, _ = _accept(name, taken, max_len=12)
            if not ok:
                continue
            taken.add(name)
            leads.take(left["root"])
            leads.take(right["root"])
            clusters = [left["dominant_cluster"], right["dominant_cluster"]]
            out.append(
                _entry(
                    name,
                    "blend",
                    f"{how} de '{left['root']}' et '{right['root']}' : deux signaux de categorie "
                    f"({lx.CLUSTER_LABELS[clusters[0]].lower()} + {lx.CLUSTER_LABELS[clusters[1]].lower()}).",
                    [left["root"], right["root"]],
                    clusters,
                    [left["root"], right["root"]],
                )
            )
            break
    return out


def build_metaphor(
    roots: list[dict], taken: set[str], limit: int, leads: _Leads
) -> list[dict]:
    """A concrete image plus one decodability morpheme (GEO-safe metaphor)."""
    out: list[dict] = []
    morphemes = list(lx.CATEGORY_MORPHEMES)
    for index, seed in enumerate(lx.METAPHOR_SEEDS):
        if len(out) >= limit:
            return out
        root = roots[index % len(roots)]
        candidates = [
            _join(seed["s"], morphemes[index % len(morphemes)]),
            _join(seed["s"], lx.SUFFIXES[index % len(lx.SUFFIXES)]["s"]),
            _join(lx.PREFIXES[index % len(lx.PREFIXES)]["s"], seed["s"]),
        ]
        for name in candidates:
            if len(out) >= limit:
                return out
            if not leads.allow(seed["s"]):
                break
            ok, _ = _accept(name, taken, max_len=13)
            if not ok:
                continue
            taken.add(name)
            leads.take(seed["s"])
            anchor = [m for m in morphemes if name.endswith(m)][:1]
            out.append(
                _entry(
                    name,
                    "metaphor",
                    f"Image '{seed['s']}' ({seed['meaning']}) + morphème de categorie : "
                    "l'humain retient l'image, la machine retrouve le secteur.",
                    [seed["s"], root["root"]],
                    ["metaphor", root["dominant_cluster"]],
                    anchor,
                )
            )
            break
    return out


def build_neologism(taken: set[str], rng: random.Random, limit: int) -> list[dict]:
    """Short invented word with legal FR/EN phonotactics.

    Deliberately strict: CV syllables only, optional single-consonant coda.
    A name that a French speaker cannot read aloud on the first try is worse
    than no name at all, so most draws are thrown away.
    """
    out: list[dict] = []
    onsets = ("b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z",
              "br", "dr", "fl", "gr", "pl", "pr", "tr", "bl", "cl", "vr", "kr")
    nuclei = ("a", "e", "i", "o", "u", "ai", "au", "ei", "ou")
    codas = ("", "", "", "n", "r", "l", "s", "x")
    guard = 0
    while len(out) < limit and guard < 8000:
        guard += 1
        count = rng.choice((2, 2, 3, 3))
        parts: list[str] = []
        for position in range(count):
            parts.append(rng.choice(onsets) + rng.choice(nuclei))
        if count == 2:
            parts[-1] += rng.choice(codas)
        name = "".join(parts)
        if not (4 <= len(name) <= 7):
            continue
        if tx.pronounceability(name) < 74:
            continue
        if re.search(r"[aeiou]{3}", name):
            continue
        if re.search(r"(.)\1", name):
            continue
        ok, _ = _accept(name, taken, max_len=7)
        if not ok:
            continue
        taken.add(name)
        out.append(
            _entry(
                name,
                "neologism",
                "Neologisme de 2-3 syllabes ouvertes, phonotaxe FR/EN validée : "
                "aucun sens parasite, coût de recherche de marque minimal.",
                [],
                ["neologism"],
                [],
                {"invented": True},
            )
        )
    return out


def build_geo(
    roots: list[dict],
    taken: set[str],
    limit: int,
    brief_tokens: list[str],
    leads: _Leads,
) -> list[dict]:
    """One morpheme = the sector, one = the mechanics.

    GEO logic: a model with no prior knowledge of the brand must be able to
    infer the category from the name alone, otherwise it refuses to answer
    or attaches the name to an existing entity.
    """
    out: list[dict] = []
    ordered = sorted(roots, key=lambda r: -r["score"])

    # Prefer roots that the brief itself uses: those are the words a buyer
    # would type into ChatGPT.
    def brief_weight(root: dict) -> int:
        return 1 if any(t in brief_tokens for t in root["root"].split()) else 0

    ordered = sorted(ordered, key=lambda r: (-brief_weight(r), -r["score"]))

    for index, root in enumerate(ordered[:18]):
        if len(out) >= limit:
            return out
        base = root["root"]
        if len(base) > 7:
            base = _head(base, 6)
        if not (3 <= len(base) <= 6):
            continue
        if not leads.allow(base):
            continue
        for step in range(len(METHOD_WORDS)):
            method = METHOD_WORDS[(index + step) % len(METHOD_WORDS)]
            if base.endswith(method) or method.startswith(base):
                continue
            name = _join(base, method)
            ok, _ = _accept(name, taken, max_len=12)
            if not ok:
                continue
            taken.add(name)
            leads.take(base)
            anchor = [base, method]
            brief_hit = [t for t in anchor if t in brief_tokens]
            out.append(
                _entry(
                    name,
                    "geo",
                    f"'{base}' nomme le domaine, '{method}' nomme la mécanique : "
                    "un LLM peut deviner la categorie sans contexte additionnel"
                    + (f" (aligné sur le brief : {', '.join(brief_hit[:3])})" if brief_hit else "")
                    + ".",
                    [base],
                    [root["dominant_cluster"], "tech"],
                    anchor,
                    {"brief_alignment": brief_hit},
                )
            )
            break
    return out


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def generate(document: dict, count: int = 30, seed: int = 7) -> dict:
    rng = random.Random(seed)
    roots = _pool(document)
    brief_tokens = document.get("brief", {}).get("tokens", [])
    per_archetype = max(1, count // 5)
    taken: set[str] = set()
    leads = _Leads(cap=2)

    buckets: dict[str, list[dict]] = {
        "descriptive": build_descriptive(roots, taken, per_archetype, leads),
        "blend": build_blend(roots, taken, per_archetype, leads),
        "metaphor": build_metaphor(roots, taken, per_archetype, leads),
        "neologism": build_neologism(taken, rng, per_archetype),
        "geo": build_geo(roots, taken, per_archetype, brief_tokens, leads),
    }

    candidates = [c for bucket in buckets.values() for c in bucket]
    if len(candidates) < count:
        extra = build_descriptive(roots[8:], taken, count - len(candidates), leads)
        buckets["descriptive"].extend(extra)
        candidates.extend(extra)
    if len(candidates) < count:
        extra = build_blend(roots[4:], taken, count - len(candidates), leads)
        buckets["blend"].extend(extra)
        candidates.extend(extra)

    candidates.sort(key=lambda c: (c["archetype"], -c["generation_score"], c["name"]))
    candidates = candidates[:count]

    distribution: dict[str, int] = {}
    for candidate in candidates:
        distribution[candidate["archetype"]] = distribution.get(candidate["archetype"], 0) + 1

    return {
        "meta": {
            "count": len(candidates),
            "requested": count,
            "seed": seed,
            "distribution": distribution,
            "leads_used": leads.count,
            "roots_used": len({r for c in candidates for r in c["roots"]}),
            "source": document.get("sources", {}),
        },
        "archetypes": ARCHETYPES,
        "candidates": candidates,
    }
