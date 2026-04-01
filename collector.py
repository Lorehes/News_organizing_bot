from __future__ import annotations

import asyncio
import feedparser
import aiohttp
from newspaper import Article as NewspaperArticle
from dataclasses import dataclass, field


@dataclass
class Article:
    source: str
    source_role: str       # 팩트 / 교차검증 / 오피니언 / 헤드라인감시
    title: str
    url: str
    content: str           # 본문 or 요약 (소스에 따라 다름)
    published_at: str
    importance_score: float = field(default=0.0)
    score_reason: str = field(default="")


FEEDS = {
    "AP News":      {"url": "https://rsshub.app/apnews/topics/world-news",            "role": "팩트",       "crawl": False},
    "Reuters":      {"url": "https://feeds.reuters.com/reuters/worldNews",             "role": "팩트",       "crawl": False},
    "Yonhap":       {"url": "https://en.yna.co.kr/RSS/news.xml",                      "role": "국내팩트",   "crawl": True},
    "Korea Herald": {"url": "https://rss.koreaherald.com/list.php?ct=020100000000",    "role": "국내팩트",   "crawl": True},
    "BBC World":    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",             "role": "교차검증",   "crawl": False},
    "Al Jazeera":   {"url": "https://www.aljazeera.com/xml/rss/all.xml",               "role": "교차검증",   "crawl": True},
    "SCMP":         {"url": "https://www.scmp.com/rss/91/feed",                        "role": "교차검증",   "crawl": False},
    "The Diplomat": {"url": "https://thediplomat.com/feed",                            "role": "지정학",     "crawl": True},
    "NYT World":    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  "role": "오피니언",   "crawl": False},
    "CNN World":    {"url": "https://rss.cnn.com/rss/edition_world.rss",               "role": "오피니언",   "crawl": False},
    "Bloomberg":    {"url": "https://news.google.com/rss/search?q=site:bloomberg.com", "role": "헤드라인감시", "crawl": False},
    "FT":           {"url": "https://news.google.com/rss/search?q=site:ft.com",        "role": "헤드라인감시", "crawl": False},
    "Nikkei Asia":  {"url": "https://news.google.com/rss/search?q=site:asia.nikkei.com", "role": "헤드라인감시", "crawl": False},
}


async def fetch_feed(session: aiohttp.ClientSession, name: str, config: dict) -> list[Article]:
    try:
        async with session.get(config["url"], timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.text()
        feed = feedparser.parse(content)
        articles = []
        for entry in feed.entries[:20]:
            articles.append(Article(
                source=name,
                source_role=config["role"],
                title=entry.get("title", "").strip(),
                url=entry.get("link", ""),
                content=entry.get("summary", "")[:500],
                published_at=entry.get("published", ""),
            ))
        return articles
    except Exception as e:
        print(f"[수집 실패] {name}: {e}")
        return []


def fetch_body(article: Article) -> str:
    """크롤링 가능 소스 본문 추출"""
    try:
        news = NewspaperArticle(article.url)
        news.download()
        news.parse()
        return news.text[:3000] if news.text else article.content
    except Exception:
        return article.content


async def collect_all() -> list[Article]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, name, cfg) for name, cfg in FEEDS.items()]
        results = await asyncio.gather(*tasks)

    all_articles = [a for batch in results for a in batch]

    # 크롤링 가능 소스 본문 추출
    for article in all_articles:
        if FEEDS[article.source]["crawl"]:
            article.content = fetch_body(article)
            await asyncio.sleep(1.5)  # 요청 간격

    print(f"[수집 완료] 총 {len(all_articles)}건")
    return all_articles
