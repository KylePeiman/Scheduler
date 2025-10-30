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
            shift_start_time = shift.get('start_time', "00:00")
            shift_end_time = shift.get('end_time', "00:00")
        except Exception:
            continue
        if shift_date.month == month and shift_date.year == year:
            # Add start_time and end_time to each shift if not present (for backward compatibility)
            if 'start_time' not in shift or 'end_time' not in shift:
                # Example logic: assign based on shift_type
                shift_type = shift.get('shift_type', '').lower()
                if shift_type == 'day':
                    shift['start_time'] = '07:00'
                    shift['end_time'] = '15:00'
                elif shift_type == 'evening':
                    shift['start_time'] = '15:00'
                    shift['end_time'] = '23:00'
                elif shift_type == 'night':
                    shift['start_time'] = '23:00'
                    shift['end_time'] = '07:00'
                elif shift_type == 'call':
                    shift['start_time'] = '17:00'
                    shift['end_time'] = '07:00'
                else:
                    shift['start_time'] = '08:00'
                    shift['end_time'] = '16:00'
            if user:
                if 'provider' in shift and shift['provider'] in user:
                    result.setdefault(shift['date'], []).append(shift)
            else:
                result.setdefault(shift['date'], []).append(shift)
    return result
