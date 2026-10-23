"""
Train and compare risk models, then save the best one.

Steps:
  1. Load ml/data/shipments.csv (run ml.generate_data first)
  2. Split 80/20, stratified by risk level
  3. Train Logistic Regression, Random Forest and Gradient Boosting
  4. Compare them with 5-fold cross-validated macro F1 on the training set
  5. Evaluate the winner on the held-out test set
  6. Save the model (ml/model.joblib) and its metrics (ml/metrics.json)

Usage:
    python -m ml.train
"""
import json
import os

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.generate_data import RISK_LEVELS

ML_DIR = os.path.dirname(__file__)
NUMERIC = ["temperature", "humidity", "delay_hours"]
CATEGORICAL = ["product_type"]


def build_pipeline(classifier):
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("model", classifier)])


# MEDIUM is the smallest class, so class_weight="balanced" stops the models
# from ignoring it (raised MEDIUM recall from ~0.46 to ~0.69 for Random Forest).
CANDIDATES = {
    "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "random_forest": RandomForestClassifier(
        n_estimators=100, max_depth=10, min_samples_leaf=3, class_weight="balanced", random_state=42
    ),
    "gradient_boosting": GradientBoostingClassifier(random_state=42),
}


def main():
    df = pd.read_csv(os.path.join(ML_DIR, "data", "shipments.csv"))
    X, y = df[NUMERIC + CATEGORICAL], df["risk"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    cv_scores = {}
    for name, clf in CANDIDATES.items():
        scores = cross_val_score(build_pipeline(clf), X_train, y_train, cv=5, scoring="f1_macro")
        cv_scores[name] = round(float(scores.mean()), 4)
        print(f"{name:22s} CV macro F1 = {scores.mean():.4f} (+/- {scores.std():.4f})")

    best_name = max(cv_scores, key=cv_scores.get)
    best = build_pipeline(CANDIDATES[best_name]).fit(X_train, y_train)
    y_pred = best.predict(X_test)

    metrics = {
        "best_model": best_name,
        "cv_macro_f1": cv_scores,
        "test_accuracy": round(accuracy_score(y_test, y_pred), 4),
        "test_macro_f1": round(f1_score(y_test, y_pred, average="macro"), 4),
        "labels": RISK_LEVELS,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=RISK_LEVELS).tolist(),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
    }

    print(f"\nBest model: {best_name}")
    print(classification_report(y_test, y_pred, labels=RISK_LEVELS))
    print("Confusion matrix (rows = actual, cols = predicted):", RISK_LEVELS)
    for label, row in zip(RISK_LEVELS, metrics["confusion_matrix"]):
        print(f"  {label:6s} {row}")

    joblib.dump(best, os.path.join(ML_DIR, "model.joblib"))
    with open(os.path.join(ML_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print("\nSaved ml/model.joblib and ml/metrics.json")


if __name__ == "__main__":
    main()
