from joblib import load
import matplotlib.pyplot as plt
import numpy as np

# Load trained pipeline
model = load("core/data/rf_model.joblib")

# Extract components
rf = model.named_steps["rf"]
scaler = model.named_steps["sc"]

# Try to get feature names safely
try:
    features = scaler.feature_names_in_
except AttributeError:
    # Fallback for older sklearn versions
    import pandas as pd
    features = [f"feature_{i}" for i in range(len(rf.feature_importances_))]

# Sort importances
importances = rf.feature_importances_
idx = np.argsort(importances)

# Plot
plt.figure(figsize=(8, 6))
plt.barh(np.array(features)[idx], importances[idx])
plt.xlabel("Importance")
plt.ylabel("Feature")
plt.title("RandomForest Feature Importances (Core vs Utility)")
plt.tight_layout()
plt.savefig("core/data/feature_importance.png")

print("[+] Saved feature importance chart to core/data/feature_importance.png")