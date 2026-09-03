"""统一的生信代码校验错误输出。

人类输出先说明错误类型、具体内容和修复建议，最后给出退出码；退出码只供调用程序判断。
"""
from __future__ import annotations

import sys
from typing import Iterable


EXIT_CODES = {
    "SUCCESS": 0,
    "RUNTIME_ERROR": 1,
    "OUTPUT_ERROR": 1,
    "INPUT_ERROR": 2,
    "CONFIG_ERROR": 2,
    "EVIDENCE_ERROR": 2,
    "DECISION_REQUIRED": 2,
    "DEPENDENCY_ERROR": 3,
}


def classify(message: str, domain: str = "runtime") -> str:
    """根据校验上下文把一条消息归入稳定的错误类型。"""
    text = message.lower()
    if "decision_required" in text or "conflict" in text:
        return "DECISION_REQUIRED"
    if domain == "source":
        return "EVIDENCE_ERROR"
    if any(word in text for word in ("dependency", "runtime_install", "environment", "interpreter", "package")):
        return "DEPENDENCY_ERROR"
    if text.startswith("cannot read") or text.startswith("invalid json"):
        return "INPUT_ERROR"
    if domain == "figure":
        return "OUTPUT_ERROR"
    if any(word in text for word in ("cannot read", "does not exist", "not found", "file", "path")):
        return "INPUT_ERROR"
    if "source_review" in text:
        return "EVIDENCE_ERROR"
    if any(word in text for word in ("dependency", "runtime_install", "environment", "interpreter", "package")):
        return "DEPENDENCY_ERROR"
    if any(
        word in text
        for word in (
            "config", "contract", "schema", "field", "parameter", "unknown", "missing",
            "profile", "stages", "quality", "effort", "result_layout", "evidence_pack", "commands",
        )
    ):
        return "CONFIG_ERROR"
    if any(word in text for word in ("input", "source root", "file does not exist", "path", "utf-8")):
        return "INPUT_ERROR"
    if any(word in text for word in ("figure", "manifest", "output", "result", "format", "render")):
        return "OUTPUT_ERROR"
    return "RUNTIME_ERROR"


def entries(
    errors: Iterable[str],
    warnings: Iterable[str],
    subject: str,
    *,
    domain: str = "runtime",
    fixes: str = "修正标记内容后重新运行校验",
) -> list[dict[str, object]]:
    """生成兼容旧字段的机器诊断，同时增加明确的类型和内容字段。"""
    result: list[dict[str, object]] = []
    for message in errors:
        kind = classify(message, domain)
        result.append(
            {
                "code": f"{domain}/{kind.lower()}",
                "error_type": kind,
                "severity": "error",
                "message": message,
                "content": message,
                "subject": {"path": subject},
                "evidence": {},
                "supportedFixes": [fixes],
            }
        )
    for message in warnings:
        result.append(
            {
                "code": f"{domain}/evidence-needed",
                "error_type": "EVIDENCE_NEEDED",
                "severity": "warning",
                "message": message,
                "content": message,
                "subject": {"path": subject},
                "evidence": {},
                "supportedFixes": [fixes],
            }
        )
    return result


def exit_code(
    errors: Iterable[str],
    warnings: Iterable[str] = (),
    *,
    status: str = "BLOCKED",
    domain: str = "runtime",
) -> int:
    """把诊断归入约定的四个进程退出码。"""
    error_list = list(errors)
    if not error_list and status == "PASS":
        return EXIT_CODES["SUCCESS"]
    kinds = {classify(message, domain) for message in error_list}
    if "DEPENDENCY_ERROR" in kinds:
        return EXIT_CODES["DEPENDENCY_ERROR"]
    if kinds & {"INPUT_ERROR", "CONFIG_ERROR", "EVIDENCE_ERROR", "DECISION_REQUIRED"}:
        return EXIT_CODES["CONFIG_ERROR"]
    if kinds & {"RUNTIME_ERROR", "OUTPUT_ERROR"}:
        return EXIT_CODES["RUNTIME_ERROR"]
    if status in {"EVIDENCE_NEEDED", "DRAFT", "BLOCKED", "DECISION_REQUIRED"} or list(warnings):
        return EXIT_CODES["CONFIG_ERROR"]
    return EXIT_CODES["RUNTIME_ERROR"]


def print_result(
    prefix: str,
    status: str,
    errors: Iterable[str],
    warnings: Iterable[str],
    *,
    domain: str = "runtime",
    fixes: str = "修正标记内容后重新运行校验",
) -> None:
    """输出错误类型、内容、修复建议，最后输出机器退出码。"""
    error_list = list(errors)
    warning_list = list(warnings)
    for message in error_list:
        print(
            f"错误类型: {classify(message, domain)}\n错误内容: {message}\n修复建议: {fixes}",
            file=sys.stderr,
        )
    for message in warning_list:
        print(
            f"提示类型: EVIDENCE_NEEDED\n提示内容: {message}\n修复建议: {fixes}",
            file=sys.stdout,
        )
    print(f"{prefix}_{status} errors={len(error_list)} warnings={len(warning_list)}")
    print(f"退出码: {exit_code(error_list, warning_list, status=status, domain=domain)}", file=sys.stderr)
