"""Loads the trained risk model and scores shipment readings."""
import os

import joblib
import pandas as pd

from ml.generate_data import PRODUCT_PROFILES

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "model.joblib")
PRODUCT_TYPES = list(PRODUCT_PROFILES)

_model = None


def _train_model():
    """Generate the dataset and train the model (first run only, takes a few seconds)."""
    from ml import generate_data, train

    data_dir = os.path.join(os.path.dirname(MODEL_PATH), "data")
    os.makedirs(data_dir, exist_ok=True)
    generate_data.generate().to_csv(os.path.join(data_dir, "shipments.csv"), index=False)
    train.main()


def get_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            _train_model()
        _model = joblib.load(MODEL_PATH)
    return _model


def describe_issues(product_type, temperature, humidity, delay_hours):
    """Words describing which safe limits a reading breaks, used to search the SOPs.

    The phrases match how SOP sections name their actions (e.g. "excursion response").
    """
    t_min, t_max, h_max, delay_tol = PRODUCT_PROFILES[product_type]
    issues = []
    if temperature > t_max:
        issues.append("temperature excursion response")
    if temperature < t_min:
        issues.append("freezing temperature excursion response")
    if humidity > h_max:
        issues.append("humidity response")
    if delay_hours > delay_tol:
        issues.append("delay handling")
    return issues


def sop_search_query(product_type, risk, temperature, humidity, delay_hours):
    """Search text for finding the SOP sections that apply to one reading."""
    issues = describe_issues(product_type, temperature, humidity, delay_hours)
    return f"{product_type} {risk} risk {' '.join(issues)}"


def predict_risk(product_type, temperature, humidity, delay_hours):
    """Return (risk level, probability of that level) for one reading."""
    model = get_model()
    features = pd.DataFrame([{
        "temperature": temperature,
        "humidity": humidity,
        "delay_hours": delay_hours,
        "product_type": product_type,
    }])
    probabilities = model.predict_proba(features)[0]
    best = probabilities.argmax()
    return str(model.classes_[best]), round(float(probabilities[best]), 3)
