"""Translation layer for the LEGO mechanic.

Goal: take a keyword in one language and obtain it in the languages most used
online, so that a phrase can be contracted into a short brandable name
(`leg godt` -> LEGO). Two providers, in order:

1. `MiniLexicon` - a curated, offline seed of high-value naming concepts.
   Fast, deterministic, no rate limit. Used first, always.
2. `MyMemory` - free public translation API (no key). Used for everything the
   lexicon does not cover, with on-disk cache and pacing.

Honesty rule: a translation is either known (`source: "lexicon"`), fetched and
cached (`source: "api"`), or absent. Never guessed, never invented.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import text as tx

# --------------------------------------------------------------------------
# Languages: the ones worth naming in, ordered by online reach.
# `latin` means "we can romanise it well enough to build a brandable string".
# --------------------------------------------------------------------------

LANGUAGES: tuple[dict, ...] = (
    {"code": "en", "label": "English", "latin": True, "reach": 1},
    {"code": "es", "label": "Espanol", "latin": True, "reach": 2},
    {"code": "fr", "label": "Francais", "latin": True, "reach": 3},
    {"code": "de", "label": "Deutsch", "latin": True, "reach": 4},
    {"code": "pt", "label": "Portugues", "latin": True, "reach": 5},
    {"code": "it", "label": "Italiano", "latin": True, "reach": 6},
    {"code": "nl", "label": "Nederlands", "latin": True, "reach": 7},
    {"code": "pl", "label": "Polski", "latin": True, "reach": 8},
    {"code": "tr", "label": "Turkce", "latin": True, "reach": 9},
    {"code": "sv", "label": "Svenska", "latin": True, "reach": 10},
    {"code": "da", "label": "Dansk", "latin": True, "reach": 11},
    {"code": "no", "label": "Norsk", "latin": True, "reach": 12},
    {"code": "id", "label": "Bahasa Indonesia", "latin": True, "reach": 13},
    {"code": "vi", "label": "Tieng Viet", "latin": True, "reach": 14},
    {"code": "ru", "label": "Russkiy", "latin": True, "reach": 15, "translit": "cyrillic"},
    {"code": "el", "label": "Ellinika", "latin": True, "reach": 16, "translit": "greek"},
    {"code": "ar", "label": "Arabiyya", "latin": False, "reach": 17},
    {"code": "hi", "label": "Hindi", "latin": False, "reach": 18},
    {"code": "zh", "label": "Zhongwen", "latin": False, "reach": 19},
    {"code": "ja", "label": "Nihongo", "latin": False, "reach": 20},
    {"code": "ko", "label": "Hangugeo", "latin": False, "reach": 21},
)

LANG_CODES: tuple[str, ...] = tuple(lang["code"] for lang in LANGUAGES)
LATIN_CODES: tuple[str, ...] = tuple(lang["code"] for lang in LANGUAGES if lang["latin"])
LANG_BY_CODE: dict[str, dict] = {lang["code"]: lang for lang in LANGUAGES}

# Phrases are built as adjective + noun or noun + adjective depending on the
# language. Used to keep the source expression grammatical enough to be
# recognisable by a native speaker.
ADJ_FIRST: set[str] = {"en", "de", "nl", "sv", "da", "no", "pl", "tr", "ru", "el", "id"}

# --------------------------------------------------------------------------
# Offline seed lexicon. Only concepts we are confident about, in the languages
# where a one-word translation is stable. Everything else goes through the API.
# --------------------------------------------------------------------------

CONCEPTS: dict[str, dict[str, str]] = {
    # nouns
    "price": {"fr": "prix", "en": "price", "es": "precio", "de": "preis", "it": "prezzo",
              "pt": "preco", "nl": "prijs", "da": "pris", "sv": "pris", "pl": "cena",
              "tr": "fiyat", "ru": "цена"},
    "cost": {"fr": "cout", "en": "cost", "es": "coste", "de": "kosten", "it": "costo",
             "pt": "custo", "nl": "kosten", "da": "pris", "sv": "kostnad", "pl": "koszt",
             "tr": "maliyet", "ru": "цена"},
    "menu": {"fr": "carte", "en": "menu", "es": "menu", "de": "karte", "it": "menu",
             "pt": "menu", "nl": "kaart", "da": "menu", "sv": "meny", "pl": "menu",
             "tr": "menu", "ru": "меню"},
    "data": {"fr": "donnees", "en": "data", "es": "datos", "de": "daten", "it": "dati",
             "pt": "dados", "nl": "data", "da": "data", "sv": "data", "pl": "dane",
             "tr": "veri", "ru": "данные"},
    "team": {"fr": "equipe", "en": "team", "es": "equipo", "de": "team", "it": "squadra",
             "pt": "equipe", "nl": "team", "da": "hold", "sv": "team", "pl": "zespol",
             "tr": "ekip", "ru": "команда"},
    "brand": {"fr": "marque", "en": "brand", "es": "marca", "de": "marke", "it": "marca",
              "pt": "marca", "nl": "merk", "da": "marke", "sv": "varumarke", "pl": "marka",
              "tr": "marka", "ru": "бренд"},
    "market": {"fr": "marche", "en": "market", "es": "mercado", "de": "markt", "it": "mercato",
               "pt": "mercado", "nl": "markt", "da": "marked", "sv": "marknad", "pl": "rynek",
               "tr": "pazar", "ru": "рынок"},
    "time": {"fr": "temps", "en": "time", "es": "tiempo", "de": "zeit", "it": "tempo",
             "pt": "tempo", "nl": "tijd", "da": "tid", "sv": "tid", "pl": "czas",
             "tr": "zaman", "ru": "время"},
    "money": {"fr": "argent", "en": "money", "es": "dinero", "de": "geld", "it": "denaro",
              "pt": "dinheiro", "nl": "geld", "da": "penge", "sv": "pengar", "pl": "pieniadze",
              "tr": "para", "ru": "деньги"},
    "work": {"fr": "travail", "en": "work", "es": "trabajo", "de": "arbeit", "it": "lavoro",
             "pt": "trabalho", "nl": "werk", "da": "arbejde", "sv": "arbete", "pl": "praca",
             "tr": "is", "ru": "работа"},
    "idea": {"fr": "idee", "en": "idea", "es": "idea", "de": "idee", "it": "idea",
             "pt": "ideia", "nl": "idee", "da": "ide", "sv": "ide", "pl": "pomysl",
             "tr": "fikir", "ru": "идея"},
    "key": {"fr": "cle", "en": "key", "es": "clave", "de": "schlussel", "it": "chiave",
            "pt": "chave", "nl": "sleutel", "da": "nogle", "sv": "nyckel", "pl": "klucz",
            "tr": "anahtar", "ru": "ключ"},
    "path": {"fr": "chemin", "en": "path", "es": "camino", "de": "weg", "it": "via",
             "pt": "caminho", "nl": "pad", "da": "vej", "sv": "vag", "pl": "droga",
             "tr": "yol", "ru": "путь"},
    "star": {"fr": "etoile", "en": "star", "es": "estrella", "de": "stern", "it": "stella",
             "pt": "estrela", "nl": "ster", "da": "stjerne", "sv": "stjarna", "pl": "gwiazda",
             "tr": "yildiz", "ru": "звезда"},
    "wave": {"fr": "vague", "en": "wave", "es": "ola", "de": "welle", "it": "onda",
             "pt": "onda", "nl": "golf", "da": "bolge", "sv": "vag", "pl": "fala",
             "tr": "dalga", "ru": "волна"},
    "spark": {"fr": "etincelle", "en": "spark", "es": "chispa", "de": "funke", "it": "scintilla",
              "pt": "faisca", "nl": "vonk", "da": "gnist", "sv": "gnista", "pl": "iskra",
              "tr": "kivilcim", "ru": "искра"},
    "seed": {"fr": "graine", "en": "seed", "es": "semilla", "de": "samen", "it": "seme",
             "pt": "semente", "nl": "zaad", "da": "fro", "sv": "fre", "pl": "nasiono",
             "tr": "tohum", "ru": "семя"},
    "hive": {"fr": "ruche", "en": "hive", "es": "colmena", "de": "bienenstock", "it": "alveare",
             "pt": "colmeia", "nl": "korf", "da": "bikube", "sv": "kupa", "pl": "ul",
             "tr": "kovan", "ru": "улей"},
    "honey": {"fr": "miel", "en": "honey", "es": "miel", "de": "honig", "it": "miele",
              "pt": "mel", "nl": "honing", "da": "honning", "sv": "honung", "pl": "miod",
              "tr": "bal", "ru": "мед"},
    "light": {"fr": "lumiere", "en": "light", "es": "luz", "de": "licht", "it": "luce",
              "pt": "luz", "nl": "licht", "da": "lys", "sv": "ljus", "pl": "swiatlo",
              "tr": "isik", "ru": "свет"},
    "north": {"fr": "nord", "en": "north", "es": "norte", "de": "nord", "it": "nord",
              "pt": "norte", "nl": "noord", "da": "nord", "sv": "norr", "pl": "polnoc",
              "tr": "kuzey", "ru": "север"},
    "play": {"fr": "jouer", "en": "play", "es": "jugar", "de": "spielen", "it": "giocare",
             "pt": "jogar", "nl": "spelen", "da": "leg", "sv": "leka", "pl": "grac",
             "tr": "oynamak", "ru": "играть"},
    "table": {"fr": "table", "en": "table", "es": "mesa", "de": "tisch", "it": "tavolo",
              "pt": "mesa", "nl": "tafel", "da": "bord", "sv": "bord", "pl": "stol",
              "tr": "masa", "ru": "стол"},
    "food": {"fr": "repas", "en": "food", "es": "comida", "de": "essen", "it": "cibo",
             "pt": "comida", "nl": "eten", "da": "mad", "sv": "mat", "pl": "jedzenie",
             "tr": "yemek", "ru": "еда"},
    "plan": {"fr": "plan", "en": "plan", "es": "plan", "de": "plan", "it": "piano",
             "pt": "plano", "nl": "plan", "da": "plan", "sv": "plan", "pl": "plan",
             "tr": "plan", "ru": "план"},
    # qualifiers
    "well": {"fr": "bien", "en": "well", "es": "bien", "de": "gut", "it": "bene",
             "pt": "bem", "nl": "goed", "da": "godt", "sv": "bra", "pl": "dobrze",
             "tr": "iyi", "ru": "хорошо"},
    "fast": {"fr": "rapide", "en": "fast", "es": "rapido", "de": "schnell", "it": "rapido",
             "pt": "rapido", "nl": "snel", "da": "hurtig", "sv": "snabb", "pl": "szybki",
             "tr": "hizli", "ru": "быстро"},
    "simple": {"fr": "simple", "en": "simple", "es": "simple", "de": "einfach", "it": "semplice",
               "pt": "simples", "nl": "simpel", "da": "enkelt", "sv": "enkel", "pl": "prosty",
               "tr": "basit", "ru": "просто"},
    "clear": {"fr": "clair", "en": "clear", "es": "claro", "de": "klar", "it": "chiaro",
              "pt": "claro", "nl": "helder", "da": "klar", "sv": "klar", "pl": "jasny",
              "tr": "net", "ru": "ясно"},
    "true": {"fr": "vrai", "en": "true", "es": "verdadero", "de": "wahr", "it": "vero",
             "pt": "verdadeiro", "nl": "waar", "da": "sand", "sv": "sann", "pl": "prawda",
             "tr": "gercek", "ru": "правда"},
    "new": {"fr": "nouveau", "en": "new", "es": "nuevo", "de": "neu", "it": "nuovo",
            "pt": "novo", "nl": "nieuw", "da": "ny", "sv": "ny", "pl": "nowy",
            "tr": "yeni", "ru": "новый"},
    "smart": {"fr": "malin", "en": "smart", "es": "listo", "de": "klug", "it": "saggio",
              "pt": "esperto", "nl": "slim", "da": "klog", "sv": "smart", "pl": "madry",
              "tr": "akilli", "ru": "умный"},
    "easy": {"fr": "facile", "en": "easy", "es": "facil", "de": "leicht", "it": "facile",
             "pt": "facil", "nl": "makkelijk", "da": "nem", "sv": "latt", "pl": "latwy",
             "tr": "kolay", "ru": "легко"},
    "better": {"fr": "mieux", "en": "better", "es": "mejor", "de": "besser", "it": "meglio",
               "pt": "melhor", "nl": "beter", "da": "bedre", "sv": "battre", "pl": "lepiej",
               "tr": "daha iyi", "ru": "лучше"},
}

# Positive coincidence: if the contracted name happens to mean something good
# in another language, it is a free bonus (LEGO / "legere"-adjacent folklore).
BONUS_MEANINGS: dict[str, str] = {
    "luz": "lumiere (ES/PT)", "lume": "lumiere (IT/RO)", "lux": "lumiere (LA)",
    "sol": "soleil (ES/PT/LA)", "mar": "mer (ES/PT)", "vida": "vie (ES/PT)",
    "vita": "vie (IT/LA)", "vera": "vraie (IT/ES/LA)", "vero": "vrai (IT)",
    "nova": "neuve (PT/ES/LA)", "nuevo": "neuf (ES)", "alma": "ame (ES/PT)",
    "arte": "art (IT/ES/PT)", "flor": "fleur (ES/PT)", "brio": "energie (IT/ES)",
    "ora": "maintenant (IT/ES)", "via": "chemin (IT/ES/LA)", "kai": "mer (HAW)",
    "zen": "calme (JP)", "oro": "or (ES/IT)", "alto": "haut (IT/ES)",
    "forte": "fort (IT/PT)", "prima": "premiere (IT/LA)", "solo": "seul (IT/ES)",
    "tempo": "temps (IT/PT)", "mondo": "monde (IT)", "punto": "point (IT/ES)",
}

CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}

GREEK = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th",
    "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p",
    "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps",
    "ω": "o",
}


def romanize(value: str, lang: str) -> str | None:
    """Latin-alphabet form of a translated word, or None if not romanisable."""
    meta = LANG_BY_CODE.get(lang, {})
    if not meta.get("latin", True):
        return None
    text = unicodedata.normalize("NFKD", value)
    table = CYRILLIC if meta.get("translit") == "cyrillic" else (
        GREEK if meta.get("translit") == "greek" else {}
    )
    out = []
    for char in text.lower():
        if char in table:
            out.append(table[char])
        elif unicodedata.combining(char):
            continue
        else:
            out.append(char)
    roman = "".join(out)
    roman = re.sub(r"[^a-z]+", "", roman)
    return roman or None


# --------------------------------------------------------------------------
# Lexicon lookup
# --------------------------------------------------------------------------

_INDEX: dict[str, dict[str, str]] = {}
for _concept, _values in CONCEPTS.items():
    for _lang, _word in _values.items():
        _INDEX.setdefault(_lang, {})[_word.lower()] = _concept


def lexicon_lookup(concept: str, lang: str) -> str | None:
    return CONCEPTS.get(concept, {}).get(lang)


def lexicon_concepts() -> list[str]:
    return sorted(CONCEPTS)


# --------------------------------------------------------------------------
# MyMemory provider
# --------------------------------------------------------------------------


class Translator:
    """Translation facade: lexicon first, then a cached HTTP provider."""

    def __init__(
        self,
        cache_dir: str | Path,
        source_lang: str = "fr",
        provider: str = "mymemory",
        timeout: float = 10.0,
        pace: float = 0.35,
        enabled: bool = True,
    ):
        self.cache_dir = Path(cache_dir) / "translate"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.source_lang = source_lang
        self.provider = provider
        self.timeout = timeout
        self.pace = pace
        self.enabled = enabled and provider != "offline"
        self.calls = 0
        self.from_cache = 0
        self.failures = 0

    # -- cache -----------------------------------------------------------
    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{hashlib.sha1(key.encode()).hexdigest()}.json"

    def _read(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if time.time() - payload.get("ts", 0) > 30 * 24 * 3600:
            return None
        self.from_cache += 1
        return payload["body"]
    def _write(self, key: str, body: dict) -> None:
        self._path(key).write_text(
            json.dumps({"ts": time.time(), "body": body}, ensure_ascii=False), encoding="utf-8"
        )

    # -- api -------------------------------------------------------------
    def _http(self, text: str, src: str, dst: str) -> str | None:
        query = urllib.parse.urlencode({"q": text, "langpair": f"{src}|{dst}"})
        url = f"https://api.mymemory.translated.net/get?{query}"
        request = urllib.request.Request(url, headers={"User-Agent": "bom-skill/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(200_000).decode("utf-8", "replace"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            self.failures += 1
            return None
        self.calls += 1
        if data.get("responseStatus") != 200:
            self.failures += 1
            return None
        translated = (data.get("responseData") or {}).get("translatedText", "")
        if not translated or translated.lower().startswith("my memory"):
            self.failures += 1
            return None
        return translated.strip()

    # -- public ----------------------------------------------------------
    def translate(self, concept: str, lang: str) -> dict:
        """Return {value, lang, source, roman} for one concept/language."""
        known = lexicon_lookup(concept, lang)
        if known:
            return {
                "value": known,
                "lang": lang,
                "source": "lexicon",
                "roman": romanize(known, lang),
            }
        if not self.enabled:
            return {"value": None, "lang": lang, "source": "none", "roman": None}

        cache_key = f"{self.source_lang}|{lang}|{concept}"
        cached = self._read(cache_key)
        if cached is not None:
            return cached

        time.sleep(self.pace)
        raw = self._http(concept, "en", lang)
        if not raw:
            body = {"value": None, "lang": lang, "source": "none", "roman": None}
        else:
            body = {
                "value": raw,
                "lang": lang,
                "source": "api",
                "roman": romanize(raw, lang),
            }
        self._write(cache_key, body)
        return body

    def translate_word(self, word: str, src: str, dst: str) -> str | None:
        """Free-text translation (used when the corpus word is not a concept)."""
        concept = _INDEX.get(src, {}).get(tx.slugify(word))
        if concept:
            return lexicon_lookup(concept, dst)
        if not self.enabled:
            return None
        cache_key = f"{src}|{dst}|{word}"
        cached = self._read(cache_key)
        if cached is not None:
            return cached.get("value")
        time.sleep(self.pace)
        raw = self._http(word, src, dst)
        body = {"value": raw, "lang": dst, "source": "api" if raw else "none"}
        self._write(cache_key, body)
        return raw

    def stats(self) -> dict:
        return {
            "provider": self.provider if self.enabled else "offline",
            "api_calls": self.calls,
            "cache_hits": self.from_cache,
            "failures": self.failures,
        }


def resolve_languages(raw: str | None, source_lang: str) -> tuple[list[str], list[str]]:
    """Parse --langs. Returns (usable latin-script languages, skipped ones)."""
    if not raw:
        wanted = [source_lang] + [c for c in LATIN_CODES[:9] if c != source_lang]
    else:
        wanted = [item.strip().lower() for item in raw.split(",") if item.strip()]
        wanted = [item for item in wanted if item in LANG_BY_CODE]

    usable, skipped = [], []
    for code in dict.fromkeys(wanted):
        if LANG_BY_CODE[code]["latin"]:
            usable.append(code)
        else:
            skipped.append(code)
    if source_lang not in usable:
        usable.insert(0, source_lang)
    return usable, skipped
