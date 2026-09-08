# 전 변전소 substCd로 한전 OPEN API 분산전원연계정보 원본 수집 → openapi_cache.json
# 여유용량 재구성(rebuild_capacity.py)의 권위 원본. 키=os.environ KEPCO_API_KEY.
import os,json,urllib.request,urllib.parse,time,sys
KEY=os.environ.get("KEPCO_API_KEY")
BASE="https://bigdata.kepco.co.kr/openapi/v1/dispersedGeneration.do"
def q(cd,tries=6):
    for i in range(tries):
        try:
            p={"apiKey":KEY,"returnType":"json","substCd":cd}
            req=urllib.request.Request(BASE+"?"+urllib.parse.urlencode(p),headers={"User-Agent":"Mozilla/5.0"})
            d=json.loads(urllib.request.urlopen(req,timeout=50).read().decode("utf-8","replace"))
            rows=d.get("data") if isinstance(d,dict) else d
            if isinstance(d,dict) and not rows:
                for v in d.values():
                    if isinstance(v,list): rows=v;break
            return rows or []
        except Exception as e:
            if i==tries-1: return {"_err":str(e)}
            time.sleep(2+i)
def main():
    codes=[str(s['code']) for s in json.load(open('capacity.json'))['substations']]
    cache={}
    cf="openapi_cache.json"
    if os.path.exists(cf):
        try: cache=json.load(open(cf))
        except: cache={}
    done=0
    for i,cd in enumerate(codes):
        if cd in cache and not (isinstance(cache[cd],dict) and cache[cd].get("_err")):
            continue
        r=q(cd); cache[cd]=r
        done+=1
        if done%10==0:
            json.dump(cache,open(cf,"w"),ensure_ascii=False)
            ok=sum(1 for v in cache.values() if isinstance(v,list))
            print(f"{i+1}/{len(codes)} 저장 · 성공 {ok} · 방금 {cd}={'행'+str(len(r)) if isinstance(r,list) else r}",flush=True)
    json.dump(cache,open(cf,"w"),ensure_ascii=False)
    ok=sum(1 for v in cache.values() if isinstance(v,list))
    err=[k for k,v in cache.items() if isinstance(v,dict) and v.get("_err")]
    print(f"DONE · 총 {len(codes)} · 성공 {ok} · 실패 {len(err)} {err[:10]}",flush=True)
main()
