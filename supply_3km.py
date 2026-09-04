#!/usr/bin/env python3
"""공급 읍/면/동을 변전소 기준 반경 3km로 필터링해 capacity.json에 supply3 필드로 저장.

- 각 읍면동 좌표는 기존 geocode_cache.json 재사용 (키 "시도 시군구 동" → [lat,lng]).
  캐시 키 형식이 섞여있어(시도 전체/축약, 구있는시는 구 생략) (시,동)으로 정규화해 매칭.
- 3km 이내 읍면동만 supply3에 유지. 3km 안에 하나도 없으면 가장 가까운 1개만 표시(빈칸 방지) + supply3_far=True.
- 원본 supply(전체)는 그대로 보존(지번검색 등에서 사용). 팝업 표시만 supply3 사용.
- refresh.sh 파이프라인에서 enrich_addr 다음·build 전에 실행(재수집 후에도 유지).
"""
import json, math, re

RADIUS_KM = 3.0
CAP = "capacity.json"
GEO = "geocode_cache.json"

SIDO = {"서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주",
        "서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시","울산광역시","세종특별자치시",
        "경기도","강원도","강원특별자치도","충청북도","충청남도","전라북도","전북특별자치도","전라남도",
        "경상북도","경상남도","제주특별자치도","제주도"}

def norm_key(k):
    t = k.split()
    if t and t[0] in SIDO: t = t[1:]
    if not t: return None
    dong = t[-1]; si = None
    for x in t[:-1]:
        if x.endswith("시") or x.endswith("군"): si = x; break
    if si is None and len(t) >= 2: si = t[0]
    return (si, dong)

def si_of(area):
    for x in area.split():
        if x.endswith("시") or x.endswith("군"): return x
    return area.split()[0] if area.split() else area

def strip_num(dn):  # 기산1동 -> 기산동, 중앙로2가 -> 중앙로가
    return re.sub(r'(\d+)(동|가)$', r'\2', dn)

def hav(a, b):
    R = 6371; p = math.pi/180
    dlat = (b[0]-a[0])*p; dlng = (b[1]-a[1])*p
    x = math.sin(dlat/2)**2 + math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlng/2)**2
    return 2*R*math.asin(math.sqrt(x))

def main():
    cache = json.load(open(GEO, encoding="utf-8"))
    idx = {}
    for k, v in cache.items():
        if v:
            nk = norm_key(k)
            if nk: idx[nk] = v
    def coord(si, dn):
        return idx.get((si, dn)) or idx.get((si, strip_num(dn)))

    d = json.load(open(CAP, encoding="utf-8"))
    subs = d["substations"]
    kept = far = nocoord = empty = fb = 0
    for s in subs:
        sup = s.get("supply") or {}
        cand = []           # (area, dong, dist)
        for area, dongs in sup.items():
            si = si_of(area)
            for dn in dongs:
                c = coord(si, dn)
                if not c: nocoord += 1; continue
                cand.append((area, dn, hav([s["lat"], s["lng"]], c)))
        within = [(a, dn) for a, dn, dist in cand if dist <= RADIUS_KM]
        s.pop("supply3_far", None)
        if within:
            s3 = {}
            for a, dn in within: s3.setdefault(a, []).append(dn)
            for a in s3: s3[a] = sorted(set(s3[a]))
            s["supply3"] = {a: s3[a] for a in sorted(s3)}
            kept += sum(len(v) for v in s3.values())
            far += sum(1 for _, _, dist in cand if dist > RADIUS_KM)
        elif cand:
            a, dn, _ = min(cand, key=lambda t: t[2])   # 3km 안에 없으면 최근접 1개
            s["supply3"] = {a: [dn]}
            s["supply3_far"] = True
            fb += 1; far += len(cand) - 1
        else:
            s["supply3"] = {}
            empty += 1

    json.dump(d, open(CAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[supply_3km] 반경 {RADIUS_KM}km · 유지 {kept}동 · 3km초과 {far} · 좌표없음 {nocoord}")
    print(f"[supply_3km] 최근접1개 폴백 {fb}개 변전소 · 공급동 자체가 없거나 좌표전무 {empty}개")

if __name__ == "__main__":
    main()
