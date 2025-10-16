import re
import pandas as pd
from pathlib import Path

# Paths
DATA_DIR = Path("core/data")
CANDIDATES = DATA_DIR / "label_candidates.csv"
LABELS_OUT = DATA_DIR / "labels.csv"
UNCERTAIN_OUT = DATA_DIR / "uncertain_labels.csv"

if not CANDIDATES.exists():
    raise FileNotFoundError(f"{CANDIDATES} not found. Run: python3 train_ml.py --prepare-labels first.")

df = pd.read_csv(CANDIDATES)

def guess_label(row):
    """Return 'utility', 'core', or '' (uncertain)."""
    name = str(row.get("label", "")).lower()
    file_id = str(row.get("id", "")).lower()
    loc = float(row.get("loc", 0))
    comp = float(row.get("complexity", 0))
    kw = float(row.get("keyword_matches", 0))
    one_liner = int(row.get("one_liner", 0))

    # Patterns strongly indicating utility
    util_keywords = [
        "util", "helper", "parse", "to_", "from_", "convert",
        "str", "format", "encode", "decode", "validate", "calc",
        "sum", "avg", "is_", "has_", "print", "len", "split", "join", "replace"
    ]

    if any(k in name for k in util_keywords) or one_liner or loc <= 3 or kw >= 2:
        return "utility"

    # Patterns strongly indicating core logic
    core_keywords = [
        "route", "app", "endpoint", "request", "response", "schema", "model",
        "router", "startup", "shutdown", "include", "register", "mount",
        "middleware", "api", "handler", "process", "dispatch", "run"
    ]

    if any(k in name for k in core_keywords) or comp >= 6 or loc >= 20:
        return "core"

    # Fallback based on file path
    if "utils" in file_id or "helpers" in file_id:
        return "utility"
    if "applications" in file_id or "routing" in file_id or "endpoints" in file_id:
        return "core"

    # Uncertain
    return ""

# Apply heuristic labeling
df["human_label"] = df.apply(guess_label, axis=1)

# Summarize results
counts = df["human_label"].value_counts(dropna=False)
n_total = len(df)
n_core = counts.get("core", 0)
n_util = counts.get("utility", 0)
n_uncertain = df["human_label"].eq("").sum()

print("=== Auto-label Summary ===")
print(f"Total rows:     {n_total}")
print(f"Labeled 'core': {n_core}")
print(f"Labeled 'utility': {n_util}")
print(f"Uncertain (manual check): {n_uncertain}")
print("===========================")

# Save full labels
df.to_csv(LABELS_OUT, index=False)
print(f"[+] Auto-labeled dataset saved to: {LABELS_OUT}")

# Save uncertain subset for manual review
if n_uncertain > 0:
    uncertain_df = df[df["human_label"] == ""].copy()
    uncertain_df.to_csv(UNCERTAIN_OUT, index=False)
    print(f"[!] Uncertain rows saved to: {UNCERTAIN_OUT}")
    print("→ You can open this file and label only those few manually.")
else:
    print("✅ All rows labeled confidently. You can train immediately.")

print("\nNext step:")
print("  python3 train_ml.py --train")