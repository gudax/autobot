# GitHub Secrets 설정 가이드

서버: `158.247.198.24`

---

## 📋 필요한 Secrets

GitHub Actions 자동 배포를 위해 다음 4개의 Secrets가 필요합니다:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DEPLOY_HOST` | `158.247.198.24` | 배포 서버 IP |
| `DEPLOY_USER` | `root` | SSH 사용자 |
| `DEPLOY_PORT` | `22` | SSH 포트 |
| `SSH_PRIVATE_KEY` | `[개인키 전체 내용]` | SSH 개인키 |

---

## 🔑 1. SSH 개인키 가져오기

### 방법 A: 기존 SSH 키 사용

```bash
# 개인키 확인 (로컬에서)
cat ~/.ssh/id_ed25519

# 또는
cat ~/.ssh/id_rsa
```

### 방법 B: 새 SSH 키 생성 (권장)

```bash
# 배포 전용 SSH 키 생성
ssh-keygen -t ed25519 -C "github-actions@autobot" -f ~/.ssh/autobot_deploy

# 개인키 출력
cat ~/.ssh/autobot_deploy

# 공개키를 서버에 등록
ssh-copy-id -i ~/.ssh/autobot_deploy.pub root@158.247.198.24
```

**개인키 예시**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAN...
...여러 줄...
...
-----END OPENSSH PRIVATE KEY-----
```

⚠️ **중요**: `-----BEGIN`부터 `-----END`까지 **전체 내용** 복사!

---

## ⚙️ 2. GitHub Secrets 등록

### 2-1. GitHub Repository 이동

1. 브라우저에서 https://github.com/gudax/autobot 접속
2. **Settings** 탭 클릭

### 2-2. Secrets 페이지 이동

1. 좌측 사이드바에서 **Secrets and variables** 클릭
2. **Actions** 클릭
3. 화면 우측 상단의 **New repository secret** 버튼 클릭

### 2-3. Secret 추가

각 Secret을 하나씩 추가:

#### ① DEPLOY_HOST
```
Name: DEPLOY_HOST
Secret: 158.247.198.24
```
**Add secret** 버튼 클릭

#### ② DEPLOY_USER
```
Name: DEPLOY_USER
Secret: root
```
**Add secret** 버튼 클릭

#### ③ DEPLOY_PORT
```
Name: DEPLOY_PORT
Secret: 22
```
**Add secret** 버튼 클릭

#### ④ SSH_PRIVATE_KEY
```
Name: SSH_PRIVATE_KEY
Secret: [복사한 SSH 개인키 전체 내용 붙여넣기]
```

**SSH_PRIVATE_KEY 입력 예시**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAN...
(여러 줄의 키 내용)
...
-----END OPENSSH PRIVATE KEY-----
```

⚠️ 주의사항:
- 줄바꿈 포함하여 **정확히** 복사
- 앞뒤 공백 없이 입력
- `-----BEGIN`과 `-----END` 포함

**Add secret** 버튼 클릭

---

## ✅ 3. Secrets 확인

**Secrets and variables** → **Actions** 페이지에서 다음이 표시되어야 합니다:

```
Repository secrets

DEPLOY_HOST         Updated now
DEPLOY_PORT         Updated now
DEPLOY_USER         Updated now
SSH_PRIVATE_KEY     Updated now
```

**총 4개의 Secrets**가 등록되어 있어야 합니다.

---

## 🧪 4. 배포 테스트

### 방법 A: 자동 배포 (Push)

```bash
# 로컬에서
cd /Users/kei/Documents/autobot

# 테스트 파일 생성
echo "# Deployment Test" > DEPLOY_TEST.md

# Commit & Push
git add DEPLOY_TEST.md
git commit -m "test: GitHub Actions deployment"
git push origin main
```

**GitHub → Actions 탭**에서 배포 진행 상황 확인

### 방법 B: 수동 배포

1. GitHub Repository → **Actions** 탭
2. 좌측에서 **Deploy to Vultr** 선택
3. 우측 상단 **Run workflow** 버튼 클릭
4. Branch: `main` 선택
5. Component: `all` 선택
6. **Run workflow** 클릭

---

## 🔍 5. 배포 확인

### GitHub Actions 로그 확인

1. **Actions** 탭에서 실행 중인 workflow 클릭
2. 각 Job 확인:
   - ✅ **test** - 테스트 실행
   - ✅ **deploy** - 배포 실행
   - ✅ **notify** - 알림

### 서버 확인

```bash
# SSH 접속
ssh root@158.247.198.24

# 서비스 상태
cd /opt/autobot
docker compose -f docker-compose.prod.yml ps

# 로그 확인
docker compose -f docker-compose.prod.yml logs -f
```

### 웹 브라우저 확인

- Dashboard: http://158.247.198.24
- API Docs: http://158.247.198.24:8000/docs
- Health Check: http://158.247.198.24:8000/health

---

## 🐛 트러블슈팅

### 문제 1: "Permission denied (publickey)"

**원인**: SSH 개인키가 서버에 등록되지 않음

**해결**:
```bash
# 공개키를 서버에 등록
ssh-copy-id -i ~/.ssh/autobot_deploy.pub root@158.247.198.24

# 또는 수동 등록
cat ~/.ssh/autobot_deploy.pub | ssh root@158.247.198.24 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 문제 2: "Bad configuration option: IdentitiesOnly"

**원인**: SSH 키 형식 오류

**해결**:
- GitHub Secret에 개인키 전체가 정확히 입력되었는지 확인
- `-----BEGIN`과 `-----END` 포함 확인
- 줄바꿈이 올바르게 보존되었는지 확인

### 문제 3: Workflow 실행 안 됨

**원인**: Secret 이름 오타 또는 누락

**해결**:
- Secret 이름이 정확한지 확인:
  - `DEPLOY_HOST` (대문자)
  - `DEPLOY_USER` (대문자)
  - `DEPLOY_PORT` (대문자)
  - `SSH_PRIVATE_KEY` (대문자, 언더스코어)

### 문제 4: "Connection timeout"

**원인**: 서버 방화벽 또는 네트워크 문제

**해결**:
```bash
# 서버에서 방화벽 확인
sudo ufw status

# SSH 포트 허용
sudo ufw allow 22/tcp
```

---

## 📊 체크리스트

배포 전 확인:

- [ ] SSH 키 생성 완료
- [ ] 공개키를 서버에 등록
- [ ] SSH 접속 테스트 성공
- [ ] GitHub Secrets 4개 등록
- [ ] Secret 이름 정확히 입력
- [ ] SSH_PRIVATE_KEY 전체 내용 복사
- [ ] 서버 초기 설정 완료
- [ ] 애플리케이션 초기 배포 완료

배포 후 확인:

- [ ] GitHub Actions 성공
- [ ] 서비스 정상 실행
- [ ] Dashboard 접속 가능
- [ ] API 응답 정상
- [ ] WebSocket 연결 정상

---

## 📞 지원

문제가 발생하면:

1. **GitHub Actions 로그 확인**
   - Actions 탭 → 실패한 workflow → 에러 메시지

2. **서버 로그 확인**
   ```bash
   ssh root@158.247.198.24
   cd /opt/autobot
   docker compose -f docker-compose.prod.yml logs
   ```

3. **이슈 등록**
   - https://github.com/gudax/autobot/issues

---

**작성일**: 2025-10-27
**서버**: 158.247.198.24
**Repository**: https://github.com/gudax/autobot
