#!/usr/bin/env bash
# 실행:
#   chmod +x scripts/loadtest/run_headless.sh
#   scripts/loadtest/run_headless.sh
# 테스트 요약:
#   - locustfile.py를 헤드리스 모드로 실행
#   - 사용자 수/증가율/실행시간은 환경변수로 제어
#   - 결과 CSV를 scripts/loadtest/output 하위로 저장

set -euo pipefail

BASE_URL="${LOADTEST_BASE_URL:-http://127.0.0.1:8200}"
USERS="${LOADTEST_USERS:-50}"
SPAWN_RATE="${LOADTEST_SPAWN_RATE:-5}"
RUN_TIME="${LOADTEST_RUN_TIME:-10m}"
CSV_PREFIX="${LOADTEST_CSV_PREFIX:-scripts/loadtest/output/loadtest}"

mkdir -p "$(dirname "$CSV_PREFIX")"

locust \
  -f scripts/loadtest/locustfile.py \
  --host "$BASE_URL" \
  --headless \
  -u "$USERS" \
  -r "$SPAWN_RATE" \
  -t "$RUN_TIME" \
  --csv "$CSV_PREFIX" \
  --csv-full-history
