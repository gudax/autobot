# Back Office Server

Match-Trade Platform용 다중 계정 관리 백엔드 서버

## 개요

여러 사용자의 Match-Trade 계정을 동시에 관리하고, Trading Engine으로부터 받은 신호를 모든 계정에 동시에 실행하는 백엔드 서버입니다.

## 기술 스택

- Python 3.11+
- FastAPI (비동기 웹 프레임워크)
- PostgreSQL (데이터베이스)
- SQLAlchemy (ORM)
- WebSocket (실시간 통신)
- Docker (컨테이너화)

## 프로젝트 구조

```
back_office_server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── config/
│   │   ├── settings.py      # 설정 관리
│   │   └── database.py      # DB 설정
│   ├── models/              # SQLAlchemy 모델
│   ├── schemas/             # Pydantic 스키마
│   ├── api/                 # API 라우터
│   ├── services/            # 비즈니스 로직
│   ├── utils/               # 유틸리티
│   └── db/                  # 데이터베이스
├── tests/                   # 테스트
├── alembic/                 # DB 마이그레이션
├── docker-compose.yml       # Docker 설정
├── requirements.txt         # 의존성
└── README.md
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
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
# 예제 파일 복사
cp .env.example .env

# .env 파일 편집
vi .env
```

**필수 환경 변수:**
- `DB_PASSWORD`: PostgreSQL 비밀번호
- `MATCH_TRADE_BROKER_ID`: Broker ID
- `SECRET_KEY`: JWT 비밀키

### 4. PostgreSQL 데이터베이스 시작

```bash
# Docker Compose로 PostgreSQL 시작
docker-compose up -d postgres

# 데이터베이스 상태 확인
docker-compose ps
```

### 5. 데이터베이스 마이그레이션

```bash
# Alembic 초기화
alembic init alembic

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"

# 마이그레이션 적용
alembic upgrade head
```

## 실행

### 개발 모드

```bash
# FastAPI 서버 시작 (자동 리로드)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python app/main.py
```

### 프로덕션 모드

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

서버 실행 후 다음 URL에서 확인:
- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## 주요 기능

### 1. Session Manager
- 다중 유저 동시 로그인
- 세션 자동 갱신 (15분마다)
- 세션 상태 모니터링

### 2. Order Orchestrator
- 모든 유저에게 동시 주문 실행
- 병렬 처리로 빠른 실행
- 주문 상태 관리

### 3. REST API
- 유저 관리 (CRUD)
- 세션 관리
- 거래 실행
- 대시보드 데이터

### 4. WebSocket
- 실시간 포지션 업데이트
- 잔고 변화 알림
- 거래 신호 전송

## API 엔드포인트

### 유저 관리
```
POST   /api/v1/users              # 유저 생성
GET    /api/v1/users              # 유저 목록
GET    /api/v1/users/{id}         # 유저 조회
PUT    /api/v1/users/{id}         # 유저 수정
DELETE /api/v1/users/{id}         # 유저 삭제
POST   /api/v1/users/login-all    # 전체 로그인
```

### 거래 관리
```
POST   /api/v1/trading/signal     # 거래 신호 전송
POST   /api/v1/trading/execute-all # 전체 주문 실행
GET    /api/v1/trading/positions  # 포지션 조회
POST   /api/v1/trading/close-all  # 전체 청산
```

### 대시보드
```
GET    /api/v1/dashboard/overview    # 요약 정보
GET    /api/v1/dashboard/performance # 성과 분석
```

## 개발 상태

### Phase 2: Back Office Server ✅
- [x] TASK 2.1: 프로젝트 초기 설정
- [x] TASK 2.2: 데이터베이스 모델 생성
- [x] TASK 2.3: Match-Trade API Client
- [x] TASK 2.4: Session Manager
- [x] TASK 2.5: Order Orchestrator
- [x] TASK 2.6: REST API 엔드포인트
- [x] TASK 2.7: WebSocket 구현
- [x] TASK 2.8: 백그라운드 태스크
- [x] TASK 2.9: 통합 테스트

**Status**: Phase 2 Complete! 🎉

## 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=app --cov-report=html

# 특정 테스트 실행
pytest tests/test_session_manager.py -v
```

## 트러블슈팅

### PostgreSQL 연결 오류

```bash
# Docker 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs postgres

# 컨테이너 재시작
docker-compose restart postgres
```

### 포트 충돌

```bash
# 포트 8000이 사용 중인 경우
lsof -i :8000

# 프로세스 종료
kill -9 <PID>
```

## 라이센스

Proprietary

## 지원

문제가 발생하면 Issue를 생성하거나 문서를 참조하세요:
- [프로젝트 기획서](../auto_trading_system_project_plan.md)
- [Match-Trade API 문서](https://mtr-demo-prod.match-trader.com/docs)
