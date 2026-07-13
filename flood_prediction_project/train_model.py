"""
train_model.py
----------------
Trains and compares four classification models (Decision Tree, Random Forest,
KNN, XGBoost) on the flood prediction dataset, selects the best-performing
model based on test accuracy, and saves the model + scaler to disk for use
by the Flask web application.
"""

import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

RANDOM_STATE = 42

FEATURE_COLUMNS = [
    "Temp",
    "Humidity",
    "Cloud Cover",
    "ANNUAL",
    "Jan-Feb",
    "Mar-May",
    "Jun-Sep",
    "Oct-Dec",
    "avgjune",
    "sub",
]
TARGET_COLUMN = "flood"


def load_data(path="data/flood_dataset.xlsx"):
    df = pd.read_excel(path)
    # Basic integrity checks
    missing_cols = set(FEATURE_COLUMNS + [TARGET_COLUMN]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset is missing expected columns: {missing_cols}")
    if df.isnull().sum().sum() > 0:
        df = df.dropna().reset_index(drop=True)
    return df


def main():
    print("=" * 60)
    print("FLOOD PREDICTION - MODEL TRAINING")
    print("=" * 60)

    df = load_data()
    print(f"\nDataset shape: {df.shape}")
    print(f"Class distribution:\n{df[TARGET_COLUMN].value_counts()}")

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    # Stratified split preserves the flood/no-flood ratio in both sets,
    # which matters given the class imbalance (~14% flood events).
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\nTrain size: {X_train.shape[0]}  |  Test size: {X_test.shape[0]}")

    # Scale features - required for KNN, harmless for tree-based models
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "Decision Tree": DecisionTreeClassifier(random_state=RANDOM_STATE, max_depth=5),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, random_state=RANDOM_STATE, max_depth=6
        ),
        "KNN": KNeighborsClassifier(n_neighbors=5),
        "XGBoost": XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            eval_metric="logloss",
            use_label_encoder=False,
        ),
    }

    results = {}
    print("\n" + "-" * 60)
    print("MODEL COMPARISON")
    print("-" * 60)

    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, zero_division=0)

        results[name] = {
            "model": model,
            "accuracy": acc,
            "f1_score": f1,
        }

        print(f"\n{name}")
        print(f"  Accuracy : {acc * 100:.2f}%")
        print(f"  F1 Score : {f1:.4f}")
        print(f"  Confusion Matrix:\n{confusion_matrix(y_test, preds)}")

    # Select best model by accuracy (tie-broken by F1 score)
    best_name = max(results, key=lambda k: (results[k]["accuracy"], results[k]["f1_score"]))
    best_model = results[best_name]["model"]
    best_acc = results[best_name]["accuracy"]

    print("\n" + "=" * 60)
    print(f"BEST MODEL: {best_name}  |  Accuracy: {best_acc * 100:.2f}%")
    print("=" * 60)
    print("\nClassification Report (best model):")
    print(
        classification_report(
            y_test, best_model.predict(X_test_scaled), zero_division=0
        )
    )

    # Persist model + scaler + metadata for the Flask app
    joblib.dump(best_model, "model/model.pkl")
    joblib.dump(scaler, "model/scaler.pkl")

    metadata = {
        "best_model": best_name,
        "accuracy": round(best_acc * 100, 2),
        "feature_columns": FEATURE_COLUMNS,
        "all_results": {
            name: {
                "accuracy": round(r["accuracy"] * 100, 2),
                "f1_score": round(r["f1_score"], 4),
            }
            for name, r in results.items()
        },
    }
    with open("model/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("\nSaved: model/model.pkl, model/scaler.pkl, model/metadata.json")


if __name__ == "__main__":
    main()
