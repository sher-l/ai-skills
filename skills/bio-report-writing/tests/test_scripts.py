#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], text=True, capture_output=True, check=False)


def pack(path: Path) -> None:
    value = {
        "schema_version": "0.1.0",
        "module": "demo",
        "quality_profile": "draft",
        "result_layout": "flat",
        "evidence_targets": [{"id": "ET-01", "title": "主要分析结果"}],
        "analysis_points": [{
            "id": "AP-01", "title": "差异表达结果", "scope": "两个供体组的表达矩阵", "qc": "输入和顺序已核对",
            "inputs": [{"id": "IN-01", "path": "result/input.tsv", "identity": "demo"}],
            "method": {"name": "limma", "version": "3.58"}, "parameters": {"fdr": 0.05},
            "statistical_unit": "sample", "comparison": {"target": "case", "reference": "control", "direction": "case-control"},
            "results": [{"name": "n", "value": 4, "unit": "gene", "source": "result/01.DEG_all.tsv"}],
            "outputs": [{"id": "OUT-01", "path": "result/01.DEG_all.tsv", "kind": "table", "published": True, "purpose": "结果表", "consumers": ["project_analyst"]}],
            "figure_table_refs": [], "interpretation_level": "descriptive", "interpretation": "当前数据中的描述性结果", "limitations": ["样本范围"], "status": "complete", "next_step": "作为后续通路分析的输入"
        }]
    }
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


class ReportSkillSmoke(unittest.TestCase):
    def test_unified_cli_exposes_fixed_operations(self) -> None:
        result = run("bio_report.py", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skeleton", result.stdout)

    def test_fixed_pipeline_builds_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            output = root / "report-work"
            pack(evidence)
            result = run("bio_report.py", "run", "--evidence-pack", str(evidence), "--output-dir", str(output))
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn("EVIDENCE_NEEDED", result.stdout)
            self.assertTrue((output / "report_plan.json").is_file())
            self.assertTrue((output / "report_draft.md").is_file())
            self.assertTrue((output / "report.docx").is_file())

    def test_plan_skeleton_validate_and_docx(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            markdown = root / "draft.md"
            docx = root / "report.docx"
            pack(evidence)
            result = run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run("build_report_skeleton.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--output", str(markdown))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("## 摘要", markdown.read_text(encoding="utf-8"))
            self.assertIn("n=4 gene", markdown.read_text(encoding="utf-8"))
            result = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--markdown", str(markdown))
            self.assertNotEqual(result.returncode, 0)  # skeleton intentionally has evidence markers
            result = run("build_docx.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--output", str(docx))
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn("DRAFT", result.stdout)
            result = run("validate_docx_structure.py", str(docx))
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn("EVIDENCE_NEEDED", result.stdout)

    def test_question_and_placeholder_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            markdown = root / "draft.md"
            pack(evidence)
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            markdown.write_text("# 哪些结果？\n\n[[EVIDENCE_REQUIRED:x]]\n", encoding="utf-8")
            result = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--markdown", str(markdown))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("declarative", result.stderr)

    def test_docx_visible_question_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            docx = root / "report.docx"
            pack(evidence)
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            value = json.loads(plan.read_text(encoding="utf-8"))
            value["title"] = "哪些结果？"
            plan.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            built = run("build_docx.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--output", str(docx))
            self.assertNotEqual(built.returncode, 0)
            self.assertIn("declarative", built.stderr)

    def test_docx_question_is_blocked_without_final_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docx = Path(temp) / "question.docx"
            xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>当前 GRN 优先哪些 TF-target 关系？</w:t></w:r></w:p></w:body></w:document>"""
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr("word/document.xml", xml)
            checked = run("validate_docx_structure.py", str(docx))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("non-declarative", checked.stderr)

    def test_failed_skeleton_keeps_previous_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "report.md"
            output.write_text("trusted previous report\n", encoding="utf-8")
            result = run("build_report_skeleton.py", "--plan", str(root / "missing-plan.json"), "--evidence-pack", str(root / "missing-pack.json"), "--output", str(output))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "trusted previous report\n")

    def test_unknown_plan_field_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            pack(evidence)
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            value = json.loads(plan.read_text(encoding="utf-8"))
            value["unrequested_option"] = True
            plan.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            checked = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("unknown top-level", checked.stderr)

    def test_question_title_in_pack_is_blocked_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            pack(evidence)
            value = json.loads(evidence.read_text(encoding="utf-8"))
            value["analysis_points"][0]["title"] = "当前 GRN 优先哪些 TF-target 关系？"
            evidence.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            checked = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("declarative", checked.stderr)

    def test_unbounded_claim_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            pack(evidence)
            value = json.loads(evidence.read_text(encoding="utf-8"))
            value["analysis_points"][0]["interpretation"] = "该结果证明了治疗效果"
            evidence.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            checked = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("overclaim", checked.stderr)

    def test_bounded_negative_claim_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            pack(evidence)
            value = json.loads(evidence.read_text(encoding="utf-8"))
            value["analysis_points"][0]["interpretation"] = "该关联不能证明因果"
            evidence.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            checked = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence))
            self.assertNotEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("EVIDENCE_NEEDED", checked.stdout)

    def test_nonzero_docx_crop_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            docx = Path(temp) / "cropped.docx"
            xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><pic:pic><a:blip r:embed="rId1"/><a:srcRect l="50000"/></pic:pic></w:body></w:document>"""
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr("word/document.xml", xml)
            checked = run("validate_docx_structure.py", str(docx))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("srcRect", checked.stderr)

    def test_generic_builder_refuses_final_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            docx = root / "report.docx"
            pack(evidence)
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            result = run("build_docx.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--output", str(docx), "--final")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("draft-only", result.stderr)
            self.assertFalse(docx.exists())

    def test_path_escape_is_blocked_when_root_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "pack.json"
            plan = root / "plan.json"
            pack(evidence)
            value = json.loads(evidence.read_text(encoding="utf-8"))
            value["analysis_points"][0]["outputs"][0]["path"] = "../outside.csv"
            evidence.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            run("init_report_plan.py", "--evidence-pack", str(evidence), "--output", str(plan))
            result = run("validate_report_contract.py", "--plan", str(plan), "--evidence-pack", str(evidence), "--root", str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("relative", result.stderr)


if __name__ == "__main__":
    unittest.main()
