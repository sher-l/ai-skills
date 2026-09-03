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
sys.path.insert(0, str(SCRIPTS))
import diagnostic_output


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
        self.assertIn("证据包", result.stdout)

    def test_init_and_contract_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "r,python")
            self.assertEqual(made.returncode, 0, made.stderr)
            module_root = out.parent
            self.assertTrue((module_root / "module.config.ini").is_file())
            self.assertTrue((module_root / "run.sh").is_file())
            for stage in ("calculate", "plot", "report"):
                self.assertTrue((module_root / "scripts" / stage / "main.R").is_file())
                self.assertTrue((module_root / "scripts" / stage / "main.py").is_file())
            self.assertTrue((module_root / "scripts" / "init.R").is_file())
            self.assertTrue((module_root / "scripts" / "init.py").is_file())
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

    def test_init_scaffolds_ini_and_declared_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run(
                "init_code_contract.py",
                "--module", "demo",
                "--output", str(out),
                "--languages", "python",
                "--with-plot", "--with-report", "--with-full",
            )
            self.assertEqual(made.returncode, 0, made.stderr)
            module_root = out.parent
            self.assertTrue((module_root / "module.config.ini").is_file())
            self.assertTrue((module_root / "run.sh").is_file())
            self.assertTrue((module_root / "run.sh").stat().st_mode & 0o111)
            for stage in ("calculate", "plot", "report"):
                self.assertTrue((module_root / "scripts" / stage / "main.py").is_file())
            self.assertTrue((module_root / "scripts" / "init.py").is_file())
            self.assertFalse((out / "module.config.ini").exists())
            self.assertFalse(any(path.name.startswith("config.") for path in out.iterdir()))
            config = (module_root / "module.config.ini").read_text(encoding="utf-8")
            self.assertIn("[stages]", config)
            self.assertIn("enabled = calculate,plot,report,full", config)
            contract = json.loads((out / "code_contract.json").read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in contract["stages"]], ["init", "calculate", "plot", "report", "full"])
            self.assertEqual(contract["full"]["expands_to"], ["calculate", "plot", "report"])
            self.assertNotIn("init", contract["full"]["expands_to"])
            checked = run("bio_code.py", "stage", "init", "-c", str(module_root / "module.config.ini"), "--json")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            plot_checked = run("bio_code.py", "stage", "plot", "-c", str(module_root / "module.config.ini"), "--json")
            self.assertEqual(plot_checked.returncode, 0, plot_checked.stderr)

    def test_stage_validator_blocks_unmet_reuse_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "module.config.ini"
            config.write_text("[module]\nname = demo\n[stages]\nenabled = report\n", encoding="utf-8")
            checked = run("validate_stage_contract.py", "report", "-c", str(config), "--json")
            self.assertNotEqual(checked.returncode, 0)
            payload = json.loads(checked.stdout)
            self.assertIn("report 需要在 stages.enabled 中声明 calculate 和 plot", "\n".join(payload["errors"]))
            self.assertEqual(payload["exit_code"], 2)

    def test_full_stage_uses_one_log_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "module.config.ini"
            config.write_text("[module]\nname = demo\n[stages]\nenabled = calculate,plot,report,full\n", encoding="utf-8")
            output = root / "full"
            (output / "log").mkdir(parents=True)
            (output / "log" / "calculate.log").write_text("错误\n", encoding="utf-8")
            checked = run("validate_stage_contract.py", "full", "-c", str(config), "--output", str(output), "--json")
            self.assertNotEqual(checked.returncode, 0)
            payload = json.loads(checked.stdout)
            self.assertIn("只能使用 log/full.log", "\n".join(payload["errors"]))

    def test_init_default_declares_all_business_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "python")
            self.assertEqual(made.returncode, 0, made.stderr)
            contract = json.loads((out / "code_contract.json").read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in contract["stages"]], ["init", "calculate", "plot", "report", "full"])
            self.assertEqual(
                (out.parent / "module.config.ini").read_text(encoding="utf-8").split("enabled = ", 1)[1].splitlines()[0],
                "calculate,plot,report,full",
            )

    def test_scaffold_does_not_rewrite_existing_root_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = Path(temp) / "module"
            module.mkdir()
            config = module / "module.config.ini"
            config.write_text("[module]\nname = kept\nlanguage = r\n", encoding="utf-8")
            out = module / ".code-contract"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "python")
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertEqual(config.read_text(encoding="utf-8"), "[module]\nname = kept\nlanguage = r\n")

    def test_generated_run_sh_keeps_init_and_full_log_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "python")
            self.assertEqual(made.returncode, 0, made.stderr)
            module_root = out.parent
            init_run = subprocess.run(
                ["./run.sh", "init", "-c", "module.config.ini"],
                cwd=module_root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init_run.returncode, 0, init_run.stderr)
            self.assertFalse((module_root / "log").exists())
            full_run = subprocess.run(
                ["./run.sh", "full", "-c", "module.config.ini"],
                cwd=module_root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(full_run.returncode, 0)
            self.assertTrue((module_root / "log" / "full.log").is_file())
            for sibling in ("calculate.log", "plot.log", "report.log"):
                self.assertFalse((module_root / "log" / sibling).exists())

    def test_generated_run_sh_passes_output_root_to_business_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "python")
            self.assertEqual(made.returncode, 0, made.stderr)
            module_root = out.parent
            (module_root / "scripts" / "calculate" / "main.py").write_text(
                "from pathlib import Path\nimport sys\nPath(sys.argv[3]).mkdir(parents=True, exist_ok=True)\nPath(sys.argv[3], 'received.txt').write_text(sys.argv[2], encoding='utf-8')\n",
                encoding="utf-8",
            )
            target = Path(temp) / "published"
            result = subprocess.run(
                ["./run.sh", "calculate", "-c", "module.config.ini", "-o", str(target)],
                cwd=module_root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / "received.txt").read_text(encoding="utf-8"), "--output")

    def test_init_rejects_invalid_ini_without_creating_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "module.config.ini"
            config.write_text("not an ini", encoding="utf-8")
            out = root / "workspace"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "-c", str(config))
            self.assertEqual(made.returncode, 2)
            self.assertIn("错误类型: CONFIG_ERROR", made.stderr)
            self.assertFalse(out.exists())

    def test_public_init_config_mode_is_zero_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "module.config.ini"
            config.write_text("[module]\nname = demo\n", encoding="utf-8")
            checked = run("bio_code.py", "init", "-c", str(config), "--json")
            self.assertEqual(checked.returncode, 0, checked.stderr)
            payload = json.loads(checked.stdout)
            self.assertEqual(payload["status"], "PASS")
            self.assertFalse((root / "log").exists())

    def test_public_init_creates_one_config_file_without_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = Path(temp) / "module"
            out = module / ".code-contract"
            made = run("init_code_contract.py", "--module", "demo", "--output", str(out), "--languages", "python")
            self.assertEqual(made.returncode, 0, made.stderr)
            target = Path(temp) / "caller.config.ini"
            module_run = subprocess.run(
                ["./run.sh", "init", "-c", str(target)],
                cwd=module,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(module_run.returncode, 0, module_run.stderr)
            self.assertTrue(target.is_file())
            self.assertFalse((Path(temp) / "config").exists())
            self.assertFalse((module / "log").exists())

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
            machine = run("validate_code_contract.py", str(path), "--json")
            self.assertNotEqual(machine.returncode, 0)
            payload = json.loads(machine.stdout)
            self.assertTrue(payload["diagnostics"])
            self.assertIn("error_type", payload["diagnostics"][0])
            self.assertIn("content", payload["diagnostics"][0])
            self.assertEqual(payload["exit_code"], 2)
            self.assertIn("退出码: 2", plain.stderr)

    def test_error_exit_code_categories(self) -> None:
        self.assertEqual(diagnostic_output.exit_code([], status="PASS"), 0)
        self.assertEqual(diagnostic_output.exit_code(["runtime failed"], domain="runtime"), 1)
        self.assertEqual(diagnostic_output.exit_code(["missing config field"], domain="contract"), 2)
        self.assertEqual(diagnostic_output.exit_code(["dependency package is unavailable"], domain="runtime"), 3)

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

    def test_final_contract_requires_five_stage_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = {
                "schema_version": "0.1.0", "module": "demo", "description": "d",
                "help": {"summary": "s", "commands": {"calculate": "run"}},
                "quality_profile": "release", "effort_profile": "mechanical", "max_repair_rounds": 2,
                "result_layout": "flat", "canonical_source": "stage.R", "source_review": "doc/source-review.md",
                "stages": [{"id": "calculate", "purpose": "p", "inputs": [], "outputs": [], "method": {}, "parameters": {}, "seed": 1, "non_degenerate": "n"}],
                "inputs": [], "outputs": [], "evidence_pack": "pack.json",
            }
            path = root / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = run("validate_code_contract.py", str(path), "--final")
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("requires stages", checked.stderr)

    def test_declared_nonflat_layout_is_blocked_in_v22(self) -> None:
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
            self.assertIn("result_layout must be flat", checked.stderr)

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
            text = text.replace("| OFF-01 | 填写官方资料标题 | 待填写官方资料地址 | 填写版本或 commit |", "| OFF-01 | Official API | https://example.org/api | 1.0 |", 1)
            text = text.replace("| RUN-01 | 填写实际命令 | 填写 run id | 填写相对日志或产物 | PENDING |", "| RUN-01 | python calculate.py module.config.ini | run-01 | run.json | PASS |", 1)
            text = text.replace("| CK-01 | 填写可测试的科学定义 | OFF-01 | 填写源码路径和位置 | RUN-01 | 填写官方精确定义 | 填写函数/行和行为 | 填写运行或产物观察 | PENDING | 填写决策或理由 |", "| CK-01 | score definition | OFF-01 | calculate.py | RUN-01 | official score | implementation differs | observed score | CONFLICT | DECISION_REQUIRED: owner decision |", 1)
            document.write_text(text, encoding="utf-8")
            conflict = run("bio_code.py", "source-review", "validate", str(document), "--source-root", str(root), "--json")
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn('"status": "DECISION_REQUIRED"', conflict.stdout)
            self.assertIn("DECISION_REQUIRED", conflict.stdout)


if __name__ == "__main__":
    unittest.main()
