# Setup and Run Instructions

Everything here runs on a normal laptop in about a minute. No server, no account needed.

**Tested on:** Python 3.10–3.12, pandas 2.0+.

---

## 1. Install Python

Check whether you already have it:

```bash
python --version
```

If that fails, try `python3 --version`. If neither works, install Python 3.12 from
[python.org/downloads](https://www.python.org/downloads/).

> **Windows users:** on the first installer screen, tick **"Add python.exe to PATH"** before
> clicking Install. If you miss it, `python` will not be recognised in the terminal and you
> will have to re-run the installer and choose Modify.

Throughout this file, replace `python` with `python3` if that is what works on your machine
(usual on macOS and Linux).

---

## 2. Install the libraries

From the project folder:

```bash
pip install -r requirements.txt
```

If `pip` is not recognised, use `python -m pip install -r requirements.txt`.

---

## 3. Build the data and run the analysis

Run these three in order, from the project root:

```bash
python scripts/generate_raw_data.py
python scripts/build_database.py
python scripts/analysis.py
python scripts/make_charts.py
```

**Step 1** writes four CSVs to `data/raw/`. Expect:

```
orders     (40180, 11)
customers  (16000, 3)
pincodes   (121, 4)
logistics  (40000, 5)
```

**Step 2** builds `data/brightbasket.db`. Expect:

```
removed 180 duplicate order rows
corrected 119 negative discounts
zeroed 140 phantom shipping charges on cancelled orders

view check:
  rows        cm  loss_orders
39355 3265824.0        11169
```

**Step 3** prints the whole analysis and writes `data/processed/order_economics.csv`.
The last line should read:

```
COMBINED ANNUAL RECOVERY: Rs 570,297 (17.5% lift on current CM)
```

> **Verification checkpoint.** If you see `39355`, `3265824.0` and `11169`, the SQL and pandas
> paths agree and everything downstream is trustworthy. If any of the three differ, stop and
> find out why before building the dashboard.

---

## 4. Open the notebook

```bash
cd notebooks
jupyter notebook
```

Your browser opens; click `01_cleaning_and_analysis.ipynb`, then **Kernel → Restart & Run All**.

> The notebook uses relative paths (`../data/raw/...`), so it **must** be launched from inside
> the `notebooks/` folder. Launching Jupyter from the project root will give you
> `FileNotFoundError`.

Prefer VS Code? Install the Python and Jupyter extensions, open the folder, open the `.ipynb`,
and pick your Python interpreter from the kernel selector in the top right.

---

## 5. Run the SQL

Install [DB Browser for SQLite](https://sqlitebrowser.org/dl/) — free, about 30 MB.

1. Open it → **Open Database** → `data/brightbasket.db`
2. Go to the **Execute SQL** tab
3. Open any file from `sql/`, paste it in, run with **Ctrl+Return** (**Cmd+Return** on Mac)

Run one statement at a time rather than the whole file — DB Browser shows results for the last
statement only, and each query in these files is meant to be read separately.

Start with `sql/04_confounder_checks.sql`. It is the analytical core of the project.

> `sql/02_order_economics_view.sql` has already been applied by `build_database.py`. You do not
> need to run it again unless you change the margin definition — in which case re-run
> `build_database.py` so the notebook and the view stay in agreement.

---

## 6. Open the Excel dashboard

Open `dashboard/BrightBasketDashboard.xlsx`.

Excel usually shows a yellow **Enable Editing** bar the first time. Click it, or the formulas
won't recalculate and the numbers will look frozen.

Go to the **Dashboard** sheet and change the Category dropdown in row 5. Every KPI and all three
charts update. Then open **Scenario Model** and change the conversion rate from 35% to 0%: the
combined gain drops but stays positive, because the avoided losses don't depend on anyone
switching to prepaid.

### Add the PivotTable (about 3 minutes)

The workbook ships without one, on purpose. A PivotTable stores its own copy of the data, and if
that copy goes stale it shows wrong numbers with no warning. Building it yourself means it's fresh.

1. **Order Data** sheet, click any cell
2. **Insert** → **PivotTable** → **New Worksheet** → OK
3. Drag `zone` to Rows, `payment_mode` to Columns, `contribution_margin` to Values
4. Click the Values field → **Value Field Settings** → change Sum to **Average**
5. **PivotTable Analyze** → **Insert Slicer** → tick `category`, `courier_partner`,
   `acquisition_channel`
6. Rename the sheet to `Pivot`

**Then check it.** Metro/COD should read 91.7 and Tier3/COD should read −4.0. If they don't, a
slicer is filtering something — click the clear-filter icon (funnel with a red cross) on each one.

Those two numbers also appear on the Segment Analysis sheet. If the pivot ever disagrees with that
sheet, the pivot is stale: **PivotTable Analyze** → **Refresh**.

> **Don't re-run `scripts/make_excel_dashboard.py` over a file you've added a pivot to.** The
> script can't recreate PivotTables or slicers, so it would wipe them. It refuses to overwrite for
> that reason; `--force` overrides it.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `'python' is not recognized` | Python not on PATH | Re-run the installer, choose Modify, tick "Add to PATH". Or use `py` instead on Windows. |
| `ModuleNotFoundError: No module named 'pandas'` | Libraries not installed, or installed to a different Python | `python -m pip install -r requirements.txt` — the `python -m` form guarantees it installs into the interpreter you are actually running. |
| `FileNotFoundError: '../data/raw/orders.csv'` | Jupyter launched from the wrong folder | `cd notebooks` first, then `jupyter notebook`. |
| `FileNotFoundError` running a script | Not in the project root | Run scripts from the project root, not from inside `scripts/`. |
| `database is locked` | DB Browser has the file open | Close the database in DB Browser before re-running `build_database.py`. |
| Numbers differ from those above | Random seed changed | The seed is `20260906` in `generate_raw_data.py`. Do not change it — every number in the README depends on it. |
| Workbook opens as `[Read-Only]` | Windows blocks files downloaded from the internet | File → Save As over it, or right-click the file → Properties → tick **Unblock**. |
| `make_excel_dashboard.py` refuses to run | It's protecting a PivotTable you added | Working as intended. Add `--force` only if you want the plain workbook back. |
| Pivot numbers don't match Segment Analysis | Stale pivot cache, or a slicer left on | PivotTable Analyze → Refresh, then clear every slicer. |

---

## 7. Push to GitHub

Install Git from [git-scm.com/download/win](https://git-scm.com/download/win) if you don't
have it (accept every default in the installer). Then create an **empty** repo on github.com —
no README, no .gitignore, no licence, since this folder already has them.

From the project root:

```
git init
git add .
git commit -m "Order-level margin leak analysis"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/brightbasket-margin-leak.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

**On the password prompt:** GitHub stopped accepting account passwords in 2021. You need a
Personal Access Token. Go to github.com → your avatar → Settings → Developer settings →
Personal access tokens → Tokens (classic) → Generate new token. Tick the **repo** scope, set an
expiry, generate, and copy it. Paste that token where Git asks for a password — it will not
appear on screen as you paste, which is normal.

Newer Git for Windows installs open a browser sign-in window instead, which is easier. If that
happens, just sign in there.

### First-time Git setup

If Git complains it doesn't know who you are:

```
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### After pushing

Check the repo page renders: the README should show the four charts inline, and
`notebooks/01_cleaning_and_analysis.ipynb` should display with its outputs. If the notebook
shows as raw JSON, it uploaded before executing — re-run it locally and push again.
