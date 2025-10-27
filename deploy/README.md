# AutoBot Trading System - Deployment Guide

이 가이드는 AutoBot Trading System을 Vultr 서버에 배포하는 방법을 설명합니다.

## 📋 목차

1. [사전 준비](#사전-준비)
2. [서버 초기 설정](#서버-초기-설정)
3. [수동 배포](#수동-배포)
4. [자동 배포 (GitHub Actions)](#자동-배포-github-actions)
5. [환경 변수 설정](#환경-변수-설정)
6. [SSL 인증서 설정](#ssl-인증서-설정)
7. [모니터링 설정](#모니터링-설정)
8. [백업 및 복구](#백업-및-복구)
9. [트러블슈팅](#트러블슈팅)

---

## 사전 준비

### 1. Vultr 서버 생성

- **OS**: Ubuntu 22.04 LTS 또는 Debian 11
- **권장 사양**:
  - CPU: 4 cores 이상
  - RAM: 8GB 이상
  - Storage: 80GB SSD 이상
  - Network: 1Gbps

### 2. 로컬 환경 준비

```bash
# SSH 키 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# SSH 키를 서버에 복사
ssh-copy-id root@your-server-ip
```

### 3. 필수 정보

- 서버 IP 주소
- SSH 접속 정보
- GitHub Personal Access Token (자동 배포용)
- 도메인 네임 (선택사항)

---

## 서버 초기 설정

### 1단계: 서버 접속

```bash
ssh root@your-server-ip
```

### 2단계: 초기 설정 스크립트 실행

서버에 접속한 후:

```bash
# 설정 스크립트 다운로드
wget https://raw.githubusercontent.com/gudax/autobot/main/deploy/scripts/server_setup.sh

# 실행 권한 부여
chmod +x server_setup.sh

# 스크립트 실행
sudo bash server_setup.sh
```

이 스크립트는 다음을 자동으로 설치합니다:
- Docker & Docker Compose
- Python 3.11
- Node.js 20.x
- PostgreSQL 15
- Nginx
- 필수 시스템 도구

**예상 소요 시간**: 5-10분

### 3단계: PostgreSQL 데이터베이스 설정

```bash
# PostgreSQL에 접속
sudo -u postgres psql

# 데이터베이스 및 사용자 생성
CREATE DATABASE autobot_trading;
CREATE USER autobot_user WITH ENCRYPTED PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE autobot_trading TO autobot_user;

# 종료
\q
```

---

## 수동 배포

### 1단계: 배포 설정

로컬 환경에서:

```bash
cd autobot/deploy

# 설정 파일 복사 및 수정
cp config.env.example config.env
vim config.env  # 또는 nano, code 등
```

**필수 설정 항목**:
```bash
SERVER_HOST=your-server-ip
SERVER_USER=root
SSH_KEY_PATH=~/.ssh/id_rsa

POSTGRES_PASSWORD=your_strong_password
SECRET_KEY=your_32_char_secret_key
ENCRYPTION_KEY=your_encryption_key

APP_DOMAIN=autobot.yourdomain.com  # 도메인이 있는 경우
```

### 2단계: 암호화 키 생성

```bash
# SECRET_KEY 생성
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3단계: 배포 실행

```bash
# 배포 스크립트에 실행 권한 부여
chmod +x deploy.sh

# 전체 배포
./deploy.sh production all

# 특정 컴포넌트만 배포
./deploy.sh production backend    # 백엔드만
./deploy.sh production frontend   # 프론트엔드만
./deploy.sh production trading    # 트레이딩 엔진만
```

**배포 프로세스**:
1. ✓ 서버 연결 확인
2. ✓ 배포 디렉토리 준비
3. ✓ GitHub에서 코드 업데이트
4. ✓ 환경 변수 설정
5. ✓ Docker 컨테이너 빌드 및 시작
6. ✓ 데이터베이스 마이그레이션
7. ✓ 헬스 체크
8. ✓ 서비스 상태 확인

**예상 소요 시간**: 3-5분

### 4단계: 배포 확인

```bash
# 서비스 상태 확인
ssh root@your-server-ip 'cd /opt/autobot && docker compose -f docker-compose.prod.yml ps'

# 로그 확인
ssh root@your-server-ip 'cd /opt/autobot && docker compose -f docker-compose.prod.yml logs -f back_office_server'
```

**접속 URL**:
- Dashboard: `http://your-server-ip`
- API: `http://your-server-ip/api`
- API Docs: `http://your-server-ip/docs`
- WebSocket: `ws://your-server-ip/ws`

---

## 자동 배포 (GitHub Actions)

### 1단계: GitHub Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions

다음 secrets를 추가:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DEPLOY_HOST` | 서버 IP 주소 | `123.45.67.89` |
| `DEPLOY_USER` | SSH 사용자 | `root` |
| `DEPLOY_PORT` | SSH 포트 | `22` |
| `SSH_PRIVATE_KEY` | SSH 개인키 전체 내용 | `-----BEGIN RSA...` |

**SSH_PRIVATE_KEY 설정 방법**:
```bash
# 개인키 내용 복사
cat ~/.ssh/id_rsa

# 출력 전체를 복사하여 GitHub Secret에 추가
```

### 2단계: 서버에 초기 배포

첫 번째 배포는 수동으로 진행:

```bash
# 서버에 코드 클론
ssh root@your-server-ip
cd /opt
git clone https://github.com/gudax/autobot.git
cd autobot

# 환경 변수 설정
cp back_office_server/.env.example back_office_server/.env
vim back_office_server/.env  # 설정 입력

# Docker Compose로 시작
docker compose -f docker-compose.prod.yml up -d
```

### 3단계: 자동 배포 트리거

**자동 트리거**:
```bash
# main 브랜치에 push하면 자동 배포
git push origin main
```

**수동 트리거**:
1. GitHub Repository → Actions
2. "Deploy to Vultr" 워크플로우 선택
3. "Run workflow" 클릭
4. 배포할 컴포넌트 선택 (all/backend/frontend/trading)
5. "Run workflow" 버튼 클릭

### GitHub Actions 워크플로우 단계:

1. **Test Job**:
   - ✓ 코드 체크아웃
   - ✓ Python/Node.js 설정
   - ✓ 의존성 설치
   - ✓ 테스트 실행
   - ✓ 빌드 검증

2. **Deploy Job**:
   - ✓ SSH 연결 설정
   - ✓ 서버에서 코드 업데이트
   - ✓ Docker 컨테이너 재배포
   - ✓ 데이터베이스 마이그레이션
   - ✓ 헬스 체크

3. **Notify Job**:
   - ✓ 배포 성공/실패 알림

---

## 환경 변수 설정

### Back Office Server (.env)

```bash
# Production Environment
APP_ENV=production
SECRET_KEY=your_32_char_secret_key_here
ENCRYPTION_KEY=your_fernet_encryption_key_here

# Database
DATABASE_URL=postgresql://autobot_user:password@postgres:5432/autobot_trading

# Match-Trade API
MATCH_TRADE_API_URL=https://api.match-trade.com
MATCH_TRADE_WS_URL=wss://api.match-trade.com

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# CORS
CORS_ORIGINS=http://your-server-ip,https://your-domain.com

# Session
SESSION_REFRESH_INTERVAL_MINUTES=10
SESSION_EXPIRY_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/back_office.log
```

### Dashboard (.env)

```bash
VITE_API_URL=http://your-server-ip:8000
VITE_WS_URL=ws://your-server-ip:8000
VITE_APP_ENV=production
```

### Trading Engine (.env)

```bash
MATCH_TRADE_API_URL=https://api.match-trade.com
MATCH_TRADE_WS_URL=wss://api.match-trade.com
BACK_OFFICE_API_URL=http://localhost:8000
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/trading_engine.log
```

---

## SSL 인증서 설정

### Let's Encrypt (무료 SSL)

```bash
# 서버에 접속
ssh root@your-server-ip

# Certbot 설치
apt-get update
apt-get install -y certbot python3-certbot-nginx

# 인증서 발급
certbot --nginx -d autobot.yourdomain.com

# 자동 갱신 설정 (cron)
certbot renew --dry-run
```

### Nginx SSL 설정 활성화

```bash
# Nginx 설정 파일 수정
vim /opt/autobot/deploy/nginx/conf.d/autobot.conf

# HTTPS 서버 블록 주석 해제 및 도메인 설정
# server_name을 실제 도메인으로 변경

# Nginx 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart nginx
```

---

## 모니터링 설정

### Prometheus + Grafana 활성화

```bash
# 서버에서
cd /opt/autobot

# 모니터링 프로파일로 시작
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# 접속 URL
# Prometheus: http://your-server-ip:9090
# Grafana: http://your-server-ip:3001
```

### Grafana 초기 설정

1. 접속: `http://your-server-ip:3001`
2. 로그인: admin / admin (초기 비밀번호)
3. 비밀번호 변경
4. Dashboard 추가:
   - Import → ID: 3662 (Prometheus 2.0 Overview)
   - Import → ID: 7362 (PostgreSQL Dashboard)

---

## 백업 및 복구

### 데이터베이스 백업

```bash
# 백업 스크립트 생성
cat > /opt/autobot/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/autobot
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL 백업
docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres \
  pg_dump -U autobot_user autobot_trading | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
EOF

chmod +x /opt/autobot/backup.sh
```

### 자동 백업 (Cron)

```bash
# crontab 편집
crontab -e

# 매일 새벽 3시에 백업
0 3 * * * /opt/autobot/backup.sh >> /var/log/autobot/backup.log 2>&1
```

### 복구

```bash
# 백업 파일에서 복구
gunzip < /var/backups/autobot/db_20231027_030000.sql.gz | \
  docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres \
  psql -U autobot_user -d autobot_trading
```

---

## 트러블슈팅

### 서비스가 시작되지 않음

```bash
# 로그 확인
docker compose -f /opt/autobot/docker-compose.prod.yml logs back_office_server

# 컨테이너 상태 확인
docker compose -f /opt/autobot/docker-compose.prod.yml ps

# 컨테이너 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart
```

### 데이터베이스 연결 오류

```bash
# PostgreSQL 상태 확인
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres pg_isready

# 연결 테스트
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres \
  psql -U autobot_user -d autobot_trading -c "SELECT 1;"

# 환경 변수 확인
docker compose -f /opt/autobot/docker-compose.prod.yml exec back_office_server env | grep DATABASE
```

### WebSocket 연결 실패

```bash
# Nginx 로그 확인
docker compose -f /opt/autobot/docker-compose.prod.yml logs nginx

# WebSocket 프록시 설정 확인
cat /opt/autobot/deploy/nginx/conf.d/autobot.conf | grep -A 10 "location /ws"
```

### 메모리 부족

```bash
# 메모리 사용량 확인
docker stats

# 불필요한 이미지 정리
docker system prune -a

# Worker 수 줄이기 (back_office_server/.env)
WORKERS=2
```

### 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h

# Docker 볼륨 정리
docker volume prune

# 로그 파일 정리
find /var/log/autobot -name "*.log" -mtime +30 -delete
```

---

## 유용한 명령어

### 서비스 관리

```bash
# 전체 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart

# 특정 서비스 재시작
docker compose -f /opt/autobot/docker-compose.prod.yml restart back_office_server

# 서비스 중지
docker compose -f /opt/autobot/docker-compose.prod.yml down

# 서비스 시작
docker compose -f /opt/autobot/docker-compose.prod.yml up -d
```

### 로그 확인

```bash
# 실시간 로그
docker compose -f /opt/autobot/docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker compose -f /opt/autobot/docker-compose.prod.yml logs -f back_office_server

# 마지막 100줄
docker compose -f /opt/autobot/docker-compose.prod.yml logs --tail=100
```

### 데이터베이스 작업

```bash
# PostgreSQL 쉘 접속
docker compose -f /opt/autobot/docker-compose.prod.yml exec postgres \
  psql -U autobot_user -d autobot_trading

# SQL 실행
docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres \
  psql -U autobot_user -d autobot_trading -c "SELECT COUNT(*) FROM users;"
```

---

## 성능 최적화

### 1. PostgreSQL 튜닝

```sql
-- /var/lib/postgresql/data/postgresql.conf
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### 2. Nginx 캐싱

```nginx
# proxy_cache 설정 추가
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;
proxy_cache_key "$scheme$request_method$host$request_uri";
```

### 3. Redis 캐싱

Back Office Server에서 Redis를 사용하여 자주 사용하는 데이터 캐싱

---

## 보안 체크리스트

- [ ] SSH 포트 변경 (기본 22 → 다른 포트)
- [ ] 방화벽 설정 (UFW)
- [ ] SSL 인증서 설정
- [ ] 강력한 데이터베이스 비밀번호
- [ ] 정기적인 보안 업데이트
- [ ] 백업 자동화
- [ ] 로그 모니터링
- [ ] Rate limiting 설정
- [ ] API 키 암호화
- [ ] 2FA 활성화 (선택사항)

---

## 지원 및 문의

- **이슈 리포트**: https://github.com/gudax/autobot/issues
- **문서**: https://github.com/gudax/autobot/wiki
- **라이선스**: MIT

---

**Last Updated**: 2025-10-27
