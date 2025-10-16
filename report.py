import base64
from io import BytesIO
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
DATA_DIR = Path("core/data")
CSV_HEURISTIC = DATA_DIR / "ranked_functions_scores.csv"
CSV_ML = DATA_DIR / "ranked_functions_ml.csv"
OUT_HTML = DATA_DIR / "ranked_functions_report.html"

# ---------- Load data ----------
if not CSV_HEURISTIC.exists():
    raise FileNotFoundError("Missing ranked_functions_scores.csv — run rank_functions.py first.")

df = pd.read_csv(CSV_HEURISTIC)
has_ml = CSV_ML.exists()
if has_ml:
    df_ml = pd.read_csv(CSV_ML)
    # merge to compare combined_score vs heuristic
    df = df.merge(
        df_ml[["id", "model_prob_core", "combined_score"]],
        on="id", how="left"
    )

# ---------- Plots ----------
sns.set(style="whitegrid")

def fig_to_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

# 1. Importance distribution (heuristic)
fig, ax = plt.subplots(figsize=(8, 4))
sns.histplot(df["importance"], bins=30, kde=True, ax=ax)
ax.set_title("Heuristic Importance Distribution")
ax.set_xlabel("Importance")
importance_b64 = fig_to_b64(fig)
plt.close(fig)

# 2. If ML available, plot combined vs heuristic
scatter_b64 = ""
if has_ml:
    fig, ax = plt.subplots(figsize=(6, 6))
    sns.scatterplot(
        data=df, x="importance", y="combined_score",
        hue=(df["combined_score"] > 0.5),
        palette=["#999", "#2b8a3e"], alpha=0.6, legend=False
    )
    ax.set_title("Heuristic vs Combined (ML) Scores")
    ax.set_xlabel("Heuristic Importance")
    ax.set_ylabel("ML Combined Score")
    scatter_b64 = fig_to_b64(fig)
    plt.close(fig)

# 3. Correlation heatmap (numeric features)
num_cols = df.select_dtypes("number").columns
corr_b64 = ""
if len(num_cols) > 2:
    corr = df[num_cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, cmap="vlag", center=0, annot=True, fmt=".2f", ax=ax)
    ax.set_title("Feature Correlation Heatmap")
    corr_b64 = fig_to_b64(fig)
    plt.close(fig)

# ---------- Tables ----------
top_df = df.sort_values("importance", ascending=False).head(50)
bottom_df = df.sort_values("importance", ascending=True).head(50)

def df_html(df_sub):
    return df_sub.to_html(classes="summary", index=False, escape=False)

main_html = df.to_html(classes="display nowrap compact", index=False, table_id="main_table", escape=False)
top_html = df_html(top_df)
bottom_html = df_html(bottom_df)

# ---------- Build HTML ----------
html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Ranked Functions Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
<style>
body {{
  font-family: system-ui, Arial, sans-serif;
  margin: 20px;
  background: #fafafa;
}}
h1,h2,h3 {{ margin-top: 1em; }}
table.dataTable tbody tr:hover {{ background-color: #f0f0f0; }}
img.plot {{ max-width: 100%; border: 1px solid #ccc; border-radius: 6px; margin-bottom: 16px; }}
summary,details {{ margin-bottom: 8px; }}
.code {{ font-family: monospace; font-size: 13px; background:#f9f9f9; padding:2px 4px; border-radius:4px; }}
</style>
</head>
<body>

<h1>Function Ranking Report</h1>
<p>Total functions: <strong>{len(df):,}</strong></p>

{"<h2>Includes ML-enhanced scores</h2>" if has_ml else "<h2>Heuristic-only report</h2>"}

<h3>Plots</h3>
<img class="plot" src="data:image/png;base64,{importance_b64}" alt="Importance distribution">
{f'<img class="plot" src="data:image/png;base64,{scatter_b64}" alt="Heuristic vs ML scatter">' if has_ml else ""}
{f'<img class="plot" src="data:image/png;base64,{corr_b64}" alt="Correlation heatmap">' if corr_b64 else ""}

<h3>Interactive Table (All Functions)</h3>
<p>You can search, sort, and filter columns.</p>
<table id="main_table" class="display nowrap compact" style="width:100%">
{main_html}
</table>

<h3>Top 50 Functions (Most Important)</h3>
{top_html}

<h3>Bottom 50 Functions (Most Trivial)</h3>
{bottom_html}

<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script>
$(document).ready(function() {{
  $('#main_table').DataTable({{
    pageLength: 25,
    scrollX: true,
    order: [[2, 'desc']],
  }});
}});
</script>
</body>
</html>
"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"[+] Report written to {OUT_HTML}")
print("[+] Open it in your browser to explore interactively.")