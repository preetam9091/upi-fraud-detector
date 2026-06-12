import numpy as np
import shap
import joblib
import matplotlib.pyplot as plt
import os
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve, average_precision_score
)

def evaluate(model, X_test, y_test):
    """
    Evaluate model performance. For fraud detection, RECALL is the most important metric.

    WHY RECALL OVER ACCURACY?
    Accuracy is useless for imbalanced data.
    If your model predicts "not fraud" for every transaction, it's 99.7% accurate
    but catches 0% of fraud — completely useless.

    RECALL = what % of actual fraud cases did we catch?
    Target: > 90% recall (miss fewer than 1 in 10 fraud cases)

    PRECISION = of the ones we flagged as fraud, what % were actually fraud?
    Target: > 50% precision (not spamming users with false alarms)

    F1 = harmonic mean of precision and recall (overall balance)
    AUC-PR = best single number for imbalanced classification
    """
    print("\n  [→] Running evaluation...")

    # Get predictions
    y_pred       = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Classification report
    print("\n  ── Classification Report ──")
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"],
                                 digits=3))

    # Key numbers
    auc_roc = roc_auc_score(y_test, y_pred_proba)
    auc_pr  = average_precision_score(y_test, y_pred_proba)
    print(f"  AUC-ROC  : {auc_roc:.4f}  (target: >0.95)")
    print(f"  AUC-PR   : {auc_pr:.4f}   (target: >0.70 for imbalanced data)")

    # Confusion matrix (shows exactly what the model got right/wrong)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    print(f"\n  ── Confusion Matrix ──")
    print(f"  True Negatives  (correctly said legit)  : {tn:,}")
    print(f"  False Positives (wrongly flagged legit)  : {fp:,}")
    print(f"  False Negatives (missed actual fraud)    : {fn:,}  ← minimize this")
    print(f"  True Positives  (correctly caught fraud) : {tp:,}  ← maximize this")

    os.makedirs("model/artifacts", exist_ok=True)

    # ── SHAP EXPLAINABILITY ────────────────────────────────────────────────
    # SHAP tells you: for each prediction, which features pushed the score up or down?
    # This is what makes your project defensible in interviews.
    # "My model doesn't just say 'fraud' — it says WHY it thinks it's fraud."
    print("\n  [→] Computing SHAP values (this takes ~1 min)...")

    explainer   = shap.TreeExplainer(model)
    # Use a sample of 2000 test cases — full dataset would take too long
    sample_idx  = np.random.choice(len(X_test), size=min(2000, len(X_test)), replace=False)
    X_sample    = X_test.iloc[sample_idx]
    shap_values = explainer.shap_values(X_sample)

    # Global feature importance plot
    # Shows: across all transactions, which features matter most?
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.title("Feature Importance (SHAP)")
    plt.tight_layout()
    plt.savefig("model/artifacts/shap_importance.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: model/artifacts/shap_importance.png")

    # Beeswarm plot
    # Shows: for each feature, how does its value affect fraud probability?
    # Red dots = high feature value, blue = low. Right side = pushes toward fraud.
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.title("SHAP Beeswarm — Feature Impact on Fraud Score")
    plt.tight_layout()
    plt.savefig("model/artifacts/shap_beeswarm.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: model/artifacts/shap_beeswarm.png")

    # Single prediction explanation — the "why did you flag this?" feature
    # Pick the first fraud case in the sample and explain it
    fraud_indices = np.where(y_test.iloc[sample_idx].values == 1)[0]
    if len(fraud_indices) > 0:
        idx = fraud_indices[0]
        print(f"\n  ── Example Fraud Explanation ──")
        print(f"  Transaction features:")
        for col, val in X_sample.iloc[idx].items():
            print(f"    {col:<30} {val:.4f}")

        top_features = np.argsort(np.abs(shap_values[idx]))[-5:][::-1]
        print(f"\n  Top 5 SHAP drivers (why this was flagged as fraud):")
        for feat_idx in top_features:
            feat_name  = X_sample.columns[feat_idx]
            feat_val   = X_sample.iloc[idx, feat_idx]
            shap_val   = shap_values[idx][feat_idx]
            direction  = "↑ toward fraud" if shap_val > 0 else "↓ away from fraud"
            print(f"    {feat_name:<30} value={feat_val:.2f}  SHAP={shap_val:+.3f}  {direction}")

    return auc_roc, auc_pr