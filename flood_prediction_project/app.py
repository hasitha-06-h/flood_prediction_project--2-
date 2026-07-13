"""
app.py
------
Flask web application for the Rising Waters flood prediction system.

Routes:
    /            Home dashboard
    /predict     Input form (GET) + prediction handling (POST)
    /history     Table of past predictions (stored in SQLite)
"""

import json
import os
import sqlite3
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "model", "scaler.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "model", "metadata.json")
DB_PATH = os.path.join(BASE_DIR, "history.db")

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

app = Flask(__name__)
app.config["SECRET_KEY"] = "flood-prediction-secret-key"

# ----------------------------------------------------------------------
# Model / metadata loading
# ----------------------------------------------------------------------
_model = None
_scaler = None
_metadata = {}


def load_artifacts():
    """Load the trained model and scaler once at startup."""
    global _model, _scaler, _metadata

    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(
            "Model or scaler not found. Run `python train_model.py` first "
            "to generate model/model.pkl and model/scaler.pkl."
        )

    _model = joblib.load(MODEL_PATH)
    _scaler = joblib.load(SCALER_PATH)

    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH) as f:
            _metadata = json.load(f)
    else:
        _metadata = {"best_model": "Unknown", "accuracy": None}


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temp REAL, humidity REAL, cloud_cover REAL,
            annual REAL, jan_feb REAL, mar_may REAL,
            jun_sep REAL, oct_dec REAL, avgjune REAL, sub REAL,
            prediction INTEGER,
            probability REAL
        )
        """
    )
    conn.commit()
    conn.close()


def save_prediction(values, prediction, probability):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO predictions
            (timestamp, temp, humidity, cloud_cover, annual, jan_feb,
             mar_may, jun_sep, oct_dec, avgjune, sub, prediction, probability)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            *values,
            int(prediction),
            float(probability),
        ),
    )
    conn.commit()


def fetch_history(limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return rows


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html", metadata=_metadata)


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "GET":
        return render_template("form.html", errors=None, form_data={})

    # POST: validate and predict
    errors = {}
    form_data = {}
    values = []

    field_specs = [
        ("temp", "Temperature", -10, 60),
        ("humidity", "Humidity", 0, 100),
        ("cloud_cover", "Cloud Cover", 0, 100),
        ("annual", "Annual Rainfall", 0, 20000),
        ("jan_feb", "Jan-Feb Rainfall", 0, 5000),
        ("mar_may", "Mar-May Rainfall", 0, 5000),
        ("jun_sep", "Jun-Sep Rainfall", 0, 10000),
        ("oct_dec", "Oct-Dec Rainfall", 0, 5000),
        ("avgjune", "Average June Rainfall", 0, 3000),
        ("sub", "Sub (Seasonal Aggregate)", 0, 5000),
    ]

    for field, label, lo, hi in field_specs:
        raw = request.form.get(field, "").strip()
        form_data[field] = raw
        if raw == "":
            errors[field] = f"{label} is required."
            continue
        try:
            val = float(raw)
        except ValueError:
            errors[field] = f"{label} must be a number."
            continue
        if not (lo <= val <= hi):
            errors[field] = f"{label} should be between {lo} and {hi}."
            continue
        values.append(val)

    if errors:
        return render_template("form.html", errors=errors, form_data=form_data)

    X = pd.DataFrame([values], columns=FEATURE_COLUMNS)
    X_scaled = _scaler.transform(X)
    prediction = int(_model.predict(X_scaled)[0])

    if hasattr(_model, "predict_proba"):
        probability = float(_model.predict_proba(X_scaled)[0][1])
    else:
        probability = float(prediction)

    save_prediction(values, prediction, probability)

    return render_template(
        "result.html",
        prediction=prediction,
        probability=round(probability * 100, 2),
        form_data=form_data,
        metadata=_metadata,
    )


@app.route("/history")
def history():
    rows = fetch_history()
    return render_template("history.html", rows=rows)


@app.route("/history/clear", methods=["POST"])
def clear_history():
    conn = get_db()
    conn.execute("DELETE FROM predictions")
    conn.commit()
    return redirect(url_for("history"))


# ----------------------------------------------------------------------
if __name__ == "__main__":
    load_artifacts()
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, host="0.0.0.0", port=port)
else:
    # Also initialize when imported (e.g. by a WSGI server)
    load_artifacts()
    init_db()
