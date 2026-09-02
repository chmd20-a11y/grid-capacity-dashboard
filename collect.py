#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한전 계통 여유용량 수집기 — 광역 확장판 (전라도 전체 + 경기/충남 확장 + 강화)
소스: cyber.kepco.co.kr (로그인·키 없이 작동)
계층 자동 대응: 광역시 구 / 도의 군(-기타지역) / 시(구 있음: 시→구→읍면동) / 시(구 없음: 시→읍면동).
여유용량 = viewDetail 인자 vol1/vol2/vol3(변전소/주변압기/선로), kW.
좌표=읍면동 지오코딩 평균, 사업소=최근접. (enrich_osm.py가 실명·정확좌표 보강)
"""
import json, re, time, urllib.parse, urllib.request, http.cookiejar, hashlib, math, os
from collections import Counter
from datetime import datetime, timezone, timedelta

BASE = "https://cyber.kepco.co.kr/ckepco/mobile/resources"
REF = BASE + "/resources_search2.jsp"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
GEO_UA = "happysolar-grid-dashboard/1.0 (contact chmd20@gmail.com)"
GEO_CACHE = "geocode_cache.json"
SHORTDO = {"광주광역시":"광주","인천광역시":"인천","경기도":"경기","전라남도":"전남","전북특별자치도":"전북",
           "충청남도":"충남","서울특별시":"서울","부산광역시":"부산","대구광역시":"대구","대전광역시":"대전",
           "울산광역시":"울산","세종특별자치시":"세종","경상남도":"경남","경상북도":"경북",
           "충청북도":"충북","강원특별자치도":"강원","제주특별자치도":"제주"}

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
    """(addrList, addr_type) 반환. addr_type은 서버가 채운 레벨(addr_gu/addr_lidong 등)."""
    try:
        d = json.loads(_get(BASE + "/resources_search_jibun_list.jsp",
            {"addr": target, "addr_do": do, "addr_si": si, "addr_gu": gu, "addr_lidong": lidong}))
        if d.get("status") == "true":
            return d.get("addrList", []), d.get("addr", target)
    except Exception as e:
        print("  list err:", e)
    return [], target

VD = re.compile(r"viewDetail\(([^)]*)\)")
ARG = re.compile(r"'([^']*)'")

def fetch_detail(do, si, gu, lidong, tries=3):
    for t in range(tries):
        try:
            op = fresh_opener()
            html = _get(BASE + "/resources_jibun_detail2_1.jsp",
                {"addr_do": do, "addr_si": si, "addr_gu": gu,
                 "addr_lidong": lidong, "addr_li": "", "addr_jibun": ""}, op=op)
        except Exception:
            time.sleep(0.6); continue
        rows = [ARG.findall(m.group(1)) for m in VD.finditer(html)]
        rows = [a for a in rows if len(a) >= 20]
        if rows:
            return rows
        time.sleep(0.35)
    return []

def to_mw(x):
    try: return round(int(x) / 1000.0, 3)
    except: return 0.0

def haversine(a,b):
    R=6371;p=math.pi/180
    return 2*R*math.asin(math.sqrt(math.sin((b[0]-a[0])*p/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin((b[1]-a[1])*p/2)**2))

# ---- 지오코딩 ----
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
        time.sleep(1.1)
        if data: return [round(float(data[0]["lat"]),5), round(float(data[0]["lon"]),5)]
    except Exception:
        time.sleep(1.1)
    return None
def geocode(addr, cache):
    if addr in cache: return cache[addr]
    res = _nomi(addr)
    if res is None:
        parts = addr.split(" ", 1)
        if len(parts) == 2: res = _nomi(parts[1])
    cache[addr] = res
    return res

# ---- 사업소(핀) ----
OFFICES = [
    {"name":"본사(광주)","lat":35.1595,"lng":126.8526},
    {"name":"영암지사","lat":34.8000,"lng":126.6970},
    {"name":"장흥지사","lat":34.6814,"lng":126.9070},
    {"name":"해남사업소","lat":34.5730,"lng":126.5990},
    {"name":"파주지사","lat":37.7600,"lng":126.7800},
    {"name":"평택지사","lat":36.9920,"lng":127.1130},
    {"name":"강화사업소","lat":37.7470,"lng":126.4850},
    {"name":"전남동부권","lat":34.9500,"lng":127.4900},
    {"name":"전북권","lat":35.8242,"lng":127.1480},   # 전주 중심(신규 타겟)
]
# 수집대상: (do, 포함 시/군 리스트 또는 "ALL")
SCRAPE = [
    ("광주광역시", ["광산구","남구","동구","북구","서구"]),
    ("전라남도", "ALL"),
    ("전북특별자치도", "ALL"),
    ("경기도", ["파주시","평택시","화성시","수원시","용인시","연천군","남양주시","하남시","안양시"]),
    ("충청남도", ["천안시","서산시"]),
    ("인천광역시", ["강화군"]),
]
def jit(code, base, span=0.006):
    h=int(hashlib.md5(code.encode()).hexdigest(),16)
    return [round(base[0]+(((h//1000)%1000)/1000-0.5)*span,5),
            round(base[1]+((h%1000)/1000-0.5)*span,5)]
def nearest_office(latlng):
    return min(OFFICES,key=lambda o:haversine(latlng,[o["lat"],o["lng"]]))["name"]

def build_cells(do, names):
    """(do,si,gu,region,known_dongs) 리스트. known_dongs는 구없는 시에서 이미 확보한 읍면동."""
    cells=[]
    silist,_ = list_addr("addr_si", do)
    for si in silist:
        if si == "-기타지역":
            gus,_ = list_addr("addr_gu", do, si)
            for gu in gus:
                if gu in ("Unknown","-기타지역"): continue
                if names=="ALL" or gu in names:
                    cells.append((do, si, gu, gu, None))       # 군/광역시구 → region=gu
        else:  # 시
            if names!="ALL" and si not in names: continue
            items,itype = list_addr("addr_gu", do, si)
            if itype=="addr_gu":       # 시에 구 있음
                for gu in items:
                    if gu in ("Unknown","-기타지역"): continue
                    cells.append((do, si, gu, si, None))       # region=시명
            else:                       # 시에 구 없음 → items=읍면동
                cells.append((do, si, "", si, items))          # region=시명
    return cells

def main():
    warm()
    subs = {}
    for do, names in SCRAPE:
        for (d, si, gu, region, known) in build_cells(do, names):
            dongs = known if known is not None else list_addr("addr_lidong", d, si, gu)[0]
            dongs = [x for x in dongs if x and x not in ("Unknown","-기타지역")]
            print(f"[{d} {si if si!='-기타지역' else ''} {region}] 읍면동 {len(dongs)}개")
            for dong in dongs:
                rows = fetch_detail(d, si, gu, dong)
                addr_str = f"{SHORTDO.get(d,d)} {region} {dong}"
                found=0
                for a in rows:
                    subst_cd = a[12]
                    if not subst_cd: continue
                    r = subs.get(subst_cd)
                    if not r:
                        r = {"code":subst_cd,"nm":a[0],"subst_capa":to_mw(a[14]),
                             "g_subst":to_mw(a[9]),"transformers":{},"lines":{},
                             "addrs":Counter(),"regions":Counter()}
                        subs[subst_cd]=r
                    r["subst_capa"]=max(r["subst_capa"],to_mw(a[14]))
                    r["g_subst"]=max(r["g_subst"],to_mw(a[9]))
                    r["addrs"][addr_str]+=1; r["regions"][region]+=1
                    r["transformers"][a[1]]={"mtr_no":a[1],"mtr_capa":to_mw(a[15]),"g_mtr":to_mw(a[10])}
                    conn=min(to_mw(a[9]),to_mw(a[10]),to_mw(a[11]))
                    r["lines"][f"{a[1]}|{a[2]}|{a[13]}"]={"mtr_no":a[1],"dl_nm":a[2],
                        "dl_capa":to_mw(a[16]),"g_dl":to_mw(a[11]),"conn":round(conn,3)}
                    found+=1
                if found: print(f"    {dong}: {found}")
                time.sleep(0.08)

    # 지오코딩
    cache=load_cache()
    uniq=sorted({a for r in subs.values() for a in r["addrs"]})
    print(f"\n[지오코딩] 고유 읍면동 {len(uniq)}개 (캐시 {sum(1 for a in uniq if a in cache)})")
    for i,a in enumerate(uniq):
        if a not in cache:
            geocode(a,cache)
            if i%25==0: save_cache(cache); print(f"  ...{i}/{len(uniq)}")
    save_cache(cache)
    print(f"[지오코딩] 성공 {sum(1 for a in uniq if cache.get(a))}/{len(uniq)}")

    out=[]
    for cd,r in subs.items():
        pts=[cache[a] for a in r["addrs"] if cache.get(a)]
        if pts:
            lat=round(sum(p[0] for p in pts)/len(pts),5); lng=round(sum(p[1] for p in pts)/len(pts),5)
        else:
            base=CENTROID_FALLBACK; lat,lng=jit(cd,base)
        region=r["regions"].most_common(1)[0][0]
        lines=list(r["lines"].values())
        out.append({"code":cd,"name":r["nm"],"region":region,"branch":nearest_office([lat,lng]),
            "lat":lat,"lng":lng,"subst_capa_mw":r["subst_capa"],"subst_free_mw":r["g_subst"],
            "subst_free_pct":round(100.0*r["g_subst"]/r["subst_capa"],1) if r["subst_capa"] else 0,
            "transformers":list(r["transformers"].values()),
            "lines":sorted(lines,key=lambda x:-x["conn"]),
            "connect_max_mw":round(max([l["conn"] for l in lines],default=0),1),
            "geocoded":bool(pts),"dong_count":len(r["addrs"])})
    out.sort(key=lambda x:-x["subst_free_mw"])
    kst=timezone(timedelta(hours=9))
    payload={"generated_at":datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
        "source":"한전 cyber.kepco.co.kr (분산형전원 계통연계 조회) — 전라도 전체 + 경기·충남 확장",
        "unit":"MW · 여유용량=vol(변전소/주변압기/선로) · 좌표=읍면동 지오코딩 평균 · 사업소=최근접",
        "branches":[{"name":o["name"],"lat":o["lat"],"lng":o["lng"]} for o in OFFICES],
        "substations":out}
    json.dump(payload,open("capacity.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    from collections import Counter as C
    print(f"\n=== 완료: 변전소 {len(out)}개 ===")
    print("사업소별:",dict(C(x["branch"] for x in out)))

CENTROID_FALLBACK=[35.8,127.0]

if __name__=="__main__":
    main()
