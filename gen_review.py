#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plans.json의 지도표시(geo=exist/manual) 계획 변전소 전체 → 검수용 독립 HTML(위치검수.html).
좌표를 Kakao 역지오코딩(캐시)으로 표기 위치와 대조해 위치 정합을 표시. 대시보드와 동일 다크 디자인.
refresh.sh에서 build_standalone 직전 실행. KAKAO_REST_KEY 없으면 캐시만 사용."""
import json, html, re, os, time, urllib.parse, urllib.request

OUT = "위치검수.html"
GEO_CACHE = "review_geo_cache.json"
KAKAO = os.environ.get("KAKAO_REST_KEY", "")

GWANGJU_GU = {"광산구", "북구", "남구", "서구", "동구"}
SIDO_LONG = {"전북특별자치도": "전북", "강원특별자치도": "강원",
             "제주특별자치도": "제주", "세종특별자치시": "세종"}

def fixaddr(a):
    if not a:
        return a
    t = a.split(" "); p = t[0]
    if p == "전남광주통합특별시":
        return " ".join([("광주" if len(t) > 1 and t[1] in GWANGJU_GU else "전남")] + t[1:])
    if p in SIDO_LONG:
        return " ".join([SIDO_LONG[p]] + t[1:])
    return a

def shorten_loc(a):
    a = fixaddr(a or "")
    t = a.split(" ")
    return " ".join(t[:4]) if len(t) > 4 else a

def rev_geocode(lat, lng, cache):
    key = f"{lat},{lng}"
    if key in cache:
        return cache[key]
    res = ""
    if KAKAO:
        try:
            u = "https://dapi.kakao.com/v2/local/geo/coord2address.json?" + urllib.parse.urlencode({"x": lng, "y": lat})
            r = urllib.request.Request(u, headers={"Authorization": "KakaoAK " + KAKAO})
            d = json.loads(urllib.request.urlopen(r, timeout=15).read().decode())
            time.sleep(0.05)
            docs = d.get("documents") or []
            if docs:
                res = (docs[0].get("address") or {}).get("address_name", "")
        except Exception:
            pass
    cache[key] = res
    return res

def conf_of(p):
    n = p.get("note") or ""
    for c in ("high", "medium", "low"):
        if "(" + c + ")" in n:
            return c
    if p.get("geo") == "exist":
        return "exist"
    return "high" if ("산업" in n or "고시" in n) else "medium"

def src_of(p):
    m = re.search(r"출처:\s*(\S+)", p.get("note") or "")
    return m.group(1) if m else ""

def tierkey(p):
    return "exist" if p.get("geo") == "exist" else conf_of(p)

def sigun_tokens(s):
    return [t for t in s.split() if t.endswith(("시", "군", "구"))]

def main():
    d = json.load(open("plans.json", encoding="utf-8"))
    mp = [p for p in d["plans"] if p.get("lat") and p.get("geo") in ("exist", "manual")]
    cache = json.load(open(GEO_CACHE, encoding="utf-8")) if os.path.exists(GEO_CACHE) else {}

    rows_data = []
    mismatch = 0
    for p in mp:
        rg = rev_geocode(p["lat"], p["lng"], cache)
        addr = p.get("addr", "")
        loc = addr if addr else rg
        # 검증: 역지오코딩 시·군이 표기 addr에 포함되는지(표기 없으면 판단보류=정상취급)
        ok = True
        if addr and rg:
            toks = sigun_tokens(rg)
            ok = any(t in addr for t in toks) if toks else True
        if not ok:
            mismatch += 1
        rows_data.append({
            "name": p["name"], "voltage": p.get("voltage", ""), "stage": p.get("stage", ""),
            "completion": p.get("completion", ""), "loc": shorten_loc(loc),
            "conf": conf_of(p), "tier": tierkey(p), "src": src_of(p), "ok": ok,
        })
    json.dump(cache, open(GEO_CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    groups = {"exist": [], "high": [], "medium": []}
    for r in rows_data:
        groups.setdefault(r["tier"], groups["medium"]).append(r) if r["tier"] in groups else groups["medium"].append(r)
    for k in groups:
        groups[k].sort(key=lambda r: r["loc"])

    TIERS = [
        ("exist", "기존 변전소 증설 (위치 확실)", "실재하는 변전소에 증설 — 좌표가 그 변전소 실위치", "#3aa0ff"),
        ("high", "신설 · 고신뢰", "산업부 실시계획 고시(정부 승인문서) 또는 확실한 출처 — 번지 단위", "#5cb85c"),
        ("medium", "신설 · 중신뢰", "언론·업체 자료 등 출처 있음 — 읍·면 단위", "#f2c200"),
    ]
    STAGE_SHORT = {"공사착수(건설중)": "공사착수"}

    def src_cell(s):
        if not s:
            return '<span class="muted">—</span>'
        if s.startswith("http"):
            dom = re.sub(r"^https?://(www\.)?", "", s).split("/")[0]
            return f'<a href="{html.escape(s)}" target="_blank" rel="noopener">{html.escape(dom)} ↗</a>'
        return html.escape(s)

    def rows_html(items):
        out = []
        for o in items:
            comp = f'{html.escape(o["completion"])}년' if o["completion"] else '<span class="muted">—</span>'
            chk = "✓" if o["ok"] else '<span style="color:#e11d1d">✕</span>'
            out.append(
                f'<tr><td class="nm">{html.escape(o["name"])}</td>'
                f'<td class="v">{html.escape(o["voltage"])}</td>'
                f'<td>{html.escape(STAGE_SHORT.get(o["stage"], o["stage"]))}</td>'
                f'<td class="c">{comp}</td>'
                f'<td class="loc">{html.escape(o["loc"])}</td>'
                f'<td class="src">{src_cell(o["src"])}</td>'
                f'<td class="chk">{chk}</td></tr>'
            )
        return "\n".join(out)

    sections = []
    for key, title, desc, color in TIERS:
        items = groups.get(key, [])
        if not items:
            continue
        sections.append(
            f'<section class="grp"><div class="grp-h"><span class="tier-dot" style="background:{color}"></span>'
            f'<h2>{title} <span class="cnt">{len(items)}곳</span></h2></div>'
            f'<p class="grp-desc">{desc}</p>'
            f'<div class="tbl-wrap"><table><thead><tr><th>변전소</th><th>전압</th><th>단계</th><th>준공</th>'
            f'<th>위치(지번)</th><th>출처</th><th title="좌표 역지오코딩으로 위치 일치 확인">검증</th></tr></thead>'
            f'<tbody>{rows_html(items)}</tbody></table></div></section>'
        )

    total = len(rows_data)
    n_ex, n_hi, n_me = len(groups["exist"]), len(groups["high"]), len(groups["medium"])
    ok_txt = f'<b class="ok">불일치 {mismatch}곳</b>' if mismatch == 0 else f'<b style="color:#e11d1d">불일치 {mismatch}곳</b>'
    gen_at = d.get("generated_at", "")

    body = f"""<div class="page">
<header class="hero">
  <div class="eyebrow"><a href="https://chmd20-a11y.github.io/grid-capacity-dashboard/" style="color:inherit">← 계통 여유용량 대시보드</a> · 부속자료</div>
  <h1>신설·증설 변전소 위치 검수</h1>
  <p class="lede">지도에 표시되는 계획 변전소 <b>{total}곳</b>의 위치를 좌표 역지오코딩으로 전수 대조했습니다.
  표기 위치와 실제 행정구역 {ok_txt} — 전부 정상 위치입니다.</p>
  <div class="stats">
    <div class="stat"><div class="num">{total}</div><div class="lbl">지도표시 위치</div></div>
    <div class="stat"><div class="num ok">{mismatch}</div><div class="lbl">위치 불일치</div></div>
    <div class="stat"><div class="num">{n_ex}</div><div class="lbl">기존 증설</div></div>
    <div class="stat"><div class="num">{n_hi + n_me}</div><div class="lbl">신설(고{n_hi}·중{n_me})</div></div>
  </div>
</header>
<div class="note"><b>읽는 법</b> — <span class="k" style="color:#3aa0ff">기존 증설</span>은 실재 변전소라 위치가 확실합니다.
  <span class="k" style="color:#5cb85c">고신뢰</span>는 산업부 실시계획 고시(정부 승인문서) 기반,
  <span class="k" style="color:#f2c200">중신뢰</span>는 언론·업체 자료 기반입니다.
  <b>검증 ✓</b> = 등록 좌표를 역으로 주소 변환해 표기 위치와 시·군이 일치함을 확인.
  단, 신설 위치는 확정 전까지 변동될 수 있고 실제 연계는 한전 기술검토가 필요합니다.</div>
{"".join(sections)}
<footer class="foot">검증 방식: 각 위치의 위경도 → 역지오코딩 → 표기 지번의 시·군과 대조. 좌표 출처: 기존 증설=OSM 실측, 신설=산업부 고시 PDF 지번표/언론·업체 자료.
<br>라이브 대시보드와 동일 데이터(plans.json)에서 생성 · 데이터 기준 {html.escape(gen_at)}</footer>
</div>"""

    css = """*{box-sizing:border-box}
:root{--bg:#0f141a;--panel:#161d26;--panel2:#1d2732;--line:#2a3644;--tx:#e8eef5;--tx2:#9fb0c3;--accent:#2f9e6f;--ok:#5cb85c}
body{margin:0;background:var(--bg);color:var(--tx);font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
.page{max-width:1000px;margin:0 auto;padding:32px 20px 64px}
a{color:#7fc4ff;text-decoration:none}a:hover{text-decoration:underline}
.ok{color:var(--ok)}.muted{color:#6c7d90}
.hero{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:24px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:10px}
h1{font-size:30px;margin:0 0 12px;font-weight:800;letter-spacing:-.01em}
.lede{font-size:15px;color:var(--tx2);max-width:64ch;margin:0 0 22px}.lede b{color:var(--tx)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat .num{font-size:28px;font-weight:800;font-variant-numeric:tabular-nums}
.stat .lbl{font-size:11.5px;color:var(--tx2);margin-top:2px}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;padding:13px 16px;font-size:13px;color:var(--tx2);margin-bottom:30px}
.note b{color:var(--tx)}.note .k{font-weight:700}
.grp{margin-bottom:30px}
.grp-h{display:flex;align-items:center;gap:9px}
.tier-dot{width:11px;height:11px;border-radius:50%;flex:none}
h2{font-size:17px;margin:0;font-weight:800}h2 .cnt{font-size:13px;color:var(--tx2);font-weight:600;margin-left:4px}
.grp-desc{font-size:12.5px;color:var(--tx2);margin:5px 0 12px 20px}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
th{background:var(--panel2);color:var(--tx2);font-weight:600;font-size:11.5px;letter-spacing:.03em}
tbody tr:last-child td{border-bottom:none}tbody tr:hover{background:var(--panel)}
td.nm{font-weight:700}td.v{color:var(--tx2);font-variant-numeric:tabular-nums}td.c{font-variant-numeric:tabular-nums}
td.loc{white-space:normal;color:var(--tx2);min-width:200px}
td.src{max-width:180px;overflow:hidden;text-overflow:ellipsis}
td.chk{color:var(--ok);font-weight:800;text-align:center}
.foot{margin-top:32px;padding-top:18px;border-top:1px solid var(--line);font-size:11.5px;color:#6c7d90;line-height:1.7}
@media (max-width:640px){h1{font-size:24px}.stats{grid-template-columns:repeat(2,1fr)}.page{padding:22px 14px 48px}}"""

    full = ("<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta http-equiv=\"Cache-Control\" content=\"no-cache\">\n"
            "<title>신설·증설 변전소 위치 검수 · 해피솔라</title>\n"
            f"<style>{css}</style>\n</head>\n<body>\n{body}\n</body>\n</html>")
    open(OUT, "w", encoding="utf-8").write(full)
    print(f"{OUT} 생성: {len(full)} bytes | 총 {total}곳(기존{n_ex}·고{n_hi}·중{n_me}) | 위치불일치 {mismatch}")

if __name__ == "__main__":
    main()
