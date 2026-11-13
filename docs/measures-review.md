# Measures review and report design (cover + 6 pages)

Snapshot 2026-11-12, checked against the live **GA4 Ecommerce** Direct Lake model (workspace GA4-Report).

- Measure source of truth: [`semantic/ga4_measures.py`](../semantic/ga4_measures.py) → generates `ga4_measures.dax` (a `DEFINE` block you can run in DAX query view) and `ga4_measures.json` (for the notebook upsert).
- Interactive page prototype: [`design/index.html`](../design/index.html) with `design/data.js`. The data is pulled from the live model through these measures. Serve the folder (`python3 -m http.server`) and open it in a browser.
- **Deployed 2026-11-13** to `_Measures` through Fabric `updateDefinition`: 167 measures in the model (26 base, 3 of them revised, plus 141 new), all valid. The old "04 Funnel & Products" folder is now split into "04 Funnel" and "05 Products". `nb_semantic_model_ga4` carries the revised AOV and cart rates, so re-running it does not revert them; it leaves the 141 report measures untouched (upsert only). **Update 2026-11-13:** 41 more measures were deployed for the cover page and a time intelligence page, bringing the total to 208, all valid. A third deploy added 70 rolling-window measures (`Base\Time\Rolling Windows`: L7D / P7D / Δ, L14D, L28D for Sessions, Engaged Sessions, Pageviews, Transactions, Revenue, Conversion Rate, AOV and Revenue per Session) plus `06 · 003 Rolling Table HTML`: **278 measures, all valid**. They are in `Base\Time` and the new folders `Pages\00 Welcome` and `Pages\06 Time Intelligence`. Before deploying, all measures were evaluated with query-scoped `DEFINE MEASURE` over four windows: full 92 days, Dec 2020, Jan 2021, and Dec 7–20.

## 1. Review of the 25 deployed measures

All 25 are valid and tie to the gold totals: 360,129 sessions, $362,165 revenue, 1,350,428 pageviews. Four need attention:

| Measure | Finding | Action |
|---|---|---|
| **AOV** | Divides by purchase **events** (5,692), which is 411 more than distinct transactions (5,281) because some transactions fire `purchase` more than once. This understates AOV ($63.63 vs $68.58). | **Revised**: `DIVIDE([Revenue], [Transactions])`. The old logic is kept, hidden, as `Revenue per Purchase Event`. |
| **View Item to Cart Rate**, **Cart to Checkout Rate** | The GA4 sample has almost no `add_to_cart` events before **2020-11-25**: 0 on most days, plus a short burst on Nov 16–19. This made November cart abandonment read 26.5%. | **Revised**: both rates, and the new Cart Abandonment Rate, are computed from `Cart Tracking Start` (Nov 25). The funnel visual uses the same window, and a footnote measure explains it. |
| **Add-to-Cart Rate** (item level) | Reads **135%**: item add-to-carts (37,262) exceed item views (27,585). The gold item filter drops `view_item` rows whose quantity is null. | Not shown on the report. `Item Data Check` shows the footnote. **Gold fix needed** in `nb_gold_ga4_marketing` (`kept` CTE: keep single-item `view_item` rows with a null quantity, or count `view_item` at event level). |
| **Revenue Share of Top Channel** | Correct. The top channel (Referral, 54%) includes **$111k from `shop.googlemerchandisestore.com`**, the store's own domain: 31% of all revenue is a self-referral. | New `Self-Referral Revenue (Share)` measures make this visible on page 2. Consider adding the domain to a referral exclusion in gold. |

Engagement rate is 89%, which is high by GA4 norms. It comes from `session_engaged` in the obfuscated sample and is not a measure bug. It is noted in the prototype, but no action is needed.

## 2. New measures, by folder

| Folder | What's in it |
|---|---|
| `Base\Core` | Transactions, AOV (revised), Converting Sessions, Returning Users, New User Share, Pages per Session, Avg Engagement Time (sec / text), Event Param Attribution Share |
| `Base\Time` | Period Start/End/Days/Label, PP Start/End/Label, Sessions & Revenue L7D/P7D/WoW %, Daily Avg Sessions/Revenue |
| `Base\Prior Period` | `<metric> PP` + `Δ%` or `Δ pts` for 22 metrics. The prior period is the previous calendar month when a whole month is selected, otherwise the same number of days just before the selection. It is blank when that window falls before Nov 1. |
| `Pages\01 Overview` | Top Channel, Peak Season Revenue/Share/Day Share/Conversion, Off-Peak Conversion, Peak Conversion Lift, Best Revenue Day, Holiday Day Revenue, **01 Headline** |
| `Pages\02 Acquisition` | Session Share, Revenue Share, Revenue Index, Conversion vs Site, Channel Revenue Rank, Self-Referral Revenue/Share/Sessions, **02 Headline** |
| `Pages\03 Content` | Entrances, Exits, Exit Rate, Page Sessions, Page Avg Engagement Time (session-weighted), Landing Session/Revenue Share, Landing RPS Index, Landing Page Role, Home Session/Revenue Share, **03 Headline** |
| `Pages\04 Funnel` | Cart Tracking Start, View Item to Cart Rate / Cart to Checkout Rate (revised), Session to View Item Rate, Cart & Checkout Abandonment, Lost at each step, Biggest Drop Step, Cart Window Note, **04 Headline** |
| `Pages\05 Products` | Units Purchased, Checkout Item Rows, Avg Item Price, Items Sold, Item Revenue Share/Rank, Top 10 Item Revenue Share, Items for Half of Revenue, Top Item, Top Category (+ share), Item Data Check, **05 Headline** |
| `Base\Time` (added) | Revenue / Sessions / Transactions MTD, PMTD and MTD vs PMTD %, Conversion Rate MTD / PMTD / pts, MTD Label, Revenue Running Total / Running Share, Revenue & Sessions 7D Avg and 28D Avg, Conversion Rate 7D, Revenue / Sessions Momentum % |
| `Pages\06 Time Intelligence` | Week Revenue / Sessions WoW %, Avg Daily Revenue / Sessions (Row), Weekday Revenue Index, Best / Worst Weekday, Best Weekday Index, Weekend Revenue Share / Day Share, Weekend / Weekday Conversion Rate, **06 Headline**, 06 Headline HTML, 06 KPI Strip HTML + Alt Text |
| `Pages\00 Welcome` | 00 Welcome Facts (dataset scope line for the cover) |
| Components (in the page folders) | `0N · 000 Headline HTML` and `0N · 001 KPI Strip HTML` (+ Alt Text) for each page, plus `04 · 002 Funnel HTML` (+ Alt Text). They render in the **HTML Content** visual, use single quotes only, and have no external JS. |

## 3. The pages

| Page | Question | Story technique |
|---|---|---|
| 00 Welcome | What is in the report and where to start? | A landing-page hero modelled on Gus Bavia's Briarport and Peaches covers. An animated SVG scene draws from the data: daily revenue (3-day average) as a light trail over a perspective grid, weekly sessions as a faint skyline, and a sessions screenshot from `design/assets/` at 5% as texture. On top: a centred 'DataPat.ai presents' eyebrow, the title 'From Click to Checkout', one subtitle and one event line. A bottom band reads 'Select an area to explore' above six page buttons, with How to read and Connect LinkedIn in the top corner. No KPIs on the cover. |
| 01 Overview | Is revenue up or down, and which channel drove it? | Headline-first sentence, a hero KPI with deltas, a 92-day trend with a peak-season band and holiday markers, channel concentration, and a dark "key insight" card (52% of revenue in 38% of the days; January keeps visitors but loses buyers) |
| 02 Acquisition | Which sources bring revenue, not just sessions? | A mirrored traffic-share vs revenue-share bar chart with a revenue-index chip, a sortable source table that flags the self-referral, a device split, and an attribution-check card |
| 03 Content & Landing | Which landing pages earn, and which only attract? | A quadrant (Earners / Attractors / Hidden gems / Long tail) on traffic vs yield, a role-tagged landing table, and session share vs revenue share by page type |
| 04 Funnel | Where do shoppers drop? | A funnel with the leak in red, lost-session cards, a step-rate heatmap by channel, and a "where to act" card. It is device-switchable. |
| 05 Products | Which products and categories carry revenue? | A top-10 ranking, category bars, a Pareto curve (36 of 426 items make half the revenue), and a data note on the item-view gap |

| 06 Time Intelligence | Is the business speeding up or slowing down, and when in the week does it earn? | Daily bars with 7- and 28-day average lines and a momentum callout, month-to-date pacing curves (selected month vs the month before), a week-over-week table that flags partial weeks, a day-of-week index, and a momentum card with the weekend gap. The sample is 92 days, so there is no year-over-year. |

In Power BI, the cover screenshots need a public URL (a CDN or the GitHub raw link): the Image visual cannot load local files.

**Prototype layout (all pages):** a collapsible navy sidebar with icons (the `[` key or the Collapse button), and a white header card with the page title and a two-line story headline. On the right of the header, a calendar date picker offers quick ranges (Full, Nov, Dec, Jan, Peak season, Black Friday – Cyber Monday, Last 7/14/28 days) or any custom range from Nov 1 to Jan 31. KPI cards show an icon, the value, the prior value and the change. For custom ranges, KPIs, channel, device, funnel, weekday and rolling tables recompute from daily data, and match the model; landing, source and product tables use the containing month and say so in the header. In Power BI the picker is a native date slicer (Between) on `'Date'[date]`.

**Power BI build (report GA4-Dashboard, workspace GA4-Report):** generated by `scripts/build_report_pages.py` and published through Fabric `updateDefinition`. Every page body is one HTML Content visual (`0N · 002 Body HTML`). It runs the prototype's own chart code, which `scripts/build_pbi_runtime.py` extracts from `design/index.html` into `semantic/pbi_runtime.js/.css`, on a DATA object built in DAX under the current filters, so Power BI looks and behaves like the HTML file: same layout, toggles, sortable tables and tooltips. The header (`0N · 000`), KPI strip (`0N · 001`) and cover (`00 · 001`) are HTML measures too. Native visuals are kept only where Power BI has to act: the page navigator, the cover buttons, the LinkedIn and DataPat.ai links, and the date slicer (Between on `'Date'[date]`, synced across pages). To change a chart, edit `design/index.html`, then re-run both scripts and deploy.

Shared across pages: one indigo accent; green/red always comes with a sign and an arrow; every chart says how to read it. The "How to read" panel maps to tutorial bookmarks, and the "Build notes" toggle shows the Power BI visual and measure behind each block.
