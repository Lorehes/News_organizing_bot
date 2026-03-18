import sys
import feedparser
from config import RSS_SOURCES, NEWSAPI_SOURCES, GDELT_SOURCES

ALL_DOMAINS = {s["domain"]: s for s in RSS_SOURCES}


def list_sources():
    print("\n=== 사용 가능한 RSS 매체 ===\n")
    for i, s in enumerate(RSS_SOURCES, 1):
        print(f"  {i:2d}. [{s['domain']}] (Tier {s['tier']})")
    print(f"\n  * NewsAPI 전용: {', '.join(s['domain'] for s in NEWSAPI_SOURCES)}")
    print(f"  * GDELT 전용: {', '.join(s['domain'] for s in GDELT_SOURCES)}")


def read_feed(domain, num_articles=10):
    source = ALL_DOMAINS.get(domain)
    if not source:
        print(f"'{domain}'은 RSS 목록에 없습니다.")
        list_sources()
        return

    print(f"\n=== {domain} (Tier {source['tier']}) 최신 기사 ===\n")
    feed = feedparser.parse(source["rss"])

    if not feed.entries:
        print("기사를 불러올 수 없습니다.")
        return

    for i, entry in enumerate(feed.entries[:num_articles], 1):
        title = entry.get("title", "제목 없음")
        summary = entry.get("summary", "")[:200]
        link = entry.get("link", "")
        published = entry.get("published", "")

        print(f"[{i}] {title}")
        if published:
            print(f"    날짜: {published}")
        if summary:
            print(f"    요약: {summary}")
        print(f"    링크: {link}")
        print()


def read_all(num_per_source=3):
    print("\n=== 전체 매체 최신 기사 ===\n")
    for source in RSS_SOURCES:
        print(f"--- {source['domain']} (Tier {source['tier']}) ---")
        try:
            feed = feedparser.parse(source["rss"])
            for i, entry in enumerate(feed.entries[:num_per_source], 1):
                title = entry.get("title", "제목 없음")
                link = entry.get("link", "")
                print(f"  [{i}] {title}")
                print(f"      {link}")
            print()
        except Exception:
            print(f"  [실패] RSS를 불러올 수 없습니다.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python rss_reader.py list              # 매체 목록")
        print("  python rss_reader.py all               # 전체 매체 최신 기사")
        print("  python rss_reader.py reuters.com       # 특정 매체 기사")
        print("  python rss_reader.py reuters.com 20    # 특정 매체 20건")
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        list_sources()
    elif command == "all":
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        read_all(num)
    else:
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        read_feed(command, num)
