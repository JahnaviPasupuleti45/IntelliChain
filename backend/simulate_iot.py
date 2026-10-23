"""
Simulates IoT sensors on several shipments sending readings to the backend.

Usage:
    python simulate_iot.py                 # 5 rounds of readings, 1 second apart
    python simulate_iot.py --rounds 10
"""
import argparse
import os
import random
import time

import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:5000")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "dev-device-key")

# shipment id, product, route, and how its conditions drift over time
SHIPMENTS = [
    # Healthy shipments
    ("SHP1", "pharma", "Hyderabad", {"temperature": (5, 0.3), "humidity": (50, 1), "delay_hours": (0.5, 0.2)}),
    ("SHP4", "food", "Rajahmundry", {"temperature": (6, 0.2), "humidity": (70, 1), "delay_hours": (1, 0.2)}),
    ("SHP6", "general", "Guntur", {"temperature": (30, 0.5), "humidity": (65, 1), "delay_hours": (4, 1)}),
    # Problem shipments: refrigeration failing, delays building up, humidity rising
    ("SHP2", "pharma", "Vijayawada", {"temperature": (9, 3), "humidity": (58, 2), "delay_hours": (2, 1.5)}),
    ("SHP3", "food", "Kakinada", {"temperature": (14, 3), "humidity": (84, 2), "delay_hours": (3, 2)}),
    ("SHP5", "electronics", "Visakhapatnam", {"temperature": (28, 0.5), "humidity": (60, 6), "delay_hours": (6, 4)}),
]


def main(rounds, interval):
    state = {sid: {k: v[0] for k, v in drift.items()} for sid, _, _, drift in SHIPMENTS}
    for round_no in range(1, rounds + 1):
        print(f"--- Round {round_no} ---")
        for shipment_id, product, location, drift in SHIPMENTS:
            values = state[shipment_id]
            for key, (_, step) in drift.items():
                # Conditions drift: mostly up for problem shipments, with some noise
                values[key] = max(0.0, values[key] + random.uniform(-step / 2, step))
            payload = {
                "shipment_id": shipment_id,
                "product_type": product,
                "location": location,
                **{k: round(v, 1) for k, v in values.items()},
            }
            response = requests.post(
                f"{API_URL}/api/sensor", json=payload, headers={"X-API-Key": DEVICE_API_KEY}, timeout=60
            )
            body = response.json()
            if response.ok:
                print(f"{shipment_id:5s} {product:12s} temp={payload['temperature']:5.1f} "
                      f"hum={payload['humidity']:5.1f} delay={payload['delay_hours']:4.1f}h "
                      f"-> {body['risk']:6s} ({body['risk_probability']:.0%})")
            else:
                print(f"{shipment_id}: error {response.status_code} {body}")
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    main(args.rounds, args.interval)
