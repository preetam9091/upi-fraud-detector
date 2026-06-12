import pandas as pd
import numpy as np


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load raw CSVs generated in Phase 1."""
    txns  = pd.read_csv("data/transactions.csv", parse_dates=["timestamp"])
    users = pd.read_csv("data/users.csv")
    return txns, users


def engineer_features(txns: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw transactions into ML-ready features.

    Four categories:
    1. Time features     — when did this happen?
    2. Amount features   — how unusual is this amount?
    3. Behavioral        — how does this compare to this user's history?
    4. Network           — who is sending to whom?
    """

    print("  [→] Merging user profiles...")
    user_cols = ["user_id", "account_age_days", "avg_txn_amount",
                 "city_tier", "primary_device", "monthly_spend"]
    df = txns.merge(users[user_cols], on="user_id", how="left")

    # ── 1. TIME FEATURES ───────────────────────────────────────────────────
    print("  [→] Engineering time features...")

    df["hour"]        = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek   # 0=Monday, 6=Sunday

    # Odd hour: between midnight and 5am — when attackers operate
    df["is_odd_hour"] = df["hour"].between(0, 5).astype(int)
    df["is_weekend"]  = df["day_of_week"].isin([5, 6]).astype(int)

    # ── 2. AMOUNT FEATURES ─────────────────────────────────────────────────
    print("  [→] Engineering amount features...")

    # Log transform reduces extreme skewness of transaction amounts
    df["amount_log"] = np.log1p(df["amount"])

    # Round number flag: attackers type ₹50,000; real users type ₹47,382
    df["is_round_number"] = (df["amount"] % 100 == 0).astype(int)

    # Threshold gaming: amounts just below ₹50,000 scrutiny threshold
    df["amount_just_below_50k"] = df["amount"].between(45000, 49999).astype(int)

    # How does this amount compare to what this user normally spends?
    df["amount_vs_user_avg"] = df["amount"] / (df["avg_txn_amount"] + 1e-8)

    # ── 3. BEHAVIORAL FEATURES (rolling, no data leakage) ──────────────────
    # Sort by user + time, then use .shift(1) so we never use the current
    # transaction to compute its own features (that would be data leakage)
    print("  [→] Engineering behavioral features (this takes ~30s)...")

    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

    # Rolling mean and std of amount over last 30 transactions per user
    # shift(1) = look at previous transactions only, not current one
    df["rolling_mean"] = (
        df.groupby("user_id")["amount"]
        .transform(lambda x: x.shift(1).rolling(30, min_periods=1).mean())
    )
    df["rolling_std"] = (
        df.groupby("user_id")["amount"]
        .transform(lambda x: x.shift(1).rolling(30, min_periods=1).std().fillna(1))
    )

    # Fill NaN from rolling — first transaction per user has no history
    # Use the user's known average as the best available estimate
    df["rolling_mean"] = df["rolling_mean"].fillna(df["avg_txn_amount"])
    df["rolling_std"]  = df["rolling_std"].fillna(df["avg_txn_amount"] * 0.3)

    # Z-score: how many standard deviations is this amount from normal?
    # Z-score of 5+ = extremely unusual for this user
    df["amount_zscore"] = (
        (df["amount"] - df["rolling_mean"]) / (df["rolling_std"] + 1e-8)
    ).clip(-10, 10)

    # Fill NaN z-scores — no history means assume normal (z-score = 0)
    df["amount_zscore"] = df["amount_zscore"].fillna(0)

    # Cumulative transaction count per user (velocity proxy)
    df["user_txn_rank"] = df.groupby("user_id").cumcount()

    # Days since last transaction for this user
    # User silent for months then sending ₹50,000 = red flag
    df["prev_timestamp"] = df.groupby("user_id")["timestamp"].shift(1)
    df["days_since_last_txn"] = (
        (df["timestamp"] - df["prev_timestamp"])
        .dt.total_seconds() / 86400
    ).fillna(999)   # 999 = first ever transaction (no prior history)

    # Is the device different from the user's registered primary device?
    df["is_new_device"] = (df["device_id"] != df["primary_device"]).astype(int)

    # City tier as a number (tier1=0, tier2=1, tier3=2)
    tier_map = {"tier1": 0, "tier2": 1, "tier3": 2}
    df["city_tier_encoded"] = df["city_tier"].map(tier_map).fillna(1)

    # ── 4. NETWORK FEATURES ────────────────────────────────────────────────
    # NOTE: In production these come from real-time Redis counters.
    # Here we compute globally — a valid offline approximation for training.
    print("  [→] Engineering network features...")

    # Fan-in: how many unique senders has this recipient received from?
    # Mule accounts have HIGH fan-in (many victims → one account)
    recipient_fan_in = df.groupby("recipient_vpa")["user_id"].nunique()
    df["recipient_fan_in"] = df["recipient_vpa"].map(recipient_fan_in)

    # Fan-out: how many unique recipients has this sender sent to?
    # Attackers doing rapid multi-transfers have HIGH fan-out
    sender_fan_out = df.groupby("user_id")["recipient_vpa"].nunique()
    df["sender_fan_out"] = df["user_id"].map(sender_fan_out)

    # ── CLEANUP ────────────────────────────────────────────────────────────
    # Drop helper columns not needed by the model
    df = df.drop(columns=["prev_timestamp", "rolling_mean", "rolling_std",
                           "primary_device", "city_tier"])

    # Safety net: fill any remaining NaN in feature columns with 0
    feature_cols = get_feature_columns()
    df[feature_cols] = df[feature_cols].fillna(0)

    return df


def get_feature_columns() -> list[str]:
    """
    The exact list of features the model trains on.
    Keeping this as a function means train and serve code always use the same features.
    """
    return [
        # Time
        "hour", "day_of_week", "is_odd_hour", "is_weekend",
        # Amount
        "amount_log", "is_round_number", "amount_just_below_50k",
        "amount_vs_user_avg", "amount_zscore",
        # Behavioral
        "account_age_days", "user_txn_rank", "days_since_last_txn",
        "is_new_device", "city_tier_encoded",
        # Existing flags from Phase 1
        "recipient_seen_before", "is_festival_day",
        # Network
        "recipient_fan_in", "sender_fan_out",
    ]