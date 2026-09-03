#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한전 '송변전 건설 정보공개'에서 변전소 신설/증설 사업을 수집 → plans.json.
단계: 계획확정(64)/사업승인(65)/공사착수(66). 변전(설비종류=변전)만 필터.
목록에 사업명·설비종류·담당본부·담당사업소가 있음(상세 불필요). 위치=변전소명 지오코딩(Kakao).
※ 정확한 준공연도·주소는 한전이 구조적으로 공개 안 함(첨부 PDF) → 단계로 표시.
"""
import json, re, time, urllib.parse, urllib.request, http.cookiejar, os

BASEROOT = "https://www.kepco.co.kr/home/disclosure/transdisclosure/transstatus"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1"
KAKAO_REST = os.environ.get("KAKAO_REST_KEY", "")
GEO_CACHE = "plan_geo_cache.json"

STAGES = [("64","계획확정","plantoapprove"),
          ("65","사업승인","approvetostart"),
          ("66","공사착수(건설중)","starttocomplete")]

ROW = re.compile(r"fn_Detail\('(\d+)','(\d+)'\);\"><strong>(.*?)</strong>.*?설비종류\"><span>(.*?)</span>.*?담당본부\"><span>(.*?)</span>.*?담당사업소\"><span>(.*?)</span>", re.S)
# 본부 대략 좌표(지오코딩 실패 폴백)
HQ_XY = {
    "경인건설본부":[37.55,126.9],"남부건설본부":[35.3,128.6],"중부건설본부":[36.6,127.3],
    "서부건설본부":[35.5,126.9],"영남건설본부":[35.9,128.6],"강원건설본부":[37.8,128.2],
}

def opener_with_session(stg_path):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    url = f"{BASEROOT}/{stg_path}/boardList.do"
    html = op.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8","replace")
    csrf = re.search(r'name="csrfToken"[^>]*value="([^"]+)"', html)
    return op, (csrf.group(1) if csrf else ""), html

def post_page(op, stg_path, mng, csrf, page):
    url = f"{BASEROOT}/{stg_path}/boardList.do"
    data = urllib.parse.urlencode({"csrfToken":csrf,"boardMngNo":mng,"boardNo":"","page":str(page),
                                   "s_field":"ALL","s_yearCd":"","s_word":""}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent":UA,"Referer":url,
        "Content-Type":"application/x-www-form-urlencoded"})
    return op.open(req, timeout=30).read().decode("utf-8","replace")

def subst_name(saup):
    # 사업명 → 변전소명 추출
    v = re.match(r"\s*([0-9]+)\s*kV", saup)
    volt = (v.group(1)+"kV") if v else ""
    s = re.sub(r"^\s*[0-9]+\s*kV\s*", "", saup)
    s = re.split(r"\s+(건설사업|증설|보강|신설)", s)[0].strip()
    s = re.sub(r"#\d+", "", s)
    s = s.replace("S/S", "변전소").replace("변환소","변환소").strip()
    if "변전소" not in s and "변환소" not in s: s = s + "변전소"
    return s, volt

def geocode(name, cache):
    if name in cache: return cache[name]
    res = None
    if KAKAO_REST:
        for path,parser in [("keyword.json",lambda d:d.get("documents")), ("address.json",lambda d:d.get("documents"))]:
            try:
                url="https://dapi.kakao.com/v2/local/search/"+path+"?"+urllib.parse.urlencode({"query":name,"size":1})
                req=urllib.request.Request(url,headers={"Authorization":"KakaoAK "+KAKAO_REST})
                d=json.loads(urllib.request.urlopen(req,timeout=15).read().decode()); time.sleep(0.05)
                docs=parser(d)
                if docs: res=[round(float(docs[0]["y"]),5),round(float(docs[0]["x"]),5)]; break
            except Exception: pass
    cache[name]=res
    return res

def main():
    cache = json.load(open(GEO_CACHE,encoding="utf-8")) if os.path.exists(GEO_CACHE) else {}
    plans=[]; seen=set()
    for mng, stage, path in STAGES:
        op, csrf, html = opener_with_session(path)
        print(f"[{stage}] mng={mng} csrf={'OK' if csrf else 'X'}")
        page=1; empty=0
        while page<=60:
            h = html if page==1 else post_page(op, path, mng, csrf, page)
            rows = ROW.findall(h)
            if not rows:
                empty+=1
                if empty>=2: break
                page+=1; continue
            empty=0
            for mngNo,boardNo,saup,fac,hq,office in rows:
                fac=re.sub("<[^>]+>","",fac).strip()
                if "변전" not in fac: continue   # 변전소만
                saup=re.sub(r"\s+"," ",re.sub("<[^>]+>","",saup)).strip()
                key=(saup, stage)
                if key in seen: continue
                seen.add(key)
                nm, volt = subst_name(saup)
                plans.append({"saup":saup,"name":nm,"voltage":volt,"stage":stage,
                              "hq":hq.strip(),"office":office.strip()})
            page+=1
            time.sleep(0.15)
        print(f"  누적 변전 사업: {len(plans)}")

    # 기존 변전소 좌표(증설 매칭용)
    exist={}
    if os.path.exists("capacity.json"):
        for s in json.load(open("capacity.json",encoding="utf-8"))["substations"]:
            for nm in (s.get("osm_name"), s.get("name")):
                if nm:
                    k=nm.replace("변전소","").replace("변환소","").replace("*","").strip()
                    if k and k not in exist: exist[k]=[s["lat"],s["lng"]]
    def match_exist(name):
        return exist.get(name.replace("변전소","").replace("변환소","").strip())

    # 지오코딩: Kakao(신설·기존) → 기존변전소 매칭(증설) → 위치없음(목록전용)
    print(f"[지오코딩] {len(plans)}건")
    for i,p in enumerate(plans):
        xy = geocode(p["name"], cache)
        if xy: p["geo"]="ok"
        else:
            xy = match_exist(p["name"]); p["geo"]="exist" if xy else "none"
        if xy: p["lat"],p["lng"]=xy[0],xy[1]
        if i%30==0: json.dump(cache,open(GEO_CACHE,"w",encoding="utf-8"),ensure_ascii=False)
    json.dump(cache,open(GEO_CACHE,"w",encoding="utf-8"),ensure_ascii=False)

    # 수동 등록 계획 병합(한전 공개목록에 아직 없는 신설 건). 이름 중복 시 수동본 우선.
    if os.path.exists("manual_plans.json"):
        man = (json.load(open("manual_plans.json",encoding="utf-8")).get("plans") or [])
        names = {p["name"] for p in plans}
        for mp in man:
            if mp.get("name") not in names:
                plans.append(mp)
        print(f"[수동병합] {len(man)}건 (신규 {sum(1 for mp in man if mp.get('name') not in names)}건)")

    # plans 전체 유지(목록용). 좌표 있는 것만 지도표시.
    from datetime import datetime,timezone,timedelta
    kst=timezone(timedelta(hours=9))
    located=[p for p in plans if p.get("lat")]
    out={"generated_at":datetime.now(kst).strftime("%Y-%m-%d %H:%M KST"),
         "source":"한전 송변전 건설 정보공개(계획확정/사업승인/공사착수) — 변전소 사업",
         "note":"신설 예정 변전소는 정확 위치가 공개되지 않아(첨부 PDF만) 지도표시는 일부만. 전체는 목록 참조.",
         "total":len(plans),"located":len(located),"plans":plans}
    json.dump(out,open("plans.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    from collections import Counter
    print(f"=== 완료: 전체 {len(plans)}건 / 지도표시 {len(located)}건 ===")
    print("단계별:",dict(Counter(p['stage'] for p in plans)))
    print("좌표소스:",dict(Counter(p['geo'] for p in plans)))

if __name__=="__main__":
    main()
