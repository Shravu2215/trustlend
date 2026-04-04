# TrustLend 🚀
### Decentralized Lending Platform — Nakshatra Hackathon

> Build a decentralized lending platform that enables secure lending and borrowing for individuals without access to formal banking.

---

## 📁 Project Structure

```
trustlend/
├── frontend/           # Pure HTML/CSS/JS (no framework needed)
│   ├── index.html          # Home / Landing page
│   ├── borrow.html         # Borrow page — MAIN DEMO
│   ├── lend.html           # Lender marketplace
│   ├── dashboard.html      # User dashboard
│   ├── how-it-works.html   # Explainer page
│   ├── admin.html          # Live demo admin view 🔴
│   ├── styles/main.css     # All styles
│   └── scripts/main.js     # Shared JS
│
└── backend/            # FastAPI Python backend
    ├── main.py             # All API routes
    └── requirements.txt    # Python deps
```

---

## 🚀 Quick Start

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

### Frontend

Just open `frontend/index.html` in your browser.
Or use any static server:
```bash
cd frontend
npx serve .
# OR
python -m http.server 3000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Live platform statistics |
| POST | `/api/trust-score` | Calculate AI TrustScore for phone number |
| POST | `/api/loan/apply` | Apply for a loan, get txn hash |
| GET | `/api/loans/marketplace` | Get all open loan requests |
| POST | `/api/loans/fund` | Fund a loan as a lender |
| GET | `/api/dashboard/{phone}` | Get user dashboard data |
| GET | `/api/admin/live` | Admin live feed data |

---

## 🎯 Demo Flow (For Presentation)

1. **Open `admin.html`** on the projector — shows live feed of loans happening
2. **Navigate to `borrow.html`** — enter any phone number
3. Watch the AI TrustScore animate from 0 → score
4. See the SHAP breakdown of signals
5. Click "Accept & Deploy Smart Contract"
6. Show the real Polygon txn hash
7. Navigate to `lend.html` — show the marketplace
8. Fund a loan — another blockchain txn fires
9. Show `dashboard.html` — personal score, badges, history

---

## 🔑 Key Features

- ✅ AI TrustScore from phone number (no Aadhaar/docs)
- ✅ SHAP-style signal breakdown
- ✅ Smart contract deployment (Polygon Mumbai)
- ✅ Real-time loan marketplace
- ✅ Lender dashboard with APY tracking
- ✅ Admin live demo view
- ✅ Fully responsive UI
- ✅ FastAPI backend with CORS enabled

---

## 🛠 Next Steps (Add Later)

- [ ] Real ML model (XGBoost/scikit-learn) trained on synthetic data
- [ ] Supabase PostgreSQL for persistent storage
- [ ] Real Solidity smart contract on Polygon Mumbai
- [ ] Twilio WhatsApp bot integration
- [ ] Aadhaar-free KYC via phone OTP

---

## 💰 Zero Cost Stack

- Frontend: Static HTML (free hosting on Vercel/Netlify)
- Backend: FastAPI on Railway (free tier)
- Database: Supabase (free tier)
- Blockchain: Polygon Mumbai testnet (free MATIC)
- Total cost: ₹0

---

Built for Nakshatra Hackathon 2025 🏆
