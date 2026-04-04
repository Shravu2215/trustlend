from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import random

from ai_model import ModelUnavailableError, load_or_train_model, score_application, build_offer, build_signals

app = FastAPI(title="TrustLend API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

loans_db = []
users_db: Dict[str, Any] = {}


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else phone.strip()


def build_decision_reasons(form: Dict[str, Any], score: int, offer: Dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    income = float(form.get("monthly_income", 0))
    expenses = float(form.get("monthly_expenses", 0))
    amount = float(form.get("amount", 0))
    months = max(int(form.get("months", 1)), 1)
    employment_years = float(form.get("employment_years", 0))
    residence_years = float(form.get("residence_years", 0))
    credit_history = form.get("credit_history", "good")

    emi = amount / months if months else amount
    buffer_amount = income - expenses
    if score < 65:
        reasons.append(f"TrustScore {score} is below the approval threshold of 65.")
    if income > 0 and emi / income > 0.35:
        reasons.append("Monthly EMI is too high compared with monthly income.")
    if buffer_amount < emi:
        reasons.append("Income left after expenses is not enough to comfortably cover EMI.")
    if credit_history == "late":
        reasons.append("Credit history includes late-payment behaviour.")
    elif credit_history == "new":
        reasons.append("Borrower has limited credit history, so confidence is lower.")
    if employment_years < 1:
        reasons.append("Employment history is too short for a stronger approval signal.")
    if residence_years < 1:
        reasons.append("Residence stability is low compared with approved borrowers.")
    if amount > offer.get("max_amount", amount):
        reasons.append("Requested amount is higher than the ML-approved limit.")
    if not reasons:
        reasons.append("Borrower profile passed the ML approval checks.")
    return reasons

class TrustScoreRequest(BaseModel):
    phone: str
    age: int
    monthly_income: float
    monthly_expenses: float
    employment_years: float
    residence_years: float
    dependents: int
    housing: str
    credit_history: str
    amount: float
    months: int
    purpose: Optional[str] = "education"

class LoanRequest(BaseModel):
    phone: str
    amount: float
    months: Optional[int] = None
    tenure_months: Optional[int] = None
    txn_hash: Optional[str] = None

class FundRequest(BaseModel):
    lender_phone: str
    loan_id: str
    amount: float

@app.get("/")
def root():
    return {"message": "TrustLend API running"}


@app.on_event("startup")
def warm_model():
    try:
        load_or_train_model()
    except Exception as exc:
        print(f"TrustLend model startup warning: {exc}")

@app.post("/api/trust-score")
def get_trust_score(req: TrustScoreRequest):
    if len(req.phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    form = req.dict()
    try:
        score, prob = score_application(form)
        offer = build_offer(score, form)
        signals = build_signals(form)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if score >= 80:
        risk = "Low"
    elif score >= 65:
        risk = "Medium"
    else:
        risk = "High"

    normalized_phone = normalize_phone(req.phone)
    decision_status = "approved" if score >= 65 and offer.get("approved", False) else "rejected"
    decision_reasons = build_decision_reasons(form, score, offer)

    users_db[normalized_phone] = {
        "phone": normalized_phone,
        "trust_score": score,
        "risk": risk,
        "prob_good": prob,
        "loan_offer": offer,
        "signals": signals,
        "profile": form,
        "decision": {
            "status": decision_status,
            "reasons": decision_reasons,
            "evaluated_at": datetime.utcnow().isoformat(),
            "requested_amount": form.get("amount"),
            "months": form.get("months"),
        },
        "last_updated": datetime.utcnow().isoformat(),
    }

    return {
        "trust_score": score,
        "risk": risk,
        "loan_offer": offer,
        "signals": signals,
        "decision": {
            "status": decision_status,
            "reasons": decision_reasons,
        },
        "model_info": {
            "dataset": "OpenML credit-g (German Credit)",
            "model": "Logistic Regression",
            "source_url": "https://api.openml.org/d/31",
            "source_name": "OpenML credit-g",
            "instances": 1000,
            "features": 20,
            "target": "good / bad credit risk",
            "note": "Model trained on open credit dataset; inputs are mapped to closest matching features.",
        },
    }

@app.post("/api/loan/apply")
def apply_loan(req: LoanRequest):
    months = req.months or req.tenure_months or 3
    if months <= 0:
        raise HTTPException(status_code=400, detail="Invalid tenure")

    normalized_phone = normalize_phone(req.phone)
    score_snapshot = users_db.get(normalized_phone, {})
    trust_score = score_snapshot.get("trust_score", 0)
    loan_offer = score_snapshot.get("loan_offer", {})
    if not score_snapshot:
        raise HTTPException(status_code=400, detail="Run TrustScore analysis before applying for a loan")
    if trust_score < 65 or not loan_offer.get("approved", False):
        raise HTTPException(
            status_code=400,
            detail=f"Loan rejected by ML model. TrustScore {trust_score} is below approval threshold.",
        )
    interest_rate = score_snapshot.get("loan_offer", {}).get("interest_rate", 9.5)
    loan_id = str(uuid.uuid4())[:8].upper()
    loan = {
        "loan_id": loan_id,
        "borrower_phone": normalized_phone,
        "amount": req.amount,
        "tenure_months": months,
        "interest_rate": interest_rate,
        "trust_score": score_snapshot.get("trust_score", 0),
        "risk": score_snapshot.get("risk", "Pending"),
        "status": "approved",
        "txn_hash": req.txn_hash or f"0x{uuid.uuid4().hex}",
        "created_at": datetime.utcnow().isoformat(),
        "monthly_emi": round((req.amount * (1 + interest_rate / 100)) / months, 2),
        "decision_reasons": score_snapshot.get("decision", {}).get("reasons", []),
    }
    loans_db.append(loan)
    return {**loan, "polygon_url": f"https://mumbai.polygonscan.com/tx/{loan['txn_hash']}"}

@app.get("/api/loans/marketplace")
def marketplace():
    pending = [l for l in loans_db if l["status"] == "pending"]
    if not pending:
        pending = [
            {"loan_id":"A1B2C3","borrower_phone":"98765XXXXX","amount":8000,"tenure_months":3,"interest_rate":6.0,"trust_score":78,"risk":"Low","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=5)).isoformat(),"monthly_emi":2826.67},
            {"loan_id":"D4E5F6","borrower_phone":"91234XXXXX","amount":5000,"tenure_months":2,"interest_rate":9.5,"trust_score":64,"risk":"Medium","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=12)).isoformat(),"monthly_emi":2737.5},
            {"loan_id":"G7H8I9","borrower_phone":"87654XXXXX","amount":12000,"tenure_months":6,"interest_rate":6.0,"trust_score":85,"risk":"Low","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=2)).isoformat(),"monthly_emi":2120.0},
        ]
    enriched = []
    for l in pending:
        score = l.get("trust_score", random.randint(55, 88))
        risk = l.get("risk", "Medium")
        if score >= 85:
            tier = "Platinum"
        elif score >= 75:
            tier = "Gold"
        elif score >= 65:
            tier = "Silver"
        else:
            tier = "Bronze"

        if risk == "Low":
            default_prob = round(random.uniform(0.03, 0.08), 3)
            protection = 80
            repayment_rate = 97.5
        elif risk == "Medium":
            default_prob = round(random.uniform(0.10, 0.18), 3)
            protection = 60
            repayment_rate = 93.0
        else:
            default_prob = round(random.uniform(0.22, 0.35), 3)
            protection = 35
            repayment_rate = 86.0

        interest = float(l.get("interest_rate", 9.5))
        risk_adjusted = max(0.0, round(interest - (default_prob * 100 * 0.35), 2))

        enriched.append({
            **l,
            "trust_score": score,
            "risk": risk,
            "trust_tier": tier,
            "default_prob": default_prob,
            "protection_percent": protection,
            "repayment_rate": repayment_rate,
            "community_vouches": random.randint(2, 9),
            "risk_adjusted_apy": risk_adjusted,
            "ai_flags": [
                "Stable income pattern",
                "Low EMI-to-income ratio",
                "Consistent repayment behavior",
            ][: random.randint(2, 3)],
        })
    return {"loans": enriched}

@app.post("/api/lend/fund")
@app.post("/api/loans/fund")
def fund_loan(req: FundRequest):
    loan = next((l for l in loans_db if l["loan_id"] == req.loan_id), None)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    loan["status"] = "active"
    loan["lender_phone"] = req.lender_phone
    loan["funded_at"] = datetime.utcnow().isoformat()
    loan["fund_txn_hash"] = f"0x{uuid.uuid4().hex}"
    return {"message": "Loan funded successfully", "loan": loan}

@app.get("/api/stats")
def stats():
    return {
        "total_loans_given": 1847 + len(loans_db),
        "total_amount_disbursed": 14200000,
        "total_repaid": 13100000,
        "active_lenders": 342,
        "default_rate": 2.3,
        "avg_trust_score": 71,
        "loans_today": 47 + len(loans_db),
    }

@app.get("/api/dashboard/{phone}")
def dashboard(phone: str):
    normalized_phone = normalize_phone(phone)
    user = users_db.get(normalized_phone, {})
    user_loans = [l for l in loans_db if normalize_phone(l.get("borrower_phone", "")) == normalized_phone]
    decision = user.get("decision")
    if decision and decision.get("status") == "rejected":
        rejection_row = {
            "loan_id": "ML-REJECT",
            "borrower_phone": normalized_phone,
            "amount": decision.get("requested_amount", user.get("profile", {}).get("amount", 0)),
            "tenure_months": decision.get("months", user.get("profile", {}).get("months", 0)),
            "interest_rate": user.get("loan_offer", {}).get("interest_rate", 0),
            "trust_score": user.get("trust_score", 0),
            "risk": user.get("risk", "High"),
            "status": "rejected",
            "txn_hash": "-",
            "created_at": decision.get("evaluated_at", user.get("last_updated")),
            "monthly_emi": user.get("loan_offer", {}).get("emi", 0),
            "decision_reasons": decision.get("reasons", []),
        }
        if not any(loan.get("loan_id") == "ML-REJECT" for loan in user_loans):
            user_loans.append(rejection_row)
    return {
        "phone": normalized_phone,
        "trust_score": user.get("trust_score", 0),
        "score_data": user,
        "loans": user_loans,
        "badges": [
            {"name": "Early Adopter", "icon": "rocket", "earned": True},
            {"name": "Verified Identity", "icon": "check", "earned": True},
            {"name": "On-Time Repayer", "icon": "clock", "earned": len(user_loans) > 0},
            {"name": "Community Validator", "icon": "handshake", "earned": False},
        ],
        "vouches": 3,
        "ai_tip": "Paying expenses on time can improve your affordability score.",
    }
