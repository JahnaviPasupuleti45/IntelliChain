"""
Generate a synthetic shipment dataset for training the risk model.

Real cold-chain sensor data is not publicly available, so we simulate it.
Each product type has its own safe ranges (pharma is much stricter than
general cargo). A hidden "spoilage score" grows as readings move outside
those ranges and as delays get longer. Random noise is added so the
classes overlap, like they would in real life, and the model has to learn
the pattern instead of memorising a single threshold.

Usage:
    python -m ml.generate_data            # writes ml/data/shipments.csv
"""
import os

import numpy as np
import pandas as pd

# Safe ranges per product type: (min temp, max temp, max humidity, delay tolerance in hours)
PRODUCT_PROFILES = {
    "pharma": (2.0, 8.0, 60.0, 2.0),
    "food": (0.0, 15.0, 85.0, 4.0),
    "electronics": (5.0, 35.0, 55.0, 12.0),
    "general": (0.0, 40.0, 90.0, 24.0),
}

RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]


def spoilage_score(product_type, temperature, humidity, delay_hours):
    """How far a reading is from the safe range for its product (0 = perfectly safe)."""
    t_min, t_max, h_max, delay_tol = PRODUCT_PROFILES[product_type]
    temp_excess = max(0.0, t_min - temperature) + max(0.0, temperature - t_max)
    humidity_excess = max(0.0, humidity - h_max)
    delay_excess = max(0.0, delay_hours - delay_tol)
    # Heat damage gets worse the longer the shipment is delayed
    return 0.45 * temp_excess + 0.08 * humidity_excess + 0.25 * delay_excess + 0.03 * temp_excess * delay_hours


def generate(n_rows=6000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n_rows):
        product = rng.choice(list(PRODUCT_PROFILES))
        t_min, t_max, h_max, delay_tol = PRODUCT_PROFILES[product]

        # Most shipments are fine; some drift out of range
        if rng.random() < 0.6:
            temperature = rng.uniform(t_min, t_max)
            humidity = rng.uniform(30, h_max)
            delay = rng.exponential(delay_tol / 2)
        else:
            temperature = rng.uniform(t_min - 6, t_max + 12)
            humidity = rng.uniform(30, 98)
            delay = rng.exponential(delay_tol * 1.5)

        score = spoilage_score(product, temperature, humidity, delay) + rng.normal(0, 0.6)
        risk = "LOW" if score < 1.0 else "MEDIUM" if score < 3.0 else "HIGH"

        rows.append({
            "product_type": product,
            "temperature": round(float(temperature), 1),
            "humidity": round(float(humidity), 1),
            "delay_hours": round(float(delay), 1),
            "risk": risk,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)
    df = generate()
    path = os.path.join(out_dir, "shipments.csv")
    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")
    print(df["risk"].value_counts().to_string())
