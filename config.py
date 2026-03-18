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

# === 1단계: 팩트 체크 (글로벌 1차 데이터) ===
# === 2단계: 국내/지역 팩트 ===
# === 3단계: 글로벌 교차 검증 ===
# === 4단계: 경제/산업 흐름 ===
# === 5단계: 미래 기술 및 지정학 ===
# === 보조: 서구권 여론 ===

NEWSAPI_SOURCES = [
    {"domain": "apnews.com",    "count": 3, "tier": 1},
    {"domain": "bbc.com",       "count": 3, "tier": 3},
    {"domain": "bloomberg.com", "count": 2, "tier": 4},
    {"domain": "cnn.com",       "count": 2, "tier": 6},
]

NEWSAPI_DOMAINS = ",".join(s["domain"] for s in NEWSAPI_SOURCES)

RSS_SOURCES = [
    # 1단계
    # (Reuters RSS 미지원 → GDELT)
    # 2단계
    {"domain": "en.yna.co.kr",      "count": 3, "tier": 2,
     "rss": "https://en.yna.co.kr/RSS/news.xml"},
    # 3단계
    {"domain": "aljazeera.com",     "count": 2, "tier": 3,
     "rss": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"domain": "scmp.com",          "count": 2, "tier": 3,
     "rss": "https://www.scmp.com/rss/91/feed"},
    # 4단계
    {"domain": "asia.nikkei.com",   "count": 2, "tier": 4,
     "rss": "https://asia.nikkei.com/rss/feed/nar"},
    {"domain": "ft.com",            "count": 2, "tier": 4,
     "rss": "https://www.ft.com/rss/home"},
    # 5단계
    {"domain": "thediplomat.com",   "count": 2, "tier": 5,
     "rss": "https://thediplomat.com/feed/"},
    {"domain": "technologyreview.com", "count": 2, "tier": 5,
     "rss": "https://www.technologyreview.com/feed/"},
    # 보조
    {"domain": "nytimes.com",       "count": 2, "tier": 6,
     "rss": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"domain": "japantimes.co.jp",  "count": 2, "tier": 6,
     "rss": "https://www.japantimes.co.jp/feed/"},
]

GDELT_SOURCES = [
    {"domain": "reuters.com",     "count": 3, "tier": 1},
    {"domain": "koreaherald.com", "count": 2, "tier": 2},
]

ALL_SOURCES = sorted(
    NEWSAPI_SOURCES + RSS_SOURCES + GDELT_SOURCES,
    key=lambda s: s["tier"]
)
