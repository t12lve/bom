"""Phase 1 - keyword ingestion, semantic clustering and root extraction.

Input: a raw file (100-500+ keywords, one per line, optionally with a
volume and an intent column), plus an optional product brief.
Output: a `clusters.json` document consumed by `generate` and `score`.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from . import lexicons as lx
from . import text as tx

VOLUME_RE = re.compile(r"^\s*(\d[\d\s.,]*)\s*$")

HEADER_TOKENS: set[str] = {
    "keyword", "keywords", "mot", "mot-cle", "mot cle", "motcle", "requete",
    "query", "queries", "terme", "term", "volume", "vol", "recherches",
    "intent", "intention", "market", "marche", "lang", "langue", "cluster",
    "categorie", "category",
}


def _is_header(cells: list[str]) -> bool:
    """Detect a header row without ever mistaking a keyword for one.

    A header has at least one known column name and no numeric volume in the
    second cell. 'mot-cle,volume' is a header; 'prix juste,1200' is not.
    """
    normalized = [tx.normalize(cell) for cell in cells if cell.strip()]
    if len(cells) < 2 or not normalized:
        return False
    if any(tx.normalize(cell) in HEADER_TOKENS for cell in cells):
        # a real keyword that happens to start with 'mot' is still possible
        if all(not _parse_volume(cell) for cell in cells[1:]):
            return True
    return False


def _parse_volume(raw: str) -> int | None:
    raw = raw.strip()
    if not raw or not VOLUME_RE.match(raw):
        return None
    cleaned = raw.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def load_keywords(path: str | Path) -> list[dict]:
    """Read keywords from txt/csv/md. Tolerates bullets, numbering, extra columns."""
    path = Path(path)
    raw = path.read_text(encoding="utf-8-sig")
    rows: list[dict] = []
    seen: set[str] = set()
    first_row = True
    suffix = path.suffix.lower()
    delimiter = "\t" if suffix == ".tsv" else ("," if suffix in {".csv", ".tsv"} else None)

    for line in raw.splitlines():
        line = line.strip().lstrip("-*•").strip()
        if not line or line.startswith("#"):
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", line):
            continue  # markdown table separator
        cells = [c.strip() for c in line.split(delimiter)] if delimiter else [line]
        if not delimiter and "|" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
        elif not delimiter and re.search(r",\s*\d[\d\s.,]*\s*$", line):
            # "keyword, 1200" pasted into a .txt file
            cells = [c.strip() for c in line.rsplit(",", 1)]
        if first_row and _is_header(cells):
            first_row = False
            continue
        first_row = False
        if not delimiter and cells and cells[0].startswith(("http://", "https://")):
            continue
        keyword = re.sub(r"^\d+[.)]\s*", "", cells[0]).strip()
        keyword = keyword.strip("\"'")
        if not keyword:
            continue
        normalized = tx.normalize(keyword)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        volume = None
        intent = None
        for cell in cells[1:]:
            if volume is None and _parse_volume(cell):
                volume = _parse_volume(cell)
            elif cell.lower() in lx.INTENT_MARKERS:
                intent = cell.lower()
        rows.append(
            {
                "text": keyword,
                "normalized": normalized,
                "volume": volume,
                "declared_intent": intent,
                "tokens": [t for t in tx.tokens(keyword) if t not in lx.STOPWORDS],
            }
        )
    return rows


def _variants(token: str) -> list[str]:
    """Light French/English inflection: plurals only, and only when safe.

    'recettes' must match 'recette', but 'avis' must not become 'avi'. We only
    strip a trailing s/x on words long enough to stay meaningful.
    """
    out = [token]
    if len(token) > 4 and token.endswith("s"):
        out.append(token[:-1])
    if len(token) > 5 and token.endswith("es"):
        out.append(token[:-2])
    if len(token) > 4 and token.endswith("x"):
        out.append(token[:-1])
    return out


def detect_intent(keyword: dict) -> str:
    """Classify search intent from markers, defaulting to informational."""
    words = set(keyword["tokens"]) | set(tx.tokens(keyword["text"]))
    haystack = " " + " ".join(keyword["tokens"]) + " "
    hits: list[str] = []
    for name, markers in lx.INTENT_MARKERS.items():
        for marker in markers:
            if " " in marker:
                if f" {marker} " in haystack:
                    hits.append(name)
                    break
            elif marker in words:
                hits.append(name)
                break
    if keyword.get("declared_intent"):
        return keyword["declared_intent"]
    for priority in ("transactional", "commercial", "navigational", "problem", "informational"):
        if priority in hits:
            return priority
    return "informational"


def cluster_scores(keyword: dict) -> dict[str, float]:
    """Score each of the five clusters for one keyword."""
    words = keyword["tokens"]
    expanded: set[str] = set()
    for token in words:
        expanded.update(_variants(token))
    joined = " " + " ".join(words) + " "
    scores: dict[str, float] = {}
    for cluster in lx.CLUSTER_IDS:
        lexicon = lx.CLUSTER_LEXICONS[cluster]
        hits = 0.0
        for term in lexicon:
            if " " in term:
                if f" {term} " in joined:
                    hits += 1.5
            elif term in expanded:
                hits += 1.0
        scores[cluster] = hits
    return scores


def assign_cluster(keyword: dict) -> dict:
    scores = cluster_scores(keyword)
    best_cluster = max(scores, key=lambda c: (scores[c], -lx.CLUSTER_IDS.index(c)))
    best = scores[best_cluster]
    total = sum(scores.values())
    if best == 0:
        # No lexical match: leave it unclassified, build_clusters() will
        # spread these evenly so the five-cluster map stays readable.
        return {
            "cluster": None,
            "confidence": "none",
            "matched": 0.0,
            "matched_terms": [],
            "scores": scores,
        }
    confidence = "high" if best >= 2.5 else ("medium" if best >= 1.5 else "low")
    matched = [t for t in lx.CLUSTER_LEXICONS[best_cluster] if t in keyword["tokens"]]
    return {
        "cluster": best_cluster,
        "confidence": confidence,
        "matched": best,
        "matched_terms": sorted(matched)[:6],
        "scores": scores,
    }


def extract_roots(keywords: list[dict], limit: int = 40) -> list[dict]:
    """Rank unigrams/bigrams by frequency x specificity x intent value."""
    counts: dict[tuple[str, ...], dict] = {}
    for keyword in keywords:
        grams = tx.keyword_ngrams(keyword["tokens"], sizes=(1, 2))
        for gram, count in grams.items():
            if not gram or len(gram[0]) < 3:
                continue
            entry = counts.setdefault(
                gram, {"count": 0, "volume": 0, "clusters": {}, "intents": set()}
            )
            entry["count"] += count
            entry["volume"] += keyword.get("volume") or 0
            entry["clusters"][keyword["cluster"]] = (
                entry["clusters"].get(keyword["cluster"], 0) + count
            )
            entry["intents"].add(keyword["intent"])

    roots: list[dict] = []
    for gram, entry in counts.items():
        phrase = " ".join(gram)
        slug = tx.slugify(phrase)
        if not (3 <= len(slug) <= 12):
            continue
        if all(word in lx.STOPWORDS for word in gram):
            continue
        if phrase in lx.GENERIC_WORDS:
            continue
        intent_bonus = 0.4 if {"commercial", "transactional"} & entry["intents"] else 0.0
        volume_bonus = min(entry["volume"] / 1000.0, 2.0)
        score = entry["count"] * (1.0 + intent_bonus) + volume_bonus
        roots.append(
            {
                "root": slug,
                "phrase": phrase,
                "freq": entry["count"],
                "volume": entry["volume"],
                "score": round(score, 3),
                "clusters": entry["clusters"],
                "dominant_cluster": max(entry["clusters"], key=entry["clusters"].get),
                "multiword": len(gram) > 1,
            }
        )
    roots.sort(key=lambda r: (-r["score"], -len(r["root"]), r["root"]))
    return roots[:limit]


def build_clusters(rows: list[dict]) -> dict:
    for row in rows:
        payload = assign_cluster(row)
        row["cluster"] = payload["cluster"]
        row["cluster_confidence"] = payload["confidence"]
        row["matched_terms"] = payload.get("matched_terms", [])
        row["intent"] = detect_intent(row)

    unclassified = [row for row in rows if not row["cluster"]]
    for index, row in enumerate(unclassified):
        row["cluster"] = lx.CLUSTER_IDS[index % len(lx.CLUSTER_IDS)]
        row["cluster_confidence"] = "none"

    clusters: dict[str, dict] = {}
    for cluster in lx.CLUSTER_IDS:
        members = [r for r in rows if r["cluster"] == cluster]
        members.sort(key=lambda r: (-(r.get("volume") or 0), -len(r["tokens"]), r["text"]))
        clusters[cluster] = {
            "id": cluster,
            "label": lx.CLUSTER_LABELS[cluster],
            "count": len(members),
            "share": round(len(members) / max(len(rows), 1), 4),
            "keywords": members,
        }

    roots = extract_roots(rows)
    per_cluster_roots: dict[str, list[str]] = {c: [] for c in lx.CLUSTER_IDS}
    for root in roots:
        per_cluster_roots[root["dominant_cluster"]].append(root["root"])
    for cluster, payload in clusters.items():
        own = [r["root"] for r in roots if r["dominant_cluster"] == cluster]
        payload["roots"] = own[:10]

    intents: dict[str, int] = {}
    for row in rows:
        intents[row["intent"]] = intents.get(row["intent"], 0) + 1

    return {
        "meta": {
            "total_keywords": len(rows),
            "clusters_used": len([c for c in lx.CLUSTER_IDS if clusters[c]["count"]]),
            "unclassified": len(unclassified),
            "assigned_by_fallback": len(unclassified),
        },
        "intents": intents,
        "clusters": clusters,
        "roots": roots,
        "per_cluster_roots": per_cluster_roots,
    }


def intake(keywords_path: str, brief_path: str | None, out_path: str) -> dict:
    rows = load_keywords(keywords_path)
    if not rows:
        raise SystemExit(f"[bom] aucun mot-cle lisible dans {keywords_path}")
    document = build_clusters(rows)
    brief = ""
    if brief_path:
        brief = Path(brief_path).read_text(encoding="utf-8")
    document["brief"] = {
        "raw": brief,
        "tokens": [t for t in tx.tokens(brief) if t not in lx.STOPWORDS][:120],
    }
    document["sources"] = {"keywords": str(keywords_path), "brief": brief_path}
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    return document


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, payload: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_keyword_csv(document: dict, path: str) -> None:
    rows = []
    for cluster in lx.CLUSTER_IDS:
        for kw in document["clusters"][cluster]["keywords"]:
            rows.append(
                {
                    "keyword": kw["text"],
                    "cluster": cluster,
                    "confidence": kw["cluster_confidence"],
                    "intent": kw["intent"],
                    "volume": kw.get("volume") or "",
                    "matched": "|".join(kw.get("matched_terms", [])),
                }
            )
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["keyword", "cluster", "confidence", "intent", "volume", "matched"],
        )
        writer.writeheader()
        writer.writerows(rows)
