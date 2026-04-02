from __future__ import annotations

import anthropic
from datetime import datetime
from pathlib import Path

from collector import Article

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수

PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "briefing_system.txt").read_text(encoding="utf-8")
BRIEFING_TEMPLATE = (PROMPTS_DIR / "briefing_template.txt").read_text(encoding="utf-8")


def generate_briefing(top_articles: list[Article], max_retries: int = 3) -> dict:
    """Claude Sonnet으로 브리핑 생성 (재시도 최대 3회)"""

    today = datetime.now().strftime("%Y년 %m월 %d일")

    # 소스 역할별 그룹핑
    by_role: dict[str, list[Article]] = {}
    for a in top_articles:
        by_role.setdefault(a.source_role, []).append(a)

    sections = []
    for role, arts in by_role.items():
        lines = "\n".join([
            f"  [{a.source}] {a.title} (중요도 {a.importance_score:.1f})\n  {a.content[:500]}"
            for a in arts
        ])
        sections.append(f"[{role}]\n{lines}")

    prompt = BRIEFING_TEMPLATE.format(
        today=today,
        top_count=len(top_articles),
        sections="\n".join(sections),
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # stop_reason 확인 — 토큰 한도에서 잘렸는지 감지
            stop_reason = response.stop_reason
            if stop_reason == "max_tokens":
                print(f"[경고] 브리핑이 max_tokens({8000})에서 잘렸습니다. 출력이 불완전할 수 있습니다.")

            return {
                "text": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "truncated": stop_reason == "max_tokens",
            }
        except Exception as e:
            last_error = e
            print(f"[브리핑 생성 실패] 시도 {attempt + 1}/{max_retries}: {e}")

    raise RuntimeError(f"브리핑 생성 {max_retries}회 실패: {last_error}")
