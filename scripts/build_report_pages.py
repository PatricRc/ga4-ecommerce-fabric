"""Generate the GA4 marketing report ("From Click to Checkout") as PBIR into a downloaded .Report folder.

Usage: python3 scripts/build_report_pages.py <path-to-downloaded-report-folder>
Design source: design/index.html (prototype). HTML components come from DAX measures (semantic/ga4_measures.py),
rendered by the HTML Content visual. Every page body is one HTML Content visual running the prototype's chart code
(semantic/pbi_runtime.js) on DAX-built data; native visuals only for the page navigator, buttons and the synced date slicer.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

REPORT = Path(sys.argv[1])
DEF = REPORT / "definition"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"
M = "_Measures"
HTML = "htmlContent443BE3AD55E043BF878BED274D3A6855"
THEME_NAME = "GA4-Marketing-Indigo.json"

# ---------------------------------------------------------------- tokens (design/index.html :root)
BG, CARD, INK, SUB, MUTED, LINE = "#F3F4FA", "#FFFFFF", "#1A1840", "#5E6189", "#9A9DC0", "#ECEDF6"
ACC, ACC_D, ACC2, ACC3, SOFT = "#5B5BD6", "#4338CA", "#8B8CF0", "#C7C8F7", "#EEEFFD"
GOOD, BAD, NAVY, NAVY2 = "#0E9F6E", "#E5484D", "#1B1946", "#0F0D2E"
FONT = "Segoe UI"

PAGES = [("p00welcome", "Welcome"), ("p01overview", "Overview"), ("p02acquisition", "Acquisition"),
         ("p03content", "Content & Landing"), ("p04funnel", "Funnel"), ("p05products", "Products"),
         ("p06time", "Time Intelligence")]
PID = {n: p for p, n in PAGES}
X0, W0 = 218, 1044          # content column (rail is 200 wide + 18 gutter)
BODY_Y, BODY_H = 240, 464   # below header (16..96) and KPI strip (108..228)


def uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]


def lit(v) -> dict:
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, int):
        s = f"{v}L"
    elif isinstance(v, float):
        s = f"{v}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def num(v) -> dict:
    return {"expr": {"Literal": {"Value": f"{float(v)}D"}}}


def color(hex_: str) -> dict:
    return {"solid": {"color": lit(hex_)}}


def mfield(name: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": name}}


def cfield(table: str, col: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}}


def mproj(name: str, display: str | None = None) -> dict:
    p = {"field": mfield(name), "queryRef": f"{M}.{name}", "nativeQueryRef": display or name}
    if display:
        p["displayName"] = display
    return p


def cproj(table: str, col: str, display: str | None = None) -> dict:
    p = {"field": cfield(table, col), "queryRef": f"{table}.{col}", "nativeQueryRef": display or col}
    if display:
        p["displayName"] = display
    return p


def no_chrome(pad: int = 0) -> dict:
    return {"background": [{"properties": {"show": lit(False)}}],
            "border": [{"properties": {"show": lit(False)}}],
            "title": [{"properties": {"show": lit(False)}}],
            "visualHeader": [{"properties": {"show": lit(False)}}],
            "dropShadow": [{"properties": {"show": lit(False)}}],
            "padding": [{"properties": {k: num(pad) for k in ("top", "bottom", "left", "right")}}]}


def topn(pid: str, key: str, table: str, col: str, measure: str, n: int) -> dict:
    return {"filters": [{
        "name": uid(pid, key, "topn"), "field": cfield(table, col), "type": "TopN",
        "filter": {"Version": 2, "From": [
            {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                "Version": 2,
                "From": [{"Name": "t", "Entity": table, "Type": 0}, {"Name": "m", "Entity": M, "Type": 0}],
                "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": col}, "Name": "field"}],
                "OrderBy": [{"Direction": 2, "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}],
                "Top": n}}}, "Type": 2},
            {"Name": "t", "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": col}}],
                "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
        "howCreated": "User"}]}


class Page:
    def __init__(self, name: str, bg: str = BG):
        self.pid, self.name, self.bg, self.visuals, self.z = PID[name], name, bg, [], 0

    def add(self, key, x, y, w, h, visual, filter_config=None, alt=None):
        self.z += 1
        vc = {"$schema": VC_SCHEMA, "name": uid(self.pid, key),
              "position": {"x": x, "y": y, "z": self.z * 100, "width": w, "height": h, "tabOrder": self.z * 100},
              "visual": visual}
        if alt:
            visual.setdefault("visualContainerObjects", {})["general"] = [{"properties": {"altText": lit(alt)}}]
        if filter_config:
            vc["filterConfig"] = filter_config
        self.visuals.append(vc)

    # ---- primitives
    def shape(self, key, x, y, w, h, fill, outline=None, radius=14, transparency=0):
        objs = {"shape": [{"properties": {"tileShape": lit("rectangleRounded" if radius else "rectangle"),
                                          **({"rectangleRoundedCurve": lit(max(1, round(radius * 100 / min(w, h))))} if radius else {})}}],
                "fill": [{"properties": {"fillColor": color(fill), "transparency": num(transparency)}, "selector": {"id": "default"}}],
                "outline": [{"properties": {"show": lit(outline is not None)}},
                            {"properties": {"lineColor": color(outline or fill), "weight": num(1),
                                            "transparency": num(0)}, "selector": {"id": "default"}}]}
        self.add(key, x, y, w, h, {"visualType": "shape", "objects": objs, "visualContainerObjects": no_chrome()})

    def text(self, key, x, y, w, h, paras, align="left"):
        """paras: list of paragraphs, each a list of (text, size_px, color, bold)."""
        paragraphs = [{"textRuns": [{"value": t, "textStyle": {"fontFamily": FONT, "fontSize": f"{s}px", "color": c,
                                                                **({"fontWeight": "bold"} if b else {})}}
                                    for (t, s, c, b) in para], "horizontalTextAlignment": align} for para in paras]
        self.add(key, x, y, w, h, {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
                                   "visualContainerObjects": no_chrome()})

    def html(self, key, x, y, w, h, measure, alt=None):
        vco = no_chrome()
        self.add(key, x, y, w, h, {"visualType": HTML,
                                   "query": {"queryState": {"content": {"projections": [mproj(measure)]}}},
                                   "objects": {"compatibility": [{"properties": {"legacyRendering": lit(False)}}]},
                                   "visualContainerObjects": vco, "drillFilterOtherVisuals": True}, alt=alt or measure)

    def card(self, key, x, y, w, h, title, sub=None):
        """White rounded panel + title/subtitle text; returns the inner content box (x, y, w, h)."""
        self.shape(key + "-bg", x, y, w, h, CARD, outline=LINE)
        paras = [[(title, 14, INK, True)]] + ([[(sub, 11, SUB, False)]] if sub else [])
        self.text(key + "-title", x + 12, y + 8, w - 24, 46 if sub else 30, paras)
        top = 54 if sub else 40
        return x + 12, y + top, w - 24, h - top - 10

    def button(self, key, x, y, w, h, label, *, page=None, url=None, fill=CARD, fc=INK, outline=None, hover=SOFT,
               size=11, transparency=0):
        objs = {"text": [{"properties": {"show": lit(True)}},
                         {"properties": {"text": lit(label), "fontFamily": lit(FONT), "fontSize": num(size), "bold": lit(True),
                                         "fontColor": color(fc), "horizontalAlignment": lit("center")}, "selector": {"id": "default"}},
                         {"properties": {"fontColor": color("#FFFFFF")}, "selector": {"id": "hover"}}],
                "icon": [{"properties": {"show": lit(False)}}],
                "fill": [{"properties": {"show": lit(True)}},
                         {"properties": {"fillColor": color(fill), "transparency": num(transparency)}, "selector": {"id": "default"}},
                         {"properties": {"fillColor": color(hover), "transparency": num(0)}, "selector": {"id": "hover"}}],
                "outline": [{"properties": {"show": lit(outline is not None)}},
                            {"properties": {"lineColor": color(outline or fill), "weight": num(1)}, "selector": {"id": "default"}}],
                "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(8)}}]}
        vco = no_chrome()
        link = {"show": lit(True)}
        if page:
            link.update(type=lit("PageNavigation"), navigationSection=lit(PID[page]))
        else:
            link.update(type=lit("WebUrl"), webUrl=lit(url))
        vco["visualLink"] = [{"properties": link}]
        self.add(key, x, y, w, h, {"visualType": "actionButton", "objects": objs, "visualContainerObjects": vco,
                                   "drillFilterOtherVisuals": True}, alt=f"Go to {page or label}")

    # ---- native charts
    def _axes(self, cat=True, val=False, grid=True):
        return {"categoryAxis": [{"properties": {"show": lit(cat), "fontFamily": lit(FONT), "fontSize": num(9), "labelColor": color(SUB),
                                                 "showAxisTitle": lit(False), "gridlineShow": lit(False)}}],
                "valueAxis": [{"properties": {"show": lit(val), "fontFamily": lit(FONT), "fontSize": num(9), "labelColor": color(MUTED),
                                              "showAxisTitle": lit(False), "gridlineShow": lit(grid), "gridlineColor": color(LINE),
                                              "gridlineStyle": lit("dashed")}}]}

    def chart(self, key, box, vtype, roles, colors=None, *, legend=False, labels=False, val_axis=True, fc=None, extra=None,
              sort=None, cat_axis=True, k=False):
        x, y, w, h = box
        objs = self._axes(cat=cat_axis, val=val_axis)
        objs["legend"] = [{"properties": {"show": lit(legend), "position": lit("TopRight"), "fontSize": num(9),
                                          "labelColor": color(SUB), "fontFamily": lit(FONT)}}]
        if vtype != "scatterChart":
            objs["labels"] = [{"properties": {"show": lit(labels), "fontSize": num(9), "color": color(INK), "fontFamily": lit(FONT),
                                              **({"labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}, "labelPrecision": lit(1)} if k else {})}}]
        if colors:
            objs["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{M}.{n}"}} for n, c in colors]
        if extra:
            objs.update(extra)
        query = {"queryState": roles}
        if sort:
            query["sortDefinition"] = {"sort": sort, "isDefaultSort": True}
        self.add(key, x, y, w, h, {"visualType": vtype, "query": query, "objects": objs,
                                   "visualContainerObjects": no_chrome(), "drillFilterOtherVisuals": True}, fc)

    def table(self, key, box, cols, sort_measure, fc=None, widths=None):
        x, y, w, h = box
        objs = {"columnHeaders": [{"properties": {"fontFamily": lit(FONT), "fontSize": num(9), "bold": lit(True),
                                                  "fontColor": color(MUTED), "backColor": color(CARD), "wordWrap": lit(False)}}],
                "values": [{"properties": {"fontFamily": lit(FONT), "fontSize": num(10), "fontColorPrimary": color(INK),
                                           "fontColorSecondary": color(INK), "backColorPrimary": color(CARD),
                                           "backColorSecondary": color(CARD), "wordWrap": lit(False)}}],
                "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": color("#F3F4FA"),
                                         "gridVertical": lit(False), "outlineColor": color(LINE), "rowPadding": num(5)}}],
                "total": [{"properties": {"totals": lit(False)}}]}
        if widths:
            objs["columnWidth"] = [{"properties": {"value": num(wd)}, "selector": {"metadata": ref}} for ref, wd in widths]
        vco = no_chrome()
        vco["stylePreset"] = [{"properties": {"name": lit("None")}}]
        self.add(key, x, y, w, h, {"visualType": "tableEx",
                                   "query": {"queryState": {"Values": {"projections": cols}},
                                             "sortDefinition": {"sort": [{"field": mfield(sort_measure), "direction": "Descending"}],
                                                                "isDefaultSort": True}},
                                   "objects": objs, "visualContainerObjects": vco, "drillFilterOtherVisuals": True}, fc)

    def write(self, root: Path):
        pdir = root / "pages" / self.pid
        if pdir.exists():
            shutil.rmtree(pdir)
        (pdir / "visuals").mkdir(parents=True)
        page = {"$schema": PAGE_SCHEMA, "name": self.pid, "displayName": self.name, "displayOption": "FitToPage",
                "height": 720, "width": 1280,
                "objects": {"background": [{"properties": {"color": color(self.bg), "transparency": num(0)}}],
                            "outspace": [{"properties": {"color": color(self.bg)}}]}}
        (pdir / "page.json").write_text(json.dumps(page, indent=2), encoding="utf-8")
        for v in self.visuals:
            vd = pdir / "visuals" / v["name"]
            vd.mkdir()
            (vd / "visual.json").write_text(json.dumps(v, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- shared chrome
def rail(p: Page):
    p.shape("rail", 0, 0, 200, 720, NAVY, radius=0)
    p.shape("logo", 18, 22, 36, 36, ACC, radius=10)
    p.text("logo-t", 18, 28, 36, 26, [[("G4", 12, "#FFFFFF", True)]], align="center")
    p.text("brand", 60, 20, 136, 44, [[("Merchandise Store", 13, "#FFFFFF", True)], [("GA4 · Microsoft Fabric", 10, "#A9AAD6", False)]])
    p.text("sec1", 16, 84, 170, 22, [[("CHOOSE A PAGE", 9, "#7F80B5", True)]])
    nav = {
        "layout": [{"properties": {"orientation": {"expr": {"Literal": {"Value": "1D"}}}, "cellPadding": lit(4)}}],
        "pages": [{"properties": {"showHiddenPages": lit(False), "showTooltipPages": lit(False)}}],
        "text": [{"properties": {"fontFamily": lit(FONT), "fontSize": num(11), "fontColor": color("#C5C6EA"),
                                 "horizontalAlignment": lit("left"), "leftMargin": lit(12)}, "selector": {"id": "default"}},
                 {"properties": {"fontColor": color("#FFFFFF")}, "selector": {"id": "hover"}},
                 {"properties": {"fontColor": color("#FFFFFF"), "bold": lit(True)}, "selector": {"id": "selected"}}],
        "fill": [{"properties": {"show": lit(True), "fillColor": color(NAVY), "transparency": num(0)}, "selector": {"id": "default"}},
                 {"properties": {"fillColor": color("#2A2860")}, "selector": {"id": "hover"}},
                 {"properties": {"fillColor": color("#34327A")}, "selector": {"id": "selected"}}],
        "outline": [{"properties": {"show": lit(False)}}] + [{"properties": {"show": lit(False)}, "selector": {"id": s}}
                                                               for s in ("default", "hover", "selected", "disabled")],
        "shape": [{"properties": {"tileShape": lit("rectangleRounded"), "roundEdge": lit(10)}}],
        "accentBar": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}},
                      {"properties": {"show": lit(True), "color": color(ACC2), "position": lit("Left"), "width": num(3)},
                       "selector": {"id": "selected"}}],
    }
    p.add("nav", 10, 108, 180, 300, {"visualType": "pageNavigator", "objects": nav, "visualContainerObjects": no_chrome()},
          alt="Page navigation")
    p.text("sec2", 16, 596, 170, 22, [[("SUPPORT", 9, "#7F80B5", True)]])
    p.button("li", 14, 620, 172, 34, "LinkedIn", url="https://www.linkedin.com/in/patriciorioscanepa", fill="#2A2860", fc="#E3E4FF",
             hover=ACC, size=10)
    p.button("dp", 14, 662, 172, 34, "DataPat.ai", url="https://data-pat-ai.netlify.app/", fill="#2A2860", fc="#E3E4FF",
             hover=ACC, size=10)


def date_slicer(p: Page):
    t, c = "Date", "date"
    objs = {"data": [{"properties": {"mode": lit("Between")}}],
            "header": [{"properties": {"show": lit(False)}}],
            "slider": [{"properties": {"show": lit(False)}}],
            "date": [{"properties": {"fontFamily": lit(FONT), "textSize": num(10), "fontColor": color(INK), "background": color(CARD)}}],
            "items": [{"properties": {"fontFamily": lit(FONT), "textSize": num(10), "fontColor": color(INK)}}]}
    p.add("date", X0 + W0 - 286, 20, 270, 40, {
        "visualType": "slicer",
        "syncGroup": {"groupName": "DateRange", "fieldChanges": True, "filterChanges": True},
        "query": {"queryState": {"Values": {"projections": [cproj(t, c)]}}},
        "objects": objs, "visualContainerObjects": no_chrome(2)}, alt="Date range")


def frame(p: Page, n: str):
    rail(p)
    p.html("hdr", X0, 16, W0, 80, f"{n} · 000 Headline HTML", alt=f"{n} · 000 Headline HTML")
    date_slicer(p)
    p.html("kpi", X0, 108, W0, 120, f"{n} · 001 KPI Strip HTML", alt=f"{n} · 001 KPI Strip Alt Text")


def cols(*fr, gap=12, x=X0, w=W0):
    tot = sum(fr)
    inner = w - gap * (len(fr) - 1)
    out, cx = [], x
    for f in fr:
        cw = round(inner * f / tot)
        out.append((cx, cw))
        cx += cw + gap
    return out


# ---------------------------------------------------------------- pages
def cover() -> Page:
    p = Page("Welcome", bg="#07061A")
    p.html("cover", 0, 0, 1280, 720, "00 · 001 Cover HTML", alt="00 · 001 Cover Alt Text")
    labels = [("Overview", "Overview"), ("Acquisition", "Acquisition"), ("Content", "Content & Landing"),
              ("Funnel", "Funnel"), ("Products", "Products"), ("Time Intelligence", "Time Intelligence")]
    widths = [118, 132, 112, 104, 116, 160]
    gap = 12
    x = (1280 - sum(widths) - gap * 5) // 2
    for (lab, page), w in zip(labels, widths):
        p.button("go-" + lab, x, 638, w, 40, lab, page=page, fill="#16143C", fc="#E3E4FF", outline="#3A3870", hover=ACC, size=11)
        x += w + gap
    p.button("cover-li", 1080, 26, 160, 32, "CONNECT LINKEDIN ›", url="https://www.linkedin.com/in/patriciorioscanepa",
             fill="#3B3A8C", fc="#FFFFFF", outline="#5B5BD6", hover=ACC, size=9)
    return p


def body_page(name: str, n: str) -> Page:
    """Header + KPI strip + one HTML Content visual running the prototype's page code (0N · 002 Body HTML)."""
    p = Page(name)
    frame(p, n)
    p.html("body", X0, BODY_Y, W0, BODY_H, f"{n} · 002 Body HTML", alt=f"{name} charts and tables")
    return p


def overview() -> Page:
    return body_page("Overview", "01")


def acquisition() -> Page:
    return body_page("Acquisition", "02")


def content() -> Page:
    return body_page("Content & Landing", "03")


def funnel() -> Page:
    return body_page("Funnel", "04")


def products() -> Page:
    return body_page("Products", "05")


def time_page() -> Page:
    return body_page("Time Intelligence", "06")


# ---------------------------------------------------------------- theme + report.json
def write_theme():
    theme = {
        "name": THEME_NAME,
        "dataColors": [ACC, ACC3, INK, ACC2, "#5BD6B0", BAD, GOOD, MUTED],
        "foreground": INK, "foregroundNeutralSecondary": SUB, "foregroundNeutralTertiary": MUTED,
        "background": CARD, "backgroundLight": BG, "backgroundNeutral": LINE, "tableAccent": ACC,
        "good": GOOD, "bad": BAD, "neutral": MUTED, "maximum": ACC, "center": ACC3, "minimum": "#F3F4FA",
        "textClasses": {"callout": {"fontFace": FONT, "color": INK}, "title": {"fontFace": FONT, "color": INK, "fontSize": 12},
                        "header": {"fontFace": FONT, "color": INK}, "label": {"fontFace": FONT, "color": SUB, "fontSize": 9}},
        "visualStyles": {"*": {"*": {"title": [{"show": False}], "background": [{"show": False}], "border": [{"show": False}],
                                     "dropShadow": [{"show": False}], "visualHeader": [{"show": False}]}},
                         "page": {"*": {"background": [{"color": {"solid": {"color": BG}}, "transparency": 0}],
                                        "outspace": [{"color": {"solid": {"color": BG}}}]}}},
    }
    res = REPORT / "StaticResources" / "RegisteredResources"
    res.mkdir(parents=True, exist_ok=True)
    (res / THEME_NAME).write_text(json.dumps(theme, indent=2), encoding="utf-8")
    rp = DEF / "report.json"
    report = json.loads(rp.read_text(encoding="utf-8"))
    base = report["themeCollection"]["baseTheme"]
    report["themeCollection"]["customTheme"] = {"name": THEME_NAME, "reportVersionAtImport": base["reportVersionAtImport"],
                                                "type": "RegisteredResources"}
    report["publicCustomVisuals"] = [HTML]
    pkgs = [p for p in report.get("resourcePackages", []) if p["name"] != "RegisteredResources"]
    pkgs.append({"name": "RegisteredResources", "type": "RegisteredResources",
                 "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}]})
    report["resourcePackages"] = pkgs
    report.pop("reportSource", None)
    rp.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    write_theme()
    pages_dir = DEF / "pages"
    for d in pages_dir.iterdir():
        if d.is_dir():
            shutil.rmtree(d)
    pages = [cover(), overview(), acquisition(), content(), funnel(), products(), time_page()]
    for p in pages:
        p.write(DEF)
    meta = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p.pid for p in pages], "activePageName": pages[0].pid}
    (pages_dir / "pages.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("pages:", [(p.name, len(p.visuals)) for p in pages])


if __name__ == "__main__":
    main()
