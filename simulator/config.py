# All numbers are grounded in RBI 2024 data or NPCI reports
# This is your single source of truth — change numbers here, everything updates

SIMULATION_CONFIG = {

    # Scale
    "num_users": 10_000,
    "num_transactions": 500_000,

    # Fraud TRANSACTION rate — each fraudulent transaction counted individually
# Source: RBI Annual Report 2023-24 (matches RBI's per-transaction definition)
"fraud_rate": 0.003,

    # Fraud type distribution (must sum to 1.0)
    # Based on RBI's Annual Report 2023-24 fraud category breakdown
    "fraud_type_weights": {
        "account_takeover":   0.35,   # SIM swap / credential theft
        "vishing":            0.30,   # "I'm calling from your bank"
        "mule_chain":         0.15,   # money laundering through mule accounts
        "new_account_fraud":  0.12,   # fake KYC, instant loan default
        "threshold_gaming":   0.08,   # splitting to avoid ₹50k scrutiny
    },

    # Indian city tiers — affects transaction amounts and patterns
    "city_tiers": {
        "tier1": {
            "cities": ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata"],
            "weight": 0.45,
            "avg_monthly_spend": 25000,
        },
        "tier2": {
            "cities": ["Jaipur", "Lucknow", "Ahmedabad", "Surat", "Kochi", "Indore", "Nagpur"],
            "weight": 0.35,
            "avg_monthly_spend": 12000,
        },
        "tier3": {
            "cities": ["Jodhpur", "Varanasi", "Patna", "Bhopal", "Coimbatore", "Visakhapatnam"],
            "weight": 0.20,
            "avg_monthly_spend": 6000,
        },
    },

    # Transaction categories with typical amount ranges (in INR)
    "merchant_categories": {
        "food_delivery":    {"min": 100,   "max": 800,    "weight": 0.20},
        "groceries":        {"min": 200,   "max": 3000,   "weight": 0.18},
        "fuel":             {"min": 500,   "max": 3000,   "weight": 0.10},
        "utilities":        {"min": 300,   "max": 5000,   "weight": 0.08},
        "rent":             {"min": 5000,  "max": 50000,  "weight": 0.05},
        "peer_transfer":    {"min": 100,   "max": 20000,  "weight": 0.22},
        "shopping":         {"min": 300,   "max": 15000,  "weight": 0.10},
        "medical":          {"min": 200,   "max": 10000,  "weight": 0.04},
        "entertainment":    {"min": 100,   "max": 2000,   "weight": 0.03},
    },

    # Hour-of-day transaction probability weights (index 0 = midnight, 23 = 11pm)
    # Models real Indian UPI usage patterns
    "hourly_weights": [
        0.005, 0.003, 0.002, 0.002, 0.003, 0.008,   # midnight–5am (very low)
        0.020, 0.045, 0.065, 0.070, 0.065, 0.060,   # 6am–11am (morning ramp)
        0.070, 0.065, 0.060, 0.055, 0.058, 0.065,   # noon–5pm (afternoon)
        0.075, 0.072, 0.065, 0.050, 0.030, 0.012,   # 6pm–11pm (evening peak)
    ],

    # Festival multipliers — transaction volume spikes
    "festival_dates_2024": [
        "2024-10-31",  # Diwali eve (3x volume)
        "2024-11-01",  # Diwali (2.5x volume)
        "2024-03-25",  # Holi
        "2024-10-02",  # Gandhi Jayanti long weekend
    ],
    "festival_multiplier": 2.8,
}