# 재수집 복원: aug_substations.json(누락 보강분 시드)을 capacity.json에 stub으로 추가.
# collect.py가 691로 덮어쓴 뒤 실행 → fetch_openapi/rebuild_capacity가 용량 채움. refresh.sh: fetch_openapi 前.
import json,os
try: seed=json.load(open('aug_substations.json'))
except FileNotFoundError: seed=[]
d=json.load(open('capacity.json')); subs=d['substations']
exist=set(str(s['code']) for s in subs); n=0
for a in seed:
    if str(a['code']) in exist: continue
    subs.append({'code':a['code'],'name':a['name'],'region':a.get('region'),
                 'lat':a['lat'],'lng':a['lng'],'addr':a.get('addr'),
                 'osm_name':None,'coord_exact':True,'coord_src':'augmented_re100',
                 'geocoded':True,'supply':{}, 'supply3':{}, 'augmented':True}); n+=1
json.dump(d,open('capacity.json','w'),ensure_ascii=False)
print(f"apply_augment: {n}곳 보강 stub 복원(총 {len(subs)})")
