import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from simulator.config import SIMULATION_CONFIG

random.seed(42)
np.random.seed(42)

START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime(2024, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

def _pick_hour(user: dict) -> int:
    """Pick a transaction hour biased toward this user's personal pattern."""
    config = SIMULATION_CONFIG
    # 70% chance: pick from user's preferred hours
    # 30% chance: pick randomly from global distribution (people are unpredictable)
    if random.random() < 0.70:
        return random.choice(user["preferred_hours"])
    else:
        return random.choices(range(24), weights=config["hourly_weights"])[0]

def _pick_amount(user: dict, category: str) -> float:
    """
    Pick a transaction amount for this category, personalised to this user's spending level.
    Why not just uniform random? Because real spending clusters around habits.
    """
    config = SIMULATION_CONFIG
    cat = config["merchant_categories"][category]

    # User's typical amount for this category, drawn from a log-normal
    # Log-normal = amounts cluster around a typical value but have a long tail
    amount = np.random.lognormal(
        mean=np.log(max(user["avg_txn_amount"], cat["min"])),
        sigma=0.4
    )

    # Clamp to category bounds
    amount = max(cat["min"], min(amount, cat["max"]))

    # 15% chance of a round number (people often type ₹500, ₹1000)
    if random.random() < 0.15:
        amount = round(amount / 100) * 100

    return round(amount, 2)

def generate_normal_transactions(users: list[dict], num_transactions: int) -> list[dict]:
    """
    Generate realistic normal (non-fraud) transactions.
    Each transaction is tied to a real user and follows their behavioral profile.
    """
    config = SIMULATION_CONFIG
    transactions = []

    # Build a lookup dict for fast user access
    user_lookup = {u["user_id"]: u for u in users}

    # Pre-compute user selection weights
    # Users with higher monthly_txn_count generate more transactions
    user_ids    = [u["user_id"] for u in users]
    user_weights = [u["monthly_txn_count"] for u in users]

    # Track known recipients per user (for "seen before" feature later)
    user_recipients: dict[str, list[str]] = {u["user_id"]: [] for u in users}

    # Generate a pool of recipient VPAs (people you send money to)
    all_vpas = [u["vpa"] for u in users]

    for _ in range(num_transactions):
        # Pick a user weighted by their activity level
        user_id = random.choices(user_ids, weights=user_weights)[0]
        user = user_lookup[user_id]

        # Pick a random day in 2024
        day_offset = random.randint(0, TOTAL_DAYS)
        txn_date = START_DATE + timedelta(days=day_offset)

        # Is it a festival day? If yes, much higher volume (already handled by
        # the num_transactions count, but we mark it for feature use)
        is_festival = txn_date.strftime("%Y-%m-%d") in config["festival_dates_2024"]

        # Pick hour with personal bias
        hour   = _pick_hour(user)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        timestamp = txn_date.replace(hour=hour, minute=minute, second=second)

        # Pick category by weight
        categories = list(config["merchant_categories"].keys())
        cat_weights = [config["merchant_categories"][c]["weight"] for c in categories]
        category = random.choices(categories, weights=cat_weights)[0]

        # Pick device — 90% primary device, 10% secondary
        if len(user["devices"]) > 1 and random.random() < 0.10:
            device_id = random.choice(user["devices"][1:])
        else:
            device_id = user["primary_device"]

        # Pick recipient
        # 70%: someone they've sent to before (habit)
        # 30%: new recipient
        if user_recipients[user_id] and random.random() < 0.70:
            recipient_vpa = random.choice(user_recipients[user_id])
            recipient_seen_before = True
        else:
            recipient_vpa = random.choice(all_vpas)
            user_recipients[user_id].append(recipient_vpa)
            recipient_seen_before = False

        amount = _pick_amount(user, category)

        transactions.append({
            "txn_id":                   str(uuid.uuid4()),
            "user_id":                  user_id,
            "timestamp":                timestamp.isoformat(),
            "amount":                   amount,
            "category":                 category,
            "device_id":                device_id,
            "city":                     user["city"],
            "recipient_vpa":            recipient_vpa,
            "recipient_seen_before":    recipient_seen_before,
            "is_festival_day":          is_festival,
            "is_fraud":                 False,
            "fraud_type":               None,
        })

    return transactions