# Scheduler App - Project Overview

This project is a scheduling platform that allows users to view provider shift calendars via a web interface. It uses a Python FastAPI backend and a static HTML/JS frontend.

## File Interactions

- **data_manager.py**: Contains the `DataManager` class, which manages provider and shift data. It can generate sample data and assigns providers to shifts for demo purposes.
- **api.py**: FastAPI backend that exposes two endpoints:
  - `/providers`: Returns a list of all providers for the frontend dropdown.
  - `/shifts`: Returns shifts for a given month/year, filtered by selected provider(s) if specified. Uses `DataManager` to access and filter shift data.
- **docs/index.html**: The static frontend. Fetches providers and shifts from the FastAPI backend and displays them in an Outlook-style calendar. Users can select one or more providers to view their shifts.

## How it Works

1. **Backend Startup**: When you run `uvicorn api:app --reload`, FastAPI loads sample data using `DataManager` and assigns providers to shifts.
2. **Frontend Usage**: Open `docs/index.html` in your browser. The page fetches providers and displays a calendar. When you select providers, it fetches and displays only their assigned shifts.
3. **API Filtering**: The `/shifts` endpoint only returns shifts assigned to the selected provider(s). If no provider is selected, all shifts are shown.

## Running Locally

1. Install dependencies:
   ```
   pip install fastapi uvicorn
   ```
2. Start the backend:
   ```
   uvicorn api:app --reload
   ```
3. Open `docs/index.html` in your browser. (You may need to use a local server for some browsers to allow JS fetch requests.)

## Extending
- To use real data, update `data_manager.py` to load from a database or other source.
- To allow shift assignment/editing, add new API endpoints and frontend controls.

---
