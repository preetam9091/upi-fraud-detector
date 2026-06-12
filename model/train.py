import numpy as np
import joblib
import os
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE

def split_data(df, feature_cols: list[str]):
    """
    Split into train/test sets.

    WHY STRATIFY? Because fraud is only 0.3% of data. Without stratify=,
    you might randomly get a test set with almost no fraud cases — useless for evaluation.
    stratify= guarantees both sets have the same fraud ratio.
    """
    X = df[feature_cols].astype(float)
    y = df["is_fraud"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        random_state=42,
        stratify=y       # ← critical for imbalanced data
    )

    print(f"  Train size : {len(X_train):,} ({y_train.sum():,} fraud)")
    print(f"  Test size  : {len(X_test):,}  ({y_test.sum():,} fraud)")

    return X_train, X_test, y_train, y_test


def apply_smote(X_train, y_train):
    """
    SMOTE = Synthetic Minority Oversampling Technique.

    WHY? Your dataset has ~1,200 fraud cases and ~399,000 normal transactions.
    If you train on this as-is, the model just learns to predict 'not fraud' for
    everything and gets 99.7% accuracy — completely useless.

    SMOTE generates synthetic fraud examples by interpolating between real ones,
    balancing the classes so the model actually learns what fraud looks like.

    IMPORTANT: Apply SMOTE only to training data, NEVER to test data.
    Test data must stay real to give you honest evaluation numbers.
    """
    print("  [→] Applying SMOTE oversampling...")
    before = y_train.value_counts().to_dict()

    smote = SMOTE(
        sampling_strategy=0.1,  # make fraud = 10% of training data (not 50% — too aggressive)
        random_state=42,
        k_neighbors=5
    )
    X_res, y_res = smote.fit_resample(X_train, y_train)

    after = {0: (y_res == 0).sum(), 1: (y_res == 1).sum()}
    print(f"  Before SMOTE: {before}")
    print(f"  After SMOTE : {after}")

    return X_res, y_res


def train_xgboost(X_train, y_train):
    """
    Train XGBoost classifier.

    WHY XGBOOST AND NOT A NEURAL NETWORK?
    - Tabular data (rows and columns) → XGBoost wins almost every time
    - Interpretable: SHAP works perfectly with tree models
    - Fast to train, fast to serve (<5ms per prediction)
    - Industry standard for fraud detection (Stripe, PayPal, Razorpay all use it)
    - Doesn't need millions of samples to work well

    KEY PARAMETERS:
    - scale_pos_weight: extra boost for the minority class (fraud)
      Set to neg/pos ratio as a safety net alongside SMOTE
    - max_depth: how complex each decision tree can be
      Too high = overfitting, too low = underfitting. 6 is standard.
    - n_estimators: how many trees to build. More = better but slower.
    - learning_rate: how much each tree corrects the previous one.
      Lower = more robust but needs more trees.
    """
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale = round(neg / pos)

    print(f"  [→] Training XGBoost (scale_pos_weight={scale})...")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,           # use 80% of data per tree (reduces overfitting)
        colsample_bytree=0.8,    # use 80% of features per tree
        scale_pos_weight=scale,
        eval_metric="aucpr",     # AUC-PR is better than AUC-ROC for imbalanced data
        random_state=42,
        n_jobs=-1,               # use all CPU cores
        verbosity=0,
    )

    model.fit(X_train, y_train)
    return model


def save_model(model, feature_cols: list[str]):
    """Save model + feature list so the API can load it later in Phase 4."""
    os.makedirs("model/artifacts", exist_ok=True)
    joblib.dump(model, "model/artifacts/fraud_model.pkl")
    joblib.dump(feature_cols, "model/artifacts/feature_cols.pkl")
    print("  Saved: model/artifacts/fraud_model.pkl")
    print("  Saved: model/artifacts/feature_cols.pkl")