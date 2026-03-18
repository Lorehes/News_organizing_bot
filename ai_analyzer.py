import json
from config import ai_client

SKIP = "SKIP"
DEFAULT_KEYWORDS = ["economy", "politics", "technology", "trade", "climate",
                    "security", "inflation", "diplomacy", "energy", "election"]


def extract_keywords(articles):
    """1단계 팩트 기사들에서 주요 이슈 키워드 10개를 추출"""
    headlines = "\n".join(
        f"- {a['title']}" for a in articles[:20]
    )
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are a news analyst. Based on the following headlines, "
                    "extract 10 trending keywords or phrases that are most relevant "
                    "for searching related news articles. "
                    "Each keyword should be 2-3 words in English, suitable for news search queries. "
                    "Return ONLY a JSON array of strings, e.g. [\"keyword1\", \"keyword2\", ...]"
                )},
                {"role": "user", "content": headlines}
            ]
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"  [AI] 키워드 추출 실패 ({e.__class__.__name__}), 기본 키워드 사용")
        return DEFAULT_KEYWORDS


def filter_and_summarize(title, description):
    """필터링 + 요약을 1번의 API 호출로 처리. 인사이트 없으면 'SKIP' 반환."""
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are a professional news analyst. "
                "First, determine if the article provides meaningful insight about politics, economy, society, technology, environment, or global affairs. "
                "If it is about crime/accidents, entertainment/celebrity, sports, weather, or lifestyle/food, reply ONLY with 'SKIP'. "
                "Otherwise, provide a neutral briefing in Korean with: "
                "1) 핵심 요약 (2-3 sentences) "
                "2) 주요 키워드 (3-5 keywords) "
                "3) 카테고리 (정치/경제/사회/기술/환경/건강 중 선택). "
                "Focus on factual context and policy implications."
            )},
            {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"}
        ]
    )
    return response.choices[0].message.content.strip()
