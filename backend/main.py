from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timedelta

from ai_model import score_application, build_offer, build_signals

app = FastAPI(title="TrustLend API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

loans_db = []
users_db: Dict[str, Any] = {}

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

@app.post("/api/trust-score")
def get_trust_score(req: TrustScoreRequest):
    if len(req.phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    form = req.dict()
    score, prob = score_application(form)
    offer = build_offer(score, form)
    signals = build_signals(form)

    if score >= 80:
        risk = "Low"
    elif score >= 65:
        risk = "Medium"
    else:
        risk = "High"

    users_db[req.phone] = {
        "trust_score": score,
        "risk": risk,
        "prob_good": prob,
        "last_updated": datetime.utcnow().isoformat(),
    }

    return {
        "trust_score": score,
        "risk": risk,
        "loan_offer": offer,
        "signals": signals,
        "model_info": {
            "dataset": "OpenML credit-g (German Credit)",
            "note": "Model trained on open credit dataset; inputs are mapped to closest matching features.",
        },
    }

@app.post("/api/loan/apply")
def apply_loan(req: LoanRequest):
    months = req.months or req.tenure_months or 3
    if months <= 0:
        raise HTTPException(status_code=400, detail="Invalid tenure")

    loan_id = str(uuid.uuid4())[:8].upper()
    loan = {
        "loan_id": loan_id,
        "borrower_phone": req.phone,
        "amount": req.amount,
        "tenure_months": months,
        "status": "pending",
        "txn_hash": req.txn_hash or "",
        "created_at": datetime.utcnow().isoformat(),
    }
    loans_db.append(loan)
    return loan

@app.get("/api/loans/marketplace")
def marketplace():
    pending = [l for l in loans_db if l["status"] == "pending"]
    if not pending:
        pending = [
            {"loan_id":"A1B2C3","borrower_phone":"98765XXXXX","amount":8000,"tenure_months":3,"interest_rate":6.0,"trust_score":78,"risk":"Low","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=5)).isoformat(),"monthly_emi":2826.67},
            {"loan_id":"D4E5F6","borrower_phone":"91234XXXXX","amount":5000,"tenure_months":2,"interest_rate":9.5,"trust_score":64,"risk":"Medium","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=12)).isoformat(),"monthly_emi":2737.5},
            {"loan_id":"G7H8I9","borrower_phone":"87654XXXXX","amount":12000,"tenure_months":6,"interest_rate":6.0,"trust_score":85,"risk":"Low","status":"pending","txn_hash":f"0x{uuid.uuid4().hex}","created_at":(datetime.utcnow()-timedelta(minutes=2)).isoformat(),"monthly_emi":2120.0},
        ]
    return pending

@app.post("/api/lend/fund")
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
    user = users_db.get(phone)
    user_loans = [l for l in loans_db if l.get("borrower_phone") == phone]
    return {
        "phone": phone,
        "trust_score": user or {},
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
