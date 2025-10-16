import json
import ast
import re
import sys
from pathlib import Path

# Optional: pandas for CSV output (falls back to csv module)
try:
    import pandas as pd
    PANDAS_OK = True
except Exception:
    PANDAS_OK = False

ROOT = Path(".")
INPUT = ROOT / "core" / "data" / "analysis-with-code.json"
OUT_CSV = ROOT / "core" / "data" / "ranked_functions_scores.csv"
OUT_JSON = ROOT / "core" / "data" / "ranked_functions.json"

if not INPUT.exists():
    print(f"ERROR: input file not found at {INPUT}", file=sys.stderr)
    sys.exit(1)

with INPUT.open("r", encoding="utf-8") as f:
    data = json.load(f)

nodes = data.get("analysisData", {}).get("graphNodes", [])
print(f"[+] Found {len(nodes)} nodes in input JSON. Processing...")

# AST helpers
BRANCH_NODES = (ast.If, ast.For, ast.While, ast.IfExp, ast.Try, ast.ExceptHandler, ast.With)

def safe_parse(code_str):
    if not code_str or not isinstance(code_str, str):
        return None
    try:
        return ast.parse(code_str)
    except Exception:
        # wrap in a dummy function to try to parse fragments
        try:
            wrapped = "def __wrapper__():\n" + "\n".join("    " + ln for ln in code_str.splitlines())
            return ast.parse(wrapped)
        except Exception:
            return None

def compute_cyclomatic_complexity(tree):
    if tree is None:
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, BRANCH_NODES):
            count += 1
        if isinstance(node, ast.BoolOp):
            count += max(0, len(node.values) - 1)
    return max(1, count + 1)

def count_nodes_of_type(tree, t):
    if tree is None:
        return 0
    return sum(1 for n in ast.walk(tree) if isinstance(n, t))

def extract_docstring_length(tree):
    if tree is None:
        return 0
    doc = ast.get_docstring(tree)
    if doc:
        return len(doc)
    # fallback: first FunctionDef's docstring
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            ds = ast.get_docstring(node)
            if ds:
                return len(ds)
    return 0

keyword_pattern = re.compile(
    r"\b(get|set|to_|from_|format|util|helper|json|str|parse|is_\w+|has_\w+|len\(|join\(|split\()",
    flags=re.IGNORECASE
)

rows = []
for node in nodes:
    # Preserve original node dict (keeps hidden metadata)
    original_node = dict(node) if isinstance(node, dict) else {"id": str(node)}

    node_id = original_node.get("id")
    label = original_node.get("label", "") or ""
    code = original_node.get("code", "") or ""

    # static features
    loc = len([ln for ln in str(code).splitlines() if ln.strip() != ""])
    tree = safe_parse(code)
    complexity = compute_cyclomatic_complexity(tree)
    num_funcs = count_nodes_of_type(tree, ast.FunctionDef)
    num_params = 0
    if tree:
        fdefs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        if fdefs:
            try:
                num_params = len(fdefs[0].args.args)
            except Exception:
                num_params = 0
        else:
            lambdas = [n for n in ast.walk(tree) if isinstance(n, ast.Lambda)]
            if lambdas:
                try:
                    num_params = len(lambdas[0].args.args)
                except Exception:
                    num_params = 0

    num_calls = count_nodes_of_type(tree, ast.Call)
    num_returns = count_nodes_of_type(tree, ast.Return)
    num_assigns = count_nodes_of_type(tree, ast.Assign) + count_nodes_of_type(tree, ast.AugAssign)
    num_imports = count_nodes_of_type(tree, ast.Import) + count_nodes_of_type(tree, ast.ImportFrom)
    doc_len = extract_docstring_length(tree)
    keyword_matches = len(keyword_pattern.findall(str(code)))
    one_liner = 1 if loc <= 3 and len(str(code).strip().splitlines()) <= 3 else 0
    has_type_annotations = 1 if (":" in str(code) and "->" in str(code)) or (":" in str(code) and re.search(r":\s*\w", str(code))) else 0

    # create a combined row: keep original fields then add analysis features
    row = dict(original_node)  # preserves any hidden fields
    row.update({
        "id": node_id,
        "label": label,
        "loc": int(loc),
        "complexity": float(complexity),
        "num_funcs": int(num_funcs),
        "num_params": int(num_params),
        "num_calls": int(num_calls),
        "num_returns": int(num_returns),
        "num_assigns": int(num_assigns),
        "num_imports": int(num_imports),
        "doc_len": int(doc_len),
        "keyword_matches": int(keyword_matches),
        "one_liner": int(one_liner),
        "has_type_annotations": int(has_type_annotations),
        # keep a tiny snippet in case it's inspected later
        "code_snippet": (str(code)[:1000] + "...") if len(str(code)) > 1000 else str(code)
    })
    rows.append(row)

# Normalize numeric features (min-max)
numeric_cols = ["loc", "complexity", "num_funcs", "num_params", "num_calls",
                "num_returns", "num_assigns", "num_imports", "doc_len", "keyword_matches"]

def min_max(vals):
    if not vals:
        return []
    mn = min(vals)
    mx = max(vals)
    if abs(mx - mn) < 1e-12:
        return [0.0 for _ in vals]
    return [(v - mn) / (mx - mn) for v in vals]

col_vals = {c: [r.get(c, 0) for r in rows] for c in numeric_cols}
col_norm = {c: min_max(col_vals[c]) for c in numeric_cols}

for i, r in enumerate(rows):
    for c in numeric_cols:
        r[f"{c}_norm"] = float(col_norm[c][i])

# Heuristic weights
weights = {
    "loc_norm": 0.35,
    "complexity_norm": 0.20,
    "num_calls_norm": 0.05,
    "num_params_norm": 0.05,
    "keyword_matches_norm": 0.20,
    "doc_len_norm": 0.05,
    "num_imports_norm": 0.05
}

def compute_triviality(r):
    loc_n = r.get("loc_norm", 0.0)
    comp_n = r.get("complexity_norm", 0.0)
    calls_n = r.get("num_calls_norm", 0.0)
    params_n = r.get("num_params_norm", 0.0)
    kw_n = r.get("keyword_matches_norm", 0.0)
    doc_n = r.get("doc_len_norm", 0.0)
    imports_n = r.get("num_imports_norm", 0.0)

    score = (
        weights["loc_norm"] * (1.0 - loc_n) +
        weights["complexity_norm"] * (1.0 - comp_n) +
        weights["num_calls_norm"] * (1.0 - calls_n) +
        weights["num_params_norm"] * (1.0 - params_n) +
        weights["keyword_matches_norm"] * kw_n +
        weights["doc_len_norm"] * (1.0 - doc_n) +
        weights["num_imports_norm"] * (1.0 - imports_n)
    )

    if r.get("one_liner", 0) and r.get("num_calls", 0) <= 1 and r.get("complexity", 0) <= 2:
        score = min(1.0, score + 0.10)

    # --- NEW: protect short but important core logic ---
    name = str(r.get("label", "")).lower()
    file_id = str(r.get("id", "")).lower()

    critical_names = ["__init__", "decorator", "on_event", "setup", "configure", "mount"]
    critical_files = ["applications", "routing", "endpoints", "schemas", "models"]

    if any(k in name for k in critical_names) or any(f in file_id for f in critical_files):
        # these are often core even if short → lower triviality
        score = max(0.0, score - 0.15)

    # reward documentation and typing (sign of design importance)
    if r.get("has_type_annotations", 0) or r.get("doc_len", 0) > 80:
        score = max(0.0, score - 0.08)


    return max(0.0, min(1.0, float(score)))

for r in rows:
    r["triviality"] = round(compute_triviality(r), 4)
    r["importance"] = round(1.0 - r["triviality"], 4)

# Sort by importance descending for output
rows_sorted = sorted(rows, key=lambda x: x.get("importance", 0.0), reverse=True)

# Ensure output folder exists
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

# Write JSON (full rows_sorted)
OUT_JSON.write_text(json.dumps({"function_rankings": rows_sorted}, indent=2), encoding="utf-8")
print(f"[+] Written JSON to: {OUT_JSON}")

# Write CSV
csv_columns = [
    # include original fields 'id' and 'label' first, then core numeric fields
    "id", "label", "importance", "triviality",
    "loc", "complexity", "num_funcs", "num_params",
    "num_calls", "num_returns", "num_assigns", "num_imports",
    "doc_len", "keyword_matches", "one_liner", "has_type_annotations"
]

if PANDAS_OK:
    import pandas as pd
    df = pd.DataFrame(rows_sorted)
    # try to reorder columns to csv_columns if available
    cols_present = [c for c in csv_columns if c in df.columns]
    df.to_csv(OUT_CSV, index=False, columns=cols_present)
    print(f"[+] Written CSV to: {OUT_CSV} (using pandas)")
else:
    import csv
    with OUT_CSV.open("w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=[c for c in csv_columns])
        writer.writeheader()
        for r in rows_sorted:
            writer.writerow({c: r.get(c, "") for c in csv_columns})
    print(f"[+] Written CSV to: {OUT_CSV} (using csv)")

# Final sanity check: counts
out_rows_count = 0
try:
    with OUT_CSV.open("r", encoding="utf-8") as f:
        out_rows_count = len(f.read().splitlines()) - 1  # minus header
except Exception:
    out_rows_count = len(rows_sorted)

print(f"[+] Input nodes: {len(nodes)}")
print(f"[+] Output CSV rows: {out_rows_count}")
if len(nodes) != out_rows_count:
    print("WARNING: counts differ! Make sure no rows were dropped.", file=sys.stderr)
else:
    print("[+] Counts match. All nodes preserved.")

print("[+] Done.")