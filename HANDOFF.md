# 계통 여유용량 영업 대시보드 — 개발 인수인계 문서 (모바일화용)

> 이 문서는 **다른 팀원의 Claude Code가 사전 학습**한 뒤 **모바일 버전 개발**을 이어가기 위한 인수인계 자료입니다.
> 현재까지는 **데스크톱/웹 위주의 단일 페이지**로 개발되어 있고, 실사용자는 **영업직원이 외부에서 휴대폰으로** 보게 됩니다. → **모바일 최적화가 다음 목표.**

---

## 1. 프로젝트 개요

- **무엇**: 전국 변전소의 **계통 여유용량**(태양광을 계통에 연결할 수 있는 여유)을 지도로 보여주는 **태양광 영업 타겟팅 대시보드**.
- **왜**: 해피솔라(태양광 회사) 영업팀이 "이 지역/이 변전소는 아직 연계 여유가 있으니 영업 우선순위"를 현장에서 빠르게 판단하기 위함.
- **사용자·환경**: **영업직원, 외부, 휴대폰 브라우저**. (지금 UI는 데스크톱 기준 → 모바일화 필요)
- **라이브 URL**: https://chmd20-a11y.github.io/grid-capacity-dashboard/
- **저장소**: GitHub `chmd20-a11y/grid-capacity-dashboard` (공개, GitHub Pages)
- **로컬 경로**: `/Users/happysolar/Desktop/02_Claude/grid-capacity-dashboard/` (원 개발 PC 기준)

### 핵심 도메인 개념 (모바일 개발자도 반드시 이해)
- **연계가능(connect_max_mw)** = 그 변전소에서 **지금 실제로 태양광을 붙일 수 있는 양**. 변전소·주변압기·**선로(DL)** 여유의 **병목(min)**. 보통 선로당 **≤13MW**(22.9kV 한계). **이게 대표 지표.**
- **지역여지(subst_free_mw)** = 변전소 전체 총여유. 확장 잠재력(선로 증설 시)일 뿐, 한 지점에 다 붙일 수 있는 값이 아님. **보조 지표.**
- **연계불가** = connect_max ≤ 0 (빨간 마커 + 흰 ✕). 신규 연계 불가.
- 데이터는 한전 **추정치**이고 실제 연계는 별도 기술검토 필요 — UI에 이 주의문구가 항상 있어야 함.

---

## 2. 지금 되어 있는 기능 (프론트엔드)

1. **지도**(Leaflet) — 변전소 690개 마커. 색=연계가능MW(초록 많음→노랑→주황→빨강 연계불가), **전 마커 동일 크기(지름 22px)**, 흰테두리+그림자로 시인성 확보, 연계불가는 빨간원+흰✕(최상단).
2. **바탕지도 전환**(우상단) — 일반지도(OSM) / 위성(Esri) / 위성+지명.
3. **마커 팝업** — 변전소명, 연계가능/지역여지, 선로별 연계가능량, 📞 관할 한전지사 직통 연락처(tel 링크), 🏘 공급 읍/면/동 목록.
4. **📍 지번으로 가까운 변전소 찾기** — 지번/주소 입력 → 가까운 변전소 3곳(거리·선로·연계가능·연락처). (Kakao 지오코딩 사용)
5. **🔎 변전소명으로 검색** — 이름으로 변전소+증설계획 검색, 결과에 **지번주소·연계가능·연락처**.
6. **🏗 신설/증설 계획** — 좌측 목록 + 지도 🏗 마커(위치 확실한 것만). 단계 필터(계획확정/사업승인/공사착수).
7. **딥링크** — `#<변전소코드>`(팝업 자동열기), `?find=<주소>`(지번검색 자동실행).
8. **⭕ 이격거리 원 + 드래그 핀** — 지번 검색 시 그 지점에 **반경 100/200/300/500m 원**(기본 200m, 칩 선택) 표시. **`L.circle`(미터 단위)** 사용이라 **줌/축척을 바꿔도 항상 실제 거리 유지**. 중심 핀은 **드래그 가능한 `L.marker`(📍, draggable:true)** — 드래그하면 원(`drag`→`SEP_CIRCLE.setLatLng`)과 가까운 변전소 목록(`dragend`→`showNearest(...,fromDrag=true)`)이 따라 갱신. 원 안 변전소는 "⭕ Nm 이내" 배지. 함수: `drawSepCircle()`,`renderSepChips()`, 전역 `SEP_CIRCLE/SEP_RADIUS/LAST_PT`, `showNearest(lat,lng,label,gu,dong,fromDrag)`.

---

## 3. 아키텍처 & 기술스택

```
[Python 수집 스크립트들]  →  capacity.json / plans.json  →  [git commit/push]  →  [GitHub Pages 정적 호스팅]
     (한전 웹 스크랩)            (데이터 파일)                                         index.html이 JSON을 fetch해서 렌더
```

- **프론트**: 순수 **단일 `index.html`** (별도 빌드 없음). **Leaflet 1.x**(지도) CDN. 프레임워크 없음(바닐라 JS). CSS도 index.html 내부.
- **지도 타일**: OpenStreetMap(기본) + Esri World Imagery(위성). **무료·키 불필요.**
- **데이터**: 정적 JSON 파일(`capacity.json` 약 1.66MB, `plans.json` 약 55KB)을 브라우저가 `fetch`.
- **호스팅**: GitHub Pages(정적). **서버 없음** → 런타임 계산·DB 없음, 모든 건 정적 파일 + 클라이언트 JS.
- **지오코딩**(지번→좌표)만 **Kakao 지도 JS SDK**(브라우저)를 씀. 그 외 지도는 OSM.
- `대시보드_standalone.html` = capacity.json/plans.json을 **내장한 단독 파일**(서버 없이 더블클릭으로 열림). 오프라인 배포용.

---

## 4. 파일 구성

### 프론트엔드
| 파일 | 역할 |
|---|---|
| `index.html` | **대시보드 본체**(HTML+CSS+JS 전부). 라이브 페이지. |
| `capacity.json` | 변전소 690개 데이터(수집 산출물). |
| `plans.json` | 신설/증설 계획 데이터. |
| `대시보드_standalone.html` | 데이터 내장 단독본(`build_standalone.py`가 생성). |

### 데이터 파이프라인(Python, 표준 라이브러리만 사용 — pip 설치 불필요)
| 파일 | 역할 | 실행 순서 |
|---|---|---|
| `collect.py` | 한전에서 전국 변전소·선로 여유용량 수집 → `capacity.json` | 1 |
| `enrich_osm.py` | OSM Overpass로 변전소 **실명+정확좌표** 매칭(571/734) | 2 |
| `merge_dupes.py` | **같은 좌표 중복 변전소 병합**(734→690) | 3 |
| `apply_contacts.py` | 관할 한전지사 **직통 연락처** 대입(`kepco_contacts.json` 사용) | 4 |
| `enrich_addr.py` | 좌표→**지번주소** 역지오코딩(Kakao) → `addr` 필드(686/690) | 5 |
| `plans_collect.py` | 한전 송변전 건설 정보공개에서 증설계획 수집 + `manual_plans.json` 병합 → `plans.json` | 6 |
| `build_standalone.py` | index.html에 데이터 내장 → `대시보드_standalone.html` | 7 |
| `refresh.sh` | 위 1~7 + git push (주1회 자동). **⚠️ Kakao REST 키 포함 → 커밋 금지(.gitignore).** | (자동) |

### 데이터 소스 정의
| 파일 | 역할 |
|---|---|
| `kepco_contacts.json` | DJ가 준 PDF 전사 = 한전 지역별 지사 직통번호(선로확인 담당). |
| `manual_plans.json` | 한전 공개목록에 아직 없는 신설변전소 **수동 등록**(예: 시종변전소). plans_collect가 병합. |
| `*_cache.json` | 지오코딩/OSM/주소/사무소 캐시(재수집 속도↑). |

### 기타
- `update_offices.py` : 지사 위치/배정 갱신용 1회성.
- `capacity_*backup.json`, `capacity_pre_*.json` : 백업(.gitignore).
- 자동갱신: 로컬 **launchd** `~/Library/LaunchAgents/com.happysolar.gridrefresh.plist`(매주 화 06:00 → refresh.sh). *GitHub Actions는 토큰 workflow 스코프 없어 미사용.*

---

## 5. 데이터 소스 & 핵심 트릭 (수집기 이해)

> **모바일 개발자는 보통 수집기를 건드릴 필요 없음**(데이터 JSON만 쓰면 됨). 아래는 데이터가 어떻게 만들어지는지 이해용.

- **한전 엔드포인트**(로그인·키 불필요): `cyber.kepco.co.kr/ckepco/mobile/resources/`
  - 주소 캐스케이드: `resources_search_jibun_list.jsp` (시도→시군구→읍면동)
  - 여유용량 상세: `resources_jibun_detail2_1.jsp` (HTML 안 `viewDetail(...)` 인자들)
- **⚠️ 핵심 트릭**: 상세 엔드포인트는 **세션당 1회만** 데이터 반환 → **요청마다 새 쿠키(fresh session)** 필수(`collect.py`의 `fresh_opener()`).
- **필드 매핑**(viewDetail 인자): pos9/10/11 = 변전소/주변압기/선로 **여유용량(kW)**. connect_max = min(그 셋). subst_free = 변전소 총여유. (pos17-19 G_*는 여유 아님 — 쓰지 말 것.)
- **동別 부분반환**: 한전은 "그 동을 담당하는 선로"만 부분 반환 → 같은 변전소가 동마다 다른(마스킹된) 코드로 쪼개져 저장됨 → `merge_dupes.py`가 **같은 좌표 레코드를 하나로 병합**(선로/공급지 union).
- **변전소 실명**: 한전은 이름을 마스킹(보안시설)함. `enrich_osm.py`가 **OpenStreetMap**의 power=substation과 첫글자+글자수+근접으로 매칭해 실명·정확좌표 복원(571/734). 나머지는 읍면동 근사좌표.
- **증설계획**: `www.kepco.co.kr/.../transstatus/*/boardList.do` (계획확정/사업승인/공사착수). **한계: 상세에 정확 위치·준공연도 없음(첨부PDF만)** → 이름검색(geo=ok)은 오차 커서 **지도엔 신뢰분(geo=exist 기존변전소 증설 / geo=manual 수동)만** 표시.

---

## 6. 데이터 스키마

### capacity.json
```jsonc
{
 "generated_at": "2026-09-03 15:29 KST",
 "source": "...", "unit": "...",
 "branches": [ {"name":"본사(광주)","lat":35.20187,"lng":126.86126}, ... ],  // 지사 핀 7개
 "substations": [ {
   "code": "S136",              // 변전소 코드(딥링크 #S136)
   "name": "신**",              // 한전 마스킹 이름
   "osm_name": "신파주변전소",    // OSM 실명(있으면 이걸 표시). 없을 수 있음
   "region": "고양시",           // 시군구
   "branch": "파주지사",         // 최근접 관할 지사
   "lat": 37.739871, "lng": 126.77118,
   "coord_exact": true,          // true=OSM정확좌표, false=읍면동 근사
   "connect_max_mw": 11.8,       // ★ 연계가능(대표지표). ≤0이면 연계불가(빨강)
   "subst_capa_mw": 200.0,       // 변전소 기준용량
   "subst_free_mw": 187.628,     // 지역여지(총여유)
   "subst_free_pct": 93.8,
   "transformers": [ {"mtr_no":"1","mtr_capa":50.0,"g_mtr":42.507}, ... ],
   "lines": [ {"mtr_no":"1","dl_nm":"한가","dl_capa":12.0,"g_dl":11.776,"conn":11.776}, ... ], // 선로별 conn=연계가능
   "supply": { "고양시 일산동구": ["문봉동","사리현동", ...] },  // 공급 읍면동(시군구별)
   "dong_count": 7,
   "office": { "name":"한전 고양지사", "phone":"031-920-4273", "addr":"경기 고양시 일산동구 장백로 39" }, // 선로확인 문의처
   "addr": "경기 파주시 와동동 1512"  // 변전소 지번주소(역지오코딩, 686/690 보유)
 }, ... ]
}
```

### plans.json
```jsonc
{
 "generated_at":"...", "total":231, "located":39,
 "plans":[ {
   "saup":"345kV 신김해#2S/S 건설사업", "name":"신김해변전소", "voltage":"345kV",
   "stage":"계획확정",           // 계획확정 / 사업승인 / 공사착수(건설중)
   "hq":"남부건설본부", "office":"직할",
   "geo":"exist",               // exist=기존변전소증설(지도표시O) / manual=수동(O) / ok=이름검색(지도표시X, 오차큼) / none=위치미상
   "lat":35.218875, "lng":128.777851,
   "addr":"전남 영암군 시종면 신학리 1244"  // manual 등 일부만
 }, ... ]
}
```
> **지도에 핀 찍는 규칙**: `p.lat && (geo==='exist' || geo==='manual')` 만. 나머지는 목록에 "·위치미상".

---

## 7. index.html 프론트엔드 구조

- **레이아웃**: `header` + `.wrap`(flex) = 좌측 `.side`(패널 420px) + `#map`(나머지). **반응형 @media(max-width:760px)**: 세로 스택(패널 위 / 지도 56vh). ← **모바일에선 이 부분을 대폭 개선 필요**(아래 9장).
- **데이터 로드**: `init(d)` — `capacity.json` fetch(또는 standalone은 `window.__DATA__`). `plans.json`(또는 `window.__PLANS__`).
- **주요 함수**:
  - `render()` — 변전소 마커 그리기(divIcon halo, 연계불가 흰✕).
  - `popup(s)` / `supplyHtml(s)` / `contactHtml(s)` — 팝업 구성.
  - `searchAddr()` / `showNearest()` — 지번검색(Kakao Geocoder, 좌표직접입력 지원).
  - `searchByName()` — 변전소명 검색(변전소+계획, 지번주소 표기).
  - `renderPlans()` — 증설계획 목록/마커/필터.
  - `colorConn(mw)` — 연계가능→색.
- **Kakao 지도 SDK**: `window.KAKAO_KEY`(JS키, index.html에 있음=공개키). 지번검색에만 사용. **도메인 등록 필요**(플랫폼 JS키 SDK 도메인 = 배포 도메인).

---

## 8. 배포

1. 데이터/HTML 수정 → `git add` → `git commit` → `git push`.
2. GitHub Pages가 자동 재빌드(~1분). **빌드가 HEAD 커밋과 일치**해야 라이브 반영됨:
   `gh api repos/chmd20-a11y/grid-capacity-dashboard/pages/builds/latest` 의 commit이 HEAD와 같고 status=built인지 확인.
3. `.nojekyll` 파일 필수(Jekyll 빌드오류 방지).
4. 스크린샷 검증: 크롬 헤드리스(`--headless=new --screenshot`)가 안정적.
5. 커밋 메시지 규칙(원 저장소 관례): 한국어 접두 `feat:`/`fix:`/`data:` 등.

---

## 9. 📱 모바일 개발 가이드 (다음 목표 — 여기가 핵심)

### 현재 모바일 상태 (기반은 있음)
- ✅ `<meta viewport width=device-width>` 있음.
- ✅ 반응형 @media(max-width:760px) 1개 존재: 패널을 지도 위로 세로 스택, 지도 56vh.
- ⚠️ 하지만 **데스크톱 우선 설계**라, 휴대폰에선 좌측 패널(검색·타일·계획목록)이 세로로 길게 쌓여 **지도를 보려면 스크롤**해야 하고, 팝업/컨트롤이 터치에 최적화 안 됨.
- ⚠️ `capacity.json` **1.66MB** — 모바일 셀룰러에서 초기 로딩 부담. 690개 마커 렌더도 부하.

### 모바일화 권장 방향 (우선순위)
1. **지도 우선 풀스크린 레이아웃** — 지도를 화면 전체로, 검색/목록은 **하단 시트(bottom sheet)** 또는 **상단 접이식/탭**으로. 영업직원은 "지도+검색"이 주목적.
2. **검색 UX 모바일화** — 지번검색·변전소명검색을 큰 터치 입력 + 결과를 카드/시트로. 현재 위치(GPS) 기반 "내 주변 변전소" 버튼 추가 고려(geolocation).
3. **팝업 → 하단 시트** — 마커 탭 시 데스크톱 말풍선 대신 하단 디테일 시트(연계가능·선로·연락처 전화 바로걸기).
4. **성능** — (a) capacity.json 경량화/분할(예: 지도상 필요한 필드만 담은 슬림 JSON + 상세는 지연로드), (b) 마커 클러스터링(Leaflet.markercluster) 또는 뷰포트 기반 렌더, (c) gzip(이미 Pages가 압축) 활용.
5. **터치 타깃** — 버튼/칩 최소 44px, 마커 탭 영역 확대.
6. **PWA 고려**(선택) — 오프라인/홈화면 추가. 영업 현장 반복 사용에 유리.
7. **연락처 전화 바로걸기**는 이미 `tel:` 링크로 되어 있음 — 모바일에서 그대로 유효.

### 접근 선택지
- **A. 기존 index.html을 모바일 반응형으로 개선**(권장 시작점): 같은 데이터/함수 재사용, CSS/레이아웃/시트만 모바일화. 가장 빠름.
- **B. 모바일 전용 페이지 신규**(예: `m.html` 또는 별도 모바일 뷰): 데스크톱과 분리. 유지보수 2벌 부담.
- **C. 프레임워크 도입**(React/Vue 등): 오버킬 가능성. 현재 규모(단일 HTML)엔 A가 합리적.
> **DJ 선호**: 대시보드를 **가볍게** 유지(대용량 데이터·과한 복잡도 지양). 모바일도 이 기조 유지 권장.

---

## 10. 로컬 실행 방법

```bash
# 1) 저장소 클론
git clone https://github.com/chmd20-a11y/grid-capacity-dashboard.git
cd grid-capacity-dashboard

# 2) 로컬 미리보기 (index.html은 capacity.json을 fetch하므로 file:// 대신 로컬서버 필요)
python3 -m http.server 8899
#   → http://localhost:8899  접속

# 3) (선택) 데이터 재수집 — 시간 걸림. Kakao REST 키(env) 필요
export KAKAO_REST_KEY="<DJ에게 요청>"   # 지오코딩/주소보강/사무소조회용
python3 collect.py && python3 enrich_osm.py && python3 merge_dupes.py \
  && python3 apply_contacts.py && python3 enrich_addr.py \
  && python3 plans_collect.py && python3 build_standalone.py
```
> 모바일 UI만 개발할 때는 **재수집 불필요** — 기존 `capacity.json`/`plans.json`로 충분.

---

## 11. 함정·주의사항

- **비밀키**: `refresh.sh`는 Kakao **REST 키**를 담고 있어 **절대 커밋 금지**(.gitignore 처리됨). Kakao **JS 키**는 index.html에 있으나 이는 공개 가능(도메인 제한형).
- **Kakao 도메인 등록**: 배포 도메인이 바뀌면(예: 모바일 별도 도메인) Kakao 개발자콘솔 플랫폼 JS키 **SDK 도메인**에 새 도메인 등록해야 지번검색 작동.
- **Pages 반영 지연**: push 후 라이브 반영까지 ~1분. 빌드 commit이 HEAD와 일치하는지 확인(캐시로 이전 데이터 보일 수 있음).
- **좌표 정확도**: 528개 정확(OSM), 162개 읍면동 근사. "가까운 변전소"는 참고지표(한전 실제 배정과 다를 수 있음).
- **증설 geo=ok 부정확**: 이름검색 위치는 오차 커서 지도표시 제외됨(목록만).
- **데이터 변동**: 여유용량은 계속 바뀜 → 주1회 재수집(launchd) 전제.

---

## 12. 보류/향후 (참고)

- **보류(데이터 방대)**: 전주(전신주)번호 조회, 법정리 경계 오버레이 — 데이터가 커서 DJ가 보류. 재요청 시만.
- **여지**: 증설계획 준공연도/신설위치(첨부PDF), 우선순위 점수, 역방향(동→변전소), 변전소 addr의 시도접두("전남광주통합특별시") 정리.

---

### 요약 한 줄
> **정적 GitHub Pages + 바닐라 단일 HTML + 한전 스크랩 JSON** 구조. 데이터는 그대로 두고 **index.html을 모바일(지도 풀스크린 + 하단시트 검색/상세)로 개선**하는 게 다음 작업. DJ 기조 = 가볍게.
