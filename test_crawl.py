"""Phase 1~2 실행 후 크롤링 성공/실패 현황 리포트"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from collector import collect_all
from deduplicator import clean


async def main():
    print("=" * 60)
    print("크롤링 현황 테스트")
    print("=" * 60)

    # Phase 1: 수집 + 크롤링
    print("\n[1/2] 뉴스 수집 + 본문 크롤링 중...")
    articles = await collect_all()

    # Phase 2: 정제
    print("\n[2/2] 정제 중...")
    articles = clean(articles)

    # 소스별 통계
    stats = {}
    for a in articles:
        if a.source not in stats:
            stats[a.source] = {"total": 0, "body": 0, "headline": 0, "role": a.source_role}
        stats[a.source]["total"] += 1
        if a.has_body:
            stats[a.source]["body"] += 1
        else:
            stats[a.source]["headline"] += 1

    body_total = sum(s["body"] for s in stats.values())
    headline_total = sum(s["headline"] for s in stats.values())

    # 리포트 출력
    print("\n" + "=" * 60)
    print(f"총 {len(articles)}건 | 본문 {body_total}건 | 헤드라인만 {headline_total}건")
    print("=" * 60)

    print(f"\n{'소스':<16} {'역할':<10} {'총':<5} {'본문':<5} {'헤드라인':<5} {'성공률':<8}")
    print("-" * 60)
    for source, s in sorted(stats.items(), key=lambda x: x[1]["body"], reverse=True):
        rate = f"{s['body'] / s['total'] * 100:.0f}%" if s["total"] > 0 else "0%"
        print(f"{source:<16} {s['role']:<10} {s['total']:<5} {s['body']:<5} {s['headline']:<5} {rate:<8}")

    # 헤드라인만 가져온 기사 샘플 (소스별 최대 2건씩)
    print("\n" + "=" * 60)
    print("[헤드라인만 가져온 기사 샘플 + 실패 원인 추정]")
    print("=" * 60)

    FAIL_REASONS = {
        "Bloomberg":    "하드 페이월 — Google News 경유, 원본 접근 불가",
        "FT":           "하드 페이월 — Google News 경유, 원본 접근 불가",
        "Nikkei Asia":  "하드 페이월 — Google News 경유, 원본 접근 불가",
        "NYT World":    "소프트 페이월 — 무료 한도 초과 시 차단",
        "SCMP":         "소프트 페이월 — 일부 기사 접근 제한",
        "Reuters":      "봇 감지 — 자동 크롤링 차단",
        "CNN World":    "봇 감지 — 자동 크롤링 차단",
        "AP News":      "봇 감지 또는 동적 렌더링 — JS 기반 페이지",
        "BBC World":    "봇 감지 또는 리다이렉트 — 지역 제한 가능",
    }

    shown = {}
    for a in articles:
        if a.has_body:
            continue
        if shown.get(a.source, 0) >= 2:
            continue
        shown[a.source] = shown.get(a.source, 0) + 1
        reason = FAIL_REASONS.get(a.source, "알 수 없음 — 사이트 구조 확인 필요")
        print(f"\n  [{a.source}] {a.title}")
        print(f"  URL: {a.url}")
        print(f"  실패 원인: {reason}")

    # 본문 성공 기사 샘플 (3건)
    print("\n" + "=" * 60)
    print("[본문 추출 성공 샘플 (앞 200자)]")
    print("=" * 60)
    body_count = 0
    for a in articles:
        if not a.has_body:
            continue
        body_count += 1
        if body_count > 3:
            break
        print(f"\n  [{a.source}] {a.title}")
        print(f"  본문: {a.content[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
