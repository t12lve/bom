"""Phase 2 - automated technical audit.

Checks, per candidate:
  * static filters        (profanity, brand blocklist, genericity, morphology)
  * domain availability   (RDAP + DNS, per TLD)
  * code registries       (GitHub user/repos, npm, PyPI, crates.io)
  * app stores            (iTunes Search API; Play Store is manual-only)
  * SERP / trademark      (no open API: emits the exact query pack for Phase 3)

Everything is stdlib-only, cached, rate-limited and concurrency-safe.
Statuses are always one of: available | registered | unknown | manual.
`unknown` is never reported as a pass.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import lexicons as lx
from . import text as tx

USER_AGENT = (
    "bom-skill/1.0 (brand due diligence; +https://opencode.ai) "
    "python-urllib"
)
CACHE_TTL_OK = 7 * 24 * 3600
CACHE_TTL_UNKNOWN = 24 * 3600

RDAP_FALLBACK: dict[str, tuple[str, ...]] = {
    "fr": ("https://rdap.nic.fr/domain/{}", "https://rdap.org/domain/{}"),
    "com": ("https://rdap.org/domain/{}",),
    "ai": ("https://rdap.org/domain/{}",),
    "app": ("https://rdap.org/domain/{}",),
    "io": ("https://rdap.org/domain/{}",),
}


# --------------------------------------------------------------------------
# Network layer
# --------------------------------------------------------------------------


class Net:
    """Tiny HTTP client: cache, retry, per-host pacing, JSON helpers."""

    def __init__(self, cache_dir: str | Path, timeout: float = 8.0, retries: int = 2, pace: float = 0.25):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.retries = retries
        self.pace = pace
        self._lock = threading.Lock()
        self._last_hit: dict[str, float] = {}
        self._context = ssl.create_default_context()
        self.github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self._blocked: dict[str, str] = {}

    # -- rate-limit circuit breaker --------------------------------------
    @staticmethod
    def _block_key(url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        first = parsed.path.strip("/").split("/")[0]
        return f"{parsed.netloc}/{first}" if first else parsed.netloc

    def _is_blocked(self, url: str) -> bool:
        key = self._block_key(url)
        return any(key.startswith(blocked) for blocked in self._blocked)

    def _block(self, url: str, reason: str) -> None:
        with self._lock:
            self._blocked[self._block_key(url)] = reason

    # -- cache -----------------------------------------------------------
    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _cache_read(self, key: str) -> dict | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        ttl = CACHE_TTL_OK if payload.get("status") in {"ok"} else CACHE_TTL_UNKNOWN
        if time.time() - payload.get("ts", 0) > ttl:
            return None
        return payload

    def _cache_write(self, key: str, status: str, body: dict) -> None:
        path = self._cache_path(key)
        path.write_text(
            json.dumps({"ts": time.time(), "status": status, "body": body}, ensure_ascii=False),
            encoding="utf-8",
        )

    # -- pacing ----------------------------------------------------------
    def _wait(self, host: str) -> None:
        with self._lock:
            last = self._last_hit.get(host, 0.0)
            wait = self.pace - (time.time() - last)
            if wait > 0:
                time.sleep(min(wait, self.pace))
            self._last_hit[host] = time.time()

    # -- request ---------------------------------------------------------
    def fetch(self, url: str, accept: str = "application/json") -> dict:
        if self._is_blocked(url):
            return {
                "http": 403,
                "raw": "",
                "blocked": True,
                "error": "quota: verification interrompue",
            }
        cached = self._cache_read(url)
        if cached:
            return cached["body"]

        last_error = "unknown"
        for attempt in range(self.retries + 1):
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc
            self._wait(host)
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": accept,
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
            if host == "api.github.com" and self.github_token:
                headers["Authorization"] = f"Bearer {self.github_token}"
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout, context=self._context) as response:
                    raw = response.read(400_000)
                    code = response.status
                body = {"http": code, "raw": raw.decode("utf-8", "replace")}
                if accept.endswith("json"):
                    try:
                        body["json"] = json.loads(body["raw"][:400_000])
                    except json.JSONDecodeError:
                        body["json"] = None
                self._cache_write(url, "ok", body)
                return body
            except urllib.error.HTTPError as exc:
                body = {"http": exc.code, "raw": ""}
                if exc.code in (404, 410):
                    self._cache_write(url, "ok", body)
                    return body
                if exc.code in (401, 403, 429):
                    # Never cache a quota or auth failure: it would poison the
                    # cache for days and turn a temporary limit into a finding.
                    self._block(url, "rate_limited" if exc.code != 401 else "auth")
                    last_error = "rate_limited" if exc.code != 401 else "auth"
                    if exc.code == 429:
                        time.sleep(1.2 * (attempt + 1))
                        continue
                    return body
                if 400 <= exc.code < 500:
                    return body
                last_error = f"http_{exc.code}"
                time.sleep(0.6 * (attempt + 1))
            except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as exc:
                last_error = type(exc).__name__
                time.sleep(0.6 * (attempt + 1))

        body = {"http": None, "raw": "", "error": last_error}
        self._cache_write(url, "error", body)
        return body


# --------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------


def check_domain(net: Net, name: str, tld: str) -> dict:
    domain = f"{name}.{tld}"
    result = {
        "tld": tld,
        "domain": domain,
        "status": "unknown",
        "confidence": "low",
        "detail": "",
        "registrar": None,
        "created": None,
        "url": f"https://{domain}",
    }

    # DNS first: a resolving name is registered even if RDAP is silent.
    resolves: bool | None = False
    try:
        socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        resolves = True
    except socket.gaierror:
        resolves = False
    except OSError:
        resolves = None

    rdap_templates = RDAP_FALLBACK.get(tld, ("https://rdap.org/domain/{}",))
    for template in rdap_templates:
        body = net.fetch(template.format(domain), accept="application/rdap+json")
        code = body.get("http")
        if code == 404:
            result.update(
                status="available",
                confidence="high",
                detail="RDAP: aucune inscription trouvee (404)",
            )
            break
        if code == 200 and body.get("json"):
            data = body["json"]
            registrar = None
            try:
                for entity in data.get("entities", []) or []:
                    if "registrar" in (entity.get("roles") or []):
                        for item in entity.get("vcardArray", [[], []])[1]:
                            if item and item[0] == "fn":
                                registrar = item[3]
                                break
            except (IndexError, KeyError, TypeError):
                registrar = None
            created = None
            for event in data.get("events", []) or []:
                if event.get("eventAction") == "registration":
                    created = event.get("eventDate")
            result.update(
                status="registered",
                confidence="high",
                detail="RDAP: domaine enregistre",
                registrar=registrar,
                created=created,
            )
            break
        result["detail"] = f"RDAP indisponible ({code or body.get('error')})"

    if result["status"] == "unknown" and resolves is True:
        result.update(
            status="registered",
            confidence="medium",
            detail="DNS resout: domaine actif (RDAP muet)",
        )
    if result["status"] == "unknown" and resolves is False:
        result["detail"] = result["detail"] or "DNS ne resout pas, RDAP muet: a confirmer chez le registraire"
    return result


def check_registries(net: Net, name: str) -> list[dict]:
    checks: list[dict] = []

    body = net.fetch(f"https://api.github.com/users/{name}")
    if body.get("http") == 404:
        checks.append(_reg("github_user", "libre", "aucun compte GitHub a ce nom"))
    elif body.get("http") == 200 and body.get("json"):
        login = body["json"].get("login", name)
        checks.append(
            _reg(
                "github_user",
                "pris",
                f"compte GitHub @{login} ({body['json'].get('public_repos', 0)} repos)",
                f"https://github.com/{login}",
            )
        )
    else:
        checks.append(_reg("github_user", "inconnu", _net_note(body)))

    repo_body = net.fetch(
        f"https://api.github.com/search/repositories?q={urllib.parse.quote(name)}"
        "&in=name&per_page=1"
    )
    if repo_body.get("http") == 200 and repo_body.get("json") is not None:
        total = repo_body["json"].get("total_count", 0)
        status = "libre" if total == 0 else ("pris" if total > 5 else "ambigu")
        checks.append(
            _reg(
                "github_repo",
                status,
                f"{total} depot(s) GitHub contiennent '{name}' dans le nom",
                f"https://github.com/search?q={urllib.parse.quote(name)}&type=repositories",
            )
        )
    else:
        checks.append(_reg("github_repo", "inconnu", _net_note(repo_body)))

    body = net.fetch(f"https://registry.npmjs.org/{name}")
    if body.get("http") == 404:
        checks.append(_reg("npm", "libre", "aucun paquet npm"))
    elif body.get("http") == 200:
        downloads = ""
        if isinstance(body.get("json"), dict):
            dist_tags = body["json"].get("dist-tags", {})
            downloads = f" (version {dist_tags.get('latest', '?')})"
        checks.append(_reg("npm", "pris", f"paquet npm existant{downloads}", f"https://www.npmjs.com/package/{name}"))
    else:
        checks.append(_reg("npm", "inconnu", _net_note(body)))

    body = net.fetch(f"https://pypi.org/pypi/{name}/json")
    if body.get("http") == 404:
        checks.append(_reg("pypi", "libre", "aucun paquet PyPI"))
    elif body.get("http") == 200:
        checks.append(_reg("pypi", "pris", "paquet PyPI existant", f"https://pypi.org/project/{name}/"))
    else:
        checks.append(_reg("pypi", "inconnu", _net_note(body)))

    body = net.fetch(f"https://crates.io/api/v1/crates/{name}", accept="application/json")
    if body.get("http") == 404:
        checks.append(_reg("crates", "libre", "aucune crate Rust"))
    elif body.get("http") == 200:
        checks.append(_reg("crates", "pris", "crate Rust existante", f"https://crates.io/crates/{name}"))
    else:
        checks.append(_reg("crates", "inconnu", _net_note(body)))

    return checks


def check_stores(net: Net, name: str) -> list[dict]:
    checks: list[dict] = []
    query = urllib.parse.quote(name)
    body = net.fetch(
        f"https://itunes.apple.com/search?term={query}&entity=software&limit=25&country=fr"
    )
    if body.get("http") == 200 and isinstance(body.get("json"), dict):
        results = body["json"].get("results", [])
        exact = [
            r
            for r in results
            if tx.slugify(str(r.get("trackName", "")).split(" - ")[0]) == name
            or tx.slugify(str(r.get("trackName", ""))) == name
        ]
        status = "libre" if not exact else "pris"
        if not exact and results:
            status = "ambigu"
        detail = f"{len(results)} app(s) remontent pour '{name}'"
        if exact:
            detail += f", dont {len(exact)} homonyme(s) exact(s): {exact[0].get('trackName')}"
        checks.append(_reg("itunes", status, detail, f"https://apps.apple.com/fr/search?term={query}"))
    else:
        checks.append(_reg("itunes", "inconnu", _net_note(body)))

    checks.append(
        _reg(
            "google_play",
            "manuel",
            "pas d'API publique: vérifier a la main",
            f"https://play.google.com/store/search?q={query}&c=apps",
        )
    )
    checks.append(
        _reg(
            "producthunt",
            "manuel",
            "pas d'API publique sans token",
            f"https://www.producthunt.com/search?q={query}",
        )
    )
    return checks


def _reg(check_id: str, status: str, detail: str, url: str | None = None) -> dict:
    labels = {
        "github_user": "GitHub (compte)",
        "github_repo": "GitHub (repos)",
        "npm": "npm",
        "pypi": "PyPI",
        "crates": "crates.io",
        "itunes": "App Store",
        "google_play": "Google Play",
        "producthunt": "Product Hunt",
    }
    label = labels.get(check_id, check_id)
    return {"id": check_id, "label": label, "status": status, "detail": detail, "url": url}


def _net_note(body: dict) -> str:
    if body.get("blocked"):
        return "quota ou authentification: verification interrompue (reessayer plus tard)"
    code = body.get("http")
    if code == 403:
        return "rate limit API (non authentifie): a rejouer plus tard"
    if code == 401:
        return "authentification refusee: verifier GITHUB_TOKEN"
    if code == 429:
        return "quota depasse: a rejouer plus tard"
    if code is None:
        return f"réseau indisponible ({body.get('error', 'inconnu')})"
    return f"réponse inattendue ({code})"


# --------------------------------------------------------------------------
# Static screening
# --------------------------------------------------------------------------


def static_screen(name: str) -> dict:
    slug = tx.slugify(name)
    hard, soft = tx.bad_word_hits(slug)
    reasons: list[str] = []
    warnings: list[str] = []

    if hard:
        reasons.append(f"mot interdit dans le nom: {', '.join(hard)}")
    generic = tx.has_generic_word(slug)
    if generic:
        reasons.append(f"mot générique non appropriable: '{generic}'")
    if slug in lx.DICTIONARY_NOUNS:
        reasons.append("nom commun de dictionnaire: non distinctif et non deposable tel quel")
    brand = tx.brand_collision(slug)
    if brand:
        reasons.append(f"collision frontale avec la marque '{brand}'")
    if not tx.is_ascii_slug(slug):
        reasons.append("nom non transposable en identifiant ASCII (domaine, paquet, handle)")
    if not (3 <= len(slug) <= 16):
        reasons.append(f"longueur {len(slug)} hors bornes 3-16")
    if tx.max_consonant_run(slug) >= 4:
        reasons.append("amas de 4 consonnes: illisible a l'oral")
    if tx.pronounceability(slug) < 45:
        reasons.append("prononcabilite < 45/100")

    if soft:
        warnings.append(f"substring risquee en FR/EN: {', '.join(soft)}")
    if tx.is_common_first_name(slug):
        warnings.append("prénom courant: dilution SERP et GEO")
    if slug in lx.GENERIC_WORDS:
        warnings.append("dictionnaire: mot commun")
    if len(slug) > 12:
        warnings.append("nom long: coût de frappe et de memorisation")

    return {
        "hard_fail": bool(reasons),
        "hard_fail_reasons": reasons,
        "warnings": warnings,
        "checks": {
            "length": len(slug),
            "syllables": tx.syllable_count(slug),
            "pronounceability": tx.pronounceability(slug),
            "phone_penalty": tx.phone_test_penalty(slug),
            "vowel_ratio": round(tx.vowel_ratio(slug), 2),
            "fr_issues": tx.fr_pronunciation_issues(slug),
            "en_issues": tx.en_pronunciation_issues(slug),
        },
    }


# --------------------------------------------------------------------------
# Query pack for Phase 3 (agent-driven web search)
# --------------------------------------------------------------------------


def serp_pack(name: str, tlds: tuple[str, ...]) -> dict:
    quoted = urllib.parse.quote(f'"{name}"')
    domain = f"{name}.{tlds[0] if tlds else 'com'}"
    google = f"https://www.google.fr/search?q={quoted}"
    return {
        "status": "pending_web_search",
        "queries": [
            f'"{name}"',
            f'"{name}" app',
            f'"{name}" logiciel OR software OR outil',
            f'"{name}" avis OR review',
            f'site:{domain}',
        ],
        "urls": {
            "google": google,
            "google_news": f"https://www.google.fr/search?q={quoted}&tbm=nws",
            "bing": f"https://www.bing.com/search?q={quoted}",
            "duckduckgo": f"https://duckduckgo.com/?q={quoted}",
            "reddit": f"https://www.google.fr/search?q={quoted}+site%3Areddit.com",
            "wikipedia": f"https://fr.wikipedia.org/w/index.php?search={urllib.parse.quote(name)}",
        },
        "acceptance": {
            "serp_virgin": "0-2 résultats organiques hors dictionnaire = SERP vierge",
            "serp_ambiguous": "3-10 résultats sans entité dominante = exploitable",
            "serp_blocked": "entité forte (film, marque, celebrite) sur la 1re page = éliminé",
        },
    }


def trademark_pack(name: str) -> dict:
    return {
        "status": "manual_screen_required",
        "query": name,
        "classes": [9, 42],
        "queries": [
            f'"{name}" marque INPI',
            f'"{name}" trademark EUIPO',
            f'"{name}" trademark USPTO class 9 42',
            f'"{name}" marque logiciel',
        ],
        "urls": {
            "inpi": "https://data.inpi.fr/search?q=" + urllib.parse.quote(name),
            "euipo": "https://euipo.europa.eu/eSearch/#basic/" + urllib.parse.quote(name),
            "uspto": "https://tmsearch.uspto.gov/search/search-information",
            "tmview": "https://www.tmdn.org/tmview/#/tmview/results?page=1&pageSize=30&criteria=C&basicSearch="
            + urllib.parse.quote(name),
            "wipo": "https://branddb.wipo.int/en/similarname?q=" + urllib.parse.quote(name),
        },
        "note": (
            "Aucune API publique gratuite: la classe 9 (logiciels) et 42 (SaaS, services "
            "technologiques) doivent etre verifiees a la main ou par un conseil en PI. "
            "Un pre-filtre automatique (blocklist, générique, prénom) a déjà ete applique."
        ),
    }


# --------------------------------------------------------------------------
# Candidate audit
# --------------------------------------------------------------------------


def audit_candidate(
    candidate: dict,
    net: Net | None,
    tlds: tuple[str, ...],
    offline: bool,
    skip_registries: bool = False,
) -> dict:
    name = candidate["name"]
    base = {
        "name": name,
        "display": candidate.get("display", tx.display_form(name)),
        "archetype": candidate.get("archetype"),
        "archetype_label": candidate.get("archetype_label"),
        "rationale": candidate.get("rationale"),
        "geo_anchor": candidate.get("geo_anchor", []),
        "fidelity": candidate.get("fidelity"),
        "source_language": candidate.get("source_language"),
        "source_phrase": candidate.get("source_phrase"),
        "rule": candidate.get("rule"),
        "rule_label": candidate.get("rule_label"),
        "translations": candidate.get("translations", {}),
        "provenance": candidate.get("provenance", []),
        "static": static_screen(name),
        "domains": [],
        "registries": [],
        "stores": [],
        "serp": serp_pack(name, tlds),
        "trademarks": trademark_pack(name),
        "mode": "static-only" if offline else "network",
    }

    if not offline and net is not None:
        for tld in tlds:
            base["domains"].append(check_domain(net, name, tld))
        if not skip_registries:
            base["registries"] = check_registries(net, name)
            base["stores"] = check_stores(net, name)
        else:
            base["registries"] = [
                _reg(rid, "inconnu", "non vérifie (mode rapide)") for rid in
                ("github_user", "github_repo", "npm", "pypi")
            ]
    else:
        base["domains"] = [
            {
                "tld": tld,
                "domain": f"{name}.{tld}",
                "status": "unknown",
                "confidence": "none",
                "detail": "mode hors ligne: non vérifie",
                "registrar": None,
                "created": None,
                "url": f"https://{name}.{tld}",
            }
            for tld in tlds
        ]
        base["registries"] = [
            _reg(rid, "inconnu", "non vérifie (mode hors ligne)")
            for rid in ("github_user", "github_repo", "npm", "pypi", "crates", "itunes")
        ]

    base["summary"] = summarise(base)
    return base


def summarise(candidate: dict) -> dict:
    domains = candidate["domains"]
    available = [d["tld"] for d in domains if d["status"] == "available"]
    registered = [d["tld"] for d in domains if d["status"] == "registered"]
    unknown = [d["tld"] for d in domains if d["status"] not in {"available", "registered"}]

    free = [r["id"] for r in candidate["registries"] if r["status"] == "libre"]
    taken = [r["id"] for r in candidate["registries"] if r["status"] == "pris"]
    ambig = [r["id"] for r in candidate["registries"] if r["status"] == "ambigu"]

    return {
        "domains_available": available,
        "domains_registered": registered,
        "domains_unknown": unknown,
        "com_available": "com" in available,
        "registries_free": free,
        "registries_taken": taken,
        "registries_ambiguous": ambig,
        "hard_fail": candidate["static"]["hard_fail"],
        "warnings": candidate["static"]["warnings"],
        "needs_web_search": True,
        "needs_trademark_screen": True,
    }


def screen(
    candidates: list[dict],
    cache_dir: str | Path,
    tlds: tuple[str, ...] = ("com", "app", "ai", "io", "fr"),
    offline: bool = False,
    workers: int = 6,
    skip_registries: bool = False,
    timeout: float = 8.0,
) -> dict:
    net = None if offline else Net(cache_dir, timeout=timeout)
    audited: list[dict] = []

    if offline or net is None:
        for candidate in candidates:
            audited.append(audit_candidate(candidate, None, tlds, True, skip_registries))
    else:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(audit_candidate, c, net, tlds, False, skip_registries): c
                for c in candidates
            }
            for future in as_completed(futures):
                audited.append(future.result())

    order = {c["name"]: index for index, c in enumerate(candidates)}
    audited.sort(key=lambda item: order.get(item["name"], 999))

    hard_failed = [a for a in audited if a["static"]["hard_fail"]]
    survivors = [a for a in audited if not a["static"]["hard_fail"]]
    survivors.sort(
        key=lambda a: (
            not a["summary"]["com_available"],
            len(a["summary"]["domains_available"]) * -1,
            len(a["summary"]["registries_taken"]),
            a["name"],
        )
    )

    return {
        "meta": {
            "mode": "static-only" if offline else "network",
            "tlds": list(tlds),
            "audited": len(audited),
            "hard_failed": len(hard_failed),
            "survivors": len(survivors),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "caveats": [
                "RDAP 404 = probablement libre, pas une garantie: confirmer chez le registraire.",
                "Les APIs non authentifiees sont rate-limitees: 'inconnu' n'est pas un feu vert.",
                "SERP, App Store/Play, Product Hunt et marques (INPI/EUIPO/USPTO) exigent la Phase 3.",
            ],
        },
        "candidates": audited,
        "survivors": [s["name"] for s in survivors],
        "hard_failed": [h["name"] for h in hard_failed],
    }
