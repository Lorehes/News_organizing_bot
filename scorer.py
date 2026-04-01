from __future__ import annotations

import re
import time
import requests
import json

from collector import Article

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3-14b-mlx"  # LM Studio에서 로드한 모델명

# 가중치 설정
W_GLOBAL = 0.40      # 글로벌 파급력
W_STRUCTURAL = 0.35  # 구조적 변화 신호
W_KOREA = 0.25       # 한국 관련성


def score_articles(articles: list[Article]) -> list[Article]:
    """Qwen3로 기사별 중요도 3축 평가 → 가중 합산"""
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


SCORING_PROMPT = """/no_think
당신은 글로벌 뉴스 중요도 분석 전문가입니다.
아래 기사들을 3가지 기준으로 각각 1~10점 평가하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기준 1: 글로벌 파급력 (global)
여러 국가·시장·국제기구에 동시 영향을 미치는 정도

  9~10: 전쟁·휴전 선언, 글로벌 금융위기, UN안보리 결의, 주요국 정권교체
  7~8 : 양자 정상회담, 경제제재 발동, 대규모 무역협정, 중앙은행 금리결정
  5~6 : 단일 국가 정책변화, 특정 산업 규제, 지역 분쟁 진전
  3~4 : 지역적 이슈, 제한적 국제 영향
  1~2 : 국내 단신, 연예, 스포츠, 생활 뉴스

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기준 2: 구조적 변화 신호 (structural)
단기 이벤트가 아닌 장기 흐름의 변곡점 여부

  9~10: 패러다임 전환 (새 동맹체제, 기술 패권 이동, 체제 전환)
  7~8 : 주요 정책 선회, 새 규제 프레임워크 도입, 공급망 재편
  5~6 : 기존 추세 지속, 예상된 전개
  3~4 : 정례 행사, 예정된 회의, 반복 이슈
  1~2 : 일회성 사건, 체계적 함의 없음

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기준 3: 한국 관련성 (korea)
한국 경제·안보·사회에 미치는 직간접 영향

  9~10: 한국 직접 언급, 한반도 안보 위협, 주요 교역국의 대한국 정책
  7~8 : 반도체·배터리 공급망, 동아시아 안보 변동, 원유·환율 직접 영향
  5~6 : 글로벌 트렌드의 간접 영향 (세계 경기, 기술 규제 등)
  3~4 : 약한 연관성
  1~2 : 한국과 무관

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ 헤드라인 전용 규칙:
(헤드라인만)으로 표시된 기사는 본문이 없습니다.
- 제목만으로 명확히 판단 가능한 경우에만 높은 점수 허용
- 판단 근거가 부족하면 각 기준을 5점(중립)으로 보수적 처리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{articles}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이:
{{
  "scores": [
    {{"index": 0, "global": 8, "structural": 7, "korea": 6, "reason": "이유 한 줄"}},
    {{"index": 1, "global": 5, "structural": 4, "korea": 3, "reason": "이유 한 줄"}}
  ]
}}"""


def _score_batch(batch: list[Article], offset: int, max_retries: int = 3) -> list[Article]:
    items = []
    for idx, a in enumerate(batch):
        content_label = "본문" if a.has_body else "헤드라인만"
        items.append(f"[{offset + idx}] [{a.source_role}] {a.source} ({content_label})\n제목: {a.title}\n내용: {a.content[:300]}")

    prompt = SCORING_PROMPT.format(articles="\n---\n".join(items))

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
                g = _clamp(s.get("global", 5))
                st = _clamp(s.get("structural", 5))
                k = _clamp(s.get("korea", 5))
                # 가중 합산은 Python에서 직접 계산
                article.importance_score = round(g * W_GLOBAL + st * W_STRUCTURAL + k * W_KOREA, 1)
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


def _clamp(value, lo=1, hi=10) -> float:
    """점수를 1~10 범위로 제한"""
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return 5.0


def select_top(articles: list[Article], top_n: int = 30) -> list[Article]:
    """상위 N건 선별"""
    return sorted(articles, key=lambda x: x.importance_score, reverse=True)[:top_n]
