#!/usr/bin/env python3
"""Create the neutral DOCX style reference used by the report builder."""
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor
    except ImportError:
        print("STYLE_REFERENCE_BLOCKED: install optional python-docx", file=sys.stderr)
        return 2
    output = Path(__file__).resolve().parents[1] / "assets" / "report-style-reference.docx"
    document = Document()
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    styles = document.styles
    for name, size, bold, color in (("Normal", 11.5, False, None), ("Title", 22, True, "0F4761"), ("Heading 1", 16, True, "0F4761"), ("Heading 2", 14, True, "0F4761"), ("Heading 3", 12, True, "0F4761"), ("Caption", 9.5, True, "2F75B5")):
        style = styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = bold
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        if color:
            style.font.color.rgb = RGBColor.from_string(color)
    title = document.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("生信分析报告样式参考")
    document.add_heading("分析结果与解读", level=1)
    paragraph = document.add_paragraph()
    paragraph.add_run("结果：").bold = True
    paragraph.add_run("此处仅放来自 evidence pack 的已确认事实。")
    note = document.add_table(rows=1, cols=1)
    note.cell(0, 0).text = "Note｜说明：解释边界和比较方向应紧邻相关结果。"
    note.cell(0, 0).paragraphs[0].style = "Normal"
    caption = document.add_paragraph(style="Caption")
    caption.add_run("Figure 1: 完整源图及其逐 panel 图注。")
    document.add_heading("软件与资源版本", level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, ("软件/资源", "版本", "用途")):
        cell.text = value
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    print(f"STYLE_REFERENCE_PASS output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
