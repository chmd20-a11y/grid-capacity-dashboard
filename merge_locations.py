#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리서치 결과(loc_result_*.json: 산업부 고시 등에서 찾은 신설변전소 위치·준공연도)를
지오코딩(Kakao) → manual_plans.json에 병합 → plans.json에 즉시 주입.
found=true + confidence(high/medium)만 반영. 위치는 최소 시군구+읍면동.
"""
import json, os, glob, time, urllib.parse, urllib.request

SC = "/private/tmp/claude-501/-Users-happysolar-Desktop-02-Claude/13bd2fe2-185f-46a9-bdd0-3cd592819ee6/scratchpad"
KAKAO = os.environ.get("KAKAO_REST_KEY", "")

def geocode(q):
    """주소검색 → 실패 시 키워드검색. (lat,lng,정규화주소) 또는 None."""
    for path in ("address.json", "keyword.json"):
        try:
            url = "https://dapi.kakao.com/v2/local/search/" + path + "?" + urllib.parse.urlencode({"query": q, "size": 1})
            req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + KAKAO})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
            time.sleep(0.05)
            docs = d.get("documents") or []
            if docs:
                doc = docs[0]
                return round(float(doc["y"]), 5), round(float(doc["x"]), 5), doc.get("address_name", q)
        except Exception:
            pass
    return None

def main():
    if not KAKAO:
        print("KAKAO_REST_KEY 필요"); return
    # 1) 결과 취합
    results = []
    for f in sorted(glob.glob(os.path.join(SC, "loc_result_*.json"))):
        try:
            results += json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print("skip", f, e)
    found = [r for r in results if r.get("found") and r.get("location") and r.get("confidence") in ("high", "medium")]
    print(f"결과 {len(results)}건 중 위치확인 {len(found)}건")

    # 2) 지오코딩
    ok = []
    for r in found:
        loc = r["location"].strip()
        g = geocode(loc)
        if not g:  # 지번 떼고 읍면동까지로 재시도
            parts = loc.split()
            if len(parts) > 3:
                g = geocode(" ".join(parts[:4]))
            if not g and len(parts) > 2:
                g = geocode(" ".join(parts[:3]))
        if g:
            r["lat"], r["lng"] = g[0], g[1]
            ok.append(r)
        else:
            print("  지오코딩 실패:", r["name"], "|", loc)
    print(f"지오코딩 성공 {len(ok)}건")

    # 3) manual_plans.json 병합 (name 기준, 기존 수동건 우선 유지)
    mp_path = "manual_plans.json"
    mp = json.load(open(mp_path, encoding="utf-8")) if os.path.exists(mp_path) else {"plans": []}
    existing = {p["name"] for p in mp["plans"]}
    # plans.json에서 stage/전압 등 원본 메타 참조
    pj = json.load(open("plans.json", encoding="utf-8"))
    meta = {p["name"]: p for p in pj["plans"]}
    added = 0
    for r in ok:
        if r["name"] in existing:
            continue
        m = meta.get(r["name"], {})
        entry = {
            "saup": r.get("saup") or m.get("saup", ""),
            "name": r["name"],
            "voltage": m.get("voltage", ""),
            "stage": m.get("stage", ""),
            "hq": m.get("hq", ""),
            "office": m.get("office", ""),
            "lat": r["lat"], "lng": r["lng"],
            "geo": "manual",
            "addr": r["location"],
            "note": f"출처: {r.get('source','')} ({r.get('confidence','')})",
        }
        if r.get("completion"):
            entry["completion"] = str(r["completion"])[:4]
        mp["plans"].append(entry)
        existing.add(r["name"])
        added += 1
    json.dump(mp, open(mp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"manual_plans.json: +{added}건 (총 {len(mp['plans'])}건)")

    # 4) plans.json 즉시 주입 (기존 항목이면 위치·준공만 업데이트, 없으면 추가)
    byname = {p["name"]: p for p in pj["plans"]}
    upd = new = 0
    for e in mp["plans"]:
        if e["name"] in byname:
            p = byname[e["name"]]
            if p.get("geo") not in ("manual",):  # exist는 유지? → 수동(지번확인)이 더 정확하므로 덮되 exist 좌표보다 상세
                p.update({k: e[k] for k in ("lat", "lng", "geo", "addr") if k in e})
            if e.get("completion"): p["completion"] = e["completion"]
            if e.get("note"): p["note"] = e["note"]
            upd += 1
        else:
            pj["plans"].append(e); new += 1
    pj["total"] = len(pj["plans"])
    pj["located"] = sum(1 for p in pj["plans"] if p.get("lat") and p.get("geo") in ("exist", "manual"))
    json.dump(pj, open("plans.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"plans.json: 갱신 {upd}·신규 {new} → 신뢰 위치 {pj['located']}건 / 전체 {pj['total']}건")

if __name__ == "__main__":
    main()
