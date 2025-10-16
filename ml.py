import argparse
from pathlib import Path
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, cross_validate, StratifiedKFold
from sklearn.metrics import classification_report, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(".")
CSV_IN = ROOT / "core" / "data" / "ranked_functions_scores.csv"
LABEL_CANDIDATES = ROOT / "core" / "data" / "label_candidates.csv"
LABELS_IN = ROOT / "core" / "data" / "labels.csv"   # user-supplied labelled file
MODEL_OUT = ROOT / "core" / "data" / "rf_model.joblib"
PRED_OUT = ROOT / "core" / "data" / "ranked_functions_ml.csv"

def load_ranked_csv():
    if not CSV_IN.exists():
        raise FileNotFoundError(f"{CSV_IN} not found. Run rank_functions.py first.")
    df = pd.read_csv(CSV_IN)
    return df

def prepare_label_candidates(df, n_top=50, n_bottom=50, n_mid=50):
    df_sorted = df.sort_values("importance", ascending=False).reset_index(drop=True)
    top = df_sorted.head(n_top)
    bottom = df_sorted.tail(n_bottom)
    # ambiguous mid sample: nearest to median importance
    median_imp = df_sorted["importance"].median()
    df_sorted["dist_med"] = (df_sorted["importance"] - median_imp).abs()
    mid = df_sorted.sort_values("dist_med").iloc[:n_mid]
    candidates = pd.concat([top, mid, bottom]).drop_duplicates(subset=["id"]).reset_index(drop=True)
    # keep useful columns for labeling
    cols = ["id", "label", "importance", "triviality", "loc", "complexity", "num_calls",
            "num_params", "doc_len", "keyword_matches", "one_liner", "has_type_annotations"]
    # ensure columns exist
    for c in cols:
        if c not in candidates.columns:
            candidates[c] = ""
    # Add empty label column for human labeling
    if "human_label" not in candidates.columns:
        candidates["human_label"] = ""
    candidates.to_csv(LABEL_CANDIDATES, index=False)
    print(f"[+] Labeling candidates created at: {LABEL_CANDIDATES}")
    print("  -> Open this CSV and add a column 'human_label' with values 'utility' or 'core' for each row.")
    print("  -> When done, save as core/data/labels.csv and run: python3 train_ml.py --train")

def build_feature_matrix(df):
    # select features that were used by heuristic
    features = []
    for c in ["loc", "complexity", "num_calls", "num_params", "doc_len", "keyword_matches", "num_imports", "one_liner", "has_type_annotations"]:
        if c in df.columns:
            features.append(c)
    X = df[features].fillna(0).astype(float)
    return X, features

def train_and_evaluate(df, labels):
    # df: full dataset (for predictions)
    # labels: labeled subset with 'id' and 'human_label'
    # prepare training set by joining features
    X_all, feature_names = build_feature_matrix(df)
    df_features = df[["id"]].copy()
    for i, c in enumerate(feature_names):
        df_features[c] = X_all.iloc[:, i].values

    # load labels
    lab = pd.read_csv(LABELS_IN)
    if "human_label" not in lab.columns:
        raise ValueError("labels.csv must contain a 'human_label' column with values 'utility' or 'core'")

    lab = lab[["id", "human_label"]].dropna()
    lab = lab[lab["human_label"].isin(["utility", "core"])]
    merged = df_features.merge(lab, on="id", how="inner")
    if merged.shape[0] < 20:
        print("WARNING: less than 20 labeled samples. Model may not generalize well. Try to label at least 50-100 examples.")
    X = merged[feature_names].values
    y = (merged["human_label"] == "core").astype(int).values  # core=1, utility=0

    # pipeline with scaling + RF
    pipe = Pipeline([
        ("sc", StandardScaler()),
        ("rf", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced"))
    ])

    # cross-validated metrics (precision for utility class is important — we want less false positives)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["precision", "recall", "f1"]
    scores = cross_validate(pipe, X, y, cv=cv, scoring=scoring, return_train_score=False)
    print("\n=== Cross-validated scores (core class=1) ===")
    print(f"Precision: {np.mean(scores['test_precision']):.3f} ± {np.std(scores['test_precision']):.3f}")
    print(f"Recall:    {np.mean(scores['test_recall']):.3f} ± {np.std(scores['test_recall']):.3f}")
    print(f"F1:        {np.mean(scores['test_f1']):.3f} ± {np.std(scores['test_f1']):.3f}")

    # fit on all labeled data
    pipe.fit(X, y)
    # save model
    joblib.dump(pipe, MODEL_OUT)
    print(f"[+] Model saved to: {MODEL_OUT}")

    # predict probabilities on full dataset
    X_full = df_features[feature_names].values
    probs = pipe.predict_proba(X_full)  # columns: prob(utility=0), prob(core=1)
    prob_core = probs[:, 1]  # probability for core
    df_out = df.copy()
    df_out["model_prob_core"] = prob_core
    # combined score: simple average of heuristic importance and model prob (tweakable)
    if "importance" in df_out.columns:
        df_out["combined_score"] = (
    0.4 * df_out["importance"].astype(float) +
    0.6 * df_out["model_prob_core"]
)
    else:
        df_out["combined_score"] = df_out["model_prob_core"]

    # sort by combined score (most important first)
    df_out = df_out.sort_values("combined_score", ascending=False).reset_index(drop=True)
    df_out.to_csv(PRED_OUT, index=False)
    print(f"[+] Predictions and combined scores written to: {PRED_OUT}")

    # show top/bottom few
    print("\nTop 5 by combined_score:")
    print(df_out[["id", "label", "importance", "model_prob_core", "combined_score"]].head(5).to_string(index=False))
    print("\nBottom 5 by combined_score:")
    print(df_out[["id", "label", "importance", "model_prob_core", "combined_score"]].tail(5).to_string(index=False))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-labels", action="store_true", help="Create core/data/label_candidates.csv for manual labeling")
    parser.add_argument("--train", action="store_true", help="Train model using core/data/labels.csv (must exist)")
    parser.add_argument("--candidates", type=int, default=150, help="Number of labeling candidates (default 150)")
    args = parser.parse_args()

    df = load_ranked_csv()

    if args.prepare_labels:
        n = args.candidates
        print("[+] Preparing labeling candidates...")
        prepare_label_candidates(df, n_top=50, n_bottom=50, n_mid=(n - 100))
        return

    if args.train:
        if not LABELS_IN.exists():
            print(f"ERROR: labels file {LABELS_IN} not found. Create it by labeling {LABEL_CANDIDATES} and saving as core/data/labels.csv", flush=True)
            return
        print("[+] Training model using labels in:", LABELS_IN)
        train_and_evaluate(df, LABELS_IN)
        return

    parser.print_help()

if __name__ == "__main__":
    main()