#!/usr/bin/env bash
# 生信模块唯一公开入口；这里只解析参数、检查边界并调度阶段脚本。
set -Eeuo pipefail

MODULE_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
STAGE="${1:-}"
shift 2>/dev/null || true
CONFIG=""
OUTPUT="$MODULE_ROOT"

fail() {
  local kind="$1"
  local content="$2"
  local fix="$3"
  local code="${4:-2}"
  printf '错误类型: %s\n错误内容: %s\n修复建议: %s\n退出码: %s\n' "$kind" "$content" "$fix" "$code" >&2
  return "$code"
}

if [[ -z "$STAGE" || "$STAGE" == "help" || "$STAGE" == "-h" || "$STAGE" == "--help" ]]; then
  printf '%s\n' '用法: run.sh init|calculate|plot|report|full -c module.config.ini [-o OUTPUT]'
  printf '%s\n' 'init -c PATH 生成或校验单个 INI 配置；full 只串联 calculate → plot → report。'
  exit 0
fi
case "$STAGE" in
  init|calculate|plot|report|full) ;;
  *) fail 'INPUT_ERROR' "不支持的阶段: $STAGE" '使用 init、calculate、plot、report 或 full' 2; exit $? ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      [[ $# -ge 2 ]] || { fail 'CONFIG_ERROR' '缺少 -c 的配置文件路径' '传入 module.config.ini' 2; exit $?; }
      CONFIG="$2"
      shift 2
      ;;
    -o|--output)
      [[ $# -ge 2 ]] || { fail 'OUTPUT_ERROR' '缺少 -o 的输出目录路径' '传入可写的输出目录' 1; exit $?; }
      OUTPUT="$2"
      shift 2
      ;;
    *) fail 'INPUT_ERROR' "未知参数: $1" '只使用 -c/--config 和 -o/--output' 2; exit $? ;;
  esac
done
[[ -n "$CONFIG" ]] || { fail 'CONFIG_ERROR' '必须显式提供配置文件' '使用 -c module.config.ini' 2; exit $?; }
if [[ "$CONFIG" != /* ]]; then CONFIG="$MODULE_ROOT/$CONFIG"; fi
if [[ "$OUTPUT" != /* ]]; then OUTPUT="$PWD/$OUTPUT"; fi
if [[ "$STAGE" == "init" && "$OUTPUT" != "$MODULE_ROOT" ]]; then
  fail 'INPUT_ERROR' 'init 不接受 -o/--output；配置目标由 -c 指定' '使用 run.sh init -c module.config.ini' 2
  exit $?
fi
if [[ "$STAGE" != "init" && ! -f "$CONFIG" ]]; then
  fail 'INPUT_ERROR' "配置文件不存在: $CONFIG" '检查 module.config.ini 的路径和文件名' 2
  exit $?
fi

stage_language=""
if [[ -f "$CONFIG" ]] && command -v awk >/dev/null 2>&1; then
  stage_language="$(awk -F= '/^[[:space:]]*language[[:space:]]*=/{gsub(/[[:space:]]/,"",$2); print tolower($2); exit}' "$CONFIG")"
fi
if [[ -n "$stage_language" && "$stage_language" != "python" && "$stage_language" != "r" ]]; then
  fail 'CONFIG_ERROR' "module.config.ini 的 language 只能是 python 或 r，实际值: $stage_language" '修正 [module] language 后重试' 2
  exit $?
fi
if [[ -z "$stage_language" ]]; then
  if [[ -f "$MODULE_ROOT/scripts/init.py" && -x "$(command -v python3 2>/dev/null || true)" ]]; then
    stage_language="python"
  elif [[ -f "$MODULE_ROOT/scripts/init.R" && -x "$(command -v Rscript 2>/dev/null || true)" ]]; then
    stage_language="r"
  fi
fi

run_script() {
  local name="$1"
  local -a stage_args=("$CONFIG")
  if [[ "$name" != "init" ]]; then
    stage_args+=(--output "$OUTPUT")
  fi
  if [[ "$stage_language" != "r" && -f "$MODULE_ROOT/scripts/$name/main.py" ]]; then
    command -v python3 >/dev/null 2>&1 || { fail 'DEPENDENCY_ERROR' '找不到 Python 3 运行时' '安装或加载已批准的 Python 环境' 3; return $?; }
    python3 "$MODULE_ROOT/scripts/$name/main.py" "${stage_args[@]}"
    return $?
  fi
  if [[ "$stage_language" != "python" && -f "$MODULE_ROOT/scripts/$name/main.R" ]]; then
    command -v Rscript >/dev/null 2>&1 || { fail 'DEPENDENCY_ERROR' '找不到 Rscript 运行时' '安装或加载已批准的 R 环境' 3; return $?; }
    Rscript "$MODULE_ROOT/scripts/$name/main.R" "${stage_args[@]}"
    return $?
  fi
  if [[ "$stage_language" != "r" && -f "$MODULE_ROOT/scripts/$name.py" ]]; then
    command -v python3 >/dev/null 2>&1 || { fail 'DEPENDENCY_ERROR' '找不到 Python 3 运行时' '安装或加载已批准的 Python 环境' 3; return $?; }
    python3 "$MODULE_ROOT/scripts/$name.py" "${stage_args[@]}"
    return $?
  fi
  if [[ "$stage_language" != "python" && -f "$MODULE_ROOT/scripts/$name.R" ]]; then
    command -v Rscript >/dev/null 2>&1 || { fail 'DEPENDENCY_ERROR' '找不到 Rscript 运行时' '安装或加载已批准的 R 环境' 3; return $?; }
    Rscript "$MODULE_ROOT/scripts/$name.R" "${stage_args[@]}"
    return $?
  fi
  fail 'CONFIG_ERROR' "找不到 $name 阶段脚本" "创建 scripts/$name/main.R 或 main.py" 2
  return $?
}

if [[ "$STAGE" == "init" ]]; then
  if run_script init; then
    status=0
  else
    status=$?
  fi
  if [[ "$status" -eq 0 ]]; then
    exit 0
  elif [[ "$status" -eq 3 ]]; then
    fail 'DEPENDENCY_ERROR' 'init 阶段缺少运行环境' '加载合同指定的 R/Python 环境后重试' 3
    exit 3
  elif [[ "$status" -eq 2 ]]; then
    fail 'CONFIG_ERROR' 'init 阶段配置校验失败' '查看上面的具体错误并修正配置' 2
    exit 2
  else
    fail 'RUNTIME_ERROR' 'init 阶段校验失败' '查看上面的具体错误并修正配置' 1
    exit 1
  fi
fi

mkdir -p "$OUTPUT/log" || { fail 'OUTPUT_ERROR' "无法创建日志目录: $OUTPUT/log" '选择可写的输出目录' 1; exit $?; }
LOG="$OUTPUT/log/$STAGE.log"
if [[ "$STAGE" == "full" ]]; then
  # full 只保留一个自身日志；子阶段直接调用，不创建兄弟阶段日志。
  : > "$LOG" || { fail 'OUTPUT_ERROR' "无法写入日志: $LOG" '检查输出目录权限' 1; exit $?; }
  if {
    printf '%s\n' '开始 full：calculate → plot → report'
    if run_script calculate; then :; else exit $?; fi
    if run_script plot; then :; else exit $?; fi
    if run_script report; then :; else exit $?; fi
    printf '%s\n' 'full 阶段完成'
  } 2>&1 | tee -a "$LOG"; then
    status=0
  else
    status=${PIPESTATUS[0]}
  fi
else
  : > "$LOG" || { fail 'OUTPUT_ERROR' "无法写入日志: $LOG" '检查输出目录权限' 1; exit $?; }
  if run_script "$STAGE" 2>&1 | tee -a "$LOG"; then
    status=0
  else
    status=${PIPESTATUS[0]}
  fi
fi
if [[ "$status" -ne 0 ]]; then
  if [[ "$status" -eq 2 ]]; then
    if [[ "$STAGE" == "init" ]]; then
      fail 'CONFIG_ERROR' "阶段 $STAGE 的配置校验失败，详见 $LOG" '修正 module.config.ini 或阶段入口后重试' 2
    else
      fail 'EVIDENCE_ERROR' "阶段 $STAGE 的输入、合同或证据校验失败，详见 $LOG" '补齐真实输入和已批准合同后重试' 2
    fi
    exit 2
  fi
  if [[ "$status" -eq 3 ]]; then
    fail 'DEPENDENCY_ERROR' "阶段 $STAGE 缺少运行环境，详见 $LOG" '加载合同指定的 R/Python 环境后重试' 3
    exit 3
  fi
  fail 'RUNTIME_ERROR' "阶段 $STAGE 执行失败，详见 $LOG" '修正阶段脚本或输入后重试' 1
  exit 1
fi
exit 0
