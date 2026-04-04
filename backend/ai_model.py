from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple

import numpy as np
import pandas as pd
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
import joblib

BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
META_PATH = os.path.join(BASE_DIR, "model_meta.json")


@dataclass
class ModelBundle:
    model: Pipeline
    meta: Dict[str, Any]


def _compute_defaults(df: pd.DataFrame) -> Dict[str, Any]:
    defaults = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            defaults[col] = float(df[col].median())
        else:
            defaults[col] = df[col].mode(dropna=True)[0]
    return defaults


def _train_model() -> ModelBundle:
    data = fetch_openml(name="credit-g", version=1, as_frame=True)
    X = data.data.copy()
    y = (data.target == "good").astype(int)

    # Be robust to pandas categorical dtypes from OpenML
    num_cols = list(X.select_dtypes(include=["number", "bool"]).columns)
    cat_cols = [c for c in X.columns if c not in num_cols]

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ]
    )
    clf = LogisticRegression(max_iter=2000)
    model = Pipeline(steps=[("preprocess", pre), ("clf", clf)])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model.fit(X_train, y_train)

    defaults = _compute_defaults(X)
    meta = {
        "dataset": "OpenML credit-g (German Credit)",
        "columns": list(X.columns),
        "cat_cols": cat_cols,
        "num_cols": num_cols,
        "defaults": defaults,
    }

    joblib.dump(model, MODEL_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return ModelBundle(model=model, meta=meta)


def load_or_train_model() -> ModelBundle:
    if os.path.exists(MODEL_PATH) and os.path.exists(META_PATH):
        model = joblib.load(MODEL_PATH)
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return ModelBundle(model=model, meta=meta)
    return _train_model()


def _map_employment(years: float) -> str:
    if years <= 0.5:
        return "unemployed"
    if years <= 1:
        return "<1"
    if years <= 4:
        return "1<= <4"
    if years <= 7:
        return "4<= <7"
    return ">=7"


def _map_installment_rate(monthly_income: float, amount: float, months: int) -> int:
    if monthly_income <= 0 or months <= 0:
        return 4
    emi = amount / months
    ratio = emi / monthly_income
    if ratio <= 0.2:
        return 1
    if ratio <= 0.3:
        return 2
    if ratio <= 0.4:
        return 3
    return 4


def _map_residence(years: float) -> int:
    if years <= 1:
        return 1
    if years <= 2:
        return 2
    if years <= 3:
        return 3
    return 4


def _map_savings_status(monthly_savings: float) -> str:
    if monthly_savings <= 0:
        return "<100"
    if monthly_savings < 100:
        return "<100"
    if monthly_savings < 500:
        return "100<= <500"
    if monthly_savings < 1000:
        return "500<= <1000"
    return ">=1000"


def _map_checking_status(monthly_savings: float) -> str:
    if monthly_savings <= 0:
        return "<0"
    if monthly_savings < 200:
        return "0<= <200"
    return ">=200"


def _map_credit_history(tag: str) -> str:
    if tag == "late":
        return "critical/other existing credit"
    if tag == "new":
        return "no credits/all paid"
    return "existing paid"


def _map_purpose(tag: str) -> str:
    mapping = {
        "education": "education",
        "business": "business",
        "medical": "medical",
        "home": "domestic appliance",
    }
    return mapping.get(tag, "car (used)")


def _map_property(housing: str, monthly_savings: float) -> str:
    if housing == "own":
        return "real estate"
    if monthly_savings > 500:
        return "car"
    return "no known property"


def _map_job(employment_years: float) -> str:
    if employment_years <= 1:
        return "unskilled"
    return "skilled"


def build_feature_row(form: Dict[str, Any], meta: Dict[str, Any]) -> pd.DataFrame:
    defaults = meta["defaults"].copy()

    age = float(form.get("age", 28))
    monthly_income = float(form.get("monthly_income", 25000))
    monthly_expenses = float(form.get("monthly_expenses", 14000))
    employment_years = float(form.get("employment_years", 2))
    residence_years = float(form.get("residence_years", 2))
    dependents = int(form.get("dependents", 0))
    housing = form.get("housing", "rent")
    credit_history = form.get("credit_history", "good")
    amount = float(form.get("amount", 8000))
    months = int(form.get("months", 3))
    purpose = form.get("purpose", "education")

    monthly_savings = max(monthly_income - monthly_expenses, 0)

    overrides = {
        "duration": months,
        "credit_amount": amount,
        "age": age,
        "employment": _map_employment(employment_years),
        "installment_rate": _map_installment_rate(monthly_income, amount, months),
        "residence_since": _map_residence(residence_years),
        "num_dependents": 2 if dependents >= 2 else 1,
        "housing": housing,
        "checking_status": _map_checking_status(monthly_savings),
        "savings_status": _map_savings_status(monthly_savings),
        "credit_history": _map_credit_history(credit_history),
        "purpose": _map_purpose(purpose),
        "property_magnitude": _map_property(housing, monthly_savings),
        "existing_credits": 1,
        "job": _map_job(employment_years),
        "own_telephone": "yes",
        "foreign_worker": "yes",
        "other_parties": "none",
        "other_payment_plans": "none",
        "personal_status": "male single",
    }

    for k, v in overrides.items():
        if k in defaults:
            defaults[k] = v

    df = pd.DataFrame([defaults], columns=meta["columns"])
    return df


def score_application(form: Dict[str, Any]) -> Tuple[int, float]:
    bundle = load_or_train_model()
    X_row = build_feature_row(form, bundle.meta)
    prob_good = float(bundle.model.predict_proba(X_row)[0][1])
    score = int(round(35 + prob_good * 60))
    score = max(35, min(95, score))
    return score, prob_good


def build_signals(form: Dict[str, Any]) -> list[Dict[str, Any]]:
    income = float(form.get("monthly_income", 0))
    expenses = float(form.get("monthly_expenses", 0))
    employment = float(form.get("employment_years", 0))
    residence = float(form.get("residence_years", 0))
    history = form.get("credit_history", "good")
    amount = float(form.get("amount", 0))
    months = int(form.get("months", 3))

    savings = max(income - expenses, 0)
    emi = amount / max(months, 1)
    affordability = max(0, min(25, int(25 - (emi / max(income, 1)) * 50)))

    signals = [
        {"name": "Income vs Expenses", "points": min(22, int(savings / 1000)), "icon": "??"},
        {"name": "Employment Stability", "points": min(18, int(employment * 3)), "icon": "??"},
        {"name": "Residence Stability", "points": min(16, int(residence * 4)), "icon": "??"},
        {"name": "Credit History", "points": 18 if history == "good" else 8 if history == "new" else 4, "icon": "??"},
        {"name": "Affordability", "points": affordability, "icon": "??"},
        {"name": "Requested Amount", "points": 10 if amount <= 10000 else 6 if amount <= 20000 else 3, "icon": "??"},
    ]
    return signals


def build_offer(score: int, form: Dict[str, Any]) -> Dict[str, Any]:
    income = float(form.get("monthly_income", 25000))
    amount = float(form.get("amount", 8000))
    months = int(form.get("months", 3))

    if score >= 80:
        rate = 6.0
        max_amount = income * 0.8
    elif score >= 65:
        rate = 9.5
        max_amount = income * 0.5
    else:
        rate = 14.0
        max_amount = income * 0.25

    approved = min(amount, max_amount)
    monthly_emi = (approved * (1 + rate / 100)) / max(months, 1)

    return {
        "amount": round(approved, 2),
        "requested_amount": amount,
        "max_amount": round(max_amount, 2),
        "interest_rate": rate,
        "months": months,
        "emi": round(monthly_emi, 2),
        "approved": approved >= amount * 0.6,
    }
