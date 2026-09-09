# Starting over cleanly

Follow these in order. Takes about 15 minutes.

## 1. Delete the old folder

Close Excel, Command Prompt, Jupyter and DB Browser first — Windows won't delete a folder while
something inside it is open.

Then delete `C:\Projects\brightbasket-margin-leak`.

Also delete the old zips in your Downloads so you don't extract the wrong one later.

## 2. Extract the new zip

Right-click the new zip → **Extract All** → set the path to exactly:

```
C:\Projects
```

Nothing after it. The zip already contains the folder name, so adding it again gives you the
folder twice.

## 3. Check it works

Open the folder, click the address bar, type `cmd`, press Enter. Then:

```
python scripts/generate_raw_data.py
python scripts/build_database.py
python scripts/analysis.py
python scripts/make_charts.py
```

After the second one you should see:

```
 rows        cm  loss_orders
39355 3265824.0        11169
```

Those three numbers are the check. If they match, everything downstream is right.

## 4. Add the PivotTable to the Excel file

The workbook ships without one. Steps are on the **Read Me** sheet inside it, or in SETUP.md
section 6. Three minutes.

Then check Metro/COD reads 91.7 and Tier3/COD reads −4.0 before you save.

## 5. Wipe the GitHub repo and push again

The old repo has files you don't want any more, so replace it rather than adding to it.

**Delete the old one:** go to your repo on github.com → **Settings** → scroll to the bottom →
**Delete this repository** → type the name to confirm.

**Make a new empty one:** github.com → **+** → **New repository** → name it
`brightbasket-margin-leak` → **Public** → leave README, .gitignore and licence **unticked** →
Create.

**Push,** one command at a time from the project folder:

```
git init
```
```
git add .
```
```
git commit -m "Order-level margin analysis: SQL, Python, Excel"
```
```
git branch -M main
```
```
git remote add origin https://github.com/prathamhirolikar7-hash/brightbasket-margin-leak.git
```
```
git push -u origin main
```

A browser window will open for sign-in. After that it uploads about 9 MB.

## 6. Check the repo page

Open your repo and confirm:

- The README shows with the four charts
- `notebooks/01_cleaning_and_analysis.ipynb` opens as a notebook with results, not raw code
- No broken links

Then add a description: click the gear next to **About** and paste:

> Order-level profit analysis on 39K D2C orders. Found ₹11.5L of annual losses and two rule
> changes worth ₹5.7L. Excel, SQL, Python.

And pin it: your profile → **Customize your pins** → tick this repo.
