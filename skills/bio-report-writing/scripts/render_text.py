"""Small deterministic helpers for draft scaffolds, not reader-facing report prose."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence


LABELS = {
    "name": "名称",
    "version": "版本",
    "citation": "来源",
    "target": "目标组",
    "reference": "参照组",
    "direction": "方向",
    "metric": "指标",
    "statistical_unit": "推断单位",
    "effect_expression": "效应表达",
    "source": "来源",
    "path": "文件",
    "purpose": "用途",
    "kind": "类型",
    "value": "数值",
    "unit": "单位",
}


def marker(name: str) -> str:
    return f"[[EVIDENCE_REQUIRED:{name}]]"


def scalar(value: object) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def compact(value: object, missing: str = "evidence") -> str:
    """Render JSON-like values as readable, stable Chinese inline text."""
    if value is None or value == "" or value == [] or value == {}:
        return marker(missing)
    if isinstance(value, Mapping):
        parts = []
        for key, item in value.items():
            label = LABELS.get(str(key), str(key))
            parts.append(f"{label}：{compact(item, missing)}")
        return "；".join(parts)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "；".join(compact(item, missing) for item in value)
    return scalar(value)


def method_text(value: object, missing: str = "method") -> str:
    if not isinstance(value, Mapping):
        return compact(value, missing)
    ordered = [key for key in ("name", "version", "citation") if value.get(key)]
    ordered += [key for key in value if key not in ordered]
    parts = []
    for key in ordered:
        label = LABELS.get(str(key), str(key))
        parts.append(f"{label}：{compact(value.get(key), missing)}")
    return "；".join(parts) or marker(missing)


def parameters_text(value: object, missing: str = "parameters") -> str:
    return compact(value, missing)


def comparison_text(point: Mapping[str, object], missing: str = "comparison") -> str:
    unit = point.get("statistical_unit")
    comparison = point.get("comparison")
    parts = []
    if unit:
        parts.append(f"推断单位：{scalar(unit)}")
    if isinstance(comparison, Mapping):
        for key in ("target", "reference", "metric", "direction"):
            if comparison.get(key) not in (None, ""):
                parts.append(f"{LABELS.get(key, key)}：{compact(comparison[key], missing)}")
    if not parts:
        return marker(missing)
    return "；".join(parts)


def result_texts(value: object, missing: str = "results") -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return compact(value, missing)
    rendered = []
    for item in value:
        if isinstance(item, Mapping):
            name = scalar(item.get("name", "结果"))
            amount = item.get("value")
            unit = item.get("unit")
            text = f"{name}={scalar(amount) if amount is not None else marker(missing)}"
            if unit:
                text += f" {scalar(unit)}"
            if item.get("source"):
                text += f"（来源：{scalar(item['source'])}）"
            rendered.append(text)
        else:
            rendered.append(compact(item, missing))
    return "；".join(rendered) or marker(missing)


def output_texts(value: object, missing: str = "outputs") -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return compact(value, missing)
    rendered = []
    for item in value:
        if isinstance(item, Mapping):
            path = scalar(item.get("path", marker(missing)))
            purpose = item.get("purpose")
            rendered.append(f"{path}" + (f"（{scalar(purpose)}）" if purpose else ""))
        else:
            rendered.append(compact(item, missing))
    return "；".join(rendered) or marker(missing)


def reference_texts(value: object, missing: str = "references") -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return compact(value, missing)
    rendered = []
    for item in value:
        if isinstance(item, Mapping):
            name = scalar(item.get("name", "来源"))
            version = item.get("version")
            source = item.get("source")
            suffix = []
            if version:
                suffix.append(f"版本 {scalar(version)}")
            if source:
                suffix.append(scalar(source))
            rendered.append(name + (f"（{'；'.join(suffix)}）" if suffix else ""))
        else:
            rendered.append(compact(item, missing))
    return "；".join(rendered) or marker(missing)


def figure_ref_texts(value: object, missing: str = "figure_table_refs") -> str:
    if not value:
        return "本分析点未声明图表"
    rendered = []
    for item in value:
        if isinstance(item, Mapping):
            ident = scalar(item.get("id", "Figure/Table"))
            path = scalar(item.get("path", marker(missing)))
            rendered.append(f"{ident}：{path}")
        else:
            rendered.append(compact(item, missing))
    return "；".join(rendered)
