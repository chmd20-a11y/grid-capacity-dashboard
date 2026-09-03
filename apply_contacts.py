#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capacity.json의 각 변전소에 '관할 한전지사 직통(선로확인) 연락처'를 대입.
소스: kepco_contacts.json (한전 지역별 담당자 연락처 PDF 전사).
매칭: region(시군구) → 지사 직통. 폴백: 시도 지역본부. 최종: 123.
"""
import json, re, os

C = json.load(open("kepco_contacts.json", encoding="utf-8"))
JISA, HQ, ALIAS, DUP = C["jisa"], C["hq"], C["alias"], C["dup_by_sido"]

def sido_key(s):
    o = s.get("office") or {}
    addr = (o.get("addr") or "").strip()
    tok = addr.split(" ")[0] if addr else ""
    if not tok: return ""
    if tok.startswith("강원"): return "강원"
    if tok.startswith("충청북"): return "충북"
    if tok.startswith("충청남"): return "충남"
    if tok.startswith("전북") or tok.startswith("전라북"): return "전북"
    if tok.startswith("전라남") or tok.startswith("전남광주"): return "전남"
    if tok.startswith("전남"): return "전남"
    if tok.startswith("경상북"): return "경북"
    if tok.startswith("경상남"): return "경남"
    if tok.startswith("제주"): return "제주"
    for k in ["경기","서울","부산","대구","인천","광주","대전","울산","세종"]:
        if tok.startswith(k): return k
    return ""

def stem(region):
    r = re.sub(r"(특별자치시|특별자치도|광역시|특별시)$", "", region)
    r = re.sub(r"(시|군|구)$", "", r)
    return r

def resolve(region, sido):
    st = stem(region)
    # 동명 지사 중복(고성 등) → 시도로 구분
    for key in (region, st):
        if key in DUP:
            ph = DUP[key].get(sido)
            if ph: return ("한전 " + key + "지사", ph)
    for k in (region, st, ALIAS.get(region), ALIAS.get(st)):
        if k and k in JISA:
            return ("한전 " + k + "지사", JISA[k])
    if sido and sido in HQ:
        nm = "한전 고객센터" if HQ[sido] == "123" else "한전 " + sido + "지역본부"
        return (nm, HQ[sido])
    return ("한전 고객센터", "123")

def main():
    d = json.load(open("capacity.json", encoding="utf-8"))
    matched = 0
    for s in d["substations"]:
        sido = sido_key(s)
        name, phone = resolve(s.get("region",""), sido)
        s["office"] = {"name": name, "phone": phone, "addr": (s.get("office") or {}).get("addr","")}
        if phone != "123": matched += 1
    json.dump(d, open("capacity.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"연락처 대입: {matched}/{len(d['substations'])}개 직통번호 (나머지 123)")
    from collections import Counter
    c = Counter(s["office"]["name"] for s in d["substations"])
    print("예시:", dict(list(c.items())[:10]))

if __name__ == "__main__":
    main()
