# GA4 Ecommerce — HTML design kit

The design stage for the Google Merchandise Store report. Open the welcome page, explore the four analytical pages, inspect the component library, then use the theme and fixed-canvas assets when building Power BI.

**All preview observations are synthetic.** Some full-window totals match repository-reported checkpoints for layout scale only. No live Fabric connection is configured, and no report or model is deployed or modified.

## Preview

```sh
cd design
npm ci
npm run dev -- --port 4173 --strictPort
```

Open http://localhost:4173/. Individual pages are in `pages/`, the design library in `components/index.html`, and background previews in `assets/backgrounds/gallery.html`.

For a plain static copy, run `npm run build`, then serve `dist/` with any HTTP server. For example, `python3 -m http.server 4174 --directory dist`. The HTML uses ES modules and a JSON fixture, so opening `file://` directly is not supported. Runtime icons, fonts and Chart.js are bundled locally; the preview does not need third-party CDNs or API credentials.

## Generated artwork

Three transparent PNG illustrations made with OpenAI Image Gen are in `assets/generated/`: ecommerce cover, acquisition storefront, and shopping journey. Open `assets/generated/gallery.html` for previews and downloads, or insert the PNGs directly into Power BI. The cover illustration also appears on the HTML welcome page.

## Deliverables

| Path | Purpose |
|---|---|
| `index.html` | Welcome and report chapter navigation |
| `pages/overview.html` | KPIs, trend, channel performance and device mix |
| `pages/acquisition.html` | Source/medium matrix, channel ranking, geography/device and conversion |
| `pages/content.html` | Landing-page scatter, page-type revenue, search, sort and detail |
| `pages/funnel.html` | Event reach, device comparison and product performance |
| `components/index.html` | Palette, typography, component states and downloadable assets |
| `css/tokens.css`, `css/report.css` | Shared theme and responsive styling |
| `js/components.js`, `js/charts.js` | Reusable HTML renderers and Chart.js adapters |
| `js/pages/*.js` | Individual page compositions and visual bindings |
| `theme/powerbi-theme.json` | Native Power BI theme defaults |
| `theme/tokens.json` | Cross-tool color, type, geometry and formatting tokens |
| `assets/backgrounds/*.png` | Five 1600 × 900 canvas backgrounds |
| `assets/backgrounds/canvas.html` | Editable HTML source for the exported backgrounds |
| `assets/icons/`, `assets/fonts/`, `assets/vendor/` | Licensed local UI assets |
| `specs/page-layouts.json` | Native visual coordinates and filter scopes |
| `specs/model-bindings.json` | Existing model DAX, required additions and source revision |
| `specs/README.md`, `specs/handoff.html` | Report implementation guide |
| `qa/` | Browser evidence and automated interaction results |
| `design-qa.md` | Verification status and fidelity limitations |

## Verification

`npm run check` validates fixture totals, rate calculations, filter scopes, product scope invariance, empty results, layout bounds, native theme structure, source measure count, and local assets. `npm run build` creates the portable static artifact.

Browser checks cover all six pages on desktop and mobile, navigation, chart controls, persisted filters, landing-page search/sort, dialogs, category/device controls, CSV downloads, horizontal overflow and console errors. The check results are saved under `qa/`.

The three original reference-image files are absent from this cloud workspace. Their inline chat images guided the design; exact source-file side-by-side fidelity QA remains blocked. Fabric access and Power BI theme import/execution also remain outside the verified scope. See `design-qa.md` and `specs/README.md`.

## Regenerate editable assets

```sh
python3 scripts/generate-fixture.py
python3 scripts/generate-layouts.py
```

To re-export background PNGs, capture `assets/backgrounds/canvas.html?page=<page>` at 1600 × 900 after `body[data-ready=true]` appears. Valid page names: welcome, overview, acquisition, content, funnel. Keep these surfaces free of data so native Power BI visuals remain editable and accessible.

Use the model and verified gold tables for production. Do not import `data/preview-fixture.json` into the report.
