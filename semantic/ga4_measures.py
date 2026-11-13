"""Report measures for the GA4 Ecommerce model (5-page report).

Single source of truth for every measure the report uses. Base measures already deployed by
nb_semantic_model_ga4 are listed in BASE (two are revised, see REVISED); everything else is new.

    python3 semantic/ga4_measures.py            # writes semantic/ga4_measures.dax (DEFINE block, testable)
    python3 semantic/ga4_measures.py --json     # writes semantic/ga4_measures.json (for the notebook upsert)

Folder convention follows the report pages:  Pages\\01 Overview … Pages\\05 Products,
plus Base\\… for shared building blocks and Components\\… for HTML visuals (HTML Content visual).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
M: list[dict] = []

F_INT, F_USD, F_USD2, F_PCT = "#,##0", "$#,##0", "$#,##0.00", "0.00%"
F_DPCT, F_DPTS, F_DUSD = "+0.0%;-0.0%;0.0%", "+0.00\" pts\";-0.00\" pts\";0.00\" pts\"", "+$#,##0;-$#,##0;$0"

P = {1: r"Pages\01 Overview", 2: r"Pages\02 Acquisition", 3: r"Pages\03 Content", 4: r"Pages\04 Funnel",
     5: r"Pages\05 Products", 6: r"Pages\06 Time Intelligence", 0: r"Pages\00 Welcome"}
BASE_F, TIME_F, PP_F, TXT_F, CMP_F = r"Base\Core", r"Base\Time", r"Base\Prior Period", r"Base\Text", r"Components"


def add(name, expr, folder, fmt=None, desc="", hidden=False, kind="new"):
    M.append({"name": name, "expr": expr.strip(), "folder": folder, "format": fmt, "description": desc,
              "hidden": hidden, "kind": kind})


# ======================================================================================== base (deployed)
# Already in the model; listed so the .dax file is complete and testable. Unchanged unless in REVISED.
BASE_NAMES = ["Sessions", "Users", "New Users", "Engaged Sessions", "Engagement Rate", "Purchases", "Revenue",
              "Conversion Rate", "Revenue per Session", "Revenue Share of Top Channel", "Pageviews",
              "View Item Sessions", "Add to Cart Sessions", "Begin Checkout Sessions", "Add Payment Info Sessions",
              "Purchase Sessions", "View Item to Cart Rate", "Cart to Checkout Rate", "Checkout to Payment Rate",
              "Payment to Purchase Rate", "View Item to Purchase Rate", "Item Views", "Add to Carts", "Item Revenue",
              "Add-to-Cart Rate"]

# ---- revised / added core
add("Transactions", "SUM('Sessions'[transactions])", BASE_F, F_INT,
    "Distinct purchase transactions (transaction_id). 5,281 vs 5,692 purchase events: some transactions fire purchase twice.")
add("AOV", "DIVIDE([Revenue], [Transactions])", BASE_F, F_USD2,
    "REVISED. Average order value = Revenue / Transactions. The deployed version divides by purchase events, "
    "which double-counts duplicated purchase hits and understates AOV ($63.63 vs $68.58).", kind="revised")
add("Revenue per Purchase Event", "DIVIDE([Revenue], [Purchases])", BASE_F, F_USD2,
    "The previous AOV definition, kept for reconciliation only.", hidden=True)
add("Converting Sessions", "CALCULATE([Sessions], 'Sessions'[purchases] > 0)", BASE_F, F_INT,
    "Sessions with at least one purchase; numerator of Conversion Rate.")
add("Returning Users", "CALCULATE(DISTINCTCOUNT('Sessions'[user_pseudo_id]), 'Sessions'[is_new_user] = FALSE())",
    BASE_F, F_INT, "Distinct users with a session that is not their first.")
add("New User Share", "DIVIDE([New Users], [Users])", BASE_F, F_PCT)
add("Pages per Session", "DIVIDE(SUM('Sessions'[pageviews]), [Sessions])", BASE_F, "0.00")
add("Avg Engagement Time (sec)", "AVERAGE('Sessions'[engagement_time_sec])", BASE_F, "0.0",
    "Mean engaged seconds per session (sum of engagement_time_msec / 1000).")
add("Avg Engagement Time", """
VAR _s = [Avg Engagement Time (sec)]
RETURN IF(ISBLANK(_s), BLANK(), FORMAT(INT(_s / 60), "0") & "m " & FORMAT(MOD(INT(_s), 60), "00") & "s")""",
    BASE_F, None, "Text, e.g. 1m 10s.")
add("Event Param Attribution Share",
    "DIVIDE(CALCULATE([Sessions], 'Sessions'[attribution_source] = \"event_params\"), [Sessions])", BASE_F, F_PCT,
    "Share of sessions whose source/medium came from session event params (the rest fall back to first-touch traffic_source).")

# ======================================================================================== time
add("Period Start", "MIN('Date'[date])", TIME_F, "mmm d, yyyy", hidden=True)
add("Period End", "MAX('Date'[date])", TIME_F, "mmm d, yyyy", hidden=True)
add("Period Days", "INT([Period End] - [Period Start]) + 1", TIME_F, "0", hidden=True)
add("Period Label", """
VAR _s = [Period Start]
VAR _e = [Period End]
RETURN
SWITCH(TRUE(),
    ISBLANK(_s), BLANK(),
    _s = DATE(YEAR(_s), MONTH(_s), 1) && _e = EOMONTH(_s, 0), FORMAT(_s, "mmmm yyyy"),
    YEAR(_s) = YEAR(_e), FORMAT(_s, "mmm d") & " – " & FORMAT(_e, "mmm d, yyyy"),
    FORMAT(_s, "mmm d, yyyy") & " – " & FORMAT(_e, "mmm d, yyyy"))""", TIME_F, None,
    "Selected window as text: 'December 2020', 'Nov 1 – Nov 30, 2020'.")

# Prior period = previous calendar month when a whole month is selected, otherwise the same number of days
# immediately before the selection. Blank when that window falls before the first day of data.
PP_VARS = """VAR _s = [Period Start]
VAR _e = [Period End]
VAR _d = [Period Days]
VAR _full = _s = DATE(YEAR(_s), MONTH(_s), 1) && _e = EOMONTH(_s, 0)
VAR _ps = IF(_full, EDATE(_s, -1), _s - _d)
VAR _pe = IF(_full, EOMONTH(_s, -1), _s - 1)
VAR _min = CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))"""
add("PP Start", PP_VARS + "\nRETURN IF(_ps >= _min, _ps)", TIME_F, "mmm d, yyyy", hidden=True)
add("PP End", PP_VARS + "\nRETURN IF(_ps >= _min, _pe)", TIME_F, "mmm d, yyyy", hidden=True)
add("PP Label", """
VAR _ps = [PP Start]
VAR _pe = [PP End]
RETURN
SWITCH(TRUE(),
    ISBLANK(_ps), "no earlier period in data",
    _ps = DATE(YEAR(_ps), MONTH(_ps), 1) && _pe = EOMONTH(_ps, 0), "vs " & FORMAT(_ps, "mmm yyyy"),
    "vs prior " & FORMAT(INT(_pe - _ps) + 1, "0") & " days")""", TIME_F, None,
    "Comparison label used under every KPI: 'vs Nov 2020' or 'vs prior 14 days'.")

PP = {  # metric -> (format of value, delta kind)
    "Sessions": (F_INT, "pct"), "Users": (F_INT, "pct"), "New Users": (F_INT, "pct"), "Revenue": (F_USD, "pct"),
    "Transactions": (F_INT, "pct"), "Conversion Rate": (F_PCT, "pts"), "AOV": (F_USD2, "pct"),
    "Revenue per Session": (F_USD2, "pct"), "Engagement Rate": (F_PCT, "pts"), "Pageviews": (F_INT, "pct"),
    "Pages per Session": ("0.00", "pct"), "Avg Engagement Time (sec)": ("0.0", "pct"),
    "View Item Sessions": (F_INT, "pct"), "Begin Checkout Sessions": (F_INT, "pct"), "Purchase Sessions": (F_INT, "pct"),
    "View Item to Purchase Rate": (F_PCT, "pts"), "Cart Abandonment Rate": (F_PCT, "pts"),
    "Item Revenue": (F_USD, "pct"), "Units Purchased": (F_INT, "pct"), "Avg Item Price": (F_USD2, "pct"),
    "Items Sold": (F_INT, "pct"), "Top 10 Item Revenue Share": (F_PCT, "pts"),
}


def add_pp():
    for m, (fmt, kind) in PP.items():
        add(f"{m} PP", PP_VARS + f"\nRETURN IF(_ps >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _ps, _pe)))",
            PP_F, fmt, f"{m} in the prior period (see PP Label).")
        if kind == "pct":
            add(f"{m} Δ%", f"VAR _p = [{m} PP]\nRETURN IF(NOT ISBLANK(_p), DIVIDE([{m}] - _p, _p))", PP_F, F_DPCT)
        else:
            add(f"{m} Δ pts", f"VAR _p = [{m} PP]\nRETURN IF(NOT ISBLANK(_p), ([{m}] - _p) * 100)", PP_F, F_DPTS)


# Rolling 7 days anchored on the last selected day (Traffic Report pattern)
for m, fmt in (("Sessions", F_INT), ("Revenue", F_USD)):
    add(f"{m} L7D", f"VAR _e = [Period End]\nRETURN CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - 6, _e))",
        TIME_F, fmt, f"{m} in the 7 days ending on the last selected day.")
    add(f"{m} P7D", f"""VAR _e = [Period End]
VAR _min = CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))
RETURN IF(_e - 13 >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - 13, _e - 7)))""", TIME_F, fmt)
    add(f"{m} WoW %", f"VAR _p = [{m} P7D]\nRETURN IF(NOT ISBLANK(_p), DIVIDE([{m} L7D] - _p, _p))", TIME_F, F_DPCT)
add("Daily Avg Sessions", "DIVIDE([Sessions], [Period Days])", TIME_F, F_INT)
add("Daily Avg Revenue", "DIVIDE([Revenue], [Period Days])", TIME_F, F_USD)

# Rolling windows: last N days ending on the last selected day vs the N days before (7 / 14 / 28).
ROLL_F = r"Base\Time\Rolling Windows"
ROLL = {  # metric -> (format, delta kind)
    "Sessions": (F_INT, "pct"), "Engaged Sessions": (F_INT, "pct"), "Pageviews": (F_INT, "pct"),
    "Transactions": (F_INT, "pct"), "Revenue": (F_USD, "pct"), "Conversion Rate": (F_PCT, "pts"),
    "AOV": (F_USD2, "pct"), "Revenue per Session": (F_USD2, "pct")}
for n in (7, 14, 28):
    for m, (fmt, kind) in ROLL.items():
        ln, pn = f"{m} L{n}D", f"{m} P{n}D"
        if not (n == 7 and m in ("Sessions", "Revenue")):  # those two already exist above
            add(ln, f"VAR _e = [Period End]\nRETURN CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - {n - 1}, _e))", ROLL_F, fmt,
                f"{m} in the {n} days ending on the last selected day.")
            add(pn, f"""VAR _e = [Period End]
VAR _min = CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))
RETURN IF(_e - {2 * n - 1} >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - {2 * n - 1}, _e - {n})))""", ROLL_F, fmt,
                f"{m} in the {n} days before the last {n} days (blank when that falls before Nov 1).")
        if kind == "pct":
            add(f"{m} L{n}D Δ%", f"VAR _p = [{pn}]\nRETURN IF(NOT ISBLANK(_p), DIVIDE([{ln}] - _p, _p))", ROLL_F, F_DPCT)
        else:
            add(f"{m} L{n}D Δ pts", f"VAR _p = [{pn}]\nRETURN IF(NOT ISBLANK(_p), ([{ln}] - _p) * 100)", ROLL_F, F_DPTS)

# Week over week for every KPI card (pages 1-5): last 7 days ending on the last selected day vs the 7 days before.
# Sessions, Revenue, Conversion Rate, AOV, Transactions, Revenue per Session and Pageviews already exist above (Time / Rolling Windows).
WOW_EXTRA = {"New Users": (F_INT, "pct"), "Engagement Rate": (F_PCT, "pts"), "Pages per Session": ("0.00", "pct"),
             "Avg Engagement Time (sec)": ("0.0", "pct"), "View Item Sessions": (F_INT, "pct"),
             "Begin Checkout Sessions": (F_INT, "pct"), "Purchase Sessions": (F_INT, "pct"),
             "Cart Abandonment Rate": (F_PCT, "pts"), "Item Revenue": (F_USD, "pct"), "Units Purchased": (F_INT, "pct"),
             "Avg Item Price": (F_USD2, "pct"), "Items Sold": (F_INT, "pct")}
for m, (fmt, kind) in WOW_EXTRA.items():
    add(f"{m} L7D", f"""VAR _e = [Period End]
VAR _min = CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))
RETURN IF(_e - 6 >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - 6, _e)))""", ROLL_F, fmt,
        f"{m} in the 7 days ending on the last selected day.")
    add(f"{m} P7D", f"""VAR _e = [Period End]
VAR _min = CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))
RETURN IF(_e - 13 >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - 13, _e - 7)))""", ROLL_F, fmt,
        f"{m} in the 7 days before the last 7 days.")
    if kind == "pct":
        add(f"{m} L7D Δ%", f"VAR _p = [{m} P7D]\nRETURN IF(NOT ISBLANK(_p), DIVIDE([{m} L7D] - _p, _p))", ROLL_F, F_DPCT)
    else:
        add(f"{m} L7D Δ pts", f"VAR _p = [{m} P7D]\nRETURN IF(NOT ISBLANK(_p), ([{m} L7D] - _p) * 100)", ROLL_F, F_DPTS)

# ======================================================================================== 01 Overview
add("Top Channel", """
VAR _t = ADDCOLUMNS(ALLSELECTED('Channel'[channel_group]), "@r", [Revenue])
RETURN MAXX(TOPN(1, _t, [@r], DESC), 'Channel'[channel_group])""", P[1], None, "Channel with the most revenue in the selection.")
add("Peak Season Revenue", "CALCULATE([Revenue], 'Date'[is_peak_season] = TRUE())", P[1], F_USD,
    "Revenue on peak-season days (dim_ga4_date.is_peak_season: Black Friday week to Christmas).")
add("Peak Season Revenue Share", "DIVIDE([Peak Season Revenue], [Revenue])", P[1], F_PCT)
add("Peak Season Day Share",
    "DIVIDE(CALCULATE(COUNTROWS('Date'), 'Date'[is_peak_season] = TRUE()), COUNTROWS('Date'))", P[1], F_PCT)
add("Peak Season Conversion Rate", "CALCULATE([Conversion Rate], 'Date'[is_peak_season] = TRUE())", P[1], F_PCT)
add("Off-Peak Conversion Rate", "CALCULATE([Conversion Rate], 'Date'[is_peak_season] = FALSE())", P[1], F_PCT)
add("Peak Conversion Lift", """
VAR _p = [Peak Season Conversion Rate]
VAR _o = [Off-Peak Conversion Rate]
RETURN IF(NOT ISBLANK(_p) && NOT ISBLANK(_o), DIVIDE(_p, _o) - 1)""", P[1], F_DPCT,
    "Peak-season conversion rate vs off-peak, relative. Blank unless the selection has both kinds of day.")
add("Best Revenue Day", """
VAR _t = ADDCOLUMNS(VALUES('Date'[date]), "@r", [Revenue])
VAR _top = TOPN(1, _t, [@r], DESC)
RETURN FORMAT(MAXX(_top, 'Date'[date]), "ddd, mmm d") & " · $" & FORMAT(MAXX(_top, [@r]), "#,##0")""",
    P[1], None)
add("Holiday Day Revenue", "CALCULATE([Revenue], NOT ISBLANK('Date'[holiday_name]))", P[1], F_USD,
    "Revenue on Black Friday, Cyber Monday, Christmas and New Year days.")
add("01 Headline", """
VAR _r = [Revenue]
VAR _d = [Revenue Δ%]
VAR _ch = [Top Channel]
VAR _sh = [Revenue Share of Top Channel]
VAR _peak = [Peak Season Revenue Share]
VAR _peakDays = [Peak Season Day Share]
RETURN
IF(ISBLANK(_d),
    FORMAT(_peakDays, "0%") & " of the days brought " & FORMAT(_peak, "0%") & " of the revenue.",
    "Revenue " & IF(_d >= 0, "grew ", "fell ") & FORMAT(ABS(_d), "0%") & " " & [PP Label] & ", and " & _ch &
    " carried " & FORMAT(_sh, "0%") & " of it.")""", P[1], None,
    "Story headline for page 1 (finding first, then the driver).")

# ======================================================================================== 02 Acquisition
ALLSEL_CH = ("ALLSELECTED('Channel'), ALLSELECTED('Device'), "
             "ALLSELECTED('Sessions'[session_source], 'Sessions'[session_medium], 'Sessions'[session_campaign])")
add("Session Share", f"DIVIDE([Sessions], CALCULATE([Sessions], {ALLSEL_CH}))", P[2], F_PCT,
    "Share of selected sessions for channel, device or source/medium rows.")
add("Revenue Share", f"DIVIDE([Revenue], CALCULATE([Revenue], {ALLSEL_CH}))", P[2], F_PCT)
add("Revenue Index", "DIVIDE([Revenue Share], [Session Share])", P[2], "0.00\"×\"",
    "Revenue share ÷ session share. Above 1× the row earns more than the traffic it brings.")
add("Site Conversion Rate", f"CALCULATE([Conversion Rate], {ALLSEL_CH})", P[2], F_PCT, hidden=True)
add("Conversion vs Site", "([Conversion Rate] - [Site Conversion Rate]) * 100", P[2], F_DPTS,
    "Conversion rate gap to the selection average, in percentage points.")
add("Channel Revenue Rank", "IF(ISINSCOPE('Channel'[channel_group]), RANKX(ALLSELECTED('Channel'[channel_group]), [Revenue]))",
    P[2], "0")
SELF_REF = "'Sessions'[session_source] = \"shop.googlemerchandisestore.com\""
add("Self-Referral Revenue", f"CALCULATE([Revenue], {SELF_REF})", P[2], F_USD,
    "Revenue attributed to the store's own domain as a referrer — an attribution leak (cross-domain/checkout "
    "redirect), not a real partner.")
add("Self-Referral Revenue Share", "DIVIDE([Self-Referral Revenue], [Revenue])", P[2], F_PCT)
add("Self-Referral Sessions", f"CALCULATE([Sessions], {SELF_REF})", P[2], F_INT)
add("02 Headline", """
VAR _t = ADDCOLUMNS(ALLSELECTED('Channel'[channel_group]), "@s", [Sessions], "@r", [Revenue])
VAR _ts = CALCULATE([Sessions], ALLSELECTED('Channel'))
VAR _tr = CALCULATE([Revenue], ALLSELECTED('Channel'))
VAR _vol = MAXX(TOPN(1, _t, [@s], DESC), 'Channel'[channel_group])
VAR _volS = DIVIDE(MAXX(TOPN(1, _t, [@s], DESC), [@s]), _ts)
VAR _volR = DIVIDE(MAXX(TOPN(1, _t, [@s], DESC), [@r]), _tr)
VAR _rev = MAXX(TOPN(1, _t, [@r], DESC), 'Channel'[channel_group])
VAR _revR = DIVIDE(MAXX(TOPN(1, _t, [@r], DESC), [@r]), _tr)
RETURN
IF(_vol = _rev,
    _vol & " leads both traffic (" & FORMAT(_volS, "0%") & ") and revenue (" & FORMAT(_revR, "0%") & ").",
    _vol & " brings " & FORMAT(_volS, "0%") & " of sessions but " & FORMAT(_volR, "0%") & " of revenue; " &
    _rev & " earns " & FORMAT(_revR, "0%") & ".")""", P[2], None)

# ======================================================================================== 03 Content
add("Entrances", "SUM('Page Sessions'[entrances])", P[3], F_INT)
add("Exits", "SUM('Page Sessions'[exits])", P[3], F_INT)
add("Exit Rate", "DIVIDE([Exits], [Pageviews])", P[3], F_PCT, "Exits ÷ pageviews of the page.")
add("Page Sessions", "SUM('Page Sessions'[sessions])", P[3], F_INT,
    "Sessions that viewed the page (date × URL grain; not additive across pages).")
add("Page Avg Engagement Time (sec)",
    "DIVIDE(SUMX('Page Sessions', 'Page Sessions'[sessions] * 'Page Sessions'[avg_engagement_time_sec]), [Page Sessions])",
    P[3], "0.0", "Session-weighted average of avg_engagement_time_sec (never a plain AVERAGE of the averages).")
add("Landing Session Share", "DIVIDE([Sessions], CALCULATE([Sessions], ALLSELECTED('Page Type')))", P[3], F_PCT)
add("Landing Revenue Share", "DIVIDE([Revenue], CALCULATE([Revenue], ALLSELECTED('Page Type')))", P[3], F_PCT)
add("Landing RPS Index",
    "DIVIDE([Revenue per Session], CALCULATE([Revenue per Session], ALLSELECTED('Page Type')))", P[3], "0.00\"×\"",
    "Landing page revenue per session ÷ selection average.")
add("Landing Page Role", """
VAR _sh = [Landing Session Share]
VAR _ix = [Landing RPS Index]
RETURN
SWITCH(TRUE(),
    ISBLANK([Sessions]), BLANK(),
    _sh >= 0.02 && _ix >= 1, "Earner",
    _sh >= 0.02, "Attractor",
    _ix >= 1, "Hidden gem",
    "Long tail")""", P[3], None,
    "Earner = high traffic and above-average revenue per session; Attractor = high traffic, below-average yield; "
    "Hidden gem = small but above-average yield. High traffic = at least 2% of landing sessions.")
add("Home Session Share",
    "DIVIDE(CALCULATE([Sessions], 'Page Type'[page_type] = \"home\"), CALCULATE([Sessions], ALLSELECTED('Page Type')))", P[3], F_PCT)
add("Home Revenue Share",
    "DIVIDE(CALCULATE([Revenue], 'Page Type'[page_type] = \"home\"), CALCULATE([Revenue], ALLSELECTED('Page Type')))", P[3], F_PCT)
add("03 Headline", """
VAR _t = FILTER(ADDCOLUMNS(ALLSELECTED('Page Type'[page_path]), "@s", [Sessions], "@rps", [Revenue per Session]), [@s] > 0)
VAR _site = CALCULATE([Revenue per Session], ALLSELECTED('Page Type'))
VAR _big = FILTER(_t, DIVIDE([@s], SUMX(_t, [@s])) >= 0.02 && [@rps] < _site)
VAR _top = TOPN(1, _big, [@s], DESC)
VAR _path = MAXX(_top, 'Page Type'[page_path])
VAR _name = SUBSTITUTE(PATHITEMREVERSE(SUBSTITUTE(_path, "/", "|"), 1), "+", " ")
VAR _s = MAXX(_top, [@s])
VAR _ix = DIVIDE(MAXX(_top, [@rps]), _site)
RETURN
"Home lands " & FORMAT([Home Session Share], "0%") & " of sessions and " & FORMAT([Home Revenue Share], "0%") & " of revenue" &
IF(NOT ISBLANK(_path), "; " & _name & " pulls " & FORMAT(_s / 1000, "0.0") & "K sessions at " & FORMAT(_ix, "0.00") & "× the average yield.", ".")""",
    P[3], None, "Story headline for page 3: the home page's weight, then the biggest attractor (high traffic, low yield).")

# ======================================================================================== 04 Funnel
CART_WIN = "KEEPFILTERS(DATESBETWEEN('Date'[date], [Cart Tracking Start], BLANK()))"
add("Cart Tracking Start", "DATE(2020, 11, 25)", P[4], "mmm d, yyyy",
    "The GA4 sample has almost no add_to_cart events before 2020-11-25 (0 on most days, a short burst on Nov 16-19). "
    "Every rate that uses the cart step is computed from this date on.", hidden=True)
add("View Item to Cart Rate", f"CALCULATE(DIVIDE([Add to Cart Sessions], [View Item Sessions]), {CART_WIN})", P[4], F_PCT,
    "REVISED. Add to Cart Sessions / View Item Sessions on days with add_to_cart tracking (from Cart Tracking Start).",
    kind="revised")
add("Cart to Checkout Rate", f"CALCULATE(DIVIDE([Begin Checkout Sessions], [Add to Cart Sessions]), {CART_WIN})", P[4], F_PCT,
    "REVISED. Begin Checkout Sessions / Add to Cart Sessions on days with add_to_cart tracking.", kind="revised")
add("Cart Window Note", """
IF([Period Start] < [Cart Tracking Start],
    "Cart step measured from " & FORMAT([Cart Tracking Start], "mmm d") & " (add_to_cart not tracked earlier).")""",
    P[4], None, "Footnote shown under the funnel when the selection starts before cart tracking.")
add("Session to View Item Rate", "DIVIDE([View Item Sessions], [Sessions])", P[4], F_PCT,
    "Share of sessions that viewed a product. Note: Page Type filters reach Sessions but not Funnel Daily.")
add("Cart Abandonment Rate", f"CALCULATE(1 - DIVIDE([Purchase Sessions], [Add to Cart Sessions]), {CART_WIN})", P[4], F_PCT,
    "Share of add-to-cart sessions that did not purchase, on days with add_to_cart tracking.")
add("Checkout Abandonment Rate", "1 - DIVIDE([Purchase Sessions], [Begin Checkout Sessions])", P[4], F_PCT)
add("Lost at View to Cart", "[View Item Sessions] - [Add to Cart Sessions]", P[4], F_INT)
add("Lost at Cart to Checkout", "[Add to Cart Sessions] - [Begin Checkout Sessions]", P[4], F_INT)
add("Lost at Checkout to Payment", "[Begin Checkout Sessions] - [Add Payment Info Sessions]", P[4], F_INT)
add("Lost at Payment to Purchase", "[Add Payment Info Sessions] - [Purchase Sessions]", P[4], F_INT)
add("Biggest Drop Step", """
VAR _t = {
    ("View item → Add to cart", [View Item to Cart Rate]),
    ("Add to cart → Checkout", [Cart to Checkout Rate]),
    ("Checkout → Payment", [Checkout to Payment Rate]),
    ("Payment → Purchase", [Payment to Purchase Rate]) }
RETURN CONCATENATEX(TOPN(1, _t, [Value2], ASC), [Value1], "")""", P[4], None,
    "Step with the lowest step-to-step rate.")
add("04 Headline", """
VAR _vi = [View Item Sessions]
VAR _ps = [Purchase Sessions]
VAR _step = [Biggest Drop Step]
VAR _rate = MINX({[View Item to Cart Rate], [Cart to Checkout Rate], [Checkout to Payment Rate], [Payment to Purchase Rate]}, [Value])
RETURN
"Of every 100 product viewers, " & FORMAT(DIVIDE(_ps, _vi) * 100, "0.0") & " buy. The leak is " & _step &
": only " & FORMAT(_rate, "0%") & " move on.\"""", P[4], None)

# ======================================================================================== 05 Products
ITEM_ALL = "ALLSELECTED('Items Daily'[item_name], 'Items Daily'[item_id], 'Items Daily'[item_category], 'Items Daily'[item_brand])"
add("Units Purchased", "SUM('Items Daily'[purchases])", P[5], F_INT, "Purchased item quantity.")
add("Checkout Item Rows", "SUM('Items Daily'[checkouts])", P[5], F_INT,
    "Item rows in begin_checkout events (fully unnested). Rows, not quantity.")
add("Avg Item Price", "DIVIDE([Item Revenue], [Units Purchased])", P[5], F_USD2)
add("Items Sold", "CALCULATE(DISTINCTCOUNT('Items Daily'[item_id]), 'Items Daily'[purchases] > 0)", P[5], F_INT)
add("Item Revenue Share", f"DIVIDE([Item Revenue], CALCULATE([Item Revenue], {ITEM_ALL}))", P[5], F_PCT)
add("Item Revenue Rank", "IF(ISINSCOPE('Items Daily'[item_name]), RANKX(ALLSELECTED('Items Daily'[item_name]), [Item Revenue]))",
    P[5], "0")
add("Top 10 Item Revenue Share", f"""
VAR _t = ADDCOLUMNS(CALCULATETABLE(VALUES('Items Daily'[item_name]), {ITEM_ALL}), "@r", CALCULATE([Item Revenue]))
RETURN DIVIDE(SUMX(TOPN(10, _t, [@r], DESC), [@r]), SUMX(_t, [@r]))""", P[5], F_PCT,
    "Concentration: share of item revenue from the ten best-selling items.")
add("Items for Half of Revenue", """
VAR _t = ADDCOLUMNS(VALUES('Items Daily'[item_name]), "@r", CALCULATE([Item Revenue]))
VAR _tot = SUMX(_t, [@r])
VAR _ranked = ADDCOLUMNS(_t, "@cum", VAR _me = [@r] RETURN SUMX(FILTER(_t, [@r] >= _me), [@r]))
RETURN COUNTROWS(FILTER(_ranked, [@cum] - [@r] < _tot / 2))""", P[5], F_INT,
    "Pareto: how many items (best first) it takes to reach 50% of item revenue.")
add("Top Item", """
VAR _t = ADDCOLUMNS(VALUES('Items Daily'[item_name]), "@r", CALCULATE([Item Revenue]))
RETURN MAXX(TOPN(1, _t, [@r], DESC), 'Items Daily'[item_name])""", P[5], None)
add("Top Category", """
VAR _t = ADDCOLUMNS(VALUES('Items Daily'[item_category]), "@r", CALCULATE([Item Revenue]))
RETURN MAXX(TOPN(1, _t, [@r], DESC), 'Items Daily'[item_category])""", P[5], None)
add("Top Category Revenue Share", """
VAR _t = ADDCOLUMNS(VALUES('Items Daily'[item_category]), "@r", CALCULATE([Item Revenue]))
RETURN DIVIDE(MAXX(_t, [@r]), SUMX(_t, [@r]))""", P[5], F_PCT)
add("Item Data Check", """
IF([Add to Carts] > [Item Views],
    "Item views are under-counted in gold (add-to-carts exceed views), so item-level view → cart rates are not shown.",
    BLANK())""", P[5], None, "Data-quality guard for the item funnel; shown as a footnote while the gold fix is pending.")
add("05 Headline", """
"Ten items earn " & FORMAT([Top 10 Item Revenue Share], "0%") & " of item revenue; " & [Top Category] &
" alone is " & FORMAT([Top Category Revenue Share], "0%") & ".\"""", P[5], None)

add_pp()


# ======================================================================================== HTML components
TOK = dict(ink="#1E1B4B", sub="#5B5F86", muted="#9A9DC0", acc="#5B5BD6", acc2="#8B8CF0", soft="#ECEDFD",
           line="#E6E7F5", good="#0E9F6E", bad="#E5484D", card="#FFFFFF")
FONT = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"


def fmt_dax(var, kind):
    return {
        "int": f'IF({var} >= 1E6, FORMAT({var} / 1E6, "0.00") & "M", IF({var} >= 1E4, FORMAT({var} / 1E3, "0.0") & "K", FORMAT({var}, "#,##0")))',
        "usd": f'"$" & IF({var} >= 1E6, FORMAT({var} / 1E6, "0.00") & "M", IF({var} >= 1E4, FORMAT({var} / 1E3, "0.0") & "K", FORMAT({var}, "#,##0")))',
        "usd2": f'"$" & FORMAT({var}, "0.00")',
        "pct": f'FORMAT({var}, "0.00%")',
        "sec": f'FORMAT(INT({var} / 60), "0") & "m " & FORMAT(MOD(INT({var}), 60), "00") & "s"',
        "num2": f'FORMAT({var}, "0.00")',
    }[kind]


ICON = {
    "dollar": "<path d='M12 2v20M17 6.5C17 4.6 14.8 4 12 4S7 5 7 7.5 9.5 10.5 12 11s5 1.5 5 4-2.2 3.5-5 3.5-5-.8-5-2.8'/>",
    "users": "<circle cx='9' cy='8' r='3.5'/><path d='M2.5 20a6.5 6.5 0 0 1 13 0'/><path d='M16 4.5a3.5 3.5 0 0 1 0 7M18.5 20a6.5 6.5 0 0 0-3-5.5'/>",
    "target": "<circle cx='12' cy='12' r='9'/><circle cx='12' cy='12' r='5'/><circle cx='12' cy='12' r='1'/>",
    "tag": "<path d='M3 12V3h9l9 9-9 9z'/><circle cx='7.5' cy='7.5' r='1.5'/>",
    "receipt": "<path d='M6 3h12v18l-3-2-3 2-3-2-3 2z'/><path d='M9 8h6M9 12h6'/>",
    "eye": "<path d='M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z'/><circle cx='12' cy='12' r='3'/>",
    "layers": "<path d='M12 3l9 5-9 5-9-5z'/><path d='M3 13l9 5 9-5'/>",
    "clock": "<circle cx='12' cy='12' r='9'/><path d='M12 7v5l3 2'/>",
    "cart": "<circle cx='9' cy='20' r='1.5'/><circle cx='18' cy='20' r='1.5'/><path d='M2 3h3l2.5 12h11L21 7H6'/>",
    "funnel": "<path d='M3 4h18l-7 8v6l-4 2v-8z'/>",
    "box": "<path d='M3 7l9-4 9 4v10l-9 4-9-4z'/><path d='M3 7l9 4 9-4M12 11v10'/>",
    "cal": "<rect x='3' y='5' width='18' height='16' rx='2'/><path d='M3 10h18M8 3v4M16 3v4'/>",
    "bolt": "<path d='M13 2L4 14h7l-1 8 9-12h-7z'/>",
}
KICON = {"Revenue": "dollar", "Sessions": "users", "Conversion rate": "target", "Average order value": "tag", "Transactions": "receipt",
         "New users": "users", "Engagement rate": "bolt", "Revenue per session": "dollar", "Pageviews": "eye", "Pages per session": "layers",
         "Engagement time": "clock", "Product viewers": "eye", "Checkout sessions": "cart", "Buyers": "receipt", "Cart abandonment": "funnel",
         "Item revenue": "dollar", "Units sold": "box", "Average item price": "tag", "Distinct items sold": "layers",
         "Revenue MTD": "dollar", "Sessions MTD": "users", "Conversion MTD": "target", "Revenue last 7 days": "cal", "Revenue 7-day average": "bolt"}
PRIOR = {"Revenue MTD vs PMTD %": "Revenue PMTD", "Sessions MTD vs PMTD %": "Sessions PMTD", "Conversion Rate MTD vs PMTD pts": "Conversion Rate PMTD",
         "Revenue WoW %": "Revenue P7D", "Revenue Momentum %": "Revenue 28D Avg"}
KCSS = (f"*{{box-sizing:border-box;margin:0;padding:0}}html,body{{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:#1A1840}}"
        f".row{{display:flex;gap:12px;height:100vh;padding:1px}}.k{{position:relative;overflow:hidden;flex:1;min-width:0;background:#fff;border:1px solid #ECEDF6;border-radius:16px;padding:14px 16px 12px;display:flex;flex-direction:column;box-shadow:0 1px 2px rgba(26,24,64,.04)}}"
        f".h{{display:flex;align-items:center;gap:9px}}.i{{width:26px;height:26px;border-radius:8px;background:#EEEFFD;display:grid;place-items:center;flex:none}}"
        f".i svg{{width:14px;height:14px;stroke:#5B5BD6;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}"
        f".l{{font-size:11px;font-weight:600;color:#5E6189;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.n{{font-size:25px;font-weight:800;letter-spacing:-.6px;margin-top:7px;line-height:1}}"
        f".d{{border-top:1px solid #ECEDF6;margin-top:auto;padding-top:7px;display:flex;flex-direction:column;gap:3px}}.r{{display:flex;justify-content:space-between;gap:8px;font-size:10px}}"
        f".r span{{color:#9A9DC0;font-weight:600;letter-spacing:.04em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.r b{{font-weight:700;white-space:nowrap;color:#5E6189}}"
        f".w{{position:absolute;inset:0;background:#1A1840;color:#fff;padding:12px 14px;font-size:10px;line-height:1.45;opacity:0;transition:opacity .2s;pointer-events:none;border-radius:16px}}"
        f".w b{{display:block;font-size:8.5px;letter-spacing:.12em;color:#C9CAF5;margin:6px 0 2px}}.w b:first-child{{margin-top:0}}.k:hover .w{{opacity:1}}")
FONT2 = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Cormorant+Garamond:ital,wght@1,400&display=swap"


KDEF = {  # card label -> (what it is, why it matters). Shown on hover. Keep in sync with design/index.html KDEF.
    "Revenue": ("Purchase revenue in USD from all sessions in the window.", "The bottom line. Every other card explains where it came from."),
    "Sessions": ("Visits to the site. One person can start several sessions.", "Traffic. Revenue rises with visits or with conversion, so read both."),
    "Conversion rate": ("Sessions with a purchase divided by all sessions.", "How well visitors become buyers. Shown in points so small moves stay readable."),
    "Average order value": ("Revenue divided by transactions: what one order is worth.", "Rising AOV with flat conversion means bigger baskets."),
    "Transactions": ("Orders placed in the window, each counted once.", "Revenue equals transactions times AOV. Read them together."),
    "New users": ("Visitors who saw the site for the first time.", "Reach. Many new users with flat revenue means they are not converting yet."),
    "Engagement rate": ("Sessions over 10 seconds, with a conversion, or with 2+ pages.", "Traffic quality. Low engagement means the wrong audience arrived."),
    "Revenue per session": ("Revenue divided by sessions: what one visit is worth.", "Compares channels of any size fairly, because it removes volume."),
    "Pageviews": ("Pages loaded in the window.", "Reach of the content. Read it with pages per session."),
    "Pages per session": ("Pageviews divided by sessions: how deep each visit goes.", "Low depth on busy landing pages means they do not guide people on."),
    "Engagement time": ("Average seconds the site was in focus per session.", "Attention. Long time on a page that earns nothing needs a fix."),
    "Product viewers": ("Sessions that viewed a product page.", "Top of the shopping funnel. Compare with checkout to find the leak."),
    "Checkout sessions": ("Sessions that started checkout.", "Buying intent. A big gap to buyers points at the checkout itself."),
    "Buyers": ("Sessions that completed a purchase.", "The end of the funnel, counted in people rather than percentages."),
    "Cart abandonment": ("Add-to-cart sessions that did not buy, counted from Nov 25.", "Lower is better. Falling with flat sessions is a checkout win."),
    "Item revenue": ("Revenue from products sold, item by item.", "Shows which products carry the money. Can differ from order revenue."),
    "Units sold": ("Items purchased, counting every unit in the basket.", "Volume. Units up with revenue flat means a cheaper mix or discounts."),
    "Average item price": ("Item revenue divided by units sold.", "A falling price with rising units often means promotions drove volume."),
    "Distinct items sold": ("Different products that sold at least once.", "Range. More products selling means less reliance on a few hero items."),
    "Revenue MTD": ("Revenue from the 1st of the month to the last selected day.", "Pace this month, against the same days of the previous month."),
    "Sessions MTD": ("Sessions from the 1st of the month to the last selected day.", "Traffic pace this month, against the same days last month."),
    "Conversion MTD": ("Sessions with a purchase divided by all sessions, month to date.", "Is buying getting easier or harder this month?"),
    "Revenue last 7 days": ("Revenue in the 7 days ending on the last selected day.", "The latest week. The change shows week over week."),
    "Revenue 7-day average": ("Average daily revenue over the last 7 days.", "Above the 28-day average means the business is accelerating."),
}
WOW_TIP = "Week over week: the last 7 days of the selection against the 7 days before them."


def kpi_strip(name, folder, cards, inverse=(), wow=True):
    """cards: (label, measure, kind, delta measure, delta_is_pts[, prior label DAX]).
    wow=True: value row = last 7 days (<measure> L7D), change = week over week (<measure> L7D delta).
    wow=False: prior-period comparison (PP measures), used by the time intelligence page."""
    t = TOK
    v, html = [], []
    for i, card in enumerate(cards):
        label, meas, kind, dm, pts = card[:5]
        good_dir = -1 if label in inverse else 1
        if wow:
            dm = f"{meas} L7D Δ pts" if pts else f"{meas} L7D Δ%"
            pm, plab, clab, tip = f"{meas} L7D", '"Last 7 days"', "WoW", WOW_TIP
        else:
            pm = PRIOR.get(dm, f"{meas} PP")
            plab, clab, tip = (card[5] if len(card) > 5 else "[PP Label]"), "Change", ""
        what, why = KDEF[label]
        v += [f"VAR _v{i} = [{meas}]", f"VAR _d{i} = [{dm}]", f"VAR _p{i} = [{pm}]",
              f"VAR _l{i} = SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({plab}, \"vs \", \"\"), \"no earlier period in data\", \"Prior period\"), \"no prior month in data\", \"Prior month\")",
              f"VAR _f{i} = IF(ISBLANK(_v{i}), \"—\", {fmt_dax(f'_v{i}', kind)})",
              f"VAR _pf{i} = IF(ISBLANK(_p{i}), \"not in data\", {fmt_dax(f'_p{i}', kind)})",
              f"VAR _c{i} = IF(ISBLANK(_d{i}), \"{t['muted']}\", IF(_d{i} * {good_dir} >= 0, \"{t['good']}\", \"{t['bad']}\"))",
              f"VAR _t{i} = IF(ISBLANK(_d{i}), \"—\", IF(_d{i} >= 0, \"▲ +\", \"▼ −\") & " +
              (f"FORMAT(ABS(_d{i}), \"0.00\") & \" pts\")" if pts else f"FORMAT(ABS(_d{i}), \"0.0%\"))")]
        html.append(f"<div class='k'><div class='h'><span class='i'><svg viewBox='0 0 24 24'>{ICON[KICON.get(label, 'dollar')]}</svg></span><span class='l'>{label}</span></div>"
                    f"<div class='n'>\" & _f{i} & \"</div><div class='d'><div class='r'><span>\" & _l{i} & \"</span><b>\" & _pf{i} & \"</b></div>"
                    f"<div class='r' title='{tip}'><span>{clab}</span><b style='color:\" & _c{i} & \"'>\" & _t{i} & \"</b></div></div>"
                    f"<div class='w'><b>WHAT IT IS</b>{what}<b>WHY IT MATTERS</b>{why}</div></div>")
    expr = "\n".join(v) + f"""
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>{KCSS}</style></head><body><div class='row'>""" + "".join(html) + """</div></body></html>\""""
    add(name, expr, folder, None, "HTML Content visual. KPI cards: icon, value, last-7-day value and week-over-week change, hover card with what it is and why it matters.")
    alt = " & \" · \" & ".join(f'"{c[0]} " & {fmt_dax(f"[{c[1]}]", c[2])}' for c in cards)
    add(name.replace("HTML", "Alt Text"), f"{alt} & \" (\" & [Period Label] & \", \" & [PP Label] & \")\"", folder, None,
        "Alt text for the KPI strip.")


TITLES = {1: "Overview", 2: "Acquisition", 3: "Content &amp; Landing", 4: "Funnel", 5: "Products", 6: "Time Intelligence"}


def headline(page, eyebrow=None):
    t = TOK
    add(f"0{page} · 000 Headline HTML", f"""
VAR _h = SUBSTITUTE(SUBSTITUTE([0{page} Headline], "&", "&amp;"), "<", "&lt;")
VAR _c = FORMAT([Period Days], "0") & " days · " & IF(ISBLANK([PP Start]), "no earlier period in data", "compared " & SUBSTITUTE([PP Label], "vs ", "with "))
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>*{{box-sizing:border-box;margin:0;padding:0}}html,body{{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:#1A1840}}.c{{height:100vh;background:#fff;border:1px solid #ECEDF6;border-radius:16px;display:flex;justify-content:space-between;align-items:center;padding:0 22px;gap:24px}}.t{{display:flex;align-items:center;gap:10px}}.n{{font-size:10px;font-weight:800;color:{t['acc']};background:#EEEFFD;border-radius:6px;padding:3px 7px;letter-spacing:.06em}}h1{{font-size:19px;font-weight:800;letter-spacing:-.3px}}p{{font-size:12px;line-height:1.5;color:#5E6189;margin-top:5px;max-width:640px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}.r{{align-self:flex-end;margin-bottom:12px;font-size:10.5px;color:#9A9DC0;white-space:nowrap}}</style></head><body><div class='c'><div><div class='t'><span class='n'>0{page}</span><h1>{TITLES[page]}</h1></div><p>" & _h & "</p></div><div class='r'>" & _c & "</div></div></body></html>\"""",
        P[page], None, "Header card: page title, story headline and the comparison period (date slicer sits on top, right).")


headline(1, "01 / OVERVIEW")
headline(2, "02 / ACQUISITION")
headline(3, "03 / CONTENT")
headline(4, "04 / FUNNEL")
headline(5, "05 / PRODUCTS")
kpi_strip("01 · 001 KPI Strip HTML", P[1], [
    ("Revenue", "Revenue", "usd", "Revenue Δ%", False), ("Sessions", "Sessions", "int", "Sessions Δ%", False),
    ("Conversion rate", "Conversion Rate", "pct", "Conversion Rate Δ pts", True), ("Average order value", "AOV", "usd2", "AOV Δ%", False),
    ("Transactions", "Transactions", "int", "Transactions Δ%", False)])
kpi_strip("02 · 001 KPI Strip HTML", P[2], [
    ("Sessions", "Sessions", "int", "Sessions Δ%", False), ("New users", "New Users", "int", "New Users Δ%", False),
    ("Engagement rate", "Engagement Rate", "pct", "Engagement Rate Δ pts", True),
    ("Revenue per session", "Revenue per Session", "usd2", "Revenue per Session Δ%", False)])
kpi_strip("03 · 001 KPI Strip HTML", P[3], [
    ("Pageviews", "Pageviews", "int", "Pageviews Δ%", False), ("Pages per session", "Pages per Session", "num2", "Pages per Session Δ%", False),
    ("Engagement time", "Avg Engagement Time (sec)", "sec", "Avg Engagement Time (sec) Δ%", False),
    ("Revenue per session", "Revenue per Session", "usd2", "Revenue per Session Δ%", False)])
kpi_strip("04 · 001 KPI Strip HTML", P[4], [
    ("Product viewers", "View Item Sessions", "int", "View Item Sessions Δ%", False),
    ("Checkout sessions", "Begin Checkout Sessions", "int", "Begin Checkout Sessions Δ%", False),
    ("Buyers", "Purchase Sessions", "int", "Purchase Sessions Δ%", False),
    ("Cart abandonment", "Cart Abandonment Rate", "pct", "Cart Abandonment Rate Δ pts", True)], inverse=("Cart abandonment",))
kpi_strip("05 · 001 KPI Strip HTML", P[5], [
    ("Item revenue", "Item Revenue", "usd", "Item Revenue Δ%", False), ("Units sold", "Units Purchased", "int", "Units Purchased Δ%", False),
    ("Average item price", "Avg Item Price", "usd2", "Avg Item Price Δ%", False), ("Distinct items sold", "Items Sold", "int", "Items Sold Δ%", False)])

# Funnel component (page 4)
_t = TOK
add("04 · 002 Funnel HTML", f"""
VAR _st = {{ (1, "Viewed a product", CALCULATE([View Item Sessions], {CART_WIN})),
            (2, "Added to cart", CALCULATE([Add to Cart Sessions], {CART_WIN})),
            (3, "Began checkout", CALCULATE([Begin Checkout Sessions], {CART_WIN})),
            (4, "Added payment", CALCULATE([Add Payment Info Sessions], {CART_WIN})),
            (5, "Purchased", CALCULATE([Purchase Sessions], {CART_WIN})) }}
VAR _note = [Cart Window Note]
VAR _top = MAXX(_st, [Value3])
VAR _min = MINX(FILTER(_st, [Value1] > 1), VAR _i = [Value1] RETURN DIVIDE([Value3], MAXX(FILTER(_st, [Value1] = _i - 1), [Value3])))
VAR _rows = CONCATENATEX(_st,
    VAR _i = [Value1]
    VAR _prev = MAXX(FILTER(_st, [Value1] = _i - 1), [Value3])
    VAR _r = DIVIDE([Value3], _prev)
    VAR _w = DIVIDE([Value3], _top)
    VAR _leak = _i > 1 && _r = _min
    RETURN
    "<div class='r'><div class='lb'>" & [Value2] & "</div><div class='tr'><div class='b" & IF(_leak, " leak", "") &
    "' style='width:" & FORMAT(MAX(_w, 0.02) * 100, "0.0") & "%'></div></div><div class='v'>" & FORMAT([Value3], "#,##0") &
    "</div><div class='p" & IF(_leak, " leak", "") & "'>" & IF(_i = 1, "100%", FORMAT(_r, "0.0%")) & "</div></div>",
    "", [Value1], ASC)
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT}' rel='stylesheet'><style>*{{box-sizing:border-box;margin:0;padding:0}}html,body{{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:{_t['ink']}}}.c{{height:100vh;background:#fff;border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;gap:10px}}.t{{font-size:14px;font-weight:700}}.s{{font-size:10.5px;color:{_t['sub']}}}.r{{display:grid;grid-template-columns:120px 1fr 64px 52px;align-items:center;gap:10px;flex:1}}.lb{{font-size:11.5px;font-weight:600}}.tr{{height:100%;max-height:30px;background:{_t['soft']};border-radius:8px;overflow:hidden}}.b{{height:100%;background:{_t['acc']};border-radius:8px}}.b.leak{{background:{_t['bad']}}}.v{{font-size:12px;font-weight:700;text-align:right}}.p{{font-size:11px;font-weight:700;color:{_t['sub']};text-align:right}}.p.leak{{color:{_t['bad']}}}</style></head><body><div class='c'><div><div class='t'>Purchase funnel</div><div class='s'>Sessions reaching each step · % = step-to-step rate · red = biggest leak" & IF(NOT ISBLANK(_note), " · " & _note) & "</div></div>" & _rows & "</div></body></html>\"""",
    P[4], None, "HTML Content visual: horizontal funnel with step-to-step rates and the leak highlighted.")
add("04 · 002 Funnel Alt Text", """
"Funnel: " & FORMAT([View Item Sessions], "#,##0") & " viewed a product, " & FORMAT([Add to Cart Sessions], "#,##0") &
" added to cart, " & FORMAT([Begin Checkout Sessions], "#,##0") & " began checkout, " & FORMAT([Add Payment Info Sessions], "#,##0") &
" added payment, " & FORMAT([Purchase Sessions], "#,##0") & " purchased. Biggest drop: " & [Biggest Drop Step] & ".\"""", P[4], None)


# ======================================================================================== 06 Time Intelligence
# The sample covers Nov 1 2020 – Jan 31 2021 (92 days): no year-over-year is possible, so the page works with
# month-to-date pacing, rolling averages, running totals, week-over-week and day-of-week patterns.
MIN_D = "CALCULATE(MIN('Date'[date]), REMOVEFILTERS('Date'))"
MTD_VARS = f"""VAR _e = MAX('Date'[date])
VAR _ms = DATE(YEAR(_e), MONTH(_e), 1)
VAR _pms = EDATE(_ms, -1)
VAR _pme = EDATE(_e, -1)
VAR _min = {MIN_D}"""
for m, fmt in (("Revenue", F_USD), ("Sessions", F_INT), ("Transactions", F_INT)):
    add(f"{m} MTD", f"{MTD_VARS}\nRETURN CALCULATE([{m}], DATESBETWEEN('Date'[date], _ms, _e), REMOVEFILTERS('Date'))", TIME_F, fmt,
        f"{m} from the 1st of the month to the last selected day. On a daily axis it is the running month total.")
    add(f"{m} PMTD", f"{MTD_VARS}\nRETURN IF(_pms >= _min, CALCULATE([{m}], DATESBETWEEN('Date'[date], _pms, _pme), REMOVEFILTERS('Date')))",
        TIME_F, fmt, f"{m} for the same days of the previous month (blank before Dec 2020: no October data).")
    add(f"{m} MTD vs PMTD %", f"VAR _p = [{m} PMTD]\nRETURN IF(NOT ISBLANK(_p), DIVIDE([{m} MTD] - _p, _p))", TIME_F, F_DPCT,
        f"Month-to-date pacing of {m} against the same days of the previous month.")
add("Conversion Rate MTD", f"{MTD_VARS}\nRETURN CALCULATE([Conversion Rate], DATESBETWEEN('Date'[date], _ms, _e), REMOVEFILTERS('Date'))", TIME_F, F_PCT)
add("Conversion Rate PMTD", f"{MTD_VARS}\nRETURN IF(_pms >= _min, CALCULATE([Conversion Rate], DATESBETWEEN('Date'[date], _pms, _pme), REMOVEFILTERS('Date')))", TIME_F, F_PCT)
add("Conversion Rate MTD vs PMTD pts", "VAR _p = [Conversion Rate PMTD]\nRETURN IF(NOT ISBLANK(_p), ([Conversion Rate MTD] - _p) * 100)", TIME_F, F_DPTS)
add("MTD Label", f"""{MTD_VARS}
RETURN IF(_pms < _min, "no prior month in data", "vs " & FORMAT(_pms, "mmm") & " 1–" & FORMAT(DAY(_pme), "0"))""", TIME_F, None,
    "Comparison label for MTD cards, e.g. 'vs Dec 1–31'.")
add("Day of Month", "IF(HASONEVALUE('Date'[date]), DAY(MAX('Date'[date])))", TIME_F, "0", hidden=True)

# Running totals inside the selection
add("Revenue Running Total", "VAR _e = MAX('Date'[date])\nRETURN CALCULATE([Revenue], FILTER(ALLSELECTED('Date'), 'Date'[date] <= _e))",
    TIME_F, F_USD, "Cumulative revenue from the first selected day.")
add("Revenue Running Share", "DIVIDE([Revenue Running Total], CALCULATE([Revenue], ALLSELECTED('Date')))", TIME_F, F_PCT,
    "Share of the selection's revenue banked by this day.")

# Rolling averages (trailing window ending on the row's last day, blank until the window is full)
for m, fmt in (("Revenue", F_USD), ("Sessions", F_INT)):
    for n in (7, 28):
        add(f"{m} {n}D Avg", f"""VAR _e = MAX('Date'[date])
VAR _min = {MIN_D}
RETURN IF(_e - {n - 1} >= _min, DIVIDE(CALCULATE([{m}], DATESBETWEEN('Date'[date], _e - {n - 1}, _e), REMOVEFILTERS('Date')), {n}))""",
            TIME_F, fmt, f"Trailing {n}-day daily average of {m}.")
add("Conversion Rate 7D", f"""VAR _e = MAX('Date'[date])
VAR _min = {MIN_D}
RETURN IF(_e - 6 >= _min, CALCULATE([Conversion Rate], DATESBETWEEN('Date'[date], _e - 6, _e), REMOVEFILTERS('Date')))""", TIME_F, F_PCT,
    "Conversion rate over the trailing 7 days (session-weighted, not an average of daily rates).")
add("Revenue Momentum %", "VAR _l = [Revenue 28D Avg]\nRETURN IF(NOT ISBLANK(_l), DIVIDE([Revenue 7D Avg] - _l, _l))", TIME_F, F_DPCT,
    "7-day average vs 28-day average on the last selected day. Positive = accelerating.")
add("Sessions Momentum %", "VAR _l = [Sessions 28D Avg]\nRETURN IF(NOT ISBLANK(_l), DIVIDE([Sessions 7D Avg] - _l, _l))", TIME_F, F_DPCT)

# Week grain (works on 'Date'[week_start] rows: compares with the 7 days before the row's first day)
add("Week Revenue WoW %", f"""VAR _s = MIN('Date'[date])
VAR _e = MAX('Date'[date])
VAR _min = {MIN_D}
VAR _p = IF(_s - 7 >= _min, CALCULATE([Revenue], DATESBETWEEN('Date'[date], _s - 7, _e - 7), REMOVEFILTERS('Date')))
RETURN IF(NOT ISBLANK(_p), DIVIDE([Revenue] - _p, _p))""", P[6], F_DPCT, "Revenue vs the same days one week earlier (use on a week axis).")
add("Week Sessions WoW %", f"""VAR _s = MIN('Date'[date])
VAR _e = MAX('Date'[date])
VAR _min = {MIN_D}
VAR _p = IF(_s - 7 >= _min, CALCULATE([Sessions], DATESBETWEEN('Date'[date], _s - 7, _e - 7), REMOVEFILTERS('Date')))
RETURN IF(NOT ISBLANK(_p), DIVIDE([Sessions] - _p, _p))""", P[6], F_DPCT)
add("Days in Row", "COUNTROWS('Date')", P[6], "0", hidden=True)

# Day-of-week pattern
DOW_ALL = "ALLSELECTED('Date'[day_name], 'Date'[day_short], 'Date'[day_of_week_num], 'Date'[is_weekend])"
add("Avg Daily Revenue (Row)", "DIVIDE([Revenue], COUNTROWS('Date'))", P[6], F_USD, "Revenue per calendar day in the row (fair across weekdays with different day counts).")
add("Avg Daily Sessions (Row)", "DIVIDE([Sessions], COUNTROWS('Date'))", P[6], F_INT)
add("Weekday Revenue Index", f"DIVIDE([Avg Daily Revenue (Row)], CALCULATE([Avg Daily Revenue (Row)], {DOW_ALL}))", P[6], "0.00\"×\"",
    "Average daily revenue for the weekday ÷ average daily revenue overall. 1.2× = 20% above a typical day.")
add("Best Weekday", f"""VAR _t = ADDCOLUMNS(VALUES('Date'[day_name]), "@v", [Avg Daily Revenue (Row)])
RETURN MAXX(TOPN(1, _t, [@v], DESC), 'Date'[day_name])""", P[6], None, "Weekday with the highest average daily revenue.")
add("Worst Weekday", f"""VAR _t = ADDCOLUMNS(VALUES('Date'[day_name]), "@v", [Avg Daily Revenue (Row)])
RETURN MAXX(TOPN(1, _t, [@v], ASC), 'Date'[day_name])""", P[6], None)
add("Best Weekday Index", f"""VAR _t = ADDCOLUMNS(VALUES('Date'[day_name]), "@v", [Weekday Revenue Index])
RETURN MAXX(_t, [@v])""", P[6], "0.00\"×\"")
add("Weekend Revenue Share", "DIVIDE(CALCULATE([Revenue], 'Date'[is_weekend] = TRUE()), [Revenue])", P[6], F_PCT)
add("Weekend Day Share", "DIVIDE(CALCULATE(COUNTROWS('Date'), 'Date'[is_weekend] = TRUE()), COUNTROWS('Date'))", P[6], F_PCT)
add("Weekend Conversion Rate", "CALCULATE([Conversion Rate], 'Date'[is_weekend] = TRUE())", P[6], F_PCT)
add("Weekday Conversion Rate", "CALCULATE([Conversion Rate], 'Date'[is_weekend] = FALSE())", P[6], F_PCT)

add("06 Headline", """
VAR _mtd = [Revenue MTD vs PMTD %]
VAR _mom = [Revenue Momentum %]
VAR _e = MAX('Date'[date])
VAR _best = [Best Weekday]
VAR _bi = [Best Weekday Index]
RETURN
SWITCH(TRUE(),
    NOT ISBLANK(_mtd),
        FORMAT(_e, "mmmm") & " revenue is pacing " & FORMAT(ABS(_mtd), "0%") & IF(_mtd >= 0, " ahead of ", " behind ") &
        "the same days of " & FORMAT(EDATE(_e, -1), "mmmm") & IF(NOT ISBLANK(_mom), ", and the 7-day trend is " &
        FORMAT(ABS(_mom), "0%") & IF(_mom >= 0, " above", " below") & " the 28-day average.", "."),
    NOT ISBLANK(_mom),
        "The 7-day revenue trend ends " & FORMAT(ABS(_mom), "0%") & IF(_mom >= 0, " above", " below") &
        " the 28-day average; " & _best & "s earn " & FORMAT(_bi, "0.0") & "× a typical day.",
    _best & "s earn " & FORMAT(_bi, "0.0") & "× a typical day's revenue.")""", P[6], None,
    "Story headline for the time page: month pacing first, then momentum.")
headline(6, "06 / TIME INTELLIGENCE")

# Rolling-window table (HTML Content): metrics × (7D, 14D, 28D) with value, prior and change.
_t = TOK
_rows = []
for i, (m, (fmt, kind)) in enumerate((k, v) for k, v in ROLL.items() if k not in ("Engaged Sessions", "Revenue per Session")):
    cells = []
    for n in (7, 14, 28):
        d = f"[{m} L{n}D Δ{'%' if kind == 'pct' else ' pts'}]"
        dtxt = (f'IF(ISBLANK({d}), "—", IF({d} >= 0, "▲ +", "▼ −") & FORMAT(ABS({d}), "0.0%"))' if kind == "pct"
                else f'IF(ISBLANK({d}), "—", IF({d} >= 0, "▲ +", "▼ −") & FORMAT(ABS({d}), "0.00") & " pts")')
        cls = f'IF(ISBLANK({d}), "n", IF({d} >= 0, "g", "b"))'
        cells.append(f'"<td>" & {fmt_dax(f"[{m} L{n}D]", {F_INT:"int",F_USD:"usd",F_USD2:"usd2",F_PCT:"pct"}[fmt])} & "</td><td class=\'p\'>" & '
                     f'IF(ISBLANK([{m} P{n}D]), "—", {fmt_dax(f"[{m} P{n}D]", {F_INT:"int",F_USD:"usd",F_USD2:"usd2",F_PCT:"pct"}[fmt])}) & "</td><td><span class=\'" & {cls} & "\'>" & {dtxt} & "</span></td>"')
    _rows.append(f'"<tr><th>{m}</th>" & ' + " & ".join(cells) + ' & "</tr>"')
add("06 · 003 Rolling Table HTML", "\"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='" + FONT + "' rel='stylesheet'><style>"
    f"*{{box-sizing:border-box;margin:0;padding:0}}html,body{{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:{_t['ink']}}}"
    f"table{{width:100%;border-collapse:collapse;font-size:11.5px}}thead th{{font-size:9.5px;font-weight:700;letter-spacing:1px;color:{_t['sub']};text-align:right;padding:6px 8px;border-bottom:1px solid #E6E7F5}}"
    f"thead tr:first-child th{{text-align:center;color:{_t['acc']};border-bottom:none}}tbody th{{text-align:left;font-weight:600;padding:8px}}td{{text-align:right;padding:8px;border-bottom:1px solid #F2F3FA}}"
    f"td.p{{color:{_t['muted']}}}.g,.b,.n{{font-size:10px;font-weight:700;padding:3px 7px;border-radius:99px}}.g{{background:#E3F6EF;color:{_t['good']}}}.b{{background:#FDE8E8;color:{_t['bad']}}}.n{{color:{_t['muted']}}}"
    "</style></head><body><table><thead><tr><th></th><th colspan='3'>LAST 7 DAYS</th><th colspan='3'>LAST 14 DAYS</th><th colspan='3'>LAST 28 DAYS</th></tr>"
    "<tr><th style='text-align:left'>METRIC</th>" + "<th>VALUE</th><th>PRIOR</th><th>CHANGE</th>" * 3 + "</tr></thead><tbody>\" & "
    + " & ".join(_rows) + " & \"</tbody></table></body></html>\"", P[6], None,
    "HTML Content visual: 7/14/28-day windows ending on the last selected day vs the window before, for six metrics.")
add("06 · 003 Rolling Table Alt Text", '"Last 7 days: revenue " & FORMAT([Revenue L7D], "$#,##0") & " (" & FORMAT([Revenue WoW %], "+0%;-0%") & "), last 28 days: revenue " & FORMAT([Revenue L28D], "$#,##0") & " (" & FORMAT([Revenue L28D Δ%], "+0%;-0%") & ")."', P[6], None)
kpi_strip("06 · 001 KPI Strip HTML", P[6], [
    ("Revenue MTD", "Revenue MTD", "usd", "Revenue MTD vs PMTD %", False, "[MTD Label]"),
    ("Sessions MTD", "Sessions MTD", "int", "Sessions MTD vs PMTD %", False, "[MTD Label]"),
    ("Conversion MTD", "Conversion Rate MTD", "pct", "Conversion Rate MTD vs PMTD pts", True, "[MTD Label]"),
    ("Revenue last 7 days", "Revenue L7D", "usd", "Revenue WoW %", False, '"Prior 7 days"'),
    ("Revenue 7-day average", "Revenue 7D Avg", "usd", "Revenue Momentum %", False, '"28-day average"')], wow=False)

# ======================================================================================== 00 Welcome
add("00 Welcome Facts", """
"92 days · " & FORMAT(CALCULATE([Sessions], REMOVEFILTERS('Date')), "#,##0") & " sessions · " &
FORMAT(CALCULATE([Revenue], REMOVEFILTERS('Date')), "$#,##0") & " revenue · " &
FORMAT(CALCULATE([Transactions], REMOVEFILTERS('Date')), "#,##0") & " orders\"""", P[0], None,
    "One-line scope of the dataset for the cover page (ignores slicers).")


# ---- cover (page 00): landing-page hero; the light trail is daily revenue (3-day average) drawn from the model
import random as _rnd
_r = _rnd.Random(7)
_floor = "".join(f"<line x1='{640 + i*14}' y1='500' x2='{640 + i*120}' y2='720'/>" for i in range(-14, 15))
for _k in range(1, 10):
    _t = (_k / 9) ** 1.9; _y = 500 + _t * 220
    _floor += f"<line x1='0' y1='{_y:.1f}' x2='1280' y2='{_y:.1f}' stroke-opacity='{.15 + _t*.5:.2f}'/>"
_parts = "".join(f"<circle class='pt' cx='{200 + _r.random()*880:.0f}' cy='{470 + _r.random()*150:.0f}' r='{.8 + _r.random()*1.8:.1f}' style='animation-duration:{5 + _r.random()*7:.1f}s;animation-delay:{_r.random()*6:.1f}s'/>" for _ in range(34))
_CCSS = ("*{box-sizing:border-box;margin:0;padding:0}html,body{height:100vh;overflow:hidden;background:#07061A;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:#fff}"
         ".w{position:relative;width:100%;height:100vh;overflow:hidden}svg{position:absolute;inset:0;width:100%;height:100%}"
         ".glow{position:absolute;inset:0;background:radial-gradient(ellipse 60% 50% at 50% 62%,rgba(91,91,214,.30),transparent 70%),radial-gradient(ellipse 40% 30% at 18% 90%,rgba(91,214,176,.10),transparent 70%)}"
         ".dim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(7,6,26,.55),rgba(7,6,26,.25) 45%,rgba(7,6,26,.65));opacity:0;animation:fi 1.6s ease 2.8s forwards}"
         ".cv{stroke-dasharray:3000;stroke-dashoffset:3000;animation:dr 3.2s cubic-bezier(.65,0,.35,1) .3s forwards}@keyframes dr{to{stroke-dashoffset:0}}"
         ".bar{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:ri 1.4s cubic-bezier(.16,1,.3,1) forwards}@keyframes ri{to{transform:scaleY(1)}}"
         ".wv{stroke-dasharray:14 22;animation:fl 9s linear infinite}@keyframes fl{to{stroke-dashoffset:-720}}"
         ".pt{animation:up linear infinite}@keyframes up{0%{transform:translateY(0);opacity:0}15%{opacity:.9}100%{transform:translateY(-140px);opacity:0}}"
         ".pu{transform-box:fill-box;transform-origin:center;animation:pu 2.2s ease-out 3.4s infinite;opacity:0}@keyframes pu{0%{transform:scale(.6);opacity:.9}100%{transform:scale(3.2);opacity:0}}"
         "@keyframes fi{to{opacity:1}}.rv{opacity:0;filter:blur(12px);transform:translateY(18px);animation:rv 1.6s cubic-bezier(.16,1,.3,1) forwards}@keyframes rv{to{opacity:1;filter:blur(0);transform:none}}"
         ".top{position:absolute;left:40px;top:28px;display:flex;align-items:center;gap:10px;font-size:11px;font-weight:700;letter-spacing:.14em;color:rgba(255,255,255,.85);opacity:0;animation:fi 1.2s ease 3.6s forwards}"
         ".top i{width:28px;height:28px;border-radius:8px;border:1.5px solid rgba(255,255,255,.5);display:grid;place-items:center;font-style:normal;font-size:11px;font-weight:800;letter-spacing:0}"
         ".c{position:absolute;left:0;right:0;top:21%;text-align:center}.eb{font-size:11px;letter-spacing:.42em;color:rgba(255,255,255,.62);font-weight:500}"
         "h1{font-size:58px;font-weight:800;color:#FFFFFF!important;font-family:'Plus Jakarta Sans','Segoe UI',sans-serif;letter-spacing:-.025em;margin-top:18px;line-height:1.04;text-shadow:0 10px 50px rgba(7,6,26,.8)}"
         ".sub{font-size:15.5px;color:rgba(255,255,255,.80);margin-top:16px}.ev{font-size:10px;letter-spacing:.3em;font-weight:700;color:rgba(255,255,255,.42);margin-top:22px}.ev span{color:#C7C8F7}"
         ".band{position:absolute;left:0;right:0;bottom:0;height:132px;border-top:1px solid rgba(255,255,255,.08);background:linear-gradient(180deg,rgba(7,6,26,.55),rgba(7,6,26,.9));text-align:center;padding-top:28px;opacity:0;animation:fi 1.2s ease 4s forwards}"
         ".band small{font-size:9.5px;letter-spacing:.3em;font-weight:600;color:rgba(255,255,255,.45)}"
         ".sig{position:absolute;right:42px;top:86px;text-align:right;opacity:0;animation:fi 1.5s ease 4.4s forwards}.sig b{display:block;font:italic 400 26px/1 'Cormorant Garamond',Georgia,serif;color:rgba(255,255,255,.75)}.sig small{font-size:8.5px;letter-spacing:.3em;color:rgba(255,255,255,.45)}")
add("00 · 001 Cover HTML", f"""
VAR _d = ADDCOLUMNS(FILTER(CALCULATETABLE(VALUES('Date'[date]), REMOVEFILTERS('Date')), NOT ISBLANK('Date'[date])), "@r",
    VAR _x = 'Date'[date] RETURN DIVIDE(CALCULATE([Revenue], DATESBETWEEN('Date'[date], _x - 2, _x), REMOVEFILTERS('Date')), 3))
VAR _min = MINX(_d, 'Date'[date])
VAR _n = COUNTROWS(_d)
VAR _mx = MAXX(_d, [@r])
VAR _path = "M" & CONCATENATEX(_d, FORMAT(90 + INT('Date'[date] - _min) * 1100 / (_n - 1), "0.0") & "," & FORMAT(600 - DIVIDE([@r], _mx) * 150, "0.0"), " L", 'Date'[date], ASC)
VAR _pk = TOPN(1, _d, [@r], DESC)
VAR _px = FORMAT(90 + INT(MAXX(_pk, 'Date'[date]) - _min) * 1100 / (_n - 1), "0.0")
VAR _py = FORMAT(600 - DIVIDE(MAXX(_pk, [@r]), _mx) * 150, "0.0")
VAR _w = FILTER(ADDCOLUMNS(FILTER(CALCULATETABLE(VALUES('Date'[week_start]), REMOVEFILTERS('Date')), NOT ISBLANK('Date'[week_start])), "@n", CALCULATE(COUNTROWS('Date')), "@s", CALCULATE([Sessions])), [@n] = 7)
VAR _ms = MAXX(_w, [@s])
VAR _nw = COUNTROWS(_w)
VAR _bars = CONCATENATEX(_w,
    VAR _i = RANKX(_w, 'Date'[week_start], , ASC) - 1
    VAR _h = 22 + DIVIDE([@s], _ms) * 70
    RETURN "<rect class='bar' x='" & FORMAT(640 - _nw * 28 + _i * 56, "0") & "' y='" & FORMAT(500 - _h, "0.0") & "' width='46' height='" & FORMAT(_h, "0.0") & "' style='animation-delay:" & FORMAT(0.15 + _i * 0.06, "0.00") & "s'/>", "", 'Date'[week_start], ASC)
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>{_CCSS}</style></head><body><div class='w'><div class='glow'></div>
<svg viewBox='0 0 1280 720' preserveAspectRatio='xMidYMid slice'><defs><filter id='g' x='-20%' y='-20%' width='140%' height='140%'><feGaussianBlur stdDeviation='5' result='b'/><feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge></filter>
<linearGradient id='c' x1='0' x2='1'><stop offset='0' stop-color='#8B8CF0' stop-opacity='.2'/><stop offset='.35' stop-color='#A5A6FF'/><stop offset='.62' stop-color='#C7C8F7'/><stop offset='1' stop-color='#8B8CF0' stop-opacity='.35'/></linearGradient>
<linearGradient id='f' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#8B8CF0' stop-opacity='0'/><stop offset='1' stop-color='#8B8CF0' stop-opacity='.9'/></linearGradient></defs>
<g stroke='url(#f)' stroke-width='1' fill='none' opacity='.45'>{_floor}</g><g fill='rgba(139,140,240,.04)' stroke='rgba(167,168,255,.16)'>" & _bars & "</g>
<path d='M-40,690 C160,560 260,720 470,610 S760,520 1320,560' fill='none' stroke='#5BD6B0' stroke-opacity='.35' stroke-width='1.6' class='wv'/>
<path d='M-40,712 C180,600 300,740 520,640 S820,560 1320,600' fill='none' stroke='#8B8CF0' stroke-opacity='.35' stroke-width='1.2' class='wv' style='animation-duration:13s'/>
<path d='" & _path & "' fill='none' stroke='#8B8CF0' stroke-width='9' stroke-opacity='.18' filter='url(#g)' class='cv'/><path d='" & _path & "' fill='none' stroke='url(#c)' stroke-width='2.2' filter='url(#g)' class='cv'/>
<g fill='#C7C8F7'>{_parts}</g><circle cx='" & _px & "' cy='" & _py & "' r='9' fill='none' stroke='#C7C8F7' stroke-width='1.5' class='pu'/></svg>
<div class='dim'></div><div class='top'><i>DP</i>DATAPAT.AI</div><div class='sig'><b>DataPat.ai</b><small>PATRICIO RIOS</small></div>
<div class='c'><div class='eb rv' style='animation-delay:3s'>DATAPAT.AI PRESENTS</div><h1 class='rv' style='animation-delay:3.2s'>From Click to Checkout</h1>
<div class='sub rv' style='animation-delay:3.7s'>GA4 marketing performance: acquisition, engagement, funnel and revenue for the Google Merchandise Store</div>
<div class='ev rv' style='animation-delay:4s'>NOV 2020 — JAN 2021 · GA4 SAMPLE · <span>BUILT ON MICROSOFT FABRIC</span></div></div>
<div class='band'><small>SELECT AN AREA TO EXPLORE</small></div></div></body></html>\"""", P[0], None,
    "Cover page hero. Daily revenue (3-day average) is drawn as an animated light trail; weekly sessions as a faint skyline. Ignores slicers.")
add("00 · 001 Cover Alt Text", '"From Click to Checkout: GA4 marketing performance for the Google Merchandise Store, Nov 2020 to Jan 2021. " & [00 Welcome Facts]', P[0], None)

# ---- insight cards (dark navy)
_ICSS = ("*{box-sizing:border-box;margin:0;padding:0}html,body{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif}"
         ".c{height:100vh;border-radius:16px;background:linear-gradient(150deg,#1B1946,#2E2A7A);color:#fff;padding:18px 20px;display:flex;flex-direction:column}"
         ".l{font-size:9.5px;font-weight:700;letter-spacing:.16em;color:#C7C8F7}.row{display:flex;gap:18px;align-items:flex-end;margin-top:10px}"
         ".b{font-size:32px;font-weight:800;letter-spacing:-1px;line-height:1}.s{font-size:10.5px;color:#C9CAF5;margin-top:4px}.t{font-size:11px;line-height:1.55;color:#E3E4FF;margin-top:auto}")
def _insight(name, folder, body_vars, html, desc):
    add(name, body_vars + f"""
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>{_ICSS}</style></head><body><div class='c'>""" + html + """</div></body></html>\"""", folder, None, desc)

_insight("01 · 002 Key Insight HTML", P[1], """
VAR _sh = CALCULATE([Peak Season Revenue Share], REMOVEFILTERS('Date'))
VAR _ds = CALCULATE([Peak Season Day Share], REMOVEFILTERS('Date'))
VAR _lift = CALCULATE([Peak Conversion Lift], REMOVEFILTERS('Date'))
VAR _jr = CALCULATE([Revenue Δ%], DATESBETWEEN('Date'[date], DATE(2021,1,1), DATE(2021,1,31)), REMOVEFILTERS('Date'))
VAR _js = CALCULATE([Sessions Δ%], DATESBETWEEN('Date'[date], DATE(2021,1,1), DATE(2021,1,31)), REMOVEFILTERS('Date'))""",
"""<div class='l'>KEY INSIGHT · PEAK SEASON</div><div class='row'><div><div class='b'>" & FORMAT(_sh, "0%") & "</div><div class='s'>of revenue in " & FORMAT(_ds, "0%") & " of the days</div></div>
<div><div class='b' style='color:#C7C8F7'>+" & FORMAT(_lift, "0%") & "</div><div class='s'>conversion lift vs off-peak days</div></div></div>
<div class='t'>In January revenue falls " & FORMAT(-_jr, "0%") & " but sessions only " & FORMAT(-_js, "0%") & ": the visitors stay, the buyers leave.</div>""",
"Dark insight card for page 1: peak-season concentration and the January drop (always the full 92 days).")

_insight("02 · 002 Attribution HTML", P[2], """
VAR _sh = [Self-Referral Revenue Share]
VAR _r = [Self-Referral Revenue]""",
"""<div class='l'>ATTRIBUTION CHECK</div><div class='row' style='align-items:center'><div class='b'>" & FORMAT(_sh, "0%") & "</div>
<div class='t' style='margin-top:0'>of revenue (" & FORMAT(_r, "$#,##0") & ") is credited to the store’s own domain, a checkout redirect rather than a partner. Read Referral’s lead with caution.</div></div>""",
"Dark insight card for page 2: self-referral share of revenue.")

_insight("04 · 003 Where To Act HTML", P[4], f"""
VAR _v = [Session to View Item Rate]
VAR _ch = FILTER(ADDCOLUMNS(VALUES('Channel'[channel_group]), "@vi", CALCULATE([View Item Sessions], {CART_WIN}), "@r", CALCULATE([View Item to Purchase Rate], {CART_WIN})), [@vi] > 500)
VAR _b = TOPN(1, _ch, [@r], DESC)
VAR _w = TOPN(1, _ch, [@r], ASC)""",
"""<div class='l'>WHERE TO ACT</div><div class='row' style='align-items:center'><div class='b'>" & FORMAT(_v, "0%") & "</div>
<div class='t' style='margin-top:0'>of sessions ever open a product page. Fixing view → cart helps those; getting more visitors to a product page widens the whole funnel. " &
IF(COUNTROWS(_ch) > 1, MAXX(_b, 'Channel'[channel_group]) & " turns " & FORMAT(MAXX(_b, [@r]), "0.0%") & " of viewers into buyers vs " & FORMAT(MAXX(_w, [@r]), "0.0%") & " for " & MAXX(_w, 'Channel'[channel_group]) & ".") & "</div></div>""",
"Dark insight card for page 4: share of sessions reaching a product page and best vs worst channel.")

add("05 · 002 Pareto HTML", f"""
VAR _t = FILTER(ADDCOLUMNS(VALUES('Items Daily'[item_name]), "@r", [Item Revenue]), [@r] > 0)
VAR _n = COUNTROWS(_t)
VAR _tot = SUMX(_t, [@r])
VAR _half = [Items for Half of Revenue]
VAR _pts = CONCATENATEX(_t,
    VAR _cur = [@r]
    VAR _rk = COUNTROWS(FILTER(_t, [@r] > _cur)) + 1
    VAR _cum = SUMX(FILTER(_t, [@r] >= _cur), [@r])
    RETURN FORMAT(DIVIDE(_rk, _n) * 1000, "0.0") & "," & FORMAT(1000 - DIVIDE(_cum, _tot) * 1000, "0.0"), " L", [@r], DESC)
VAR _hx = FORMAT(DIVIDE(_half, _n) * 1000, "0.0")
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>*{{margin:0;padding:0}}html,body{{height:100vh;overflow:hidden;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif;color:#1A1840}}.w{{position:relative;height:100vh}}svg{{width:100%;height:calc(100vh - 18px)}}.x{{font-size:10px;color:#5E6189;text-align:center}}.lb{{position:absolute;font-size:10.5px;font-weight:800}}</style></head><body><div class='w'>
<svg viewBox='0 0 1000 1000' preserveAspectRatio='none'><line x1='0' x2='1000' y1='500' y2='500' stroke='#C7C8F7' stroke-dasharray='8 8' vector-effect='non-scaling-stroke'/>
<line x1='" & _hx & "' x2='" & _hx & "' y1='500' y2='1000' stroke='#5B5BD6' stroke-dasharray='8 8' vector-effect='non-scaling-stroke'/>
<path d='M0,1000 L" & _pts & " L1000,1000 Z' fill='#5B5BD6' fill-opacity='.12'/><path d='M0,1000 L" & _pts & "' fill='none' stroke='#5B5BD6' stroke-width='2.2' vector-effect='non-scaling-stroke'/></svg>
<div class='lb' style='left:calc(" & FORMAT(DIVIDE(_half, _n) * 100, "0.0") & "% + 8px);top:calc(50% - 4px)'>" & _half & " items = 50%</div><div class='x'>" & _n & " items sold, best first</div></div></body></html>\"""", P[5], None,
    "HTML Content visual: cumulative share of item revenue (Pareto curve) with the half-revenue marker.")


# ======================================================================================== page bodies (prototype runtime)
# Each page body is ONE HTML Content visual that runs the prototype's own chart code (semantic/pbi_runtime.js, extracted
# from design/index.html by scripts/build_pbi_runtime.py). DAX builds the DATA object the code reads, under the current
# filter context, so the native date slicer drives every chart exactly as the picker does in the prototype.
_RT_JS = (HERE / "pbi_runtime.js").read_text(encoding="utf-8")
_RT_CSS = (HERE / "pbi_runtime.css").read_text(encoding="utf-8")


def _jnum(e):
    return f'IF(ISBLANK({e}), "null", FORMAT({e}, "0.##########"))'


def _jstr(e):
    return (f'IF(ISBLANK({e}), "null", "\'" & SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({e} & "", "\\", "\\\\"), "\'", "\\\'"), "<", "\\x3c") & "\'")')


def _jbool(e):
    return f'IF({e}, "true", "false")'


def _jdate(e):
    return f'"\'" & FORMAT({e}, "yyyy-mm-dd") & "T00:00:00\'"'


def _obj(fields):
    """fields: list of (key, json-valued DAX expr). Keys with spaces/symbols are quoted."""
    parts = []
    for k, v in fields:
        key = k if k.replace("_", "").isalnum() else "'" + k + "'"
        parts.append(f'"{key}:" & {v}')
    return '"{" & ' + ' & "," & '.join(parts) + ' & "}"'


def _arr(table, fields, order):
    return f'"[" & CONCATENATEX({table}, {_obj(fields)}, ",", {order}) & "]"'


def _kpi(names):
    return _obj([(n, (_jstr if t == "s" else _jnum)(f"[{n}]")) for n, t in names])


def _row(col, var_val):
    return f"VAR _d = {col} RETURN CALCULATE({var_val}, REMOVEFILTERS('Date'), 'Date'[date] = _d)"


_RANGE = _obj([("s", '"\'" & FORMAT([Period Start], "yyyy-mm-dd") & "\'"'), ("e", '"\'" & FORMAT([Period End], "yyyy-mm-dd") & "\'"')])
_ALLDATES = "FILTER(CALCULATETABLE(VALUES('Date'[date]), REMOVEFILTERS('Date')), NOT ISBLANK('Date'[date]))"


def body_measure(page, vars_dax, data_fields):
    data = _obj([("page", str(page)), ("range", "_range")] + data_fields)
    css = _RT_CSS.replace('"', '""')
    js = _RT_JS.replace('"', '""')
    add(f"0{page} · 002 Body HTML", f"""VAR _range = {_RANGE}
{vars_dax}
VAR _data = {data}
RETURN
"<!DOCTYPE html><html><head><meta charset='utf-8'><link href='{FONT2}' rel='stylesheet'><style>{css}</style></head><body><div id='pages'></div><div id='tip'></div><script>window.__D=" & _data & ";</script><script>{js}</script></body></html>\"""",
        P[page], None, "Page body: the prototype's chart code (pbi_runtime.js) fed with model data for the current filters.")


_CH = "FILTER(VALUES('Channel'[channel_group]), NOT ISBLANK('Channel'[channel_group]))"

# ---- 01 Overview
body_measure(1, f"""VAR _daily = ADDCOLUMNS(FILTER(CALCULATETABLE(SUMMARIZE('Date', 'Date'[date], 'Date'[holiday_name], 'Date'[is_peak_season]), REMOVEFILTERS('Date')), NOT ISBLANK('Date'[date])),
    "@r", {_row("'Date'[date]", "[Revenue]")}, "@s", {_row("'Date'[date]", "[Sessions]")}, "@cr", {_row("'Date'[date]", "[Conversion Rate]")})
VAR _ch = FILTER(ADDCOLUMNS({_CH}, "@r", [Revenue], "@s", [Sessions], "@rs", [Revenue Share], "@ss", [Session Share], "@cr", [Conversion Rate], "@aov", [AOV]), NOT ISBLANK([@s]))
VAR _jr = CALCULATE([Revenue Δ%], DATESBETWEEN('Date'[date], DATE(2021,1,1), DATE(2021,1,31)), REMOVEFILTERS('Date'))
VAR _js = CALCULATE([Sessions Δ%], DATESBETWEEN('Date'[date], DATE(2021,1,1), DATE(2021,1,31)), REMOVEFILTERS('Date'))""",
    [("daily", _arr("_daily", [("date", _jdate("'Date'[date]")), ("r", _jnum("[@r]")), ("s", _jnum("[@s]")), ("cr", _jnum("[@cr]")),
                               ("holiday_name", f"IF('Date'[holiday_name] = \"\", \"null\", {_jstr(chr(39)+'Date'+chr(39)+'[holiday_name]')})"),
                               ("is_peak_season", _jbool("'Date'[is_peak_season]"))], "'Date'[date], ASC")),
     ("allkpi", _obj([(n, _jnum(f"CALCULATE([{n}], REMOVEFILTERS('Date'))")) for n in ("Peak Season Day Share", "Peak Season Revenue Share", "Peak Conversion Lift")])),
     ("jankpi", _obj([("Revenue Δ%", _jnum("_jr")), ("Sessions Δ%", _jnum("_js"))])),
     ("view", _obj([("kpi", _kpi([("Revenue Share of Top Channel", "n"), ("Best Revenue Day", "s")])),
                    ("channel", _arr("_ch", [("channel_group", _jstr("'Channel'[channel_group]")), ("r", _jnum("[@r]")), ("s", _jnum("[@s]")),
                                             ("rs", _jnum("[@rs]")), ("ss", _jnum("[@ss]")), ("cr", _jnum("[@cr]")), ("aov", _jnum("[@aov]"))], "[@r], DESC"))]))])

# ---- 02 Acquisition
body_measure(2, f"""VAR _ch = FILTER(ADDCOLUMNS({_CH}, "@s", [Sessions], "@r", [Revenue], "@ss", [Session Share], "@rs", [Revenue Share], "@ri", [Revenue Index], "@cr", [Conversion Rate], "@cvs", [Conversion vs Site]), NOT ISBLANK([@s]))
VAR _sm = TOPN(12, FILTER(ADDCOLUMNS(SUMMARIZE('Sessions', 'Sessions'[session_source], 'Sessions'[session_medium], 'Channel'[channel_group]),
    "@s", [Sessions], "@r", [Revenue], "@cr", [Conversion Rate], "@rps", [Revenue per Session], "@ri", [Revenue Index]), NOT ISBLANK([@s])), [@s], DESC)
VAR _dev = FILTER(ADDCOLUMNS(FILTER(VALUES('Device'[device_category]), NOT ISBLANK('Device'[device_category])), "@s", [Sessions], "@r", [Revenue], "@cr", [Conversion Rate], "@rps", [Revenue per Session], "@ss", [Session Share]), NOT ISBLANK([@s]))""",
    [("view", _obj([("kpi", _kpi([("Self-Referral Revenue Share", "n"), ("Self-Referral Revenue", "n")])),
                    ("channel", _arr("_ch", [("channel_group", _jstr("'Channel'[channel_group]")), ("s", _jnum("[@s]")), ("r", _jnum("[@r]")), ("ss", _jnum("[@ss]")),
                                             ("rs", _jnum("[@rs]")), ("ri", _jnum("[@ri]")), ("cr", _jnum("[@cr]")), ("cvs", _jnum("[@cvs]"))], "[@s], DESC")),
                    ("srcmed", _arr("_sm", [("session_source", _jstr("'Sessions'[session_source]")), ("session_medium", _jstr("'Sessions'[session_medium]")),
                                            ("channel_group", _jstr("'Channel'[channel_group]")), ("s", _jnum("[@s]")), ("r", _jnum("[@r]")), ("cr", _jnum("[@cr]")),
                                            ("rps", _jnum("[@rps]")), ("ri", _jnum("[@ri]"))], "[@s], DESC")),
                    ("device", _arr("_dev", [("device_category", _jstr("'Device'[device_category]")), ("s", _jnum("[@s]")), ("r", _jnum("[@r]")),
                                             ("cr", _jnum("[@cr]")), ("rps", _jnum("[@rps]")), ("ss", _jnum("[@ss]"))], "[@s], DESC"))]))])

# ---- 03 Content & Landing
body_measure(3, """VAR _top = TOPN(25, FILTER(ADDCOLUMNS(SUMMARIZE('Page Type', 'Page Type'[page_path], 'Page Type'[page_type]), "@s", [Sessions]), [@s] > 0), [@s], DESC)
VAR _lp = ADDCOLUMNS(_top, "@r", [Revenue], "@cr", [Conversion Rate], "@rps", [Revenue per Session], "@ss", [Landing Session Share], "@ix", [Landing RPS Index], "@role", [Landing Page Role])
VAR _pt = FILTER(ADDCOLUMNS(FILTER(VALUES('Page Type'[page_type]), NOT ISBLANK('Page Type'[page_type])), "@s", [Sessions], "@ss", [Landing Session Share], "@rs", [Landing Revenue Share], "@rps", [Revenue per Session], "@cr", [Conversion Rate]), NOT ISBLANK([@s]))""",
    [("view", _obj([("kpi", "\"{}\""),
                    ("landing", _arr("_lp", [("page_path", _jstr("'Page Type'[page_path]")), ("page_type", _jstr("'Page Type'[page_type]")), ("s", _jnum("[@s]")),
                                            ("r", _jnum("[@r]")), ("cr", _jnum("[@cr]")), ("rps", _jnum("[@rps]")), ("ss", _jnum("[@ss]")), ("ix", _jnum("[@ix]")),
                                            ("role", _jstr("[@role]"))], "[@s], DESC")),
                    ("pagetype", _arr("_pt", [("page_type", _jstr("'Page Type'[page_type]")), ("s", _jnum("[@s]")), ("ss", _jnum("[@ss]")), ("rs", _jnum("[@rs]")),
                                              ("rps", _jnum("[@rps]")), ("cr", _jnum("[@cr]"))], "[@s], DESC"))]))])

# ---- 04 Funnel (steps counted inside the cart-tracked window)
_F = [("vi", "View Item Sessions"), ("atc", "Add to Cart Sessions"), ("bc", "Begin Checkout Sessions"), ("api", "Add Payment Info Sessions"), ("ps", "Purchase Sessions")]
_fcols = ", ".join(f'"@{k}", CALCULATE([{m}], {CART_WIN})' for k, m in _F)
body_measure(4, f"""VAR _dev = ADDCOLUMNS(FILTER(VALUES('Device'[device_category]), NOT ISBLANK('Device'[device_category])), {_fcols})
VAR _fch = FILTER(ADDCOLUMNS({_CH}, {_fcols}, "@v2p", CALCULATE([View Item to Purchase Rate], {CART_WIN})), NOT ISBLANK([@vi]))""",
    [("view", _obj([("kpi", _kpi([("Session to View Item Rate", "n"), ("Cart Window Note", "s")])),
                    ("funnel", _obj([(k, _jnum(f"CALCULATE([{m}], {CART_WIN})")) for k, m in _F])),
                    ("device", _arr("_dev", [("device_category", _jstr("'Device'[device_category]"))] + [(k, _jnum(f"[@{k}]")) for k, _ in _F], "[@vi], DESC")),
                    ("funnel_ch", _arr("_fch", [("channel_group", _jstr("'Channel'[channel_group]"))] + [(k, _jnum(f"[@{k}]")) for k, _ in _F] + [("v2p", _jnum("[@v2p]"))],
                                       "[@vi], DESC"))]))])

# ---- 05 Products
body_measure(5, """VAR _it = TOPN(10, FILTER(ADDCOLUMNS(SUMMARIZE('Items Daily', 'Items Daily'[item_name], 'Items Daily'[item_category]), "@r", [Item Revenue]), NOT ISBLANK([@r])), [@r], DESC)
VAR _it2 = ADDCOLUMNS(_it, "@u", [Units Purchased], "@p", [Avg Item Price], "@sh", [Item Revenue Share])
VAR _cat = ADDCOLUMNS(TOPN(8, FILTER(ADDCOLUMNS(FILTER(VALUES('Items Daily'[item_category]), NOT ISBLANK('Items Daily'[item_category])), "@r", [Item Revenue]), NOT ISBLANK([@r])), [@r], DESC),
    "@u", [Units Purchased], "@p", [Avg Item Price], "@sh", [Item Revenue Share])
VAR _all = FILTER(ADDCOLUMNS(VALUES('Items Daily'[item_name]), "@r", [Item Revenue]), [@r] > 0)""",
    [("view", _obj([("kpi", _kpi([("Top Item", "s"), ("Top Category", "s"), ("Top Category Revenue Share", "n"), ("Top 10 Item Revenue Share", "n"),
                                  ("Items for Half of Revenue", "n")])),
                    ("items", _arr("_it2", [("item_name", _jstr("'Items Daily'[item_name]")), ("item_category", _jstr("'Items Daily'[item_category]")),
                                            ("r", _jnum("[@r]")), ("u", _jnum("[@u]")), ("p", _jnum("[@p]")), ("sh", _jnum("[@sh]"))], "[@r], DESC")),
                    ("category", _arr("_cat", [("item_category", _jstr("'Items Daily'[item_category]")), ("r", _jnum("[@r]")), ("u", _jnum("[@u]")),
                                               ("p", _jnum("[@p]")), ("sh", _jnum("[@sh]"))], "[@r], DESC")),
                    ("pareto_rv", '"[" & CONCATENATEX(_all, FORMAT([@r], "0.##"), ",", [@r], DESC) & "]"')]))])

# ---- 06 Time Intelligence
_TI = [("r7", "Revenue 7D Avg"), ("r28", "Revenue 28D Avg"), ("s7", "Sessions 7D Avg"), ("s28", "Sessions 28D Avg"), ("rmtd", "Revenue MTD"), ("smtd", "Sessions MTD")]
_DY = [("s", "Sessions"), ("r", "Revenue"), ("tx", "Transactions"), ("cs", "Converting Sessions"), ("pv", "Pageviews")]
_ticols = ", ".join(f'"@{k}", {_row(chr(39)+"Date"+chr(39)+"[date]", "["+m+"]")}' for k, m in _TI + _DY)
body_measure(6, f"""VAR _td = ADDCOLUMNS(FILTER(CALCULATETABLE(SUMMARIZE('Date', 'Date'[date], 'Date'[day_of_month], 'Date'[year_month]), REMOVEFILTERS('Date')), NOT ISBLANK('Date'[date])), {_ticols})
VAR _wd = FILTER(ADDCOLUMNS(SUMMARIZE('Date', 'Date'[day_of_week_num], 'Date'[day_name], 'Date'[day_short], 'Date'[is_weekend]),
    "@days", CALCULATE(COUNTROWS('Date')), "@adr", [Avg Daily Revenue (Row)], "@ix", [Weekday Revenue Index], "@cr", [Conversion Rate]), NOT ISBLANK('Date'[day_name]))""",
    [("ti_daily", _arr("_td", [("date", _jdate("'Date'[date]")), ("day_of_month", _jnum("'Date'[day_of_month]")), ("year_month", _jstr("'Date'[year_month]"))]
                       + [(k, _jnum(f"[@{k}]")) for k, _ in _TI], "'Date'[date], ASC")),
     ("days", _arr("_td", [("date", _jdate("'Date'[date]"))] + [(k, _jnum(f"[@{k}]")) for k, _ in _DY], "'Date'[date], ASC")),
     ("view", _obj([("kpi", _kpi([("Best Weekday", "s"), ("Best Weekday Index", "n"), ("Weekend Day Share", "n"), ("Weekend Revenue Share", "n"),
                                  ("Revenue MTD vs PMTD %", "n"), ("MTD Label", "s")])),
                    ("weekday", _arr("_wd", [("day_of_week_num", _jnum("'Date'[day_of_week_num]")), ("day_name", _jstr("'Date'[day_name]")),
                                             ("day_short", _jstr("'Date'[day_short]")), ("is_weekend", _jbool("'Date'[is_weekend]")),
                                             ("days", _jnum("[@days]")), ("adr", _jnum("[@adr]")), ("ix", _jnum("[@ix]")), ("cr", _jnum("[@cr]"))],
                                     "'Date'[day_of_week_num], ASC"))]))])


def write():
    names = {m["name"] for m in M}
    dup = [n for n in names if sum(1 for m in M if m["name"] == n) > 1]
    assert not dup, dup
    lines = ["// GA4 Ecommerce · report measures (generated by semantic/ga4_measures.py — do not edit by hand)",
             "// Base measures already in the model are referenced, not redefined (except REVISED ones).", "DEFINE"]
    for m in M:
        lines.append(f"\t// [{m['folder']}]{' (hidden)' if m['hidden'] else ''}{' REVISED' if m['kind'] == 'revised' else ''}"
                     + (f" — {m['description']}" if m['description'] else ""))
        body = m["expr"].replace("\n", "\n\t\t")
        lines.append(f"\tMEASURE '_Measures'[{m['name']}] =\n\t\t{body}")
    (HERE / "ga4_measures.dax").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (HERE / "ga4_measures.json").write_text(json.dumps(M, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(M)} measures → ga4_measures.dax / .json")


if __name__ == "__main__":
    write()
