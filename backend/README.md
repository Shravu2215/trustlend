# TrustLend Backend

## Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API runs at http://localhost:8000
Docs at http://localhost:8000/docs

## AI Model Notes
- Uses the OpenML credit-g (German Credit) dataset.
- On first request, the model is trained and cached to `backend/model.pkl`.
- If the OpenML download fails, check your internet connection and retry.
