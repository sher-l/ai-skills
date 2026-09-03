# Renderer examples

下面示例只展示接口骨架；模块应把字段名、校验和固定 prose 换成自己的合同。两种语言都遵循同一顺序：
读已发布事实 → 校验 → 写隔离工作副本 → 填充固定模板 → 验收/发布。

目录：[DOCX-first](#docx-first新模块必须采用) · [存量 QMD/Rmd](#存量-qmdrmd接线仅迁移期间) ·
[R 示例](#r--quarto) · [Python 示例](#python--quarto)

## DOCX-first（新模块必须采用）

新模块唯一正式模板是 `report_template.docx`。renderer 使用现有 DOCX 读写能力（优先复用模块已有工具）
打开隔离副本，按 [slot-contract.md](slot-contract.md) 的 bookmark/marker 填充，不按段落序号或任意字段循环
猜位置。随 skill 提供的 `scripts/render_docx_template.py` 是可直接复制的最小 helper；模块可在其上增加
自己的固定 prose 和字段校验。下面是 R/Python 都必须满足的接口：

```text
generate_report(input_root, evidence_pack, template_dir, output_dir):
    facts = read(evidence_pack)
    validate_schema_paths_provenance_and_conditions(facts, input_root)
    params = {
      report.title, report.audience, report.summary,
      analysis.scope, analysis.method, analysis.qc,
      analysis.result, analysis.conclusion, analysis.limitations,
      notes[], result_table, figures[], output_table[], references, version_table
    }
    work = isolated_copy(template_dir/report_template.docx)
    fill_bookmarks_and_markers(work, params)       # 可调用 scripts/render_docx_template.py
    validate_contract_and_docx(work)
    publish_only_final_report(work, output_dir)
```

运行场景由变更面决定：只改正文、图题、图注、表述或 DOCX 版式时调用已发布结果的
`report-only`；只改不影响科学结果的作图代码时调用 `plot`，再调用 `report-only`；改计算、科学逻辑、
配置、合同或输出结构时才调用 `full`。`report-only` 不重算、不重画，`plot` 不重算。

DOCX-first renderer 的硬条件：

- 模板、renderer 和 evidence pack 是显式输入；所有路径相对 `input_root`，拒绝绝对路径和越界 `..`；
- `report_template.docx` 是唯一生效正文；正式运行不调用 AI、不重算、不重画、不读取日志/config/cache 猜事实；
- `result_table`、`figures[]`、`output_table[]`、`version_table[]` 和条件 `notes[]` 由固定函数生成；
- 图完整等比嵌入，表头/行分页规则和 Note 三色遵循 [figure-contract.md](figure-contract.md)；
- 失败返回 `EVIDENCE_NEEDED`/`BLOCKED`，不会发布半成品或把 marker 原样交付。

一次性 renderer 复制同一模板和接口到独立目录；不写回输入。`assets/generate_report.R.example` 与
`assets/generate_report.py.example` 已调用 `scripts/render_docx_template.py`；正式模块必须把 DOCX 锚点填充、
固定 caption、表格函数和最终验收补齐。

## 存量 QMD/Rmd 接线（仅迁移期间）

以下 Quarto 示例不是新模块默认；只适用于模块合同已经声明 `report_template.qmd|Rmd` + `reference.docx`
的旧入口。它仍必须遵守同一 slots、图表、Note、语言和验收合同，不得与 DOCX 模板并行维护正文。

### R + Quarto

示例中的 `figure_path`、`table_rows` 等简化参数仅表示 legacy 接线；真实模块必须扩展为
`notes[]`、`result_table`、`output_table`、`version_table` 和多图 `figures[]`，并按条件省略产物。

```r
generate_report <- function(input_root, evidence_json, template_dir, output_dir) {
  stopifnot(dir.exists(input_root), file.exists(evidence_json))
  facts <- jsonlite::read_json(evidence_json, simplifyVector = FALSE)
  point <- facts$analysis_points[[1L]]
  stopifnot(identical(facts$quality_profile, "release"),
            is.character(point$comparison$direction),
            length(point$limitations) > 0L)
  `%||%` <- function(x, y) if (is.null(x) || !length(x)) y else x
  render_references <- function(x) paste(vapply(x %||% list(), `[[`, "", "name"), collapse = "；")
  render_versions <- function(x) paste(vapply(x %||% list(), function(item) paste(item$name, item$version), character(1)), collapse = "；")

  safe <- function(path) {
    if (grepl("^(/|[A-Za-z]:)", path) || grepl("(^|/)[.][.](/|$)", path))
      stop("relative published path required")
    out <- normalizePath(file.path(input_root, path), mustWork = TRUE)
    root <- normalizePath(input_root, mustWork = TRUE)
    if (!startsWith(paste0(out, "/"), paste0(root, "/"))) stop("path escapes input root")
    out
  }
  params <- list(
    title = facts$title, summary = point$interpretation, scope = point$scope,
    method = point$method, parameters = point$parameters,
    results = point$results, limitations = point$limitations,
    figure_path = safe(point$figure_table_refs[[1L]]$path),
    figure_caption = build_caption(point), table_caption = point$title,
    table_rows = point$results,
    output_text = paste(vapply(point$outputs, `[[`, "", "path"), collapse = "、"),
    references_text = render_references(facts$references),
    versions_text = render_versions(facts$versions)
  )
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  work <- tempfile("report-render-"); dir.create(work)
  on.exit(unlink(work, recursive = TRUE, force = TRUE), add = TRUE)
  file.copy(file.path(template_dir, "report_template.qmd"), file.path(work, "report_template.qmd"))
  file.copy(file.path(template_dir, "reference.docx"), file.path(work, "reference.docx"))
  jsonlite::write_json(params, file.path(work, "params.json"), auto_unbox = TRUE, pretty = TRUE)
  status <- system2("quarto", c("render", "report_template.qmd", "--to", "docx",
                                "--execute-params", "params.json", "--output", "report.docx"))
  if (!identical(status, 0L)) stop("Quarto render failed")
  file.copy(file.path(work, "report.docx"), file.path(output_dir, "MODULE_report.docx"), overwrite = TRUE)
  invisible(file.path(output_dir, "MODULE_report.docx"))
}
```

`build_caption()` 应只接受已验证字段，明确对象、比较/分组、panel、轴/单位、图例语义、
n/统计层级、阈值和边界；不要把 caption 交给模型或从图像 OCR 猜。

## Python + Quarto

同样仅为存量接线示意；新模块不得把下面的 Quarto 文件复制为第二套正文。

```python
from pathlib import Path
import json, shutil, subprocess, tempfile

def render_references(items):
    return "；".join(item["name"] for item in items)

def render_versions(items):
    return "；".join(f"{item['name']} {item['version']}" for item in items)

def generate_report(root, pack_file, template_dir, output_dir):
    root, template_dir, output_dir = map(Path, (root, template_dir, output_dir))
    pack = json.loads(Path(pack_file).read_text(encoding="utf-8"))
    point = pack["analysis_points"][0]
    if pack["quality_profile"] != "release" or not point["limitations"]:
        raise ValueError("release report needs complete evidence")
    def safe(rel):
        p = (root / rel).resolve()
        if Path(rel).is_absolute() or root.resolve() not in p.parents or not p.is_file():
            raise ValueError(f"published path is missing or escapes input root: {rel}")
        return p
    params = {"title": pack.get("title", "分析报告"), "summary": point["interpretation"],
              "scope": point["scope"], "method": point["method"],
              "results": point["results"], "limitations": point["limitations"],
              "figure_path": str(safe(point["figure_table_refs"][0]["path"])),
              "figure_caption": build_caption(point), "table_caption": point["title"],
              "table_rows": point["results"],
              "output_text": "、".join(item["path"] for item in point["outputs"]),
              "references_text": render_references(pack.get("references", [])),
              "versions_text": render_versions(pack.get("versions", []))}
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="report-render-") as tmp:
        work = Path(tmp)
        shutil.copy2(template_dir / "report_template.qmd", work / "report_template.qmd")
        shutil.copy2(template_dir / "reference.docx", work / "reference.docx")
        (work / "params.json").write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
        subprocess.run(["quarto", "render", "report_template.qmd", "--to", "docx",
                        "--execute-params", "params.json", "--output", "report.docx"],
                       cwd=work, check=True)
        shutil.copy2(work / "report.docx", output_dir / "MODULE_report.docx")
```

将 `build_caption`、表格列定义、条件分支和最终验证替换为模块合同；不要引入第二套
科学计算或一份隐藏的正文模板。
