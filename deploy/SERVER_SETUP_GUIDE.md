# 🚀 Vultr 서버 초기 설정 및 GitHub Actions 배포 가이드

서버: `158.247.198.24`

---

## 📋 목차

1. [SSH 접속 설정](#1-ssh-접속-설정)
2. [서버 초기 설정](#2-서버-초기-설정)
3. [PostgreSQL 데이터베이스 설정](#3-postgresql-데이터베이스-설정)
4. [초기 애플리케이션 배포](#4-초기-애플리케이션-배포)
5. [GitHub Secrets 설정](#5-github-secrets-설정)
6. [GitHub Actions 배포 테스트](#6-github-actions-배포-테스트)

---

## 1. SSH 접속 설정

### 1-1. 로컬에서 서버 접속 테스트

```bash
# SSH로 서버 접속
ssh root@158.247.198.24

# 비밀번호 입력 또는 SSH 키 사용
```

### 1-2. SSH 키 페어 확인/생성

GitHub Actions에서 사용할 SSH 키가 필요합니다.

**옵션 A: 기존 SSH 키 사용**

로컬에서 개인키 확인:
```bash
# 개인키 파일 찾기 (보통 ~/.ssh/id_ed25519 또는 ~/.ssh/id_rsa)
ls -la ~/.ssh/

# 개인키 내용 출력 (GitHub에 등록할 내용)
cat ~/.ssh/id_ed25519
# 또는
cat ~/.ssh/id_rsa
```

**옵션 B: 새 SSH 키 페어 생성 (권장)**

```bash
# 배포 전용 SSH 키 생성
ssh-keygen -t ed25519 -C "github-actions@autobot" -f ~/.ssh/autobot_deploy

# 생성된 키 확인
ls -la ~/.ssh/autobot_deploy*
# autobot_deploy       <- 개인키 (GitHub Secret에 등록)
# autobot_deploy.pub   <- 공개키 (서버에 등록)
```

### 1-3. 서버에 공개키 등록

```bash
# 로컬에서 서버로 공개키 복사
ssh-copy-id -i ~/.ssh/autobot_deploy.pub root@158.247.198.24

# 또는 수동으로 등록
cat ~/.ssh/autobot_deploy.pub | ssh root@158.247.198.24 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 1-4. SSH 접속 테스트

```bash
# 새 키로 접속 테스트
ssh -i ~/.ssh/autobot_deploy root@158.247.198.24

# 성공하면 비밀번호 없이 접속됨
```

---

## 2. 서버 초기 설정

### 2-1. 서버 접속

```bash
ssh root@158.247.198.24
```

### 2-2. 초기 설정 스크립트 다운로드 및 실행

```bash
# 설정 스크립트 다운로드
curl -sSL https://raw.githubusercontent.com/gudax/autobot/main/deploy/scripts/server_setup.sh -o server_setup.sh

# 실행 권한 부여
chmod +x server_setup.sh

# 스크립트 실행 (5-10분 소요)
sudo bash server_setup.sh
```

**설치되는 항목**:
- ✅ Docker & Docker Compose
- ✅ Python 3.11
- ✅ Node.js 20.x & npm
- ✅ PostgreSQL 15
- ✅ Nginx
- ✅ 필수 시스템 도구

### 2-3. 설치 확인

```bash
# Docker 버전 확인
docker --version
docker compose version

# Python 버전 확인
python3 --version

# Node.js 버전 확인
node --version
npm --version

# PostgreSQL 상태 확인
sudo systemctl status postgresql

# Nginx 상태 확인
sudo systemctl status nginx
```

---

## 3. PostgreSQL 데이터베이스 설정

### 3-1. PostgreSQL 접속

```bash
sudo -u postgres psql
```

### 3-2. 데이터베이스 및 사용자 생성

```sql
-- 데이터베이스 생성
CREATE DATABASE autobot_trading;

-- 사용자 생성 (강력한 비밀번호 사용!)
CREATE USER autobot_user WITH ENCRYPTED PASSWORD 'AutoBot2024!SecurePassword';

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE autobot_trading TO autobot_user;

-- 확인
\l
\du

-- 종료
\q
```

### 3-3. 데이터베이스 연결 테스트

```bash
# 생성한 사용자로 접속 테스트
psql -U autobot_user -d autobot_trading -h localhost

# 비밀번호 입력 후 접속되면 성공
# \q로 종료
```

### 3-4. 비밀번호 기록 (나중에 사용)

```bash
# 비밀번호를 안전한 곳에 기록
echo "PostgreSQL Password: AutoBot2024!SecurePassword" > ~/db_password.txt
chmod 600 ~/db_password.txt
```

---

## 4. 초기 애플리케이션 배포

### 4-1. 애플리케이션 디렉토리 생성

```bash
# 배포 디렉토리로 이동
cd /opt

# Repository 클론
git clone https://github.com/gudax/autobot.git

# 디렉토리로 이동
cd autobot
```

### 4-2. 암호화 키 생성

```bash
# SECRET_KEY 생성
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "SECRET_KEY: $SECRET_KEY"

# ENCRYPTION_KEY 생성
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "ENCRYPTION_KEY: $ENCRYPTION_KEY"

# 키들을 파일에 저장 (나중에 참조)
cat > ~/app_keys.txt << EOF
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
EOF
chmod 600 ~/app_keys.txt
```

### 4-3. Back Office Server 환경 변수 설정

```bash
# .env 파일 생성
cat > /opt/autobot/back_office_server/.env << 'EOF'
# Application
APP_ENV=production
APP_NAME="AutoBot Trading System"
DEBUG=false

# Database
DATABASE_URL=postgresql://autobot_user:AutoBot2024!SecurePassword@postgres:5432/autobot_trading

# Match-Trade API
MATCH_TRADE_API_URL=https://mtr-demo-prod.match-trader.com
MATCH_TRADE_WS_URL=wss://mtr-demo-prod.match-trader.com

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Security (위에서 생성한 키로 교체)
SECRET_KEY=REPLACE_WITH_YOUR_SECRET_KEY
ENCRYPTION_KEY=REPLACE_WITH_YOUR_ENCRYPTION_KEY

# CORS
CORS_ORIGINS=http://158.247.198.24,http://localhost:3000

# Session
SESSION_REFRESH_INTERVAL_MINUTES=10
SESSION_EXPIRY_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/back_office.log
EOF

# 생성한 키로 .env 파일 업데이트
sed -i "s/REPLACE_WITH_YOUR_SECRET_KEY/$SECRET_KEY/" /opt/autobot/back_office_server/.env
sed -i "s/REPLACE_WITH_YOUR_ENCRYPTION_KEY/$ENCRYPTION_KEY/" /opt/autobot/back_office_server/.env
```

### 4-4. Dashboard 환경 변수 설정

```bash
cat > /opt/autobot/dashboard/.env << 'EOF'
VITE_API_URL=http://158.247.198.24:8000
VITE_WS_URL=ws://158.247.198.24:8000
VITE_APP_ENV=production
EOF
```

### 4-5. Trading Engine 환경 변수 설정

```bash
cat > /opt/autobot/trading_engine/.env << 'EOF'
# Match-Trade API
MATCH_TRADE_API_URL=https://mtr-demo-prod.match-trader.com
MATCH_TRADE_WS_URL=wss://mtr-demo-prod.match-trader.com

# Back Office API
BACK_OFFICE_API_URL=http://localhost:8000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/trading_engine.log
EOF
```

### 4-6. 로그 디렉토리 생성

```bash
mkdir -p /var/log/autobot
chmod 755 /var/log/autobot
```

### 4-7. Docker Compose로 서비스 시작

```bash
cd /opt/autobot

# 서비스 시작
docker compose -f docker-compose.prod.yml up -d --build

# 컨테이너 상태 확인
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f
```

### 4-8. 초기 배포 확인

```bash
# 헬스 체크
curl http://localhost:8000/health

# API Docs 확인
curl http://158.247.198.24:8000/docs
```

브라우저에서 접속:
- Dashboard: `http://158.247.198.24`
- API Docs: `http://158.247.198.24:8000/docs`

---

## 5. GitHub Secrets 설정

### 5-1. SSH 개인키 복사

로컬 환경에서:

```bash
# 개인키 전체 내용 출력
cat ~/.ssh/autobot_deploy

# 또는 기존 키 사용
cat ~/.ssh/id_ed25519
```

**출력 예시**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAN...
...
-----END OPENSSH PRIVATE KEY-----
```

⚠️ **주의**: `-----BEGIN`부터 `-----END`까지 **전체 내용**을 복사하세요!

### 5-2. GitHub Repository로 이동

1. 브라우저에서 GitHub 접속
2. Repository로 이동: https://github.com/gudax/autobot
3. **Settings** 탭 클릭

### 5-3. Secrets 추가

1. 좌측 메뉴: **Secrets and variables** → **Actions** 클릭
2. **New repository secret** 버튼 클릭

다음 4개의 Secrets를 추가:

#### Secret 1: `DEPLOY_HOST`
```
Name: DEPLOY_HOST
Value: 158.247.198.24
```

#### Secret 2: `DEPLOY_USER`
```
Name: DEPLOY_USER
Value: root
```

#### Secret 3: `DEPLOY_PORT`
```
Name: DEPLOY_PORT
Value: 22
```

#### Secret 4: `SSH_PRIVATE_KEY`
```
Name: SSH_PRIVATE_KEY
Value: [복사한 SSH 개인키 전체 내용]
```

**SSH_PRIVATE_KEY 예시**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAN...
(중간 내용 생략)
...
-----END OPENSSH PRIVATE KEY-----
```

### 5-4. Secrets 확인

**Secrets and variables** → **Actions** 페이지에서 다음 4개가 보여야 합니다:
- ✅ DEPLOY_HOST
- ✅ DEPLOY_USER
- ✅ DEPLOY_PORT
- ✅ SSH_PRIVATE_KEY

---

## 6. GitHub Actions 배포 테스트

### 6-1. 자동 배포 테스트 (main 브랜치 push)

로컬 환경에서:

```bash
cd /Users/kei/Documents/autobot

# 테스트용 변경사항 생성
echo "# AutoBot Trading System" > TEST_DEPLOY.md

# Git add & commit
git add TEST_DEPLOY.md
git commit -m "test: GitHub Actions deployment test"

# Push to main (자동 배포 트리거)
git push origin main
```

### 6-2. GitHub Actions 모니터링

1. GitHub Repository → **Actions** 탭
2. "Deploy to Vultr" 워크플로우 확인
3. 실행 중인 job 클릭
4. 각 단계별 로그 확인

**예상 단계**:
1. ✅ Test Job - Run Tests
2. ✅ Deploy Job - Deploy to Production
   - Setup SSH
   - Pull latest code
   - Deploy Backend
   - Deploy Trading Engine
   - Deploy Dashboard
   - Health Check
3. ✅ Notify Job - Send Notification

### 6-3. 수동 배포 트리거

1. GitHub Repository → **Actions** 탭
2. 좌측에서 "Deploy to Vultr" 워크플로우 선택
3. **Run workflow** 버튼 클릭
4. 브랜치 선택: `main`
5. Component 선택:
   - `all` (전체)
   - `backend` (백엔드만)
   - `frontend` (프론트엔드만)
   - `trading` (트레이딩 엔진만)
6. **Run workflow** 버튼 클릭

### 6-4. 배포 확인

서버에서 상태 확인:

```bash
# 서버 접속
ssh root@158.247.198.24

# 서비스 상태 확인
cd /opt/autobot
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f back_office_server

# 헬스 체크
curl http://localhost:8000/health
```

브라우저에서:
- Dashboard: http://158.247.198.24
- API Docs: http://158.247.198.24:8000/docs

---

## 7. 트러블슈팅

### 문제 1: SSH 연결 실패

**증상**: GitHub Actions에서 "SSH connection failed"

**해결**:
```bash
# 서버에서 SSH 로그 확인
sudo tail -f /var/log/auth.log

# authorized_keys 권한 확인
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# SSH 재시작
sudo systemctl restart sshd
```

### 문제 2: Docker 빌드 실패

**증상**: "docker: command not found"

**해결**:
```bash
# 서버에서 Docker 설치 확인
docker --version

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker
```

### 문제 3: 데이터베이스 연결 실패

**증상**: "Could not connect to database"

**해결**:
```bash
# PostgreSQL 상태 확인
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres pg_isready

# 비밀번호 확인
cat /opt/autobot/back_office_server/.env | grep DATABASE_URL

# PostgreSQL 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart postgres
```

### 문제 4: 포트 충돌

**증상**: "Port 8000 already in use"

**해결**:
```bash
# 포트 사용 확인
sudo netstat -tulpn | grep :8000

# 프로세스 종료
sudo kill -9 [PID]

# Docker 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart
```

---

## 8. 유용한 명령어

### 서버 상태 체크 스크립트

로컬에서 서버 상태 확인:

```bash
bash deploy/scripts/status.sh 158.247.198.24
```

### 로그 모니터링

```bash
# 서버에서
cd /opt/autobot

# 전체 로그
docker compose -f docker-compose.prod.yml logs -f

# 특정 서비스
docker compose -f docker-compose.prod.yml logs -f back_office_server

# 최근 100줄
docker compose -f docker-compose.prod.yml logs --tail=100
```

### 서비스 재시작

```bash
# 전체 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart

# 특정 서비스만
docker compose -f /opt/autobot/docker-compose.prod.yml restart back_office_server
```

---

## 9. 다음 단계

### ✅ 완료 체크리스트

- [ ] SSH 접속 성공
- [ ] 서버 초기 설정 완료 (server_setup.sh)
- [ ] PostgreSQL 데이터베이스 생성
- [ ] 암호화 키 생성 및 저장
- [ ] 초기 애플리케이션 배포 성공
- [ ] GitHub Secrets 4개 등록
- [ ] GitHub Actions 배포 테스트 성공
- [ ] 웹 브라우저 접속 확인

### 🎯 선택사항

- [ ] SSL 인증서 설정 (Let's Encrypt)
- [ ] 도메인 연결
- [ ] 백업 자동화
- [ ] 모니터링 활성화 (Prometheus + Grafana)
- [ ] 방화벽 강화

---

## 📞 지원

문제가 발생하면:
1. GitHub Issues: https://github.com/gudax/autobot/issues
2. 로그 확인: `docker compose logs -f`
3. 서버 상태: `bash deploy/scripts/status.sh 158.247.198.24`

---

**작성일**: 2025-10-27
**서버 IP**: 158.247.198.24
**GitHub**: https://github.com/gudax/autobot
