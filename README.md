# Global News Intelligence Pipeline

매일 14개 글로벌 뉴스 소스에서 기사를 수집하고, 로컬 LLM으로 중요도를 평가한 뒤, Claude API로 전략적 브리핑을 생성하여 이메일로 발송하는 자동화 파이프라인입니다.

## 파이프라인 구조

```
[1] 수집 → [2] 정제 → [3] 점수화 → [3.5] 지연 크롤링 → [4] 브리핑 생성 → [5] 이메일 발송
collector    deduplicator   scorer        collector        briefing         sender
```

### 1단계: 수집 (`collector.py`)
- 14개 RSS 피드에서 비동기 수집 (feedparser + aiohttp)
- Google News 인코딩 URL 디코딩 (googlenewsdecoder)
- trafilatura로 본문 크롤링 (병렬 10건, Semaphore 제한)
- 크롤링 실패 시 RSS summary fallback

### 2단계: 정제 (`deduplicator.py`)
- 시간 필터: 한국시간(KST) 매일 오전 8시 기준, 전날~오늘 24시간 구간
- TF-IDF 코사인 유사도 0.85 기준 중복 제거 (제목 + 본문 앞 100자)

### 3단계: 점수화 (`scorer.py`)
- LM Studio에서 구동하는 Qwen3-14b-mlx 로컬 LLM 사용
- 3축 평가: 글로벌 파급력(40%) + 구조적 변화 신호(35%) + 한국 관련성(25%)
- 배치 20건씩 처리, Python에서 가중 합산 계산

### 3.5단계: 지연 크롤링 (`collector.py`)
- NYT 등 무료 한도가 있는 소스는 점수화 후 상위 기사만 크롤링

### 4단계: 브리핑 생성 (`briefing.py`)
- Claude Sonnet API로 구조화된 브리핑 생성
- 영역별 분석: 정치·안보 / 경제·시장 / 기술·지정학 / 한국 관련

### 5단계: 이메일 발송 (`sender.py`)
- Gmail SMTP로 HTML 이메일 발송
- 마크다운 → HTML 변환 (bold, italic, 헤더, 리스트, 링크)
- 발송 실패 시 로컬 파일 저장 fallback

## 뉴스 소스

| 소스 | 역할 | 수집 방식 |
|------|------|-----------|
| AP News | 팩트 | Google News 경유 |
| Reuters | 팩트 | Google News 경유 |
| Yonhap (연합뉴스) | 국내팩트 | 직접 RSS |
| Korea Herald | 국내팩트 | 직접 RSS |
| BBC World | 교차검증 | 직접 RSS |
| Al Jazeera | 교차검증 | Google News 경유 |
| SCMP | 교차검증 | 직접 RSS |
| The Guardian | 교차검증 | 직접 RSS |
| The Diplomat | 지정학 | 직접 RSS |
| NYT World | 오피니언 | 직접 RSS (지연 크롤링) |
| CNN World | 오피니언 | Google News 경유 |
| Bloomberg | 헤드라인감시 | Google News 경유 |
| FT | 헤드라인감시 | Google News 경유 |
| Nikkei Asia | 헤드라인감시 | Google News 경유 |

## 설치 및 실행

### 사전 요구사항
- Python 3.9+
- [LM Studio](https://lmstudio.ai/) — Qwen3-14b-mlx 모델 로드 후 로컬 서버 실행 (localhost:1234)
- Gmail 앱 비밀번호 (2단계 인증 필요)
- Anthropic API 키

### 설치

```bash
git clone <repository-url>
cd News_organizing_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 환경변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```env
ANTHROPIC_API_KEY=sk-ant-...
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@gmail.com
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

### 실행

```bash
# LM Studio에서 Qwen3-14b-mlx 로드 후 서버 시작 필요
source venv/bin/activate
python main.py
```

## 자동화 (macOS launchd)

매일 오전 08:05에 자동 실행되도록 macOS launchd로 스케줄링되어 있습니다.

### 동작 흐름

1. Mac 부팅/로그인 → LM Studio 자동 시작
2. 매일 08:05 → `run_pipeline.sh` 자동 실행
3. LM Studio API 준비 대기 (최대 5분)
4. 파이프라인 실행 → 이메일 발송
5. macOS 알림으로 성공/실패 표시

### Mac이 꺼져 있었다면

launchd가 놓친 실행을 감지하여 Mac을 켜는 즉시 자동 보충 실행합니다.

### 수동 실행

```bash
./run_pipeline.sh
```

### launchd 설정 (최초 1회)

```bash
# LM Studio 로그인 시 자동 시작 등록
launchctl load ~/Library/LaunchAgents/com.lmstudio.autostart.plist

# 파이프라인 매일 08:05 스케줄 등록
launchctl load ~/Library/LaunchAgents/com.news-intelligence.daily.plist

# 등록 확인
launchctl list | grep -E "news-intelligence|lmstudio"

# 스케줄 해제 (필요 시)
launchctl unload ~/Library/LaunchAgents/com.news-intelligence.daily.plist
```

### 로그

실행 로그는 `logs/` 디렉토리에 일별로 저장됩니다 (30일 자동 정리).

```bash
cat logs/$(date +%Y-%m-%d).log
```

## 프로젝트 구조

```
News_organizing_bot/
├── main.py              # 파이프라인 오케스트레이터
├── collector.py         # RSS 수집 + 본문 크롤링
├── deduplicator.py      # 중복 제거 + 시간 필터
├── scorer.py            # LLM 중요도 점수화
├── briefing.py          # Claude API 브리핑 생성
├── sender.py            # 이메일 발송
├── run_pipeline.sh      # 자동 실행 래퍼 스크립트
├── requirements.txt     # 의존성
├── .env                 # 환경변수 (git 제외)
├── prompts/             # LLM 프롬프트 파일 (git 제외)
├── logs/                # 실행 로그 (git 제외)
└── cache/               # 체크포인트 캐시 (git 제외)
```

## 성능

| 항목 | 수치 |
|------|------|
| 수집 | ~280건 / ~8분 |
| 정제 | ~200건 / <1초 |
| 점수화 | 10배치 / ~14분 |
| 브리핑 | ~5,700토큰 / ~2분 |
| 총 소요 | ~24분 |
| API 비용 | ~$0.10/회 (월 ~$3) |

## 기술 스택

- **수집**: feedparser, aiohttp, trafilatura, googlenewsdecoder
- **처리**: scikit-learn (TF-IDF), python-dateutil
- **AI**: Qwen3-14b-mlx (로컬, LM Studio), Claude Sonnet (API)
- **발송**: smtplib (Gmail SMTP)
