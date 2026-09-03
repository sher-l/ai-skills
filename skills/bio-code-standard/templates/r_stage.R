#!/usr/bin/env Rscript
# 目的：完成一个已批准的分析目标。
# 输入：写明产物 ID、格式、行列方向、ID namespace 和单位。
# 输出：只生成已声明的表、对象、图件和 analysis_evidence_pack.json。
# 方法与版本：写明实际实现、版本和引用。
# 参数与随机种子：写明每个阈值、contrast 和随机种子。

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) stop("usage: r_stage.R CONFIG", call. = FALSE)
config_path <- normalizePath(args[[1L]], mustWork = TRUE)
config_dir <- dirname(config_path)

# 所有相对路径均从 config_dir 解析；加载 Scientific Core 前先校验输入。
# 每次过滤或对齐都记录 before/after 计数。
# set.seed(<FROZEN_SEED>)  # 仅在合同已记录固定随机种子后取消注释

stop("EVIDENCE_NEEDED：请实现已批准的科学阶段", call. = FALSE)
