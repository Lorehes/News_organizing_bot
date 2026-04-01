import asyncio
from dotenv import load_dotenv
load_dotenv()

from collector import collect_all
from deduplicator import clean
from scorer import score_articles, select_top
from briefing import generate_briefing


async def main():
    print("=" * 50)
    print("글로벌 뉴스 인텔리전스 파이프라인 시작")
    print("=" * 50)

    # 1단계: 수집
    print("\n[1/4] 뉴스 수집 중...")
    articles = await collect_all()
    collected_count = len(articles)

    # 2단계: 정제 (알고리즘, LLM 없음)
    print("\n[2/4] 중복 제거 및 정제 중...")
    articles = clean(articles)
    cleaned_count = len(articles)

    # 3단계: 중요도 점수화 (Qwen3 로컬)
    print("\n[3/4] 중요도 점수화 중... (Qwen3)")
    articles = score_articles(articles)
    top_articles = select_top(articles, top_n=30)

    # 4단계: 브리핑 생성 (Claude Sonnet)
    print("\n[4/4] 브리핑 생성 중... (Claude Sonnet)")
    result = generate_briefing(top_articles)
    print(f"      토큰 사용: input {result['input_tokens']}, output {result['output_tokens']}")

    # 결과 출력 (Phase 5 발송 구현 전 임시)
    print("\n" + "=" * 50)
    print("브리핑 생성 완료")
    print("=" * 50)
    print(f"\n수집: {collected_count}건 → 정제: {cleaned_count}건 → 분석: {len(top_articles)}건\n")
    print(result["text"])


if __name__ == "__main__":
    asyncio.run(main())
