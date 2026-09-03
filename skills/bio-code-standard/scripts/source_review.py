#!/usr/bin/env python3
"""Create and validate the portable source-review gate for a module.

The command deliberately does not fetch the network.  It records the official
URLs and execution receipts supplied by the analyst, then checks that the
three-way claims in ``doc/source-review.md`` are complete and non-conflicting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from datetime import date


SCHEMA_VERSION = "2.2"
DEFAULT_DOC = Path("doc/source-review.md")
SOURCE_EXTENSIONS = {".r": "R", ".rmd": "Rmd", ".py": "Python"}
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "cache", "log", "result",
    "report", "output", "doc", "docs", ".code-contract", "node_modules",
}
PLACEHOLDER = re.compile(
    r"(?:\b(?:TODO|TBD|REPLACE|PENDING|EVIDENCE_REQUIRED|ADD|UNKNOWN)\b|\[\s*(?:fill|add|path|url|date|claim)[^\]]*\])",
    re.IGNORECASE,
)
SHA256 = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
RELATIVE = re.compile(r"^(?!/)(?![A-Za-z]:[\\/])(?!.*(?:^|/)\.\.(?:/|$)).+")
STATUSES = {"MATCH", "CONFLICT", "MISSING", "PENDING", "NOT_APPLICABLE"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def source_inventory(root: Path) -> list[dict[str, str | int]]:
    """Return a stable inventory of R/Rmd/Python source files under root."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"source root does not exist: {root}")
    entries: list[dict[str, str | int]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        language = SOURCE_EXTENSIONS.get(path.suffix.lower())
        if language is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 保留该文件到清单，校验阶段再报告编码问题。
            text = ""
        entries.append(
            {
                "path": relative.as_posix(),
                "language": language,
                "sha256": digest(path),
                "lines": len(text.splitlines()),
                "role": "candidate",
                "canonical": "no",
            }
        )
    return entries


def _cell(value: object) -> str:
    return str(value).strip().strip("`").replace("\\|", "|")


def _heading_key(value: str) -> str:
    return re.sub(r"^\d+[.)]\s*", "", value.strip()).casefold()


def _table(lines: list[str], heading: str) -> list[dict[str, str]]:
    """Read the first Markdown table following a level-two heading."""
    start = None
    wanted = _heading_key(heading)
    for index, line in enumerate(lines):
        if line.startswith("## ") and _heading_key(line[3:]) == wanted:
            start = index + 1
            break
    if start is None:
        return []
    table_lines: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.lstrip().startswith("|"):
            table_lines.append(line.strip())
        elif table_lines and line.strip():
            break
    if len(table_lines) < 2:
        return []
    headers = [_cell(item) for item in table_lines[0].strip("|").split("|")]
    if not headers or not all(set(item.replace("-", "")) <= {":", " "} for item in table_lines[1].strip("|").split("|")):
        return []
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [_cell(item) for item in line.strip("|").split("|")]
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(dict(zip(headers, cells)))
    return rows


def _metadata(lines: list[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*-\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            metadata[match.group(1)] = _cell(match.group(2))
    return metadata


def _placeholder(value: str) -> bool:
    return not value.strip() or bool(PLACEHOLDER.search(value))


def _diag(message: str, subject: str, severity: str = "error") -> dict[str, object]:
    if "conflict" in message.lower() or "decision_required" in message.lower():
        code = "source-review/decision-required"
    elif "inventory" in message.lower() or "canonical" in message.lower():
        code = "source-review/source-identity"
    elif "official" in message.lower():
        code = "source-review/official-evidence"
    elif "execution" in message.lower():
        code = "source-review/execution-evidence"
    else:
        code = "source-review/incomplete"
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "subject": {"path": subject},
        "evidence": {},
        "supportedFixes": ["编辑 doc/source-review.md 中标记的行后重新运行 source-review validate"],
    }


def validate_document(path: Path, root: Path | None = None, final: bool = False) -> dict[str, object]:
    """Validate a source-review document and return a machine-readable result."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        result = {"status": "BLOCKED", "errors": [f"cannot read source review: {exc}"], "warnings": []}
        result["diagnostics"] = [_diag(result["errors"][0], str(path))]
        result["summary"] = {"errors": 1, "warnings": 0}
        return result

    lines = text.splitlines()
    metadata = _metadata(lines)
    required_metadata = ("schema_version", "module", "source_root", "canonical_source", "review_status")
    for key in required_metadata:
        if not metadata.get(key):
            errors.append(f"missing metadata: {key}")
    if metadata.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if metadata.get("review_status") not in {"DRAFT", "PASS", "DECISION_REQUIRED", "BLOCKED"}:
        errors.append("review_status must be DRAFT, PASS, DECISION_REQUIRED or BLOCKED")
    for heading in ("Source inventory", "Official materials", "Execution evidence", "Cross-check matrix"):
        if not any(line.startswith("## ") and _heading_key(line[3:]) == _heading_key(heading) for line in lines):
            errors.append(f"missing section: {heading}")

    inventory = _table(lines, "Source inventory")
    if not inventory:
        errors.append("source inventory table must contain at least one row")
    inventory_paths: set[str] = set()
    identity_conflict = False
    canonical_rows: list[dict[str, str]] = []
    root_path = root.resolve() if root else None
    for index, row in enumerate(inventory):
        label = f"source inventory row {index + 1}"
        source_path = row.get("path", "")
        if not RELATIVE.fullmatch(source_path):
            errors.append(f"{label} path must be relative")
            continue
        if source_path in inventory_paths:
            errors.append(f"duplicate source inventory path: {source_path}")
        inventory_paths.add(source_path)
        if row.get("language") not in set(SOURCE_EXTENSIONS.values()):
            errors.append(f"{label} language must be R, Rmd or Python")
        elif source_path and SOURCE_EXTENSIONS.get(Path(source_path).suffix.lower()) != row.get("language"):
            errors.append(f"{label} language does not match file extension: {source_path}")
        if not SHA256.fullmatch(row.get("sha256", "")):
            errors.append(f"{label} sha256 must be 64 hexadecimal characters")
        if row.get("canonical", "").lower() == "yes":
            canonical_rows.append(row)
        if root_path:
            candidate = (root_path / source_path).resolve()
            try:
                candidate.relative_to(root_path)
            except ValueError:
                errors.append(f"{label} escapes source root: {source_path}")
            else:
                if not candidate.is_file():
                    errors.append(f"{label} file does not exist: {source_path}")
                elif digest(candidate).lower() != row.get("sha256", "").lower():
                    identity_conflict = True
                    errors.append(f"source inventory hash changed: {source_path}; rerun source-review init")
                else:
                    try:
                        candidate.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        errors.append(f"source file is not UTF-8: {source_path}")
    if root_path:
        try:
            actual_paths = {str(item["path"]) for item in source_inventory(root_path)}
        except ValueError:
            actual_paths = set()
        for extra_path in sorted(actual_paths - inventory_paths):
            identity_conflict = True
            errors.append(f"source file is absent from inventory: {extra_path}; rerun source-review init")
    canonical = metadata.get("canonical_source", "")
    if canonical in {"PENDING", ""}:
        warnings.append("canonical_source is not selected")
    elif canonical not in inventory_paths:
        errors.append(f"canonical_source is absent from source inventory: {canonical}")
    elif len(canonical_rows) != 1 or canonical_rows[0].get("path") != canonical:
        errors.append("exactly one source inventory row must mark canonical=yes and match canonical_source")
    elif root_path and not (root_path / canonical).is_file():
        errors.append(f"canonical_source does not exist: {canonical}")

    official = _table(lines, "Official materials")
    if not official:
        warnings.append("official materials table has no rows")
    official_ids: set[str] = set()
    for index, row in enumerate(official):
        label = f"official materials row {index + 1}"
        item_id = row.get("id", "")
        if not item_id or item_id in official_ids:
            errors.append(f"{label} needs a unique id")
        official_ids.add(item_id)
        url = row.get("url", "")
        if _placeholder(url) or ".example/" in url or not re.match(r"^https://[^\s]+$", url):
            warnings.append(f"{label} needs an official https URL")
        for key in ("title", "version_or_commit", "accessed", "scope"):
            if _placeholder(row.get(key, "")):
                warnings.append(f"{label} needs {key}")

    execution = _table(lines, "Execution evidence")
    if not execution:
        warnings.append("execution evidence table has no rows")
    execution_ids: set[str] = set()
    execution_statuses: dict[str, str] = {}
    for index, row in enumerate(execution):
        label = f"execution evidence row {index + 1}"
        item_id = row.get("id", "")
        if not item_id or item_id in execution_ids:
            errors.append(f"{label} needs a unique id")
        execution_ids.add(item_id)
        for key in ("command", "run_id", "artifact_or_log"):
            if _placeholder(row.get(key, "")):
                warnings.append(f"{label} needs {key}")
        status = row.get("status", "").upper()
        execution_statuses[item_id] = status
        if status not in {"PASS", "SUCCESS", "FAILED", "BLOCKED", "PENDING"}:
            warnings.append(f"{label} status is not a recognized execution status")

    checks = _table(lines, "Cross-check matrix")
    if not checks:
        warnings.append("cross-check matrix has no rows")
    conflict = False
    check_ids: set[str] = set()
    for index, row in enumerate(checks):
        label = f"cross-check row {index + 1}"
        check_id = row.get("id", "")
        if not check_id or check_id in check_ids:
            errors.append(f"{label} needs a unique id")
        check_ids.add(check_id)
        status = row.get("status", "").upper()
        if status not in STATUSES:
            errors.append(f"{label} status must be one of {sorted(STATUSES)}")
        if status == "CONFLICT":
            conflict = True
        for key in ("claim", "official_definition", "source_evidence", "execution_evidence"):
            if _placeholder(row.get(key, "")):
                warnings.append(f"{label} needs {key}")
        official_ref = row.get("official_id", "")
        execution_ref = row.get("execution_id", "")
        source_ref = row.get("source_path", "")
        if official_ref and official_ids and official_ref not in official_ids:
            (warnings if _placeholder(official_ref) else errors).append(f"{label} references unknown official_id: {official_ref}")
        if execution_ref and execution_ids and execution_ref not in execution_ids:
            (warnings if _placeholder(execution_ref) else errors).append(f"{label} references unknown execution_id: {execution_ref}")
        if source_ref and source_ref not in inventory_paths:
            (warnings if _placeholder(source_ref) else errors).append(f"{label} references unknown source_path: {source_ref}")
        if status == "MATCH" and execution_ref in execution_statuses and execution_statuses[execution_ref] not in {"PASS", "SUCCESS"}:
            warnings.append(f"{label} MATCH requires a successful execution evidence row")
        if status == "CONFLICT" and _placeholder(row.get("decision", "")):
            warnings.append(f"{label} conflict requires a recorded decision")

    if conflict:
        errors.append("DECISION_REQUIRED: official definition and source/execution evidence conflict")
    if metadata.get("review_status") == "DECISION_REQUIRED" and not conflict:
        conflict = True
        errors.append("DECISION_REQUIRED: review_status remains unresolved")
    if metadata.get("review_status") == "PASS" and (errors or warnings):
        errors.append("review_status=PASS is inconsistent with unresolved review findings")

    if errors:
        status = "DECISION_REQUIRED" if (conflict or identity_conflict) else "BLOCKED"
    elif not final:
        status = "EVIDENCE_NEEDED"
        if not warnings:
            warnings.append("validation without --final is not a release PASS")
    elif warnings or metadata.get("review_status") != "PASS":
        status = "EVIDENCE_NEEDED"
    else:
        status = "PASS"
    if final and status != "PASS":
        errors.append(f"final source review requires PASS (observed {status})")
        status = "DECISION_REQUIRED" if (conflict or identity_conflict) else "BLOCKED"
    diagnostics = [_diag(item, str(path)) for item in errors]
    diagnostics.extend(_diag(item, str(path), "warning") for item in warnings)
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostics,
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }


def render_document(module: str, root: Path, output: Path) -> None:
    entries = source_inventory(root)
    if not entries:
        raise ValueError(f"no R/Rmd/Python source found under {root.resolve()}")
    inventory_rows = "\n".join(
        f"| {item['path']} | {item['language']} | {item['sha256']} | {item['lines']} | candidate | no |"
        for item in entries
    )
    today = date.today().isoformat()
    content = f"""# Source review

- schema_version: {SCHEMA_VERSION}
- module: {module}
- source_root: .
- canonical_source: PENDING
- review_status: DRAFT
- generated: {today}

先完成本文件，再修改 calculate/plot 或统计逻辑。所有路径相对模块根目录；
官方资料必须由分析者实际阅读并填写，脚本不会把搜索结果当作证据。

## Source inventory

| path | language | sha256 | lines | role | canonical |
| --- | --- | --- | --- | --- | --- |
{inventory_rows}

## Official materials

| id | title | url | version_or_commit | accessed | scope |
| --- | --- | --- | --- | --- | --- |
| OFF-01 | ADD official title | https://official.example/document | version-or-commit | {today} | definition and parameter scope |

将实际阅读的关键规则和短摘录保存到 `doc/source-review/`（例如
`doc/source-review/OFF-01.md`），文件中保留 URL/DOI、版本或 commit、访问日期和
适用范围；不要只留下搜索结果链接。该目录是长期科学资料缓存，不是运行日志或客户输出。

## Execution evidence

| id | command | run_id | artifact_or_log | status | notes |
| --- | --- | --- | --- | --- | --- |
| RUN-01 | ADD exact command | ADD run id | ADD relative log/artifact | PENDING | execution evidence is required after implementation |

## Cross-check matrix

每一条关键定义都要同时指向官方资料、源码位置和一次实际执行证据。

| id | claim | official_id | source_path | execution_id | official_definition | source_evidence | execution_evidence | status | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CK-01 | ADD one testable scientific definition | OFF-01 | ADD/source.R | RUN-01 | ADD exact official definition | ADD function/line and behavior | ADD run/artifact observation | PENDING | ADD decision or rationale |

## Decision gate

- `PASS`：canonical source、官方资料、执行证据和所有交叉核对均完整，且没有 `CONFLICT`。
- `DECISION_REQUIRED`：任何官方定义、源码实现和执行证据冲突；暂停后续 coder 工作并返回最小决策项。
- `EVIDENCE_NEEDED`：没有冲突但仍缺资料、运行记录或明确 canonical source。

运行：

```bash
python scripts/bio_code.py source-review validate doc/source-review.md --source-root . --json
```
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def init_command(args: argparse.Namespace) -> int:
    root = args.source_root.resolve()
    output = args.output.resolve() if args.output else root / DEFAULT_DOC
    try:
        output.relative_to(root)
    except ValueError:
        print(f"SOURCE_REVIEW_BLOCKED: output must be inside source root: {output}", file=sys.stderr)
        return 2
    if output.exists() and not args.force:
        print(f"SOURCE_REVIEW_BLOCKED: output exists (use --force only after review): {output}", file=sys.stderr)
        return 2
    try:
        render_document(args.module, root, output)
    except (OSError, ValueError) as exc:
        print(f"SOURCE_REVIEW_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "DRAFT", "path": str(output), "files": len(source_inventory(root))}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    init = subparsers.add_parser("init", help="inventory source and create module-local doc/source-review.md")
    init.add_argument("--module", required=True)
    init.add_argument("--source-root", required=True, type=Path)
    init.add_argument("--output", type=Path, help="defaults to SOURCE_ROOT/doc/source-review.md")
    init.add_argument("--force", action="store_true", help="allow replacing an existing review document")
    validate = subparsers.add_parser("validate", help="validate the three-way source review")
    validate.add_argument("document", type=Path)
    validate.add_argument("--source-root", type=Path)
    validate.add_argument("--final", action="store_true")
    validate.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if args.action == "init":
        return init_command(args)
    result = validate_document(args.document, args.source_root, args.final)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"SOURCE_REVIEW_{result['status']} errors={len(result['errors'])} warnings={len(result['warnings'])}")
        for item in result["errors"]:
            print(item, file=sys.stderr)
        for item in result["warnings"]:
            print(item)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
