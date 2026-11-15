"""Phase 4 - the BOM score (100 points, four pillars of 25).

Scoring is evidence-driven: every point awarded or lost is written into an
`evidence` list so the executive report can defend or contest it. GEO points
are *predictions* from name morphology plus entity-collision facts; the
Phase 3 prompt battery is what turns them into observations.
"""

from __future__ import annotations

import re

from . import lexicons as lx
from . import text as tx

PILLARS: dict[str, dict] = {
    "technique": {
        "label": "Disponibilité technique & handles",
        "max": 25,
        "parts": [
            ("com", "Domaine .com", 7),
            ("tlds", "TLD secondaires (.ai/.app/.io/.fr)", 4),
            ("registries", "Registres de code & handles", 6),
            ("spellability", "Resistance aux fautes de frappe", 4),
            ("clearance", "Pre-filtre de clearance marque", 4),
        ],
    },
    "seo": {
        "label": "Note SEO classique",
        "max": 25,
        "parts": [
            ("virginity", "Virginité SERP", 8),
            ("rankability", "Facilité a ranker #1 sur la marque", 7),
            ("intent", "Intention de recherche alignee", 5),
            ("longtail", "Potentiel longue traine", 3),
            ("snippet", "Snippet & sitelinks", 2),
        ],
    },
    "geo": {
        "label": "Note GEO / moteurs IA",
        "max": 25,
        "parts": [
            ("collision", "Absence de collision avec des entités connues des LLM", 9),
            ("transparency", "Ancrage sémantique immediat", 7),
            ("hallucination", "Risque d'hallucination / d'attribution", 5),
            ("stability", "Stabilite sur ChatGPT, Perplexity, Gemini, Claude", 4),
        ],
    },
    "commercial": {
        "label": "Potentiel commercial & branding",
        "max": 25,
        "parts": [
            ("phone", "Test du téléphone", 3),
            ("fr", "Prononciation FR", 3),
            ("en", "Prononciation EN", 3),
            ("length", "Longueur", 4),
            ("memory", "Memorabilite", 4),
            ("extensible", "Extensibilite de gamme", 3),
            ("logo", "Potentiel de marque visuelle", 2),
            ("fit", "Fit positionnement / brief", 3),
        ],
    },
}

# Tokens that tell a language model "this is a software product" without
# any context. Their presence is the core of the GEO transparency score.
CATEGORY_TOKENS: set[str] = {
    "app", "ai", "seo", "geo", "scan", "rank", "lens", "deck", "kit",
    "lab", "flow", "map", "list", "board", "pilot", "meter", "signal",
    "stack", "ops", "craft", "build", "grow", "track", "suite", "hub",
    "base", "data", "cloud", "agent", "prompt", "search", "find", "sort",
    "sync", "link", "bridge", "loop", "peak", "nest", "forge", "scope",
    "wise", "rank", "radar", "watch", "guard", "vault", "atlas", "quill",
}

PROMPT_BATTERY: tuple[dict[str, str], ...] = (
    {
        "id": "category",
        "engine_agnostic": "Sans contexte, que fait l'application {name} ?",
        "pass": "l'IA devine la categorie (outil SEO, gestion, analyse...)",
        "fail": "l'IA dit ne pas connaitre, ou invente un autre secteur",
    },
    {
        "id": "discovery",
        "engine_agnostic": "Quelles sont les meilleures applications pour {need} ?",
        "pass": "{name} apparait dans une liste longue (5-10) si le nom est connu",
        "fail": "{name} est absent ou remplace par un concurrent etabli",
    },
    {
        "id": "disambiguation",
        "engine_agnostic": "{name}, est-ce la marque logiciel ou l'autre entité homonyme ?",
        "pass": "l'IA separe correctement la marque logiciel de l'homonyme",
        "fail": "l'IA melange les deux entités ou refuse de trancher",
    },
    {
        "id": "recommendation",
        "engine_agnostic": "Recommande un outil {category} pour {target}.",
        "pass": "{name} peut etre cite sans risque d'attribution erronee",
        "fail": "l'IA cite un homonyme ou attribue des faits faux",
    },
    {
        "id": "hallucination_trap",
        "engine_agnostic": "Donne-moi le prix et le fondateur de {name}.",
        "pass": "l'IA dit qu'elle ne sait pas / renvoie au site officiel",
        "fail": "l'IA invente un prix, un fondateur ou une date",
    },
    {
        "id": "entity_resolution",
        "engine_agnostic": "Explique la difference entre {name} et {competitor}.",
        "pass": "les deux entités restent distinctes",
        "fail": "fusion, confusion ou negation de l'existence de la marque",
    },
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _find(audit: dict, check_id: str) -> dict:
    for item in audit.get("registries", []):
        if item["id"] == check_id:
            return item
    return {"id": check_id, "status": "inconnu", "detail": "non vérifie"}


def _domain(audit: dict, tld: str) -> dict:
    for item in audit.get("domains", []):
        if item["tld"] == tld:
            return item
    return {"tld": tld, "status": "unknown"}


def _collision_facts(audit: dict) -> dict:
    """Everything the open web already knows about this exact string."""
    github_user = _find(audit, "github_user")
    github_repo = _find(audit, "github_repo")
    npm = _find(audit, "npm")
    pypi = _find(audit, "pypi")
    itunes = _find(audit, "itunes")
    name = audit["name"]

    facts = {
        "github_user": github_user["status"] == "pris",
        "github_repo": github_repo["status"] == "pris",
        "github_repo_ambiguous": github_repo["status"] == "ambigu",
        "npm": npm["status"] == "pris",
        "pypi": pypi["status"] == "pris",
        "app_store": itunes["status"] == "pris",
        "dictionary": name in lx.GENERIC_WORDS,
        "first_name": tx.is_common_first_name(name),
        "brand": tx.brand_collision(name) is not None,
        "soft_meaning": bool(audit["static"].get("warnings"))
        and any("substring" in w for w in audit["static"].get("warnings", [])),
    }
    facts["exact_collisions"] = sum(
        1
        for key in ("github_user", "github_repo", "npm", "pypi", "app_store")
        if facts[key]
    )
    return facts


def score_technique(audit: dict) -> tuple[dict, list[str]]:
    evidence: list[str] = []
    parts: dict[str, dict] = {}
    maxes = {pid: mx for pid, _label, mx in PILLARS["technique"]["parts"]}

    com = _domain(audit, "com")
    if com["status"] == "available":
        com_score, note = maxes["com"], ".com libre (RDAP) : actif principal disponible"
    elif com["status"] == "registered":
        com_score, note = 0.0, ".com déjà enregistre : coût de rachat ou repli TLD impose"
    else:
        com_score, note = round(maxes["com"] * 0.45, 2), ".com non confirme : risque a lever manuellement"
    parts["com"] = {"score": com_score, "max": maxes["com"], "note": note}
    evidence.append(f"{note} ({com['domain']})")

    secondary = [t for t in ("ai", "app", "io", "fr") if _domain(audit, t)["status"] == "available"]
    unknown_secondary = [t for t in ("ai", "app", "io", "fr") if _domain(audit, t)["status"] == "unknown"]
    tld_score = _clamp(len(secondary) / 3.0) * maxes["tlds"]
    tld_score += min(len(unknown_secondary) * 0.3, 0.9)
    tld_score = round(min(tld_score, maxes["tlds"]), 2)
    parts["tlds"] = {
        "score": tld_score,
        "max": maxes["tlds"],
        "note": f"{len(secondary)} TLD secondaire(s) libre(s): {', '.join(secondary) or 'aucun'}",
    }
    evidence.append(parts["tlds"]["note"])

    github_user = _find(audit, "github_user")
    github_repo = _find(audit, "github_repo")
    npm = _find(audit, "npm")
    pypi = _find(audit, "pypi")
    reg_score = 0.0
    reg_score += 2.0 if github_user["status"] == "libre" else (0.8 if github_user["status"] == "inconnu" else 0.0)
    reg_score += 1.5 if npm["status"] == "libre" else (0.6 if npm["status"] == "inconnu" else 0.0)
    reg_score += 1.5 if pypi["status"] == "libre" else (0.6 if pypi["status"] == "inconnu" else 0.0)
    reg_score += 1.0 if github_repo["status"] == "libre" else (0.3 if github_repo["status"] == "inconnu" else 0.0)
    free = [c["id"] for c in (github_user, npm, pypi) if c["status"] == "libre"]
    parts["registries"] = {
        "score": round(min(reg_score, maxes["registries"]), 2),
        "max": maxes["registries"],
        "note": f"identifiants libres: {', '.join(free) or 'aucun'}",
    }
    evidence.append(parts["registries"]["note"])

    checks = audit["static"]["checks"]
    spell = 4.0
    spell -= min(checks["phone_penalty"], 6) * 0.35
    spell -= max(0, 10 - checks["pronounceability"]) * 0.08
    spell = round(_clamp(spell / 4.0) * maxes["spellability"], 2)
    parts["spellability"] = {
        "score": spell,
        "max": maxes["spellability"],
        "note": f"pénalité téléphone {checks['phone_penalty']}, prononcabilite {checks['pronounceability']}/100",
    }
    evidence.append(parts["spellability"]["note"])

    clearance = 4.0
    if audit["name"] in lx.GENERIC_WORDS:
        clearance -= 3.0
    if tx.is_common_first_name(audit["name"]):
        clearance -= 1.8
    if tx.brand_collision(audit["name"]):
        clearance -= 4.0
    if checks["length"] <= 4:
        clearance -= 0.6
    clearance = round(_clamp(clearance / 4.0) * maxes["clearance"], 2)
    parts["clearance"] = {
        "score": clearance,
        "max": maxes["clearance"],
        "note": "pre-filtre blocklist / générique / prénom (vérification INPI-EUIPO-USPTO en Phase 3)",
    }
    evidence.append(parts["clearance"]["note"])

    return {
        "score": round(sum(p["score"] for p in parts.values()), 2),
        "max": PILLARS["technique"]["max"],
        "parts": parts,
    }, evidence


def score_seo(
    audit: dict,
    clusters: dict | None,
    research: dict | None = None,
    facts: dict | None = None,
) -> tuple[dict, list[str]]:
    evidence: list[str] = []
    parts: dict[str, dict] = {}
    maxes = {pid: mx for pid, _label, mx in PILLARS["seo"]["parts"]}
    facts = facts or _collision_facts(audit)
    name = audit["name"]
    checks = audit["static"]["checks"]

    collisions = facts["exact_collisions"]
    if facts["dictionary"]:
        virginity = 0.0
        note = "mot de dictionnaire: la requete exacte est déjà saturee par le sens commun"
    elif collisions == 0:
        virginity = maxes["virginity"]
        note = "aucun homonyme exact détecté sur GitHub/npm/PyPI/App Store: SERP probablement vierge"
    elif collisions == 1:
        virginity = maxes["virginity"] * 0.7
        note = "1 homonyme exact: SERP a vérifier, position #1 atteignable avec du contenu"
    elif collisions == 2:
        virginity = maxes["virginity"] * 0.45
        note = "2 homonymes exacts: #1 exigera un travail editorial"
    else:
        virginity = maxes["virginity"] * 0.2
        note = f"{collisions} homonymes exacts: requete exacte non appropriable"
    parts["virginity"] = {"score": round(virginity, 2), "max": maxes["virginity"], "note": note}
    evidence.append(note)

    # Phase 3 measurement overrides the API proxy when it exists.
    serp = (research or {}).get("serp", {})
    serp_verdict = serp.get("verdict")
    if serp_verdict in {"virgin", "ambiguous", "blocked"}:
        measured = {
            "virgin": maxes["virginity"],
            "ambiguous": round(maxes["virginity"] * 0.56, 2),
            "blocked": 0.0,
        }[serp_verdict]
        parts["virginity"]["score"] = measured
        parts["virginity"]["note"] = (
            f"mesure Phase 3 : SERP {serp_verdict} "
            f"({serp.get('organic_results', '?')} resultats organiques)"
            + (f", entite dominante: {serp['dominant_entity']}" if serp.get("dominant_entity") else "")
        )
        parts["virginity"]["measured"] = True
        evidence.append(parts["virginity"]["note"])

    rankability = maxes["rankability"]
    rankability -= 3.0 if facts["dictionary"] else 0.0
    rankability -= 2.0 if facts["first_name"] else 0.0
    rankability -= 1.0 * min(collisions, 2)
    rankability += 0.8 if name not in lx.GENERIC_WORDS and len(name) >= 6 else 0.0
    rankability = round(_clamp(rankability / maxes["rankability"]) * maxes["rankability"], 2)
    parts["rankability"] = {
        "score": rankability,
        "max": maxes["rankability"],
        "note": (
            "mot inventé ou compose distinctif: la marque peut posseder sa requete"
            if rankability >= 18
            else "distinction moyenne: la marque partage sa requete avec un sens commun"
        ),
    }
    evidence.append(parts["rankability"]["note"])

    clusters = clusters or {}
    root_vocab: set[str] = set()
    cluster_vocab: dict[str, str] = {}
    for root in clusters.get("roots", [])[:60]:
        root_vocab.add(root["root"])
        cluster_vocab[root["root"]] = root.get("dominant_cluster", "")
    anchors = [tx.slugify(a) for a in audit.get("geo_anchor", [])]
    hits = [a for a in anchors if a in root_vocab]
    intent = maxes["intent"] * (0.55 + 0.45 * _clamp(len(hits) / 2))
    if not root_vocab:
        intent = maxes["intent"] * 0.5
    if facts["dictionary"]:
        intent *= 0.5
    parts["intent"] = {
        "score": round(intent, 2),
        "max": maxes["intent"],
        "note": (
            f"ancrage sur {len(hits)} racine(s) a volume du corpus: {', '.join(hits[:3])}"
            if hits
            else "aucune racine a volume dans le nom: la marque devra creer sa demande"
        ),
    }
    evidence.append(parts["intent"]["note"])

    longtail = 3.0 if any(token in CATEGORY_TOKENS for token in anchors) else 1.2
    if facts["dictionary"]:
        longtail -= 0.8
    longtail = round(_clamp(longtail / 3.0) * maxes["longtail"], 2)
    parts["longtail"] = {
        "score": longtail,
        "max": maxes["longtail"],
        "note": "le morphème de categorie permet des requetes 'nom + metier' naturelles",
    }
    evidence.append(parts["longtail"]["note"])

    snippet = 2.0 - (0.8 if checks["length"] > 12 else 0.0) - (0.7 if facts["first_name"] else 0.0)
    snippet = round(_clamp(snippet / 2.0) * maxes["snippet"], 2)
    parts["snippet"] = {
        "score": snippet,
        "max": maxes["snippet"],
        "note": "titre de 60 caracteres et sitelinks possibles sans conflit de knowledge panel",
    }
    evidence.append(parts["snippet"]["note"])

    return {
        "score": round(sum(p["score"] for p in parts.values()), 2),
        "max": PILLARS["seo"]["max"],
        "parts": parts,
    }, evidence


def score_geo(audit: dict, research: dict | None = None, facts: dict | None = None) -> tuple[dict, list[str]]:
    evidence: list[str] = []
    parts: dict[str, dict] = {}
    maxes = {pid: mx for pid, _label, mx in PILLARS["geo"]["parts"]}
    facts = facts or _collision_facts(audit)
    name = audit["name"]

    penalty = 0.0
    penalty += 3.0 if facts["brand"] else 0.0
    penalty += 2.0 if facts["github_user"] else 0.0
    penalty += 1.5 if facts["npm"] else 0.0
    penalty += 1.5 if facts["pypi"] else 0.0
    penalty += 2.5 if facts["app_store"] else 0.0
    penalty += 2.5 if facts["dictionary"] else 0.0
    penalty += 1.5 if facts["first_name"] else 0.0
    penalty += 1.0 if facts["github_repo"] else 0.0
    collision = _clamp(1 - penalty / 14.0) * maxes["collision"]
    parts["collision"] = {
        "score": round(collision, 2),
        "max": maxes["collision"],
        "note": (
            f"{facts['exact_collisions']} homonyme(s) exact(s) connu(s) des bases publiques"
            + (" + mot de dictionnaire" if facts["dictionary"] else "")
            + (" + prénom courant" if facts["first_name"] else "")
        ),
    }
    evidence.append(parts["collision"]["note"])

    tokens_in_name = {t for t in CATEGORY_TOKENS if re.search(rf"{re.escape(t)}", name)}
    transparency = 3.0 + 1.2 * len(tokens_in_name)
    if not audit.get("geo_anchor"):
        transparency -= 1.5
    transparency = round(_clamp(transparency / 7.0) * maxes["transparency"], 2)
    parts["transparency"] = {
        "score": transparency,
        "max": maxes["transparency"],
        "note": (
            f"morphemes de categorie detectes: {', '.join(sorted(tokens_in_name)) or 'aucun'}"
            f" — un LLM peut {'deviner' if tokens_in_name else 'ne pas deviner'} le secteur sans contexte"
        ),
    }
    evidence.append(parts["transparency"]["note"])

    hallucination = 5.0
    hallucination -= 1.4 * min(facts["exact_collisions"], 3)
    hallucination -= 1.5 if facts["dictionary"] else 0.0
    hallucination -= 1.0 if facts["first_name"] else 0.0
    hallucination += 0.8 if audit.get("geo_anchor") else 0.0
    hallucination = round(_clamp(hallucination / 5.0) * maxes["hallucination"], 2)
    parts["hallucination"] = {
        "score": hallucination,
        "max": maxes["hallucination"],
        "note": (
            "peu de prise pour une attribution erronee"
            if hallucination >= 3.5
            else "risque eleve: l'IA peut attribuer des faits d'un homonyme a la marque"
        ),
    }
    evidence.append(parts["hallucination"]["note"])

    # Phase 3 prompt battery: the only real GEO measurement available.
    geo_measure = (research or {}).get("geo", {})
    fails = geo_measure.get("fails")
    if isinstance(fails, int):
        factor = 1.0 if fails <= 2 else (0.75 if fails <= 6 else (0.5 if fails <= 12 else 0.2))
        parts["collision"]["score"] = round(parts["collision"]["score"] * factor, 2)
        parts["collision"]["note"] += (
            f" | mesure Phase 3 : {fails} echec(s) sur 24 cellules "
            f"({geo_measure.get('hedges', '?')} hesitations)"
        )
        parts["collision"]["measured"] = True
        evidence.append(parts["collision"]["note"])

    stability = (collision / maxes["collision"]) * 1.6 + (transparency / maxes["transparency"]) * 2.0
    stability += 0.4 if facts["exact_collisions"] == 0 else 0.0
    stability = round(_clamp(stability / 4.0) * maxes["stability"], 2)
    parts["stability"] = {
        "score": stability,
        "max": maxes["stability"],
        "note": "stabilite attendue entre ChatGPT, Perplexity, Gemini et Claude (a confirmer par le prompt battery)",
    }
    evidence.append(parts["stability"]["note"])

    return {
        "score": round(sum(p["score"] for p in parts.values()), 2),
        "max": PILLARS["geo"]["max"],
        "parts": parts,
        "prompt_battery": [
            {
                **prompt,
                "status": "a_exécuter_en_phase_3",
                "expected": prompt["pass"] if collision >= 5 else prompt["pass"] + " / risque:" + prompt["fail"],
            }
            for prompt in PROMPT_BATTERY
        ],
    }, evidence


def score_commercial(audit: dict, brief_tokens: list[str] | None = None) -> tuple[dict, list[str]]:
    evidence: list[str] = []
    parts: dict[str, dict] = {}
    maxes = {pid: mx for pid, _label, mx in PILLARS["commercial"]["parts"]}
    name = audit["name"]
    checks = audit["static"]["checks"]
    brief_tokens = brief_tokens or []

    phone = 3.0 - min(checks["phone_penalty"], 9) * 0.3
    parts["phone"] = {
        "score": round(_clamp(phone / 3.0) * maxes["phone"], 2),
        "max": maxes["phone"],
        "note": f"pénalité de dictee {checks['phone_penalty']} (B/P, D/T, M/N, lettres a epeler)",
    }
    evidence.append(parts["phone"]["note"])

    fr_issues = checks.get("fr_issues", [])
    fr = 3.0 - 0.7 * len(fr_issues)
    parts["fr"] = {
        "score": round(_clamp(fr / 3.0) * maxes["fr"], 2),
        "max": maxes["fr"],
        "note": "; ".join(fr_issues) if fr_issues else "aucun piege de lecture en francais",
    }
    evidence.append(parts["fr"]["note"])

    en_issues = checks.get("en_issues", [])
    en = 3.0 - 0.8 * len(en_issues)
    parts["en"] = {
        "score": round(_clamp(en / 3.0) * maxes["en"], 2),
        "max": maxes["en"],
        "note": "; ".join(en_issues) if en_issues else "prononciation anglaise naturelle",
    }
    evidence.append(parts["en"]["note"])

    length = checks["length"]
    if length <= 7:
        length_score = 4.0
    elif length <= 9:
        length_score = 3.4
    elif length <= 11:
        length_score = 2.2
    elif length <= 13:
        length_score = 1.2
    else:
        length_score = 0.4
    parts["length"] = {
        "score": round(length_score, 2),
        "max": maxes["length"],
        "note": f"{length} caracteres, {checks['syllables']} syllabe(s)",
    }
    evidence.append(parts["length"]["note"])

    memory = 2.0
    if not tx.is_common_first_name(name):
        memory += 0.8
    if name not in lx.GENERIC_WORDS:
        memory += 0.8
    if len(set(name)) / max(len(name), 1) > 0.65:
        memory += 0.4
    if len(name) > 11:
        memory -= 0.6
    parts["memory"] = {
        "score": round(_clamp(memory / 4.0) * maxes["memory"], 2),
        "max": maxes["memory"],
        "note": "forme sonore distinctive, faible charge de rappel",
    }
    evidence.append(parts["memory"]["note"])

    extensible = 2.2
    if checks["length"] <= 9:
        extensible += 0.6
    if audit.get("geo_anchor"):
        extensible += 0.4
    if any(t in brief_tokens for t in audit.get("geo_anchor", [])):
        extensible += 0.3
    parts["extensible"] = {
        "score": round(_clamp(extensible / 3.0) * maxes["extensible"], 2),
        "max": maxes["extensible"],
        "note": "peut porter une gamme (app, API, desktop, add-on) sans renommage",
    }
    evidence.append(parts["extensible"]["note"])

    logo = 1.4
    if checks["length"] <= 8:
        logo += 0.4
    if not checks.get("fr_issues"):
        logo += 0.2
    parts["logo"] = {
        "score": round(_clamp(logo / 2.0) * maxes["logo"], 2),
        "max": maxes["logo"],
        "note": "monogramme ou pictogramme possible a partir des 2-3 lettres dominantes",
    }
    evidence.append(parts["logo"]["note"])

    anchors = [tx.slugify(a) for a in audit.get("geo_anchor", [])]
    fit_hits = [a for a in anchors if a in brief_tokens]
    fit = 1.6 + 0.5 * min(len(fit_hits), 2) + (0.4 if audit.get("geo_anchor") else 0.0)
    parts["fit"] = {
        "score": round(_clamp(fit / 3.0) * maxes["fit"], 2),
        "max": maxes["fit"],
        "note": (
            f"aligné sur le brief: {', '.join(fit_hits)}"
            if fit_hits
            else "lien avec le brief indirect: a valider par le positionnement"
        ),
    }
    evidence.append(parts["fit"]["note"])

    return {
        "score": round(sum(p["score"] for p in parts.values()), 2),
        "max": PILLARS["commercial"]["max"],
        "parts": parts,
    }, evidence


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def tier_for(total: float, hard_fail: bool) -> tuple[str, str]:
    if hard_fail:
        return "REJETE", "Filtrage dur: nom non exploitable en l'état"
    if total >= 88:
        return "GREENLIGHT", "A acheter et déposer maintenant"
    if total >= 78:
        return "FORT", "Serieux candidat, lever les 1-2 réserves restantes"
    if total >= 62:
        return "CONDITIONNEL", "Viable si le positionnement justifie les compromis"
    return "ECARTE", "Trop de frictions pour le coût de lancement"


def score_candidate(audit: dict, clusters: dict | None = None, research: dict | None = None) -> dict:
    brief_tokens = []
    if clusters:
        brief_tokens = [tx.slugify(t) for t in clusters.get("brief", {}).get("tokens", [])][:80]

    research_item = (research or {}).get("by_name", {}).get(audit["name"])
    facts = _collision_facts(audit)
    technique, tech_ev = score_technique(audit)
    seo, seo_ev = score_seo(audit, clusters, research_item, facts)
    geo, geo_ev = score_geo(audit, research_item, facts)
    commercial, com_ev = score_commercial(audit, brief_tokens)

    total = round(technique["score"] + seo["score"] + geo["score"] + commercial["score"], 2)
    hard_fail = bool(audit["static"]["hard_fail"])
    tier, verdict = tier_for(total, hard_fail)
    provisional = audit.get("mode") == "static-only"
    measured = bool(research_item and research_item.get("measured"))
    if provisional:
        verdict = verdict + " — score provisoire: audit hors ligne, SEO et GEO ne sont pas mesures"

    # Phase 3 can disqualify outright, whatever the number says.
    if research_item:
        trademark = research_item.get("trademark", {})
        stores_block = research_item.get("stores", {})
        if trademark.get("verdict") == "blocked":
            tier = "REJETE"
            verdict = "Marque identique en classe 9/42 : arret avant toute depense"
            hard_fail = True
        elif trademark.get("verdict") == "risk":
            verdict += " — risque marque a arbitrer par un CPI"
        if stores_block.get("app_store") == "taken" or stores_block.get("play_store") == "taken":
            verdict += " — homonyme deja present en store"

    return {
        "name": audit["name"],
        "display": audit.get("display") or tx.display_form(audit["name"]),
        "archetype": audit.get("archetype"),
        "archetype_label": audit.get("archetype_label"),
        "rationale": audit.get("rationale"),
        "tier": tier,
        "provisional": provisional,
        "measured": measured,
        "research": research_item,
        "verdict": verdict,
        "fidelity": audit.get("fidelity"),
        "source_language": audit.get("source_language"),
        "source_phrase": audit.get("source_phrase"),
        "rule": audit.get("rule"),
        "rule_label": audit.get("rule_label"),
        "translations": audit.get("translations", {}),
        "provenance": audit.get("provenance", []),
        "total": total,
        "max": 100,
        "pillars": {
            "technique": technique,
            "seo": seo,
            "geo": geo,
            "commercial": commercial,
        },
        "evidence": {
            "technique": tech_ev,
            "seo": seo_ev,
            "geo": geo_ev,
            "commercial": com_ev,
        },
        "hard_fail": hard_fail,
        "hard_fail_reasons": audit["static"]["hard_fail_reasons"],
        "warnings": audit["static"]["warnings"],
        "domains": audit["domains"],
        "registries": audit["registries"],
        "stores": audit["stores"],
        "serp": audit["serp"],
        "trademarks": audit["trademarks"],
        "geo_anchor": audit.get("geo_anchor", []),
        "open_actions": build_actions(audit, technique, seo, geo),
    }


def build_actions(audit: dict, technique: dict, seo: dict, geo: dict) -> list[str]:
    actions: list[str] = []
    com = _domain(audit, "com")
    if com["status"] == "available":
        actions.append(f"Réserver {com['domain']} sous 24 h (vérifier le panier avant paiement)")
    elif com["status"] == "registered":
        actions.append(f"{com['domain']} est pris: vérifier le parking/rachat ou basculer sur un TLD secondaire")
    else:
        actions.append(f"Confirmer manuellement {com['domain']} chez un registraire (RDAP muet)")

    secondary = [d["domain"] for d in audit["domains"] if d["status"] == "available" and d["tld"] != "com"]
    if secondary:
        actions.append(f"Prendre aussi {', '.join(secondary[:2])} pour bloquer les derives")

    for registry in audit["registries"]:
        if registry["status"] in {"libre"}:
            actions.append(f"Réserver l'identifiant {registry['label']}")
        elif registry["status"] == "pris":
            actions.append(f"{registry['label']} déjà pris: négocier ou choisir un handle derive")

    if seo["score"] < 15:
        actions.append("SERP chargee: prévoir 3 mois de contenu pour posseder la requete exacte")
    if geo["score"] < 15:
        actions.append("GEO faible: accompagner le nom d'une baseline explicite et d'une fiche entité (Wikidata/schema.org)")

    actions.append(
        f"Recherche d'antériorité INPI/EUIPO/USPTO classes 9 et 42 pour '{audit['name']}' (Phase 3)"
    )
    actions.append(
        f"Exécuter le prompt battery GEO sur ChatGPT, Perplexity, Gemini et Claude pour '{audit['name']}'"
    )
    return actions


def score_all(
    audit_doc: dict,
    clusters: dict | None = None,
    limit: int | None = None,
    research: dict | None = None,
) -> dict:
    candidates = audit_doc["candidates"]
    # Hard-filtered names never enter the ranking, even if the audit document
    # was produced elsewhere and lists everybody as a survivor.
    candidates = [c for c in candidates if not c["static"]["hard_fail"]]
    survivors = set(audit_doc.get("survivors") or [])
    if survivors:
        candidates = [c for c in candidates if c["name"] in survivors]

    scored = [score_candidate(c, clusters, research) for c in candidates]
    scored.sort(key=lambda item: (-item["total"], -(item.get("fidelity") or 0), item["name"]))
    if limit:
        scored = scored[:limit]
    for index, item in enumerate(scored, start=1):
        item["rank"] = index

    greenlight = [s for s in scored if s["tier"] == "GREENLIGHT"]
    strong = [s for s in scored if s["tier"] == "FORT"]

    return {
        "meta": {
            "scored": len(scored),
            "greenlight": len(greenlight),
            "strong": len(strong),
            "measured": sum(1 for item in scored if item.get("measured")),
            "rubric": {key: {"label": value["label"], "max": value["max"]} for key, value in PILLARS.items()},
            "weights": "4 piliers de 25 points: technique, SEO, GEO, commercial",
        },
        "ranking": scored,
        "podium": [s["name"] for s in (greenlight or strong or scored)[:3]],
    }
