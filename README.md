# ⚡ 계통 여유용량 영업 대시보드 (해피솔라)

변전소별 **계통 여유용량**(태양광을 얼마나 더 연계할 수 있는가)을 지도로 보여주고,
여유용량을 근거로 **월별 영업 캠페인 지역**을 자동 배정하는 내부 영업 도구.

- **라이브**: (배포 후 GitHub Pages URL)
- **로컬**: `/Users/happysolar/Desktop/02_Claude/grid-capacity-dashboard`

## 무엇을 보여주나
- **지도**(Leaflet + OpenStreetMap): 변전소를 원으로 표시 — 색 = 변전소 여유율, 크기 = 여유용량(MW). 클릭 시 배전선로별 **실제 연계가능량**(변전소·주변압기·선로 여유의 최솟값).
- **6개 지사 + 강화(신규타겟)** 위치 핀, 각 변전소는 **최근접 지사**에 배정.
- **월별 캠페인 캘린더**: 권역별 총 여유용량이 큰 순서로 이른 달에 자동 배정 → "9월엔 A권역, 11월엔 B권역" 근거 제공.
- **변전소 여유용량 랭킹** 표(클릭 시 지도 이동).

## 데이터 소스
한국전력공사 **분산형전원 계통연계 조회**(`cyber.kepco.co.kr`)의 공개 엔드포인트.
로그인·API키 불필요. 값은 re100market과 교차검증 완료.
- 여유용량 = `viewDetail` 인자 vol1/vol2/vol3(변전소/주변압기/배전선로), 단위 kW→MW.
- 좌표: 변전소가 걸린 읍면동을 **OSM Nominatim**으로 지오코딩한 평균값(`geocode_cache.json` 캐시).

## 데이터 갱신 (여유용량은 계속 변합니다)
```bash
python3 collect.py          # 한전 재수집 + 읍면동 지오코딩 → capacity.json (~8분)
python3 enrich_osm.py       # OSM에서 변전소 실명+정확좌표 매칭 (~30초)
python3 build_standalone.py # 데이터 내장 단독 HTML 재생성 (선택)
git add -A && git commit -m "data refresh" && git push   # 배포(Pages 자동 재빌드)
```
(로컬 `refresh.sh` + launchd가 매주 화 06시 위 과정을 자동 실행)
- `geocode_cache.json`은 커밋해 두어 재실행 시 지오코딩을 건너뜁니다(새 읍면동만 조회).
- 자동 갱신: `.github/workflows/refresh.yml`(주 1회) — 첫 실행에서 한전이 GitHub IP를 막지 않는지 확인 필요. 막히면 로컬 cron 사용.

## 현재 범위 / 한계
- **범위**: 본사(광주)·영암·장흥·해남·파주·평택 6개 지사권역 + 강화도. (전국 확장은 `BRANCHES`에 권역 추가로 가능)
- 변전소명은 한전이 마스킹(예: `구*`) → 코드(subst_cd)로 식별.
- 좌표는 읍면동 지오코딩 평균(변전소 정확 지점 아님, 인근).

## 파일
- `collect.py` — 수집기(한전 스크레이프 + 지오코딩 + 최근접지사 배정)
- `index.html` — 대시보드(capacity.json 로드)
- `capacity.json` — 산출 데이터
- `geocode_cache.json` — 읍면동 좌표 캐시
- `대시보드_standalone.html` — 서버 없이 열리는 데이터 내장본
