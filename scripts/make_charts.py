"""
make_charts.py -- renders the four dashboard visuals as PNGs.

WHY THIS EXISTS: the Power BI dashboard is built by hand from dashboard/README.md.
These PNGs are the reference for that build -- same four charts, same design
decisions -- and they also let the repo show its findings visually to anyone
who opens it on GitHub without opening Power BI.

Every design choice here is justified in dashboard/README.md. If you change a
chart, change the reasoning there too.
"""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / "data" / "processed" / "order_economics.csv")

plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 130})
LOSS, GAIN, MUTE = "#C0392B", "#2E7D6F", "#9AA5B1"

# --- Chart 1: CM per order by zone x payment ---------------------------------
# Horizontal (long labels), sorted by value (worst first), diverging at zero
# (zero is the decision boundary, not a gridline), colour encodes sign only.
s = (df.groupby(["zone", "payment_mode"]).contribution_margin.mean()
       .round(1).sort_values())
labels = [f"{z} — {p}" for z, p in s.index]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.barh(labels, s.values, color=[LOSS if v < 0 else GAIN for v in s.values])
ax.axvline(0, color="#333", lw=1.2)
for i, v in enumerate(s.values):
    ax.text(v + (3 if v >= 0 else -3), i, f"₹{v}", va="center",
            ha="left" if v >= 0 else "right", fontsize=9, fontweight="bold")
ax.set_title("Only one segment loses money: COD in Tier 3",
             fontweight="bold", loc="left", pad=12)
ax.set_xlabel("Contribution margin per order (₹)")
ax.set_xlim(-25, 145)
fig.tight_layout(); fig.savefig(OUT / "01_margin_by_zone_payment.png"); plt.close(fig)

# --- Chart 2: CM per order by value band -------------------------------------
# Vertical (bands have a natural low->high order), reference line ON the policy
# boundary so the reader sees a policy causing a cliff, not five rising bars.
order = ["Under 300", "300-499", "500-699", "700-999", "1000+"]
b = df.groupby("value_band").contribution_margin.mean().reindex(order).round(1)
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.bar(b.index, b.values, color=[LOSS if v < 0 else GAIN for v in b.values], width=.62)
ax.axhline(0, color="#333", lw=1.2)
ax.axvline(1.5, color="#E67E22", ls="--", lw=1.6)
ax.text(1.58, 250, "Free delivery\nstarts here (₹499)", color="#E67E22",
        fontsize=9, fontweight="bold", va="top")
for i, v in enumerate(b.values):
    ax.text(i, v + (10 if v >= 0 else -22), f"₹{v}", ha="center",
            fontsize=9, fontweight="bold")
ax.set_title("Our own free-delivery threshold creates a margin cliff",
             fontweight="bold", loc="left", pad=12)
ax.set_ylabel("Contribution margin per order (₹)")
ax.set_xlabel("Net order value band")
ax.set_ylim(-60, 380)
fig.tight_layout(); fig.savefig(OUT / "02_margin_by_value_band.png"); plt.close(fig)

# --- Chart 3: courier, raw vs controlled -------------------------------------
# Paired bars, because the COMPARISON is the message. Showing only the corrected
# view would hide the trap and leave "take no action" looking unmotivated.
raw = df.groupby("courier_partner").contribution_margin.mean().round(1)
t3 = (df[df.zone == "Tier3"].groupby("courier_partner")
        .contribution_margin.mean().round(1))
cs = ["BharatShip", "SwiftLogix", "ZipEx"]
x = range(len(cs)); w = 0.36
fig, ax = plt.subplots(figsize=(7.2, 3.6))
ax.bar([i - w/2 for i in x], [raw[c] for c in cs], w, label="As reported (all zones)", color=MUTE)
ax.bar([i + w/2 for i in x], [t3[c] for c in cs], w, label="Within Tier 3 only", color=GAIN)
for i, c in enumerate(cs):
    ax.text(i - w/2, raw[c] + 2, f"₹{raw[c]}", ha="center", fontsize=8.5, fontweight="bold")
    ax.text(i + w/2, t3[c] + 2, f"₹{t3[c]}", ha="center", fontsize=8.5, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(cs)
ax.set_title("The courier gap disappears once you compare like routes with like",
             fontweight="bold", loc="left", pad=12)
ax.set_ylabel("Contribution margin per order (₹)")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(0, 118)
fig.tight_layout(); fig.savefig(OUT / "03_courier_raw_vs_controlled.png"); plt.close(fig)

# --- Chart 4: where the leak sits --------------------------------------------
t = df[(df.payment_mode == "COD") & (df.zone == "Tier3") & (df.net_order_value < 700)]
fig, ax = plt.subplots(figsize=(7.2, 2.5)); ax.axis("off")
rows = [
    ("Target pocket", "COD · Tier 3 · under ₹700"),
    ("Orders affected", f"{len(t):,}  ({100*len(t)/len(df):.1f}% of volume)"),
    ("RTO rate", f"{100*(t.order_status=='RTO').mean():.1f}%"),
    ("Current margin", f"−₹{abs(t.contribution_margin.sum()):,.0f}  (₹{t.contribution_margin.mean():.1f}/order)"),
    ("Net gain if fixed", "₹1,96,329"),
    ("Revenue given up", "₹9,61,197   ← the honest cost"),
]
for i, (k, v) in enumerate(rows):
    y = 0.92 - i * 0.16
    ax.text(0.02, y, k, fontsize=10, color="#5A6472")
    ax.text(0.40, y, v, fontsize=10.5, fontweight="bold",
            color=LOSS if "given up" in k or "Current" in k else "#1A1A1A")
ax.set_title("The recommendation, with its cost stated",
             fontweight="bold", loc="left", pad=6)
fig.tight_layout(); fig.savefig(OUT / "04_target_pocket_scorecard.png"); plt.close(fig)

print("wrote 4 charts to", OUT)
for p in sorted(OUT.glob("*.png")):
    print(" ", p.name, f"{p.stat().st_size//1024} KB")
