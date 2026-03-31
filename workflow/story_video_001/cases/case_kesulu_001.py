from __future__ import annotations

from workflow.story_video_001.activities.activity_script_001 import main
from workflow.story_video_001.profiles.profile_kesulu_001 import PROFILE

'''
PYTHONPATH=/Users/test/code/Python/AI_vedio_demo/pythonProject \
/Users/test/code/Python/AI_vedio_demo/pythonProject/.venv/bin/python3 \
  -m workflow.story_video_001.cases.case_kesulu_001 \
  --input '/Users/test/code/Python/AI_vedio_demo/pythonProject/workflow/story_video_001/cases/input/001.md'
  --skip_images
  --skip_video
'''

'''
PYTHONPATH=/Users/test/code/Python/AI_vedio_demo/pythonProject \
/Users/test/code/Python/AI_vedio_demo/pythonProject/.venv/bin/python3 \
  -m workflow.story_video_001.cases.case_kesulu_001 \
  --input "/Users/test/code/Python/AI_vedio_demo/pythonProject/data/Data_results/script_results/001_整篇__seg001__e23f4f31_script_20260320_162701_304/00_input/001_整篇__seg001.md" \
  --only_video "/Users/test/code/Python/AI_vedio_demo/pythonProject/data/Data_results/script_results/001_整篇__seg001__e23f4f31_script_20260320_162701_304"
'''

'''
PYTHONPATH=/Users/test/code/Python/AI_vedio_demo/pythonProject \
/Users/test/code/Python/AI_vedio_demo/pythonProject/.venv/bin/python3 \
  -m workflow.story_video_001.cases.case_kesulu_001 \
  --input "/Users/test/code/Python/AI_vedio_demo/pythonProject/workflow/story_video_001/cases/input/001_整篇__seg001.md" \
'''

'''
INPUT_DIR="/Users/test/code/Python/AI_vedio_demo/pythonProject/workflow/story_video_001/cases/input"
PROJ="/Users/test/code/Python/AI_vedio_demo/pythonProject"
PY="$PROJ/.venv/bin/python3"

ts="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$PROJ/run_logs_story_video_001_$ts"
mkdir -p "$LOG_DIR"

echo "INPUT_DIR=$INPUT_DIR"
echo "LOG_DIR=$LOG_DIR"
echo "START=$(date)"

ok=0
fail=0

# 用 process substitution 避免 while 在 subshell 导致 ok/fail 计数丢失（zsh/bash 都适用）
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  safe="${base//\//_}"
  safe="${safe// /_}"
  log="$LOG_DIR/${safe}.log"

  echo "------------------------------------------------------------"
  echo "RUN: $f"
  echo "LOG: $log"
  echo "TIME: $(date)"
  echo "------------------------------------------------------------"

  # 关键点：不再静默；stdout/stderr 同时打印到终端 + 追加写入日志
  # stdbuf 让输出尽量按行刷新（mac 上可用；如你没装 coreutils，删掉 stdbuf 这一层也能用）
  ( PYTHONPATH="$PROJ" "$PY" -m workflow.story_video_001.cases.case_kesulu_001 \
      --input "$f" \
      --provider cloubic \
    ) 2>&1 | tee -a "$log"

  rc=${pipestatus[1]:-0}  # zsh: 取管道里 python 那条命令的退出码
  if [ "$rc" -eq 0 ]; then
    echo "OK: $f"
    ok=$((ok+1))
  else
    echo "FAIL(rc=$rc): $f"
    echo "  (see log) $log"
    fail=$((fail+1))
  fi

done < <(find "$INPUT_DIR" -type f \( -name "*.md" -o -name "*.txt" \) -print0)

echo "DONE=$(date)"
echo "SUMMARY ok=$ok fail=$fail"
echo "Logs saved in: $LOG_DIR"
'''

if __name__ == "__main__":
    raise SystemExit(main(profile=PROFILE))
