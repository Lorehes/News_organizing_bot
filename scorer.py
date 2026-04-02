from __future__ import annotations

import re
import time
import requests
import json
from pathlib import Path

from collector import Article

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3-14b-mlx"  # LM Studio에서 로드한 모델명

PROMPTS_DIR = Path(__file__).parent / "prompts"

# 가중치 설정
W_GLOBAL = 0.40      # 글로벌 파급력
W_STRUCTURAL = 0.35  # 구조적 변화 신호
W_KOREA = 0.25       # 한국 관련성


def score_articles(articles: list[Article]) -> list[Article]:
    """Qwen3로 기사별 중요도 3축 평가 → 가중 합산"""
    batch_size = 20
    all_scored = []
    total_batches = (len(articles) + batch_size - 1) // batch_size

    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  [배치 {batch_num}/{total_batches}] {len(batch)}건 점수화 중...")
        scored = _score_batch(batch, offset=i)
        all_scored.extend(scored)
        print(f"  [배치 {batch_num}/{total_batches}] 완료")

    # 중요도 내림차순 정렬
    all_scored.sort(key=lambda x: x.importance_score, reverse=True)
    return all_scored


SCORING_PROMPT = (PROMPTS_DIR / "scoring_prompt.txt").read_text(encoding="utf-8")


def _score_batch(batch: list[Article], offset: int, max_retries: int = 3) -> list[Article]:
    # 배치 내 0-based 인덱스 사용 (Qwen3가 항상 0부터 반환하도록)
    items = []
    expected_indices = set(range(len(batch)))
    for idx, a in enumerate(batch):
        content_label = "본문" if a.has_body else "헤드라인만"
        items.append(f"[{idx}] [{a.source_role}] {a.source} ({content_label})\n제목: {a.title}\n내용: {a.content[:300]}")

    prompt = SCORING_PROMPT.format(
        articles="\n---\n".join(items),
        count=len(batch),
        last_index=len(batch) - 1,
    )

    for attempt in range(max_retries):
        try:
            res = requests.post(LM_STUDIO_URL, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000,
            }, timeout=120)

            content = res.json()["choices"][0]["message"]["content"]
            # Qwen3 응답에서 JSON 블록 추출 (thinking 텍스트 제거)
            json_match = re.search(r'\{[\s\S]*"scores"[\s\S]*\}', content)
            result = json.loads(json_match.group())
            score_map = {s["index"]: s for s in result["scores"]}

            # 반환된 index 검증
            returned_indices = set(score_map.keys())
            missing = expected_indices - returned_indices
            if missing:
                print(f"  [경고] 배치 {offset}: index {missing} 누락 → 기본값 5.0 적용")

            for idx, article in enumerate(batch):
                s = score_map.get(idx, {})
                g = _clamp(s.get("global", 5))
                st = _clamp(s.get("structural", 5))
                k = _clamp(s.get("korea", 5))
                # 가중 합산은 Python에서 직접 계산
                article.importance_score = round(g * W_GLOBAL + st * W_STRUCTURAL + k * W_KOREA, 1)
                article.score_reason = s.get("reason", "")

                if idx not in returned_indices:
                    article.score_reason = "[기본값] LLM 응답 누락"

            return batch

        except Exception as e:
            print(f"[점수화 실패] 배치 {offset}, 시도 {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)

    # 모든 재시도 실패 시 기본값
    print(f"[점수화 포기] 배치 {offset}: {max_retries}회 모두 실패 → 전체 기본값 5.0")
    for article in batch:
        article.importance_score = 5.0
        article.score_reason = "[기본값] 점수화 실패"
    return batch


def _clamp(value, lo=1, hi=10) -> float:
    """점수를 1~10 범위로 제한"""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 5.0


def select_top(articles: list[Article], top_n: int = 30) -> list[Article]:
    """상위 N건 선별"""
    return sorted(articles, key=lambda x: x.importance_score, reverse=True)[:top_n]
