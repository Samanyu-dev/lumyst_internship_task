import json
import csv
from pathlib import Path
import sys

ROOT = Path(".")
IN_JSON = ROOT / "core" / "data" / "analysis-with-code.json"
OUT_JSON = ROOT / "core" / "data" / "ranked_functions.json"
OUT_CSV = ROOT / "core" / "data" / "ranked_functions_scores.csv"
REPORT = ROOT / "core" / "data" / "preservation_report.txt"

def load_input_ids():
    with IN_JSON.open("r", encoding="utf-8") as f:
        j = json.load(f)
    nodes = j.get("analysisData", {}).get("graphNodes", [])
    ids = [n.get("id") for n in nodes]
    return ids

def load_out_json_ids():
    if not OUT_JSON.exists():
        return []
    with OUT_JSON.open("r", encoding="utf-8") as f:
        j = json.load(f)
    rows = j.get("function_rankings", [])
    ids = [r.get("id") for r in rows]
    return ids

def load_csv_ids():
    if not OUT_CSV.exists():
        return []
    ids = []
    with OUT_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(row.get("id"))
    return ids

def write_report(text):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8") as f:
        f.write(text)

def main():
    in_ids = load_input_ids()
    out_json_ids = load_out_json_ids()
    csv_ids = load_csv_ids()

    set_in = set(in_ids)
    set_out_json = set(out_json_ids)
    set_csv = set(csv_ids)

    missing_in_json = sorted(list(set_in - set_out_json))
    missing_in_csv = sorted(list(set_in - set_csv))
    extra_in_json = sorted(list(set_out_json - set_in))
    extra_in_csv = sorted(list(set_csv - set_in))

    ok = True
    report_lines = []
    report_lines.append(f"Input nodes: {len(in_ids)}")
    report_lines.append(f"Output JSON rows: {len(out_json_ids)}")
    report_lines.append(f"Output CSV rows: {len(csv_ids)}")
    report_lines.append("")

    if missing_in_json:
        ok = False
        report_lines.append("MISSING IN ranked_functions.json (IDs present in input but NOT in output JSON):")
        report_lines.extend(missing_in_json[:200])
    else:
        report_lines.append("No missing IDs in ranked_functions.json")

    report_lines.append("")

    if missing_in_csv:
        ok = False
        report_lines.append("MISSING IN ranked_functions_scores.csv (IDs present in input but NOT in output CSV):")
        report_lines.extend(missing_in_csv[:200])
    else:
        report_lines.append("No missing IDs in ranked_functions_scores.csv")

    report_lines.append("")

    if extra_in_json:
        report_lines.append("EXTRA IDs in ranked_functions.json not present in input (unexpected):")
        report_lines.extend(extra_in_json[:50])
    if extra_in_csv:
        report_lines.append("EXTRA IDs in ranked_functions_scores.csv not present in input (unexpected):")
        report_lines.extend(extra_in_csv[:50])

    report_text = "\n".join(report_lines)
    write_report(report_text)

    print(report_text)
    if not ok:
        print("\n[!] Verification FAILED. See core/data/preservation_report.txt for details.")
        sys.exit(2)
    else:
        print("\n[+] Verification PASSED. All IDs preserved.")
        sys.exit(0)

if __name__ == "__main__":
    main()