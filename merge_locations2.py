#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고시 PDF·웹검색으로 찾은 신설변전소 위치(loc_result_gosi.json / loc_result_web*.json)를
지오코딩(Kakao) → manual_plans.json 병합 → plans.json 주입(중복명 전부 반영).
found=true + confidence(high/medium)만 반영.
merge_locations.py의 개선판: 괄호·'일원'·'내' 등 정리 후 지오코딩, 동일명 중복 항목까지 좌표 전파.
"""
import json, os, glob, re, time, urllib.parse, urllib.request

SC = "/private/tmp/claude-501/-Users-happysolar-Desktop-02-Claude/13bd2fe2-185f-46a9-bdd0-3cd592819ee6/scratchpad"
KAKAO = os.environ.get("KAKAO_REST_KEY", "")

def clean(loc):
    """지오코딩용 핵심 주소로 정리."""
    s = re.sub(r'\(.*?\)', '', loc)          # 괄호 설명 제거
    s = s.split('·')[0].split(',')[0]        # 첫 지점만
    s = re.sub(r'(일원|일대|내|부지|신도시|국제도시)\s*$', '', s.strip())
    return s.strip()

def geocode(q):
    for path in ("address.json", "keyword.json"):
        try:
            url = "https://dapi.kakao.com/v2/local/search/" + path + "?" + urllib.parse.urlencode({"query": q, "size": 1})
            req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + KAKAO})
            d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
            time.sleep(0.05)
            docs = d.get("documents") or []
            if docs:
                doc = docs[0]
                return round(float(doc["y"]), 5), round(float(doc["x"]), 5)
        except Exception:
            pass
    return None

def geocode_robust(loc):
    core = clean(loc)
    for q in (core, " ".join(core.split()[:4]), " ".join(core.split()[:3])):
        g = geocode(q)
        if g:
            return g
    return None

def main():
    if not KAKAO:
        print("KAKAO_REST_KEY 필요"); return
    results = []
    for f in sorted(glob.glob(os.path.join(SC, "loc_result_gosi.json"))) + sorted(glob.glob(os.path.join(SC, "loc_result_web*.json"))):
        try:
            results += json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print("skip", f, e)
    found = [r for r in results if r.get("found") and r.get("location") and r.get("confidence") in ("high", "medium")]
    # 이름 dedup (high 우선)
    best = {}
    for r in found:
        n = r["name"]
        if n not in best or (r["confidence"] == "high" and best[n]["confidence"] != "high"):
            best[n] = r
    found = list(best.values())
    print(f"채택 대상 {len(found)}건 (dedup 후)")

    ok = []
    for r in found:
        g = geocode_robust(r["location"])
        if g:
            r["lat"], r["lng"] = g
            ok.append(r)
        else:
            print("  지오코딩 실패:", r["name"], "|", r["location"])
    print(f"지오코딩 성공 {len(ok)}건")

    # manual_plans.json 병합 (기존 수동건 유지)
    mp_path = "manual_plans.json"
    mp = json.load(open(mp_path, encoding="utf-8"))
    existing = {p["name"] for p in mp["plans"]}
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
        existing.add(r["name"]); added += 1
    json.dump(mp, open(mp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"manual_plans.json: +{added}건 (총 {len(mp['plans'])}건)")

    # plans.json 주입 — 동일명 '모든' 항목에 좌표 전파
    byname = {}
    for p in pj["plans"]:
        byname.setdefault(p["name"], []).append(p)
    upd = new = 0
    for e in mp["plans"]:
        if e["name"] in byname:
            for p in byname[e["name"]]:
                if p.get("geo") != "manual":
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
