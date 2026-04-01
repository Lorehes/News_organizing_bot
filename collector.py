from __future__ import annotations

import re
import asyncio
import feedparser
import aiohttp
import trafilatura
from dataclasses import dataclass, field
from googlenewsdecoder import new_decoderv1


@dataclass
class Article:
    source: str
    source_role: str       # 팩트 / 교차검증 / 오피니언 / 헤드라인감시
    title: str
    url: str
    content: str           # 본문 or 헤드라인 (크롤링 실패 시 제목만)
    published_at: str
    has_body: bool = field(default=False)  # 본문 크롤링 성공 여부
    importance_score: float = field(default=0.0)
    score_reason: str = field(default="")


FEEDS = {
    "AP News":      {"url": "https://news.google.com/rss/search?q=site:apnews.com",    "role": "팩트"},
    "Reuters":      {"url": "https://news.google.com/rss/search?q=site:reuters.com",   "role": "팩트"},
    "Yonhap":       {"url": "https://en.yna.co.kr/RSS/news.xml",                      "role": "국내팩트"},
    "Korea Herald": {"url": "https://www.koreaherald.com/rss/newsAll",                 "role": "국내팩트"},
    "BBC World":    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",             "role": "교차검증"},
    "Al Jazeera":   {"url": "https://news.google.com/rss/search?q=site:aljazeera.com", "role": "교차검증"},
    "SCMP":         {"url": "https://www.scmp.com/rss/91/feed",                        "role": "교차검증"},
    "The Guardian": {"url": "https://www.theguardian.com/world/rss",                  "role": "교차검증"},
    "The Diplomat": {"url": "https://thediplomat.com/feed",                            "role": "지정학"},
    "NYT World":    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  "role": "오피니언",    "deferred": True},
    "CNN World":    {"url": "https://news.google.com/rss/search?q=site:cnn.com",       "role": "오피니언"},
    "Bloomberg":    {"url": "https://news.google.com/rss/search?q=site:bloomberg.com", "role": "헤드라인감시"},
    "FT":           {"url": "https://news.google.com/rss/search?q=site:ft.com",        "role": "헤드라인감시"},
    "Nikkei Asia":  {"url": "https://news.google.com/rss/search?q=site:asia.nikkei.com", "role": "헤드라인감시"},
}


def decode_google_news_url(google_url: str) -> str:
    """Google News 인코딩 URL → 실제 기사 URL 디코딩"""
    try:
        result = new_decoderv1(google_url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        pass
    return google_url  # 실패 시 원본 URL 유지


async def fetch_feed(session: aiohttp.ClientSession, name: str, config: dict) -> list[Article]:
    try:
        async with session.get(config["url"], timeout=aiohttp.ClientTimeout(total=10)) as resp:
            content = await resp.text()
        feed = feedparser.parse(content)
        articles = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "")
            articles.append(Article(
                source=name,
                source_role=config["role"],
                title=title,
                url=url,
                content=title,  # 초기값은 제목만, 크롤링 성공 시 본문으로 교체
                published_at=entry.get("published", ""),
            ))
        return articles
    except Exception as e:
        print(f"[수집 실패] {name}: {e}")
        return []


NOISE_PATTERNS = [
    # 뉴스레터/구독 유도
    r"(?i)sign\s*up\s*(for|to)\s*(our|the)?\s*(newsletter|daily|morning|alerts?).*",
    r"(?i)subscribe\s+(to|for|now).*",
    r"(?i)get\s+(our|the)\s+(morning|daily|evening)\s+(briefing|newsletter|report).*",
    r"(?i)register\s+(for|to)\s+(free|full)\s+access.*",
    # SNS/공유
    r"(?i)follow\s+us\s+on\s+(twitter|facebook|instagram|x|linkedin|social\s+media).*",
    r"(?i)share\s+this\s+(article|story|post).*",
    r"(?i)(like|tweet|pin|share)\s+on\s+(facebook|twitter|pinterest|x).*",
    # 광고/스폰서
    r"(?i)^advertisement$",
    r"(?i)^sponsored\s*(content|by)?.*$",
    r"(?i)^promoted\s*(content|story)?.*$",
    # 쿠키/개인정보
    r"(?i)cookie\s*(policy|preferences|settings|consent).*",
    r"(?i)we\s+use\s+cookies.*",
    r"(?i)privacy\s*(policy|notice|statement).*",
    r"(?i)by\s+continuing.*you\s+agree.*",
    # 관련 기사/추천
    r"(?i)^(related|more|also\s+read|read\s+(also|more|next)|recommended|you\s+may\s+also\s+like)\s*:?.*",
    r"(?i)^(더\s*보기|관련\s*기사|추천\s*기사)\s*:?.*",
    # 기자/에디터 정보
    r"(?i)^(reporting|written|edited|compiled)\s+by\s+.*",
    r"(?i)^(contributed|additional\s+reporting)\s+by\s+.*",
    # 저작권
    r"(?i)^(©|\(c\)|copyright)\s*\d{4}.*",
    r"(?i)^all\s+rights\s+reserved\.?$",
    # 앱 다운로드
    r"(?i)download\s+(our|the)\s+app.*",
    r"(?i)available\s+on\s+(the\s+)?(app\s+store|google\s+play).*",
]

NOISE_REGEX = [re.compile(p) for p in NOISE_PATTERNS]


def clean_body(text: str) -> str:
    """크롤링된 본문에서 노이즈 제거"""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if any(r.match(stripped) for r in NOISE_REGEX):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def fetch_body(article: Article) -> tuple[str, bool]:
    """본문 크롤링 시도. (본문 텍스트, 성공 여부) 반환"""
    try:
        downloaded = trafilatura.fetch_url(article.url)
        if not downloaded:
            return article.title, False
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if text and len(text.strip()) > 50:
            text = clean_body(text)
            if len(text.strip()) > 50:
                return text[:3000], True
        return article.title, False
    except Exception:
        return article.title, False


async def collect_all() -> list[Article]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, name, cfg) for name, cfg in FEEDS.items()]
        results = await asyncio.gather(*tasks)

    all_articles = [a for batch in results for a in batch]

    # Google News 경유 URL → 실제 기사 URL 디코딩
    google_count = 0
    for article in all_articles:
        if "news.google.com" in article.url:
            article.url = decode_google_news_url(article.url)
            google_count += 1
            await asyncio.sleep(0.5)  # rate limit 방지
    if google_count:
        print(f"[URL 디코딩] Google News {google_count}건 → 실제 URL 변환 완료")

    # 본문 크롤링 (deferred 소스 제외)
    body_success = 0
    deferred_count = 0
    for article in all_articles:
        if FEEDS.get(article.source, {}).get("deferred"):
            deferred_count += 1
            continue  # 중요도 점수화 후 선별 크롤링
        article.content, article.has_body = fetch_body(article)
        if article.has_body:
            body_success += 1
        await asyncio.sleep(1.0)  # 요청 간격

    headline_only = len(all_articles) - body_success - deferred_count
    print(f"[수집 완료] 총 {len(all_articles)}건 (본문 {body_success}건 / 헤드라인만 {headline_only}건 / 지연 크롤링 {deferred_count}건)")
    return all_articles


def crawl_deferred(articles: list[Article]) -> int:
    """중요도 점수화 후 선별된 기사만 크롤링 (NYT 등 무료 한도 절약)"""
    crawled = 0
    for article in articles:
        if not FEEDS.get(article.source, {}).get("deferred"):
            continue
        if article.has_body:
            continue
        article.content, article.has_body = fetch_body(article)
        if article.has_body:
            crawled += 1
    print(f"[지연 크롤링] {crawled}건 본문 추출 성공")
    return crawled
