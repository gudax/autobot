# 선물 자동 거래 시스템 프로젝트 기획서
## Claude Code 에이전트 워크플로우 가이드

---

## 📋 프로젝트 개요

**프로젝트명**: Match-Trade 선물 자동 거래 시스템 (Multi-Account Scalping System)

**목적**: 차트, 거래량, 호가를 실시간 분석하여 순간적인 거래량 증가 방향으로 스캘핑하는 자동 거래 시스템. 여러 계정에 동시에 주문을 실행하고 통합 대시보드에서 모니터링.

**기술 스택**:
- Backend: Python (FastAPI)
- Trading Engine: Python (asyncio, pandas, numpy, ta-lib)
- Database: PostgreSQL
- Frontend Dashboard: React + TypeScript + Tailwind CSS
- Real-time Communication: WebSocket
- Containerization: Docker

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND DASHBOARD                       │
│                  (React + TypeScript)                        │
│  - User Management  - Balance Monitor  - Order Status       │
│  - Trade History    - P&L Analytics    - Real-time Charts   │
└────────────────┬────────────────────────────────────────────┘
                 │ WebSocket + REST API
                 │
┌────────────────▼────────────────────────────────────────────┐
│               BACK OFFICE SERVER (FastAPI)                   │
│  - User Session Manager  - Order Orchestrator               │
│  - API Gateway          - Database Manager                  │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
┌────────▼──────┐  ┌────▼──────────────────────────────────┐
│   PostgreSQL  │  │   TRADING ENGINE (Python)             │
│   Database    │  │  - Market Data Analyzer               │
│               │  │  - Volume Spike Detector              │
│               │  │  - Order Book Analyzer                │
└───────────────┘  │  - Signal Generator                   │
                   │  - Risk Manager                       │
                   └────────┬──────────────────────────────┘
                            │
                   ┌────────▼────────────────────────┐
                   │  Match-Trade Platform API       │
                   │  - Login/Auth                   │
                   │  - Market Data                  │
                   │  - Order Execution              │
                   │  - Position Management          │
                   └─────────────────────────────────┘
```

---

## 📦 Phase 1: Trading Engine (스캘핑 봇)

### 1.1 프로젝트 구조
```
trading_engine/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── settings.py          # 설정 관리
│   └── strategy_config.py   # 전략 파라미터
├── data/
│   ├── __init__.py
│   ├── market_data.py       # 시장 데이터 수집
│   ├── orderbook.py         # 호가창 데이터
│   └── websocket_client.py  # WebSocket 실시간 데이터
├── analysis/
│   ├── __init__.py
│   ├── volume_analyzer.py   # 거래량 분석
│   ├── chart_analyzer.py    # 차트 패턴 분석
│   ├── orderbook_analyzer.py # 호가 분석
│   └── indicators.py        # 기술적 지표
├── strategy/
│   ├── __init__.py
│   ├── scalping_strategy.py # 스캘핑 전략 로직
│   ├── signal_generator.py  # 매매 신호 생성
│   └── risk_manager.py      # 리스크 관리
├── execution/
│   ├── __init__.py
│   └── order_executor.py    # 주문 실행 엔진
├── utils/
│   ├── __init__.py
│   ├── logger.py            # 로깅
│   └── helpers.py           # 유틸리티 함수
├── tests/
│   └── test_*.py
├── main.py                   # 메인 실행 파일
└── requirements.txt
```

### 1.2 핵심 컴포넌트 상세 설계

#### A. Market Data Collector (`data/market_data.py`)
```python
"""
클래스: MarketDataCollector
목적: Match-Trade API에서 실시간 시장 데이터 수집

주요 기능:
- get_candles(): 캔들스틱 데이터 수집 (1m, 5m, 15m)
- get_market_watch(): 실시간 시세 정보
- get_symbols(): 거래 가능한 심볼 목록
- subscribe_realtime(): WebSocket으로 실시간 데이터 구독

데이터 구조:
{
    "symbol": "BTCUSD",
    "timestamp": 1234567890,
    "open": 50000,
    "high": 50100,
    "low": 49900,
    "close": 50050,
    "volume": 1234.56,
    "buy_volume": 650.0,
    "sell_volume": 584.56
}
"""
```

#### B. Volume Spike Detector (`analysis/volume_analyzer.py`)
```python
"""
클래스: VolumeAnalyzer
목적: 거래량 급증 감지 및 방향성 판단

핵심 알고리즘:
1. 평균 거래량 계산 (이동평균: 20, 50, 100 기간)
2. 거래량 임계값 설정 (평균의 2배, 3배, 5배)
3. 매수/매도 거래량 비율 분석
4. 거래량 급증 시점 감지
5. 방향성 판단 (Long/Short)

신호 생성 조건:
- 거래량이 평균의 3배 이상
- 매수/매도 비율이 60:40 이상
- 가격이 주요 저항/지지선 돌파
- 연속 3개 캔들 동일 방향

반환 데이터:
{
    "signal": "LONG" | "SHORT" | "NEUTRAL",
    "strength": 0.0 ~ 1.0,  # 신호 강도
    "volume_ratio": 3.5,     # 평균 대비 배수
    "buy_sell_ratio": 0.65,  # 매수 비중
    "timestamp": 1234567890
}
"""
```

#### C. Order Book Analyzer (`analysis/orderbook_analyzer.py`)
```python
"""
클래스: OrderBookAnalyzer
목적: 호가창 분석을 통한 매수/매도 압력 측정

분석 지표:
1. Bid-Ask Spread (호가 스프레드)
2. Order Book Imbalance (호가 불균형)
3. Large Order Detection (대량 주문 감지)
4. Support/Resistance Level (지지/저항선)
5. Liquidity Analysis (유동성 분석)

계산 로직:
- 매수호가 총량 vs 매도호가 총량
- 상위 10호가 내 대량 주문 비중
- 호가 밀집 구간 파악
- 급격한 호가 변화 감지

반환 데이터:
{
    "imbalance_ratio": 0.65,  # 0.5보다 크면 매수 우세
    "spread_bps": 5,           # 스프레드 (basis points)
    "large_bid_detected": true,
    "resistance_level": 50100,
    "support_level": 49900,
    "liquidity_score": 0.8
}
"""
```

#### D. Scalping Strategy (`strategy/scalping_strategy.py`)
```python
"""
클래스: ScalpingStrategy
목적: 통합 분석 결과를 바탕으로 매매 전략 실행

전략 로직:
1. 거래량 급증 감지
2. 호가창 불균형 확인
3. 차트 패턴 검증
4. 진입 조건 충족 시 신호 생성

진입 조건 (AND 조건):
- 거래량이 평균의 3배 이상
- 호가 불균형 비율 > 0.6
- 가격이 5분 이동평균선 돌파
- RSI가 과매수/과매도 구간 아님

청산 조건 (OR 조건):
- 목표 수익률 달성 (0.3% ~ 0.5%)
- 손절가 도달 (-0.2% ~ -0.3%)
- 반대 방향 신호 발생
- 최대 보유 시간 초과 (1분 ~ 5분)

포지션 사이징:
- 계좌 잔액의 1% ~ 5% 위험
- 레버리지 고려한 증거금 계산
- 동시 최대 포지션 수 제한

반환 데이터:
{
    "action": "OPEN_LONG" | "OPEN_SHORT" | "CLOSE" | "HOLD",
    "symbol": "BTCUSD",
    "entry_price": 50000,
    "quantity": 0.1,
    "stop_loss": 49900,
    "take_profit": 50150,
    "confidence": 0.85,
    "reason": "Volume spike + OB imbalance + Breakout"
}
"""
```

### 1.3 Claude Code 에이전트 지시사항 (Phase 1)

```
TASK 1.1: Trading Engine 프로젝트 초기 설정
- Python 3.11+ 가상환경 생성
- requirements.txt 작성 (asyncio, aiohttp, pandas, numpy, ta-lib, websockets, pydantic)
- 프로젝트 폴더 구조 생성
- 기본 설정 파일 작성 (config/settings.py)

TASK 1.2: Market Data Collector 구현
- Match-Trade API 연동 클래스 작성
- GET /market-watch 엔드포인트 연동
- GET /candles 엔드포인트 연동
- GET /symbols 엔드포인트 연동
- 실시간 데이터 캐싱 메커니즘 구현
- 단위 테스트 작성

TASK 1.3: Volume Analyzer 구현
- 거래량 데이터 수집 및 저장
- 이동평균 계산 함수
- 거래량 급증 감지 알고리즘
- 매수/매도 거래량 분리 및 비율 계산
- 신호 강도 계산 로직
- 백테스팅을 위한 히스토리 데이터 저장

TASK 1.4: OrderBook Analyzer 구현
- 호가창 데이터 파싱
- 호가 불균형 계산
- 대량 주문 감지 로직
- 지지/저항 레벨 계산
- 유동성 점수 산출

TASK 1.5: Scalping Strategy 구현
- 모든 분석 모듈 통합
- 진입/청산 조건 로직
- 포지션 사이징 계산
- 리스크 관리 로직
- 시뮬레이션 모드 구현

TASK 1.6: Order Executor 구현
- 주문 실행 인터페이스
- 주문 검증 로직
- 재시도 메커니즘
- 주문 상태 추적
- 에러 핸들링

TASK 1.7: 통합 테스트 및 최적화
- 전체 시스템 통합 테스트
- 성능 최적화 (비동기 처리)
- 로깅 시스템 구축
- 백테스팅 프레임워크 구현
```

---

## 📦 Phase 2: Back Office Server (다중 계정 관리)

### 2.1 프로젝트 구조
```
back_office_server/
├── __init__.py
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # 유저 모델
│   │   ├── order.py         # 주문 모델
│   │   ├── position.py      # 포지션 모델
│   │   └── trade_history.py # 거래 내역
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── order.py
│   │   └── response.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # 인증 API
│   │   ├── users.py         # 유저 관리 API
│   │   ├── trading.py       # 거래 API
│   │   ├── dashboard.py     # 대시보드 API
│   │   └── websocket.py     # WebSocket 엔드포인트
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py          # 인증 서비스
│   │   ├── user_manager.py          # 유저 관리
│   │   ├── session_manager.py       # 세션 관리
│   │   ├── order_orchestrator.py    # 주문 오케스트레이션
│   │   ├── mt_api_client.py         # Match-Trade API 클라이언트
│   │   └── trading_engine_client.py # Trading Engine 연동
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── encryption.py    # 비밀번호 암호화
│   │   └── validators.py
│   └── db/
│       ├── __init__.py
│       ├── base.py
│       └── migrations/
├── tests/
│   └── test_*.py
├── alembic/                  # DB 마이그레이션
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### 2.2 핵심 컴포넌트 상세 설계

#### A. Database Schema
```sql
-- users 테이블: 유저 로그인 정보
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    encrypted_password TEXT NOT NULL,
    broker_id VARCHAR(100) NOT NULL,
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- user_sessions 테이블: 로그인 세션
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token TEXT NOT NULL,
    trading_api_token TEXT NOT NULL,
    trading_account_id VARCHAR(100),
    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    last_refresh_at TIMESTAMP
);

-- accounts 테이블: 계정 정보
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    trading_account_uuid VARCHAR(100) UNIQUE,
    balance DECIMAL(18, 8),
    equity DECIMAL(18, 8),
    margin DECIMAL(18, 8),
    free_margin DECIMAL(18, 8),
    leverage INTEGER,
    currency VARCHAR(10),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- orders 테이블: 주문 내역
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    account_id INTEGER REFERENCES accounts(id),
    order_uuid VARCHAR(100) UNIQUE,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL, -- LONG/SHORT
    order_type VARCHAR(20), -- MARKET/LIMIT
    quantity DECIMAL(18, 8),
    entry_price DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    take_profit DECIMAL(18, 8),
    status VARCHAR(20), -- PENDING/OPEN/CLOSED/CANCELLED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- trades 테이블: 체결된 거래
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(50),
    side VARCHAR(10),
    entry_price DECIMAL(18, 8),
    exit_price DECIMAL(18, 8),
    quantity DECIMAL(18, 8),
    profit_loss DECIMAL(18, 8),
    profit_loss_percent DECIMAL(10, 4),
    commission DECIMAL(18, 8),
    duration_seconds INTEGER,
    executed_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- trading_signals 테이블: 트레이딩 신호 로그
CREATE TABLE trading_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50),
    signal_type VARCHAR(10), -- LONG/SHORT/CLOSE
    strength DECIMAL(5, 4),
    volume_ratio DECIMAL(10, 4),
    orderbook_imbalance DECIMAL(5, 4),
    price DECIMAL(18, 8),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- system_logs 테이블: 시스템 로그
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(20),
    component VARCHAR(100),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_executed_at ON trades(executed_at);
CREATE INDEX idx_signals_created_at ON trading_signals(created_at);
```

#### B. Session Manager (`services/session_manager.py`)
```python
"""
클래스: SessionManager
목적: 다중 유저 세션 동시 관리

주요 기능:
1. 다중 유저 동시 로그인
   - 병렬 로그인 처리 (asyncio.gather)
   - 로그인 실패 재시도 로직
   - 세션 정보 DB 저장

2. 세션 유지 및 갱신
   - 15분마다 자동 토큰 갱신
   - 갱신 실패 시 재로그인
   - 세션 상태 모니터링

3. 세션 풀 관리
   - 활성 세션 목록 관리
   - 세션 헬스체크
   - 비활성 세션 정리

메서드:
- async login_all_users(): 모든 유저 동시 로그인
- async login_user(user_id): 특정 유저 로그인
- async refresh_token(session_id): 토큰 갱신
- async check_session_health(): 세션 상태 확인
- async logout_user(user_id): 유저 로그아웃
- get_active_sessions(): 활성 세션 목록 조회

반환 데이터:
{
    "user_id": 1,
    "email": "user@example.com",
    "session_id": "abc123",
    "is_active": true,
    "token": "eyJ...",
    "trading_api_token": "Bearer xyz...",
    "trading_account_id": "acc_123",
    "login_at": "2025-01-01T00:00:00Z",
    "expires_at": "2025-01-01T00:15:00Z"
}
"""
```

#### C. Order Orchestrator (`services/order_orchestrator.py`)
```python
"""
클래스: OrderOrchestrator
목적: 모든 활성 유저에게 동시에 주문 실행

핵심 기능:
1. 신호 수신 및 검증
   - Trading Engine으로부터 신호 수신
   - 신호 유효성 검증
   - 리스크 체크

2. 동시 주문 실행
   - 모든 활성 세션 조회
   - 병렬 주문 실행 (asyncio.gather)
   - 주문 결과 수집 및 검증

3. 주문 상태 관리
   - 주문 상태 DB 저장
   - 실패한 주문 재시도
   - 주문 체결 확인

4. 포지션 동기화
   - 주문 체결 후 포지션 업데이트
   - 잔고 정보 갱신
   - 실시간 대시보드 업데이트

주요 메서드:
- async execute_signal_for_all(signal: TradingSignal):
    모든 유저에게 동일 신호로 주문 실행
    
- async execute_order_batch(orders: List[OrderRequest]):
    여러 주문을 동시에 실행
    
- async monitor_open_positions():
    열린 포지션 모니터링 및 청산 조건 체크
    
- async close_all_positions(symbol: str):
    특정 심볼의 모든 포지션 청산

실행 프로세스:
1. Trading Engine에서 신호 수신
   {"signal": "LONG", "symbol": "BTCUSD", "entry": 50000, ...}

2. 활성 세션 조회 (10명의 유저가 로그인 중)
   
3. 각 유저별 주문 생성
   - 계정 잔고 확인
   - 포지션 사이즈 계산
   - 주문 파라미터 생성

4. 동시 주문 실행 (asyncio.gather)
   ```python
   tasks = [
       execute_order_for_user(user1, order_params),
       execute_order_for_user(user2, order_params),
       ...
       execute_order_for_user(user10, order_params)
   ]
   results = await asyncio.gather(*tasks, return_exceptions=True)
   ```

5. 결과 처리
   - 성공: DB에 주문 기록, 대시보드 업데이트
   - 실패: 에러 로깅, 알림 발송, 재시도 큐에 추가

6. 포지션 모니터링 시작
   - 목표가/손절가 도달 확인
   - 반대 신호 발생 시 청산
   - 최대 보유 시간 체크

반환 데이터:
{
    "signal_id": "sig_123",
    "symbol": "BTCUSD",
    "executed_count": 10,
    "failed_count": 0,
    "total_volume": 1.5,
    "execution_time_ms": 234,
    "results": [
        {
            "user_id": 1,
            "order_id": "ord_123",
            "status": "SUCCESS",
            "executed_price": 50000.5
        },
        ...
    ]
}
"""
```

#### D. Match-Trade API Client (`services/mt_api_client.py`)
```python
"""
클래스: MatchTradeAPIClient
목적: Match-Trade Platform API와의 모든 통신 처리

API 문서 참조: /mnt/user-data/outputs/match_trade_api_complete_documentation.json

주요 메서드:

# 인증
- async login(email, password, broker_id) -> SessionData
- async refresh_token(token) -> SessionData
- async logout(token) -> bool

# 계정 정보
- async get_balance(token, trading_api_token) -> BalanceInfo
- async get_platform_details(token) -> PlatformDetails

# 시장 데이터
- async get_market_watch(token, trading_api_token) -> MarketData
- async get_symbols(token, trading_api_token) -> List[Symbol]
- async get_candles(token, trading_api_token, symbol, timeframe) -> List[Candle]

# 포지션 관리
- async get_opened_positions(token, trading_api_token) -> List[Position]
- async open_position(token, trading_api_token, order_params) -> Position
- async edit_position(token, trading_api_token, position_id, params) -> Position
- async close_position(token, trading_api_token, position_id) -> CloseResult
- async partial_close(token, trading_api_token, position_id, volume) -> Position
- async get_closed_positions(token, trading_api_token, filters) -> List[Position]

# 주문 관리
- async get_active_orders(token, trading_api_token) -> List[Order]
- async create_pending_order(token, trading_api_token, order_params) -> Order
- async edit_pending_order(token, trading_api_token, order_id, params) -> Order
- async cancel_pending_order(token, trading_api_token, order_id) -> bool

에러 처리:
- 401 Unauthorized: 자동 토큰 갱신 후 재시도
- 400 Bad Request: 요청 검증 및 에러 반환
- 410 Gone: 리소스 만료 처리
- Network Error: 지수 백오프 재시도 (최대 3회)
- Rate Limit: 요청 대기 후 재시도

반환 예시:
{
    "success": true,
    "data": {
        "position_id": "pos_123",
        "symbol": "BTCUSD",
        "side": "LONG",
        "volume": 0.1,
        "entry_price": 50000,
        "current_price": 50150,
        "profit_loss": 15.0,
        "profit_loss_percent": 0.3
    },
    "error": null
}
"""
```

### 2.3 API 엔드포인트 설계

```yaml
# 유저 관리 API
POST   /api/v1/users                    # 유저 생성
GET    /api/v1/users                    # 유저 목록 조회
GET    /api/v1/users/{user_id}          # 유저 상세 조회
PUT    /api/v1/users/{user_id}          # 유저 정보 수정
DELETE /api/v1/users/{user_id}          # 유저 삭제
POST   /api/v1/users/{user_id}/login    # 유저 로그인 실행
POST   /api/v1/users/{user_id}/logout   # 유저 로그아웃
POST   /api/v1/users/login-all          # 모든 유저 동시 로그인

# 세션 관리 API
GET    /api/v1/sessions                 # 활성 세션 목록
GET    /api/v1/sessions/{session_id}    # 세션 상세 정보
POST   /api/v1/sessions/refresh-all     # 모든 세션 토큰 갱신
DELETE /api/v1/sessions/{session_id}    # 세션 종료

# 계정 정보 API
GET    /api/v1/accounts                 # 모든 계정 정보
GET    /api/v1/accounts/{account_id}    # 특정 계정 상세
POST   /api/v1/accounts/sync            # 계정 정보 동기화

# 거래 API
POST   /api/v1/trading/signal           # 트레이딩 신호 전송
POST   /api/v1/trading/execute-all      # 모든 유저 동시 주문
GET    /api/v1/trading/positions        # 모든 포지션 조회
POST   /api/v1/trading/close-all        # 모든 포지션 청산
GET    /api/v1/trading/orders           # 주문 내역 조회

# 대시보드 API
GET    /api/v1/dashboard/overview       # 대시보드 요약 정보
GET    /api/v1/dashboard/users          # 유저별 현황
GET    /api/v1/dashboard/performance    # 성과 분석
GET    /api/v1/dashboard/trades         # 거래 내역

# WebSocket
WS     /ws/dashboard                    # 실시간 대시보드 업데이트
WS     /ws/trading                      # 실시간 거래 신호
WS     /ws/positions                    # 실시간 포지션 업데이트
```

### 2.4 Claude Code 에이전트 지시사항 (Phase 2)

```
TASK 2.1: 프로젝트 초기 설정
- FastAPI 프로젝트 생성
- PostgreSQL Docker 컨테이너 설정
- Alembic 마이그레이션 초기화
- requirements.txt 작성 (fastapi, sqlalchemy, asyncpg, pydantic, etc.)

TASK 2.2: 데이터베이스 설계 및 모델 생성
- SQLAlchemy 모델 작성 (users, sessions, accounts, orders, trades)
- Alembic 마이그레이션 파일 생성
- 데이터베이스 초기화 스크립트

TASK 2.3: Match-Trade API Client 구현
- API 문서 기반 클라이언트 클래스 작성
- 모든 엔드포인트 메서드 구현
- 에러 처리 및 재시도 로직
- 단위 테스트 작성

TASK 2.4: Session Manager 구현
- 다중 유저 로그인 로직
- 세션 풀 관리
- 자동 토큰 갱신 (백그라운드 태스크)
- 세션 헬스체크

TASK 2.5: Order Orchestrator 구현
- 신호 수신 및 검증
- 병렬 주문 실행 로직
- 주문 상태 관리
- 포지션 모니터링

TASK 2.6: REST API 엔드포인트 구현
- 유저 관리 API
- 세션 관리 API
- 계정 정보 API
- 거래 API
- 대시보드 API

TASK 2.7: WebSocket 구현
- 실시간 데이터 브로드캐스트
- 클라이언트 연결 관리
- 이벤트 기반 업데이트

TASK 2.8: 백그라운드 태스크
- 세션 자동 갱신 스케줄러
- 포지션 모니터링 워커
- 계정 정보 동기화 태스크

TASK 2.9: 통합 및 테스트
- Trading Engine 연동 테스트
- Match-Trade API 통합 테스트
- 부하 테스트 (다중 유저 동시 처리)
- 에러 시나리오 테스트
```

---

## 📦 Phase 3: Frontend Dashboard

### 3.1 프로젝트 구조
```
dashboard/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── users/
│   │   │   ├── UserList.tsx
│   │   │   ├── UserCard.tsx
│   │   │   ├── UserForm.tsx
│   │   │   └── LoginStatus.tsx
│   │   ├── accounts/
│   │   │   ├── BalanceCard.tsx
│   │   │   ├── AccountSummary.tsx
│   │   │   └── AccountDetails.tsx
│   │   ├── trading/
│   │   │   ├── OrderTable.tsx
│   │   │   ├── PositionTable.tsx
│   │   │   ├── TradeHistory.tsx
│   │   │   └── SignalPanel.tsx
│   │   ├── dashboard/
│   │   │   ├── Overview.tsx
│   │   │   ├── PerformanceChart.tsx
│   │   │   ├── ProfitLossChart.tsx
│   │   │   └── StatsCard.tsx
│   │   └── common/
│   │       ├── Table.tsx
│   │       ├── Button.tsx
│   │       ├── Modal.tsx
│   │       └── LoadingSpinner.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx           # 메인 대시보드
│   │   ├── Users.tsx               # 유저 관리
│   │   ├── Trading.tsx             # 거래 현황
│   │   ├── History.tsx             # 거래 내역
│   │   ├── Analytics.tsx           # 성과 분석
│   │   └── Settings.tsx            # 설정
│   ├── hooks/
│   │   ├── useWebSocket.ts         # WebSocket 훅
│   │   ├── useAPI.ts               # API 호출 훅
│   │   └── useAuth.ts              # 인증 훅
│   ├── services/
│   │   ├── api.ts                  # API 클라이언트
│   │   └── websocket.ts            # WebSocket 클라이언트
│   ├── types/
│   │   ├── user.ts
│   │   ├── order.ts
│   │   ├── position.ts
│   │   └── dashboard.ts
│   ├── utils/
│   │   ├── formatter.ts            # 데이터 포맷팅
│   │   └── constants.ts            # 상수 정의
│   ├── App.tsx
│   ├── index.tsx
│   └── index.css
├── package.json
├── tsconfig.json
└── tailwind.config.js
```

### 3.2 화면 설계

#### A. 메인 대시보드 (`/`)
```
┌─────────────────────────────────────────────────────────────┐
│  Header: 선물 자동 거래 시스템                  [Admin ▼]    │
├─────────────────────────────────────────────────────────────┤
│ Sidebar  │                                                   │
│          │  📊 Overview (실시간 업데이트)                     │
│ 대시보드   │  ┌──────────┬──────────┬──────────┬──────────┐  │
│ 유저관리   │  │ 총 유저  │ 활성세션 │ 총 잔고  │  총 수익 │  │
│ 거래현황   │  │   15명   │  12명   │ $45,230  │ +$2,345  │  │
│ 거래내역   │  └──────────┴──────────┴──────────┴──────────┘  │
│ 성과분석   │                                                   │
│ 설정      │  📈 Performance Chart (24시간)                    │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │  [수익률 라인 차트]                         │ │
│          │  │                                             │ │
│          │  └─────────────────────────────────────────────┘ │
│          │                                                   │
│          │  🔄 Active Positions (실시간)                     │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │ User  │ Symbol │ Side │ Size │ P&L │ ROI   │ │
│          │  ├─────────────────────────────────────────────┤ │
│          │  │ user1 │ BTCUSD │ LONG │ 0.1  │+$15 │ +0.3% │ │
│          │  │ user2 │ BTCUSD │ LONG │ 0.1  │+$12 │ +0.24%│ │
│          │  │ ...   │        │      │      │     │       │ │
│          │  └─────────────────────────────────────────────┘ │
│          │                                                   │
│          │  📋 Recent Trades                                 │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │ Time  │ User  │ Symbol │ P&L │ Duration    │ │
│          │  ├─────────────────────────────────────────────┤ │
│          │  │ 14:32 │ user1 │ BTCUSD │+$8  │ 2m 15s      │ │
│          │  │ 14:30 │ user2 │ ETHUSD │+$5  │ 1m 45s      │ │
│          │  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

특징:
- 실시간 데이터 업데이트 (WebSocket)
- 색상 코딩 (수익: 녹색, 손실: 빨강)
- 자동 새로고침
- 애니메이션 효과
```

#### B. 유저 관리 페이지 (`/users`)
```
┌─────────────────────────────────────────────────────────────┐
│  👥 User Management                      [+ Add User]        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔍 Search: [________]  Filter: [All ▼]  [Refresh] [Login All]│
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ User │ Email           │ Status  │ Balance │ Actions  │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 🟢   │ user1@email.com │ Active  │ $5,234  │ [Edit]   │  │
│  │      │                 │ Logged  │         │ [Logout] │  │
│  │      │                 │         │         │ [Delete] │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 🔴   │ user2@email.com │ Offline │ $3,156  │ [Edit]   │  │
│  │      │                 │         │         │ [Login]  │  │
│  │      │                 │         │         │ [Delete] │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 🟢   │ user3@email.com │ Active  │ $4,891  │ [Edit]   │  │
│  │      │                 │ Logged  │         │ [Logout] │  │
│  │      │                 │         │         │ [Delete] │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Bulk Actions: [Select All] [Login Selected] [Logout Selected]│
└─────────────────────────────────────────────────────────────┘

기능:
- 유저 추가/수정/삭제
- 개별 로그인/로그아웃
- 전체 유저 동시 로그인
- 로그인 상태 실시간 표시
- 잔고 실시간 업데이트
```

#### C. 거래 현황 페이지 (`/trading`)
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Trading Overview                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🎯 Latest Signal                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ LONG BTCUSD @ 50,000                                │    │
│  │ Strength: ████████░░ 85%                            │    │
│  │ Reason: Volume spike + OB imbalance                 │    │
│  │ Time: 2 seconds ago                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  📈 Open Positions (12 active)                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ User    │Symbol │Side │Entry  │Current│ P&L  │ROI  │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ user1   │BTCUSD │LONG │50,000 │50,150 │+$15  │+0.3%│    │
│  │ user2   │BTCUSD │LONG │50,001 │50,150 │+$14.9│+0.3%│    │
│  │ user3   │BTCUSD │LONG │50,002 │50,150 │+$14.8│+0.3%│    │
│  │ ...     │       │     │       │       │      │     │    │
│  └─────────────────────────────────────────────────────┘    │
│  [Close All Positions]                                        │
│                                                               │
│  📝 Active Orders (0)                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ No active pending orders                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

기능:
- 실시간 신호 표시
- 포지션 실시간 업데이트
- 일괄 청산 기능
- P&L 색상 표시
- 포지션 상세 보기 (클릭)
```

#### D. 거래 내역 페이지 (`/history`)
```
┌─────────────────────────────────────────────────────────────┐
│  📋 Trade History                                             │
├─────────────────────────────────────────────────────────────┤
│  Filter: [Today ▼] [All Users ▼] [All Symbols ▼]  [Export CSV]│
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │Time  │User  │Symbol │Side │Entry │Exit  │P&L │Duration│  │
│  ├─────────────────────────────────────────────────────┤    │
│  │14:32 │user1 │BTCUSD │LONG │50000 │50080 │+$8 │2m 15s │  │
│  │14:30 │user2 │ETHUSD │LONG │3000  │3015  │+$5 │1m 45s │  │
│  │14:28 │user3 │BTCUSD │SHORT│50100 │50050 │+$5 │3m 12s │  │
│  │14:25 │user1 │BTCUSD │LONG │49950 │49940 │-$1 │0m 58s │  │
│  │...   │      │       │     │      │      │    │       │  │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  📊 Statistics                                                │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ Win Rate │ Avg P&L  │ Best     │ Worst    │             │
│  │   75%    │  +$6.2   │  +$45    │  -$12    │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
└─────────────────────────────────────────────────────────────┘

기능:
- 필터링 (날짜, 유저, 심볼)
- CSV 내보내기
- 거래 통계
- 페이지네이션
- 상세 보기 (클릭)
```

#### E. 성과 분석 페이지 (`/analytics`)
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Performance Analytics                                     │
├─────────────────────────────────────────────────────────────┤
│  Period: [Last 7 Days ▼]                                     │
│                                                               │
│  💰 Overall Performance                                       │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ Total P&L│ Win Rate │ Trades   │ Avg Hold │             │
│  │ +$2,345  │   72%    │   156    │  2m 34s  │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
│                                                               │
│  📈 P&L Chart (Cumulative)                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  $3000 ┤                              ╱              │    │
│  │  $2000 ┤                         ╱                   │    │
│  │  $1000 ┤                    ╱                        │    │
│  │      0 ┤━━━━━━━━━━━━━━━━━━                          │    │
│  │        └──────────────────────────────────────>      │    │
│  │         Mon  Tue  Wed  Thu  Fri  Sat  Sun           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  👥 User Performance Ranking                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Rank │ User    │ P&L    │ Win Rate │ Trades         │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  1   │ user5   │ +$345  │   85%    │  42            │    │
│  │  2   │ user2   │ +$298  │   78%    │  38            │    │
│  │  3   │ user1   │ +$267  │   75%    │  45            │    │
│  │  ... │         │        │          │                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  📊 Symbol Performance                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Symbol  │ Trades │ Win Rate │ Avg P&L │ Total P&L  │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ BTCUSD  │  89    │   74%    │  +$6.8  │  +$605     │    │
│  │ ETHUSD  │  45    │   68%    │  +$4.2  │  +$189     │    │
│  │ XAUUSD  │  22    │   77%    │  +$7.5  │  +$165     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

기능:
- 기간별 성과 분석
- 누적 수익 차트
- 유저별 순위
- 심볼별 성과
- 통계 대시보드
```

### 3.3 핵심 기능 구현

#### A. WebSocket 실시간 업데이트
```typescript
// hooks/useWebSocket.ts
export const useWebSocket = (url: string) => {
  const [data, setData] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setData(message);
      
      // 메시지 타입별 처리
      switch (message.type) {
        case 'position_update':
          // 포지션 업데이트
          break;
        case 'balance_update':
          // 잔고 업데이트
          break;
        case 'trade_signal':
          // 거래 신호
          break;
        case 'order_executed':
          // 주문 체결
          break;
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      // 재연결 로직
      setTimeout(() => {
        // reconnect
      }, 3000);
    };
    
    return () => {
      ws.close();
    };
  }, [url]);
  
  return { data, isConnected };
};
```

#### B. 실시간 데이터 업데이트 컴포넌트
```typescript
// components/dashboard/Overview.tsx
export const Overview: React.FC = () => {
  const { data: wsData } = useWebSocket('ws://localhost:8000/ws/dashboard');
  const [stats, setStats] = useState<DashboardStats>(initialStats);
  
  useEffect(() => {
    if (wsData) {
      // 실시간 데이터로 상태 업데이트
      setStats(prev => ({
        ...prev,
        ...wsData
      }));
    }
  }, [wsData]);
  
  return (
    <div className="grid grid-cols-4 gap-4">
      <StatsCard 
        title="총 유저"
        value={stats.totalUsers}
        icon={<UsersIcon />}
      />
      <StatsCard 
        title="활성 세션"
        value={stats.activeSessions}
        icon={<CheckCircleIcon />}
        trend={stats.sessionTrend}
      />
      <StatsCard 
        title="총 잔고"
        value={formatCurrency(stats.totalBalance)}
        icon={<WalletIcon />}
      />
      <StatsCard 
        title="총 수익"
        value={formatCurrency(stats.totalProfit)}
        icon={<TrendingUpIcon />}
        valueColor={stats.totalProfit >= 0 ? 'green' : 'red'}
      />
    </div>
  );
};
```

#### C. 포지션 테이블 컴포넌트
```typescript
// components/trading/PositionTable.tsx
export const PositionTable: React.FC = () => {
  const { data: positions } = useWebSocket('ws://localhost:8000/ws/positions');
  const [sortedPositions, setSortedPositions] = useState<Position[]>([]);
  
  const handleCloseAll = async () => {
    const confirmed = await confirm('모든 포지션을 청산하시겠습니까?');
    if (confirmed) {
      await api.post('/api/v1/trading/close-all');
    }
  };
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">
          Open Positions ({positions?.length || 0})
        </h2>
        <button 
          onClick={handleCloseAll}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          Close All
        </button>
      </div>
      
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th>User</th>
            <th>Symbol</th>
            <th>Side</th>
            <th>Entry</th>
            <th>Current</th>
            <th>P&L</th>
            <th>ROI</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {positions?.map((pos) => (
            <tr key={pos.id} className="border-b hover:bg-gray-50">
              <td>{pos.user.email}</td>
              <td>{pos.symbol}</td>
              <td>
                <Badge color={pos.side === 'LONG' ? 'green' : 'red'}>
                  {pos.side}
                </Badge>
              </td>
              <td>{formatPrice(pos.entryPrice)}</td>
              <td>{formatPrice(pos.currentPrice)}</td>
              <td className={pos.profitLoss >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatCurrency(pos.profitLoss)}
              </td>
              <td className={pos.roi >= 0 ? 'text-green-600' : 'text-red-600'}>
                {formatPercent(pos.roi)}
              </td>
              <td>{formatDuration(pos.duration)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### 3.4 Claude Code 에이전트 지시사항 (Phase 3)

```
TASK 3.1: 프로젝트 초기 설정
- Create React App with TypeScript
- Tailwind CSS 설정
- React Router 설정
- 프로젝트 구조 생성

TASK 3.2: 공통 컴포넌트 구현
- Layout (Header, Sidebar)
- Table, Button, Modal, Card 등
- LoadingSpinner, ErrorBoundary
- TypeScript 타입 정의

TASK 3.3: API 클라이언트 구현
- Axios 기반 API 클라이언트
- 에러 처리 인터셉터
- 인증 토큰 관리
- TypeScript 타입 정의

TASK 3.4: WebSocket 클라이언트 구현
- WebSocket 훅 (useWebSocket)
- 재연결 로직
- 메시지 타입별 핸들러
- 연결 상태 관리

TASK 3.5: 메인 대시보드 페이지 구현
- Overview 컴포넌트
- PerformanceChart 컴포넌트
- PositionTable 컴포넌트
- RecentTrades 컴포넌트
- 실시간 데이터 업데이트

TASK 3.6: 유저 관리 페이지 구현
- UserList 컴포넌트
- UserForm (추가/수정)
- 로그인 상태 관리
- 일괄 작업 기능

TASK 3.7: 거래 현황 페이지 구현
- SignalPanel 컴포넌트
- PositionTable 컴포넌트
- OrderTable 컴포넌트
- 실시간 업데이트

TASK 3.8: 거래 내역 페이지 구현
- TradeHistory 컴포넌트
- 필터링 기능
- 통계 표시
- CSV 내보내기

TASK 3.9: 성과 분석 페이지 구현
- PerformanceChart 컴포넌트
- UserRanking 컴포넌트
- SymbolPerformance 컴포넌트
- Chart.js 또는 Recharts 사용

TASK 3.10: 반응형 디자인 및 최적화
- 모바일 반응형
- 성능 최적화 (React.memo, useMemo)
- 코드 스플리팅
- 접근성 개선
```

---

## 🔗 Phase 4: 시스템 통합 및 배포

### 4.1 Docker 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 데이터베이스
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading_system
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Trading Engine
  trading-engine:
    build: ./trading_engine
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=trading_system
      - DB_USER=admin
      - DB_PASSWORD=${DB_PASSWORD}
      - API_BASE_URL=https://mtr-demo-prod.match-trader.com
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./trading_engine:/app
    restart: unless-stopped

  # Back Office Server
  back-office:
    build: ./back_office_server
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=trading_system
      - DB_USER=admin
      - DB_PASSWORD=${DB_PASSWORD}
      - TRADING_ENGINE_URL=http://trading-engine:8001
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - trading-engine
    volumes:
      - ./back_office_server:/app
    restart: unless-stopped

  # Frontend Dashboard
  dashboard:
    build: ./dashboard
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - back-office
    volumes:
      - ./dashboard:/app
      - /app/node_modules
    restart: unless-stopped

  # Redis (캐싱 및 세션)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 4.2 환경 변수 설정

```bash
# .env.example
# Database
DB_PASSWORD=your_secure_password_here
DB_NAME=trading_system
DB_USER=admin

# API Keys
MATCH_TRADE_BROKER_ID=your_broker_id

# Trading Engine
TRADING_ENABLED=true
MAX_POSITION_SIZE=0.1
RISK_PER_TRADE=0.01

# Back Office
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### 4.3 Claude Code 에이전트 지시사항 (Phase 4)

```
TASK 4.1: Docker 설정
- Dockerfile 작성 (각 서비스별)
- docker-compose.yml 작성
- 환경 변수 설정
- 볼륨 및 네트워크 구성

TASK 4.2: 통합 테스트
- Trading Engine ↔ Back Office 통합
- Back Office ↔ Dashboard 통합
- Match-Trade API 연동 테스트
- 엔드투엔드 테스트

TASK 4.3: 모니터링 및 로깅
- 중앙화된 로깅 시스템
- 에러 추적 (Sentry 또는 자체 구현)
- 성능 모니터링
- 알림 시스템

TASK 4.4: 보안 강화
- API 인증/인가
- 비밀번호 암호화
- SQL 인젝션 방지
- CORS 설정
- Rate Limiting

TASK 4.5: 문서화
- README.md 작성
- API 문서 (Swagger/OpenAPI)
- 사용자 가이드
- 배포 가이드

TASK 4.6: 배포 준비
- 프로덕션 환경 설정
- CI/CD 파이프라인 (선택사항)
- 백업 전략
- 롤백 계획
```

---

## 📊 시스템 워크플로우

### 전체 프로세스 흐름

```
1. 시스템 시작
   ├─ Back Office Server 시작
   ├─ Trading Engine 시작
   ├─ Dashboard 시작
   └─ 데이터베이스 연결 확인

2. 유저 로그인 프로세스
   ├─ Dashboard에서 "Login All" 클릭
   ├─ Back Office: SessionManager.login_all_users() 호출
   ├─ 각 유저별로 병렬 로그인 실행
   │   ├─ Match-Trade API /manager/mtr-login 호출
   │   ├─ 토큰 수신 및 DB 저장
   │   └─ 세션 풀에 추가
   ├─ 모든 로그인 완료 후 결과 반환
   └─ Dashboard 업데이트 (WebSocket)

3. 거래 신호 생성 및 실행
   ├─ Trading Engine: 실시간 시장 데이터 수집
   │   ├─ Match-Trade API /market-watch 호출
   │   ├─ Match-Trade API /candles 호출
   │   └─ 호가창 데이터 수집
   │
   ├─ 분석 수행
   │   ├─ VolumeAnalyzer: 거래량 급증 감지
   │   ├─ OrderBookAnalyzer: 호가 불균형 분석
   │   └─ ScalpingStrategy: 진입 조건 검증
   │
   ├─ 신호 생성 (조건 충족 시)
   │   └─ signal = {
   │         "action": "OPEN_LONG",
   │         "symbol": "BTCUSD",
   │         "entry_price": 50000,
   │         "stop_loss": 49900,
   │         "take_profit": 50150
   │       }
   │
   ├─ Back Office로 신호 전송
   │   └─ POST /api/v1/trading/signal
   │
   ├─ OrderOrchestrator: 동시 주문 실행
   │   ├─ 활성 세션 조회 (12명)
   │   ├─ 각 유저별 주문 생성
   │   │   ├─ 계좌 잔고 확인
   │   │   ├─ 포지션 사이즈 계산
   │   │   └─ 주문 파라미터 생성
   │   │
   │   ├─ 병렬 주문 실행 (asyncio.gather)
   │   │   ├─ User1: Match-Trade API /positions/open
   │   │   ├─ User2: Match-Trade API /positions/open
   │   │   ├─ ...
   │   │   └─ User12: Match-Trade API /positions/open
   │   │
   │   └─ 결과 수집 및 DB 저장
   │
   └─ Dashboard 실시간 업데이트 (WebSocket)
       ├─ 신호 패널 업데이트
       ├─ 포지션 테이블 업데이트
       └─ 잔고 정보 업데이트

4. 포지션 모니터링 및 청산
   ├─ OrderOrchestrator: 백그라운드 모니터링
   │   ├─ 모든 열린 포지션 주기적 체크 (1초마다)
   │   ├─ 각 포지션별 조건 확인
   │   │   ├─ 목표가 도달?
   │   │   ├─ 손절가 도달?
   │   │   ├─ 반대 신호 발생?
   │   │   └─ 최대 보유 시간 초과?
   │   │
   │   └─ 청산 조건 충족 시
   │       ├─ 해당 유저의 포지션 청산
   │       ├─ Match-Trade API /positions/close
   │       ├─ 거래 내역 DB 저장
   │       └─ Dashboard 업데이트
   │
   └─ 통계 업데이트
       ├─ 총 수익 계산
       ├─ 승률 계산
       └─ 성과 지표 업데이트

5. 세션 유지
   ├─ SessionManager: 백그라운드 태스크
   │   ├─ 10분마다 세션 체크
   │   ├─ 만료 임박 시 토큰 갱신
   │   │   └─ Match-Trade API /manager/refresh-token
   │   │
   │   └─ 갱신 실패 시 재로그인
   │
   └─ Dashboard 상태 표시 업데이트

6. 사용자 모니터링
   ├─ Dashboard에서 실시간 데이터 확인
   │   ├─ 활성 포지션 현황
   │   ├─ 수익/손실
   │   ├─ 거래 내역
   │   └─ 성과 분석
   │
   └─ 필요 시 수동 개입
       ├─ 특정 유저 로그아웃
       ├─ 전체 포지션 청산
       └─ 설정 변경
```

---

## 📝 개발 순서 및 마일스톤

### Week 1: Foundation
- Day 1-2: Trading Engine 프로젝트 설정 및 Market Data Collector 구현
- Day 3-4: Volume Analyzer 및 OrderBook Analyzer 구현
- Day 5-7: Scalping Strategy 구현 및 테스트

### Week 2: Backend
- Day 1-2: Back Office Server 프로젝트 설정 및 Database 구축
- Day 3-4: Match-Trade API Client 구현
- Day 5-6: Session Manager 및 Order Orchestrator 구현
- Day 7: REST API 및 WebSocket 구현

### Week 3: Frontend
- Day 1-2: Dashboard 프로젝트 설정 및 공통 컴포넌트
- Day 3-4: 메인 대시보드 및 유저 관리 페이지
- Day 5-6: 거래 현황 및 내역 페이지
- Day 7: 성과 분석 페이지 및 반응형 디자인

### Week 4: Integration & Testing
- Day 1-2: 시스템 통합 및 엔드투엔드 테스트
- Day 3-4: 부하 테스트 및 성능 최적화
- Day 5-6: 보안 강화 및 에러 처리
- Day 7: 문서화 및 배포 준비

---

## 🎯 핵심 성공 요소

1. **동시성 처리**: asyncio를 활용한 효율적인 병렬 처리
2. **에러 처리**: 견고한 에러 핸들링 및 재시도 메커니즘
3. **실시간성**: WebSocket을 통한 즉각적인 데이터 업데이트
4. **확장성**: 유저 수 증가에 대응 가능한 아키텍처
5. **모니터링**: 시스템 상태 및 거래 성과 실시간 추적

---

## 🚀 Claude Code 에이전트 실행 가이드

각 Phase별로 다음과 같이 Claude Code 에이전트에게 요청하세요:

```
Phase 1 시작:
"trading_engine 프로젝트를 생성하고 TASK 1.1부터 1.7까지 순차적으로 구현해줘. 
각 태스크 완료 후 테스트 결과를 보여주고 다음 태스크로 진행해."

Phase 2 시작:
"back_office_server 프로젝트를 생성하고 TASK 2.1부터 2.9까지 순차적으로 구현해줘.
Match-Trade API 문서(/mnt/user-data/outputs/match_trade_api_complete_documentation.json)를 
참조하여 API Client를 정확하게 구현해."

Phase 3 시작:
"React + TypeScript로 dashboard 프로젝트를 생성하고 TASK 3.1부터 3.10까지 구현해줘.
Tailwind CSS를 사용하고 반응형 디자인을 적용해."

Phase 4 시작:
"전체 시스템을 Docker로 통합하고 TASK 4.1부터 4.6까지 완료해줘.
엔드투엔드 테스트를 수행하고 배포 준비를 완료해."
```

---

이 기획서를 바탕으로 Claude Code 에이전트가 각 Phase를 순차적으로 구현할 수 있습니다. 
각 컴포넌트는 독립적으로 개발 및 테스트 가능하며, 최종적으로 통합되어 완전한 자동 거래 시스템을 구성합니다.
