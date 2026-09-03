#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        text=True,
        capture_output=True,
        check=False,
    )


class CodeSkillSmoke(unittest.TestCase):
    def test_unified_cli_routes_to_contract_validator(self) -> None:
        result = run("bio_code.py", "validate", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("contract", result.stdout)

    def test_unified_cli_exposes_evidence_validator(self) -> None:
        result = run("bio_code.py", "evidence", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("evidence pack", result.stdout.lower())

    def test_init_and_contract_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "r,python")
            self.assertEqual(made.returncode, 0, made.stderr)
            contract = out / "code_contract.json"
            self.assertFalse((out / "doc" / "source-review.md").exists())
            checked = run("validate_code_contract.py", str(contract))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("EVIDENCE_NEEDED", checked.stdout)
            rooted = run("validate_code_contract.py", str(contract), "--source-root", str(out))
            self.assertNotEqual(rooted.returncode, 0)
            self.assertIn("EVIDENCE_NEEDED", rooted.stdout)
            pack_checked = run("validate_evidence_pack.py", str(out / "analysis_evidence_pack.json"))
            self.assertNotEqual(pack_checked.returncode, 0)  # starter has no analysis point
            final = run("validate_code_contract.py", str(contract), "--final")
            self.assertNotEqual(final.returncode, 0)

    def test_placeholder_is_blocked_when_scanning_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "stage.R"
            source.write_text("# TODO: replace\n", encoding="utf-8")
            contract = {
                "schema_version": "0.1.0",
                "module": "demo",
                "description": "demo module description",
                "help": {"summary": "demo", "commands": {"calculate": "run"}},
                "quality_profile": "draft",
                "effort_profile": "mechanical",
                "max_repair_rounds": 2, "result_layout": "flat",
                "canonical_source": "stage.R",
                "stages": [{"id": "calculate", "purpose": "p", "inputs": [], "outputs": [], "method": {"name": "m", "version": "1"}, "parameters": {}, "seed": 1, "non_degenerate": "n"}],
                "inputs": [],
                "outputs": [],
                "statistics": {"statistical_unit": "sample", "comparison": {"target": "a", "reference": "b", "direction": "a-b"}, "correction": "none", "thresholds": {}},
                "plot": {"figure_manifest": "figure_manifest.json"},
                "evidence_pack": "analysis_evidence_pack.json",
            }
            contract_path = root / "code_contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            checked = run("validate_code_contract.py", str(contract_path), "--source-root", str(root))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("placeholder", checked.stdout)
            final = run("validate_code_contract.py", str(contract_path), "--source-root", str(root), "--final")
            self.assertNotEqual(final.returncode, 0)
            self.assertIn("placeholder", final.stderr)

    def test_figure_manifest_requires_existing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "figure_manifest.json"
            manifest.write_text(json.dumps({"schema_version": "0.1.0", "figures": [{"id": "Figure 1", "source": "missing.png", "formats": ["png", "pdf"], "width": 6, "height": 4, "dpi": 300, "font": "Arial", "renderer": "cairo", "provenance": {"table": "result.tsv"}}]}), encoding="utf-8")
            checked = run("validate_figure_manifest.py", str(manifest), "--root", str(root))
            self.assertNotEqual(checked.returncode, 0)

    def test_figure_manifest_release_requires_both_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "figure.png"
            source.write_bytes(b"not-an-image-but-a-declared-source")
            manifest = root / "figure_manifest.json"
            manifest.write_text(json.dumps({"schema_version": "0.1.0", "figures": [{"id": "Figure-1", "source": "figure.png", "formats": ["png"], "width": 6, "height": 4, "dpi": 300, "font": "Arial", "renderer": "cairo", "provenance": {"table": "result.tsv"}}]}), encoding="utf-8")
            checked = run("validate_figure_manifest.py", str(manifest), "--root", str(root), "--final")
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("both PNG and PDF", checked.stderr)

    def test_unknown_contract_field_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = {
                "schema_version": "0.1.0", "module": "demo", "description": "d",
                "help": {"summary": "s", "commands": {}}, "quality_profile": "draft",
                "effort_profile": "mechanical", "max_repair_rounds": 2, "result_layout": "flat",
                "canonical_source": "stage.R", "stages": [{"id": "x", "purpose": "p", "inputs": [], "outputs": [], "method": {}, "parameters": {}, "seed": 1, "non_degenerate": "n"}],
                "inputs": [], "outputs": [], "statistics": {"statistical_unit": "sample", "comparison": {"target": "a", "reference": "b", "direction": "a-b"}, "correction": "none", "thresholds": {}},
                "plot": {"figure_manifest": "fig.json"}, "evidence_pack": "pack.json", "unexpected": True,
            }
            path = root / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = run("validate_code_contract.py", str(path))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("unknown top-level", checked.stderr)

    def test_error_output_names_type_and_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text("{}", encoding="utf-8")
            plain = run("validate_code_contract.py", str(path))
            self.assertNotEqual(plain.returncode, 0)
            self.assertIn("错误类型:", plain.stderr)
            self.assertIn("错误内容:", plain.stderr)
            self.assertIn("修复建议:", plain.stderr)
            self.assertIn("退出码:", plain.stderr)
            machine = run("validate_code_contract.py", str(path), "--json")
            self.assertNotEqual(machine.returncode, 0)
            payload = json.loads(machine.stdout)
            self.assertTrue(payload["diagnostics"])
            self.assertIn("error_type", payload["diagnostics"][0])
            self.assertIn("content", payload["diagnostics"][0])

    def test_result_layout_requires_flat_numbered_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = {
                "schema_version": "0.1.0", "module": "demo", "description": "d",
                "help": {"summary": "s", "commands": {"calculate": "run"}}, "quality_profile": "draft",
                "effort_profile": "mechanical", "max_repair_rounds": 2, "result_layout": "flat",
                "canonical_source": "stage.R", "stages": [{"id": "x", "purpose": "p", "inputs": [], "outputs": [], "method": {}, "parameters": {}, "seed": 1, "non_degenerate": "n"}],
                "inputs": [], "outputs": [{"path": "result/tables/01.DEG_all.csv"}],
                "statistics": {"statistical_unit": "sample", "comparison": {"target": "a", "reference": "b", "direction": "a-b"}, "correction": "none", "thresholds": {}},
                "plot": {"figure_manifest": "fig.json"}, "evidence_pack": "pack.json",
            }
            path = root / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = run("validate_code_contract.py", str(path))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("directly under result", checked.stderr)

    def test_declared_nonflat_layout_does_not_trigger_flat_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = {
                "schema_version": "0.1.0", "module": "demo", "description": "d",
                "help": {"summary": "s", "commands": {"calculate": "run"}}, "quality_profile": "release",
                "effort_profile": "mechanical", "max_repair_rounds": 2, "result_layout": "module_contract",
                "canonical_source": "stage.R", "source_review": "doc/source-review.md",
                "stages": [{"id": "x", "purpose": "p", "inputs": [], "outputs": [{"path": "result/tables/value.csv"}], "method": {}, "parameters": {}, "seed": 1, "non_degenerate": "n"}],
                "inputs": [], "outputs": [{"path": "result/tables/value.csv"}], "evidence_pack": "pack.json",
            }
            (root / "stage.R").write_text("x <- 1\n", encoding="utf-8")
            path = root / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = run("validate_code_contract.py", str(path))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("EVIDENCE_NEEDED", checked.stdout)
            self.assertNotIn("directly under result", checked.stdout + checked.stderr)

    def test_source_review_init_and_conflict_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "calculate.py").write_text("print('ok')\n", encoding="utf-8")
            made = run("bio_code.py", "source-review", "init", "--module", "demo", "--source-root", str(root))
            self.assertEqual(made.returncode, 0, made.stderr)
            document = root / "doc" / "source-review.md"
            self.assertTrue(document.is_file())
            draft = run("bio_code.py", "source-review", "validate", str(document), "--source-root", str(root), "--json")
            self.assertNotEqual(draft.returncode, 0)
            self.assertIn('"status": "EVIDENCE_NEEDED"', draft.stdout)
            text = document.read_text(encoding="utf-8")
            text = text.replace("canonical_source: PENDING", "canonical_source: calculate.py")
            text = text.replace("review_status: DRAFT", "review_status: DECISION_REQUIRED")
            text = text.replace("| calculate.py | Python |", "| calculate.py | Python |", 1)
            text = text.replace("| candidate | no |", "| candidate | yes |", 1)
            text = text.replace("| OFF-01 | ADD official title | https://official.example/document | version-or-commit |", "| OFF-01 | Official API | https://example.org/api | 1.0 |", 1)
            text = text.replace("| RUN-01 | ADD exact command | ADD run id | ADD relative log/artifact | PENDING |", "| RUN-01 | python calculate.py config.yaml | run-01 | run.json | PASS |", 1)
            text = text.replace("| CK-01 | ADD one testable scientific definition | OFF-01 | ADD/source.R | RUN-01 | ADD exact official definition | ADD function/line and behavior | ADD run/artifact observation | PENDING | ADD decision or rationale |", "| CK-01 | score definition | OFF-01 | calculate.py | RUN-01 | official score | implementation differs | observed score | CONFLICT | DECISION_REQUIRED: owner decision |", 1)
            document.write_text(text, encoding="utf-8")
            conflict = run("bio_code.py", "source-review", "validate", str(document), "--source-root", str(root), "--json")
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn('"status": "DECISION_REQUIRED"', conflict.stdout)
            self.assertIn("DECISION_REQUIRED", conflict.stdout)


if __name__ == "__main__":
    unittest.main()
