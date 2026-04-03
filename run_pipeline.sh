#!/bin/bash
# 글로벌 뉴스 인텔리전스 파이프라인 — 자동 실행 스크립트

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
VENV="$PROJECT_DIR/venv/bin/activate"
LM_STUDIO_URL="http://localhost:1234/v1/models"
MAX_WAIT=300  # LM Studio 대기 최대 5분

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d).log"

echo "========================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 파이프라인 시작" >> "$LOG_FILE"

# 1. LM Studio 실행 확인 및 대기
echo "[$(date '+%H:%M:%S')] LM Studio 확인 중..." >> "$LOG_FILE"
waited=0
while ! curl -s "$LM_STUDIO_URL" > /dev/null 2>&1; do
    if [ $waited -ge $MAX_WAIT ]; then
        echo "[$(date '+%H:%M:%S')] LM Studio 미응답 (${MAX_WAIT}초 초과) — 중단" >> "$LOG_FILE"
        osascript -e 'display notification "LM Studio가 실행되지 않아 브리핑을 생성할 수 없습니다." with title "뉴스 파이프라인 실패"'
        exit 1
    fi
    sleep 10
    waited=$((waited + 10))
done
echo "[$(date '+%H:%M:%S')] LM Studio 준비 완료 (${waited}초 대기)" >> "$LOG_FILE"

# 2. 파이프라인 실행
source "$VENV"
cd "$PROJECT_DIR"
python main.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 3. 결과 알림
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%H:%M:%S')] 파이프라인 완료 (정상)" >> "$LOG_FILE"
    osascript -e 'display notification "오늘의 브리핑이 발송되었습니다." with title "뉴스 파이프라인 완료"'
else
    echo "[$(date '+%H:%M:%S')] 파이프라인 실패 (exit code: $EXIT_CODE)" >> "$LOG_FILE"
    osascript -e 'display notification "파이프라인 실행 중 오류가 발생했습니다. 로그를 확인하세요." with title "뉴스 파이프라인 실패"'
fi

# 4. 오래된 로그 정리 (30일)
find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null
