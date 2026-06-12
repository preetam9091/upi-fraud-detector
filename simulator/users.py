import uuid
import random
import numpy as np
from faker import Faker
from simulator.config import SIMULATION_CONFIG

fake = Faker("en_IN")   # Indian locale — gives Indian names, addresses
random.seed(42)
np.random.seed(42)

def generate_users(num_users: int) -> list[dict]:
    """
    Generate realistic Indian UPI user profiles.
    Each user has consistent behavior that transactions will be drawn from.
    """
    users = []
    config = SIMULATION_CONFIG

    for _ in range(num_users):

        # Pick city tier by weight
        tier_name = random.choices(
            list(config["city_tiers"].keys()),
            weights=[t["weight"] for t in config["city_tiers"].values()]
        )[0]
        tier = config["city_tiers"][tier_name]
        city = random.choice(tier["cities"])

        # Monthly spend drawn from a log-normal distribution
        # Why log-normal? Because income in India is heavily right-skewed
        # (most people earn modest amounts, a few earn very high)
        avg_spend = tier["avg_monthly_spend"]
        monthly_spend = np.random.lognormal(
            mean=np.log(avg_spend),
            sigma=0.5
        )

        # Average transaction size for this user
        # Most transactions are well below monthly spend
        avg_txn = monthly_spend / random.randint(15, 40)

        # Devices — most Indians have 1 phone, some have 2
        num_devices = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
        devices = [f"device_{uuid.uuid4().hex[:8]}" for _ in range(num_devices)]

        # Primary device is always the first one
        primary_device = devices[0]

        # VPA (Virtual Payment Address) — like user@okicici
        banks = ["okicici", "oksbi", "okhdfc", "okhdfcbank", "ybl", "ibl", "axl"]
        vpa = f"{fake.first_name().lower()}{random.randint(10,999)}@{random.choice(banks)}"

        # Account age in days — older accounts are less risky
        account_age_days = random.randint(1, 1500)

        # How many transactions does this user make per month on average?
        monthly_txn_count = random.randint(8, 60)

        # Preferred transaction hours — each user has a personal pattern
        # (early bird vs night owl vs lunch-time spender)
        preferred_hours = random.choices(
            range(24),
            weights=config["hourly_weights"],
            k=5
        )

        users.append({
            "user_id":              str(uuid.uuid4()),
            "name":                 fake.name(),
            "vpa":                  vpa,
            "city":                 city,
            "city_tier":            tier_name,
            "state":                fake.state(),
            "account_age_days":     account_age_days,
            "monthly_spend":        round(monthly_spend, 2),
            "avg_txn_amount":       round(avg_txn, 2),
            "monthly_txn_count":    monthly_txn_count,
            "devices":              devices,
            "primary_device":       primary_device,
            "preferred_hours":      preferred_hours,
            "is_mule_account":      False,   # will be flipped later for mule fraud
        })

    return users