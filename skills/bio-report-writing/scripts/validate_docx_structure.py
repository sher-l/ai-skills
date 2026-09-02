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


def inspect(path: Path, final: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
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
    continuations = [text for text in texts if CONTINUATION.search(text)]
    visible_questions = [text for text in texts if "http://" not in text and "https://" not in text and QUESTION.search(text)]
    unresolved = [text for text in texts if PLACEHOLDER.search(text)]
    draft_markers = [text for text in texts if DRAFT_MARKER.search(text)]
    marketing = [text for text in texts if MARKETING.search(text)]
    corruption = [text for text in texts if CORRUPTION.search(text)]
    repeated_phrases = [text for text in texts if REPEATED_WORD.search(text)]
    paragraphs = document.findall(".//w:body/w:p", NS)
    caption_gaps: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        if paragraph.find(".//w:drawing", NS) is None:
            continue
        next_text = ""
        next_paragraph = None
        for candidate in paragraphs[index + 1 :]:
            candidate_text = "".join(node.text or "" for node in candidate.findall(".//w:t", NS)).strip()
            if candidate_text:
                next_text = candidate_text
                next_paragraph = candidate
                break
        if not next_text or not CAPTION.search(next_text):
            caption_gaps.append(f"drawing paragraph {index} has no adjacent caption")
        elif next_paragraph is not None and next_paragraph.find(".//w:pageBreakBefore", NS) is not None:
            caption_gaps.append(f"drawing paragraph {index} caption starts after a page break")
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
        "unresolved_markers": len(unresolved),
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
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = inspect(args.docx, final=args.final)
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
