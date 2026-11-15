"""Phase 5 - executive restitution: markdown, CSV and per-name dossiers."""

from __future__ import annotations

import csv
import time
from pathlib import Path

from . import lexicons as lx
from . import export
from . import score as sc


def _version() -> str:
    from . import __version__

    return __version__


TIER_BADGE = {
    "GREENLIGHT": "GREENLIGHT",
    "FORT": "FORT",
    "CONDITIONNEL": "CONDITIONNEL",
    "ECARTE": "ECARTE",
    "REJETE": "REJETE",
}


def _cell(value: object) -> str:
    text = str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")
    return text or "-"


def _bar(points: float, maximum: float, width: int = 10) -> str:
    if maximum <= 0:
        return "-"
    filled = round((points / maximum) * width)
    return "#" * filled + "." * (width - filled)


def _status_icon(status: str) -> str:
    return {
        "available": "libre",
        "registered": "pris",
        "unknown": "?",
        "libre": "libre",
        "pris": "pris",
        "ambigu": "ambigu",
        "inconnu": "?",
        "manuel": "manuel",
    }.get(status, status)


def comparative_table(ranking: list[dict]) -> list[str]:
    has_fidelity = any(item.get("fidelity") is not None for item in ranking)
    head = "| # | Nom | Archetype |"
    sep = "|---|-----|-----------|"
    if has_fidelity:
        head += " Fidélité |"
        sep += "---------:|"
    head += " Tech /25 | SEO /25 | GEO /25 | Com. /25 | Total /100 | Verdict |"
    sep += "---------:|--------:|--------:|---------:|-----------:|---------|"
    lines = [head, sep]
    for item in ranking:
        row = (
            "| {rank} | **{name}** | {arch} |".format(
                rank=item["rank"],
                name=_cell(item["display"]),
                arch=_cell(item["archetype_label"] or "-"),
            )
        )
        if has_fidelity:
            row += f" {item.get('fidelity') if item.get('fidelity') is not None else '-'} |"
        row += (
            " {tech} | {seo} | {geo} | {com} | **{total}** | {tier} |".format(
                tech=f"{item['pillars']['technique']['score']:.1f}",
                seo=f"{item['pillars']['seo']['score']:.1f}",
                geo=f"{item['pillars']['geo']['score']:.1f}",
                com=f"{item['pillars']['commercial']['score']:.1f}",
                total=f"{item['total']:.1f}",
                tier=TIER_BADGE.get(item["tier"], item["tier"])
                + ("*" if item.get("provisional") else "")
                + ("·m" if item.get("measured") else ""),
            )
        )
        lines.append(row)
    return lines


def provenance_block(score_doc: dict) -> list[str]:
    """LEGO mechanic: which phrase, in which language, produced which name."""
    rows = []
    for item in score_doc["ranking"]:
        if item.get("fidelity") is None:
            continue
        rows.append(
            f"| **{_cell(item['display'])}** | {_cell(item.get('source_language') or '-')} | "
            f"{_cell(item.get('source_phrase') or '-')} | {_cell(item.get('rule') or '-')} | "
            f"{item.get('fidelity')} |"
        )
    if not rows:
        return []
    return [
        "### Mécanique LEGO — provenance des noms",
        "",
        "Chaque nom est la contraction d'une expression traduite. La fidélité (0-100) dit si un "
        "locuteur de la langue source reconnaît encore l'expression dans le nom.",
        "",
        "| Nom | Langue | Expression source | Règle | Fidélité |",
        "|-----|--------|-------------------|-------|---------:|",
        *rows,
        "",
    ]


def pillar_breakdown(item: dict) -> list[str]:
    lines = []
    for pillar_id, pillar in item["pillars"].items():
        config = sc.PILLARS[pillar_id]
        lines.append(f"\n**{config['label']} - {pillar['score']:.1f}/{pillar['max']}**\n")
        lines.append("| Critere | Points | Max | Constat |")
        lines.append("|---------|-------:|----:|---------|")
        for part_id, _label, maximum in config["parts"]:
            part = pillar["parts"].get(part_id, {"score": 0, "max": maximum, "note": ""})
            label = next(lbl for pid, lbl, _ in config["parts"] if pid == part_id)
            lines.append(
                f"| {_cell(label)} | {part['score']:.1f} | {part['max']:.0f} | {_cell(part.get('note', ''))} |"
            )
    return lines


def domain_block(item: dict) -> list[str]:
    lines = ["| TLD | Domaine | Statut | Confiance | Detail |", "|-----|---------|--------|-----------|--------|"]
    for domain in item["domains"]:
        lines.append(
            f"| .{_cell(domain['tld'])} | `{_cell(domain['domain'])}` | {_status_icon(domain['status'])} | "
            f"{_cell(domain.get('confidence', '-'))} | {_cell(domain.get('detail', '-'))} |"
        )
    return lines


def registry_block(item: dict) -> list[str]:
    lines = ["| Check | Statut | Detail | Lien |", "|-------|--------|--------|------|"]
    for registry in item["registries"] + item["stores"]:
        link = f"[ouvrir]({registry['url']})" if registry.get("url") else "-"
        lines.append(
            f"| {_cell(registry['label'])} | {_status_icon(registry['status'])} | "
            f"{_cell(registry['detail'])} | {link} |"
        )
    return lines


def geo_block(item: dict) -> list[str]:
    lines = [
        "| # | Prompt (a exécuter tel quel) | Attendu si le nom passe |",
        "|---|------------------------------|-------------------------|",
    ]
    for index, prompt in enumerate(item["pillars"]["geo"].get("prompt_battery", []), start=1):
        prompt_text = prompt["engine_agnostic"].format(
            name=item["name"],
            need="[besoin du brief]",
            category="[categorie]",
            target="[cible]",
            competitor="[concurrent]",
        )
        lines.append(f"| {index} | {_cell(prompt_text)} | {_cell(prompt.get('expected', prompt.get('pass', '')))} |")
    return lines


def dossier(item: dict, cluster_doc: dict | None = None) -> str:
    lines = [
        f"# {item['display']} ({item['name']})",
        "",
        f"**Score BOM : {item['total']:.1f}/100 — {item['tier']}**",
        "",
        f"- Archetype : {item['archetype_label']}",
        f"- Raison d'etre : {item.get('rationale') or '-'}",
        f"- Ancrage GEO : {', '.join(item.get('geo_anchor') or []) or '-'}",
    ]
    if item["warnings"]:
        lines.append(f"- Alertes : {'; '.join(item['warnings'])}")
    if item["hard_fail"]:
        lines.append(f"- **REJETE** : {'; '.join(item['hard_fail_reasons'])}")
    lines.append("")
    lines.extend(pillar_breakdown(item))
    lines.extend(["", "## Domaines", ""])
    lines.extend(domain_block(item))
    lines.extend(["", "## Registres, stores et handles", ""])
    lines.extend(registry_block(item))
    lines.extend(["", "## Batterie GEO (Phase 3)", ""])
    lines.extend(geo_block(item))
    lines.extend(["", "## Anteriorite marque (Phase 3)", ""])
    lines.append(
        f"Classes 9 (logiciels) et 42 (SaaS). Recherche `{item['name']}` sur : "
        + ", ".join(f"[{name}]({url})" for name, url in item["trademarks"]["urls"].items())
    )
    lines.extend(["", "## Actions immediates", ""])
    for action in item["open_actions"]:
        lines.append(f"- [ ] {action}")
    lines.append("")
    return "\n".join(lines)


def executive_report(
    score_doc: dict,
    audit_doc: dict,
    cluster_doc: dict | None,
    candidates_doc: dict | None,
    out_dir: Path,
    top: int | None = None,
) -> Path:
    ranking = score_doc["ranking"][: top] if top else score_doc["ranking"]
    top_three = ranking[:3]
    survivors = set(audit_doc.get("survivors", []))
    rejected = [c for c in audit_doc["candidates"] if c["name"] not in survivors]

    lines = [
        "# Rapport BOM — Brand, Optimization & Market-readiness",
        "",
        f"Généré le {time.strftime('%d/%m/%Y %H:%M')} — moteur `bom` v{_version()}.",
        "",
    ]

    if cluster_doc:
        meta = cluster_doc["meta"]
        lines.extend(
            [
                "## 1. Corpus et clustering",
                "",
                f"- Mots-cles ingeres : **{meta['total_keywords']}**",
                f"- Clusters couverts : **{meta['clusters_used']}/5**",
                f"- Intentions : {', '.join(f'{k} ({v})' for k, v in cluster_doc['intents'].items())}",
                "",
                "| Cluster | Mots-cles | Part | Racines dominantes |",
                "|---------|----------:|-----:|--------------------|",
            ]
        )
        for cluster_id in lx.CLUSTER_IDS:
            cluster = cluster_doc["clusters"][cluster_id]
            lines.append(
                f"| {_cell(cluster['label'])} | {cluster['count']} | {cluster['share'] * 100:.0f}% | "
                f"{_cell(', '.join(cluster['roots'][:5]) or '-')} |"
            )
        lines.append("")

        brief = (cluster_doc.get("brief") or {}).get("raw", "").strip()
        if brief:
            snippet = " ".join(brief.split())[:600]
            lines.extend(["**Brief produit (extrait)**", "", f"> {snippet}", ""])

    if candidates_doc:
        meta = candidates_doc["meta"]
        engine = meta.get("engine", "archetypes")
        lines.extend(
            [
                "## 2. Generation des candidats",
                "",
                f"- Moteur : **{'mecanique LEGO (contraction multilingue)' if engine == 'lego' else '5 archetypes'}**",
                f"- Candidats produits : **{meta['count']}** (seed {meta['seed']})",
                "- Répartition : "
                + ", ".join(
                    f"{candidates_doc['archetypes'][key]} {value}"
                    for key, value in sorted(meta["distribution"].items())
                ),
            ]
        )
        if engine == "lego":
            lines.append(
                f"- Langues source : {', '.join(meta.get('languages_requested', []))}"
                f" | expressions evaluees : {meta.get('phrases_evaluated', 0)}"
                f" | traducteur : {meta.get('translator', {}).get('provider', '-')}"
            )
        lines.append("")
        lines.extend(provenance_block(score_doc))

    lines.extend(
        [
            "## 3. Tableau comparatif BOM",
            "",
            f"Audit technique en mode **{audit_doc['meta']['mode']}** : "
            f"{audit_doc['meta']['audited']} candidats audites, "
            f"{audit_doc['meta']['hard_failed']} elimines au filtrage dur, "
            f"{audit_doc['meta']['survivors']} survivants.",
            "",
        ]
    )
    lines.extend(comparative_table(ranking))
    measured = [item for item in ranking if item.get("measured")]
    if measured:
        lines.extend(
            [
                "",
                f"`·m` Phase 3 mesuree sur {len(measured)} nom(s) : SERP, stores, marques et batterie GEO "
                "proviennent des sous-agents de recherche, pas d'une extrapolation.",
            ]
        )
    if any(item.get("provisional") for item in ranking):
        lines.extend(
            [
                "",
                "`*` score provisoire : l'audit a tourne hors ligne, les piliers SEO et GEO ne sont pas mesures. "
                "Relancer sans `--offline` avant toute decision.",
            ]
        )
    lines.append("")

    podium = score_doc.get("podium", [])
    if podium:
        lines.extend(["## 4. Podium", ""])
        for item in top_three:
            if item["name"] not in podium:
                continue
            lines.extend(
                [
                    f"### {item['rank']}. {item['display']} — {item['total']:.1f}/100 ({item['tier']})",
                    "",
                    f"{item['verdict']}.",
                    "",
                    f"- Tech {item['pillars']['technique']['score']:.1f}/25 {_bar(item['pillars']['technique']['score'], 25)}",
                    f"- SEO {item['pillars']['seo']['score']:.1f}/25 {_bar(item['pillars']['seo']['score'], 25)}",
                    f"- GEO {item['pillars']['geo']['score']:.1f}/25 {_bar(item['pillars']['geo']['score'], 25)}",
                    f"- Commercial {item['pillars']['commercial']['score']:.1f}/25 {_bar(item['pillars']['commercial']['score'], 25)}",
                    "",
                    f"`.com` : {_status_icon(next((d['status'] for d in item['domains'] if d['tld'] == 'com'), 'unknown'))}"
                    f" ; TLD libres : {', '.join(d['tld'] for d in item['domains'] if d['status'] == 'available') or 'aucun'}",
                    "",
                    "Actions :",
                ]
            )
            for action in item["open_actions"][:6]:
                lines.append(f"- [ ] {action}")
            lines.append("")

    lines.extend(["## 5. Rejets et raisons", ""])
    if rejected:
        lines.append("| Candidat | Motif |")
        lines.append("|----------|-------|")
        for candidate in rejected:
            reasons = candidate["static"]["hard_fail_reasons"] or candidate["static"]["warnings"]
            lines.append(f"| {_cell(candidate['name'])} | {_cell('; '.join(reasons) or 'non retenu')} |")
    else:
        lines.append("Aucun rejet au filtrage dur.")
    lines.append("")

    lines.extend(
        [
            "## 6. Ce qui reste a faire (Phase 3, non automatisable sans API payante)",
            "",
            "1. **SERP** : ouvrir les requetes du pack ci-dessous pour chaque finaliste, compter les "
            "résultats organiques, reperer toute entité dominante (film, marque, celebrite).",
            "2. **Stores** : App Store et Google Play verifies a la main (l'API iTunes ne couvre qu'Apple).",
            "3. **Product Hunt** : rechercher le nom, vérifier un lancement anterieur.",
            "4. **Marques** : recherche INPI, EUIPO, USPTO classes 9 et 42 ; un avis PI humain reste requis.",
            "5. **Prompt battery GEO** : exécuter les 6 prompts sur ChatGPT, Perplexity, Gemini et Claude, "
            "noter la stabilite et l'hallucination.",
            "",
        ]
    )

    finalists = [r for r in ranking if r["tier"] in {"GREENLIGHT", "FORT"}][:3] or ranking[:3]
    for item in finalists:
        lines.extend([f"### Pack de vérification — {item['display']}", "", "**SERP**", ""])
        for query in item["serp"]["queries"]:
            lines.append(f"- `{query}`")
        lines.append("")
        lines.append("**Marques**")
        lines.append("")
        for name, url in item["trademarks"]["urls"].items():
            lines.append(f"- {name} : {url}")
        lines.append("")
        lines.append("**GEO**")
        lines.append("")
        lines.extend(geo_block(item))
        lines.append("")

    lines.extend(
        [
            "## 7. Méthode, poids et limites",
            "",
            "| Pilier | Poids | Ce qu'il mesure |",
            "|--------|------:|-----------------|",
        ]
    )
    for pillar_id, config in sc.PILLARS.items():
        detail = ", ".join(label for _pid, label, _mx in config["parts"])
        lines.append(f"| {_cell(config['label'])} | {config['max']} | {_cell(detail)} |")
    lines.extend(
        [
            "",
            "**Limites a annoncer au client**",
            "",
            "- La disponibilité d'un domaine via RDAP est un signal fort, pas une garantie contractuelle : "
            "le registraire confirme au panier.",
            "- Les APIs GitHub/npm/PyPI/iTunes sont non authentifiees : un statut `?` (rate limit) n'est pas un feu vert.",
            "- Les scores SEO et GEO sont des predictions fondees sur des signaux observables ; seule la Phase 3 "
            "les transforme en mesures.",
            "- Aucune recherche de marque automatisee : INPI/EUIPO/USPTO exigent une vérification humaine.",
            "- Ce rapport ne remplace pas un conseil juridique en propriete intellectuelle.",
            "",
        ]
    )

    if cluster_doc:
        lines.extend(["## 8. Racines a fort volume / intention", ""])
        lines.append("| Racine | Forme source | Freq | Volume | Cluster |")
        lines.append("|--------|--------------|-----:|-------:|---------|")
        for root in cluster_doc["roots"][:20]:
            lines.append(
                f"| `{_cell(root['root'])}` | {_cell(root['phrase'])} | {root['freq']} | "
                f"{root['volume'] or '-'} | {_cell(root['dominant_cluster'])} |"
            )
        lines.append("")

    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "BOM-report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Excel + consolidated JSON: the formats the client actually reuses.
    export.write_xlsx(out_dir / "BOM-names.xlsx", export.build_sheets(score_doc))
    export.write_names_json(
        out_dir / "BOM-names.json", score_doc, audit_doc, cluster_doc, candidates_doc
    )

    csv_path = out_dir / "BOM-scores.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(
            [
                "rank", "name", "display", "archetype", "technique", "seo", "geo",
                "commercial", "total", "tier", "com_available", "tlds_available",
                "registries_taken", "warnings",
            ]
        )
        for item in ranking:
            writer.writerow(
                [
                    item["rank"],
                    item["name"],
                    item["display"],
                    item["archetype"] or "",
                    f"{item['pillars']['technique']['score']:.1f}",
                    f"{item['pillars']['seo']['score']:.1f}",
                    f"{item['pillars']['geo']['score']:.1f}",
                    f"{item['pillars']['commercial']['score']:.1f}",
                    f"{item['total']:.1f}",
                    item["tier"],
                    "yes" if any(d["tld"] == "com" and d["status"] == "available" for d in item["domains"]) else "no",
                    "|".join(d["tld"] for d in item["domains"] if d["status"] == "available"),
                    "|".join(r["id"] for r in item["registries"] if r["status"] == "pris"),
                    "|".join(item["warnings"]),
                ]
            )

    dossier_dir = out_dir / "dossiers"
    dossier_dir.mkdir(parents=True, exist_ok=True)
    for item in ranking[:5]:
        (dossier_dir / f"{item['name']}.md").write_text(dossier(item, cluster_doc), encoding="utf-8")

    return report_path


def quick_answer(score_doc: dict) -> str:
    """Short console summary printed by the CLI."""
    ranking = score_doc["ranking"]
    lines = ["", "=== BOM — resultat ===", ""]
    lines.append(f"{'#':>2}  {'Nom':<14} {'Tech':>5} {'SEO':>5} {'GEO':>5} {'Com':>5} {'Total':>6}  Verdict")
    for item in ranking[:10]:
        lines.append(
            f"{item['rank']:>2}  {item['display']:<14} "
            f"{item['pillars']['technique']['score']:>5.1f} "
            f"{item['pillars']['seo']['score']:>5.1f} "
            f"{item['pillars']['geo']['score']:>5.1f} "
            f"{item['pillars']['commercial']['score']:>5.1f} "
            f"{item['total']:>6.1f}  {item['tier']}{'*' if item.get('provisional') else ''}"
        )
    lines.append("")
    if any(item.get("provisional") for item in ranking[:10]):
        lines.append("* score provisoire (audit hors ligne): SEO et GEO non mesures.")
    if score_doc["podium"]:
        lines.append(f"Podium: {', '.join(score_doc['podium'])}")
    lines.append("Prochaine etape obligatoire: Phase 3 (SERP, stores, INPI/EUIPO/USPTO, prompt battery).")
    return "\n".join(lines)
