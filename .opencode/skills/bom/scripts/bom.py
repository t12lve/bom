#!/usr/bin/env python3
"""BOM CLI — Brand, Optimization & Market-readiness.

    python bom.py run      --keywords keywords.txt --brief brief.md --out-dir runs/acme
    python bom.py intake   --keywords keywords.txt --brief brief.md --out work/clusters.json
    python bom.py generate --clusters work/clusters.json --out work/candidates.json
    python bom.py audit    --candidates work/candidates.json --out work/audit.json
    python bom.py score    --audit work/audit.json --clusters work/clusters.json --out work/scores.json
    python bom.py report   --scores work/scores.json --audit work/audit.json --out reports/
    python bom.py check    --names "rankly,hivelens" --offline

Zero third-party dependencies. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bomlib import __version__  # noqa: E402
from bomlib import audit as audit_mod  # noqa: E402
from bomlib import export as export_mod  # noqa: E402
from bomlib import generate as generate_mod  # noqa: E402
from bomlib import keywords as keywords_mod  # noqa: E402
from bomlib import lego as lego_mod  # noqa: E402
from bomlib import report as report_mod  # noqa: E402
from bomlib import research as research_mod  # noqa: E402
from bomlib import score as score_mod  # noqa: E402
from bomlib import text as tx  # noqa: E402
from bomlib import translate as translate_mod  # noqa: E402


def _load(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"[bom] fichier introuvable: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[bom] JSON invalide dans {path}: {exc}")


def _save(path: str | Path, payload: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[bom] ecrit: {path}")


def _tlds(value: str) -> tuple[str, ...]:
    items = tuple(t.strip().lstrip(".").lower() for t in value.split(",") if t.strip())
    return items or ("com", "app", "ai", "io", "fr")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_intake(args: argparse.Namespace) -> None:
    document = keywords_mod.intake(args.keywords, args.brief, args.out)
    meta = document["meta"]
    print(f"[bom] {meta['total_keywords']} mots-cles, {meta['clusters_used']}/5 clusters")
    for cluster_id in keywords_mod.lx.CLUSTER_IDS:
        cluster = document["clusters"][cluster_id]
        print(f"      {cluster['label']:<22} {cluster['count']:>4}  racines: {', '.join(cluster['roots'][:4]) or '-'}")
    if args.csv:
        keywords_mod.write_keyword_csv(document, args.csv)
        print(f"[bom] ecrit: {args.csv}")


def cmd_generate(args: argparse.Namespace) -> None:
    document = _load(args.clusters)
    result = generate_mod.generate(document, count=args.count, seed=args.seed)
    _save(args.out, result)
    distribution = ", ".join(f"{k}={v}" for k, v in sorted(result["meta"]["distribution"].items()))
    print(f"[bom] {result['meta']['count']} candidats ({distribution})")
    for candidate in result["candidates"]:
        print(f"      {candidate['display']:<14} {candidate['archetype']:<12} {candidate['rationale'][:70]}")


def cmd_audit(args: argparse.Namespace) -> None:
    document = _load(args.candidates)
    result = audit_mod.screen(
        document["candidates"],
        cache_dir=args.cache_dir,
        tlds=_tlds(args.tlds),
        offline=args.offline,
        workers=args.workers,
        skip_registries=args.quick,
        timeout=args.timeout,
    )
    _save(args.out, result)
    print(
        f"[bom] mode={result['meta']['mode']} audites={result['meta']['audited']} "
        f"rejetes={result['meta']['hard_failed']} survivants={result['meta']['survivors']}"
    )
    for name in result["hard_failed"]:
        candidate = next(c for c in result["candidates"] if c["name"] == name)
        print(f"      REJETE {name}: {'; '.join(candidate['static']['hard_fail_reasons'])}")


def cmd_score(args: argparse.Namespace) -> None:
    audit_doc = _load(args.audit)
    clusters = _load(args.clusters) if args.clusters else None
    research = research_mod.load_research(args.research) if args.research else None
    result = score_mod.score_all(audit_doc, clusters, limit=args.limit, research=research)
    _save(args.out, result)
    print(report_mod.quick_answer(result))
    if research:
        print(
            f"[bom] Phase 3 mesuree sur {research['meta']['measured']}/{len(result['ranking'])} noms"
        )


def cmd_dispatch(args: argparse.Namespace) -> None:
    if args.phase == "1":
        clusters = _load(args.clusters) if args.clusters else None
        if not clusters:
            raise SystemExit("[bom] --clusters requis en phase 1")
        packets = research_mod.creative_packets(clusters, args.out)
    else:
        scores = _load(args.scores)
        packets = research_mod.research_packets(
            scores, batch=args.batch, top=args.top, out_dir=args.out
        )
    print(f"[bom] {len(packets)} paquet(s) ecrit(s) dans {args.out}")
    for packet in packets:
        print(f"      {packet['file']} — {packet.get('title', '')}")


def cmd_merge(args: argparse.Namespace) -> None:
    document = research_mod.merge_results(args.inputs)
    _save(args.out, document)
    meta = document["meta"]
    print(
        f"[bom] couverture: {meta['measured']} nom(s) mesures, "
        f"{meta['unknown']} manquant(s), {len(meta['sources'])} fichier(s)"
    )
    for warning in meta["warnings"]:
        print(f"      /!\\ {warning}")


def cmd_report(args: argparse.Namespace) -> None:
    scores = _load(args.scores)
    audit_doc = _load(args.audit)
    clusters = _load(args.clusters) if args.clusters else None
    candidates = _load(args.candidates) if args.candidates else None
    path = report_mod.executive_report(
        scores, audit_doc, clusters, candidates, Path(args.out), top=args.top
    )
    print(f"[bom] rapport: {path}")
    print(f"[bom] CSV    : {Path(args.out) / 'BOM-scores.csv'}")
    print(f"[bom] dossiers: {Path(args.out) / 'dossiers'}")


def cmd_check(args: argparse.Namespace) -> None:
    names = [n.strip() for n in args.names.replace("\n", ",").split(",") if n.strip()]
    if not names:
        raise SystemExit("[bom] --names vide")
    candidates = []
    for name in names:
        slug = tx.slugify(name)
        candidates.append(
            {
                "name": slug,
                "display": tx.display_form(slug),
                "archetype": "adhoc",
                "archetype_label": "Candidat fourni",
                "rationale": "Nom fourni directement par l'utilisateur.",
                "geo_anchor": [slug],
            }
        )
    result = audit_mod.screen(
        candidates,
        cache_dir=args.cache_dir,
        tlds=_tlds(args.tlds),
        offline=args.offline,
        workers=args.workers,
        skip_registries=args.quick,
        timeout=args.timeout,
    )
    _save(args.out, result)
    scored = score_mod.score_all(result, None)
    print(report_mod.quick_answer(scored))


def _pipeline(args: argparse.Namespace, engine: str) -> None:
    """Shared 1->5 pipeline for both generators."""
    out_dir = Path(args.out_dir)
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    print(f"[bom] v{__version__} — pipeline complet ({engine})")
    print("[1/5] ingestion & clustering")
    clusters = keywords_mod.intake(
        args.keywords, args.brief, str(work / "clusters.json")
    )
    print(
        f"      {clusters['meta']['total_keywords']} mots-cles -> "
        f"{clusters['meta']['clusters_used']}/5 clusters"
    )

    print("[2/5] generation")
    if engine == "lego":
        langs, skipped = translate_mod.resolve_languages(
            getattr(args, "langs", None), args.source_lang
        )
        translator = translate_mod.Translator(
            cache_dir=args.cache_dir,
            source_lang=args.source_lang,
            provider=getattr(args, "translator", "mymemory"),
            enabled=not args.offline,
        )
        candidates = lego_mod.generate_lego(
            clusters,
            translator=translator,
            langs=langs,
            source_lang=args.source_lang,
            count=args.count,
            seed=args.seed,
        )
        if skipped:
            print(f"      langues non romanisables ignorees: {', '.join(skipped)}")
        stats = candidates["meta"]["translator"]
        print(
            f"      {candidates['meta']['count']} noms LEGO "
            f"({len(langs)} langues, {candidates['meta']['phrases_evaluated']} expressions, "
            f"api={stats['api_calls']} cache={stats['cache_hits']})"
        )
    else:
        candidates = generate_mod.generate(clusters, count=args.count, seed=args.seed)
        print(f"      {candidates['meta']['count']} candidats")
    _save(work / "candidates.json", candidates)

    print("[3/5] audit technique" + (" (hors ligne)" if args.offline else ""))
    audited = audit_mod.screen(
        candidates["candidates"],
        cache_dir=args.cache_dir,
        tlds=_tlds(args.tlds),
        offline=args.offline,
        workers=args.workers,
        skip_registries=args.quick,
        timeout=args.timeout,
    )
    _save(work / "audit.json", audited)
    print(
        f"      rejetes={audited['meta']['hard_failed']} survivants={audited['meta']['survivors']}"
    )

    print("[4/5] scoring BOM")
    research = None
    if getattr(args, "research", None):
        research = research_mod.load_research(args.research)
        print(
            f"      Phase 3 mesuree: {research['meta']['measured']}/"
            f"{research['meta']['names']} noms"
        )
    scores = score_mod.score_all(audited, clusters, research=research)
    _save(work / "scores.json", scores)
    print(report_mod.quick_answer(scores))

    print("[5/5] restitution")
    report_path = report_mod.executive_report(
        scores, audited, clusters, candidates, out_dir / "report", top=args.top
    )
    print(f"      rapport : {report_path}")
    print(f"      excel   : {out_dir / 'report' / 'BOM-names.xlsx'}")
    print(f"      json    : {out_dir / 'report' / 'BOM-names.json'}")

    _save(
        out_dir / "state.json",
        {
            "version": __version__,
            "engine": engine,
            "keywords": args.keywords,
            "brief": args.brief,
            "tlds": list(_tlds(args.tlds)),
            "offline": args.offline,
            "files": {
                "clusters": str(work / "clusters.json"),
                "candidates": str(work / "candidates.json"),
                "audit": str(work / "audit.json"),
                "scores": str(work / "scores.json"),
                "report": str(report_path),
                "excel": str(out_dir / "report" / "BOM-names.xlsx"),
                "json": str(out_dir / "report" / "BOM-names.json"),
            },
            "next": [
                "Phase 3 - SERP: executer le pack de requetes pour chaque finaliste",
                "Phase 3 - Stores: App Store / Google Play / Product Hunt a la main",
                "Phase 3 - Marques: INPI, EUIPO, USPTO classes 9 et 42",
                "Phase 3 - GEO: prompt battery sur ChatGPT, Perplexity, Gemini, Claude",
            ],
        },
    )
    print("\n[bom] Phase 3 requise avant toute decision finale (SERP, stores, marques, GEO).")


def cmd_run(args: argparse.Namespace) -> None:
    _pipeline(args, getattr(args, "engine", "archetypes"))


def cmd_export(args: argparse.Namespace) -> None:
    """Regenerate Excel + JSON from an existing run (no re-audit)."""
    scores = _load(args.scores)
    audit_doc = _load(args.audit)
    clusters = _load(args.clusters) if args.clusters else None
    candidates = _load(args.candidates) if args.candidates else None
    Path(args.out).mkdir(parents=True, exist_ok=True)
    xlsx = export_mod.write_xlsx(
        Path(args.out) / "BOM-names.xlsx", export_mod.build_sheets(scores)
    )
    js = export_mod.write_names_json(
        Path(args.out) / "BOM-names.json", scores, audit_doc, clusters, candidates
    )
    print(f"[bom] excel: {xlsx}")
    print(f"[bom] json : {js}")


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


def cmd_selftest(args: argparse.Namespace) -> None:
    import selftest as st

    raise SystemExit(st.main())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bom",
        description="BOM — naming commercial: clustering, generation, audit, scoring SEO+GEO.",
    )
    parser.add_argument("--version", action="version", version=f"bom {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def network_args(target: argparse.ArgumentParser, with_translation: bool = False) -> None:
        target.add_argument("--tlds", default="com,app,ai,io,fr", help="TLD a verifier (defaut: com,app,ai,io,fr)")
        target.add_argument("--offline", action="store_true", help="aucun appel reseau (filtrage statique seulement)")
        target.add_argument("--quick", action="store_true", help="domaines seulement, pas de registres de code")
        target.add_argument("--workers", type=int, default=6, help="threads reseau (defaut 6)")
        target.add_argument("--timeout", type=float, default=8.0, help="timeout HTTP en secondes")
        target.add_argument("--cache-dir", default=".bom-cache", help="repertoire de cache HTTP")
        if with_translation:
            target.add_argument("--langs", default=None, help="langues cibles, ex: fr,en,es,de,da")
            target.add_argument("--source-lang", default="fr", help="langue du corpus (defaut fr)")
            target.add_argument(
                "--translator",
                choices=("mymemory", "offline"),
                default="mymemory",
                help="fournisseur de traduction (defaut mymemory, sans cle)",
            )
        target.add_argument("--out", default="audit.json", help="fichier de sortie")

    intake = sub.add_parser("intake", help="Phase 1: ingestion et clustering")
    intake.add_argument("--keywords", required=True)
    intake.add_argument("--brief", default=None)
    intake.add_argument("--out", default="clusters.json")
    intake.add_argument("--csv", default=None)
    intake.set_defaults(func=cmd_intake)

    gen = sub.add_parser("generate", help="Phase 1b: 30 candidats sur 5 archetypes")
    gen.add_argument("--clusters", required=True)
    gen.add_argument("--count", type=int, default=30)
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--out", default="candidates.json")
    gen.set_defaults(func=cmd_generate)

    aud = sub.add_parser("audit", help="Phase 2: audit technique automatise")
    aud.add_argument("--candidates", required=True)
    network_args(aud)
    aud.set_defaults(func=cmd_audit)

    leg = sub.add_parser("lego", help="Phase 1b (LEGO): contraction multilingue d'expressions")
    leg.add_argument("--keywords", required=True)
    leg.add_argument("--brief", default=None)
    leg.add_argument("--out-dir", default="runs/lego")
    leg.add_argument("--count", type=int, default=30)
    leg.add_argument("--seed", type=int, default=7)
    leg.add_argument("--top", type=int, default=10)
    network_args(leg, with_translation=True)
    leg.set_defaults(func=lambda args: _pipeline(args, "lego"))

    disp = sub.add_parser("dispatch", help="genere les paquets de taches pour les sous-agents")
    disp.add_argument("--scores", default=None, help="scores.json (phase 3)")
    disp.add_argument("--clusters", default=None, help="clusters.json (phase 1)")
    disp.add_argument("--audit", default=None)
    disp.add_argument("--phase", choices=("1", "3"), default="3")
    disp.add_argument("--top", type=int, default=10)
    disp.add_argument("--batch", type=int, default=3, help="candidats par paquet de recherche")
    disp.add_argument("--out", default="packets")
    disp.set_defaults(func=cmd_dispatch)

    mrg = sub.add_parser("merge", help="fusionne les resultats des sous-agents de recherche")
    mrg.add_argument("--inputs", nargs="+", required=True, help="fichiers JSON rendus par les sous-agents")
    mrg.add_argument("--out", default="research.json")
    mrg.set_defaults(func=cmd_merge)

    exp = sub.add_parser("export", help="regenerer Excel + JSON depuis un run existant")
    exp.add_argument("--scores", required=True)
    exp.add_argument("--audit", required=True)
    exp.add_argument("--clusters", default=None)
    exp.add_argument("--candidates", default=None)
    exp.add_argument("--out", default="export")
    exp.set_defaults(func=cmd_export)

    sco = sub.add_parser("score", help="Phase 4: scoring BOM sur 100")
    sco.add_argument("--audit", required=True)
    sco.add_argument("--clusters", default=None)
    sco.add_argument("--research", default=None, help="research.json issu du merge (Phase 3 mesuree)")
    sco.add_argument("--limit", type=int, default=None)
    sco.add_argument("--out", default="scores.json")
    sco.set_defaults(func=cmd_score)

    rep = sub.add_parser("report", help="Phase 5: restitution executive")
    rep.add_argument("--scores", required=True)
    rep.add_argument("--audit", required=True)
    rep.add_argument("--clusters", default=None)
    rep.add_argument("--candidates", default=None)
    rep.add_argument("--top", type=int, default=10, help="lignes du tableau comparatif (defaut 10)")
    rep.add_argument("--out", default="report")
    rep.set_defaults(func=cmd_report)

    chk = sub.add_parser("check", help="audit + score ad hoc d'une liste de noms")
    chk.add_argument("--names", required=True, help="noms separes par des virgules")
    network_args(chk)
    chk.set_defaults(func=cmd_check)

    run = sub.add_parser("run", help="pipeline complet 1->5")
    run.add_argument("--keywords", required=True)
    run.add_argument("--brief", default=None)
    run.add_argument("--out-dir", default="runs/bom")
    run.add_argument("--count", type=int, default=30)
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--top", type=int, default=10)
    run.add_argument(
        "--engine",
        choices=("archetypes", "lego"),
        default="archetypes",
        help="archetypes = 5 familles ; lego = contraction multilingue",
    )
    run.add_argument("--research", default=None, help="research.json (Phase 3 deja mesuree)")
    network_args(run, with_translation=True)
    run.set_defaults(func=cmd_run)

    st = sub.add_parser("selftest", help="pipeline hors ligne de bout en bout sur les assets")
    st.set_defaults(func=cmd_selftest)

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
