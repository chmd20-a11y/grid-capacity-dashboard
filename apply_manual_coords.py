# 위치 수동교정 오버레이: manual_coords.json(코드→검증좌표)을 capacity.json에 덮어씀.
# enrich_osm의 마스킹명 오매칭으로 깨진 좌표를 재수집 후에도 유지. (fix_locations 결과 고정본)
import json
try: mc=json.load(open('manual_coords.json'))
except FileNotFoundError: mc={}
d=json.load(open('capacity.json')); n=0
for s in d['substations']:
    c=mc.get(str(s['code']))
    if c:
        s['lat']=c['lat']; s['lng']=c['lng']; s['coord_exact']=True; s['coord_src']='manual_verified'; n+=1
json.dump(d,open('capacity.json','w'),ensure_ascii=False)
print(f"apply_manual_coords: {n}곳 좌표 고정 적용")
