#!/usr/bin/env python3
# 변전소 실명 적용: 한전 「분산전원연계정보」 API를 변전소코드(substCd)로 조회해 substNm(실명)을
# capacity.json의 마스킹명(예 '송*')에 덮어씀. 커버리지는 웹수집(collect)이 담당, 이름만 API로 보강.
# refresh.sh: merge_dupes 다음(코드 확정 후)·apply_contacts 전에 실행. 키(KEPCO_API_KEY) 없으면 건너뜀.
import os, json, urllib.request, urllib.parse, time

KEY = os.environ.get("KEPCO_API_KEY", "")
BASE = "https://bigdata.kepco.co.kr/openapi/v1/dispersedGeneration.do"
CACHE = "realname_cache.json"

def realname(cd, cache):
    if cd in cache:
        return cache[cd]
    nm = None
    for _ in range(4):
        try:
            p = {"apiKey": KEY, "returnType": "json", "substCd": cd}
            req = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(p),
                                         headers={"User-Agent": "Mozilla/5.0"})
            d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace"))
            for r in d.get("data", []):
                if str(r.get("substCd")) == cd and r.get("substNm"):
                    nm = r["substNm"]; break
            break
        except Exception:
            time.sleep(0.4)
    cache[cd] = nm
    return nm

def main():
    if not KEY:
        print("[realnames] KEPCO_API_KEY 없음 — 실명 적용 건너뜀"); return
    d = json.load(open("capacity.json", encoding="utf-8"))
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    applied = miss = 0
    for i, s in enumerate(d["substations"]):
        if "*" not in str(s.get("name", "")):
            continue                       # 이미 실명
        nm = realname(s["code"], cache)
        if nm:
            s["name"] = nm; applied += 1
        else:
            miss += 1
        if i % 50 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(d, open("capacity.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[realnames] 실명 적용 {applied} · 미확인 {miss} / 총 {len(d['substations'])}")

if __name__ == "__main__":
    main()
