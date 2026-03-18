import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from newsapi import NewsApiClient
from openai import OpenAI


load_dotenv()

newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))

ai_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("GITHUB_TOKEN")
)

# (도메인, 기사 수, 우선순위 티어)
NEWS_SOURCES = [
    # Tier 1: 팩트 기반 통신사 — bias 최소, 1차 데이터
    {"domain": "reuters.com",       "count": 6, "tier": 1},
    {"domain": "apnews.com",        "count": 6, "tier": 1},
    # Tier 2: 글로벌 영향력 해석 — 정책·경제 심층 분석
    {"domain": "bbc.com",           "count": 6, "tier": 2},
    {"domain": "nytimes.com",       "count": 6, "tier": 2},
    # Tier 3: 한국 팩트 — 국내 정치·경제·북한
    {"domain": "en.yna.co.kr",      "count": 4, "tier": 3},
    {"domain": "koreaherald.com",   "count": 4, "tier": 3},
    # Tier 4: 경제·전략 분석 — 시장·금융 인사이트
    {"domain": "bloomberg.com",     "count": 4, "tier": 4},
    {"domain": "ft.com",            "count": 4, "tier": 4},
    # Tier 5: 아시아 지역 시각 — 동북아 연결
    {"domain": "asia.nikkei.com",   "count": 3, "tier": 5},
    {"domain": "scmp.com",          "count": 3, "tier": 5},
    # Tier 6: 보조 참고 — 해석 있으나 편차 존재
    {"domain": "cnn.com",           "count": 3, "tier": 6},
    {"domain": "japantimes.co.jp",  "count": 3, "tier": 6},
    {"domain": "thediplomat.com",   "count": 2, "tier": 6},
    # Tier 7: 중국 입장 확인용 — propaganda 성격, 참고만
    {"domain": "chinadaily.com.cn", "count": 1, "tier": 7},
    {"domain": "globaltimes.cn",    "count": 1, "tier": 7},
]

NEWS_DOMAINS = ",".join(s["domain"] for s in NEWS_SOURCES)


def get_articles(from_date, to_date, page_size=100):
    response = newsapi.get_everything(
        domains=NEWS_DOMAINS,
        from_param=from_date,
        to=to_date,
        language="en",
        sort_by="publishedAt",
        page_size=page_size,
    )
    return response.get("articles", [])


def is_insightful(title, description):
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a news filter. Determine if the following news article provides meaningful insight about politics, economy, society, technology, environment, or global affairs. Exclude: crime/accidents, entertainment/celebrity, sports, weather, lifestyle/food. Reply ONLY with 'yes' or 'no'."},
            {"role": "user", "content": f"Title: {title}\nDescription: {description}"}
        ]
    )
    return response.choices[0].message.content.strip().lower() == "yes"


def summarize(title, description):
    response = ai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a news analyst. Summarize the following news article in Korean based on the title and description. Include: 1) 핵심 요약 (2-3 sentences) 2) 주요 키워드 (3-5 keywords) 3) 카테고리 (정치/경제/사회/기술/환경/건강 중 선택)"},
            {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"}
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    all_articles = get_articles(yesterday, today)
    print(f"총 {len(all_articles)}건 수집\n")

    # 기사를 매체별로 분류
    domain_articles = {}
    for article in all_articles:
        url = article.get("url", "")
        for s in NEWS_SOURCES:
            if s["domain"] in url:
                domain_articles.setdefault(s["domain"], []).append(article)
                break

    # 티어 순서대로 처리 (낮은 티어 = 높은 우선순위)
    count = 0
    for src in sorted(NEWS_SOURCES, key=lambda s: s["tier"]):
        domain = src["domain"]
        target = src["count"]
        filled = 0

        for article in domain_articles.get(domain, []):
            if filled >= target:
                break

            title = article["title"]
            description = article.get("description", "")
            source_name = article["source"]["name"]

            try:
                if not is_insightful(title, description):
                    continue
            except Exception:
                continue

            filled += 1
            count += 1
            print(f"\n[{count}] [Tier {src['tier']}] [{source_name}] {title}")
            print("----------------")
            try:
                result = summarize(title, description)
                print(result)
            except Exception:
                print("[건너뜀] 콘텐츠 필터에 의해 요약할 수 없는 기사입니다.")
            print("================")

        if filled > 0:
            print(f"  → {domain}: {filled}/{target}건 완료")

    print(f"\n총 {count}건 인사이트 기사 요약 완료")
