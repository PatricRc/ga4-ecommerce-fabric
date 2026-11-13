# GA4 Ecommerce: From First Visit to Purchase (community post draft)

**Title:** Only 6 in 100 product viewers buy. The leak is the first click, not checkout

**Intro**
Google's Merchandise Store sold $362K over three months, from 360K sessions, and 1.35% of visits ended in a purchase. This Power BI report follows the journey from first visit to purchase across November 2020 to January 2021 and shows where shoppers drop out. The biggest leak is before the cart: only 26% of product viewers add anything to it.

**What's inside**
- **Overview:** Revenue, sessions, conversion and AOV for any date range. Peak season (Black Friday to Christmas) brought 52% of revenue in 38% of the days.
- **Acquisition:** Which channels bring revenue, not just sessions. Referral carries 54% of revenue on 28% of sessions.
- **Content & Landing:** Which pages earn, and which only attract visits.
- **Funnel:** Each step from product view to purchase, with the lost sessions at each stage and a channel heatmap.
- **Products:** Apparel is 47% of item revenue. 36 items make up half of it.
- **Time Intelligence:** Month to date, rolling 7/14/28-day windows and weekday patterns.

**Findings**
1. Referral turns 9.9% of product viewers into buyers. Paid Search turns 2.9%. More visitors to product pages would widen the whole funnel.
2. Peak season converts 46% better than off-peak days.
3. January revenue falls 64% against December while sessions fall 11%. The visitors stay, the buyers leave.
4. Self-referral accounts for 31% of revenue ($111K). Treat channel shares with care until attribution is checked.
5. Cart abandonment is 74.7%, measured from Nov 25, when add_to_cart started being tracked.

**Design choices**
- Every page opens with a headline sentence that states the finding.
- Each KPI compares the last 7 days with the 7 days before (week over week). Hover a card for what it measures and why it matters.
- A date picker, with presets for full period, months, peak season and Black Friday to Cyber Monday.
- A collapsible navigation rail. Charts keep their hover tooltips and sortable tables.

**How it is built**
- Data: the Google Merchandise Store GA4 ecommerce sample, loaded into a Microsoft Fabric lakehouse and modelled as a semantic model.
- Measures: about 300 DAX measures. Week-over-week and prior-period logic runs on the date slicer.
- Visuals: each page body is an HTML Content visual that runs the same chart code as the HTML prototype, fed by DAX measures, so the numbers follow the filters.

**Try this**
Pick Black Friday to Cyber Monday in the date picker, then hover a KPI card. Switch the Overview chart between Revenue, Sessions and Conversion rate.

**Notes**
- The sample ends on Jan 31, 2021. The last week of January is 81% below the week before: check the data before you read it as a trend.
- Dataset: Google Merchandise Store GA4 sample (public). This is an independent portfolio study.

**Links**
- Live report: [to add once publish-to-web is decided]
- LinkedIn: linkedin.com/in/patriciorioscanepa · Portfolio: data-pat-ai.netlify.app
