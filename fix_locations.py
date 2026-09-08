# 위치 교정: 우리 좌표가 re100 좌표와 3km+ 어긋난 변전소만, 두 좌표를 각각 역지오코딩해
#   '변전소 실명이 주소(시군구+읍면동)와 일치하는 쪽'을 채택(자가검증). 애매하면 flag.
# 원인: enrich_osm이 옛 마스킹명으로 OSM 오매칭(사리→사직) + 일부 지오코딩 폴백 오류.
# env KAKAO_REST_KEY 필요. re100_summary.json 경로 인자.
import json, os, sys, math, time, urllib.request, urllib.parse

KAKAO = os.environ.get("KAKAO_REST_KEY")
RE100 = sys.argv[1] if len(sys.argv) > 1 else "re100_summary.json"

def hav(a, b):
    R = 6371; p = math.pi/180
    dlat = (b[0]-a[0])*p; dlon = (b[1]-a[1])*p
    x = math.sin(dlat/2)**2 + math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(x))

_cache = {}
def revgeo(lat, lng):
    key = f"{lat:.5f},{lng:.5f}"
    if key in _cache: return _cache[key]
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?" + urllib.parse.urlencode({"x": lng, "y": lat})
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {KAKAO}"})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
            docs = d.get("documents", [])
            b = next((x for x in docs if x.get("region_type") == "B"), docs[0] if docs else None)
            r = (b.get("region_1depth_name","")+" "+b.get("region_2depth_name","")+" "+b.get("region_3depth_name","")) if b else ""
            _cache[key] = r.strip(); return _cache[key]
        except Exception:
            time.sleep(1)
    _cache[key] = None; return None

def core(x): return (x or "").replace("변전소","").replace("SA","").replace("BTB","").replace(" ","").strip()

def consistent(name, addr):
    """변전소 실명이 주소와 지명 일치하나(이름토큰이 주소에, 혹은 읍면동 어근이 이름에)"""
    if not addr: return False
    c = core(name)
    if not c: return False
    # 이름(2~3자)이 주소에 등장
    if len(c) >= 2 and c in addr.replace(" ",""): return True
    # 이름 앞 2자 or 뒤 2자
    for frag in {c[:2], c[-2:]}:
        if len(frag) == 2 and frag in addr.replace(" ",""): return True
    return False

def main():
    data = json.load(open('capacity.json'))
    subs = data['substations']
    their = {str(s['code']): s for s in json.load(open(RE100))['substations']}
    fixed=[]; flagged=[]; kept=[]; noref=[]
    for s in subs:
        t = their.get(str(s['code']))
        if not t or t.get('lat') is None:
            noref.append(s['name']); continue
        d = hav((s['lat'], s['lng']), (t['lat'], t['lng']))
        if d < 3:  # 이미 일치
            continue
        our_addr = revgeo(s['lat'], s['lng'])
        re_addr  = revgeo(t['lat'], t['lng'])
        our_ok = consistent(s['name'], our_addr)
        re_ok  = consistent(s['name'], re_addr)
        if our_ok and not re_ok:
            kept.append((s['name'], round(d,1), our_addr)); continue  # 우리가 맞음(re100 stale/오류)
        if re_ok and not our_ok:
            s['lat'] = round(t['lat'],6); s['lng'] = round(t['lng'],6)
            s['coord_exact'] = True; s['coord_src'] = 're100_verified'
            fixed.append((s['name'], round(d,1), our_addr, '→', re_addr)); continue
        # 둘 다 일치 or 둘 다 불일치 → 애매. 이름토큰이 주소에 나오는 re100쪽 우선 채택 조건부
        if re_ok and our_ok:
            # 둘 다 이름과 맞음(드묾) → 우리 유지
            kept.append((s['name'], round(d,1), 'both_ok')); continue
        flagged.append((s['name'], str(s['code']), round(d,1), f"우리[{our_addr}]", f"re100[{re_addr}]"))
    json.dump(data, open('capacity.json','w'), ensure_ascii=False)
    print(f"위치 교정: {len(fixed)}곳 수정(re100 검증좌표 채택) · 우리유지 {len(kept)}곳 · 애매(수동확인) {len(flagged)}곳 · re100없음 {len(noref)}곳")
    print("\n[수정됨] 실명·거리·우리주소→re100주소:")
    for nm,d,oa,arw,ra in fixed: print(f"  {nm} {d}km: {oa} → {ra}")
    if kept:
        print("\n[우리 유지](우리 좌표가 이름과 일치, re100이 오히려 다름):")
        for x in kept[:15]: print("  ", x)
    if flagged:
        print("\n[애매-수동확인 필요](둘 다 이름불일치):")
        for nm,cd,d,oa,ra in flagged: print(f"  {nm}({cd}) {d}km · {oa} · {ra}")

if __name__ == '__main__':
    main()
