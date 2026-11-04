# person_detection

카페·식당 고객 이미지를 업로드하면 **YOLO 얼굴 검출 모델**로 얼굴을 찾고, 검출된 얼굴 수를 SQLite에 저장해 이력과 시간대별·일별 통계를 보여 주는 웹 애플리케이션입니다. (소프트웨어공학 11주차 과제)

> 검출 대상은 사람 전체가 아닌 **얼굴**입니다. COCO `person` 클래스가 아니라 얼굴 데이터셋으로 학습된 `yolov8n-face` 가중치를 사용합니다.

## 기술 스택

| 구분 | 사용 기술 |
|---|---|
| Client | Node.js, Express, HTML/CSS/JavaScript, Chart.js |
| Server | Python, FastAPI, Ultralytics YOLO, OpenCV, Pillow, bcrypt |
| Database | SQLite |

## 구조

```
브라우저 ──▶ Node.js 웹 서버 (:3000) ──▶ FastAPI 서버 (:8000) ──▶ SQLite
            화면 제공, 로그인 쿠키,          인증, 이미지 검증,
            /api 프록시                     YOLO 얼굴 검출, 통계
```

- 로그인하면 FastAPI가 토큰을 발급합니다. Node.js는 이 토큰을 HttpOnly 쿠키에 담고, `/api` 요청마다 `Authorization` 헤더로 바꿔 전달합니다.
- DB에는 FastAPI만 접근합니다. 모든 쿼리는 파라미터 바인딩을 쓰고, 모든 조회는 로그인 사용자의 `user_id`로 범위가 제한됩니다.

## 디렉터리

```
person_detection/
├─ client/                 Node.js 웹 서버
│  ├─ server.js            정적 파일 제공, 로그인/로그아웃, FastAPI 프록시
│  ├─ package.json
│  └─ public/              index.html, css/style.css, js/app.js
├─ server/                 FastAPI 애플리케이션 서버
│  ├─ main.py              앱 생성, 라우터 등록, 공통 오류 처리
│  ├─ config.py            환경변수 설정
│  ├─ database.py          DB 연결, 초기화, 테스트 계정 생성
│  ├─ routers/             auth, users, analyses, stats API
│  ├─ services/            인증, 이미지 검증, 얼굴 검출, 분석, 통계
│  ├─ models/              YOLO 가중치 (yolov8n-face.pt, git 제외)
│  ├─ uploads/             업로드 원본과 결과 이미지 (실행 시 생성, git 제외)
│  └─ requirements.txt
├─ database/
│  ├─ schema.sql           테이블 정의
│  └─ database.db          실행 시 자동 생성 (git 제외)
├─ docs/design/            소프트웨어 설계서(설계1.md, PlantUML)와 UML 이미지
├─ screen_shot/            실행 화면 캡처
├─ .env.example
└─ README.md
```

## 설치 및 실행 (Windows PowerShell)

아래 명령은 모두 `person_detection` 폴더에서 실행합니다.

### 1. Python 가상환경과 패키지

Python 3.10 이상이 필요합니다(3.12에서 테스트함). CPU용 PyTorch를 먼저 설치하면 용량을 줄일 수 있습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r server\requirements.txt
```

> 프로젝트가 OneDrive 폴더 안에 있으면 `.venv`(약 1GB)까지 동기화됩니다. 이 경우 가상환경을 OneDrive 밖에 만들어도 됩니다. 예: `python -m venv $env:USERPROFILE\.venvs\person_detection`

### 2. YOLO 얼굴 검출 가중치 준비

| 항목 | 내용 |
|---|---|
| 모델 | YOLOv8n-face (YOLOv8 nano 기반 얼굴 검출, 약 6MB) |
| 출처 | https://github.com/akanametov/yolo-face (릴리스 1.0.0) |
| 라이선스 | GPL-3.0 (원 저장소 기준) |

```powershell
Invoke-WebRequest https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt -OutFile server\models\yolov8n-face.pt
```

코드에서는 `ultralytics.YOLO("server/models/yolov8n-face.pt")`로 불러와 `predict(conf=0.35)` 결과의 박스 수를 얼굴 수로 사용합니다.

### 3. 환경변수 (선택)

```powershell
Copy-Item .env.example .env
```

값을 바꾸지 않으면 기본값(웹 3000번, API 8000번 포트, 업로드 최대 10MB)이 적용됩니다.

### 4. SQLite 초기화

FastAPI 서버를 시작하면 `database/database.db`와 테스트 계정이 자동으로 만들어집니다. 직접 초기화하려면 아래 명령을 실행합니다.

```powershell
cd server
python database.py
cd ..
```

처음부터 다시 시작하려면 `database\database.db`와 `server\uploads` 폴더를 지운 뒤 서버를 다시 실행하면 됩니다.

### 5. FastAPI 서버 실행 (터미널 1)

```powershell
.\.venv\Scripts\Activate.ps1
cd server
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 6. Node.js 서버 실행 (터미널 2)

```powershell
cd client
npm install
npm start
```

### 7. 접속

- 웹: http://localhost:3000
- API 문서(Swagger): http://127.0.0.1:8000/docs
- 테스트 계정: **test / test**

## 주요 기능

| 화면 | 기능 | 요구사항 |
|---|---|---|
| 로그인 | 로그인/로그아웃, bcrypt 비밀번호 해시, 토큰 만료(12시간) | R004, R008, R015 |
| 대시보드 | 오늘 검출된 얼굴 수, 성공/실패 건수, 최근 분석 5건 | R003, R005 |
| 이미지 분석 | 업로드와 미리보기, 얼굴 bounding box 이미지, 얼굴 수, 로딩 표시 | R001, R002, R003 |
| 분석 결과 | 결과 상세, 얼굴 수의 의미 안내, 실패 시 사유 표시와 재분석 | R003, R010 |
| 분석 이력 | 시작일~종료일 검색, 최신순/오래된 순 정렬, 상태 표시, 실패 분석 재분석 | R005, R010, R011, R012 |
| 통계 | 시간대별/일별 전환, 기간 선택, Chart.js 그래프(막대 위 수치, 툴팁), 표, CSV 다운로드 | R006, R013, R014 |
| 사용자 관리 | 내 정보 조회, 이름/비밀번호 변경, 새 사용자 등록, 계정 삭제 | R004 |

### 검증 및 보안

- 업로드 파일은 확장자(jpg, jpeg, png, webp, bmp)와 크기(10MB)를 확인합니다. 그다음 Pillow로 실제 이미지 형식을 확인하고, OpenCV 디코딩까지 성공한 파일만 분석합니다.
- 실패한 분석은 `status='FAILED'`, `face_count=NULL`로 저장되고 통계에서 제외됩니다. 통계와 CSV는 같은 집계 함수를 써서 값이 항상 같습니다.
- 재분석은 기존 행을 덮어쓰지 않고 새 행(`retry_of` = 원본 ID)으로 저장합니다.
- 다른 사용자의 분석을 요청하면 존재하지 않는 것처럼 404를 반환합니다.
- 서버 내부 예외와 DB 경로는 로그에만 남기고, 사용자에게는 요약 메시지만 보여 줍니다.

## 테스트 결과

Node.js(:3000)를 거쳐 API를 호출하는 통합 테스트 21개 항목을 실제 이미지로 실행했고 **모두 통과**했습니다.

| # | 테스트 | 결과 |
|---|---|---|
| 1 | test/test 로그인 성공, 로그아웃 후 토큰 무효화 | 통과 |
| 2 | 잘못된 비밀번호 거부(401), 비로그인 API 접근 차단 | 통과 |
| 3 | 정상 이미지 업로드 | 통과 |
| 4 | `.jpg`로 위장한 텍스트 파일 거부, 허용되지 않은 확장자 거부 | 통과 |
| 5 | 얼굴 검출: 카페 사진(2명 중 정면 얼굴 1명) → 1명, bounding box 이미지 생성 | 통과 |
| 6 | 빈 매장 사진 → 0명 | 통과 |
| 7 | 분석 결과 SQLite 저장 확인 | 통과 |
| 8 | 이력 조회, 정렬, 잘못된 기간(종료일 < 시작일) 거부 | 통과 |
| 9 | 시간대별 통계(24구간) | 통과 |
| 10 | 일별 통계 | 통과 |
| 11 | 실패 분석이 통계에서 제외됨 | 통과 |
| 12 | 다른 사용자의 목록, 상세, 이미지, 재분석, 통계 접근 차단, SQL 인젝션 형태 입력 거부 | 통과 |
| 13 | CSV 다운로드(합계가 화면 통계와 일치) | 통과 |
| 14 | 실패 분석 수동 재분석(새 이력 생성, 원본 유지), 성공 분석 재분석 거부 | 통과 |

- 테스트 이미지는 Wikimedia Commons의 CC BY 2.0 사진 2장입니다("Business people discussing in the cafe", "Modern cafe interior design with empty tables…"). 저장소에는 포함하지 않았습니다.
- 11번과 14번은 실제 모델 오류를 일부러 일으키기 어려워서, 실제 업로드 원본을 가리키는 `FAILED` 행을 DB에 직접 추가해 확인했습니다.

## 알려진 한계 및 주의사항

- **얼굴 수는 고객 수와 다를 수 있습니다.** 뒷모습, 정수리만 보이는 탑뷰, 가려진 얼굴, 작은 얼굴은 검출되지 않을 수 있습니다. 테스트에서도 뒤돌아 앉은 사람은 검출되지 않았습니다.
- 같은 고객이 여러 이미지에 찍히면 통계에서 중복 집계됩니다. 이 내용은 통계 화면에도 안내합니다.
- 분석 시각은 서버의 로컬 시각 기준입니다.
- CPU에서 추론하므로 첫 분석은 모델 로딩 때문에 몇 초 더 걸립니다.
- 얼굴 검출 가중치(GPL-3.0)와 Ultralytics(AGPL-3.0)의 라이선스 조건은 각 원 저장소를 따릅니다.
