#!/usr/bin/env python3
# capacity.json을 index.html에 내장한 단독 HTML 생성 (서버 없이 열림)
import json
data = open("capacity.json", encoding="utf-8").read()
html = open("index.html", encoding="utf-8").read()
html = html.replace("</head>", "<script>window.__DATA__=" + data + ";</script>\n</head>", 1)
open("대시보드_standalone.html", "w", encoding="utf-8").write(html)
print("대시보드_standalone.html 생성:", len(html), "bytes")
