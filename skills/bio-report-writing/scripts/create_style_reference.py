#!/usr/bin/env python3
"""Build the portable DOCX-first report template and style reference.

``report_template.docx`` is intentionally boring: a renderer can locate every
slot by its visible ``[[...]]`` marker or the accompanying Word bookmark,
replace the marker, and keep the fixed reader-facing chapter order.  The
sky-blue Note is emitted as explicit WordprocessingML so its fill, border and
label colour remain inspectable after a Quarto/Pandoc render.
"""
from __future__ import annotations

from pathlib import Path
import sys


NOTE_BORDER = "5B9BD5"
NOTE_FILL = "DDEBF7"
NOTE_LABEL = "2F75B5"
HEADING = "0F4761"


def _imports():
    """Load the optional DOCX dependency only when this generator runs."""
    try:
        from docx import Document
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("install optional python-docx") from exc
    return {
        "Document": Document,
        "WD_CELL_VERTICAL_ALIGNMENT": WD_CELL_VERTICAL_ALIGNMENT,
        "WD_TABLE_ALIGNMENT": WD_TABLE_ALIGNMENT,
        "WD_ALIGN_PARAGRAPH": WD_ALIGN_PARAGRAPH,
        "OxmlElement": OxmlElement,
        "qn": qn,
        "Cm": Cm,
        "Pt": Pt,
        "RGBColor": RGBColor,
    }


def _set(element, qn, name: str, value: str) -> None:
    element.set(qn(name if ":" in name else f"w:{name}"), value)


def _run_font(run, api, *, size: float = 11.5, color: str | None = None, bold: bool | None = None) -> None:
    run.font.name = "Times New Roman"
    run.font.size = api["Pt"](size)
    if bold is not None:
        run.bold = bold
    if color:
        run.font.color.rgb = api["RGBColor"].from_string(color)
    run._element.get_or_add_rPr().rFonts.set(api["qn"]("w:eastAsia"), "宋体")


def _configure_styles(document, api) -> None:
    qn, Pt, RGBColor = api["qn"], api["Pt"], api["RGBColor"]
    for name, size, bold, color in (
        ("Normal", 11.5, False, None),
        ("Title", 22, True, HEADING),
        ("Heading 1", 16, True, HEADING),
        ("Heading 2", 14, True, HEADING),
        ("Heading 3", 12, True, HEADING),
        ("Caption", 9.5, True, NOTE_LABEL),
    ):
        style = document.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = bold
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        if color:
            style.font.color.rgb = RGBColor.from_string(color)


def _configure_page(document, api) -> None:
    section = document.sections[0]
    section.page_width = api["Cm"](21.0)
    section.page_height = api["Cm"](29.7)
    section.top_margin = api["Cm"](2.2)
    section.bottom_margin = api["Cm"](2.0)
    section.left_margin = api["Cm"](2.0)
    section.right_margin = api["Cm"](2.0)


def _bookmark(paragraph, name: str, text: str, bookmark_id: int, api, *, color: str | None = None, bold: bool = False, size: float = 11.5):
    """Append a visible slot marker wrapped in a stable Word bookmark."""
    qn, OxmlElement = api["qn"], api["OxmlElement"]
    start = OxmlElement("w:bookmarkStart")
    _set(start, qn, "id", str(bookmark_id))
    _set(start, qn, "name", name)
    end = OxmlElement("w:bookmarkEnd")
    _set(end, qn, "id", str(bookmark_id))
    paragraph._p.append(start)
    run = paragraph.add_run(text)
    _run_font(run, api, size=size, color=color, bold=bold)
    paragraph._p.append(end)
    return run


class _Bookmarks:
    def __init__(self, api):
        self.api = api
        self.next_id = 1

    def add(self, paragraph, name: str, text: str, **kwargs):
        run = _bookmark(paragraph, name, text, self.next_id, self.api, **kwargs)
        self.next_id += 1
        return run


def _add_heading(document, text: str, level: int):
    return document.add_heading(text, level=level)


def _slot(document, bookmarks, marker: str, bookmark_name: str, *, style: str | None = None, align=None):
    paragraph = document.add_paragraph(style=style)
    if align is not None:
        paragraph.alignment = align
    bookmarks.add(paragraph, bookmark_name, marker)
    return paragraph


def _paragraph_shading_and_border(paragraph, api, *, color: str = NOTE_BORDER, fill: str = NOTE_FILL) -> None:
    """Apply the standard Note properties at paragraph level as a fallback."""
    qn, OxmlElement = api["qn"], api["OxmlElement"]
    ppr = paragraph._p.get_or_add_pPr()
    if ppr.find(qn("w:keepLines")) is None:
        ppr.append(OxmlElement("w:keepLines"))
    borders = ppr.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        ppr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        for key, value in (("val", "single"), ("sz", "8"), ("space", "6"), ("color", color)):
            _set(node, qn, key, value)
    shading = ppr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        ppr.append(shading)
    _set(shading, qn, "val", "clear")
    _set(shading, qn, "fill", fill)
    indent = ppr.find(qn("w:ind"))
    if indent is None:
        indent = OxmlElement("w:ind")
        ppr.append(indent)
    _set(indent, qn, "left", "200")
    _set(indent, qn, "right", "200")


def _cell_box(cell, api, *, color: str = NOTE_BORDER, fill: str = NOTE_FILL) -> None:
    """Write exact fill and four borders on a table cell."""
    qn, OxmlElement = api["qn"], api["OxmlElement"]
    tcpr = cell._tc.get_or_add_tcPr()
    shading = tcpr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tcpr.append(shading)
    _set(shading, qn, "val", "clear")
    _set(shading, qn, "fill", fill)
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        for key, value in (("val", "single"), ("sz", "8"), ("space", "0"), ("color", color)):
            _set(node, qn, key, value)
    parent = cell._tc.getparent()
    trpr = parent.get_or_add_trPr()
    if trpr.find(qn("w:cantSplit")) is None:
        trpr.append(OxmlElement("w:cantSplit"))


def _cell_margins(cell, api, value: str = "120") -> None:
    qn, OxmlElement = api["qn"], api["OxmlElement"]
    tcpr = cell._tc.get_or_add_tcPr()
    margins = tcpr.find(qn("w:tcMar"))
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tcpr.append(margins)
    for edge in ("top", "left", "bottom", "right"):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        _set(node, qn, "w", value)
        _set(node, qn, "type", "dxa")


def _row_rules(row, api, *, header: bool = False) -> None:
    qn, OxmlElement = api["qn"], api["OxmlElement"]
    trpr = row._tr.get_or_add_trPr()
    if trpr.find(qn("w:cantSplit")) is None:
        trpr.append(OxmlElement("w:cantSplit"))
    if header and trpr.find(qn("w:tblHeader")) is None:
        trpr.append(OxmlElement("w:tblHeader"))


def _keep_next(paragraph, api, value: bool = True) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    node = ppr.find(api["qn"]("w:keepNext"))
    if value and node is None:
        ppr.append(api["OxmlElement"]("w:keepNext"))
    elif not value and node is not None:
        ppr.remove(node)


def _style_table(table, api, *, header=True, alignments=None) -> None:
    table.style = "Table Grid"
    table.autofit = True
    for index, row in enumerate(table.rows):
        _row_rules(row, api, header=header and index == 0)
        for column, cell in enumerate(row.cells):
            _cell_margins(cell, api, "90")
            cell.vertical_alignment = api["WD_CELL_VERTICAL_ALIGNMENT"].CENTER
            for paragraph in cell.paragraphs:
                if alignments and index > 0:
                    paragraph.alignment = alignments[min(column, len(alignments) - 1)]
                for run in paragraph.runs:
                    _run_font(run, api, size=10.5, bold=index == 0, color=HEADING if index == 0 else None)


def _set_table_widths(table, api, widths_cm: tuple[float, ...]) -> None:
    """Keep long output headers readable in the fixed A4 text width."""
    table.autofit = False
    for row in table.rows:
        for cell, width in zip(row.cells, widths_cm):
            cell.width = api["Cm"](width)


def _add_note(document, bookmarks, api):
    """Add one visible one-cell sky-blue Note with a replaceable body slot."""
    table = document.add_table(rows=1, cols=1)
    table.alignment = api["WD_TABLE_ALIGNMENT"].CENTER
    table.autofit = True
    cell = table.cell(0, 0)
    cell.vertical_alignment = api["WD_CELL_VERTICAL_ALIGNMENT"].CENTER
    _cell_box(cell, api)
    _cell_margins(cell, api)
    paragraph = cell.paragraphs[0]
    _paragraph_shading_and_border(paragraph, api)
    label = paragraph.add_run("Note：")
    _run_font(label, api, color=NOTE_LABEL, bold=True)
    bookmarks.add(paragraph, "slot_note_direction", "[[NOTE:DIRECTION]]")
    return table


def _add_caption(document, bookmarks, figure_id: str = "F1"):
    paragraph = document.add_paragraph(style="Caption")
    bookmarks.add(paragraph, f"slot_figure_{figure_id.lower()}_caption", f"[[FIGURE:{figure_id}.CAPTION]]")
    return paragraph


def _add_figure_block(document, bookmarks, api, figure_id: str = "F1", number: int = 1):
    heading = document.add_heading(level=2)
    heading.add_run(f"图 {number}. ")
    bookmarks.add(heading, f"slot_figure_{figure_id.lower()}_title", f"[[FIGURE:{figure_id}.TITLE]]")
    source = document.add_paragraph()
    source.alignment = api["WD_ALIGN_PARAGRAPH"].CENTER
    # The marker is replaced by the complete source image.  A renderer may
    # clone this whole three-paragraph block for F2…Fn when the pack publishes
    # additional figures; absent figures remove the block rather than emit an
    # empty chapter or fake image.
    bookmarks.add(source, f"slot_figure_{figure_id.lower()}_source", f"[[FIGURE:{figure_id}.SOURCE]]")
    _paragraph_shading_and_border(source, api, color="B7C9D6", fill="F4F8FA")
    _keep_next(source, api)
    caption = _add_caption(document, bookmarks, figure_id)
    _keep_next(heading, api)
    _keep_next(caption, api)


def _add_result_table(document, bookmarks, api):
    paragraph = document.add_paragraph(style="Caption")
    paragraph.add_run("表 1. ")
    bookmarks.add(paragraph, "slot_table_results_caption", "[[TABLE:RESULTS.CAPTION]]")
    table = document.add_table(rows=2, cols=4)
    headers = ("指标", "数值", "单位", "结果来源")
    values = ("[[RESULT.NAME]]", "[[RESULT.VALUE]]", "[[RESULT.UNIT]]", "[[RESULT.SOURCE]]")
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for cell, value in zip(table.rows[1].cells, values):
        cell.text = value
    align = (api["WD_ALIGN_PARAGRAPH"].LEFT, api["WD_ALIGN_PARAGRAPH"].RIGHT,
             api["WD_ALIGN_PARAGRAPH"].LEFT, api["WD_ALIGN_PARAGRAPH"].LEFT)
    _style_table(table, api, alignments=align)
    _set_table_widths(table, api, (4.2, 2.5, 2.5, 7.8))
    return table


def _add_output_table(document, bookmarks, api):
    paragraph = document.add_paragraph(style="Caption")
    paragraph.add_run("表 2. ")
    bookmarks.add(paragraph, "slot_table_outputs_caption", "[[TABLE:OUTPUTS.CAPTION]]")
    table = document.add_table(rows=2, cols=5)
    headers = ("文件名", "类型", "内容", "用途", "消费者")
    values = ("[[OUTPUT.PATH]]", "[[OUTPUT.KIND]]", "[[OUTPUT.DESCRIPTION]]", "[[OUTPUT.PURPOSE]]", "[[OUTPUT.CONSUMERS]]")
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for cell, value in zip(table.rows[1].cells, values):
        cell.text = value
    align = tuple(api["WD_ALIGN_PARAGRAPH"].LEFT for _ in range(5))
    _style_table(table, api, alignments=align)
    _set_table_widths(table, api, (3.4, 1.5, 3.7, 4.0, 4.4))
    return table


def _add_version_table(document, bookmarks, api):
    paragraph = document.add_paragraph(style="Caption")
    paragraph.add_run("表 3. ")
    bookmarks.add(paragraph, "slot_table_versions_caption", "[[TABLE:VERSIONS.CAPTION]]")
    table = document.add_table(rows=2, cols=3)
    headers = ("软件或资源", "版本", "用途或来源")
    values = ("[[VERSION.NAME]]", "[[VERSION.VALUE]]", "[[VERSION.PURPOSE]]")
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for cell, value in zip(table.rows[1].cells, values):
        cell.text = value
    align = tuple(api["WD_ALIGN_PARAGRAPH"].LEFT for _ in range(3))
    _style_table(table, api, alignments=align)
    _set_table_widths(table, api, (5.2, 3.0, 8.8))
    return table


def build_report_template(api):
    """Create the full reusable DOCX template."""
    document = api["Document"]()
    _configure_page(document, api)
    _configure_styles(document, api)
    bookmarks = _Bookmarks(api)

    title = document.add_paragraph(style="Title")
    title.alignment = api["WD_ALIGN_PARAGRAPH"].CENTER
    bookmarks.add(title, "slot_report_title", "[[REPORT_TITLE]]")
    metadata = document.add_paragraph()
    metadata.add_run("读者：").bold = True
    bookmarks.add(metadata, "slot_report_audience", "[[REPORT_AUDIENCE]]")

    for heading, marker, name in (
        ("摘要", "[[REPORT_SUMMARY]]", "slot_report_summary"),
        ("数据范围与分析边界", "[[ANALYSIS_SCOPE]]", "slot_analysis_scope"),
        ("材料与方法", "[[ANALYSIS_METHOD]]", "slot_analysis_method"),
        ("质控与异常", "[[ANALYSIS_QC]]", "slot_analysis_qc"),
        ("分析结果与解读", "[[ANALYSIS_RESULT]]", "slot_analysis_result"),
    ):
        _add_heading(document, heading, 1)
        _slot(document, bookmarks, marker, name)
        if heading == "分析结果与解读":
            _add_note(document, bookmarks, api)
            _add_result_table(document, bookmarks, api)

    _add_heading(document, "综合结论", 1)
    _slot(document, bookmarks, "[[ANALYSIS_CONCLUSION]]", "slot_analysis_conclusion")

    _add_heading(document, "图件", 1)
    _add_figure_block(document, bookmarks, api, "F1", 1)

    _add_heading(document, "局限、未完成与待验证", 1)
    _slot(document, bookmarks, "[[ANALYSIS_LIMITATIONS]]", "slot_analysis_limitations")

    _add_heading(document, "输出文件说明", 1)
    _slot(document, bookmarks, "[[OUTPUTS_INTRO]]", "slot_outputs_intro")
    _add_output_table(document, bookmarks, api)

    _add_heading(document, "参考文献", 1)
    _slot(document, bookmarks, "[[REFERENCES]]", "slot_references")

    _add_heading(document, "软件与资源版本", 1)
    _add_version_table(document, bookmarks, api)
    return document


def build_style_reference(api):
    """Create a compact style sample retained for old one-off workflows."""
    document = api["Document"]()
    _configure_page(document, api)
    _configure_styles(document, api)
    bookmarks = _Bookmarks(api)
    title = document.add_paragraph(style="Title")
    title.alignment = api["WD_ALIGN_PARAGRAPH"].CENTER
    title.add_run("生信分析报告样式参考")
    _add_heading(document, "分析结果与解读", 1)
    paragraph = document.add_paragraph()
    paragraph.add_run("结果：").bold = True
    paragraph.add_run("此处仅放来自 evidence pack 的已确认事实。")
    _add_note(document, bookmarks, api)
    caption = document.add_paragraph(style="Caption")
    caption.add_run("图 1. 完整源图及其逐 panel 图注。")
    _add_heading(document, "软件与资源版本", 1)
    table = document.add_table(rows=2, cols=3)
    for cell, value in zip(table.rows[0].cells, ("软件/资源", "版本", "用途")):
        cell.text = value
    for cell, value in zip(table.rows[1].cells, ("[[VERSION.NAME]]", "[[VERSION.VALUE]]", "[[VERSION.PURPOSE]]")):
        cell.text = value
    _style_table(table, api)
    return document


def main() -> int:
    try:
        api = _imports()
    except RuntimeError as exc:
        print(f"STYLE_REFERENCE_BLOCKED: {exc}", file=sys.stderr)
        return 2
    assets = Path(__file__).resolve().parents[1] / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    template_path = assets / "report_template.docx"
    style_path = assets / "report-style-reference.docx"
    build_report_template(api).save(template_path)
    build_style_reference(api).save(style_path)
    print(f"REPORT_TEMPLATE_PASS output={template_path}")
    print(f"STYLE_REFERENCE_PASS output={style_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
