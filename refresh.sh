#!/bin/zsh
# 주1회 자동 갱신: 한전 재수집 → 단독HTML 재생성 → 커밋/푸시 (launchd에서 호출)
cd /Users/happysolar/Desktop/02_Claude/grid-capacity-dashboard || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
export KAKAO_REST_KEY="1348cbc5b08ff5659f6987ef39a41a10"   # 지오코딩/지사조회용(로컬 전용, 미커밋)
LOG=refresh_cron.log
echo "===== $(date) 시작 =====" >> "$LOG"
python3 collect.py >> "$LOG" 2>&1 || { echo "collect 실패" >> "$LOG"; exit 1; }
python3 enrich_osm.py >> "$LOG" 2>&1   # OSM 실명+정확좌표 매칭
python3 merge_dupes.py >> "$LOG" 2>&1   # 같은 좌표 중복 변전소 병합(동별 분할 복원)
python3 apply_contacts.py >> "$LOG" 2>&1   # 관할 한전지사 직통 연락처 대입
python3 plans_collect.py >> "$LOG" 2>&1     # 신설/증설 계획 수집(plans.json)
python3 build_standalone.py >> "$LOG" 2>&1
git add capacity.json geocode_cache.json osm_cache.json office_cache.json kepco_contacts.json plans.json plan_geo_cache.json 대시보드_standalone.html
if git diff --cached --quiet; then
  echo "변경 없음" >> "$LOG"
else
  git -c user.name="happysolar" -c user.email="chmd20@gmail.com" \
    commit -m "chore: 여유용량 데이터 자동 갱신 $(date +%F)" >> "$LOG" 2>&1
  git push >> "$LOG" 2>&1 && echo "푸시 완료" >> "$LOG"
fi
echo "===== $(date) 종료 =====" >> "$LOG"
