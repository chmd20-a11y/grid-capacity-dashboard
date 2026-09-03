#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
같은 좌표에 겹친 변전소 레코드 병합.
원인: KEPCO가 '동(洞)'별로 조회하면 그 동을 담당하는 선로만 부분적으로 내려줌.
      → 같은 변전소가 동마다 다른(마스킹된) 코드로 쪼개져 저장되고,
        enrich_osm이 같은 이름을 같은 OSM 좌표에 붙이면서 마커가 겹쳐 보임.
해결: 동일 좌표 레코드를 하나로 합침(선로·변압기·공급지 union), connect_max 재계산.
※ enrich_osm(좌표부여) 다음, apply_contacts(연락처) 이전에 실행.
"""
import json, os
from collections import defaultdict

SRC = "capacity.json"

def key(s):
    return (round(s["lat"], 6), round(s["lng"], 6))

def unmasked(name):
    return name and "*" not in name

def merge_group(group):
    # 기준 레코드: 선로 수 최다(가장 완전) → 그 코드/좌표/지사 유지
    base = max(group, key=lambda s: len(s.get("lines", [])))
    m = dict(base)

    # 실명(비마스킹) 우선
    for s in group:
        if not unmasked(m.get("name")) and unmasked(s.get("name")):
            m["name"] = s["name"]
    # osm_name은 그룹 공통이지만 혹시 빈 경우 채움
    for s in group:
        if not m.get("osm_name") and s.get("osm_name"):
            m["osm_name"] = s["osm_name"]

    # 선로 union: (mtr_no, dl_nm) 기준 중복 제거, conn 최대값 유지
    lines = {}
    for s in group:
        for l in s.get("lines", []):
            k = (l.get("mtr_no"), l.get("dl_nm"))
            if k not in lines or (l.get("conn", 0) or 0) > (lines[k].get("conn", 0) or 0):
                lines[k] = l
    m["lines"] = sorted(lines.values(), key=lambda l: -(l.get("conn", 0) or 0))

    # 변압기 union: mtr_no 기준
    trans = {}
    for s in group:
        for t in s.get("transformers", []):
            trans.setdefault(t.get("mtr_no"), t)
    m["transformers"] = list(trans.values())

    # 공급지 union: region key별 동 합치기(순서 유지, 중복 제거)
    supply = defaultdict(list)
    for s in group:
        for reg, dongs in (s.get("supply") or {}).items():
            for d in dongs:
                if d not in supply[reg]:
                    supply[reg].append(d)
    if supply:
        m["supply"] = {k: v for k, v in supply.items()}

    # 변전소 총여유·용량은 최댓값(가장 완전한 판독)
    m["subst_free_mw"] = max((s.get("subst_free_mw") or 0) for s in group)
    m["subst_capa_mw"] = max((s.get("subst_capa_mw") or 0) for s in group)
    # 연계가능 = 병합 선로의 최대 conn
    m["connect_max_mw"] = max((l.get("conn", 0) or 0) for l in m["lines"]) if m["lines"] else 0.0

    m["merged_from"] = sorted(s["code"] for s in group)
    return m

def main():
    d = json.load(open(SRC, encoding="utf-8"))
    subs = d["substations"]
    groups = defaultdict(list)
    for s in subs:
        groups[key(s)].append(s)

    out = []
    merged_spots = 0
    absorbed = 0
    for k, g in groups.items():
        if len(g) == 1:
            out.append(g[0])
        else:
            out.append(merge_group(g))
            merged_spots += 1
            absorbed += len(g) - 1

    d["substations"] = out
    json.dump(d, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"병합: {merged_spots}곳 → 변전소 {len(subs)}개에서 {len(out)}개로 (흡수 {absorbed}개)")

if __name__ == "__main__":
    main()
