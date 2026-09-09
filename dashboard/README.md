# Dashboard notes

**File:** `BrightBasketDashboard.xlsx`
**Data:** `data/processed/order_economics.csv` (39,355 rows)

Every KPI and chart uses a live SUMIFS, COUNTIFS or AVERAGEIFS over the whole dataset. Nothing is
typed in, so changing a filter updates everything. You can click any cell and see where the number
came from, which matters — "it's an AVERAGEIFS over these two conditions" is an answer, "Python
worked it out" isn't.

| Sheet | What's on it |
|---|---|
| Dashboard | Five KPI cards, three charts, two dropdown filters |
| Pivot | PivotTable with three slicers |
| Segment Analysis | The three breakdowns the recommendation rests on |
| Scenario Model | Assumptions you can change, plus a sensitivity table |
| Data Quality | Every data problem and what I did about it |
| Order Data | All the cleaned rows, as an Excel Table called `OrderData` |
| Chart Data | The formulas feeding the charts |

**Why both a formula dashboard and a PivotTable?** They do different jobs. The dashboard answers
the same set of questions the same way every time. The PivotTable lets someone poke around — if a
manager asks "what about referral customers in tier 2?", they can find out themselves instead of
asking me.

> **If you re-run the build script:** `scripts/make_excel_dashboard.py` will refuse to overwrite an
> existing file. The PivotTable and slicers were added by hand and the script can't recreate them,
> so it would wipe them silently. Use `--force` only if you want the plain version back.

---

## How I decided what goes on it

The dashboard answers one question for one person making one decision. It's not a place to put
everything I have.

For each chart I asked: if I deleted this, could the founder still make the COD decision? If yes, I
deleted it. Three charts went that way — orders over time, revenue by category, and a breakdown by
acquisition channel. All interesting. None of them changed the decision.

**Someone will ask why there's no chart over time.** The decision is about which orders to accept,
not when they arrive. A trend line would just be decoration. Being able to say what I left out and
why is better than nine charts.

---

## Why each chart looks the way it does

### Chart 1 — profit per order by zone and payment (horizontal bars)

- **Horizontal** because labels like "Tier3 — COD" need room. Vertical would mean tilting the text.
- **Sorted by value, not alphabetically.** The worst group has to be the first thing you see.
  Sorting alphabetically is the most common way a chart hides its own point.
- **Zero line made obvious.** Zero isn't just another gridline here, it's the decision line. Above
  it, take the order. Below it, don't.
- **Colour only shows positive or negative.** Six colours would just be decoration.
- **Per order, not total.** The total would make tier-3 COD look tiny (−₹18k next to ₹14L in metro
  prepaid) and hide the fact that every one of those orders loses money.

### Chart 2 — profit per order by order size (vertical bars)

- **Vertical** because order sizes read naturally left to right, small to large.
- **The band edges sit on the ₹499 line.** If I'd used even ₹250 buckets, the gap would be split
  across two bars and you'd never see it. Bucket edges should sit where the decision is, not on
  round numbers.
- **I didn't use a second axis.** Putting the fee we charge and the shipping cost on two axes lets
  people read whatever they want into the gap between the lines.

### Chart 3 — courier, raw vs like-for-like (paired bars)

The most important chart, and the one that gets the most questions.

- **Why show the wrong number at all?** Because the point isn't what the couriers earn. The point is
  that the first number misleads you. If I only showed the corrected version, nobody would
  understand why "do nothing" is the answer.
- **Paired, not two separate charts.** The comparison is the whole message. Split apart, you have to
  remember one while looking at the other.

### The recommendation box

**The cost is on the dashboard, not in a footnote.** Showing a recommendation without its price is
how you lose credibility the first time someone works out the price themselves.

### Titles

Every chart title says what I found, not what's on it — "Only one segment loses money: COD in Tier
3", not "CM by Zone and Payment Mode". The axis labels already say what the data is.

---

## Two mistakes worth knowing about

**The `<300` label.** I originally called the smallest band `<300`. Excel reads a leading `<` in a
formula condition as "less than", so `COUNTIFS(range,"<300")` matched nothing. The chart showed ₹0
instead of −₹22.2 and gave no error at all. I renamed it to `Under 300`.

Lesson: don't put `<`, `>` or `=` in a label you're going to filter on later. The same thing breaks
in Power BI, Tableau and SQL.

**The sensitivity table.** It calculated with no errors and was still wrong. I'd pointed one part of
the formula at the retention rate cell where it should have pointed at the delivery fee. It showed
₹202,054 where the model right above it said ₹570,298.

Lesson: a spreadsheet with no error messages isn't the same as a spreadsheet with correct answers.
I only found it by checking the table against the model above it.

---

## Screenshots

`screenshots/01` to `04` are static charts from `scripts/make_charts.py`. They show up on GitHub
without anyone opening Excel and they always match the data.

To add pictures of the actual workbook: **Win + Shift + S**, drag over the area, paste into Paint,
save as `screenshots/05_excel_dashboard.png` and `06_pivot_slicers.png`.
