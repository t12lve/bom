"""Sub-agent orchestration: task packets out, structured evidence back.

The skill does not pretend the main agent can do everything well. Naming is a
reasoning task; checking SERPs, stores and trademarks is a reading task. BOM
therefore splits the work into packets:

  * phase 1 packets  -> "creation" tier (strongest reasoning model)
  * phase 3 packets  -> "research" tier (cheap, fast model, high parallelism)

Nothing is dispatched automatically: every packet carries
`requires_user_approval: true` and the orchestrator must obtain consent, naming
the models and the number of sub-agents, before spawning anything.

The packets are plain JSON so any harness (or a human) can execute them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import lexicons as lx
from . import text as tx

MODEL_TIERS: dict[str, dict] = {
    "creation": {
        "tier": "reasoning-high",
        "why": (
            "generer des noms, arbitrer des compromis phonetiques et semantiques, "
            "refuser les faux bons candidats : tache de jugement, pas de lecture."
        ),
        "guidance": "prendre le modele le plus fort en raisonnement disponible dans le harness",
        "parallelism": "1 a 5 sous-agents, un par cluster",
        "max_output_tokens": 4000,
    },
    "research": {
        "tier": "fast-cheap",
        "why": (
            "lire des resultats de recherche, compter des occurrences, recopier des "
            "numeros de marque : tache mecanique et volumineuse."
        ),
        "guidance": "prendre le modele le plus rapide et le moins cher disponible",
        "parallelism": "1 sous-agent par paquet de 2-3 noms, lances en parallele",
        "max_output_tokens": 1500,
    },
}

RESEARCH_SCHEMA: dict = {
    "phase": "3",
    "agent": "nom-du-sous-agent",
    "generated_at": "YYYY-MM-DDTHH:MM:SS",
    "results": [
        {
            "name": "slug",
            "serp": {
                "verdict": "virgin | ambiguous | blocked | not_checked",
                "organic_results": 0,
                "dominant_entity": None,
                "notes": "une phrase factuelle, datee",
                "sources": ["https://..."],
            },
            "stores": {
                "app_store": "free | taken | ambiguous | manual | not_checked",
                "play_store": "free | taken | ambiguous | manual | not_checked",
                "product_hunt": "free | taken | ambiguous | manual | not_checked",
                "notes": "",
            },
            "trademark": {
                "verdict": "clear | risk | blocked | not_checked",
                "matches": [
                    {"office": "INPI | EUIPO | USPTO", "number": "", "classes": [9, 42],
                     "owner": "", "status": "", "url": ""}
                ],
                "notes": "",
            },
            "geo": {
                "fails": 0,
                "hedges": 0,
                "passes": 6,
                "notes": "",
                "engines": {"chatgpt": "", "perplexity": "", "gemini": "", "claude": ""},
            },
        }
    ],
}

CREATIVE_SCHEMA: dict = {
    "phase": "1",
    "agent": "creative-director",
    "cluster": "benefit",
    "candidates": [
        {
            "name": "slug",
            "display": "Slug",
            "archetype": "descriptive | blend | metaphor | neologism | geo | lego",
            "rationale": "pourquoi ce nom, en une phrase defendable",
            "roots": ["racine"],
            "risk": "la principale faiblesse du nom",
            "fidelity": 0,
        }
    ],
}


# --------------------------------------------------------------------------
# Phase 1 packets: one per cluster, for the strong model
# --------------------------------------------------------------------------


def creative_packets(clusters: dict, out_dir: str | Path) -> list[dict]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    brief = (clusters.get("brief") or {}).get("raw", "")
    payloads: list[dict] = []

    for cluster_id in lx.CLUSTER_IDS:
        cluster = clusters["clusters"][cluster_id]
        if not cluster["count"]:
            continue
        packet = {
            "id": f"bom-p1-{cluster_id}",
            "title": f"Phase 1 - cluster {cluster['label']} ({cluster['count']} mots-cles)",
            "phase": "1",
            "role": "creative-director",
            "model_tier": "creation",
            "model": MODEL_TIERS["creation"],
            "requires_user_approval": True,
            "context": {
                "cluster": cluster["label"],
                "keywords": [kw["text"] for kw in cluster["keywords"][:40]],
                "roots": cluster["roots"][:8],
                "other_clusters": {
                    cid: clusters["clusters"][cid]["roots"][:4] for cid in lx.CLUSTER_IDS
                },
                "brief": " ".join(brief.split())[:1500],
            },
            "instructions": [
                f"Tu es directeur de creation. Produis 8 noms pour le cluster {cluster['label']}.",
                "Interdits: mot de dictionnaire seul, marque connue, prenom courant, plus de 12 lettres.",
                "Chaque nom doit etre prononcable par un francais de 45 ans ET par un acheteur anglais.",
                "Varie les archetypes: descriptif, mot-valise, metaphorique, neologisme <= 7, hybride GEO.",
                "Justifie chaque nom en une phrase; nomme sa faiblesse principale (champ risk).",
                "Ne verifie aucune disponibilite: ce n'est pas ton role, un autre agent le fera.",
                "Reponds uniquement avec le JSON du schema, sans texte autour.",
            ],
            "output_schema": CREATIVE_SCHEMA,
            "acceptance": [
                "8 noms, tous distincts, ASCII, 4-12 caracteres",
                "au moins 3 archetypes differents",
                "aucun nom ne reprend un mot de la blocklist",
            ],
        }
        path = out / f"{packet['id']}.json"
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        packet["file"] = str(path)
        payloads.append(packet)
    return payloads


# --------------------------------------------------------------------------
# Phase 3 packets: batches of candidates, for the cheap model
# --------------------------------------------------------------------------


def research_packets(
    score_doc: dict, batch: int = 3, top: int = 10, out_dir: str | Path = "packets"
) -> list[dict]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ranking = score_doc["ranking"][:top]
    chunks = [ranking[i : i + batch] for i in range(0, len(ranking), batch)]
    payloads: list[dict] = []

    for index, chunk in enumerate(chunks, start=1):
        candidates = []
        for item in chunk:
            candidates.append(
                {
                    "name": item["name"],
                    "display": item["display"],
                    "serp_queries": item["serp"]["queries"],
                    "serp_urls": item["serp"]["urls"],
                    "trademark_urls": item["trademarks"]["urls"],
                    "trademark_classes": item["trademarks"]["classes"],
                    "geo_prompts": [
                        prompt["engine_agnostic"].format(
                            name=item["name"],
                            need="[besoin du brief]",
                            category="[categorie]",
                            target="[cible]",
                            competitor="[concurrent]",
                        )
                        for prompt in item["pillars"]["geo"].get("prompt_battery", [])
                    ],
                    "known": {
                        "com": next(
                            (
                                d["status"]
                                for d in item.get("domains", [])
                                if d["tld"] == "com"
                            ),
                            "unknown",
                        ),
                        "taken_registries": [
                            r["id"] for r in item.get("registries", []) if r["status"] == "pris"
                        ],
                    },
                }
            )

        packet = {
            "id": f"bom-p3-batch-{index}",
            "title": f"Phase 3 - verification SERP/stores/marques/GEO ({', '.join(c['name'] for c in chunk)})",
            "phase": "3",
            "role": "research-analyst",
            "model_tier": "research",
            "model": MODEL_TIERS["research"],
            "requires_user_approval": True,
            "candidates": candidates,
            "instructions": [
                "Pour chaque nom, execute les requetes SERP fournies et note le nombre de resultats organiques.",
                "Qualifie la SERP: virgin (0-2 resultats sans entite dominante), ambiguous (3-10), blocked (entite forte).",
                "Verifie l'App Store, Google Play et Product Hunt: free / taken / ambiguous / manual.",
                "Cherche le nom sur INPI, EUIPO et USPTO en classes 9 et 42; recopie les numeros de marque trouves.",
                "Execute les 6 prompts GEO sur ChatGPT, Perplexity, Gemini et Claude; compte les echecs.",
                "N'invente rien: si une page ne repond pas, ecris not_checked et explique pourquoi.",
                "Cite l'URL de chaque constat. Reponds uniquement avec le JSON du schema.",
            ],
            "output_schema": RESEARCH_SCHEMA,
            "acceptance": [
                "un bloc par nom, meme si tout est not_checked",
                "verdicts uniquement parmi les valeurs autorisees",
                "aucune affirmation sans source ou sans date",
            ],
        }
        path = out / f"{packet['id']}.json"
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False), encoding="utf-8")
        packet["file"] = str(path)
        payloads.append(packet)
    return payloads


# --------------------------------------------------------------------------
# Merge
# --------------------------------------------------------------------------

SERP_VERDICTS = {"virgin", "ambiguous", "blocked", "not_checked"}
STORE_VERDICTS = {"free", "taken", "ambiguous", "manual", "not_checked"}
TM_VERDICTS = {"clear", "risk", "blocked", "not_checked"}


def _normalise(result: dict) -> dict:
    name = tx.slugify(str(result.get("name", "")))
    serp = result.get("serp") or {}
    stores = result.get("stores") or {}
    tm = result.get("trademark") or {}
    geo = result.get("geo") or {}

    serp_verdict = str(serp.get("verdict", "not_checked")).strip().lower()
    tm_verdict = str(tm.get("verdict", "not_checked")).strip().lower()

    return {
        "name": name,
        "serp": {
            "verdict": serp_verdict if serp_verdict in SERP_VERDICTS else "not_checked",
            "organic_results": serp.get("organic_results"),
            "dominant_entity": serp.get("dominant_entity"),
            "notes": serp.get("notes", ""),
            "sources": serp.get("sources", []),
        },
        "stores": {
            key: (
                str(stores.get(key, "not_checked")).strip().lower()
                if str(stores.get(key, "not_checked")).strip().lower() in STORE_VERDICTS
                else "not_checked"
            )
            for key in ("app_store", "play_store", "product_hunt")
        },
        "trademark": {
            "verdict": tm_verdict if tm_verdict in TM_VERDICTS else "not_checked",
            "matches": tm.get("matches", []) or [],
            "notes": tm.get("notes", ""),
        },
        "geo": {
            "fails": geo.get("fails"),
            "hedges": geo.get("hedges"),
            "passes": geo.get("passes"),
            "notes": geo.get("notes", ""),
            "engines": geo.get("engines", {}) or {},
        },
        "measured": any(
            [
                serp_verdict in {"virgin", "ambiguous", "blocked"},
                tm_verdict in {"clear", "risk", "blocked"},
                geo.get("fails") is not None,
                any(
                    stores.get(key) in {"free", "taken", "ambiguous"}
                    for key in ("app_store", "play_store")
                ),
            ]
        ),
    }


def merge_results(paths: list[str]) -> dict:
    by_name: dict[str, dict] = {}
    warnings: list[str] = []
    sources: list[str] = []

    for raw_path in paths:
        path = Path(raw_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"{path.name}: illisible ({exc})")
            continue
        sources.append(str(path))
        results = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(results, list):
            warnings.append(f"{path.name}: pas de tableau 'results'")
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            normalised = _normalise(result)
            if not normalised["name"]:
                warnings.append(f"{path.name}: resultat sans nom ignore")
                continue
            existing = by_name.get(normalised["name"])
            if existing and existing["measured"] and normalised["measured"]:
                warnings.append(
                    f"{normalised['name']}: deux mesures concurrentes, la premiere est conservee"
                )
                continue
            by_name[normalised["name"]] = normalised

    measured = sum(1 for item in by_name.values() if item["measured"])
    missing_tm = [
        name
        for name, item in by_name.items()
        if item["trademark"]["verdict"] == "not_checked"
    ]

    for name in missing_tm[:5]:
        warnings.append(f"{name}: marque non verifiee (classes 9/42)")

    return {
        "meta": {
            "schema": "bom.research/v1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sources": sources,
            "names": len(by_name),
            "measured": measured,
            "unknown": len(by_name) - measured,
            "warnings": warnings,
        },
        "by_name": by_name,
    }


def load_research(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "by_name" not in payload:
        # tolerate a raw merge input file
        return merge_results([str(path)])
    return payload
