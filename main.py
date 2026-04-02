from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from collector import collect_all, crawl_deferred, Article
from deduplicator import clean
from scorer import score_articles, select_top
from briefing import generate_briefing
from sender import send_email

CACHE_DIR = Path("cache")
CACHE_MAX_AGE_DAYS = 7


def _save_checkpoint(articles: list[Article], stage: str):
    """단계별 중간 데이터 저장 (실패 시 재시작 방지)"""
    CACHE_DIR.mkdir(exist_ok=True)
    data = []
    for a in articles:
        data.append({
            "source": a.source,
            "source_role": a.source_role,
            "title": a.title,
            "url": a.url,
            "content": a.content,
            "published_at": a.published_at,
            "has_body": a.has_body,
            "importance_score": a.importance_score,
            "score_reason": a.score_reason,
        })
    filepath = CACHE_DIR / f"{stage}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def _clean_old_cache():
    """7일 이상 된 캐시 파일 자동 삭제"""
    if not CACHE_DIR.exists():
        return
    now = time.time()
    max_age = CACHE_MAX_AGE_DAYS * 86400
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        if now - f.stat().st_mtime > max_age:
            f.unlink()
            removed += 1
    if removed:
        print(f"[캐시 정리] {removed}개 오래된 파일 삭제")


def _load_checkpoint(stage: str) -> list[Article] | None:
    """중간 저장 데이터 로드"""
    filepath = CACHE_DIR / f"{stage}.json"
    if not filepath.exists():
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Article(**d) for d in data]


async def main():
    print("=" * 50)
    print("글로벌 뉴스 인텔리전스 파이프라인 시작")
    print(f"시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    total_start = time.time()
    _clean_old_cache()

    # 1단계: 수집
    try:
        print("\n[1/5] 뉴스 수집 중...")
        t = time.time()
        articles = await collect_all()
        collected_count = len(articles)
        _save_checkpoint(articles, "1_collected")
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[치명적 오류] 수집 실패: {e}")
        return

    # 2단계: 정제
    try:
        print("\n[2/5] 중복 제거 및 정제 중...")
        t = time.time()
        articles = clean(articles)
        cleaned_count = len(articles)
        _save_checkpoint(articles, "2_cleaned")
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[치명적 오류] 정제 실패: {e}")
        return

    # 3단계: 중요도 점수화
    try:
        print("\n[3/5] 중요도 점수화 중... (Qwen3)")
        t = time.time()
        articles = score_articles(articles)
        top_articles = select_top(articles, top_n=30)
        _save_checkpoint(top_articles, "3_scored")
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[오류] 점수화 실패: {e}")
        # 점수화 실패 시 체크포인트에서 복구 시도
        cached = _load_checkpoint("2_cleaned")
        if cached:
            print("      → 정제 데이터에서 복구, 점수 없이 앞 30건 사용")
            top_articles = cached[:30]
            cleaned_count = len(cached)
        else:
            print("[치명적 오류] 복구 불가")
            return

    # 3.5단계: 지연 크롤링
    try:
        print("\n[3.5/5] 상위 기사 지연 크롤링 중... (NYT 등)")
        t = time.time()
        crawl_deferred(top_articles)
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[경고] 지연 크롤링 실패 (계속 진행): {e}")

    # 4단계: 브리핑 생성
    try:
        print("\n[4/5] 브리핑 생성 중... (Claude Sonnet)")
        t = time.time()
        result = generate_briefing(top_articles)
        print(f"      토큰 사용: input {result['input_tokens']}, output {result['output_tokens']}")
        if result.get("truncated"):
            print("      ⚠ 브리핑이 잘렸습니다 — max_tokens 증가를 고려하세요")
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[치명적 오류] 브리핑 생성 실패: {e}")
        return

    # 5단계: 발송
    try:
        print("\n[5/5] 브리핑 발송 중...")
        t = time.time()
        send_email(result["text"], {
            "collected": collected_count,
            "cleaned": cleaned_count,
            "top": len(top_articles),
        })
        print(f"      소요: {time.time() - t:.1f}초")
    except Exception as e:
        print(f"[오류] 발송 실패: {e}")
        # 발송 실패해도 로컬 저장은 sender.py 내부에서 처리

    print(f"\n{'=' * 50}")
    print(f"파이프라인 완료 — 총 소요: {time.time() - total_start:.1f}초")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())
