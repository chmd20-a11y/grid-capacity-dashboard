#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
변전소 좌표 → 지번주소 역지오코딩(Kakao coord2address). capacity.json에 addr 필드 추가.
※ enrich_osm/merge_dupes(좌표 확정) 이후 실행. coord_exact=False(읍면동 근사)는 주소도 근사임.
"""
import json, os, time, urllib.parse, urllib.request

SRC = "capacity.json"
CACHE = "addr_cache.json"
KAKAO_REST = os.environ.get("KAKAO_REST_KEY", "")

def coord2addr(lat, lng, cache):
    key = f"{lat},{lng}"
    if key in cache:
        return cache[key]
    res = {"addr": "", "road": ""}
    if KAKAO_REST:
        try:
            url = "https://dapi.kakao.com/v2/local/geo/coord2address.json?" + urllib.parse.urlencode({"x": lng, "y": lat})
            req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + KAKAO_REST})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
            time.sleep(0.04)
            docs = d.get("documents") or []
            if docs:
                a = docs[0].get("address") or {}
                r = docs[0].get("road_address") or {}
                res = {"addr": a.get("address_name", ""), "road": (r or {}).get("address_name", "")}
        except Exception:
            pass
    cache[key] = res
    return res

def main():
    if not KAKAO_REST:
        print("KAKAO_REST_KEY 없음 — 주소 보강 건너뜀")
        return
    d = json.load(open(SRC, encoding="utf-8"))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    subs = d["substations"]
    ok = 0
    for i, s in enumerate(subs):
        r = coord2addr(s["lat"], s["lng"], cache)
        if r["addr"]:
            s["addr"] = r["addr"]
            if r["road"]:
                s["road_addr"] = r["road"]
            ok += 1
        if i % 40 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(d, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"주소 보강: {ok}/{len(subs)}개 (지번주소)")

if __name__ == "__main__":
    main()
