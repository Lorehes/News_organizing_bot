from __future__ import annotations

import re
import time
import requests
import json

from collector import Article

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3-14b-mlx"  # LM Studio에서 로드한 모델명


def score_articles(articles: list[Article]) -> list[Article]:
    """Qwen3로 기사별 중요도 1~10점 점수화"""
    batch_size = 10
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


def _score_batch(batch: list[Article], offset: int, max_retries: int = 3) -> list[Article]:
    items = []
    for idx, a in enumerate(batch):
        content_label = "본문" if a.has_body else "헤드라인만"
        items.append(f"[{offset + idx}] [{a.source_role}] {a.source} ({content_label})\n제목: {a.title}\n내용: {a.content[:300]}")

    prompt = f"""/no_think
다음 뉴스 기사들의 중요도를 평가해주세요.

평가 기준:
- 글로벌 파급력: 여러 국가·시장에 영향을 미치는 이슈
- 구조적 변화 신호: 단기 이벤트가 아닌 장기 흐름의 변곡점
- 한국 관련성: 한국 경제·안보·사회에 직간접 영향

{"---".join(items)}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이:
{{
  "scores": [
    {{"index": 0, "score": 8.5, "reason": "이유 한 줄"}},
    {{"index": 1, "score": 6.0, "reason": "이유 한 줄"}}
  ]
}}"""

    for attempt in range(max_retries):
        try:
            res = requests.post(LM_STUDIO_URL, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            }, timeout=120)

            content = res.json()["choices"][0]["message"]["content"]
            # Qwen3 응답에서 JSON 블록 추출 (thinking 텍스트 제거)
            json_match = re.search(r'\{[\s\S]*"scores"[\s\S]*\}', content)
            result = json.loads(json_match.group())
            score_map = {s["index"]: s for s in result["scores"]}

            for idx, article in enumerate(batch):
                s = score_map.get(offset + idx, {})
                article.importance_score = s.get("score", 5.0)
                article.score_reason = s.get("reason", "")

            return batch

        except Exception as e:
            print(f"[점수화 실패] 배치 {offset}, 시도 {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)

    # 모든 재시도 실패 시 기본값
    print(f"[점수화 포기] 배치 {offset}: {max_retries}회 모두 실패")
    for article in batch:
        article.importance_score = 5.0
        article.score_reason = ""
    return batch


def select_top(articles: list[Article], top_n: int = 30) -> list[Article]:
    """상위 N건 선별"""
    return sorted(articles, key=lambda x: x.importance_score, reverse=True)[:top_n]
