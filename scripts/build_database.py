"""
build_database.py -- loads the four raw CSVs into a SQLite database and creates
the order_economics view, so every .sql file in sql/ is runnable as-is.

WHY SQLITE: it is a single file, needs no server, and opens in DB Browser for
SQLite (free). For a 40k-row project a database server would be theatre. The
SQL used is standard enough to run on MySQL or Postgres with no changes beyond
the CREATE VIEW header.

Run: python scripts/build_database.py
Out: data/brightbasket.db
"""
import sqlite3, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "brightbasket.db"
DB.unlink(missing_ok=True)
con = sqlite3.connect(DB)

for name in ["orders", "customers", "pincodes", "logistics"]:
    df = pd.read_csv(ROOT / "data" / "raw" / f"{name}.csv")
    df.to_sql(name, con, index=False)
    print(f"loaded {name:10s} {len(df):>7,} rows")

# Cleaning that must happen IN the database before the view is usable.
# Kept as explicit UPDATE/DELETE statements so the audit trail is visible.
cur = con.cursor()

# De-duplicate on order_id, keeping the first physical row (rowid).
cur.execute("""DELETE FROM orders WHERE rowid NOT IN
               (SELECT MIN(rowid) FROM orders GROUP BY order_id)""")
print(f"removed {cur.rowcount} duplicate order rows")

# Negative discounts are sign errors on a magnitude field.
cur.execute("UPDATE orders SET discount_amount = ABS(discount_amount) WHERE discount_amount < 0")
print(f"corrected {cur.rowcount} negative discounts")

# City casing, standardised before any GROUP BY city.
cur.execute("""UPDATE pincodes SET city =
               UPPER(SUBSTR(TRIM(city),1,1)) || LOWER(SUBSTR(TRIM(city),2))""")

# Phantom shipping cost billed on orders that were never dispatched.
cur.execute("""UPDATE logistics SET forward_shipping_cost = 0
               WHERE order_id IN (SELECT order_id FROM orders WHERE order_status='Cancelled')
                 AND forward_shipping_cost > 0""")
print(f"zeroed {cur.rowcount} phantom shipping charges on cancelled orders")

cur.executescript((ROOT / "sql" / "02_order_economics_view.sql").read_text())
con.commit()

chk = pd.read_sql("""SELECT COUNT(*) rows, ROUND(SUM(contribution_margin)) cm,
                            SUM(CASE WHEN contribution_margin<0 THEN 1 ELSE 0 END) loss_orders
                     FROM order_economics""", con)
print("\nview check:\n", chk.to_string(index=False))
con.close()
print(f"\ndatabase ready: {DB}")
