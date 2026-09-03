#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "route_module_task.py"


class RouteSmoke(unittest.TestCase):
    def test_unified_cli_exposes_route_and_validate(self) -> None:
        wrapper = ROOT / "scripts" / "module_scheduler.py"
        result = subprocess.run([sys.executable, str(wrapper), "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("route", result.stdout)

    def test_code_and_report_load(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT), "--module", "demo", "--task-type", "new", "--phase", "scope", "--changed-path", "scripts/calculate.R", "--changed-path", "scripts/report.py", "--has-report"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["route"], "ask-matt")
        self.assertIn("bio-code-standard", value["loaded_skills"])
        self.assertIn("bio-report-writing", value["loaded_skills"])
        self.assertEqual(value["work_kind"], "auto")

    def test_finish_adds_acceptance_checks(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT), "--module", "demo", "--task-type", "review", "--phase", "finish", "--quality-profile", "release", "--changed-path", "README.md", "--has-full", "--requires-review"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn("independent_test", value["required_checks"])
        self.assertIn("final_full", value["required_checks"])

    def test_unknown_route_field_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp) / "route.json"
            plan.write_text(json.dumps({"schema_version": "0.1.0", "module": "demo", "work_kind": "auto", "quality_profile": "draft", "effort_profile": "mechanical", "max_repair_rounds": 2, "route": "ask-matt", "phase": "scope", "loaded_skills": [], "required_checks": [], "blocked_reasons": [], "next_owner": "matt-executor", "unexpected": True}), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_route_plan.py"), str(plan)], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown top-level", result.stderr)

    def test_explicit_work_kind_avoids_path_guessing(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT), "--module", "demo", "--task-type", "new", "--phase", "scope", "--work-kind", "report", "--changed-path", "scripts/calculate.R"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn("bio-report-writing", value["loaded_skills"])
        self.assertNotIn("bio-code-standard", value["loaded_skills"])

    def test_review_loads_adapters_for_changed_surfaces(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT), "--module", "demo", "--task-type", "review", "--phase", "scope", "--changed-path", "scripts/calculate.R", "--changed-path", "scripts/report.py"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn("bio-code-standard", value["loaded_skills"])
        self.assertIn("bio-report-writing", value["loaded_skills"])

    def test_new_defaults_to_code_without_changed_paths(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "new",
                "--phase",
                "scope",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn("bio-code-standard", value["adapter_skills"])
        self.assertLess(
            value["required_checks"].index("source_review"),
            value["required_checks"].index("code_contract"),
        )

    def test_infer_keeps_module_for_library_callers(self) -> None:
        spec = importlib.util.spec_from_file_location("route_module_task", SCRIPT)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        value = module.infer(
            "new",
            [],
            False,
            False,
            False,
            False,
            "scope",
            "draft",
            "mechanical",
            "auto",
            2,
            module="demo",
        )
        self.assertEqual(value["module"], "demo")

    def test_report_contexts_share_checks_and_do_not_load_code(self) -> None:
        common = [
            sys.executable,
            str(SCRIPT),
            "--module",
            "demo",
            "--task-type",
            "new",
            "--phase",
            "build",
            "--work-kind",
            "report",
        ]
        plans = []
        for context in ("one-off", "module-reusable"):
            result = subprocess.run(
                [*common, "--report-context", context],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            plans.append(value)
            self.assertEqual(value["loaded_skills"], ["module-development-scheduler", "bio-report-writing"])
            self.assertNotIn("bio-code-standard", value["loaded_skills"])
        self.assertEqual(plans[0]["required_checks"], plans[1]["required_checks"])

    def test_coder_order_is_source_then_analysis_then_report(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "new",
                "--phase",
                "build",
                "--work-kind",
                "both",
                "--has-report",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "full")
        self.assertEqual(value["execution_order"], ["source_review", "analysis_coder", "report_coder"])
        self.assertEqual(value["coder_order"], ["analysis_coder", "report_coder"])

    def test_finish_policy_controls_full_and_review_checks(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "new",
                "--phase",
                "finish",
                "--quality-profile",
                "release",
                "--work-kind",
                "report",
                "--no-full",
                "--no-review",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        checks = json.loads(result.stdout)["required_checks"]
        self.assertNotIn("final_full", checks)
        self.assertNotIn("independent_test", checks)
        self.assertNotIn("scientific_review", checks)

    def test_route_validator_requires_task_type_and_rejects_owner_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp) / "route.json"
            value = json.loads(
                subprocess.run(
                    [sys.executable, str(SCRIPT), "--module", "demo", "--task-type", "new", "--phase", "scope"],
                    text=True,
                    capture_output=True,
                ).stdout
            )
            value["adapter_skills"].append("matt-executor")
            value["loaded_skills"].append("matt-executor")
            plan.write_text(json.dumps(value), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_route_plan.py"), str(plan)],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("owner", result.stderr)

    def test_route_validator_rejects_checks_outside_execution_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan = Path(temp) / "route.json"
            value = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--module", "demo",
                        "--task-type", "new",
                        "--phase", "build",
                        "--changed-path", "scripts/plot.R",
                    ],
                    text=True,
                    capture_output=True,
                ).stdout
            )
            value["required_checks"].append("analysis_evidence_pack")
            plan.write_text(json.dumps(value), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_route_plan.py"), str(plan)],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("analysis_evidence_pack", result.stderr)

    def test_execution_scope_report_only_is_explicit_and_report_coder_only(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "review",
                "--phase",
                "build",
                "--execution-scope",
                "report-only",
                "--work-kind",
                "report",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "report-only")
        self.assertEqual(value["execution_order"], ["report_coder"])
        self.assertNotIn("bio-code-standard", value["loaded_skills"])

    def test_execution_scope_plot_uses_plot_coder_and_no_analysis_pack(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "substantial_change",
                "--phase",
                "build",
                "--changed-path",
                "scripts/plot.R",
                "--execution-scope",
                "plot",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "plot")
        self.assertEqual(value["execution_order"], ["source_review", "plot_coder"])
        self.assertIn("figure_manifest", value["required_checks"])
        self.assertNotIn("analysis_evidence_pack", value["required_checks"])

    def test_plot_can_chain_report_coder_without_becoming_full(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "new",
                "--phase",
                "build",
                "--changed-path",
                "scripts/plot.R",
                "--has-report",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "plot")
        self.assertEqual(value["execution_order"], ["source_review", "plot_coder", "report_coder"])
        self.assertNotIn("analysis_evidence_pack", value["required_checks"])

    def test_execution_scope_full_covers_scientific_surfaces(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module",
                "demo",
                "--task-type",
                "optimize",
                "--phase",
                "build",
                "--changed-path",
                "scripts/calculate.R",
                "--execution-scope",
                "full",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "full")
        self.assertEqual(value["execution_order"], ["source_review", "analysis_coder"])
        self.assertIn("analysis_evidence_pack", value["required_checks"])

    def test_scoped_report_or_plot_cannot_enable_full_finish(self) -> None:
        for scope, path, work_kind in (
            ("report-only", "docs/report.md", "report"),
            ("plot", "scripts/plot.R", "auto"),
        ):
            with self.subTest(scope=scope):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--module", "demo",
                        "--task-type", "new",
                        "--phase", "finish",
                        "--quality-profile", "release",
                        "--work-kind", work_kind,
                        "--changed-path", path,
                        "--execution-scope", scope,
                        "--has-full",
                    ],
                    text=True,
                    capture_output=True,
                )
                self.assertNotEqual(result.returncode, 0)
                value = json.loads(result.stdout)
                self.assertEqual(value["route"], "BLOCKED")
                self.assertFalse(value["finish_policy"]["requires_full"])
                self.assertNotIn("final_full", value["required_checks"])

    def test_ambiguous_path_requires_explicit_scope(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module", "demo",
                "--task-type", "optimize",
                "--phase", "build",
                "--changed-path", "scripts/main.R",
            ],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        value = json.loads(result.stdout)
        self.assertEqual(value["route"], "BLOCKED")
        self.assertTrue(any("ambiguous" in item for item in value["blocked_reasons"]))

    def test_explicit_report_scope_overrides_python_suffix(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module", "demo",
                "--task-type", "review",
                "--phase", "build",
                "--work-kind", "both",
                "--changed-path", "scripts/report.py",
                "--execution-scope", "report-only",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["adapter_skills"], ["module-development-scheduler", "bio-report-writing"])
        self.assertEqual(value["execution_order"], ["report_coder"])

    def test_report_renderer_is_report_only_but_figure_renderer_is_plot(self) -> None:
        for path, expected in (
            ("scripts/report_renderer.py", "report-only"),
            ("scripts/figure_renderer.py", "plot"),
        ):
            with self.subTest(path=path):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--module",
                        "demo",
                        "--task-type",
                        "new",
                        "--phase",
                        "build",
                        "--changed-path",
                        path,
                    ],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertEqual(value["execution_scope"], expected)
                if expected == "plot":
                    self.assertEqual(
                        value["execution_order"], ["source_review", "plot_coder"]
                    )
                    self.assertNotIn("bio-report-writing", value["adapter_skills"])

    def test_configuration_surface_without_extension_is_full_code(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--module", "demo",
                "--task-type", "review",
                "--phase", "build",
                "--changed-path", "config",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["execution_scope"], "full")
        self.assertIn("bio-code-standard", value["adapter_skills"])


if __name__ == "__main__":
    unittest.main()
