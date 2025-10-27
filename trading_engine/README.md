# Trading Engine

Match-Trade Platform용 자동 거래 엔진 (Multi-Account Scalping System)

## 개요

실시간 시장 데이터를 분석하여 거래량 급증 방향으로 스캘핑 거래를 수행하는 자동 거래 시스템

## 기술 스택

- Python 3.11+
- asyncio (비동기 처리)
- pandas, numpy (데이터 분석)
- ta-lib (기술적 지표)
- PostgreSQL (데이터베이스)
- WebSocket (실시간 데이터)

## 프로젝트 구조

```
trading_engine/
├── config/              # 설정 관리
├── data/                # 시장 데이터 수집
├── analysis/            # 데이터 분석 (거래량, 호가)
├── strategy/            # 거래 전략
├── execution/           # 주문 실행
├── utils/               # 유틸리티
├── tests/               # 테스트
├── main.py              # 메인 실행 파일
└── requirements.txt     # 의존성
```

## 설치

### 1. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python3 -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
# 모든 의존성 설치
pip install -r requirements.txt

# 또는 개발 의존성 포함 (권장)
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
# 예제 파일 복사
cp .env.example .env

# .env 파일 편집
vi .env  # 또는 원하는 에디터 사용
```

**필수 환경 변수:**
- `API_BASE_URL`: Match-Trade API URL
- `DB_PASSWORD`: PostgreSQL 비밀번호
- `LOG_LEVEL`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)

## 실행

### 시뮬레이션 모드

```bash
# 기본 실행 (시뮬레이션 모드)
python main.py

# 특정 심볼로 실행
python main.py --symbols BTCUSD,ETHUSD

# 디버그 모드
python main.py --log-level DEBUG
```

### 실제 거래 모드

```bash
# 환경 변수 설정 필요
export TRADING_ENABLED=true
export API_TOKEN=your_token_here
export TRADING_API_TOKEN=your_trading_token_here

python main.py --simulation-mode false
```

## 주요 기능

### 1. Market Data Collector
- Match-Trade API에서 실시간 시장 데이터 수집
- 캔들스틱, 호가창, 거래량 데이터 수집

### 2. Volume Analyzer
- 거래량 급증 감지
- 매수/매도 거래량 비율 분석
- 신호 강도 계산

### 3. Order Book Analyzer
- 호가 불균형 분석
- 대량 주문 감지
- 지지/저항 레벨 계산

### 4. Scalping Strategy
- 통합 분석 기반 매매 신호 생성
- 진입/청산 조건 관리
- 포지션 사이징

### 5. Order Executor
- 주문 실행 및 검증
- 에러 처리 및 재시도

## 테스트

### 테스트 실행

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 테스트 파일 실행
pytest tests/test_market_data.py -v
pytest tests/test_orderbook.py -v
pytest tests/test_websocket.py -v
pytest tests/test_integration.py -v

# 특정 테스트 클래스 실행
pytest tests/test_market_data.py::TestMarketDataCollector -v

# 특정 테스트 함수 실행
pytest tests/test_market_data.py::TestMarketDataCollector::test_get_symbols_with_cache -v

# 마커로 실행
pytest tests/ -m unit -v        # 유닛 테스트만
pytest tests/ -m integration -v  # 통합 테스트만
```

### 테스트 커버리지

```bash
# 커버리지 리포트 생성
pytest tests/ --cov=. --cov-report=html --cov-report=term

# HTML 리포트 확인
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 테스트 스크립트 실행

```bash
# 편의 스크립트 사용
./run_tests.sh
```

### 테스트 작성 가이드

```python
import pytest
from data.market_data import MarketDataCollector

class TestYourFeature:
    @pytest.fixture
    def setup(self):
        # Setup code
        return MarketDataCollector()

    @pytest.mark.asyncio
    async def test_async_function(self, setup):
        # Async test code
        result = await setup.some_async_method()
        assert result is not None

    def test_sync_function(self, setup):
        # Sync test code
        assert setup.some_property is True
```

## 개발 상태

### Phase 1: Trading Engine ✅
- [x] TASK 1.1: 프로젝트 초기 설정
- [x] TASK 1.2: Market Data Collector 구현
- [x] TASK 1.3: Volume Analyzer 구현
- [x] TASK 1.4: OrderBook Analyzer 구현
- [x] TASK 1.5: Scalping Strategy 구현
- [x] TASK 1.6: Order Executor 구현
- [x] TASK 1.7: 통합 테스트 및 최적화
- [x] TASK 1.8: WebSocket 실시간 데이터 구독
- [x] TASK 1.9: 통합 테스트 강화

### Phase 2: Back Office Server (예정)
- [ ] FastAPI 백엔드 서버
- [ ] PostgreSQL 데이터베이스
- [ ] Session Manager
- [ ] Order Orchestrator

## 트러블슈팅

### 일반적인 문제

**1. 모듈을 찾을 수 없음 (ModuleNotFoundError)**
```bash
# 해결: 의존성 재설치
pip install -r requirements.txt

# 또는 파이썬 경로 확인
python -c "import sys; print(sys.path)"
```

**2. pytest 실행 오류**
```bash
# 해결: pytest 재설치
pip install --upgrade pytest pytest-asyncio

# 캐시 정리
pytest --cache-clear
```

**3. WebSocket 연결 실패**
```bash
# 로그 확인
tail -f logs/trading_engine.log

# 네트워크 연결 확인
curl -I https://mtr-demo-prod.match-trader.com
```

**4. 테스트 실패**
```bash
# 상세 로그로 재실행
pytest tests/ -vv --tb=long

# 특정 테스트만 디버그
pytest tests/test_market_data.py::test_name -vv -s
```

### 로그 확인

```bash
# 실시간 로그 모니터링
tail -f logs/trading_engine.log

# 에러만 필터링
grep ERROR logs/trading_engine.log

# JSON 로그 파싱 (jq 설치 필요)
tail -f logs/trading_engine.log | jq .
```

## 성능 최적화

- **비동기 처리**: asyncio를 활용한 동시성 극대화
- **캐싱**: 시장 데이터 캐싱으로 API 호출 최소화 (TTL: 60초)
- **연결 풀링**: HTTP 세션 재사용
- **WebSocket**: 실시간 데이터 스트리밍으로 지연 최소화

## 기여 가이드

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 라이센스

Proprietary

## 지원

문제가 발생하면 Issue를 생성하거나 문서를 참조하세요:
- [프로젝트 기획서](../auto_trading_system_project_plan.md)
- [Match-Trade API 문서](https://mtr-demo-prod.match-trader.com/docs)
