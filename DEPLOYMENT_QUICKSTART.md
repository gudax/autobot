# 🚀 AutoBot Trading System - 빠른 배포 가이드

## 5분 안에 Vultr 서버에 배포하기

### 전제 조건
- Vultr 서버 (Ubuntu 22.04, 8GB RAM 이상)
- SSH 접근 권한
- 서버 IP 주소

---

## 방법 1: 자동 배포 스크립트 (추천)

### 1단계: 서버 초기 설정 (최초 1회만)

```bash
# 서버 접속
ssh root@YOUR_SERVER_IP

# 초기 설정 스크립트 다운로드 및 실행
curl -sSL https://raw.githubusercontent.com/gudax/autobot/main/deploy/scripts/server_setup.sh | sudo bash

# 데이터베이스 설정
sudo -u postgres psql << EOF
CREATE DATABASE autobot_trading;
CREATE USER autobot_user WITH ENCRYPTED PASSWORD 'change_this_password';
GRANT ALL PRIVILEGES ON DATABASE autobot_trading TO autobot_user;
\q
EOF
```

### 2단계: 로컬에서 배포 설정

```bash
# 로컬 환경
cd autobot/deploy

# 설정 파일 생성
cp config.env.example config.env

# 필수 항목 수정
vim config.env
# SERVER_HOST=YOUR_SERVER_IP
# POSTGRES_PASSWORD=change_this_password
# SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
# ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 3단계: 배포 실행

```bash
# 배포 스크립트 실행
./deploy.sh production all

# 완료! 서비스 접속
# Dashboard: http://YOUR_SERVER_IP
# API Docs: http://YOUR_SERVER_IP/docs
```

---

## 방법 2: GitHub Actions 자동 배포

### 1단계: GitHub Secrets 설정

GitHub Repository → Settings → Secrets → New repository secret

```
DEPLOY_HOST = YOUR_SERVER_IP
DEPLOY_USER = root
DEPLOY_PORT = 22
SSH_PRIVATE_KEY = [복사한 SSH 개인키]
```

### 2단계: 서버 초기 배포

```bash
# 서버 접속
ssh root@YOUR_SERVER_IP

# 코드 클론
cd /opt
git clone https://github.com/gudax/autobot.git
cd autobot

# 환경 변수 설정
cat > back_office_server/.env << EOF
APP_ENV=production
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
DATABASE_URL=postgresql://autobot_user:change_this_password@postgres:5432/autobot_trading
MATCH_TRADE_API_URL=https://api.match-trade.com
HOST=0.0.0.0
PORT=8000
EOF

# Docker Compose 시작
docker compose -f docker-compose.prod.yml up -d
```

### 3단계: 자동 배포

```bash
# 이제 main 브랜치에 push하면 자동 배포됨
git add .
git commit -m "Update code"
git push origin main

# GitHub Actions에서 자동으로 배포 진행
```

---

## 배포 확인

### 서비스 상태 확인

```bash
# 서버에서
docker compose -f /opt/autobot/docker-compose.prod.yml ps

# 로그 확인
docker compose -f /opt/autobot/docker-compose.prod.yml logs -f
```

### 헬스 체크

```bash
# API 헬스 체크
curl http://YOUR_SERVER_IP:8000/health

# Dashboard 접속
# 브라우저에서: http://YOUR_SERVER_IP
```

---

## 주요 명령어

```bash
# 서비스 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart

# 서비스 중지
docker compose -f /opt/autobot/docker-compose.prod.yml down

# 서비스 시작
docker compose -f /opt/autobot/docker-compose.prod.yml up -d

# 로그 확인
docker compose -f /opt/autobot/docker-compose.prod.yml logs -f back_office_server
```

---

## 트러블슈팅

### 문제: 서비스가 시작되지 않음
```bash
# 로그 확인
docker compose -f /opt/autobot/docker-compose.prod.yml logs

# 환경 변수 확인
docker compose -f /opt/autobot/docker-compose.prod.yml config
```

### 문제: 데이터베이스 연결 실패
```bash
# PostgreSQL 상태 확인
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres pg_isready

# 연결 테스트
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres \
  psql -U autobot_user -d autobot_trading -c "SELECT 1;"
```

### 문제: 포트 충돌
```bash
# 사용 중인 포트 확인
sudo netstat -tulpn | grep :8000

# docker-compose.prod.yml에서 포트 변경
vim /opt/autobot/docker-compose.prod.yml
```

---

## 다음 단계

1. ✅ SSL 인증서 설정 (Let's Encrypt)
2. ✅ 도메인 연결
3. ✅ 백업 자동화 설정
4. ✅ 모니터링 활성화 (Prometheus + Grafana)
5. ✅ 방화벽 설정 강화

**자세한 내용**: [deploy/README.md](deploy/README.md)

---

## 지원

- 이슈: https://github.com/gudax/autobot/issues
- 문서: https://github.com/gudax/autobot/wiki

**배포 소요 시간**: 약 5-10분
