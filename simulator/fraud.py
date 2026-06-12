import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from simulator.config import SIMULATION_CONFIG

random.seed(99)

def inject_fraud(transactions: list[dict], users: list[dict]) -> list[dict]:
    """
    Inject fraud transactions into the dataset.

    IMPORTANT: fraud_counts represent TARGET TRANSACTION counts, not incident counts.
    This matches RBI's definition — each fraudulent transaction is counted individually.

    For multi-transaction fraud types (ATO, threshold gaming), we control
    the number of attacks so the resulting transaction count hits the target.
    """
    config = SIMULATION_CONFIG

    # Total fraud transactions we want — matching RBI's per-transaction definition
    target_fraud_txns = int(len(transactions) * config["fraud_rate"])

    # Transaction targets per fraud type
    txn_targets = {
        ft: int(target_fraud_txns * config["fraud_type_weights"][ft])
        for ft in config["fraud_type_weights"]
    }

    fraud_txns = []

    # ── Fraud Type 1: Account Takeover (ATO) ───────────────────────────────
    # Each attack spawns 2–5 transactions.
    # We keep generating attacks until we've produced exactly txn_targets["account_takeover"]
    # transactions — no more, no less.
    ato_generated = 0
    ato_target = txn_targets["account_takeover"]

    while ato_generated < ato_target:
        user = random.choice(users)
        attacker_device = f"device_{uuid.uuid4().hex[:8]}"
        hour = random.randint(1, 5)

        # How many transactions for this attack?
        # Cap at remaining budget so we never overshoot
        remaining = ato_target - ato_generated
        num_hits = min(random.randint(2, 5), remaining)

        base_time = datetime(
            2024, random.randint(1, 12), random.randint(1, 28),
            hour, random.randint(0, 59)
        )

        for i in range(num_hits):
            fraud_txns.append({
                "txn_id":                str(uuid.uuid4()),
                "user_id":               user["user_id"],
                "timestamp":             (base_time + timedelta(seconds=i * 45)).isoformat(),
                "amount":                round(random.uniform(45000, 49800), 2),
                "category":              "peer_transfer",
                "device_id":             attacker_device,      # ← new device: red flag
                "city":                  random.choice(["Mumbai", "Delhi", "Bengaluru"]),
                "recipient_vpa":         f"mule{uuid.uuid4().hex[:6]}@ybl",
                "recipient_seen_before": False,
                "is_festival_day":       False,
                "is_fraud":              True,
                "fraud_type":            "account_takeover",
            })
            ato_generated += 1

    # ── Fraud Type 2: Vishing ───────────────────────────────────────────────
    # 1 transaction per incident — loop count = transaction count directly
    for _ in range(txn_targets["vishing"]):
        user = random.choice(users)
        hour = random.choices(
            range(9, 20),
            weights=[5, 8, 10, 9, 8, 9, 10, 9, 8, 7, 6]
        )[0]
        amount = random.uniform(
            user["avg_txn_amount"] * 5,
            min(user["monthly_spend"] * 0.8, 100000)
        )
        fraud_txns.append({
            "txn_id":                str(uuid.uuid4()),
            "user_id":               user["user_id"],
            "timestamp":             datetime(
                                         2024, random.randint(1, 12),
                                         random.randint(1, 28),
                                         hour, random.randint(0, 59)
                                     ).isoformat(),
            "amount":                round(amount, 2),
            "category":              "peer_transfer",
            "device_id":             user["primary_device"],   # ← own device (victim did it)
            "city":                  user["city"],
            "recipient_vpa":         f"scam{uuid.uuid4().hex[:6]}@okicici",
            "recipient_seen_before": False,
            "is_festival_day":       False,
            "is_fraud":              True,
            "fraud_type":            "vishing",
        })

    # ── Fraud Type 3: Mule Chain ────────────────────────────────────────────
    # 1 transaction per incident
    mule_users = random.sample(users, min(50, len(users)))
    for u in mule_users:
        u["is_mule_account"] = True

    for _ in range(txn_targets["mule_chain"]):
        mule = random.choice(mule_users)
        inbound_amount = random.uniform(10000, 80000)
        txn_time = datetime(
            2024, random.randint(1, 12), random.randint(1, 28),
            random.randint(0, 23), random.randint(0, 59)
        )
        fraud_txns.append({
            "txn_id":                str(uuid.uuid4()),
            "user_id":               mule["user_id"],
            "timestamp":             (txn_time + timedelta(minutes=random.randint(2, 15))).isoformat(),
            "amount":                round(inbound_amount * random.uniform(0.85, 0.98), 2),
            "category":              "peer_transfer",
            "device_id":             mule["primary_device"],
            "city":                  mule["city"],
            "recipient_vpa":         f"exit{uuid.uuid4().hex[:6]}@oksbi",
            "recipient_seen_before": False,
            "is_festival_day":       False,
            "is_fraud":              True,
            "fraud_type":            "mule_chain",
        })

    # ── Fraud Type 4: New Account Fraud ────────────────────────────────────
    # 1 transaction per incident
    # Requires users with account_age_days < 30 — fixed in users.py
    young_users = [u for u in users if u["account_age_days"] < 30]
    for _ in range(txn_targets["new_account_fraud"]):
        if not young_users:
            break
        user = random.choice(young_users)
        fraud_txns.append({
            "txn_id":                str(uuid.uuid4()),
            "user_id":               user["user_id"],
            "timestamp":             datetime(
                                         2024, random.randint(1, 12),
                                         random.randint(1, 28),
                                         random.randint(9, 22),
                                         random.randint(0, 59)
                                     ).isoformat(),
            "amount":                round(random.uniform(20000, 90000), 2),
            "category":              "peer_transfer",
            "device_id":             f"device_{uuid.uuid4().hex[:8]}",  # new device
            "city":                  user["city"],
            "recipient_vpa":         f"fraud{uuid.uuid4().hex[:6]}@ybl",
            "recipient_seen_before": False,
            "is_festival_day":       False,
            "is_fraud":              True,
            "fraud_type":            "new_account_fraud",
        })

    # ── Fraud Type 5: Threshold Gaming ─────────────────────────────────────
    # Each scenario spawns 2–4 transactions.
    # Same "fill up to target" approach as ATO.
    tg_generated = 0
    tg_target = txn_targets["threshold_gaming"]

    while tg_generated < tg_target:
        user = random.choice(users)
        attacker_device = f"device_{uuid.uuid4().hex[:8]}"
        hour = random.randint(0, 5)
        base_time = datetime(
            2024, random.randint(1, 12), random.randint(1, 28), hour, 0
        )

        remaining = tg_target - tg_generated
        num_hits = min(random.randint(2, 4), remaining)

        for i in range(num_hits):
            fraud_txns.append({
                "txn_id":                str(uuid.uuid4()),
                "user_id":               user["user_id"],
                "timestamp":             (base_time + timedelta(seconds=i * 30)).isoformat(),
                "amount":                round(random.uniform(48000, 49900), 2),
                "category":              "peer_transfer",
                "device_id":             attacker_device,
                "city":                  "Mumbai",
                "recipient_vpa":         f"mule{uuid.uuid4().hex[:6]}@okhdfc",
                "recipient_seen_before": False,
                "is_festival_day":       False,
                "is_fraud":              True,
                "fraud_type":            "threshold_gaming",
            })
            tg_generated += 1

    # Merge + shuffle so fraud isn't bunched at the end
    all_transactions = transactions + fraud_txns
    random.shuffle(all_transactions)
    return all_transactions