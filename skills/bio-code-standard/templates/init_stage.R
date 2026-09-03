#!/usr/bin/env Rscript
# init 只生成或检查单个 module.config.ini，不运行科学分析或生成阶段日志。

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) {
  cat("错误类型: INPUT_ERROR\n错误内容: init 需要一个 module.config.ini 路径\n修复建议: 使用 run.sh init -c module.config.ini\n退出码: 2\n", file = stderr())
  quit(status = 2)
}
raw_config_path <- path.expand(args[[1L]])
config_link <- Sys.readlink(raw_config_path)
if (!is.na(config_link) && nzchar(config_link)) {
  cat("错误类型: OUTPUT_ERROR\n错误内容: 配置目标不能是符号链接\n修复建议: 使用普通 module.config.ini 文件\n退出码: 1\n", file = stderr())
  quit(status = 1)
}
config_path <- normalizePath(raw_config_path, mustWork = FALSE)
created <- FALSE
if (!file.exists(config_path)) {
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[[1L]]) else ""
  module_root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
  template <- file.path(module_root, "module.config.ini")
  parent <- dirname(config_path)
  if (!dir.exists(parent)) {
    cat("错误类型: OUTPUT_ERROR\n错误内容: 配置文件的父目录不存在；init 不创建配置目录\n修复建议: 先创建父目录，再使用 -c module.config.ini\n退出码: 1\n", file = stderr())
    quit(status = 1)
  }
  if (!file.exists(template) || normalizePath(config_path, mustWork = FALSE) == normalizePath(template, mustWork = FALSE)) {
    cat("错误类型: CONFIG_ERROR\n错误内容: 找不到可复制的模块 INI 模板\n修复建议: 保留模块根 module.config.ini，或先运行代码脚手架\n退出码: 2\n", file = stderr())
    quit(status = 2)
  }
  if (!file.copy(template, config_path, overwrite = FALSE)) {
    cat("错误类型: OUTPUT_ERROR\n错误内容: 无法生成配置文件\n修复建议: 检查目标目录权限后重试\n退出码: 1\n", file = stderr())
    quit(status = 1)
  }
  created <- TRUE
}
lines <- tryCatch(readLines(config_path, encoding = "UTF-8", warn = FALSE), error = function(error) NULL)
if (is.null(lines) || !any(grepl("^\\s*\\[.+\\]\\s*$", lines))) {
  cat("错误类型: CONFIG_ERROR\n错误内容: INI 配置没有可解析的 section\n修复建议: 修正 module.config.ini 格式后重试\n退出码: 2\n", file = stderr())
  quit(status = 2)
}
cat(sprintf("INIT_PASS config=%s created=%s\n", config_path, if (created) "true" else "false"))
