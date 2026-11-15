"""Exports: a real .xlsx (stdlib only) and a consolidated names.json.

Excel is the format clients actually open. Writing it without a dependency
means producing the OOXML package by hand: six small XML parts, zipped.
The result is a normal workbook: frozen header, autofilter, column widths,
styled headers and numeric cells (so sorting works).
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from . import score as sc

CONTROL = {chr(i): "" for i in range(0x20) if i not in (0x09, 0x0A, 0x0D)}


def _clean(value: object) -> str:
    text = "" if value is None else str(value)
    for char, replacement in CONTROL.items():
        text = text.replace(char, replacement)
    return text


def _col(index: int) -> str:
    """1 -> A, 27 -> AA."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _cell(ref: str, value: object, kind: str, style: int) -> str:
    if value is None or value == "":
        return f'<c r="{ref}" s="{style}"/>'
    if kind in {"float1", "float2", "int"}:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return (
                f'<c r="{ref}" s="2" t="inlineStr"><is><t xml:space="preserve">'
                f"{escape(_clean(value))}</t></is></c>"
            )
        if kind == "int":
            number = int(round(number))
        return f'<c r="{ref}" s="{style}"><v>{number}</v></c>'
    return (
        f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">'
        f"{escape(_clean(value))}</t></is></c>"
    )


def _sheet_xml(sheet: dict) -> str:
    columns = sheet["columns"]
    rows = sheet["rows"]
    last_col = _col(len(columns))
    last_row = len(rows) + 1
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        f'<dimension ref="A1:{last_col}{last_row}"/>',
        '<sheetViews><sheetView workbookViewId="0" tabSelected="1">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>",
        '<sheetFormatPr defaultRowHeight="16"/>',
        "<cols>",
    ]
    for index, column in enumerate(columns, start=1):
        width = column.get("width", 14)
        parts.append(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        )
    parts.append("</cols><sheetData>")

    header = ['<row r="1" ht="30" customHeight="1">']
    for index, column in enumerate(columns, start=1):
        header.append(_cell(f"{_col(index)}1", column["label"], "text", 1))
    header.append("</row>")
    parts.append("".join(header))

    for row_index, row in enumerate(rows, start=2):
        cells = []
        for col_index, column in enumerate(columns, start=1):
            kind = column.get("kind", "text")
            style = {"float1": 3, "float2": 3, "int": 4}.get(kind, 2)
            cells.append(
                _cell(f"{_col(col_index)}{row_index}", row.get(column["key"]), kind, style)
            )
        parts.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

    parts.append("</sheetData>")
    parts.append(f'<autoFilter ref="A1:{last_col}{last_row}"/>')
    parts.append("</worksheet>")
    return "".join(parts)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.0"/></numFmts>
<fonts count="3">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
</fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF1F3864"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFD9D9D9"/></left><right style="thin"><color rgb="FFD9D9D9"/></right><top style="thin"><color rgb="FFD9D9D9"/></top><bottom style="thin"><color rgb="FFD9D9D9"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="5">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
<xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def write_xlsx(path: str | Path, sheets: list[dict]) -> Path:
    """Write a multi-sheet workbook. Each sheet: {name, columns, rows}."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
    ]
    for index in range(1, len(sheets) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    sheet_entries = []
    workbook_rels = []
    for index, sheet in enumerate(sheets, start=1):
        name = escape(sheet["name"][:31])
        sheet_entries.append(
            f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        )
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    style_id = len(sheets) + 1
    workbook_rels.append(
        f'<Relationship Id="rId{style_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>" + "".join(sheet_entries) + "</sheets></workbook>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(workbook_rels)
            + "</Relationships>",
        )
        archive.writestr("xl/styles.xml", STYLES)
        for index, sheet in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheet))
    return path


# --------------------------------------------------------------------------
# Row building
# --------------------------------------------------------------------------


def _com_status(item: dict) -> str:
    for domain in item.get("domains", []):
        if domain["tld"] == "com":
            return {
                "available": "libre",
                "registered": "pris",
                "unknown": "?",
            }.get(domain["status"], domain["status"])
    return "-"


def ranking_rows(score_doc: dict) -> list[dict]:
    rows: list[dict] = []
    for item in score_doc["ranking"]:
        tlds = [d["tld"] for d in item.get("domains", []) if d["status"] == "available"]
        taken = [r["id"] for r in item.get("registries", []) if r["status"] == "pris"]
        rows.append(
            {
                "rank": item["rank"],
                "name": item["display"],
                "slug": item["name"],
                "total": item["total"],
                "fidelity": item.get("fidelity", ""),
                "archetype": item.get("archetype_label") or "",
                "language": item.get("source_language", ""),
                "phrase": item.get("source_phrase", ""),
                "rule": item.get("rule", ""),
                "technique": item["pillars"]["technique"]["score"],
                "seo": item["pillars"]["seo"]["score"],
                "geo": item["pillars"]["geo"]["score"],
                "commercial": item["pillars"]["commercial"]["score"],
                "com": _com_status(item),
                "tlds": ", ".join(tlds) or "-",
                "registries": ", ".join(taken) or "-",
                "tier": item["tier"] + ("*" if item.get("provisional") else ""),
                "warnings": "; ".join(item.get("warnings", [])),
            }
        )
    return rows


def _provenance_rows(score_doc: dict) -> list[dict]:
    rows: list[dict] = []
    for item in score_doc["ranking"]:
        for prov in item.get("provenance", []):
            rows.append(
                {
                    "name": item["display"],
                    "language": prov.get("language", ""),
                    "phrase": prov.get("phrase", ""),
                    "rule": prov.get("rule_label", prov.get("rule", "")),
                    "order": prov.get("order", ""),
                    "fidelity": prov.get("fidelity", ""),
                }
            )
    return rows


def build_sheets(score_doc: dict) -> list[dict]:
    has_fidelity = any(item.get("fidelity") is not None for item in score_doc["ranking"])
    columns = [
        {"key": "rank", "label": "#", "width": 5, "kind": "int"},
        {"key": "name", "label": "Nom", "width": 18},
        {"key": "total", "label": "Score BOM", "width": 11, "kind": "float1"},
    ]
    if has_fidelity:
        columns.append({"key": "fidelity", "label": "Fidélité", "width": 10, "kind": "int"})
    columns += [
        {"key": "archetype", "label": "Archétype", "width": 26},
        {"key": "language", "label": "Langue", "width": 8},
        {"key": "phrase", "label": "Expression source", "width": 26},
        {"key": "rule", "label": "Règle", "width": 26},
        {"key": "technique", "label": "Tech /25", "width": 9, "kind": "float1"},
        {"key": "seo", "label": "SEO /25", "width": 9, "kind": "float1"},
        {"key": "geo", "label": "GEO /25", "width": 9, "kind": "float1"},
        {"key": "commercial", "label": "Com. /25", "width": 9, "kind": "float1"},
        {"key": "com", "label": ".com", "width": 7},
        {"key": "tlds", "label": "TLD libres", "width": 18},
        {"key": "registries", "label": "Registres pris", "width": 22},
        {"key": "tier", "label": "Verdict", "width": 14},
        {"key": "warnings", "label": "Réserves", "width": 44},
    ]

    sheets = [
        {
            "name": "Classement",
            "columns": columns,
            "rows": ranking_rows(score_doc),
        }
    ]

    if has_fidelity:
        sheets.append(
            {
                "name": "Provenances",
                "columns": [
                    {"key": "name", "label": "Nom", "width": 18},
                    {"key": "language", "label": "Langue", "width": 8},
                    {"key": "phrase", "label": "Expression", "width": 28},
                    {"key": "rule", "label": "Règle", "width": 26},
                    {"key": "order", "label": "Ordre", "width": 10},
                    {"key": "fidelity", "label": "Fidélité", "width": 10, "kind": "int"},
                ],
                "rows": _provenance_rows(score_doc),
            }
        )

    method_rows = []
    for pillar_id, pillar in sc.PILLARS.items():
        method_rows.append(
            {
                "pillar": pillar["label"],
                "points": pillar["max"],
                "parts": ", ".join(label for _pid, label, _mx in pillar["parts"]),
            }
        )
    sheets.append(
        {
            "name": "Méthode",
            "columns": [
                {"key": "pillar", "label": "Pilier", "width": 38},
                {"key": "points", "label": "Points", "width": 8, "kind": "int"},
                {"key": "parts", "label": "Sous-critères", "width": 110},
            ],
            "rows": method_rows,
        }
    )
    return sheets


def write_names_json(
    path: str | Path,
    score_doc: dict,
    audit_doc: dict,
    clusters: dict | None,
    candidates: dict | None,
) -> Path:
    """Consolidated, machine-readable deliverable (everything in one file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "bom.names/v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "engine": (candidates or {}).get("meta", {}).get("engine", "archetypes"),
        "audit": {
            "mode": audit_doc["meta"]["mode"],
            "tlds": audit_doc["meta"]["tlds"],
            "survivors": audit_doc["meta"]["survivors"],
            "hard_failed": audit_doc["meta"]["hard_failed"],
            "caveats": audit_doc["meta"]["caveats"],
        },
        "rubric": {
            key: {"label": value["label"], "max": value["max"]} for key, value in sc.PILLARS.items()
        },
        "corpus": (
            {
                "keywords": clusters["meta"]["total_keywords"],
                "clusters": {k: v["count"] for k, v in clusters["clusters"].items()},
                "assigned_by_fallback": clusters["meta"].get("assigned_by_fallback", 0),
            }
            if clusters
            else None
        ),
        "ranking": [
            {
                "rank": item["rank"],
                "name": item["name"],
                "display": item["display"],
                "total": item["total"],
                "tier": item["tier"],
                "provisional": item.get("provisional", False),
                "measured": item.get("measured", False),
                "verdict": item["verdict"],
                "fidelity": item.get("fidelity"),
                "source_language": item.get("source_language"),
                "source_phrase": item.get("source_phrase"),
                "rule": item.get("rule"),
                "translations": item.get("translations"),
                "provenance": item.get("provenance", []),
                "pillars": {
                    key: value["score"] for key, value in item["pillars"].items()
                },
                "domains": [
                    {
                        "domain": domain["domain"],
                        "status": domain["status"],
                        "confidence": domain["confidence"],
                        "detail": domain["detail"],
                    }
                    for domain in item.get("domains", [])
                ],
                "registries": [
                    {"id": reg["id"], "status": reg["status"], "detail": reg["detail"]}
                    for reg in item.get("registries", [])
                ],
                "stores": [
                    {"id": store["id"], "status": store["status"], "detail": store["detail"]}
                    for store in item.get("stores", [])
                ],
                "warnings": item.get("warnings", []),
                "actions": item.get("open_actions", []),
            }
            for item in score_doc["ranking"]
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
