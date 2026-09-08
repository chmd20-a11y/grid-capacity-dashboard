# 누락 변전소 보강: aug243_cache(한전 OPEN API)+aug243_meta(re100 좌표/이름) → 레코드 생성.
# 한전 분산전원 데이터 있는 곳만 추가(여유/선로 표시 가능). 좌표=re100(검증), 주소/지역=역지오코딩.
# capacity.json에 stub 추가 + openapi_cache 병합 → 이후 rebuild_capacity가 용량 채움, apply_contacts가 지사 배정.
import json,os,sys,time,urllib.request,urllib.parse
KAKAO=os.environ["KAKAO_REST_KEY"]
SCR=sys.argv[1]
cache=json.load(open(SCR+"/aug243_cache.json"))
meta=json.load(open(SCR+"/aug243_meta.json"))
gc={}
gcf=SCR+"/aug_geocache.json"
if os.path.exists(gcf): gc=json.load(open(gcf))
def revgeo(lat,lng):
    k=f"{lat:.5f},{lng:.5f}"
    if k in gc: return gc[k]
    # 지역
    u1="https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?"+urllib.parse.urlencode({"x":lng,"y":lat})
    u2="https://dapi.kakao.com/v2/local/geo/coord2address.json?"+urllib.parse.urlencode({"x":lng,"y":lat})
    reg=addr=None
    for u,kind in [(u1,'reg'),(u2,'addr')]:
        for _ in range(3):
            try:
                req=urllib.request.Request(u,headers={"Authorization":f"KakaoAK {KAKAO}"})
                d=json.loads(urllib.request.urlopen(req,timeout=15).read().decode("utf-8"))
                docs=d.get("documents",[])
                if kind=='reg':
                    b=next((x for x in docs if x.get("region_type")=="B"),docs[0] if docs else None)
                    if b: reg=(b["region_1depth_name"],b["region_2depth_name"])
                else:
                    if docs:
                        a=docs[0].get("address") or {}
                        addr=(a.get("region_1depth_name","")+" "+a.get("region_2depth_name","")+" "+a.get("region_3depth_name","")+" "+a.get("main_address_no","")+("-"+a.get("sub_address_no") if a.get("sub_address_no") else "")).strip()
                break
            except: time.sleep(1)
    gc[k]=(reg,addr); return gc[k]
def region_field(reg):
    if not reg: return None
    d1,d2=reg
    metros=("서울","부산","대구","인천","광주","대전","울산","세종")
    if d1.startswith(metros): return d2  # 광역시 → 구
    # 도: 2depth가 "성남시 분당구"면 시만
    return d2.split(" ")[0] if " " in d2 else d2
cur=json.load(open('capacity.json')); subs=cur['substations']
existing=set(str(s['code']) for s in subs)
opcache=json.load(open('openapi_cache.json'))
added=0; nodata=[]; skipped=0
for cd,rows in cache.items():
    if cd in existing: skipped+=1; continue
    if not isinstance(rows,list) or not rows: nodata.append(cd); continue
    m=meta.get(cd,{})
    if not m.get('lat'): nodata.append(cd); continue
    lat,lng=m['lat'],m['lng']
    reg,addr=revgeo(lat,lng)
    name=rows[0].get('substNm') or m.get('name') or cd
    rec={'code':cd,'name':name,'region':region_field(reg) or (m.get('addr','').split(' ')[1] if m.get('addr') else ''),
         'lat':round(lat,6),'lng':round(lng,6),'addr':addr or m.get('addr'),
         'osm_name':None,'coord_exact':True,'coord_src':'augmented_re100','geocoded':True,
         'supply':{}, 'supply3':{}, 'augmented':True}
    subs.append(rec)
    opcache[cd]=rows  # rebuild_capacity가 채우도록 병합
    added+=1
json.dump(cur,open('capacity.json','w'),ensure_ascii=False)
json.dump(opcache,open('openapi_cache.json','w'),ensure_ascii=False)
json.dump(gc,open(gcf,'w'),ensure_ascii=False)
print(f"보강: {added}곳 추가 · 한전데이터 없음(제외) {len(nodata)}곳 · 이미존재 {skipped}곳")
print("데이터없음 코드:",nodata[:40])
