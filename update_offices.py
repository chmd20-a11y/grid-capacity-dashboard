#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capacity.json의 지사(핀) 목록을 collect.OFFICES(7개)로 갱신하고,
각 변전소 branch를 최근접 지사로 재배정. (전남동부권/전북권 제거 반영)"""
import json
from collect import OFFICES, haversine

d = json.load(open("capacity.json", encoding="utf-8"))
d["branches"] = [{"name":o["name"],"lat":o["lat"],"lng":o["lng"]} for o in OFFICES]
for s in d["substations"]:
    s["branch"] = min(OFFICES, key=lambda o: haversine([s["lat"],s["lng"]],[o["lat"],o["lng"]]))["name"]
json.dump(d, open("capacity.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print("지사 핀:", [o["name"] for o in OFFICES])
print("배정:", dict(Counter(s["branch"] for s in d["substations"])))
