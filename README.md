# 뷰티판다 카드뉴스 자동화 (추가 비용 0원)

평일(월~금) 하루 한 개씩 인스타그램에 카드뉴스가 올라갑니다.
원장님이 하실 일은 **일주일에 한 번 Claude에게 한 마디**, 그리고 **검수 후 `승인`** 뿐이에요.

```
[월요일]  원장님 → Claude: "이번 주 카드뉴스 만들어줘"
          Claude: 주제 5개 제안 → 원고 작성 → 원장님 크롬에서 힉스필드 무제한 모드로 사진 생성(크레딧 0)
                  → GitHub '작업함'에 넘김
          GitHub: 카드뉴스 5개 완성 → 글마다 검수 요청 알림
[검수]    괜찮으면 `승인` / 고칠 건 Claude에게 말하기
[월~금 정오] 승인된 글이 하루에 하나씩 자동 게시
```

| 항목 | 비용 |
|---|---|
| 원고 | Claude 채팅에서 작성 (지금 쓰시는 Claude 요금제 안에서) |
| 사진 | 힉스필드 무제한 모드 (지금 쓰시는 요금제 안에서, 크레딧 0) |
| 카드뉴스 제작·예약 게시 | GitHub 공개 저장소 자동 실행 (무료) |
| 인스타 게시 | 인스타그램 공식 API (무료) |

피드 목표는 **뷰티샵 원장님을 모으는 것**입니다. (`config.yaml`의 `goal`)

---

## 처음 한 번만 하는 설정

### 1. GitHub 저장소 만들기
1. [github.com](https://github.com) 가입 → 오른쪽 위 **+ → New repository**
2. 이름 자유, **Public**으로 만들기 (인스타그램이 이미지를 가져가려면 공개여야 해요. 비밀 정보는 3번 Secrets에 따로 보관돼 공개되지 않아요.)
3. 빈 저장소 화면의 **uploading an existing file** → zip을 푼 폴더 **안의 내용물 전부**를 끌어다 놓기 → **Commit changes**
   - `.github` 폴더는 숨김 폴더예요. 맥 Finder `Cmd + Shift + .`, 윈도우 탐색기 **보기 → 숨긴 항목**을 켜면 보입니다.

### 2. 인스타그램 게시 권한 받기
1. 인스타 앱에서 @_beauty.panda를 **비즈니스 계정**으로 전환하고 **페이스북 페이지와 연결**
2. [developers.facebook.com](https://developers.facebook.com)에서 앱 만들기(유형: 비즈니스) → **Instagram** 제품 추가
3. 권한 `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`로 토큰 발급
   (비즈니스 설정의 **시스템 사용자 토큰** 권장. 일반 토큰은 60일 뒤 만료)
4. Graph API 탐색기에서 `me/accounts?fields=instagram_business_account` 조회 → 나오는 숫자가 계정 ID

가장 까다로운 단계예요. Claude에게 크롬 화면을 같이 봐달라고 하세요.

### 3. GitHub에 키 등록
저장소 → **Settings → Secrets and variables → Actions → New repository secret**
- `IG_USER_ID` : 인스타그램 계정 ID (숫자)
- `IG_ACCESS_TOKEN` : 인스타그램 토큰

**Settings → Actions → General → Workflow permissions**를 **Read and write permissions**로 변경.

### 4. 작업함 만들기
저장소 **Actions → 처음 설정 (한 번만) → Run workflow**. Issues 탭에 "📥 Claude 작업함"이 생기면 완료.

### 5. Claude 프로젝트 만들기 (추천)
claude.ai에서 **프로젝트**를 하나 만들고, 프로젝트 지침에 아래를 붙여넣으세요. 이러면 새 채팅에서도 Claude가 할 일을 바로 압니다.
```
뷰티판다 인스타 카드뉴스 담당이야. 저장소: https://github.com/<내아이디>/<저장소이름>
"이번 주 카드뉴스 만들어줘"라고 하면 저장소의 CLAUDE_GUIDE.md를 raw 주소로 읽고 그대로 진행해.
```

### 6. 휴대폰에 GitHub 앱 설치
검수 요청 알림 받는 용도예요.

---

## 평소 사용법
- **월요일**: 프로젝트 채팅에서 **"이번 주 카드뉴스 만들어줘"**. Claude가 주제 5개를 먼저 보여주고, 괜찮다고 하시면 원고와 사진을 만들어 넘깁니다. 사진 만드는 데 20~30분 걸려요. 로봇 확인 화면이 뜨면 그것만 직접 눌러주세요.
- **검수 요청이 오면**: 미리보기 확인 → 괜찮으면 **Labels**에서 `승인`. 예정 요일 정오에 올라갑니다 (예정일이 지났으면 바로).
- **고칠 게 있으면**: Claude에게 "10/7 글 표지 더 짧게"처럼 말하기. 수정본이 오면 다시 승인.
- **게시 전 확인** 항목이 있으면 이슈 본문 편집에서 체크해야 게시돼요.
- **급한 글·공지**: Claude에게 "오늘 품절 공지 하나 올리자". 승인하면 바로 올라갑니다.

## 바꾸고 싶을 때 (`config.yaml`)
- 게시 시각: `publish_time` + `.github/workflows/publish.yml`의 `cron` (한국시간 = UTC + 9)
- 정보·마케팅 비율: `rotation` (예: `[info, info, mkt]`)
- 장수, 글당 사진 수: `slides.count`, `slides.max_photos`

## 폴더 구조
```
CLAUDE_GUIDE.md      Claude가 따르는 작업 규칙 (원고 규칙, 사진 만드는 법, 넘기는 형식)
config.yaml          설정
src/pipeline.py      카드뉴스 완성 · 승인 · 게시
src/render.py        카드뉴스 이미지 렌더링
src/instagram.py     인스타그램 게시
templates/           카드뉴스 디자인 (스튜디오와 동일)
posts/               만들어진 카드뉴스
data/history.json    글 기록 (주제 중복 방지, 게시 일정)
```
