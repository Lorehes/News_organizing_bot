from __future__ import annotations

import anthropic

from collector import Article

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수


def generate_briefing(top_articles: list[Article], max_retries: int = 3) -> dict:
    """Claude Sonnet으로 브리핑 생성 (재시도 최대 3회)"""

    # 소스 역할별 그룹핑
    by_role: dict[str, list[Article]] = {}
    for a in top_articles:
        by_role.setdefault(a.source_role, []).append(a)

    sections = []
    for role, arts in by_role.items():
        lines = "\n".join([
            f"  [{a.source}] {a.title} (중요도 {a.importance_score:.1f})\n  {a.content[:200]}"
            for a in arts
        ])
        sections.append(f"[{role}]\n{lines}")

    prompt = f"""다음은 오늘 전 세계에서 수집된 주요 뉴스입니다. (Qwen3가 중요도 상위 30건으로 선별)

{"=" * 60}
{chr(10).join(sections)}
{"=" * 60}

아래 형식으로 분석해주세요.

## 오늘의 세계 — 3줄 요약
(핵심 흐름 3가지를 각 1~2문장으로. 읽는 즉시 오늘 세계 상황을 파악할 수 있게)

## 영역별 브리핑

### 정치·안보
(주요 이슈 2~3개. 각 이슈당 3~5문장. 배경·현재·의미 순서로 서술)

### 경제·시장
(주요 이슈 2~3개. 각 이슈당 3~5문장. 수치와 흐름 포함)

### 기술·지정학
(주요 이슈 1~2개. 기술 패권 이동, 공급망 변화 중심)

### 한국 관련
(한국에 직간접 영향을 주는 이슈. 없으면 생략)

## 이번 주 주목할 변수
(향후 7일 내 전개될 가능성 있는 이슈 2~3개. 근거 포함)

## 오늘 꼭 읽어볼 기사 Top 5
(위 기사 중 정독 가치가 높은 5개 선정. 형식:)
1. [소스] 제목
   추천 이유: (전략적 가치 한 줄)
   링크: URL

(2~5번 동일)

---
총 분량 기준: 읽는 데 약 15분"""

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "text": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        except Exception as e:
            last_error = e
            print(f"[브리핑 생성 실패] 시도 {attempt + 1}/{max_retries}: {e}")

    raise RuntimeError(f"브리핑 생성 {max_retries}회 실패: {last_error}")
