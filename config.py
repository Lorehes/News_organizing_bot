import os
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
