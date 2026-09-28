# FlowDesk Intelligence frontend

React + Vite + TypeScript frontend for the FlowDesk Product Feedback Intelligence Agent.

## Run locally

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`.

Start the backend separately:

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Live workflows

- Command center metrics and issue signals derived from feedback records
- Single feedback intake with automatic triage
- CSV batch ingestion
- Search, filter, pagination, and per-record re-analysis
- Hindsight memory overview and recall
- Product intelligence reflection with optional observation retention

The architecture document also describes product releases and before/after comparisons. Those backend routes are not present in the current API, so the frontend does not invent or display mock release data for them.
