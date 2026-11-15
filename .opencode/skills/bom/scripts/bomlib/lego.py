"""The LEGO mechanic: contract a phrase into a 2-3 syllable name.

Reference case — LEGO comes from the Danish *leg godt* ("play well"), contracted
to LE + GO. The mechanic is not an acronym: it keeps the sound of the words,
not their initials, so the result stays pronounceable and looks like a word
rather than a code.

BOM generalises it:

    keyword (any language)
      -> translated into the most-used languages
      -> paired with a qualifier to form a short, meaningful phrase
      -> contracted by one of six rules
      -> repaired for FR/EN phonotactics
      -> filtered (profanity, brands, dictionary, pronounceability)
      -> scored for fidelity (0-100) and, later, on the BOM grid

Fidelity answers one question: *could someone who knows the source phrase
recognise this name, and does it sound like a brand rather than a truncation?*
"""

from __future__ import annotations

import re
from collections import Counter

from . import lexicons as lx
from . import text as tx
from . import translate as tr
from .generate import accept_name

ARCHETYPE = "lego"
ARCHETYPE_LABEL = "Contraction LEGO"

RULES: dict[str, str] = {
    "lego2": "2 premieres lettres de chaque mot (regle LEGO)",
    "head2": "premiere syllabe de chaque mot",
    "head_tail": "premiere syllabe du 1er mot + derniere syllabe du 2e",
    "cvc2": "consonne+voyelle de chaque mot",
    "blend": "fusion sur les lettres communes",
    "initials": "initiales + voyelle de liaison",
}

QUALIFIERS: tuple[str, ...] = (
    "fast", "simple", "clear", "true", "new", "smart", "easy", "better", "well",
)

MAX_LEN = 9


# --------------------------------------------------------------------------
# Phonetic surgery
# --------------------------------------------------------------------------


def _clean(word: str) -> str:
    slug = tx.slugify(word)
    return slug


def _head(word: str, maximum: int = 3) -> str:
    """First pronounceable chunk: onset + nucleus (+ coda if it helps)."""
    match = re.match(r"^[^aeiouy]*[aeiouy]+", word)
    if not match:
        return word[:maximum]
    head = match.group(0)
    if len(head) < 2 and len(word) > 2:
        head = word[:2]
    return head[:maximum]


def _tail(word: str, minimum: int = 2) -> str:
    matches = list(re.finditer(r"[aeiouy]+", word))
    if not matches:
        return word[-minimum:]
    last = matches[-1]
    start = max(0, last.start() - 1)
    return word[start:]


def repair(name: str) -> str:
    """Make a raw contraction sayable in French and English."""
    name = re.sub(r"(.)\1\1", r"\1\1", name)
    name = re.sub(r"[^a-z]", "", name)
    if not name:
        return name

    # break 3+ consonant piles with a neutral vowel
    def fix_run(match: re.Match) -> str:
        run = match.group(0)
        return run[0] + "a" + run[1:]

    name = re.sub(r"[bcdfghjklmnpqrstvwxz]{3,}", fix_run, name)

    # a final cluster is hard to say: close on a vowel
    if re.search(r"[bcdfghjklmnpqrstvwxz]{2}$", name):
        name += "o"

    # not enough vowels: open the first cluster
    if tx.vowel_ratio(name) < 0.3:
        name += "a"

    # cheap elegance: drop a doubled vowel at the seam
    name = re.sub(r"([aeiouy])\1+", r"\1", name)
    return name[:MAX_LEN]


def contract(words: list[str], rule: str) -> str | None:
    """Apply one contraction rule to an already normalised phrase."""
    cleaned = [w for w in (_clean(w) for w in words) if w]
    if len(cleaned) < 1:
        return None
    first = cleaned[0]
    second = cleaned[1] if len(cleaned) > 1 else ""

    if rule == "lego2":
        if not second:
            return repair(first[:4])
        return repair(first[:2] + second[:2])
    if rule == "head2":
        if not second:
            return repair(_head(first))
        return repair(_head(first) + _head(second))
    if rule == "head_tail":
        if not second:
            return repair(_head(first) + _tail(first))
        return repair(_head(first) + _tail(second))
    if rule == "cvc2":
        if not second:
            return repair(first[:2])
        return repair(first[0] + _head(first)[1:2] + second[0] + _head(second)[1:2])
    if rule == "blend":
        if not second:
            return None
        overlap = tx.longest_overlap(first, second, minimum=2)
        if overlap:
            return repair(first + second[overlap:])
        return repair(first[: max(2, len(first) - 1)] + second[1:])
    if rule == "initials":
        letters = "".join(word[0] for word in cleaned[:3])
        return repair(letters + "o")
    return None


def contract_phrase(phrase: str, rule: str = "lego2") -> str | None:
    """Public helper: 'leg godt' -> 'lego' (rule lego2)."""
    return contract(phrase.split(), rule)


# --------------------------------------------------------------------------
# Fidelity: does the contraction still carry the phrase?
# --------------------------------------------------------------------------


def recoverable_parts(name: str, words: list[str]) -> int:
    """How many source words are still recognisable inside the contraction."""
    count = 0
    for word in words:
        if not word:
            continue
        if name.startswith(word[:2]) or word[:3] in name or word[:2] in name[1:]:
            count += 1
    return count


def fidelity(name: str, words: list[str], lang_count: int, phone_penalty: int) -> int:
    syllables = tx.syllable_count(name)
    score = {1: 10, 2: 30, 3: 26, 4: 12}.get(syllables, 4)

    parts = recoverable_parts(name, words)
    score += min(parts, 2) * 12
    if all(len(word) >= 4 for word in words[:2]):
        score += 6

    score += min(lang_count, 4) * 4
    score += 10 if tx.pronounceability(name) >= 80 else 5
    score += 6 if phone_penalty <= 3 else 2
    if name in tr.BONUS_MEANINGS:
        score += 4
    return max(0, min(100, score))


# --------------------------------------------------------------------------
# Phrase building
# --------------------------------------------------------------------------

PHRASE_ORDERS: dict[str, tuple[str, str]] = {
    # lang -> (natural order, reversed order). We try both: a reversed phrase is
    # often ungrammatical, but it is what produces the best contraction, and
    # the source language is recorded so the user can judge.
    "fr": ("nq", "qn"), "es": ("nq", "qn"), "it": ("nq", "qn"),
    "pt": ("nq", "qn"), "en": ("qn", "nq"), "de": ("qn", "nq"),
    "nl": ("qn", "nq"), "sv": ("qn", "nq"), "da": ("qn", "nq"),
    "no": ("qn", "nq"), "pl": ("qn", "nq"), "tr": ("qn", "nq"),
    "ru": ("qn", "nq"), "el": ("qn", "nq"), "id": ("nq", "qn"),
    "vi": ("nq", "qn"),
}


def _order(lang: str, first: str, second: str, order: str) -> list[str]:
    return [first, second] if order == "nq" else [second, first]


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def _concept_pool(clusters: dict, source_lang: str, translator: tr.Translator) -> list[str]:
    """Corpus concepts we can translate: lexicon hits first, then top roots."""
    corpus_words = {tx.slugify(root["root"]) for root in clusters.get("roots", [])}
    brief_words = {tx.slugify(t) for t in clusters.get("brief", {}).get("tokens", [])}
    corpus_words |= brief_words

    source_values = {
        word: concept for concept, values in tr.CONCEPTS.items()
        for lang, word in values.items() if lang == source_lang
    }
    found = [concept for word, concept in source_values.items() if word in corpus_words]

    if not found:
        # No corpus concept could be mapped. Fall back on concepts we know in
        # the source language, never on raw roots: translating a French root as
        # if it were English produces nonsense.
        found = [
            concept for concept, values in tr.CONCEPTS.items()
            if source_lang in values
        ][:12]
    return list(dict.fromkeys(found))


def _translate_concept(
    concept: str, langs: list[str], source_lang: str, translator: tr.Translator
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for lang in langs:
        payload = translator.translate(concept, lang)
        if payload.get("value") and payload.get("roman"):
            out[lang] = payload
    return out


def generate_lego(
    clusters: dict,
    translator: tr.Translator,
    langs: list[str],
    source_lang: str = "fr",
    count: int = 30,
    seed: int = 7,
) -> dict:
    concepts = _concept_pool(clusters, source_lang, translator)
    qualifier_pool = [q for q in QUALIFIERS if tr.CONCEPTS.get(q)]

    # concept -> {lang: {value, roman, source}}
    concept_terms: dict[str, dict[str, dict]] = {}
    for concept in concepts:
        terms = _translate_concept(concept, langs, source_lang, translator)
        if len(terms) >= 2:
            concept_terms[concept] = terms

    # qualifier -> {lang: {value, roman, source}}
    qualifier_terms: dict[str, dict[str, dict]] = {}
    for qualifier in qualifier_pool:
        terms = _translate_concept(qualifier, langs, source_lang, translator)
        if len(terms) >= 2:
            qualifier_terms[qualifier] = terms

    records: dict[str, dict] = {}
    families: dict[tuple, tuple[str, float]] = {}
    phrase_count = 0

    def quality_of(name: str, score: int, rule: str) -> float:
        rule_bonus = {
            "lego2": 14,      # the canonical shape: 2 letters + 2 letters
            "head2": 4,
            "head_tail": 2,
            "blend": 0,
            "cvc2": -6,
            "initials": -8,
        }.get(rule, 0)
        return round(
            score * 0.45
            + tx.pronounceability(name) * 0.3
            + (8 if 5 <= len(name) <= 7 else 0)
            + rule_bonus
            - (10 if tx.phone_test_penalty(name) > 5 else 0),
            3,
        )

    for concept, terms in list(concept_terms.items())[:14]:
        for lang, payload in terms.items():
            if lang not in PHRASE_ORDERS:
                continue
            for qualifier, q_terms in list(qualifier_terms.items())[:8]:
                q_payload = q_terms.get(lang)
                if not q_payload:
                    continue
                for order in PHRASE_ORDERS[lang]:
                    words = _order(lang, payload["roman"], q_payload["roman"], order)
                    if any(len(word) < 2 for word in words):
                        continue
                    phrase_count += 1
                    phrase = " ".join(
                        [payload["value"], q_payload["value"]]
                        if order == "nq" else [q_payload["value"], payload["value"]]
                    )
                    for rule in RULES:
                        name = contract(words, rule)
                        if not name:
                            continue
                        ok, _reason = accept_name(name, set(), max_len=MAX_LEN)
                        if not ok:
                            continue
                        language_count = sum(
                            1
                            for other_lang in langs
                            if concept_terms[concept].get(other_lang)
                            and qualifier_terms[qualifier].get(other_lang)
                        )
                        score = fidelity(
                            name, words, language_count, tx.phone_test_penalty(name)
                        )
                        if recoverable_parts(name, words) == 0:
                            continue
                        quality = quality_of(name, score, rule)
                        provenance = {
                            "phrase": phrase,
                            "language": lang,
                            "rule": rule,
                            "rule_label": RULES[rule],
                            "order": "natural" if order == PHRASE_ORDERS[lang][0] else "inverse",
                            "concept": concept,
                            "qualifier": qualifier,
                            "words": words,
                            "fidelity": score,
                        }
                        entry = records.get(name)
                        if entry is None:
                            records[name] = {
                                "provenance": [provenance],
                                "fidelity": score,
                                "quality": quality,
                                "languages": {lang},
                            }
                        else:
                            entry["provenance"].append(provenance)
                            entry["languages"].add(lang)
                            if score > entry["fidelity"]:
                                entry["fidelity"] = score
                            if quality > entry["quality"]:
                                entry["quality"] = quality

                        # One winner per (concept, qualifier, language): this is
                        # what kills the biec / bieco / biecou / biecourt family.
                        key = (concept, qualifier, lang)
                        current = families.get(key)
                        if current is None or quality > current[1]:
                            families[key] = (name, quality)

    pool: dict[str, dict] = {}
    seen_names: set[str] = set()
    for key in sorted(families, key=lambda k: -families[k][1]):
        name = families[key][0]
        if name in seen_names:
            continue
        seen_names.add(name)
        pool[name] = records[name]

    # Language diversity: no single language takes more than 40% of the list,
    # and no single contraction rule more than 60%: the list must show options.
    cap = max(2, int(count * 0.4))
    rule_cap = max(3, int(count * 0.6))
    per_lang: Counter = Counter()
    per_rule: Counter = Counter()
    selected: list[dict] = []
    for name, payload in sorted(
        pool.items(), key=lambda item: (-item[1]["quality"], -item[1]["fidelity"], item[0])
    ):
        best = max(payload["provenance"], key=lambda p: p["fidelity"])
        if per_lang[best["language"]] >= cap:
            continue
        if per_rule[best["rule"]] >= rule_cap:
            continue
        # collapse near-duplicates: bico/bieco/cleco are the same idea
        if any(tx.levenshtein(name, other["name"]) <= 1 for other in selected):
            continue
        per_lang[best["language"]] += 1
        per_rule[best["rule"]] += 1
        selected.append({"name": name, **payload, "best": best})
        if len(selected) >= count:
            break

    candidates: list[dict] = []
    for item in selected:
        name = item["name"]
        best = item["best"]
        hard, soft = tx.bad_word_hits(name)
        flags = {
            "soft_bad": soft,
            "first_name": tx.is_common_first_name(name),
            "dictionary_noun": name in lx.DICTIONARY_NOUNS,
            "cliche_suffix": False,
            "invented": False,
            "coincidence": tr.BONUS_MEANINGS.get(name),
        }
        candidates.append(
            {
                "name": name,
                "display": tx.display_form(name),
                "archetype": ARCHETYPE,
                "archetype_label": ARCHETYPE_LABEL,
                "rationale": (
                    f"'{best['phrase']}' ({best['language']}) -> {best['rule_label']} : "
                    f"{len(item['provenance'])} provenance(s) dans "
                    f"{len(item['languages'])} langue(s)."
                    + (f" Coincidence: {flags['coincidence']}." if flags["coincidence"] else "")
                ),
                "roots": [best["concept"], best["qualifier"]],
                "clusters": ["lego", best["concept"]],
                "geo_anchor": best.get("words", [])[:2],
                "length": len(name),
                "syllables": tx.syllable_count(name),
                "pronounceability": tx.pronounceability(name),
                "phone_penalty": tx.phone_test_penalty(name),
                "flags": flags,
                "generation_score": item["fidelity"],
                "fidelity": item["fidelity"],
                "source_language": best["language"],
                "source_phrase": best["phrase"],
                "translations": {
                    prov["language"]: prov["phrase"] for prov in item["provenance"]
                },
                "rule": best["rule"],
                "provenance": item["provenance"][:6],
            }
        )

    return {
        "meta": {
            "engine": "lego",
            "count": len(candidates),
            "requested": count,
            "seed": seed,
            "source_language": source_lang,
            "languages_requested": langs,
            "concepts": len(concept_terms),
            "qualifiers": len(qualifier_terms),
            "phrases_evaluated": phrase_count,
            "translator": translator.stats(),
            "distribution": {ARCHETYPE: len(candidates)},
            "source": clusters.get("sources", {}),
        },
        "archetypes": {ARCHETYPE: ARCHETYPE_LABEL},
        "candidates": candidates,
    }
