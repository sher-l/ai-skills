# Renderer examples

下面示例只展示接口骨架；模块应把字段名、校验和固定 prose 换成自己的合同。两种语言
都遵循同一顺序：读已发布事实 → 校验 → 写隔离 params → 调 Quarto → 验收/发布。

## R + Quarto

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
