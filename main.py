import asyncio
from dotenv import load_dotenv
load_dotenv()

from collector import collect_all, crawl_deferred
from deduplicator import clean
from scorer import score_articles, select_top
from briefing import generate_briefing
from sender import send_email


async def main():
    print("=" * 50)
    print("글로벌 뉴스 인텔리전스 파이프라인 시작")
    print("=" * 50)

    # 1단계: 수집
    print("\n[1/5] 뉴스 수집 중...")
    articles = await collect_all()
    collected_count = len(articles)

    # 2단계: 정제 (알고리즘, LLM 없음)
    print("\n[2/5] 중복 제거 및 정제 중...")
    articles = clean(articles)
    cleaned_count = len(articles)

    # 3단계: 중요도 점수화 (Qwen3 로컬)
    print("\n[3/5] 중요도 점수화 중... (Qwen3)")
    articles = score_articles(articles)
    top_articles = select_top(articles, top_n=30)

    # 3.5단계: 지연 크롤링 (NYT 등 무료 한도 절약 — 상위 기사만 본문 추출)
    print("\n[3.5/5] 상위 기사 지연 크롤링 중... (NYT 등)")
    crawl_deferred(top_articles)

    # 4단계: 브리핑 생성 (Claude Sonnet)
    print("\n[4/5] 브리핑 생성 중... (Claude Sonnet)")
    result = generate_briefing(top_articles)
    print(f"      토큰 사용: input {result['input_tokens']}, output {result['output_tokens']}")

    # 5단계: 발송
    print("\n[5/5] 브리핑 발송 중...")
    send_email(result["text"], {
        "collected": collected_count,
        "cleaned": cleaned_count,
        "top": len(top_articles),
    })


if __name__ == "__main__":
    asyncio.run(main())
