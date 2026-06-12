import os
import time
import pandas as pd
from tqdm import tqdm
from simulator.config import SIMULATION_CONFIG
from simulator.users import generate_users
from simulator.transactions import generate_normal_transactions
from simulator.fraud import inject_fraud

def main():
    config = SIMULATION_CONFIG
    print("=" * 50)
    print("  UPI Fraud Detector — Data Simulator")
    print("=" * 50)

    # Step 1: Generate users
    print(f"\n[1/4] Generating {config['num_users']:,} user profiles...")
    t0 = time.time()
    users = generate_users(config["num_users"])
    print(f"      Done in {time.time()-t0:.1f}s")

    # Step 2: Generate normal transactions
    print(f"\n[2/4] Generating {config['num_transactions']:,} normal transactions...")
    t0 = time.time()
    transactions = generate_normal_transactions(users, config["num_transactions"])
    print(f"      Done in {time.time()-t0:.1f}s")

    # Step 3: Inject fraud
    print(f"\n[3/4] Injecting fraud scenarios...")
    t0 = time.time()
    all_txns = inject_fraud(transactions, users)
    t1 = time.time()

    # Stats
    fraud_count  = sum(1 for t in all_txns if t["is_fraud"])
    total_count  = len(all_txns)
    actual_rate  = fraud_count / total_count * 100
    print(f"      Done in {t1-t0:.1f}s")
    print(f"      Total transactions : {total_count:,}")
    print(f"      Fraud transactions  : {fraud_count:,} ({actual_rate:.2f}%)")

    # Fraud type breakdown
    df = pd.DataFrame(all_txns)
    fraud_df = df[df["is_fraud"] == True]
    print(f"\n      Fraud breakdown:")
    for ft, count in fraud_df["fraud_type"].value_counts().items():
        print(f"        {ft:<25} {count:>5} ({count/fraud_count*100:.1f}%)")

    # Step 4: Save
    print(f"\n[4/4] Saving to CSV...")
    os.makedirs("data", exist_ok=True)

    # Transactions CSV
    txn_path = "data/transactions.csv"
    df.to_csv(txn_path, index=False)
    size_mb = os.path.getsize(txn_path) / 1_000_000
    print(f"      Saved: {txn_path} ({size_mb:.1f} MB)")

    # Users CSV
    users_path = "data/users.csv"
    pd.DataFrame(users).to_csv(users_path, index=False)
    print(f"      Saved: {users_path}")

    print(f"\n✓ Phase 1 complete. Your dataset is ready.")
    print(f"  Run:  python -c \"import pandas as pd; print(pd.read_csv('data/transactions.csv').head())\"")
    print("=" * 50)

if __name__ == "__main__":
    main()