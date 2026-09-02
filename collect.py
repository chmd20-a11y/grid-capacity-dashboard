#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한전 계통 여유용량 수집기 (프로토타입: 6개 지사 권역) — v2 정밀좌표
소스: cyber.kepco.co.kr (로그인·키 없이 작동)
 - 읍면동 목록:  resources_search_jibun_list.jsp
 - 변전소/선로 여유용량: resources_jibun_detail2_1.jsp (HTML, viewDetail 인자)
여유용량 = viewDetail 인자 pos9/10/11 (vol1=변전소, vol2=주변압기, vol3=선로), 단위 kW.
좌표: 변전소가 걸린 읍면동을 OSM Nominatim으로 지오코딩 → 평균(정밀). 지사=최근접.
"""
import json, re, time, urllib.parse, urllib.request, http.cookiejar, hashlib, math, os
from collections import Counter
from datetime import datetime, timezone, timedelta

BASE = "https://cyber.kepco.co.kr/ckepco/mobile/resources"
REF = BASE + "/resources_search2.jsp"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
GEO_UA = "happysolar-grid-dashboard/1.0 (contact chmd20@gmail.com)"
GEO_CACHE = "geocode_cache.json"
SHORTDO = {"광주광역시":"광주","인천광역시":"인천","경기도":"경기","전라남도":"전남",
           "서울특별시":"서울","부산광역시":"부산","대구광역시":"대구","대전광역시":"대전",
           "울산광역시":"울산","세종특별자치시":"세종","경상남도":"경남","경상북도":"경북",
           "충청남도":"충남","충청북도":"충북","전북특별자치도":"전북","강원특별자치도":"강원","제주특별자치도":"제주"}

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def _get(url, params, op=None):
    op = op or opener
    qs = urllib.parse.urlencode(params, encoding="utf-8")
    req = urllib.request.Request(url + "?" + qs, headers={
        "User-Agent": UA, "Referer": REF, "X-Requested-With": "XMLHttpRequest", "Accept": "*/*"})
    with op.open(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def warm():
    opener.open(urllib.request.Request(REF, headers={"User-Agent": UA}), timeout=30).read()

def fresh_opener():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(REF, headers={"User-Agent": UA}), timeout=30).read()
    return op

def list_addr(target, do="", si="", gu="", lidong=""):
    try:
        d = json.loads(_get(BASE + "/resources_search_jibun_list.jsp",
            {"addr": target, "addr_do": do, "addr_si": si, "addr_gu": gu, "addr_lidong": lidong}))
        return d.get("addrList", []) if d.get("status") == "true" else []
    except Exception as e:
        print("  list err:", e); return []

VD = re.compile(r"viewDetail\(([^)]*)\)")
ARG = re.compile(r"'([^']*)'")

def fetch_detail(do, si, gu, lidong, tries=4):
    for t in range(tries):
        try:
            op = fresh_opener()   # detail은 세션당 1회만 유효 → 매번 새 세션
            html = _get(BASE + "/resources_jibun_detail2_1.jsp",
                {"addr_do": do, "addr_si": si, "addr_gu": gu,
                 "addr_lidong": lidong, "addr_li": "", "addr_jibun": ""}, op=op)
        except Exception:
            time.sleep(0.6); continue
        rows = [ARG.findall(m.group(1)) for m in VD.finditer(html)]
        rows = [a for a in rows if len(a) >= 20]
        if rows:
            return rows
        time.sleep(0.4)
    return []

def to_mw(x):
    try: return round(int(x) / 1000.0, 3)
    except: return 0.0

def haversine(a, b):
    R=6371; p=math.pi/180
    dlat=(b[0]-a[0])*p; dlng=(b[1]-a[1])*p
    x=math.sin(dlat/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlng/2)**2
    return 2*R*math.asin(math.sqrt(x))

# ---- 지오코딩 (OSM Nominatim, 캐시) ----
def load_cache():
    if os.path.exists(GEO_CACHE):
        try: return json.load(open(GEO_CACHE, encoding="utf-8"))
        except: return {}
    return {}
def save_cache(c): json.dump(c, open(GEO_CACHE,"w",encoding="utf-8"), ensure_ascii=False)

def _nomi(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "countrycodes": "kr", "limit": 1}, encoding="utf-8")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": GEO_UA, "Accept-Language": "ko"})
        data = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8"))
        time.sleep(1.1)   # Nominatim 정책 준수
        if data: return [round(float(data[0]["lat"]),5), round(float(data[0]["lon"]),5)]
    except Exception:
        time.sleep(1.1)
    return None

def geocode(addr, cache):
    """addr = '광주 남구 봉선동' 형식. 실패 시 '군구 읍면동'로 폴백."""
    if addr in cache: return cache[addr]
    res = _nomi(addr)
    if res is None:
        parts = addr.split(" ", 1)
        if len(parts) == 2: res = _nomi(parts[1])
    cache[addr] = res
    return res

BRANCHES = [
    {"name":"본사(광주)","office":[35.1595,126.8526],"do":"광주광역시","si":"-기타지역","gus":["광산구","남구","동구","북구","서구"]},
    {"name":"영암지사","office":[34.8000,126.6970],"do":"전라남도","si":"-기타지역","gus":["영암군"]},
    {"name":"장흥지사","office":[34.6814,126.9070],"do":"전라남도","si":"-기타지역","gus":["장흥군"]},
    {"name":"해남사업소","office":[34.5730,126.5990],"do":"전라남도","si":"-기타지역","gus":["해남군"]},
    {"name":"파주지사","office":[37.7600,126.7800],"do":"경기도","si":"파주시","gus":[""]},
    {"name":"평택지사","office":[36.9920,127.1130],"do":"경기도","si":"평택시","gus":[""]},
    {"name":"강화사업소","office":[37.7470,126.4850],"do":"인천광역시","si":"-기타지역","gus":["강화군"]},
]
CENTROID = {  # 지오코딩 실패 시 폴백
    "광산구":[35.139,126.793],"남구":[35.133,126.902],"동구":[35.146,126.923],
    "북구":[35.174,126.912],"서구":[35.152,126.890],
    "영암군":[34.800,126.697],"장흥군":[34.681,126.907],"해남군":[34.573,126.599],
    "파주시":[37.760,126.780],"평택시":[36.992,127.113],"강화군":[37.720,126.460],
}
def jit(code, base, span=0.006):
    h=int(hashlib.md5(code.encode()).hexdigest(),16)
    return [round(base[0]+(((h//1000)%1000)/1000-0.5)*span,5),
            round(base[1]+((h%1000)/1000-0.5)*span,5)]

def main():
    warm()
    subs = {}
    for br in BRANCHES:
        do, si = br["do"], br["si"]
        for gu in br["gus"]:
            if do == "경기도":
                dongs = list_addr("addr_gu", do, si, "", ""); region = si
            else:
                dongs = list_addr("addr_lidong", do, si, gu, ""); region = gu
            dongs = [d for d in dongs if d and d not in ("Unknown","-기타지역")]
            print(f"[{br['name']}] {region}: 읍면동 {len(dongs)}개")
            for dong in dongs:
                gu_param = gu if do != "경기도" else ""
                rows = fetch_detail(do, si, gu_param, dong)
                addr_str = f"{SHORTDO.get(do,do)} {region} {dong}"
                found = 0
                for a in rows:
                    subst_cd = a[12]
                    if not subst_cd: continue
                    r = subs.get(subst_cd)
                    if not r:
                        r = {"code":subst_cd,"nm":a[0],"subst_capa":to_mw(a[14]),
                             "g_subst":to_mw(a[9]),"transformers":{},"lines":{},
                             "addrs":Counter(),"regions":Counter()}
                        subs[subst_cd] = r
                    r["subst_capa"]=max(r["subst_capa"],to_mw(a[14]))
                    r["g_subst"]=max(r["g_subst"],to_mw(a[9]))
                    r["addrs"][addr_str]+=1; r["regions"][region]+=1
                    r["transformers"][a[1]]={"mtr_no":a[1],"mtr_capa":to_mw(a[15]),"g_mtr":to_mw(a[10])}
                    conn=min(to_mw(a[9]),to_mw(a[10]),to_mw(a[11]))
                    r["lines"][f"{a[1]}|{a[2]}|{a[13]}"]={"mtr_no":a[1],"dl_nm":a[2],
                        "dl_capa":to_mw(a[16]),"g_dl":to_mw(a[11]),"conn":round(conn,3)}
                    found+=1
                if found: print(f"    {dong}: {found}")
                time.sleep(0.1)

    # ---- 지오코딩 ----
    cache = load_cache()
    uniq = sorted({a for r in subs.values() for a in r["addrs"]})
    print(f"\n[지오코딩] 고유 읍면동 {len(uniq)}개 (캐시 {sum(1 for a in uniq if a in cache)}개)")
    for i,a in enumerate(uniq):
        if a not in cache:
            geocode(a, cache)
            if i%20==0: save_cache(cache); print(f"  ...{i}/{len(uniq)}")
    save_cache(cache)
    ok=sum(1 for a in uniq if cache.get(a)); print(f"[지오코딩] 성공 {ok}/{len(uniq)}")

    # ---- 정리: 좌표(읍면동 평균)+최근접 지사+권역 ----
    offices=[(b["name"],b["office"]) for b in BRANCHES]
    out=[]
    for cd,r in subs.items():
        pts=[cache[a] for a in r["addrs"] if cache.get(a)]
        if pts:
            lat=round(sum(p[0] for p in pts)/len(pts),5); lng=round(sum(p[1] for p in pts)/len(pts),5)
        else:
            base=CENTROID.get(r["regions"].most_common(1)[0][0],[35.1,126.9]); lat,lng=jit(cd,base)
        region=r["regions"].most_common(1)[0][0]
        branch=min(offices,key=lambda o:haversine([lat,lng],o[1]))[0]
        lines=list(r["lines"].values())
        out.append({"code":cd,"name":r["nm"],"region":region,"branch":branch,
            "lat":lat,"lng":lng,"subst_capa_mw":r["subst_capa"],"subst_free_mw":r["g_subst"],
            "subst_free_pct":round(100.0*r["g_subst"]/r["subst_capa"],1) if r["subst_capa"] else 0,
            "transformers":list(r["transformers"].values()),
            "lines":sorted(lines,key=lambda x:-x["conn"]),
            "connect_max_mw":round(max([l["conn"] for l in lines],default=0),1),
            "geocoded":bool(pts),"dong_count":len(r["addrs"])})
    out.sort(key=lambda x:-x["subst_free_mw"])
    kst=timezone(timedelta(hours=9))
    payload={"generated_at":datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
        "source":"한전 cyber.kepco.co.kr (분산형전원 계통연계 조회) — 프로토타입 6개 지사권역",
        "unit":"MW · 여유용량=vol(변전소/주변압기/선로) · 좌표=읍면동 지오코딩 평균 · 지사=최근접",
        "branches":[{"name":b["name"],"lat":b["office"][0],"lng":b["office"][1]} for b in BRANCHES],
        "substations":out}
    json.dump(payload,open("capacity.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    bc=Counter(s["branch"] for s in out)
    print(f"\n=== 완료: 변전소 {len(out)}개, 지오코딩 {sum(1 for s in out if s['geocoded'])}개 ===")
    print("지사별:",dict(bc))
    for s in out[:8]:
        print(f"  {s['branch']:9s} {s['region']:5s} {s['name']:6s} 여유{s['subst_free_mw']:6.1f}MW 연계{s['connect_max_mw']:5.1f} ({s['lat']},{s['lng']})")

if __name__=="__main__":
    main()
