# 용량/여유 재구성: 한전 OPEN API 원본(openapi_cache.json)으로 capacity.json의
#   subst_free_mw(여유)·subst_capa_mw(기준)·connect_max_mw(연계가능)·lines·transformers 를 권위값으로 덮어씀.
# 좌표/공급지/연락처/주소/이름은 기존 유지. fetch_openapi.py 먼저 실행(캐시 생성) 필요.
#
# 규칙(검증 결론 2026-09-08):
#  - 변전소 여유 = "최다 모선(bus)의 vol1"  (다중모선일 때 주력모선. re100=한전과 94% 일치)
#  - 기준용량   = 그 모선 접수(substPwr) + vol1  (연계 기준용량; 물리 nameplate가 아닌 연계가능 총량)
#  - 선로 연계가능(conn) = min(vol1,vol2,vol3)/1000   · connect_max = 선로 최대 conn
#  - 웹수집의 유령 DL(다른 변전소 선로 오병합) 제거 → API DL만 사용
import json, collections, sys

def num(x):
    try: return float(x)
    except: return 0.0

def main():
    cache = json.load(open('openapi_cache.json'))
    data = json.load(open('capacity.json'))
    subs = data['substations']
    changed = 0; skipped = []; big_shift = []
    for s in subs:
        cd = str(s['code'])
        rows = cache.get(cd)
        if not isinstance(rows, list) or not rows:
            skipped.append((cd, s.get('name'))); continue
        # 최다 모선 vol1
        vcnt = collections.Counter(r.get('vol1') for r in rows if r.get('vol1') is not None)
        if not vcnt:
            skipped.append((cd, s.get('name'))); continue
        dom_vol1 = vcnt.most_common(1)[0][0]
        dom_rows = [r for r in rows if r.get('vol1') == dom_vol1]
        substPwr = num(dom_rows[0].get('substPwr'))
        subst_free = dom_vol1 / 1000.0
        subst_capa = (substPwr + dom_vol1) / 1000.0
        # 선로(DL): (mtrNo,dlNm) 유니크, conn=min(vol1,vol2,vol3)
        lines = []; conns = []; seen = set()
        for r in rows:
            v1 = num(r.get('vol1')); v2 = num(r.get('vol2')); v3 = num(r.get('vol3'))
            conn = min(v1, v2, v3) / 1000.0
            conns.append(conn)
            key = (r.get('mtrNo'), r.get('dlNm'))
            if key in seen: continue
            seen.add(key)
            lines.append({'mtr_no': r.get('mtrNo'), 'dl_nm': r.get('dlNm'),
                          'dl_capa': round((num(r.get('dlPwr')) + v3) / 1000.0, 3),
                          'g_dl': round(v3 / 1000.0, 3), 'conn': round(conn, 3)})
        connect_max = round(max(conns), 3) if conns else 0.0
        # 불변식: 변전소 여유 ≥ 연계가능(어떤 선로든 그 모선에 최소 그만큼 여유가 있음).
        # 주력모선이 만차인데 타 모선 선로에 여유가 있는 드문 경우 교정.
        if connect_max > subst_free:
            subst_free = connect_max
        if subst_capa < subst_free:
            subst_capa = subst_free
        # 주변압기: mtrNo 유니크, vol2=여유, mtr_capa=접수+vol2
        trans = {}
        for r in rows:
            mtr = r.get('mtrNo')
            if mtr in trans: continue
            v2 = num(r.get('vol2'))
            trans[mtr] = {'mtr_no': mtr, 'mtr_capa': round((num(r.get('mtrPwr')) + v2) / 1000.0, 3),
                          'g_mtr': round(v2 / 1000.0, 3)}
        old_free = s.get('subst_free_mw')
        if old_free is not None and abs(old_free - subst_free) > 5:
            big_shift.append((s.get('name'), cd, round(old_free, 1), round(subst_free, 1)))
        s['subst_free_mw'] = round(subst_free, 3)
        s['subst_capa_mw'] = round(subst_capa, 1)
        s['subst_free_pct'] = round(subst_free / subst_capa * 100, 1) if subst_capa > 0 else 0
        s['connect_max_mw'] = connect_max
        s['lines'] = lines
        s['transformers'] = list(trans.values())
        s['bus_count'] = len(set(r.get('vol1') for r in rows))
        changed += 1
    data['source'] = '한전 bigdata.kepco.co.kr OPEN API 분산전원연계정보 (substCd 조회, 권위값)'
    data['unit'] = ('MW · 여유=변전소 최다모선 여유(vol1) · 기준용량=접수+여유 · '
                    '연계가능=선로별 min(변전소/주변압기/선로 여유) · 좌표=OSM/지오코딩')
    json.dump(data, open('capacity.json', 'w'), ensure_ascii=False)
    print(f"재구성 완료: {changed}곳 갱신 · 스킵(캐시없음) {len(skipped)}곳")
    if skipped: print("  스킵:", skipped[:20])
    print(f"\n여유 5MW+ 변동(부풀림 교정) {len(big_shift)}곳 · 큰 순 상위 25:")
    for nm, cd, o, n in sorted(big_shift, key=lambda x: -(x[2] - x[3]))[:25]:
        print(f"  {nm}({cd}): {o} → {n} MW ({o - n:+.1f})")

if __name__ == '__main__':
    main()
