#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSM(OpenStreetMap)에서 변전소 실명+정확좌표를 가져와 capacity.json에 매칭.
- 매칭키: 마스킹 첫글자 + 글자수(마스크 길이) + 근접좌표(읍면동 근사).
- 무료·오픈데이터. 매칭 실패분은 기존(마스킹명·근사좌표) 유지.
출력: capacity.json 갱신(osm_name, coord_exact, lat/lng), osm_cache.json 캐시.
"""
import json, urllib.request, urllib.parse, time, math, os

OVERPASS = "https://overpass-api.de/api/interpreter"
CACHE = "osm_cache.json"

# 우리 region(시군구) → OSM 조회 행정구역명
REGION_AREA = {
    "광산구":"광주광역시","남구":"광주광역시","동구":"광주광역시","북구":"광주광역시","서구":"광주광역시",
    "영암군":"영암군","장흥군":"장흥군","해남군":"해남군","파주시":"파주시","평택시":"평택시","강화군":"강화군",
}
EXTRA_AREAS = ["김포시"]  # 강화 인접(통진 등)

def haversine(a,b):
    R=6371;p=math.pi/180
    return 2*R*math.asin(math.sqrt(math.sin((b[0]-a[0])*p/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin((b[1]-a[1])*p/2)**2))

def overpass_area(area):
    q=f'''[out:json][timeout:60];
area["name"="{area}"][boundary=administrative]->.a;
(node["power"="substation"](area.a);way["power"="substation"](area.a);relation["power"="substation"](area.a););
out center tags;'''
    req=urllib.request.Request(OVERPASS,data=urllib.parse.urlencode({"data":q}).encode(),
        headers={"User-Agent":"happysolar-grid-dashboard/1.0 (chmd20@gmail.com)"})
    out=[]
    try:
        d=json.loads(urllib.request.urlopen(req,timeout=90).read().decode())
        for e in d.get("elements",[]):
            t=e.get("tags",{}); nm=t.get("name")
            lat=e.get("lat") or (e.get("center") or {}).get("lat")
            lon=e.get("lon") or (e.get("center") or {}).get("lon")
            if nm and lat and lon:
                out.append({"name":nm,"lat":round(lat,6),"lng":round(lon,6),"volt":t.get("voltage","")})
    except Exception as ex:
        print("  overpass err",area,ex)
    return out

def base_name(osm_name):
    return osm_name.replace("변전소","").replace("변환소","").strip()

def main():
    d=json.load(open("capacity.json",encoding="utf-8"))
    subs=d["substations"]

    # 1) OSM 변전소 수집 (지역별, 캐시)
    cache=json.load(open(CACHE,encoding="utf-8")) if os.path.exists(CACHE) else {}
    areas=sorted(set(REGION_AREA.get(s["region"], s["region"]) for s in subs) | set(EXTRA_AREAS))
    osm=[]
    for ar in areas:
        if ar in cache:
            osm+=cache[ar]; continue
        print("OSM 조회:",ar)
        res=overpass_area(ar); cache[ar]=res; osm+=res
        json.dump(cache,open(CACHE,"w",encoding="utf-8"),ensure_ascii=False)
        time.sleep(2.5)
    # dedup
    seen=set(); uniq=[]
    for o in osm:
        k=(o["name"],o["lat"],o["lng"])
        if k not in seen: seen.add(k); uniq.append(o)
    osm=uniq
    print(f"OSM 변전소 총 {len(osm)}개 (지역 {len(areas)})")

    # 2) 매칭
    matched=0
    for s in subs:
        m=s["name"]  # 마스킹명 예: 구*, 서**, 송*
        first=m[0]; mlen=len(m)  # 마스크 문자열 길이 = 원명 글자수
        cur=[s["lat"],s["lng"]]
        cands=[]
        for o in osm:
            b=base_name(o["name"])
            if b and b[0]==first and len(b)==mlen:
                cands.append((haversine(cur,[o["lat"],o["lng"]]),o))
        # 첫글자+길이 매칭 후보 중 최근접. 후보 없으면 첫글자만으로 근접(느슨) 재시도
        if not cands:
            for o in osm:
                b=base_name(o["name"])
                if b and b[0]==first:
                    cands.append((haversine(cur,[o["lat"],o["lng"]]),o))
        if cands:
            cands.sort(key=lambda x:x[0])
            dist,o=cands[0]
            if dist<=25:  # 25km 이내만 신뢰
                s["osm_name"]=o["name"]; s["lat"]=o["lat"]; s["lng"]=o["lng"]
                s["coord_exact"]=True; s["match_km"]=round(dist,1); matched+=1
                continue
        s["coord_exact"]=False

    # 3) 좌표 바뀌었으니 최근접 지사 재계산
    offices=[(b["name"],[b["lat"],b["lng"]]) for b in d["branches"]]
    for s in subs:
        s["branch"]=min(offices,key=lambda o:haversine([s["lat"],s["lng"]],o[1]))[0]

    d["unit"]=d["unit"].replace("좌표=읍면동 지오코딩 평균","좌표=OSM 실측(매칭분)+읍면동근사(미매칭)")
    json.dump(d,open("capacity.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print(f"\n=== 매칭 완료: {matched}/{len(subs)}개 실명+정확좌표 ===")
    for s in subs:
        tag="✅"+s.get("osm_name","") if s.get("coord_exact") else "🔸근사"
        print(f"  {s['region']:5s} {s['name']:4s}{s['code']:5s} {tag}")

if __name__=="__main__":
    main()
