# 위치 교정 2차: 1차에서 '애매'였던 곳을 region 필드(한전 조회지역=신뢰) 대조로 재판정.
# 여전히 >3km 어긋난 곳만: 우리·re100 좌표 각각 역지오코딩 → region(시/군/구)과 일치하는 쪽 채택.
import json, os, sys, math, time, urllib.request, urllib.parse
KAKAO = os.environ.get("KAKAO_REST_KEY")
RE100 = sys.argv[1] if len(sys.argv) > 1 else "re100_summary.json"

def hav(a, b):
    R=6371;p=math.pi/180;dlat=(b[0]-a[0])*p;dlon=(b[1]-a[1])*p
    x=math.sin(dlat/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(x))

_c={}
def revgeo(lat,lng):
    k=f"{lat:.5f},{lng:.5f}"
    if k in _c: return _c[k]
    url="https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?"+urllib.parse.urlencode({"x":lng,"y":lat})
    for _ in range(3):
        try:
            req=urllib.request.Request(url,headers={"Authorization":f"KakaoAK {KAKAO}"})
            d=json.loads(urllib.request.urlopen(req,timeout=15).read().decode("utf-8"))
            docs=d.get("documents",[]); b=next((x for x in docs if x.get("region_type")=="B"),docs[0] if docs else None)
            _c[k]=(b.get("region_1depth_name",""),b.get("region_2depth_name",""),b.get("region_3depth_name","")) if b else None
            return _c[k]
        except Exception: time.sleep(1)
    _c[k]=None; return None

def core(x): return (x or "").replace("변전소","").replace("SA","").replace("BTB","").replace(" ","").strip()

def region_match(region, rg):
    """region 필드(용인시/괴산군/동구)가 역지오코딩 (시도,시군구,읍면동)과 일치?"""
    if not rg: return False
    si1,si2,dong=rg
    full=(si1+" "+si2).replace(" ","")
    r=region.strip()
    # 시/군: 접미어 떼고 매칭
    base=r[:-1] if r[-1:] in "시군" else r
    if r[-1:] in "시군":
        return base in full
    # 구: 구명 그대로 시군구에 포함 (동구/남구 등)
    if r.endswith("구"):
        return r in si2 or r in full
    return base in full

def name_match(name, rg):
    if not rg: return False
    c=core(name); addr=("".join(rg))
    if len(c)>=2 and c in addr: return True
    for f in {c[:2],c[-2:]}:
        if len(f)==2 and f in addr: return True
    return False

def main():
    data=json.load(open('capacity.json')); subs=data['substations']
    their={str(s['code']):s for s in json.load(open(RE100))['substations']}
    fixed=[]; kept=[]; flag=[]
    for s in subs:
        if s.get('coord_src')=='re100_verified': continue  # 1차 확정
        t=their.get(str(s['code']))
        if not t or t.get('lat') is None: continue
        if hav((s['lat'],s['lng']),(t['lat'],t['lng']))<3: continue  # 이미 일치
        our=revgeo(s['lat'],s['lng']); re=revgeo(t['lat'],t['lng'])
        reg=s.get('region','')
        our_ok=region_match(reg,our) or name_match(s['name'],our)
        re_ok =region_match(reg,re)  or name_match(s['name'],re)
        if re_ok and not our_ok:
            s['lat']=round(t['lat'],6); s['lng']=round(t['lng'],6); s['coord_exact']=True; s['coord_src']='re100_verified'
            fixed.append((s['name'],s.get('region'),our,re))
        elif our_ok and not re_ok:
            kept.append((s['name'],s.get('region')))
        else:
            flag.append((s['name'],str(s['code']),s.get('region'),our,re))
    json.dump(data,open('capacity.json','w'),ensure_ascii=False)
    print(f"2차 위치 교정: {len(fixed)}곳 추가수정 · 우리유지 {len(kept)}곳 · 남은애매 {len(flag)}곳")
    print("\n[추가수정] 실명(region): 우리→re100")
    for nm,rg,o,r in fixed: print(f"  {nm}({rg}): {o}→{r}")
    print("\n[여전히 애매-수동] 실명(region) 우리 / re100")
    for nm,cd,rg,o,r in flag: print(f"  {nm}({cd},{rg}): 우리{o} · re100{r}")

if __name__=='__main__': main()
