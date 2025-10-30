from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from data_manager import DataManager
from datetime import datetime
from typing import Dict, List

app = FastAPI()

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_manager = DataManager()
data_manager.load_sample_data()

@app.get("/providers")
def get_providers():
    """Return all providers (for dropdown selection)."""
    return data_manager.providers

@app.get("/shifts")
def get_shifts(month: int, year: int, user: List[str] = Query(None)) -> Dict[str, List[dict]]:
    """
    Returns shifts for the given month and year, grouped by date (YYYY-MM-DD).
    If user(s) are specified, only shifts assigned to those providers are returned.
    """
    result = {}
    for shift in data_manager.shifts:
        try:
            shift_date = datetime.strptime(shift['date'], "%Y-%m-%d")
        except Exception:
            continue
        if shift_date.month == month and shift_date.year == year:
            if user:
                # Only include shifts with a 'provider' key matching one of the users
                if 'provider' in shift and shift['provider'] in user:
                    result.setdefault(shift['date'], []).append(shift)
            else:
                result.setdefault(shift['date'], []).append(shift)
    return result
