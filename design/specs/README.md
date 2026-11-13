# GA4 Ecommerce design handoff

This is the design stage, before building the Power BI report. The new files do not change Fabric, the notebooks, lakehouse, semantic model, or a published report.

## Visual direction

The supplied references define the lavender canvas, white cards, violet chart palette, compact navigation, KPI strip, fine chart grids, and restrained semantic deltas. The design deliberately adapts those patterns to GA4 rather than recreating sales/profit/CLV measures absent from the model. Each analytical page has a different question and composition. The welcome page follows the opening-page convention documented in the prior NVIDIA design chat and Trading Analytics portfolio project.

HTML uses locally bundled DM Sans; Power BI uses Segoe UI because custom web fonts are not portable in native report visuals. Bootstrap Icons supply the standard navigation and UI assets. Three decorative illustrations were subsequently created with OpenAI Image Gen and saved in assets/generated/; the welcome page uses the cover illustration. These are unbranded artwork, not real product thumbnails. There are no image placeholders.

## Pages

| Page | Purpose | Composition | Filter scope |
|---|---|---|---|
| Welcome | Introduce the store analytics story | Opening copy and four chapter links | None |
| Executive overview | Is traffic and revenue moving together? | Five KPIs; trend + revenue mix; channel table + device mix | Date, Channel, Device |
| Acquisition | Which sources create value? | KPI strip; source matrix + channel ranking; country/device bars + device conversion | Date, Channel, Device |
| Content & landing pages | Which pages earn their traffic? | Four KPIs; traffic/value scatter + page-type revenue; searchable/sortable page table | Date, Page Type, local path search |
| Funnel & products | Which events do sessions reach and which products sell? | Event-session KPIs; event reach + device comparison; product table | Event panels: Date, Channel, Device. Product section: Date + Category only |
| Design system | Inspect and reuse the design | Palette, typography, spacing, state samples, shared components, downloads | Demonstration controls |

## Power BI implementation

1. Import `theme/powerbi-theme.json` using View → Themes → Browse for themes. This sets visual defaults; it does not create report pages, measures or relationships. JSON and structural checks are included. Import testing against a running Power BI Desktop instance remains outstanding.
2. Create a **custom 1600 × 900** report canvas for every page. The responsive HTML is the interaction reference; the native report uses the fixed coordinate plan in `page-layouts.json`.
3. Set the matching `assets/backgrounds/<page>.png` as the canvas background, image fit **Fit**, transparency **0%**. These backgrounds contain static surfaces and navigation icons only. Place live report titles, visual titles, slicers, chart data, legends and KPI values above them.
4. Use the exact `visualRect` coordinates, with transparent visual backgrounds and borders/shadows off. Each white card’s outer surface belongs to the PNG; do not create a second white visual card over it. Add live titles within the given card bounds.
5. Add transparent page navigation buttons over each rail icon. Coordinates are in `navigation` in `page-layouts.json`; set Page navigation actions individually. Baked icons are decorative. Include accessible button names and tab order; the PNG itself does not provide accessible navigation.
6. Use model measures from `model-bindings.json` and the inspected semantic-model notebook. Exported fixture rows are **never** a production data source. Connect the report to the existing `GA4 Ecommerce` model after its notebook validation passes.
7. Use native slicers, matrices, bar/line/scatter charts and button/bookmark controls. Prefer a native bar for event reach. Donuts can be replaced with bars if accessible labels are too dense. No custom visual is required by this kit.
8. Validate date, channel and device interactions across the report. Products must ignore Channel and Device. Landing-page aggregates do not support Channel or Device in the current model. Do not silently extend filter scope; change the gold grain and model first if required.
9. Add a report tooltip with metric definition, population and source. Use logical keyboard order: navigation → filters → KPIs → chart sections → detail table. Native report text should meet contrast and font requirements at actual reading size.
10. Verify production totals, selected-period comparisons and native report accessibility in Fabric/Power BI before publishing. HTML tests cannot validate Direct Lake relationships or DAX execution.

## Measures and caveats

- Revenue = SUM Sessions[revenue]. Purchases = SUM Sessions[purchases], a count of purchase events. AOV = Revenue / Purchases.
- Conversion = sessions with purchases > 0 / all sessions. This is not purchase events / sessions.
- Engagement = engaged sessions / sessions. Recompute rates from their numerators and denominators.
- Users are distinct users, not additive across dates or categories. The preview deliberately avoids a Users card because it uses aggregated synthetic records.
- The funnel fact counts independent event-bearing sessions. It cannot establish sequential step conversion or abandonment. Call the visual **Shopping event reach** until ordered session-event logic is added.
- The product fact is date × item, with no channel/device columns. Its Item Revenue may differ from the session revenue field.
- Landing-page revenue is in Landing Pages, not Page Sessions. Pageviews are sourced from Page Sessions. Session-level measures use Sessions with Page Type relationships.
- Comparisons in the preview are previous complete calendar month, with differing month lengths. They are unavailable for November and the complete 92-day window. Period-over-period measures are not in the inspected notebook and must be added deliberately before native implementation.
- The 92-day public sample is obfuscated and covers Black Friday and Christmas. Do not present it as a live store or a normal seasonal baseline.

## Interaction inventory

Navigation links open separate HTML pages. Date/channel/device selections persist within the browser session; only supported filters apply on each page. Revenue/sessions switches change the trend, channel rank switches between revenue and revenue/session, table headers sort landing pages, search filters the content page, table rows open accessible detail dialogs, Escape closes dialogs, Reset clears filters, and CSV exports contain the current filtered fixture rows with a synthetic classification column. Products have their own scoped CSV export.

Search with no matches produces a visible empty state with a clear-search action. Missing preview data produces a visible load error with local-server instructions. Reduced-motion preferences suppress transitions. Mobile navigation moves to the bottom; wide tables scroll inside their cards.

## Source review

- Project: https://github.com/PatricRc/ga4-ecommerce-fabric
- Inspected README, semantic model notebook, marketing gold notebook, and page-sessions notebook. Exact source revision is preserved in `model-bindings.json` and fixture metadata.
- Repository-reported checkpoints: 360,129 sessions, USD 362,165 revenue, 1,350,428 pageviews, 4,848 purchase sessions, and 11,106 begin-checkout sessions. These are source claims, not independently re-queried Fabric results.
- Fabric URL could not be inspected: the environment network proxy returns HTTP 403. No authenticated browser or Fabric connector is exposed here.
- Prior work: https://github.com/PatricRc/trading-analytics-fabric and the accessible chat “Check Power BI and Fabric skills” (NVIDIA opening-page and HTML-first workflow).
- The three original user image attachments were visually supplied in chat, but their `/var/folders/...` files are not present in the cloud filesystem. Exact file-based side-by-side fidelity QA is blocked; functional and responsive browser checks remain possible.

## Asset ownership

- Original work: report copy, layout, HTML/CSS/JS, tokens, background surfaces and page plans.
- Bootstrap Icons 1.11.3, MIT — `assets/icons/LICENSE`.
- Chart.js 4.4.8, MIT — `assets/vendor/chartjs-LICENSE.md`.
- DM Sans, SIL Open Font License — `assets/fonts/OFL.txt`.
- No Google branding or third-party reference logos are reproduced. The basket emblem is a Bootstrap icon.
