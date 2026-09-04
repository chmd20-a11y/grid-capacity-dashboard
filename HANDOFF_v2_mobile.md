# 모바일 UI 인수인계 (v2) — Fork 기반

> 원본 `HANDOFF.md` 를 이어받아 모바일 UI 작업을 완료한 상태입니다. 이 문서 하나로 재현 · 배포 가능합니다.
> **재현 방식**: 아래 §3 의 fork 저장소에서 `mobile-ui` 브랜치를 pull 하면 로컬에 코드가 자동 반영됩니다. (파일 첨부 · 코드 복붙 불필요)

---

## 1. 개요

- **무엇**: `HANDOFF.md` §9 (모바일화 권장 방향) 진행 · 접근 A (기존 index.html 반응형 개선) 채택.
- **결과**: 데스크톱 UI 는 그대로. 모바일(≤760px) 에선 지도 풀스크린 + 좌측 슬라이드 드로어 + iOS 스타일 컴포넌트로 전환.
- **바뀐 파일**: `index.html` (수정), `mobile_prototype.html` (신규, 개발자용 뷰어).
- **한 커밋** 으로 정리: `d5a14aa feat: 모바일 뷰 지원(좌측 드로어 토글)·지도중심 대한민국 재정렬`.

---

## 2. 지금 되어 있는 기능 (모바일)

- 지도 풀스크린 (`.side` 는 좌측 슬라이드 드로어)
- 좌상단 ☰ 토글 → 드로어 오픈 · 백드롭·×·지도탭 3가지 닫기
- 📡 GPS "내 주변 변전소 찾기" (드로어 최상단 · `navigator.geolocation`)
- 검색 탭 통합 (지번 ↔ 변전소명 하나의 탭 UI · 세로공간 절약)
- iOS 토글 스위치 (`지도에 표시` 체크박스 대체)
- iOS 세그먼트 컨트롤 (계획 필터 4단 균등 폭)
- 접기 legend (`숫자 읽는 법`, `범례` — `<details>` 기본 접힘)
- 지도 초기 중심 남한 지리중심 이동 + fitBounds 자동 조정
- iOS safe-area 대응 (헤더 아일랜드/노치 아래로 자동 밀림)
- Leaflet 컨트롤 다크 테마 재스킨 (데스크톱·모바일 공통)
- 마커 팝업은 기본 Leaflet 유지 (데스크톱과 코드 동일 · 유지보수 이득)

---

## 3. 재현 방법

### 사전 조건
- `chmd20-a11y/grid-capacity-dashboard` 저장소 로컬 clone 있음 (원저자면 이미 있을 것)
- git · Python 3

### 명령
```bash
cd grid-capacity-dashboard

# 모바일 UI 브랜치를 fork 저장소에서 pull
git remote add mobile https://github.com/yooona12/grid-capacity-dashboard.git
git fetch mobile mobile-ui

# 방식 A: 로컬에서 확인만 (main 병합 X)
git checkout -b mobile-ui mobile/mobile-ui
python3 -m http.server 8901
# → http://127.0.0.1:8901/mobile_prototype.html    (프레임 안 실동작 미리보기)
# → http://127.0.0.1:8901/index.html                (원본 · DevTools 모바일 뷰)

# 방식 B: main 에 병합 후 배포
git checkout main
git merge mobile/mobile-ui        # fast-forward or 3-way merge (충돌시 해결)
git push origin main              # GitHub Pages 자동 재빌드
```

### 검증
`https://chmd20-a11y.github.io/grid-capacity-dashboard/` 배포 ~1분 후 반영:
```bash
gh api repos/chmd20-a11y/grid-capacity-dashboard/pages/builds/latest | grep -E '"commit"|"status"'
# commit == HEAD  &&  status == "built"  확인
```

---

## 4. 파일 변경

| 파일 | 상태 | 요지 |
|---|---|---|
| `index.html` | 수정 | 모바일 CSS (@media ≤760px), 드로어 · 토글 · GPS · 세그먼트 · 접기 legend, Leaflet 다크 재스킨, safe-area, `initSearchTabs / initGpsButton / initMobileDrawer` JS |
| `mobile_prototype.html` | 신규 | 개발자용 iPhone 프레임 뷰어 (기기 프리셋 5종 · safe-area 시뮬레이션 · 회전) |
| `capacity.json`, `plans.json` | 무변경 | 데이터 스키마 그대로 |
| Python 수집기 · JSON 캐시 | 무변경 | |

---

## 5. 아키텍처 · 결정 배경 (원본 HANDOFF §9 대비)

- 접근 A (반응형 개선) 채택 — 프레임워크 없이 단일 HTML. DJ "가볍게" 기조.
- **하단 시트 (bottom sheet) 폐기 · 좌측 드로어 채택** — 사이드바 콘텐츠 재활용 (한 벌 유지). 시트 방식은 마커상세·검색·목록 각각 별도 렌더 필요해 코드 중복 컸음.
- **마커 팝업 기본 Leaflet 유지** — 시트 폐기와 함께 popup 우회 로직도 제거. 데스크톱·모바일 코드 갈래 하나.
- **계획 필터: 세그먼트 컨트롤 최종안** — 초기 pill(2줄 wrap) → 세그먼트로 정착. `width:100%; box-sizing:border-box` 강제로 X축 전폭.

---

## 6. 알려진 이슈

### 6.1 Kakao 지오코딩 — 로컬 개발 한정
- Kakao JS 키 (`3c003211be49659008929069de83dced`) 는 프로덕션 `chmd20-a11y.github.io` 에만 등록됨.
- 로컬 (`127.0.0.1`, `localhost`) 에선 SDK 로드 거부 → 지번검색 ⚠ 문구.
- 해결: Kakao 개발자콘솔 → 플랫폼 → Web 사이트 도메인에 로컬 URL 추가, 또는 프로덕션에서 테스트.
- 좌표 직접입력 (`37.5, 127.0`) 은 Kakao 없이도 작동.

### 6.2 성능 (미착수)
- `capacity.json` 1.66MB — 셀룰러 초기 로딩 부담. 슬림화 미착수.
- 마커 690개 클러스터링 미도입. 저사양 안드로이드 스크롤 렉 가능.

### 6.3 헤더 meta
- 모바일에서 `#meta` (생성 타임스탬프) hide → 헤더 3줄 wrap 방지. 데스크톱은 노출.

---

## 7. 실기기 검증 체크리스트 (배포 후)

- [ ] iPhone Safari · Android Chrome 실기기 접속
- [ ] 헤더 타이틀 아일랜드/노치 아래로 밀려서 다 보이나
- [ ] ☰ 탭 → 드로어 슬라이드 자연스러운가
- [ ] 백드롭·×·지도탭 3가지 다 닫힘 트리거
- [ ] 📡 GPS 위치 권한 팝업 → 허용 → 결과 카드
- [ ] 검색 탭 스위치 · input 포커스 시 키보드
- [ ] 📖 📗 접기/펼치기
- [ ] 토글 스위치 슬라이드 애니메이션
- [ ] 세그먼트 컨트롤 4단 잘림 없음 (기종별)
- [ ] `tel:` 실전화 걸림
- [ ] 로드 초기 지도 = 남한 전체 시야

---

## 8. 다음 우선순위 (Nice-to-have)

- **Nominatim (OSM 지오코딩) fallback** — Kakao SDK 미로드 시 자동 fallback → 로컬 개발 편의 + 프로덕션 안전망
- **capacity.json 슬림화** — 지도용 필드만 담은 슬림 JSON + 마커 클릭 시 상세 lazy load
- **최근 검색 3개 (localStorage)** — 영업 반복 사용 패턴
- **PWA (홈화면 추가)** — manifest + service worker
- **마커 클러스터링** — Leaflet.markercluster (저사양 대응)

---

### 요약
> Fork 저장소 `yooona12/grid-capacity-dashboard` 의 `mobile-ui` 브랜치를 pull → 확인/병합 → `chmd20-a11y/main` 으로 push. **한 커밋 (d5a14aa)** 안에 모바일 UI 전부 · 데이터·파이프라인 무변경.
