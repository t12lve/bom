"""Text, phonetics and morphology helpers for BOM.

Pure functions only. Every heuristic here is explainable: the score engine
quotes these numbers in its evidence, so they must stay deterministic.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Iterable

from . import lexicons as lx

WORD_RE = re.compile(r"[a-z0-9]+")
VOWELS = set("aeiouy")


@lru_cache(maxsize=8192)
def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@lru_cache(maxsize=8192)
def normalize(value: str) -> str:
    """Lowercase, accent-free, single-spaced form used for all comparisons."""
    value = strip_accents(value or "").lower()
    value = value.replace("&", " et ").replace("'", " ").replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=8192)
def slugify(value: str) -> str:
    """ASCII slug suitable for a domain label and a package name."""
    value = strip_accents(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


@lru_cache(maxsize=8192)
def tokens(value: str) -> list[str]:
    return WORD_RE.findall(normalize(value))


@lru_cache(maxsize=8192)
def display_form(slug: str) -> str:
    """CamelCase display form; keeps the slug as the canonical identity."""
    return slug[:1].upper() + slug[1:] if slug else slug


@lru_cache(maxsize=8192)
def is_ascii_slug(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9]{1,20}", value or ""))


@lru_cache(maxsize=8192)
def vowel_ratio(value: str) -> float:
    letters = [c for c in value if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c in VOWELS) / len(letters)


@lru_cache(maxsize=8192)
def consonant_runs(value: str) -> list[str]:
    return re.findall(r"[bcdfghjklmnpqrstvwxz]{2,}", value or "")


@lru_cache(maxsize=8192)
def max_consonant_run(value: str) -> int:
    runs = consonant_runs(value)
    return max((len(r) for r in runs), default=0)


@lru_cache(maxsize=8192)
def syllable_count(value: str) -> int:
    """Rough syllable estimate: vowel groups, adjusted for silent finals."""
    groups = re.findall(r"[aeiouy]+", value or "")
    count = len(groups)
    if count > 1 and value.endswith("e") and not value.endswith(("le", "re")):
        count -= 1
    return max(count, 1)


@lru_cache(maxsize=8192)
def pronounceability(value: str) -> int:
    """0-100 heuristic: can a French or English speaker read it out loud?"""
    slug = slugify(value)
    if not slug:
        return 0
    score = 100
    run = max_consonant_run(slug)
    if run >= 4:
        score -= 30
    elif run == 3:
        score -= 12
    ratio = vowel_ratio(slug)
    if ratio < 0.25:
        score -= 25
    elif ratio > 0.62:
        score -= 10
    if not any(c in VOWELS for c in slug):
        score -= 40
    if re.search(r"(.)\1\1", slug):
        score -= 15
    if re.search(r"[bcdfghjklmnpqrstvwxz]{3}$", slug):
        score -= 10
    if re.search(r"[qx][^aeiouy]", slug):
        score -= 8
    if re.search(r"(sz|cz|rz|ssz|shch|kh|zh)", slug):
        score -= 14
    if re.search(r"[aeiou]{3}", slug):
        score -= 6
    if re.search(r"(iu|uo|ua|ue|ii|uu|yi)", slug):
        score -= 9
    if len(slug) <= 3:
        score -= 10
    return max(0, min(100, score))


@lru_cache(maxsize=8192)
def phone_test_penalty(value: str) -> int:
    """0 = easy to dictate on the phone, positive = ambiguity cost.

    Models the classic French telephone alphabet pain: B/P, D/T, M/N,
    S/F, and letters that need spelling out (y, w, k, q, h).
    """
    slug = slugify(value)
    penalty = 0
    tricky = sum(1 for c in slug if c in "ywkqh")
    penalty += tricky * 2
    for pair in ("bp", "pb", "dt", "td", "mn", "nm", "sz", "zs", "fv", "vf"):
        if pair in slug:
            penalty += 3
    if re.search(r"[aeiou]{3}", slug):
        penalty += 3
    if re.search(r"(.)\1", slug):
        penalty += 2
    if len(slug) >= 12:
        penalty += 4
    return penalty


@lru_cache(maxsize=8192)
def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(
                min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            )
        prev = cur
    return prev[-1]


@lru_cache(maxsize=8192)
def longest_overlap(left: str, right: str, minimum: int = 2) -> int:
    """Longest suffix of `left` that is a prefix of `right`."""
    for size in range(min(len(left), len(right)), minimum - 1, -1):
        if left.endswith(right[:size]):
            return size
    return 0


def _word_hit(word: str, slug: str) -> bool:
    """Length-aware match, so 'pute' blocks 'pute'/'puteapp' but not 'compute'.

    Short words are the dangerous ones in French: 'pute' lives inside
    'compute', 'bite' inside 'arbiter', 'cul' inside 'calcul'. A brand is a
    single token, so position is the only usable signal.
    """
    size = len(word)
    if word == "xxx":
        return word in slug
    if size >= 5:
        return word in slug
    if size == 4:
        return (
            slug == word
            or slug.startswith(word)
            or (slug.endswith(word) and len(slug) <= size + 2)
        )
    return slug == word


# Common words that legitimately contain a soft term. A candidate built on one
# of them must not be flagged: 'analytics' is not 'anal', 'asset' is not 'ass'.
BENIGN_WORDS: tuple[str, ...] = (
    "analytics", "analysis", "analyst", "analog", "analogue",
    "asset", "assets", "assess", "assist", "assemble", "association",
    "sextant", "sextet", "sexton",
    "chief", "chiefs", "chiefdom",
    "skill", "skills", "skilled", "skillful",
)


@lru_cache(maxsize=8192)
def bad_word_hits(value: str) -> tuple[list[str], list[str]]:
    """Return (hard_hits, soft_hits) for profanity and derision checks."""
    slug = slugify(value)
    hard = sorted({word for word in lx.HARD_BAD_WORDS if _word_hit(word, slug)})
    soft = sorted(
        {
            word
            for word in lx.SOFT_BAD_SUBSTRINGS
            if word not in hard
            and _word_hit(word, slug)
            and not any(
                benign.startswith(word) and slug.startswith(benign)
                for benign in BENIGN_WORDS
            )
        }
    )
    return hard, soft


@lru_cache(maxsize=8192)
def has_generic_word(value: str) -> str | None:
    slug = slugify(value)
    if slug in lx.GENERIC_WORDS:
        return slug
    for word in lx.GENERIC_WORDS:
        if len(word) >= 5 and slug == word:
            return word
    return None


@lru_cache(maxsize=8192)
def brand_collision(value: str) -> str | None:
    """Return the known brand a candidate would collide with, if any.

    Two rules: an exact match, or a distinctive brand (>= 4 letters) embedded
    in the candidate. Short generic tokens are skipped so that 'make' does
    not reject every 'maker' name.
    """
    slug = slugify(value)
    for brand in lx.BRAND_BLOCKLIST:
        if slug == brand:
            return brand
    for brand in lx.BRAND_BLOCKLIST:
        if len(brand) >= 4 and brand in slug:
            return brand
    return None


@lru_cache(maxsize=8192)
def is_common_first_name(value: str) -> bool:
    return slugify(value) in lx.COMMON_FIRST_NAMES


@lru_cache(maxsize=8192)
def fr_pronunciation_issues(value: str) -> list[str]:
    """Specific traps a French audience hits when reading a coined name."""
    slug = slugify(value)
    issues: list[str] = []
    if "th" in slug:
        issues.append("'th' se lit 't' en FR: perte de la prononciation voulue")
    if re.search(r"[aeiou]?ck", slug):
        issues.append("'ck' final peu naturel en FR")
    if slug.endswith(("ly", "ify")) and len(slug) > 6:
        issues.append("suffixe SaaS anglophone: sonne importe en FR")
    if re.search(r"w[^aeiouy]", slug):
        issues.append("'w' sans voyelle: lecture hesitante")
    if re.search(r"^[aeiou]", slug):
        issues.append("attaque vocalique: elision possible a l'oral ('l'app')")
    return issues


@lru_cache(maxsize=8192)
def en_pronunciation_issues(value: str) -> list[str]:
    slug = slugify(value)
    issues: list[str] = []
    if re.search(r"^(kn|gn|pn|ps)", slug):
        issues.append("attaque muette en EN")
    if re.search(r"[aeiou]{2}(ou|au|eu)", slug):
        issues.append("digramme vocalique ambigu EN/FR")
    if slug.endswith(("e",)) and len(slug) > 5:
        issues.append("'e' final muet en EN, prononce en FR")
    if re.search(r"(zh|kh|gh)", slug):
        issues.append("digramme consonantique rare en EN")
    return issues


def pseudo_words(text: str) -> list[str]:
    """Capitalised multiword n-grams, useful for detecting existing brands."""
    words = tokens(text)
    return [" ".join(words[i : i + 2]) for i in range(len(words) - 1)]


def keyword_ngrams(words: Iterable[str], sizes: tuple[int, ...] = (1, 2)) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    seq = [w for w in words if w]
    for size in sizes:
        for i in range(len(seq) - size + 1):
            gram = tuple(seq[i : i + size])
            counts[gram] = counts.get(gram, 0) + 1
    return counts


def title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())
