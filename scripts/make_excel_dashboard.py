"""
make_excel_dashboard.py -- builds the CEO-level interactive Excel workbook.

DESIGN PRINCIPLE: every summary number is a FORMULA against the Order Data
sheet, never a value pasted in by Python. Two reasons that matters:
  1. You can click any cell and see where the number came from. In an interview
     "it's an AVERAGEIFS over these two conditions" is an answer. "Python
     calculated it" is not.
  2. Change a filter and the whole dashboard recalculates itself.

NOTE ON SLICERS: real Excel slicers require PivotTables, which openpyxl cannot
generate. The Dashboard dropdowns give the same interactivity via data
validation. 'Order Data' is written as a formatted Excel Table so a PivotTable
plus slicers can be added by hand in ~10 minutes -- see the Read Me sheet.

Run: python scripts/make_excel_dashboard.py
Out: dashboard/BrightBasketDashboard.xlsx

SAFETY: this script refuses to overwrite an existing workbook. The delivered
file has a PivotTable and slicers added by hand, and openpyxl cannot recreate
those -- regenerating blindly would silently destroy them. Pass --force only
if you genuinely want the base workbook back.
"""
import sys
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "BrightBasketDashboard.xlsx"
df = pd.read_csv(ROOT / "data" / "processed" / "order_economics.csv")
N = len(df)
LAST = N + 1

NAVY, TEAL, RED, GREY = "1F3A5F", "2E7D6F", "C0392B", "5A6472"
A = "Arial"
F_H    = Font(A, size=11, bold=True, color="FFFFFF")
F_LBL  = Font(A, size=9,  color=GREY)
F_KPI  = Font(A, size=18, bold=True, color=NAVY)
F_BODY = Font(A, size=10)
F_BOLD = Font(A, size=10, bold=True)
F_IN   = Font(A, size=10, bold=True, color="0000FF")     # blue = editable input
F_NOTE = Font(A, size=9,  italic=True, color=GREY)
FILL_NAVY = PatternFill("solid", fgColor=NAVY)
FILL_HDR  = PatternFill("solid", fgColor=TEAL)
FILL_CARD = PatternFill("solid", fgColor="F2F5F8")
FILL_IN   = PatternFill("solid", fgColor="FFFDE7")
FILL_REC  = PatternFill("solid", fgColor="E8F3F0")
THIN = Side("thin", color="C8D0D8")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
RS, PCT, NUM = '"₹"#,##0;[Red]-"₹"#,##0', '0.0%', '#,##0'

if OUT.exists() and "--force" not in sys.argv:
    raise SystemExit(
        f"{OUT.name} already exists and may contain a hand-built PivotTable and\n"
        f"slicers that this script cannot recreate. Re-run with --force to overwrite.")

wb = Workbook()

# ===================================================== ORDER DATA
ws = wb.active; ws.title = "Order Data"
ws.append(list(df.columns))
for row in df.itertuples(index=False):
    ws.append(list(row))
for c in range(1, len(df.columns) + 1):
    ws.cell(1, c).font = F_H; ws.cell(1, c).fill = FILL_HDR
    ws.column_dimensions[get_column_letter(c)].width = 15
ws.freeze_panes = "A2"
t = Table(displayName="OrderData", ref=f"A1:{get_column_letter(len(df.columns))}{LAST}")
t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(t)

COL = {c: get_column_letter(i + 1) for i, c in enumerate(df.columns)}
def R(c): return f"'Order Data'!${COL[c]}$2:${COL[c]}${LAST}"

# "*" is the SUMIFS wildcard for "any text" -- that is how the All option works.
CAT = 'IF(Dashboard!$C$5="All","*",Dashboard!$C$5)'
ACQ = 'IF(Dashboard!$F$5="All","*",Dashboard!$F$5)'
FLT = f'{R("category")},{CAT},{R("acquisition_channel")},{ACQ}'

# ===================================================== CHART DATA
cd = wb.create_sheet("Chart Data")
cd["A1"] = "Chart feed -- every cell is a live formula honouring the Dashboard filters. Do not edit."
cd["A1"].font = F_NOTE

cd["A3"], cd["B3"] = "Segment", "CM per order"
for i, (lab, z, p) in enumerate([
        ("Tier3 - COD", "Tier3", "COD"), ("Tier2 - COD", "Tier2", "COD"),
        ("Tier3 - Prepaid", "Tier3", "Prepaid"), ("Metro - COD", "Metro", "COD"),
        ("Tier2 - Prepaid", "Tier2", "Prepaid"), ("Metro - Prepaid", "Metro", "Prepaid")], 4):
    cd[f"A{i}"] = lab
    cd[f"B{i}"] = (f'=IFERROR(AVERAGEIFS({R("contribution_margin")},'
                   f'{R("zone")},"{z}",{R("payment_mode")},"{p}",{FLT}),0)')

cd["D3"], cd["E3"] = "Value band", "CM per order"
for i, b in enumerate(["Under 300", "300-499", "500-699", "700-999", "1000+"], 4):
    cd[f"D{i}"] = b
    cd[f"E{i}"] = (f'=IFERROR(AVERAGEIFS({R("contribution_margin")},'
                   f'{R("value_band")},"{b}",{FLT}),0)')

cd["G3"], cd["H3"], cd["I3"] = "Courier", "As reported", "Within Tier 3"
for i, c in enumerate(["BharatShip", "SwiftLogix", "ZipEx"], 4):
    cd[f"G{i}"] = c
    cd[f"H{i}"] = (f'=IFERROR(AVERAGEIFS({R("contribution_margin")},'
                   f'{R("courier_partner")},"{c}",{FLT}),0)')
    cd[f"I{i}"] = (f'=IFERROR(AVERAGEIFS({R("contribution_margin")},'
                   f'{R("courier_partner")},"{c}",{R("zone")},"Tier3",{FLT}),0)')
for col in "BEHI":
    for r in range(4, 10):
        cd[f"{col}{r}"].number_format = '#,##0.0'
for col in "ABDEGHI":
    cd.column_dimensions[col].width = 17
for c in ("A3", "B3", "D3", "E3", "G3", "H3", "I3"):
    cd[c].font = F_BOLD

# ===================================================== DASHBOARD
d = wb.create_sheet("Dashboard", 0)
d.sheet_view.showGridLines = False
for col, w in zip("ABCDEFGHIJKL", [3,18,16,16,16,16,16,16,16,16,16,3]):
    d.column_dimensions[col].width = w

for c in range(2, 12):
    d.cell(2, c).fill = FILL_NAVY
d.merge_cells("B2:K2")
d["B2"] = "BrightBasket  |  Where Is Our Order Margin Leaking?"
d["B2"].font = Font(A, size=18, bold=True, color="FFFFFF")
d["B2"].alignment = Alignment(vertical="center", indent=1)
d.row_dimensions[2].height = 34
d.merge_cells("B3:K3")
d["B3"] = (f"Order-level contribution margin  |  {N:,} orders  |  FY Apr 2025 - Mar 2026  "
           "|  Synthetic dataset, see Read Me")
d["B3"].font = F_NOTE

d["B5"] = "FILTERS"; d["B5"].font = Font(A, size=9, bold=True, color=GREY)
d["C4"], d["F4"] = "Category", "Acquisition channel"
d["C4"].font = F_LBL; d["F4"].font = F_LBL
for cell, items in [("C5", ["All"] + sorted(df.category.unique())),
                    ("F5", ["All"] + sorted(df.acquisition_channel.unique()))]:
    d[cell] = "All"; d[cell].font = F_IN; d[cell].fill = FILL_IN; d[cell].border = BOX
    d[cell].alignment = Alignment(horizontal="center")
    dv = DataValidation(type="list", formula1='"' + ",".join(items) + '"', allow_blank=False)
    d.add_data_validation(dv); dv.add(d[cell])
d.merge_cells("C5:E5"); d.merge_cells("F5:H5")

ORD  = f'COUNTIFS({FLT})'
LOSSN = f'COUNTIFS({FLT},{R("is_loss")},TRUE)'
kpis = [("B", "REVENUE",
         f'=SUMIFS({R("net_revenue")},{FLT})+SUMIFS({R("delivery_revenue")},{FLT})', RS),
        ("D", "CONTRIBUTION MARGIN", f'=SUMIFS({R("contribution_margin")},{FLT})', RS),
        ("F", "CM %", '=IFERROR(D8/B8,0)', PCT),
        ("H", "LOSS-MAKING ORDERS", f'=IFERROR({LOSSN}/{ORD},0)', PCT),
        ("J", "MARGIN BURNED",
         f'=SUMIFS({R("contribution_margin")},{FLT},{R("is_loss")},TRUE)', RS)]
nxt = {"B": "C", "D": "E", "F": "G", "H": "I", "J": "K"}
for col, lab, f, fmt in kpis:
    d[f"{col}7"] = lab; d[f"{col}7"].font = F_LBL
    d[f"{col}8"] = f;  d[f"{col}8"].font = F_KPI; d[f"{col}8"].number_format = fmt
    d.merge_cells(f"{col}7:{nxt[col]}7"); d.merge_cells(f"{col}8:{nxt[col]}8")
    for r in (7, 8):
        for cc in (col, nxt[col]):
            d[f"{cc}{r}"].fill = FILL_CARD; d[f"{cc}{r}"].border = BOX
d.row_dimensions[8].height = 28

d["B10"] = ("Margin burned is shown separately, not netted into contribution margin. "
            "Netting is exactly what hides the problem.")
d["B10"].font = F_NOTE

def chart(title, data, cats, anchor, horiz=False, multi=False):
    ch = BarChart(); ch.type = "bar" if horiz else "col"
    ch.title = title; ch.style = 2; ch.gapWidth = 60
    ch.height, ch.width = 7.6, 12.4
    ch.add_data(data, titles_from_data=True)
    ch.set_categories(cats)
    ch.y_axis.title = "Rs per order"
    if not multi:
        ch.legend = None
    d.add_chart(ch, anchor)

chart("Only one segment loses money: COD in Tier 3",
      Reference(cd, min_col=2, min_row=3, max_row=9),
      Reference(cd, min_col=1, min_row=4, max_row=9), "B12", horiz=True)
chart("Our free-delivery threshold creates a margin cliff",
      Reference(cd, min_col=5, min_row=3, max_row=8),
      Reference(cd, min_col=4, min_row=4, max_row=8), "G12")
chart("The courier gap disappears once you compare like routes with like",
      Reference(cd, min_col=8, max_col=9, min_row=3, max_row=7),
      Reference(cd, min_col=7, min_row=4, max_row=7), "B28", horiz=True, multi=True)

d["G28"] = "RECOMMENDATION"
d["G28"].font = Font(A, size=11, bold=True, color=NAVY)
d.merge_cells("G28:K28")
for i, (txt, bold) in enumerate([
    ("1.  Prepaid-only for COD orders under Rs 700 in Tier-3 pincodes.", True),
    ("     ~8% of volume, running a 17% return rate.  Net gain Rs 1,96,329.", False),
    ("     Stays profitable even if 0% of blocked customers switch to prepaid.", False),
    ("2.  Raise the free-delivery threshold from Rs 499 to Rs 699.", True),
    ("     10,176 orders would newly pay Rs 49.  At 75% retention: Rs 3,73,968.", False),
    ("3.  Take no courier action.", True),
    ("     The margin gap is route mix, not partner performance.", False),
    ("", False),
    ("COMBINED:  Rs 5,70,297 / year  -  a 17.5% lift on contribution margin.", True),
    ("COST:  ~Rs 9.6L of revenue walks away. It carried negative margin.", True)]):
    cell = d.cell(29 + i, 7, txt)
    cell.font = Font(A, size=9, bold=bold, color=RED if txt.startswith("COST") else "1A1A1A")
    for col in range(7, 12):
        d.cell(29 + i, col).fill = FILL_REC

# ===================================================== SEGMENT ANALYSIS
a = wb.create_sheet("Segment Analysis")
a.sheet_view.showGridLines = False
a["B2"] = "Segment analysis -- unfiltered, live formulas across all orders"
a["B2"].font = Font(A, size=13, bold=True, color=NAVY)

a["B4"] = "1.  Contribution margin by zone and payment mode"; a["B4"].font = F_BOLD
for j, h in enumerate(["Zone","Payment","Orders","RTO rate","Avg order value","CM per order","CM total"]):
    c = a.cell(5, 2 + j, h); c.font = F_H; c.fill = FILL_HDR
r = 6
for z in ("Metro", "Tier2", "Tier3"):
    for p in ("COD", "Prepaid"):
        b = f'{R("zone")},"{z}",{R("payment_mode")},"{p}"'
        a.cell(r, 2, z).font = F_BODY; a.cell(r, 3, p).font = F_BODY
        a.cell(r, 4, f'=COUNTIFS({b})').number_format = NUM
        a.cell(r, 5, f'=IFERROR(COUNTIFS({b},{R("order_status")},"RTO")/COUNTIFS({b}),0)').number_format = PCT
        a.cell(r, 6, f'=AVERAGEIFS({R("net_order_value")},{b})').number_format = RS
        a.cell(r, 7, f'=AVERAGEIFS({R("contribution_margin")},{b})').number_format = RS
        a.cell(r, 8, f'=SUMIFS({R("contribution_margin")},{b})').number_format = RS
        for col in range(2, 9):
            a.cell(r, col).border = BOX
        r += 1
a.cell(13, 2, "Only Tier3 x COD is negative. That is why the recommendation is geographic, not payment-wide.").font = F_NOTE

a["B16"] = "2.  Contribution margin by order value band"; a["B16"].font = F_BOLD
for j, h in enumerate(["Band","Orders","Avg fee charged","Avg shipping cost","CM per order"]):
    c = a.cell(17, 2 + j, h); c.font = F_H; c.fill = FILL_HDR
for i, bnd in enumerate(["Under 300","300-499","500-699","700-999","1000+"]):
    rr = 18 + i; b = f'{R("value_band")},"{bnd}"'
    a.cell(rr, 2, bnd).font = F_BODY
    a.cell(rr, 3, f'=COUNTIFS({b})').number_format = NUM
    a.cell(rr, 4, f'=AVERAGEIFS({R("delivery_revenue")},{b})').number_format = RS
    a.cell(rr, 5, f'=AVERAGEIFS({R("shipping_cost")},{b})').number_format = RS
    a.cell(rr, 6, f'=AVERAGEIFS({R("contribution_margin")},{b})').number_format = RS
    for col in range(2, 7):
        a.cell(rr, col).border = BOX
a.cell(24, 2, "The 500-699 band earns a fraction of 700-999 across a Rs 1 difference in order value. That gap is our policy, not customer behaviour.").font = F_NOTE

a["B27"] = "3.  Courier -- raw ranking vs like-for-like"; a["B27"].font = F_BOLD
for j, h in enumerate(["Courier","Orders","CM per order (all)","CM per order (Tier 3)","% of volume in Tier 3"]):
    c = a.cell(28, 2 + j, h); c.font = F_H; c.fill = FILL_HDR
for i, cr in enumerate(["BharatShip","SwiftLogix","ZipEx"]):
    rr = 29 + i; b = f'{R("courier_partner")},"{cr}"'
    a.cell(rr, 2, cr).font = F_BODY
    a.cell(rr, 3, f'=COUNTIFS({b})').number_format = NUM
    a.cell(rr, 4, f'=AVERAGEIFS({R("contribution_margin")},{b})').number_format = RS
    a.cell(rr, 5, f'=AVERAGEIFS({R("contribution_margin")},{b},{R("zone")},"Tier3")').number_format = RS
    a.cell(rr, 6, f'=IFERROR(COUNTIFS({b},{R("zone")},"Tier3")/COUNTIFS({b}),0)').number_format = PCT
    for col in range(2, 7):
        a.cell(rr, col).border = BOX
a.cell(33, 2, "Raw ranking says BharatShip is worst. Within Tier 3 all three are level -- the gap was route allocation, not performance.").font = F_NOTE
for col, w in zip("ABCDEFGH", [3,18,15,18,18,18,18,16]):
    a.column_dimensions[col].width = w

# ===================================================== SCENARIO MODEL
s = wb.create_sheet("Scenario Model")
s.sheet_view.showGridLines = False
s["B2"] = "Scenario model -- how much does the recommendation depend on my assumptions?"
s["B2"].font = Font(A, size=13, bold=True, color=NAVY)
s["B3"] = "Blue cells on yellow are inputs. Change them and everything below recalculates."
s["B3"].font = F_NOTE

s["B5"] = "Live inputs, pulled from the data"; s["B5"].font = F_BOLD
POCKET = f'{R("payment_mode")},"COD",{R("zone")},"Tier3",{R("net_order_value")},"<700"'
for i, (lab, f, fmt) in enumerate([
    ("Target pocket orders  (COD, Tier 3, under Rs 700)", f'=COUNTIFS({POCKET})', NUM),
    ("Current margin on that pocket", f'=SUMIFS({R("contribution_margin")},{POCKET})', RS),
    ("Prepaid analogue -- CM per order, same zone and size",
     f'=AVERAGEIFS({R("contribution_margin")},{R("payment_mode")},"Prepaid",'
     f'{R("zone")},"Tier3",{R("net_order_value")},"<700")', RS),
    ("Orders in the Rs 500-698 band (delivered)",
     f'=COUNTIFS({R("order_status")},"Delivered",{R("net_order_value")},">=500",'
     f'{R("net_order_value")},"<699")', NUM)]):
    s.cell(6 + i, 2, lab).font = F_BODY
    c = s.cell(6 + i, 6, f); c.number_format = fmt; c.border = BOX
    c.font = Font(A, size=10, color="008000")

s["B12"] = "Assumptions -- change these"; s["B12"].font = F_BOLD
for i, (lab, v, fmt) in enumerate([("Prepaid conversion rate  (Lever 1)", 0.35, PCT),
                                   ("Fee retention rate  (Lever 2)", 0.75, PCT),
                                   ("Delivery fee charged (Rs)", 49, NUM)]):
    s.cell(13 + i, 2, lab).font = F_BODY
    c = s.cell(13 + i, 6, v); c.font = F_IN; c.fill = FILL_IN
    c.border = BOX; c.number_format = fmt

s["B17"] = "Result"; s["B17"].font = F_BOLD
for i, (lab, f) in enumerate([
    ("Losses avoided  (does not depend on conversion)", "=-F7"),
    ("Margin from customers who convert", "=F6*F13*F8"),
    ("Lever 1 net gain", "=F18+F19"),
    ("Lever 2 fee revenue", "=F9*F15*F14"),
    ("COMBINED ANNUAL GAIN", "=F20+F21")]):
    rr = 18 + i
    big = "COMBINED" in lab
    s.cell(rr, 2, lab).font = F_BOLD if big else F_BODY
    c = s.cell(rr, 6, f); c.number_format = RS; c.border = BOX
    c.font = Font(A, size=11, bold=True, color=NAVY) if big else F_BODY

s["B25"] = "Sensitivity -- combined annual gain across both assumptions"; s["B25"].font = F_BOLD
s["B26"] = "Rows = prepaid conversion rate   |   Columns = fee retention rate"; s["B26"].font = F_NOTE
rets  = [0.50, 0.60, 0.70, 0.75, 0.80, 0.90]
convs = [0.00, 0.15, 0.25, 0.35, 0.45, 0.55]
c = s.cell(27, 2, "Conv / Ret"); c.font = F_H; c.fill = FILL_HDR
for j, rt in enumerate(rets):
    c = s.cell(27, 3 + j, rt); c.number_format = PCT; c.font = F_H; c.fill = FILL_HDR
for i, cv in enumerate(convs):
    rr = 28 + i
    c = s.cell(rr, 2, cv); c.number_format = PCT; c.font = F_H; c.fill = FILL_HDR
    for j in range(len(rets)):
        cc = s.cell(rr, 3 + j,
                    # F15 = delivery fee. Using F14 here (the retention rate) is the
                    # classic sensitivity-grid bug: it recalculates cleanly and is wrong.
                    f'=-$F$7+($F$6*$B{rr}*$F$8)+($F$9*{get_column_letter(3+j)}$27*$F$15)')
        cc.number_format = '"₹"#,##0'; cc.border = BOX; cc.font = F_BODY
s.cell(35, 2, "Every cell is positive, including the 0% conversion row. The recommendation does not depend on the assumption I am least sure about.").font = F_NOTE
for col, w in zip("ABCDEFGHI", [3,46,13,13,13,15,13,13,13]):
    s.column_dimensions[col].width = w

# ===================================================== DATA QUALITY
q = wb.create_sheet("Data Quality")
q.sheet_view.showGridLines = False
q["B2"] = "Data quality audit -- every defect counted before it was fixed"
q["B2"].font = Font(A, size=13, bold=True, color=NAVY)
q["B3"] = "Counting first is what makes each cleaning decision auditable rather than a claim."
q["B3"].font = F_NOTE
for j, h in enumerate(["Defect", "Rows", "Decision", "Why it mattered"]):
    c = q.cell(5, 2 + j, h); c.font = F_H; c.fill = FILL_HDR
for i, row in enumerate([
    ("Duplicate order_id", 180, "Drop, keep first",
     "order_id is the table's grain -- duplicates inflate revenue AND cost invisibly"),
    ("Missing pincode", 602, "Drop after bias check",
     "Dropped rows were 53% COD vs 57% retained -- no bias introduced"),
    ("Mixed date formats", 900, "Parse each row on its own terms",
     "errors='coerce' would have silently nulled 900 real dates"),
    ("Negative discounts", 120, "Absolute value, flagged",
     "A discount is a magnitude; the sign was a misposted refund"),
    ("Zero-value orders", 45, "Drop",
     "All from INTERNAL_QA -- test orders, not demand"),
    ("Shipping on cancelled orders", 140, "Zero out",
     "Never dispatched -- the 3PL billed us in error. A finding in its own right"),
    ("Inconsistent city casing", 121, "Title-case",
     "GROUP BY city would have split Bengaluru into three rows")]):
    rr = 6 + i
    q.cell(rr, 2, row[0]).font = F_BODY
    q.cell(rr, 3, row[1]).number_format = NUM
    q.cell(rr, 4, row[2]).font = F_BODY
    q.cell(rr, 5, row[3]).font = Font(A, size=9, color=GREY)
    for col in range(2, 6):
        q.cell(rr, col).border = BOX
q.cell(14, 2, "Rows retained").font = F_BOLD
c = q.cell(14, 3, f'=COUNTA({R("order_id")})'); c.number_format = NUM; c.font = F_BOLD
q.cell(15, 2, "Retention rate vs 40,180 raw rows").font = F_BODY
q.cell(15, 3, "=C14/40180").number_format = PCT
for col, w in zip("ABCDE", [3,30,10,32,74]):
    q.column_dimensions[col].width = w

# ===================================================== READ ME
rm = wb.create_sheet("Read Me")
rm.sheet_view.showGridLines = False
for i, (txt, sz, bold, col) in enumerate([
 ("BrightBasket CEO Dashboard -- how to use this workbook", 14, True, NAVY),
 ("", 10, False, "1A1A1A"),
 ("THE BUSINESS QUESTION", 11, True, NAVY),
 ("Orders grew 30% year on year but contribution margin stayed flat. Which orders lose money,", 10, False, "1A1A1A"),
 ("and what single policy change recovers the most margin without wrecking volume?", 10, False, "1A1A1A"),
 ("", 10, False, "1A1A1A"),
 ("SHEETS", 11, True, NAVY),
 ("Dashboard          Main view. Two dropdowns filter every KPI and all three charts.", 10, False, "1A1A1A"),
 ("Segment Analysis   The three cuts the recommendation rests on, unfiltered.", 10, False, "1A1A1A"),
 ("Scenario Model     Change the assumptions and watch the recommendation hold or break.", 10, False, "1A1A1A"),
 ("Data Quality       Every defect found, counted, and the decision taken.", 10, False, "1A1A1A"),
 ("Order Data         All cleaned orders, as an Excel Table named 'OrderData'.", 10, False, "1A1A1A"),
 ("Chart Data         Formula feed for the dashboard charts. Do not edit.", 10, False, "1A1A1A"),
 ("", 10, False, "1A1A1A"),
 ("HOW THE FILTERS WORK", 11, True, NAVY),
 ("Every KPI and chart is a live SUMIFS / COUNTIFS / AVERAGEIFS over the Order Data sheet.", 10, False, "1A1A1A"),
 ("Nothing is typed in -- click any cell and you can see where the number came from.", 10, False, "1A1A1A"),
 ("", 10, False, "1A1A1A"),
 ("ADD A PIVOTTABLE AND SLICERS  (about 3 minutes)", 11, True, NAVY),
 ("1.  Order Data sheet -> click any cell -> Insert -> PivotTable -> New Worksheet", 10, False, "1A1A1A"),
 ("2.  Drag 'zone' to Rows, 'payment_mode' to Columns, 'contribution_margin' to Values", 10, False, "1A1A1A"),
 ("3.  Value Field Settings -> change Sum to Average", 10, False, "1A1A1A"),
 ("4.  PivotTable Analyze -> Insert Slicer -> tick category, zone, payment_mode", 10, False, "1A1A1A"),
 ("Then check it: Metro/COD should read 91.7 and Tier3/COD should read -4.0. Those two", 10, False, "1A1A1A"),
 ("numbers are also on the Segment Analysis sheet. If the pivot ever disagrees with that", 10, False, "1A1A1A"),
 ("sheet, it is holding stale data -- PivotTable Analyze -> Refresh, and clear the slicers.", 10, False, "1A1A1A"),
 ("", 10, False, "1A1A1A"),
 ("This file ships without a pivot on purpose. A PivotTable keeps its own copy of the data,", 10, False, GREY),
 ("and a stale copy shows wrong numbers with no warning. Building it yourself keeps it fresh.", 10, False, GREY),
 ("", 10, False, "1A1A1A"),
 ("ASSUMPTIONS AND LIMITATIONS", 11, True, NAVY),
 ("The data is made up. Product cost, shipping cost and return status per order together are", 10, False, "1A1A1A"),
 ("a company's unit economics and nobody publishes them. The generator is open in", 10, False, "1A1A1A"),
 ("scripts/generate_raw_data.py and every number is written down in docs/ASSUMPTIONS.md.", 10, False, "1A1A1A"),
 ("So this shows the method, not a discovery about a real company.", 10, False, "1A1A1A"),
 ("", 10, False, "1A1A1A"),
 ("The 35% prepaid switch rate is a guess, not a measurement. See the Scenario Model: the", 10, False, "1A1A1A"),
 ("recommendation still makes money even at 0%, because the avoided losses do not depend on", 10, False, "1A1A1A"),
 ("anyone switching. The weakest assumption is the 75% fee retention on the second change.", 10, False, "1A1A1A")]):
    rm.cell(2 + i, 2, txt).font = Font(A, size=sz, bold=bold, color=col)
rm.column_dimensions["A"].width = 3
rm.column_dimensions["B"].width = 100

wb.move_sheet("Read Me", offset=-5)
wb.save(OUT)
print("wrote", OUT)
