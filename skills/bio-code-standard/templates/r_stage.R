#!/usr/bin/env Rscript
# 目的：完成一个已批准的分析目标。
# 输入：写明产物 ID、格式、行列方向、ID namespace 和单位。
# 输出：只生成已声明的表、对象、图件和 analysis_evidence_pack.json。
# 方法与版本：写明实际实现、版本和引用。
# 参数与随机种子：写明每个阈值、contrast 和随机种子。

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  cat("错误类型: INPUT_ERROR\n错误内容: 未提供配置文件\n修复建议: 使用 run.sh <stage> -c module.config.ini\n退出码: 2\n", file = stderr())
  quit(status = 2)
}
raw_stage_config <- path.expand(args[[1L]])
if (!file.exists(raw_stage_config)) {
  cat("错误类型: INPUT_ERROR\n错误内容: 配置文件不存在\n修复建议: 检查 module.config.ini 路径和权限\n退出码: 2\n", file = stderr())
  quit(status = 2)
}
config_path <- normalizePath(raw_stage_config, mustWork = TRUE)
config_dir <- dirname(config_path)
output_arg <- which(args == "--output")
output_dir <- if (length(output_arg) && output_arg[[1L]] < length(args)) {
  normalizePath(args[[output_arg[[1L]] + 1L]], mustWork = FALSE)
} else {
  config_dir
}

# 所有相对路径均从 config_dir 解析；加载科学核心代码前先校验输入。
# 每次过滤或对齐都记录 before/after 计数。
# set.seed(<FROZEN_SEED>)  # 仅在合同已记录固定随机种子后取消注释

cat("错误类型: EVIDENCE_ERROR\n错误内容: 当前阶段仍是脚手架，尚未接入已批准的科学逻辑\n修复建议: 按 code_contract 填写真实输入、方法、产物和非退化检查后重试\n退出码: 2\n", file = stderr())
quit(status = 2)
