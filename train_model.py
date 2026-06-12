import time
from features.engineer import load_data, engineer_features, get_feature_columns
from model.train import split_data, apply_smote, train_xgboost, save_model
from model.evaluate import evaluate

def main():
    print("=" * 55)
    print("  UPI Fraud Detector — Phase 2: Model Training")
    print("=" * 55)

    # Step 1: Load + engineer features
    print("\n[1/4] Loading data and engineering features...")
    t0 = time.time()
    txns, users = load_data()
    df = engineer_features(txns, users)
    feature_cols = get_feature_columns()
    print(f"      Done in {time.time()-t0:.1f}s")
    print(f"      Dataset shape : {df.shape}")
    print(f"      Features used : {len(feature_cols)}")
    print(f"      Fraud cases   : {df['is_fraud'].sum():,} ({df['is_fraud'].mean()*100:.2f}%)")

    # Step 2: Train/test split
    print("\n[2/4] Splitting data...")
    X_train, X_test, y_train, y_test = split_data(df, feature_cols)

    # Step 3: SMOTE + train
    print("\n[3/4] Training model...")
    X_res, y_res = apply_smote(X_train, y_train)
    model = train_xgboost(X_res, y_res)
    save_model(model, feature_cols)

    # Step 4: Evaluate
    print("\n[4/4] Evaluating model...")
    auc_roc, auc_pr = evaluate(model, X_test, y_test)

    print("\n" + "=" * 55)
    if auc_roc > 0.95:
        print(f"  ✓ Model looks great! AUC-ROC: {auc_roc:.4f}")
    else:
        print(f"  ⚠ AUC-ROC is {auc_roc:.4f} — below target. Check features.")
    print("  Charts saved to model/artifacts/")
    print("  Ready for Phase 3: Kafka streaming pipeline")
    print("=" * 55)

if __name__ == "__main__":
    main()