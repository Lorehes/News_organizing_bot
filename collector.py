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
    content: str           # 본문 or 헤드라인 (크롤링 실패 시 제목만)
    has_body: bool = field(default=False)  # 본문 크롤링 성공 여부
    published_at: str
    importance_score: float = field(default=0.0)
    score_reason: str = field(default="")


FEEDS = {
    "AP News":      {"url": "https://rsshub.app/apnews/topics/world-news",            "role": "팩트"},
    "Reuters":      {"url": "https://feeds.reuters.com/reuters/worldNews",             "role": "팩트"},
    "Yonhap":       {"url": "https://en.yna.co.kr/RSS/news.xml",                      "role": "국내팩트"},
    "Korea Herald": {"url": "https://rss.koreaherald.com/list.php?ct=020100000000",    "role": "국내팩트"},
    "BBC World":    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",             "role": "교차검증"},
    "Al Jazeera":   {"url": "https://www.aljazeera.com/xml/rss/all.xml",               "role": "교차검증"},
    "SCMP":         {"url": "https://www.scmp.com/rss/91/feed",                        "role": "교차검증"},
    "The Diplomat": {"url": "https://thediplomat.com/feed",                            "role": "지정학"},
    "NYT World":    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  "role": "오피니언"},
    "CNN World":    {"url": "https://rss.cnn.com/rss/edition_world.rss",               "role": "오피니언"},
    "Bloomberg":    {"url": "https://news.google.com/rss/search?q=site:bloomberg.com", "role": "헤드라인감시"},
    "FT":           {"url": "https://news.google.com/rss/search?q=site:ft.com",        "role": "헤드라인감시"},
    "Nikkei Asia":  {"url": "https://news.google.com/rss/search?q=site:asia.nikkei.com", "role": "헤드라인감시"},
}


async def fetch_feed(session: aiohttp.ClientSession, name: str, config: dict) -> list[Article]:
    try:
        async with session.get(config["url"], timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.text()
        feed = feedparser.parse(content)
        articles = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "").strip()
            articles.append(Article(
                source=name,
                source_role=config["role"],
                title=title,
                url=entry.get("link", ""),
                content=title,  # 초기값은 제목만, 크롤링 성공 시 본문으로 교체
                published_at=entry.get("published", ""),
            ))
        return articles
    except Exception as e:
        print(f"[수집 실패] {name}: {e}")
        return []


def fetch_body(article: Article) -> tuple[str, bool]:
    """본문 크롤링 시도. (본문 텍스트, 성공 여부) 반환"""
    try:
        news = NewspaperArticle(article.url)
        news.download()
        news.parse()
        if news.text and len(news.text.strip()) > 50:
            return news.text[:3000], True
        return article.title, False
    except Exception:
        return article.title, False


async def collect_all() -> list[Article]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, name, cfg) for name, cfg in FEEDS.items()]
        results = await asyncio.gather(*tasks)

    all_articles = [a for batch in results for a in batch]

    # 모든 소스 본문 크롤링 시도
    body_success = 0
    for article in all_articles:
        article.content, article.has_body = fetch_body(article)
        if article.has_body:
            body_success += 1
        await asyncio.sleep(1.0)  # 요청 간격

    headline_only = len(all_articles) - body_success
    print(f"[수집 완료] 총 {len(all_articles)}건 (본문 {body_success}건 / 헤드라인만 {headline_only}건)")
    return all_articles
