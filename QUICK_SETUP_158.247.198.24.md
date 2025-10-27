# 🚀 빠른 배포 가이드 - 158.247.198.24

GitHub Actions 자동 배포를 위한 단계별 가이드입니다.

---

## ⏱️ 예상 소요 시간: 20분

- 서버 설정: 10분
- GitHub Secrets 설정: 5분
- 배포 테스트: 5분

---

## 📋 사전 준비

제공된 정보:
- ✅ 서버 IP: `158.247.198.24`
- ✅ SSH Key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAy9CRykQetrQIXu3tMLb9GNkkWE8JIxteXTX/6X8hJz`

---

## 1단계: SSH 접속 설정 (5분)

### 1-1. SSH 개인키 확인

로컬 터미널에서:

```bash
# 개인키 위치 확인
ls -la ~/.ssh/

# 개인키 내용 확인
cat ~/.ssh/id_ed25519
# 또는
cat ~/.ssh/id_rsa
```

**출력 예시**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmU...
(여러 줄)
-----END OPENSSH PRIVATE KEY-----
```

⚠️ **이 내용을 메모장에 복사** (GitHub Secrets에 사용)

### 1-2. 서버 접속 테스트

```bash
# SSH로 서버 접속
ssh root@158.247.198.24

# 성공하면 서버 프롬프트가 보임
# root@server:~#
```

✅ 접속 성공하면 다음 단계로

---

## 2단계: 서버 초기 설정 (10분)

### 2-1. 자동 설정 스크립트 (권장)

**로컬에서** 실행:

```bash
cd /Users/kei/Documents/autobot/deploy/scripts

# 자동 설정 스크립트 실행
bash setup-server-158.247.198.24.sh
```

이 스크립트가 자동으로 실행:
1. ✅ SSH 연결 테스트
2. ✅ Docker, Python, Node.js 설치
3. ✅ PostgreSQL 설정
4. ✅ Repository 클론
5. ✅ 암호화 키 생성
6. ✅ 환경 변수 설정
7. ✅ 서비스 시작
8. ✅ 헬스 체크

**완료 후 생성되는 파일**: `./generated_keys.txt` (보관 필수!)

### 2-2. 수동 설정 (자동 스크립트 실패 시)

상세 가이드 참조: [deploy/SERVER_SETUP_GUIDE.md](deploy/SERVER_SETUP_GUIDE.md)

---

## 3단계: GitHub Secrets 설정 (5분)

### 3-1. GitHub 접속

1. https://github.com/gudax/autobot 접속
2. **Settings** 탭 클릭
3. 좌측: **Secrets and variables** → **Actions**
4. **New repository secret** 클릭

### 3-2. 4개의 Secrets 추가

#### Secret 1: DEPLOY_HOST
```
Name: DEPLOY_HOST
Secret: 158.247.198.24
```
→ **Add secret**

#### Secret 2: DEPLOY_USER
```
Name: DEPLOY_USER
Secret: root
```
→ **Add secret**

#### Secret 3: DEPLOY_PORT
```
Name: DEPLOY_PORT
Secret: 22
```
→ **Add secret**

#### Secret 4: SSH_PRIVATE_KEY
```
Name: SSH_PRIVATE_KEY
Secret: [1-1에서 복사한 개인키 전체 내용]
```

**중요**:
- `-----BEGIN`부터 `-----END`까지 전체 복사
- 줄바꿈 포함
- 공백 없이

→ **Add secret**

### 3-3. 확인

**Secrets and variables** → **Actions** 페이지에서:
- ✅ DEPLOY_HOST
- ✅ DEPLOY_USER
- ✅ DEPLOY_PORT
- ✅ SSH_PRIVATE_KEY

**총 4개** 표시되면 성공!

상세 가이드: [deploy/GITHUB_SECRETS_SETUP.md](deploy/GITHUB_SECRETS_SETUP.md)

---

## 4단계: 배포 테스트 (5분)

### 4-1. 자동 배포 (Push)

로컬 터미널:

```bash
cd /Users/kei/Documents/autobot

# 테스트 파일 생성
echo "# GitHub Actions Deployment Test" > DEPLOY_TEST.md

# Git commit & push
git add .
git commit -m "test: GitHub Actions deployment to 158.247.198.24"
git push origin main
```

### 4-2. GitHub Actions 모니터링

1. GitHub → **Actions** 탭
2. "Deploy to Vultr" workflow 확인
3. 실행 로그 확인

**예상 시간**: 3-5분

### 4-3. 배포 확인

**브라우저에서**:
- Dashboard: http://158.247.198.24
- API Docs: http://158.247.198.24:8000/docs
- Health Check: http://158.247.198.24:8000/health

**서버에서**:
```bash
ssh root@158.247.198.24 'cd /opt/autobot && docker compose -f docker-compose.prod.yml ps'
```

---

## ✅ 완료 체크리스트

### 초기 설정
- [ ] SSH 접속 성공
- [ ] 서버 초기 설정 완료 (자동 스크립트)
- [ ] `generated_keys.txt` 파일 보관
- [ ] 브라우저에서 Dashboard 접속 확인

### GitHub Actions 설정
- [ ] GitHub Secrets 4개 등록
- [ ] Secret 이름 정확히 입력 (대문자)
- [ ] SSH_PRIVATE_KEY 전체 내용 복사

### 배포 테스트
- [ ] Git push 실행
- [ ] GitHub Actions 성공 (녹색 체크)
- [ ] 웹 서비스 정상 작동
- [ ] API 응답 확인

---

## 🎯 이제 사용 가능!

### 자동 배포 방법

**방법 1**: 코드 수정 후 Push
```bash
git add .
git commit -m "update: some changes"
git push origin main
```
→ 자동으로 서버에 배포됨

**방법 2**: 수동 트리거
1. GitHub → Actions → Deploy to Vultr
2. Run workflow 클릭
3. Component 선택 (all/backend/frontend/trading)
4. Run workflow 실행

### 서비스 접속

- **Dashboard**: http://158.247.198.24
- **API Docs**: http://158.247.198.24:8000/docs
- **WebSocket**: ws://158.247.198.24:8000/ws

---

## 🔧 유용한 명령어

### 서버 상태 확인

```bash
# 로컬에서 원격 상태 확인
bash deploy/scripts/status.sh 158.247.198.24
```

### 서비스 관리

```bash
# 서버에 접속
ssh root@158.247.198.24

# 서비스 상태
cd /opt/autobot
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f

# 재시작
docker compose -f docker-compose.prod.yml restart
```

---

## 🆘 문제 해결

### SSH 접속 실패
```bash
# 권한 확인
chmod 600 ~/.ssh/id_ed25519

# 연결 테스트
ssh -v root@158.247.198.24
```

### GitHub Actions 실패
1. Actions 탭에서 에러 로그 확인
2. Secret 이름/값 재확인
3. SSH 키 재등록

### 서비스 시작 실패
```bash
# 서버에서 로그 확인
ssh root@158.247.198.24
cd /opt/autobot
docker compose -f docker-compose.prod.yml logs
```

---

## 📚 상세 문서

- **전체 가이드**: [deploy/SERVER_SETUP_GUIDE.md](deploy/SERVER_SETUP_GUIDE.md)
- **GitHub Secrets**: [deploy/GITHUB_SECRETS_SETUP.md](deploy/GITHUB_SECRETS_SETUP.md)
- **배포 매뉴얼**: [deploy/README.md](deploy/README.md)

---

## 📞 지원

- GitHub Issues: https://github.com/gudax/autobot/issues
- 서버 로그: `docker compose logs -f`
- 상태 체크: `bash deploy/scripts/status.sh 158.247.198.24`

---

**준비 완료!** 이제 `git push`만 하면 자동으로 배포됩니다! 🎉

**서버**: 158.247.198.24
**Repository**: https://github.com/gudax/autobot
**작성**: 2025-10-27
