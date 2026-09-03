#!/usr/bin/env python3
"""Fill a DOCX-first report template with explicit, evidence-bound slots.

This is a small renderer helper for module R/Python report coders.  It never
calculates statistics or invents prose.  Without ``--final`` it deliberately
returns ``DRAFT``; a release caller must still run the contract and visual
validators.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from validate_docx_structure import TEMPLATE_MARKER, _marker_bookmark_name, extract_template_markers, inspect
from validate_report_contract import (
    normalise_relative,
    resolve_under,
    validate_pack,
    validate_plan,
    validate_slot_alignment,
)


TABLE_SPECS = {
    "RESULTS": {
        "rows_key": "RESULT_TABLE_ROWS",
        "keys": ("name", "value", "unit", "source"),
        "caption_key": "TABLE:RESULTS.CAPTION",
    },
    "OUTPUTS": {
        "rows_key": "OUTPUT_TABLE_ROWS",
        "keys": ("path", "kind", "description", "purpose", "consumers"),
        "caption_key": "TABLE:OUTPUTS.CAPTION",
    },
    "VERSIONS": {
        "rows_key": "VERSION_TABLE_ROWS",
        "keys": ("name", "version", "purpose"),
        "caption_key": "TABLE:VERSIONS.CAPTION",
    },
}
SOURCE_SUFFIX = ".SOURCE"


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _scalar(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        return "；".join(_scalar(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}：{_scalar(item)}" for key, item in value.items())
    return str(value)


def _slot_text(value: object) -> str:
    if isinstance(value, dict):
        for key in ("text", "content", "body", "value", "description"):
            if value.get(key) not in (None, "", [], {}):
                return _scalar(value[key])
    return _scalar(value)


def _key(value: object) -> str:
    return str(value).strip().strip("[]").upper()


def _flatten_values(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("slot values must be a JSON object")
    source = value.get("slots") if isinstance(value.get("slots"), dict) else value
    values = {_key(name): item for name, item in source.items() if name not in {"tables", "figures", "notes", "text"}}
    text = source.get("text") if isinstance(source, dict) else None
    if isinstance(text, dict):
        values.update({_key(name): item for name, item in text.items()})
    tables = source.get("tables") if isinstance(source, dict) else None
    if isinstance(tables, dict):
        for name, table in tables.items():
            kind = str(name).upper().replace("TABLE:", "")
            values[f"TABLE:{kind}"] = table
            if kind in TABLE_SPECS:
                values[TABLE_SPECS[kind]["rows_key"]] = table
                if isinstance(table, dict) and table.get("caption") not in (None, ""):
                    values[TABLE_SPECS[kind]["caption_key"]] = table["caption"]
    figures = source.get("figures") if isinstance(source, dict) else None
    if isinstance(figures, list):
        for index, figure in enumerate(figures, 1):
            if not isinstance(figure, dict):
                continue
            ident = str(figure.get("id", f"F{index}")).upper()
            prefix = f"FIGURE:{ident}"
            for suffix, key in (("TITLE", "title"), ("SOURCE", "path"), ("CAPTION", "caption"), ("CAPTION_FIELDS", "caption_fields")):
                if key in figure:
                    values[f"{prefix}.{suffix}"] = figure[key]
    notes = source.get("notes") if isinstance(source, dict) else None
    if isinstance(notes, list):
        for index, note in enumerate(notes):
            if isinstance(note, dict):
                ident = str(note.get("id", "direction")).upper()
                values[f"NOTE:{ident}"] = note
                if index == 0 and "NOTE:DIRECTION" not in values:
                    values["NOTE:DIRECTION"] = note
    defaults = {
        "TABLE:RESULTS.CAPTION": "主要结果",
        "TABLE:OUTPUTS.CAPTION": "公开业务文件",
        "TABLE:VERSIONS.CAPTION": "软件与资源版本",
    }
    for name, default in defaults.items():
        values.setdefault(name, default)
    return values


def _lookup(values: dict[str, object], marker: str) -> object:
    name = _key(marker[2:-2] if marker.startswith("[[") else marker)
    if name in values:
        return values[name]
    # Permit dotted/colon aliases supplied by a renderer.
    aliases = {
        name.replace(".", ":"),
        name.replace(":", "."),
        name.replace(".", "_"),
    }
    # The pack/slot examples use both short names and the explicit report
    # prefix.  Keep this aliasing deterministic rather than accepting arbitrary
    # fuzzy matches.
    if name.startswith("REPORT_"):
        aliases.add(name[7:])
    elif name in {"SUMMARY", "SCOPE", "METHOD", "QC", "RESULT", "CONCLUSION", "LIMITATIONS"}:
        aliases.add(f"REPORT_{name}" if name == "SUMMARY" else f"ANALYSIS_{name}")
    for alias in aliases:
        if alias in values:
            return values[alias]
    return None


def values_from_pack(pack: dict[str, object]) -> dict[str, object]:
    """Build conservative defaults from the shared evidence pack.

    Module renderers should normally pass their own explicit slot map; these
    defaults only make the DOCX template useful for a one-off run.
    """
    points = [item for item in pack.get("analysis_points", []) if isinstance(item, dict)]
    point = points[0] if points else {}
    comparison = point.get("comparison") if isinstance(point.get("comparison"), dict) else {}
    results = point.get("results", [])
    outputs = [
            item for item in point.get("outputs", [])
            if isinstance(item, dict) and item.get("published")
        ]
    values: dict[str, object] = {
        "REPORT_TITLE": pack.get("title", "分析报告"),
        "REPORT_AUDIENCE": pack.get("audience", ""),
        "REPORT_SUMMARY": point.get("interpretation", ""),
        "ANALYSIS_SCOPE": point.get("scope", ""),
        "ANALYSIS_METHOD": point.get("method", ""),
        "ANALYSIS_QC": point.get("qc", ""),
        "QC.CONDITION": bool(point.get("qc")),
        "ANALYSIS_RESULT": results,
        "RESULTS.CONDITION": bool(results),
        "ANALYSIS_CONCLUSION": point.get("interpretation", ""),
        "ANALYSIS_LIMITATIONS": point.get("limitations", []),
        "OUTPUTS_INTRO": "当前分析实际发布的业务文件及其用途。",
        "REFERENCES": pack.get("references", []),
        "RESULT_TABLE_ROWS": results,
        "OUTPUT_TABLE_ROWS": outputs,
        "VERSION_TABLE_ROWS": pack.get("versions", []),
        "FIGURES.CONDITION": bool(point.get("figure_table_refs")),
    }
    if comparison:
        target = comparison.get("target", "")
        reference = comparison.get("reference", "")
        direction = comparison.get("direction", "")
        metric = comparison.get("metric", "")
        values["NOTE:DIRECTION"] = {
            "kind": "direction",
            "text": f"{metric + '：' if metric else ''}{direction}；目标组={target}；参照组={reference}",
        }
    notes = point.get("notes", pack.get("notes", []))
    if isinstance(notes, list):
        for index, note in enumerate(notes):
            if isinstance(note, dict):
                note_id = str(note.get("id", "direction")).upper()
                values[f"NOTE:{note_id}"] = note
                if index == 0 and "NOTE:DIRECTION" not in values:
                    values["NOTE:DIRECTION"] = note
                if note_id == "DIRECTION":
                    values["NOTE:DIRECTION"] = note
    for ref in point.get("figure_table_refs", []):
        if not isinstance(ref, dict):
            continue
        ident = str(ref.get("id", "F1"))
        prefix = f"FIGURE.{ident.upper()}"
        values[f"{prefix}.SOURCE"] = ref.get("path", "")
        values[f"{prefix}.TITLE"] = ref.get("title", ref.get("id", ident))
        values[f"{prefix}.CAPTION"] = ref.get("caption", "")
        values[f"{prefix}.CAPTION_FIELDS"] = ref.get("caption_fields", "")
    for table_name, spec in TABLE_SPECS.items():
        captions = {"RESULTS": "主要结果", "OUTPUTS": "公开业务文件", "VERSIONS": "软件与资源版本"}
        values.setdefault(spec["caption_key"], captions[table_name])
        values.setdefault(f"TABLE:{table_name}", "")
    return values


def _iter_paragraphs(document):
    # ``python-docx`` can create a short-lived proxy for the same XML paragraph
    # on each property access; using ``id(proxy)`` therefore causes IDs to be
    # reused and silently skips table-cell paragraphs.  Keep the underlying
    # lxml element itself in the set instead.
    seen: set[object] = set()

    def cells(table):
        for row in table.rows:
            for cell in row.cells:
                yield cell
                for nested in cell.tables:
                    yield from cells(nested)

    def add(container):
        for paragraph in getattr(container, "paragraphs", []):
            if paragraph._p not in seen:
                seen.add(paragraph._p)
                yield paragraph
        for table in getattr(container, "tables", []):
            for cell in cells(table):
                for paragraph in cell.paragraphs:
                    if paragraph._p not in seen:
                        seen.add(paragraph._p)
                        yield paragraph

    yield from add(document)
    for section in document.sections:
        for container in (section.header, section.footer, section.first_page_header, section.first_page_footer):
            yield from add(container)


def _paragraph_text(paragraph) -> str:
    return "".join(run.text or "" for run in paragraph.runs)


def _replace_span(paragraph, start: int, end: int, replacement: str) -> None:
    """Replace a text span even when Word split a marker across runs."""
    runs = list(paragraph.runs)
    positions: list[tuple[int, int]] = []
    cursor = 0
    for run in runs:
        text = run.text or ""
        positions.append((cursor, cursor + len(text)))
        cursor += len(text)
    touched = [index for index, (left, right) in enumerate(positions) if right > start and left < end]
    if not touched:
        return
    first = touched[0]
    last = touched[-1]
    left_offset = start - positions[first][0]
    right_offset = end - positions[last][0]
    first_text = runs[first].text or ""
    if first == last:
        runs[first].text = first_text[:left_offset] + replacement + first_text[right_offset:]
        return
    last_text = runs[last].text or ""
    suffix = last_text[right_offset:]
    runs[first].text = first_text[:left_offset] + replacement
    for index in touched[1:]:
        runs[index].text = suffix if index == last else ""


def _insert_picture(paragraph, marker: str, value: object, root: Path | None) -> bool:
    raw = _scalar(value)
    if not raw:
        return False
    candidate = Path(raw)
    if root is not None and not candidate.is_absolute():
        relative = normalise_relative(raw)
        candidate = resolve_under(root, relative) if relative else None
    else:
        candidate = candidate.resolve()
    if candidate is None or not candidate.is_file() or candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return False
    runs = list(paragraph.runs)
    full = _paragraph_text(paragraph)
    start = full.find(marker)
    if start < 0:
        return False
    end = start + len(marker)
    positions: list[tuple[int, int]] = []
    cursor = 0
    for run in runs:
        text = run.text or ""
        positions.append((cursor, cursor + len(text)))
        cursor += len(text)
    touched = [index for index, (left, right) in enumerate(positions) if right > start and left < end]
    if not touched:
        return False
    first, last = touched[0], touched[-1]
    left_offset = start - positions[first][0]
    right_offset = end - positions[last][0]
    first_text = runs[first].text or ""
    suffix = (runs[last].text or "")[right_offset:]
    runs[first].text = first_text[:left_offset]
    for index in touched[1:]:
        runs[index].text = ""
    runs[first].add_picture(str(candidate))
    if suffix:
        paragraph.add_run(suffix)
    return True


def _cell_set_text(cell, value: object) -> None:
    paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    for run in paragraph.runs:
        run.text = ""
    paragraph.add_run(_scalar(value))
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)


def _table_kind(table) -> str | None:
    text = "".join(cell.text for row in table.rows for cell in row.cells).upper()
    marker_prefixes = {
        "RESULTS": ("[[RESULT.NAME]]", "[[RESULT.VALUE]]", "[[RESULT.UNIT]]", "[[RESULT.SOURCE]]"),
        "OUTPUTS": ("[[OUTPUT.PATH]]", "[[OUTPUT.KIND]]", "[[OUTPUT.DESCRIPTION]]", "[[OUTPUT.PURPOSE]]", "[[OUTPUT.CONSUMERS]]"),
        "VERSIONS": ("[[VERSION.NAME]]", "[[VERSION.VALUE]]", "[[VERSION.PURPOSE]]"),
    }
    for kind, markers in marker_prefixes.items():
        if any(marker in text for marker in markers):
            return kind
    return None


def _records_and_columns(raw: object, kind: str) -> tuple[list[object], list[str] | None]:
    if isinstance(raw, dict):
        records = raw.get("rows", raw.get("data", []))
        columns = raw.get("columns")
        if isinstance(columns, list):
            names: list[str] = []
            for item in columns:
                if isinstance(item, dict):
                    names.append(str(item.get("key", item.get("name", ""))))
                else:
                    names.append(str(item))
            columns = names
        else:
            columns = None
    else:
        records, columns = raw, None
    if not isinstance(records, list):
        records = []
    return records, columns


def _row_values_for_kind(record: object, kind: str, columns: list[str] | None, count: int) -> list[object]:
    keys = columns or list(TABLE_SPECS[kind]["keys"])
    if isinstance(record, dict):
        values = []
        for key in keys[:count]:
            value = record.get(key, "")
            if value in (None, "") and key == "description":
                value = record.get("content", record.get("purpose", ""))
            values.append(value)
        return values + [""] * max(0, count - len(values))
    if isinstance(record, list):
        return list(record[:count]) + [""] * max(0, count - len(record))
    return [_scalar(record)] + [""] * max(0, count - 1)


def _expand_table_rows(document, values: dict[str, object]) -> int:
    """Fill the prototype data row of each named table, preserving its style."""
    from docx.table import Table

    count = 0
    tables: list[Table] = []

    def collect(container):
        for table in getattr(container, "tables", []):
            tables.append(table)
            for row in table.rows:
                for cell in row.cells:
                    collect(cell)

    collect(document)
    for table in tables:
        kind = _table_kind(table)
        if kind is None or len(table.rows) < 2:
            continue
        spec = TABLE_SPECS[kind]
        raw = _lookup(values, spec["rows_key"])
        if raw is None:
            raw = _lookup(values, f"TABLE:{kind}")
        if raw is None:
            continue
        records, columns = _records_and_columns(raw, kind)
        header = table.rows[0]
        if columns and len(columns) == len(header.cells):
            for cell, column in zip(header.cells, columns):
                _cell_set_text(cell, column)
        prototype = table.rows[1]
        template_xml = deepcopy(prototype._tr)
        parent = prototype._tr.getparent()
        insert_at = parent.index(prototype._tr)
        for offset, record in enumerate(records):
            cloned = deepcopy(template_xml)
            cells = cloned.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
            row_values = _row_values_for_kind(record, kind, columns, len(cells))
            for cell, cell_value in zip(cells, row_values):
                text_nodes = cell.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                if text_nodes:
                    text_nodes[0].text = _scalar(cell_value)
                    for node in text_nodes[1:]:
                        node.text = ""
            parent.insert(insert_at + offset, cloned)
        parent.remove(prototype._tr)
        count += len(records)
    return count


def _remove_paragraph(paragraph) -> None:
    parent = paragraph._p.getparent()
    if parent is not None:
        parent.remove(paragraph._p)


def _figure_ids(values: dict[str, object]) -> list[str]:
    found: set[str] = set()
    for key in values:
        match = re.match(r"FIGURE[.:]([A-Z][A-Z0-9_-]*)[.]SOURCE$", key.upper())
        if match and values[key] not in (None, ""):
            found.add(match.group(1))
    return sorted(found, key=lambda item: (int(item[1:]) if item[1:].isdigit() else 10**9, item))


def _replace_xml_text(root, replacements: dict[str, str]) -> None:
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "t" or node.text is None:
            continue
        text = node.text
        for old, new in replacements.items():
            text = text.replace(old, new)
        node.text = text


def _clone_figure_blocks(document, values: dict[str, object]) -> None:
    """Clone the complete stock F1 title/image/caption block for F2…Fn."""
    ids = _figure_ids(values)
    if len(ids) <= 1:
        return
    paragraphs = list(document.paragraphs)
    source = next((p for p in paragraphs if "[[FIGURE:F1.SOURCE]]" in _paragraph_text(p)), None)
    title = next((p for p in paragraphs if "[[FIGURE:F1.TITLE]]" in _paragraph_text(p)), None)
    caption = next((p for p in paragraphs if "[[FIGURE:F1.CAPTION]]" in _paragraph_text(p)), None)
    if not all((source, title, caption)):
        return
    blocks = [title._p, source._p, caption._p]
    insertion = caption._p
    for number, ident in enumerate(ids[1:], 2):
        clones = [deepcopy(block) for block in blocks]
        replacements = {
            "[[FIGURE:F1.TITLE]]": f"[[FIGURE:{ident}.TITLE]]",
            "[[FIGURE:F1.SOURCE]]": f"[[FIGURE:{ident}.SOURCE]]",
            "[[FIGURE:F1.CAPTION]]": f"[[FIGURE:{ident}.CAPTION]]",
            "图 1.": f"图 {number}.",
        }
        for clone in clones:
            _replace_xml_text(clone, replacements)
            # A cloned block is filled by marker text; duplicate bookmarks
            # would make Word repair the document, so remove them.
            for node in list(clone.iter()):
                if node.tag.rsplit("}", 1)[-1] in {"bookmarkStart", "bookmarkEnd"}:
                    parent = node.getparent()
                    if parent is not None:
                        parent.remove(node)
        for clone in clones:
            insertion.addnext(clone)
            insertion = clone


def _ensure_first_figure(values: dict[str, object]) -> None:
    """Use the first declared figure for the stock F1 block when needed."""
    ids = _figure_ids(values)
    if not ids or "F1" in ids:
        return
    first = ids[0]
    for suffix in ("TITLE", "SOURCE", "CAPTION", "CAPTION_FIELDS"):
        value = _lookup(values, f"[[FIGURE:{first}.{suffix}]]")
        if value is not None:
            values[f"FIGURE.F1.{suffix}"] = value


def _remove_optional_figure_block(document, values: dict[str, object]) -> None:
    """Remove the stock F1 block when no published figure is supplied."""
    source = _lookup(values, "[[FIGURE:F1.SOURCE]]")
    if source not in (None, ""):
        return
    paragraphs = list(_iter_paragraphs(document))
    for paragraph in paragraphs:
        text = _paragraph_text(paragraph)
        if any(token in text for token in ("[[FIGURE:F1.TITLE]]", "[[FIGURE:F1.SOURCE]]", "[[FIGURE:F1.CAPTION]]")):
            _remove_paragraph(paragraph)
    # The heading becomes an empty chapter if the optional figure block is gone.
    for paragraph in list(_iter_paragraphs(document)):
        if _paragraph_text(paragraph) == "图件":
            _remove_paragraph(paragraph)
            break


def _remove_optional_qc(document, values: dict[str, object]) -> None:
    """Remove the QC section when no QC fact was declared."""
    qc = _lookup(values, "[[ANALYSIS_QC]]")
    if qc not in (None, "", [], {}):
        return
    paragraphs = list(document.paragraphs)
    heading = next((p for p in paragraphs if _paragraph_text(p) == "质控与异常"), None)
    if heading is None:
        return
    remove = [heading]
    after_heading = False
    for paragraph in paragraphs:
        if paragraph is heading:
            after_heading = True
            continue
        if not after_heading:
            continue
        if _paragraph_text(paragraph) in {"分析结果与解读", "综合结论"}:
            break
        remove.append(paragraph)
    for paragraph in remove:
        _remove_paragraph(paragraph)


def _remove_optional_note(document, values: dict[str, object]) -> None:
    """Remove the styled Note block when no note is applicable."""
    note = _lookup(values, "[[NOTE:DIRECTION]]")
    if note not in (None, "", [], {}):
        return
    for table in list(document.tables):
        content = "".join(cell.text for row in table.rows for cell in row.cells)
        if "[[NOTE:" in content or content.strip().startswith("Note"):
            element = table._element
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)


def _caption_value(values: dict[str, object], marker: str) -> object:
    direct = _lookup(values, marker)
    if direct not in (None, "", [], {}):
        return direct
    body = marker[2:-2].upper()
    match = re.fullmatch(r"TABLE:(RESULTS|OUTPUTS|VERSIONS)\.CAPTION", body)
    if match:
        kind = match.group(1)
        raw = values.get(f"TABLE:{kind}")
        if raw in (None, "", [], {}):
            raw = values.get(TABLE_SPECS[kind]["rows_key"])
        if raw in (None, "", [], {}):
            raw = _lookup(values, f"TABLE:{kind}")
        if isinstance(raw, dict):
            return raw.get("caption", "")
    return direct


def fill_document(template: Path, values: dict[str, object], output: Path, root: Path | None = None) -> dict[str, object]:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("python-docx is required for DOCX template rendering") from exc
    document = Document(str(template))
    _ensure_first_figure(values)
    _remove_optional_qc(document, values)
    _remove_optional_note(document, values)
    _clone_figure_blocks(document, values)
    _remove_optional_figure_block(document, values)
    expanded_rows = _expand_table_rows(document, values)
    replaced = 0
    unresolved: list[str] = []
    for paragraph in _iter_paragraphs(document):
        while True:
            full = _paragraph_text(paragraph)
            matches = list(TEMPLATE_MARKER.finditer(full))
            if not matches:
                break
            match = matches[0]
            marker = match.group(0)
            value = _caption_value(values, marker) if marker[2:-2].upper().endswith(".CAPTION") else _lookup(values, marker)
            marker_name = marker[2:-2].upper()
            if value is None and marker_name in {"QC.CONDITION", "RESULTS.CONDITION", "FIGURES.CONDITION", "TABLE:RESULTS", "TABLE:OUTPUTS", "TABLE:VERSIONS"}:
                value = ""
            if marker[2:-2].upper().endswith(SOURCE_SUFFIX) and value not in (None, ""):
                if _insert_picture(paragraph, marker, value, root):
                    replaced += 1
                    continue
                unresolved.append(f"invalid figure source: {value}")
                _replace_span(paragraph, match.start(), match.end(), "")
                replaced += 1
                continue
            if value is None:
                unresolved.append(marker)
                # Leave it visible for draft diagnostics and avoid looping.
                break
            replacement = _slot_text(value)
            if marker[2:-2].upper().startswith("NOTE:") and replacement.lower().startswith("note："):
                replacement = replacement.split("：", 1)[1]
            _replace_span(paragraph, match.start(), match.end(), replacement)
            replaced += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", dir=output.parent, prefix=f".{output.name}.", delete=False) as handle:
            temporary = Path(handle.name)
        document.save(temporary)
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {"replaced": replaced, "expanded_rows": expanded_rows, "unresolved": sorted(set(unresolved))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--values", "--slots", dest="values", type=Path)
    parser.add_argument("--evidence-pack", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--final", action="store_true", help="run release marker and structure gates")
    parser.add_argument("--require-note", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        template = args.template.resolve()
        if template.is_dir():
            template = template / "report_template.docx"
        if not template.is_file():
            raise ValueError(f"template does not exist: {template}")
        marker_info = extract_template_markers(template)
        if marker_info.get("error"):
            raise ValueError(str(marker_info["error"]))
        bookmark_map = marker_info.get("bookmarks", {})
        if isinstance(bookmark_map, dict):
            for marker in marker_info.get("markers", []):
                marker_body = marker[2:-2].upper()
                # Prototype cell fields are replaced by table-row expansion;
                # they do not need one bookmark per column.  The caption/table
                # anchor is the stable bookmark for the whole table.
                if marker_body.startswith(("RESULT.", "OUTPUT.", "VERSION.")):
                    continue
                expected = _marker_bookmark_name(marker)
                actual = bookmark_map.get(marker, [])
                if expected not in actual:
                    message = f"template marker {marker} has no matching bookmark {expected}"
                    (errors if args.final else warnings).append(message)
        if args.values:
            values = {}
            if args.evidence_pack:
                pack_for_defaults = _load(args.evidence_pack)
                if not isinstance(pack_for_defaults, dict):
                    raise ValueError("evidence pack must be a JSON object")
                values.update(values_from_pack(pack_for_defaults))
            values.update(_flatten_values(_load(args.values)))
        elif args.evidence_pack:
            pack = _load(args.evidence_pack)
            if not isinstance(pack, dict):
                raise ValueError("evidence pack must be a JSON object")
            values = values_from_pack(pack)
        else:
            raise ValueError("one of --values/--evidence-pack is required")
        root = args.root.resolve() if args.root else None
        if root is not None and not root.is_dir():
            raise ValueError(f"artifact root does not exist: {root}")
        # A template with slot bookmarks is the DOCX-first contract.  Legacy
        # templates without bookmarks remain usable but are reported by the
        # structural validator in release mode.
        result = fill_document(template, values, args.output.resolve(), root)
        if args.final:
            if args.evidence_pack:
                pack = _load(args.evidence_pack)
                if not isinstance(pack, dict):
                    raise ValueError("evidence pack must be a JSON object")
                errors.extend(validate_pack(pack, root, require_files=True, final=True))
                if args.plan:
                    plan = _load(args.plan)
                    if not isinstance(plan, dict):
                        raise ValueError("report plan must be a JSON object")
                    point_ids = {item.get("id") for item in pack.get("analysis_points", []) if isinstance(item, dict)}
                    errors.extend(validate_plan(plan, point_ids, final=True))
                    errors.extend(validate_slot_alignment(pack, plan, strict=True))
                elif pack.get("quality_profile") != "release":
                    errors.append("final template render requires evidence pack quality_profile=release")
            if result["unresolved"]:
                errors.append(f"unresolved template markers: {result['unresolved']}")
            checked = inspect(args.output.resolve(), final=True, require_note=args.require_note)
            if checked.get("status") != "PASS":
                errors.extend(f"DOCX: {message}" for message in checked.get("errors", []))
                if not checked.get("errors") and checked.get("status") != "PASS":
                    errors.append(f"DOCX structural gate returned {checked.get('status')}")
        status = "PASS" if args.final and not errors else ("BLOCKED" if errors else "DRAFT")
        payload = {"status": status, **result, "template_markers": marker_info.get("markers", []), "warnings": warnings, "errors": errors}
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
            print(f"DOCX_TEMPLATE_{status} output={args.output.resolve()} sha256={digest}")
            for message in errors:
                print(message, file=sys.stderr)
            for message in warnings:
                print(message)
        return 0 if status == "PASS" else 2
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"DOCX_TEMPLATE_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
