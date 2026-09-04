#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주소 시도 접두어 정규화. 카카오 역지오코딩이 뱉는 이상/장문 라벨을 표준 단축형으로.
 - '전남광주통합특별시' → 두번째 토큰이 광주 자치구면 '광주', 아니면 '전남'
 - 전북특별자치도/강원특별자치도/제주특별자치도/세종특별자치시 → 전북/강원/제주/세종
capacity.json(addr·road_addr·office.addr)·plans.json(addr)에 적용. 재실행 안전(멱등)."""
import json

GWANGJU_GU = {"광산구", "북구", "남구", "서구", "동구"}
SIDO_LONG = {"전북특별자치도": "전북", "강원특별자치도": "강원",
             "제주특별자치도": "제주", "세종특별자치시": "세종"}

def fix(a):
    if not a:
        return a
    toks = a.split(" ")
    p = toks[0]
    if p == "전남광주통합특별시":
        newp = "광주" if len(toks) > 1 and toks[1] in GWANGJU_GU else "전남"
        return " ".join([newp] + toks[1:])
    if p in SIDO_LONG:
        return " ".join([SIDO_LONG[p]] + toks[1:])
    return a

def main():
    n = 0
    cap = json.load(open("capacity.json", encoding="utf-8"))
    for s in cap["substations"]:
        for k in ("addr", "road_addr"):
            if s.get(k):
                nv = fix(s[k])
                if nv != s[k]:
                    s[k] = nv; n += 1
        o = s.get("office")
        if o and o.get("addr"):
            nv = fix(o["addr"])
            if nv != o["addr"]:
                o["addr"] = nv; n += 1
    json.dump(cap, open("capacity.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    pj = json.load(open("plans.json", encoding="utf-8"))
    for p in pj["plans"]:
        if p.get("addr"):
            nv = fix(p["addr"])
            if nv != p["addr"]:
                p["addr"] = nv; n += 1
    json.dump(pj, open("plans.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"정규화 완료: {n}건 수정")

if __name__ == "__main__":
    main()
