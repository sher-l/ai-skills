#!/usr/bin/env python3
"""Inspect DOCX drawing/crop structure for whole-figure delivery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import zipfile
import xml.etree.ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}
CONTINUATION = re.compile(
    r"(?:图\s*\d+\s*[（(]\s*续|续\s*[，,:： ]*第\s*\d+\s*/\s*\d+\s*幅|第\s*\d+\s*/\s*\d+\s*幅)"
)
CAPTION = re.compile(r"(?:图\s*(?:注|[A-Za-z0-9.-]+)|Figure\s*[A-Za-z0-9.-]+|表\s*(?:注|[A-Za-z0-9.-]+)|Table\s*[A-Za-z0-9.-]+|caption)", re.I)
QUESTION = re.compile(r"(?:[？?]|哪些|如何|是否|为什么|什么|哪种|请判断|待确认)")
PLACEHOLDER = re.compile(r"(?:EVIDENCE_REQUIRED|\{\{[^}]+\}\}|\b(?:TODO|TBD|REPLACE)\b)", re.I)
DRAFT_MARKER = re.compile(r"(?:^\s*DRAFT\b|通用 slot 预览|generic key-value)", re.I)
MARKETING = re.compile(r"(?:扫码|公司介绍|服务领域|风险比看不懂|小果带你|联系我们)")
CORRUPTION = re.compile(r"\uFFFD")
REPEATED_WORD = re.compile(r"(?:结果显示|候选|表达|分析|数值越大表示){2,}")
TEMPLATE_MARKER = re.compile(r"\[\[(?:[A-Za-z0-9_.:-]+)\]\]")
FIGURE_TITLE = re.compile(r"^(?:图\s*\d+(?:[.、:：-]|\s)|Figure\s*\d+(?:[.、:：-]|\s))", re.I)
NOTE_TEXT = re.compile(r"(?:^|[\s｜|:：])Note(?:$|[\s｜|:：])|\[\[NOTE:", re.I)
EXPECTED_NOTE_COLORS = {"fill": "DDEBF7", "border": "5B9BD5", "label": "2F75B5"}


def make_diagnostics(errors: list[str], warnings: list[str], subject: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for message in errors:
        code = "figure/crop" if "srcRect" in message or "crop" in message else "docx/structure"
        if "continuation" in message:
            code = "figure/continuation"
        if "caption adjacency" in message:
            code = "figure/caption-adjacency"
        if "declarative" in message:
            code = "language/non-declarative"
        fixes = ["repair the source figure or report layout and validate again"]
        if code == "language/non-declarative":
            fixes.insert(0, "将内部问题改为陈述式标题，例如“GRN 候选 TF–target 关系”")
        entries.append({"code": code, "severity": "error", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": fixes})
    for message in warnings:
        entries.append({"code": "review/manual-check", "severity": "warning", "message": message, "subject": {"path": subject}, "evidence": {}, "supportedFixes": ["review the rendered DOCX"]})
    return entries


def _text(root: ET.Element) -> str:
    return "".join(node.text or "" for node in root.findall(".//w:t", NS))


def _xml_parts(archive: zipfile.ZipFile) -> list[tuple[str, ET.Element]]:
    parts: list[tuple[str, ET.Element]] = []
    for name in archive.namelist():
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        if name in {"word/styles.xml", "word/settings.xml", "word/fontTable.xml", "word/theme/theme1.xml"}:
            continue
        try:
            parts.append((name, ET.fromstring(archive.read(name))))
        except ET.ParseError:
            # document.xml is handled by inspect() and gets a hard error; an
            # optional header/footer parse failure is reported there as well.
            continue
    return parts


def extract_template_markers(path: Path) -> dict[str, object]:
    """Return visible ``[[...]]`` markers and bookmark names from a DOCX.

    The result is intentionally read-only and JSON-serialisable so a renderer
    can preflight a template before opening it with python-docx.
    """
    markers: list[str] = []
    bookmarks: dict[str, list[str]] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for part_name, root in _xml_parts(archive):
                active: list[str] = []
                for node in root.iter():
                    local = node.tag.rsplit("}", 1)[-1]
                    if local == "bookmarkStart":
                        name = node.get(f"{{{NS['w']}}}name")
                        if name:
                            active.append(name)
                    elif local == "bookmarkEnd":
                        bid = node.get(f"{{{NS['w']}}}id")
                        # End tags do not carry the name; keeping the stack
                        # conservative is preferable to guessing across runs.
                        if active:
                            active.pop()
                    elif local == "t" and node.text:
                        for match in TEMPLATE_MARKER.findall(node.text):
                            markers.append(match)
                            if active:
                                bookmarks.setdefault(match, []).extend(active)
                # Markers split across runs are recovered from paragraph text.
                for paragraph in root.findall(".//w:p", NS):
                    paragraph_text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
                    for match in TEMPLATE_MARKER.findall(paragraph_text):
                        if match not in markers:
                            markers.append(match)
    except (OSError, zipfile.BadZipFile):
        return {"markers": [], "bookmarks": {}, "error": f"invalid DOCX: {path}"}
    return {
        "markers": list(dict.fromkeys(markers)),
        "bookmarks": {key: list(dict.fromkeys(value)) for key, value in bookmarks.items()},
    }


def _marker_bookmark_name(marker: str) -> str:
    body = marker[2:-2].strip().lower()
    special = {
        "qc.condition": "slot_analysis_qc_condition",
        "results.condition": "slot_analysis_results_condition",
    }
    if body in special:
        return special[body]
    body = re.sub(r"[^a-z0-9]+", "_", body).strip("_")
    return f"slot_{body}"


def _color(value: str | None) -> str:
    return (value or "").lstrip("#").upper()[:6]


def _note_style_issues(root: ET.Element) -> tuple[int, list[str]]:
    """Inspect Note callouts where OOXML exposes deterministic style values."""
    note_count = 0
    issues: list[str] = []
    for table in root.findall(".//w:tbl", NS):
        table_text = _text(table)
        if not NOTE_TEXT.search(table_text):
            continue
        note_count += 1
        cells = table.findall(".//w:tc", NS)
        fills = {
            _color(node.get(f"{{{NS['w']}}}fill"))
            for cell in cells
            for node in cell.findall(".//w:shd", NS)
            if node.get(f"{{{NS['w']}}}fill")
        }
        border_colors = {
            _color(node.get(f"{{{NS['w']}}}color"))
            for node in table.findall(".//w:tcBorders/*", NS)
            + table.findall(".//w:pBdr/*", NS)
            if node.get(f"{{{NS['w']}}}color")
        }
        label_colors: set[str] = set()
        # ElementTree's XPath subset cannot express a text predicate portably;
        # inspect each run and only retain colours attached to a run containing
        # the visible Note label.
        for cell in cells:
            for run in cell.findall(".//w:r", NS):
                run_text = "".join(node.text or "" for node in run.findall(".//w:t", NS))
                if "Note" not in run_text:
                    continue
                label_colors.update(
                    _color(node.get(f"{{{NS['w']}}}val"))
                    for node in run.findall(".//w:color", NS)
                    if node.get(f"{{{NS['w']}}}val")
                )
        if EXPECTED_NOTE_COLORS["fill"] not in fills:
            issues.append("Note callout missing fill #DDEBF7")
        if EXPECTED_NOTE_COLORS["border"] not in border_colors:
            issues.append("Note callout missing border #5B9BD5")
        if EXPECTED_NOTE_COLORS["label"] not in label_colors:
            issues.append("Note label missing color #2F75B5")
    return note_count, issues


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).strip()


def _is_caption_paragraph(paragraph: ET.Element) -> bool:
    """Use the semantic Word style when a caption text omits a literal label."""
    styles = {
        node.get(f"{{{NS['w']}}}val", "").lower()
        for node in paragraph.findall("./w:pPr/w:pStyle", NS)
    }
    return bool(styles.intersection({"caption", "imagecaption", "tablecaption", "figurecaption"}))


def _body_blocks(document: ET.Element) -> list[tuple[str, ET.Element, str]]:
    body = document.find(".//w:body", NS)
    if body is None:
        return []
    blocks: list[tuple[str, ET.Element, str]] = []
    for child in list(body):
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            blocks.append(("p", child, _paragraph_text(child)))
        elif local == "tbl":
            blocks.append(("tbl", child, _text(child).strip()))
    return blocks


def inspect(
    path: Path,
    final: bool = False,
    *,
    require_note: bool = False,
    expected_markers: set[str] | None = None,
) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    template_markers: dict[str, object] = {"markers": [], "bookmarks": {}}
    note_count = 0
    note_style_issues: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
            parts = _xml_parts(archive)
            template_markers = extract_template_markers(path)
            note_count, note_style_issues = _note_style_issues(document)
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        message = f"invalid DOCX: {exc}"
        return {"status": "BLOCKED", "errors": [message], "warnings": [], "draft_markers": 0, "diagnostics": make_diagnostics([message], [], str(path))}
    drawings = document.findall(".//pic:pic", NS)
    embeds = [node.get(f"{{{NS['r']}}}embed") for node in document.findall(".//a:blip", NS)]
    crops: list[dict[str, str]] = []
    for node in document.findall(".//a:srcRect", NS):
        attrs = {key: value for key, value in node.attrib.items() if value not in (None, "0", "")}
        if attrs:
            crops.append(attrs)
    texts = [node.text or "" for node in document.findall(".//w:t", NS)]
    all_texts = list(texts)
    for part_name, part_root in parts:
        if part_name != "word/document.xml":
            all_texts.extend(node.text or "" for node in part_root.findall(".//w:t", NS))
    continuations = [text for text in texts if CONTINUATION.search(text)]
    visible_questions = [text for text in texts if "http://" not in text and "https://" not in text and QUESTION.search(text)]
    unresolved = [text for text in all_texts if PLACEHOLDER.search(text)]
    draft_markers = [text for text in texts if DRAFT_MARKER.search(text)]
    marketing = [text for text in all_texts if MARKETING.search(text)]
    corruption = [text for text in all_texts if CORRUPTION.search(text)]
    repeated_phrases = [text for text in all_texts if REPEATED_WORD.search(text)]
    markers = list(template_markers.get("markers", []))
    bookmark_issues: list[str] = []
    bookmark_map = template_markers.get("bookmarks", {})
    if isinstance(bookmark_map, dict):
        for marker in markers:
            marker_body = marker[2:-2].strip().upper()
            # Column markers are prototype text inside a table row.  The
            # caption/table anchor is the stable bookmark for that row group;
            # requiring one bookmark per column creates noise and does not add
            # a usable insertion point.
            if marker_body.startswith(("RESULT.", "OUTPUT.", "VERSION.")):
                continue
            expected = _marker_bookmark_name(marker)
            actual = bookmark_map.get(marker, [])
            if actual and expected not in actual:
                bookmark_issues.append(f"template marker {marker} is not wrapped by {expected}")
            elif not actual:
                bookmark_issues.append(f"template marker {marker} has no slot bookmark {expected}")
    if expected_markers is not None:
        missing_expected = sorted(set(expected_markers) - set(markers))
        if missing_expected:
            errors.append(f"template markers missing: {missing_expected}")
    if markers:
        unresolved_markers = [text for text in all_texts if TEMPLATE_MARKER.search(text)]
        if unresolved_markers:
            # Keep the marker count distinct from generic TODO markers.
            unresolved.extend(unresolved_markers)
    if bookmark_issues:
        message = f"template slot bookmark issues found: {len(bookmark_issues)}"
        (errors if final else warnings).append(message)
    paragraphs = document.findall(".//w:body/w:p", NS)
    caption_gaps: list[str] = []
    title_gaps: list[str] = []
    blocks = _body_blocks(document)
    paragraph_indices = {id(node): index for index, (kind, node, _) in enumerate(blocks) if kind == "p"}
    for index, paragraph in enumerate(paragraphs):
        if paragraph.find(".//w:drawing", NS) is None:
            continue
        block_index = paragraph_indices.get(id(paragraph))
        next_text = ""
        next_paragraph = None
        if block_index is not None:
            for candidate_kind, candidate, candidate_text in blocks[block_index + 1 :]:
                if candidate_kind == "p" and not candidate_text:
                    continue
                if candidate_kind != "p":
                    caption_gaps.append(f"drawing paragraph {index} has a non-paragraph block before caption")
                    break
                next_text = candidate_text
                next_paragraph = candidate
                break
        if not next_text or (not CAPTION.search(next_text) and not _is_caption_paragraph(next_paragraph)):
            caption_gaps.append(f"drawing paragraph {index} has no adjacent caption")
        elif next_paragraph is not None and next_paragraph.find(".//w:pageBreakBefore", NS) is not None:
            caption_gaps.append(f"drawing paragraph {index} caption starts after a page break")
        if block_index is not None:
            previous_text = ""
            for candidate_kind, candidate, candidate_text in reversed(blocks[:block_index]):
                if candidate_kind == "p" and candidate_text:
                    previous_text = candidate_text
                    break
            if not FIGURE_TITLE.search(previous_text):
                title_gaps.append(f"drawing paragraph {index} has no preceding numbered figure title")
    if crops:
        errors.append(f"non-zero srcRect found: {len(crops)}")
    if continuations:
        errors.append(f"continuation figure labels found: {len(continuations)}")
    if visible_questions:
        message = f"non-declarative visible text found: {len(visible_questions)}"
        errors.append(message)
    if unresolved:
        message = f"unresolved template markers found: {len(unresolved)}"
        (errors if final else warnings).append(message)
    if draft_markers:
        message = f"draft scaffold marker found: {len(draft_markers)}"
        (errors if final else warnings).append(message)
    if marketing:
        errors.append(f"marketing text found: {len(marketing)}")
    if corruption:
        errors.append(f"encoding corruption markers found: {len(corruption)}")
    if repeated_phrases:
        errors.append(f"repeated phrases found: {len(repeated_phrases)}")
    if caption_gaps:
        message = f"figure caption adjacency issues found: {len(caption_gaps)}"
        (errors if final else warnings).append(message)
    if title_gaps:
        message = f"figure title adjacency issues found: {len(title_gaps)}"
        (errors if final else warnings).append(message)
    if require_note and note_count == 0:
        message = "required Note callout is missing"
        (errors if final else warnings).append(message)
    if note_style_issues:
        message = f"Note callout style issues found: {len(note_style_issues)}"
        (errors if final else warnings).append(message)
    media_reuse = {item for item in embeds if item and embeds.count(item) > 1}
    if media_reuse and crops:
        errors.append("a source media is repeated with crop structure")
    if errors:
        status = "BLOCKED"
    elif not final:
        status = "EVIDENCE_NEEDED"
        warnings.append("DOCX structure checked without --final; visual/release gate is still required")
    elif warnings:
        status = "EVIDENCE_NEEDED"
    else:
        status = "PASS"
    result = {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "drawings": len(drawings),
        "embedded_media": len(embeds),
        "unique_media": len(set(item for item in embeds if item)),
        "nonzero_crops": len(crops),
        "continuations": len(continuations),
        "visible_questions": len(visible_questions),
        "unresolved_markers": len(set(unresolved)),
        "template_markers": markers,
        "template_bookmark_issues": bookmark_issues,
        "note_callouts": note_count,
        "note_style_issues": note_style_issues,
        "draft_markers": len(draft_markers),
        "marketing_text": len(marketing),
        "encoding_corruption": len(corruption),
        "repeated_phrases": len(repeated_phrases),
        "caption_adjacency_issues": len(caption_gaps),
        "final": final,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }
    result["diagnostics"] = make_diagnostics(errors, warnings, str(path))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--require-note", action="store_true", help="require a styled semantic Note callout")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = inspect(args.docx, final=args.final, require_note=args.require_note)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"DOCX_STRUCTURE_{result['status']} drawings={result.get('drawings', 0)} crops={result.get('nonzero_crops', 0)} continuations={result.get('continuations', 0)}")
        for item in result["errors"]:
            print(item, file=sys.stderr)
        for item in result["warnings"]:
            print(item)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
