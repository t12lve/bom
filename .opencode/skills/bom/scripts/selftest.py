#!/usr/bin/env python3
"""Self-test: run the whole offline pipeline on the bundled assets and assert.

    python scripts/bom.py selftest

It exists so that "the skill works" is a verified statement, not an opinion.
No network is used.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bomlib import audit as audit_mod  # noqa: E402
from bomlib import generate as gen_mod  # noqa: E402
from bomlib import keywords as kw_mod  # noqa: E402
from bomlib import lego as lego_mod  # noqa: E402
from bomlib import report as report_mod  # noqa: E402
from bomlib import research as research_mod  # noqa: E402
from bomlib import score as score_mod  # noqa: E402
from bomlib import text as tx_mod  # noqa: E402
from bomlib import translate as translate_mod  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = ROOT / "assets" / "keywords.example.csv"
BRIEF = ROOT / "assets" / "brief.example.md"
ARCHETYPE_MIN = 4  # each archetype should land at least this many candidates


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes = 0

    def ok(self, condition: bool, label: str, detail: str = "") -> None:
        if condition:
            self.passes += 1
            print(f"  PASS  {label}")
        else:
            self.failures.append(f"{label}{' — ' + detail if detail else ''}")
            print(f"  FAIL  {label}{' — ' + detail if detail else ''}")

    def report(self) -> int:
        print()
        if self.failures:
            print(f"FAIL: {len(self.failures)} verification(s) en echec, {self.passes} OK")
            for failure in self.failures:
                print(f"  - {failure}")
            return 1
        print(f"PASS: {self.passes} verifications")
        return 0


def main() -> int:
    check = Check()
    print("[selftest] assets")
    check.ok(KEYWORDS.exists(), "corpus d'exemple present")
    check.ok(BRIEF.exists(), "brief d'exemple present")

    with tempfile.TemporaryDirectory(prefix="bom-selftest-") as tmp:
        work = Path(tmp)

        print("[selftest] phase 1 — intake")
        clusters = kw_mod.intake(str(KEYWORDS), str(BRIEF), str(work / "clusters.json"))
        check.ok(clusters["meta"]["total_keywords"] >= 100, "corpus >= 100 mots-cles",
                 f"{clusters['meta']['total_keywords']}")
        check.ok(
            clusters["meta"]["total_keywords"] == 147,
            "l'en-tete CSV n'est pas compte comme mot-cle",
            f"{clusters['meta']['total_keywords']} au lieu de 147",
        )
        populated = [c for c in clusters["clusters"].values() if c["count"] > 0]
        check.ok(len(populated) == 5, "5 clusters peuples", f"{len(populated)}/5")
        check.ok(len(clusters["roots"]) >= 5, "racines extraites", f"{len(clusters['roots'])}")

        print("[selftest] phase 1b — generation")
        candidates = gen_mod.generate(clusters, count=30, seed=7)
        check.ok(candidates["meta"]["count"] == 30, "30 candidats generes",
                 str(candidates["meta"]["count"]))
        names = [c["name"] for c in candidates["candidates"]]
        check.ok(len(set(names)) == len(names), "noms uniques")
        check.ok(all(n.isascii() and n.isalpha() for n in names), "noms ASCII alphabetiques")
        thin = [a for a, n in candidates["meta"]["distribution"].items() if n < ARCHETYPE_MIN]
        check.ok(not thin, "chaque archetype >= 4 candidats", ",".join(thin))
        check.ok(
            all(len(c["rationale"]) > 20 for c in candidates["candidates"]),
            "chaque candidat a une justification",
        )

        print("[selftest] phase 2 — audit hors ligne")
        audited = audit_mod.screen(
            candidates["candidates"],
            cache_dir=work / ".cache",
            tlds=("com", "app", "ai", "io", "fr"),
            offline=True,
        )
        check.ok(audited["meta"]["mode"] == "static-only", "mode statique")
        check.ok(len(audited["candidates"]) == 30, "30 candidats audites")
        check.ok(
            all(c["domains"] and len(c["domains"]) == 5 for c in audited["candidates"]),
            "5 TLD verifies par candidat",
        )
        check.ok(
            all(c["serp"]["status"] == "pending_web_search" for c in audited["candidates"]),
            "pack SERP present (Phase 3 non simulee)",
        )

        print("[selftest] phase 4 — scoring")
        scores = score_mod.score_all(audited, clusters)
        check.ok(len(scores["ranking"]) == 30, "30 candidats notes")
        coherent = True
        for item in scores["ranking"]:
            total = sum(item["pillars"][p]["score"] for p in item["pillars"])
            if abs(total - item["total"]) > 0.05:
                coherent = False
        check.ok(coherent, "somme des 4 piliers = total")
        check.ok(
            all(0 <= item["total"] <= 100 for item in scores["ranking"]),
            "totaux dans 0-100",
        )
        check.ok(
            all(item.get("provisional") for item in scores["ranking"]),
            "audit hors ligne marque provisional",
        )
        check.ok(
            all(item["pillars"]["geo"]["prompt_battery"] for item in scores["ranking"]),
            "batterie GEO attachee a chaque score",
        )

        print("[selftest] phase 5 — restitution")
        report_path = report_mod.executive_report(
            scores, audited, clusters, candidates, work / "report", top=10
        )
        text = report_path.read_text(encoding="utf-8")
        check.ok(report_path.exists(), "rapport ecrit")
        check.ok("Tableau comparatif BOM" in text, "section comparative")
        check.ok("Méthode, poids et limites" in text, "section limites")
        check.ok("INPI" in text and "EUIPO" in text, "section marques")
        check.ok("provisoire" in text.lower(), "avertissement score provisoire")
        check.ok((work / "report" / "BOM-scores.csv").exists(), "export CSV")
        check.ok(
            len(list((work / "report" / "dossiers").glob("*.md"))) == 5,
            "5 dossiers individuels",
        )
        check.ok(
            len(json.loads((work / "clusters.json").read_text(encoding="utf-8"))["clusters"]) == 5,
            "clusters.json relisible",
        )

        print("[selftest] exports — Excel et JSON")
        xlsx = work / "report" / "BOM-names.xlsx"
        check.ok(xlsx.exists(), "classeur Excel ecrit")
        with zipfile.ZipFile(xlsx) as archive:
            parts = set(archive.namelist())
        check.ok(
            {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/styles.xml"}
            <= parts,
            "structure OOXML complete",
            ", ".join(sorted(parts)),
        )
        names_json = json.loads((work / "report" / "BOM-names.json").read_text(encoding="utf-8"))
        check.ok(names_json["schema"] == "bom.names/v1", "schema JSON names")
        check.ok(len(names_json["ranking"]) == 30, "JSON contient tout le classement")

        limited = report_mod.executive_report(
            scores, audited, clusters, candidates, work / "report-top3", top=3
        )
        limited_json = json.loads(
            (work / "report-top3" / "BOM-names.json").read_text(encoding="utf-8")
        )
        check.ok(
            len(limited_json["ranking"]) == 30,
            "top=3 ne tronque pas les exports",
            f"{len(limited_json['ranking'])} lignes",
        )
        table_rows = [
            line for line in limited.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ") and "**" in line
        ]
        check.ok(len(table_rows) == 3, "top=3 tronque le tableau du rapport", str(len(table_rows)))

        print("[selftest] filtres de mots — faux positifs")
        hard, soft = tx_mod.bad_word_hits("compute")
        check.ok(not hard and not soft, "'compute' n'est pas censure", f"{hard} {soft}")
        hard, soft = tx_mod.bad_word_hits("analytics")
        check.ok(not soft, "'analytics' ne declenche pas 'anal'", f"{soft}")
        hard, soft = tx_mod.bad_word_hits("skillhub")
        check.ok(not soft, "'skillhub' ne declenche pas 'kill'", f"{soft}")
        hard, _ = tx_mod.bad_word_hits("pute")
        check.ok(bool(hard), "'pute' reste bloque")
        hard, _ = tx_mod.bad_word_hits("puteapp")
        check.ok(bool(hard), "'puteapp' reste bloque")
        check.ok(audit_mod.static_screen("excelboard")["hard_fail"], "collision 'excel' bloquee")

        print("[selftest] mecanique LEGO")
        contracted = lego_mod.contract_phrase("leg godt", "lego2")
        check.ok(contracted == "lego", "leg godt -> lego", str(contracted))
        accepted, reason = gen_mod.accept_name("lego", set())
        check.ok(not accepted, "lego rejete comme marque connue", reason)

        translator = translate_mod.Translator(
            cache_dir=work / ".cache", source_lang="fr", provider="offline", enabled=False
        )
        langs, _skipped = translate_mod.resolve_languages("fr,en,es,de,it,da", "fr")
        lego_doc = lego_mod.generate_lego(
            clusters, translator=translator, langs=langs, source_lang="fr", count=16, seed=7
        )
        check.ok(lego_doc["meta"]["engine"] == "lego", "moteur LEGO")
        check.ok(len(lego_doc["candidates"]) >= 8, "noms LEGO generes",
                 str(len(lego_doc["candidates"])))
        check.ok(
            all(c["fidelity"] is not None and c["source_phrase"] for c in lego_doc["candidates"]),
            "chaque nom LEGO a une provenance et une fidelite",
        )
        anchor_ok = all(
            set(tx_mod.tokens(" ".join(c["geo_anchor"])))
            <= set(tx_mod.tokens(c["source_phrase"]))
            for c in lego_doc["candidates"]
        )
        check.ok(anchor_ok, "ancrage GEO LEGO = mots de l'expression source")
        check.ok(
            all(2 <= c["syllables"] <= 3 for c in lego_doc["candidates"]),
            "noms LEGO courts (2-3 syllabes)",
        )

        print("[selftest] sous-agents — paquets et fusion")
        packets = research_mod.research_packets(
            scores, batch=3, top=6, out_dir=work / "packets"
        )
        check.ok(len(packets) >= 2, "paquets de recherche generes", str(len(packets)))
        first = json.loads(Path(packets[0]["file"]).read_text(encoding="utf-8"))
        check.ok(first["requires_user_approval"] is True, "paquet soumis a accord utilisateur")
        check.ok(first["model_tier"] == "research", "tier de modele indique")
        target_names = [c["name"] for c in first["candidates"]]
        result = {
            "phase": "3",
            "agent": "selftest",
            "results": [
                {
                    "name": target_names[0],
                    "serp": {"verdict": "virgin", "organic_results": 1},
                    "stores": {"app_store": "free", "play_store": "free", "product_hunt": "free"},
                    "trademark": {"verdict": "clear", "matches": []},
                    "geo": {"fails": 0, "hedges": 1, "passes": 6},
                },
                {
                    "name": target_names[1],
                    "serp": {"verdict": "blocked", "organic_results": 11,
                             "dominant_entity": "film"},
                    "stores": {"app_store": "taken", "play_store": "free"},
                    "trademark": {"verdict": "blocked", "matches": [{"office": "EUIPO", "classes": [42]}]},
                    "geo": {"fails": 15, "hedges": 2, "passes": 0},
                },
            ],
        }
        result_path = work / "packets" / "result.json"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        merged = research_mod.merge_results([str(result_path)])
        check.ok(merged["meta"]["measured"] == 2, "fusion: 2 noms mesures")
        rescored = score_mod.score_all(audited, clusters, research=merged)
        measured = [i for i in rescored["ranking"] if i.get("measured")]
        check.ok(len(measured) == 2, "re-scoring avec preuve mesuree")
        blocked = [i for i in rescored["ranking"] if i["name"] == target_names[1]]
        check.ok(blocked and blocked[0]["tier"] == "REJETE", "marque bloquee -> REJETE")
        virgin = [i for i in rescored["ranking"] if i["name"] == target_names[0]]
        check.ok(
            virgin
            and virgin[0]["pillars"]["seo"]["parts"]["virginity"].get("measured") is True,
            "SERP vierge mesuree remplace l'estimation",
        )

        print("[selftest] compatibilite harnais")
        skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
        fields: dict[str, str] = {}
        if match:
            for line in match.group(1).splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    fields[key.strip()] = value.strip().strip('"')
        check.ok(fields.get("name") == "bom", "frontmatter: name=bom")
        description = fields.get("description", "")
        check.ok(
            0 < len(description) <= 500,
            "description <= 500 caracteres (limite Codex)",
            str(len(description)),
        )

        installer = ROOT / "scripts" / "install_skill.py"
        check.ok(installer.exists(), "installateur multi-harnais present")
        sandbox = work / "sandbox-home"
        proc = subprocess.run(
            [sys.executable, str(installer), "--home", str(sandbox), "--copy", "--harness", "all"],
            capture_output=True,
            text=True,
        )
        check.ok(proc.returncode == 0, "installation dans un HOME de test", proc.stderr[-160:])
        expected = [
            ".claude/skills/bom",
            ".agents/skills/bom",
            ".gemini/config/skills/bom",
            ".config/opencode/skills/bom",
        ]
        missing = [path for path in expected if not (sandbox / path / "SKILL.md").exists()]
        check.ok(not missing, "4 chemins harnais ecrits", ",".join(missing))
        check.ok(
            all((sandbox / path / "scripts" / "bom.py").exists() for path in expected),
            "bom.py present dans chaque installation",
        )

    return check.report()


if __name__ == "__main__":
    raise SystemExit(main())
