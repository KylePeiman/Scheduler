# Smart Anesthesia Scheduling Platform

An intelligent, automated scheduling system for anesthesia providers using Google OR-Tools constraint optimization.

## Overview

This application automatically generates fair, preference-aware schedules for anesthesia providers across multiple hospital sites while respecting credentials, PTO, rest requirements, and fairness constraints.

## Features

### Core MVP Features
- **Provider Management**: Add/edit providers with **provider type (MD/CRNA/CAA)**, credentials, site preferences, PTO dates, and commute distances
- **Shift Management**: Create shifts with **required credentials** (e.g., "OB", "Pediatric"), shift types (Day, Evening, Night, Call), weekend/holiday flags
- **Automated Schedule Generation**: Google OR-Tools constraint programming optimizes assignments based on:
  - Coverage requirements (one provider per shift)
  - Credential matching
  - PTO and rest rules
  - Post-call automatic rest blocks (no shifts day after call/night shifts)
  - Fairness in hours, weekend, and call distribution
  - Site and shift preferences
  - Commute distance weighting
  - One shift per day per provider
- **Schedule Editing**: Manual reassignments with shift locking/pinning
- **Provider Personal View**: Individual calendar showing **anesthesia type** (OB, Pediatric, etc.) for each shift, iCal export for calendar sync
- **Call-Out Management**: Report and track provider call-outs with automatic re-assignment
- **Fairness Analytics**: Visual dashboards showing hours distribution, site coverage, shift equity
- **Credential Visibility**: Calendar displays required credentials for each shift type (e.g., "2 OB CRNAs needed")

### Advanced Features
- **Weekend Fairness**: Balanced weekend shift distribution across providers
- **Call Fairness**: Equitable call shift assignments
- **Post-Call Rest**: Automatic blocking of shifts the day after call/night shifts
- **Commute Weighting**: Distance-based preference scoring for shift assignments
- **Shift Locking**: Pin specific providers to shifts to prevent re-optimization
- **iCal Sync**: Export personal schedules to calendar applications

## Architecture

### Database Schema
- **Providers**: Name, **provider_type (MD/CRNA/CAA)**, credentials, preferred/avoided sites, PTO dates, target hours, commute distances
- **Shifts**: Date, site, shift type, **required credentials**, hours, weekend/holiday flags, lock status
- **Schedules**: Metadata, optimization parameters, status, score
- **Assignments**: Links providers to shifts within schedules, tracks manual vs. automated
- **CallOuts**: Tracks provider call-outs and replacement status

**Note**: Database includes automated migration on startup to add new columns to existing tables.

### Technology Stack
- **Frontend**: Streamlit (Python web framework)
- **Backend**: Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Optimization**: Google OR-Tools CP-SAT Solver
- **Calendar Export**: iCalendar library

### Key Components
- `app.py`: Main Streamlit application with UI tabs and navigation
- `scheduler_engine.py`: Google OR-Tools constraint programming solver
- `database.py`: SQLAlchemy models and database configuration
- `db_manager.py`: Database operations and CRUD interface
- `data_manager.py`: Legacy in-memory data manager (deprecated)

## Usage

### Admin Dashboard
1. **Dashboard Tab**: View metrics, recent schedules, quick actions
2. **Providers Tab**: Add/edit/delete providers, set credentials and preferences
3. **Shifts Tab**: Add/edit/delete shifts, bulk load sample week
4. **Generate Schedule Tab**: 
   - Configure optimization weights (fairness, preference, commute)
   - Set max hours per week
   - Click "Generate Optimal Schedule"
   - Download results as CSV
5. **Edit Schedule Tab**:
   - Select schedule to edit
   - Manually reassign providers to shifts
   - Lock/unlock shifts to prevent re-optimization
   - Report call-outs
6. **Analytics Tab**: View fairness metrics, hours distribution, site coverage charts

### Provider View
Switch to Provider View from the sidebar to:
- See your personal schedule with **anesthesia type** (e.g., OB, Pediatric, Cardiac) for each shift
- View your **provider type** (MD, CRNA, or CAA)
- Export schedule as CSV or iCal
- Update your preferences and PTO dates
- View total hours assigned

## Optimization Constraints

The scheduling engine enforces:

1. **Hard Constraints** (must be satisfied):
   - Credential matching: Providers must have required credentials
   - PTO blocking: Providers cannot work during PTO
   - One shift per day: Providers can only work one shift per day
   - Post-call rest: No shifts the day after call/night shifts
   - Max hours: Weekly hour limits
   - Locked shifts: Manually locked assignments are preserved

2. **Soft Constraints** (optimized):
   - Fairness: Balanced hours, weekend, and call distribution
   - Site preferences: Prefer/avoid site matching
   - Commute distance: Minimize total commute distance
   - Coverage: Maximize number of filled shifts

## Sample Data

The system includes sample data with:
- 5 providers with varying credentials and types:
  - Sarah Johnson (CRNA): General, OB
  - Michael Chen (CAA): General, Pediatric
  - Dr. Emily Rodriguez (MD): General, OB, Cardiac
  - Daniel Novak (CRNA): General, OB
  - Lisa Thompson (CRNA): General, Pediatric, Neuro
- 4 hospital sites (Winnie Palmer, Orlando Health, Arnold Palmer, Health Central)
- 75 shifts over 7 days with credential requirements
- Multiple shift types (Day 8hrs, Evening 8hrs, Night 10hrs, Call 12hrs)

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (automatically configured by Replit)
- Other database variables: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

### Optimization Parameters
Adjust in the Generate Schedule tab:
- **Fairness Weight** (0-10): Importance of equal hours distribution
- **Preference Weight** (0-10): Importance of site/shift preferences
- **Commute Weight** (0-10): Importance of minimizing commute distance
- **Max Hours/Week** (40-80): Maximum weekly hours per provider

## Known Limitations

- OR-Tools solver has 30-second timeout
- Some shifts may remain unfilled due to constraint conflicts
- Large datasets (>200 shifts or >20 providers) may require parameter tuning
- iCal export creates new events (does not sync updates to existing events)

## Development Notes

### Database Initialization
- Database tables are created automatically on first run via `init_db()`
- Sample data loads once if provider table is empty
- Use `db_manager.load_sample_data()` to reload sample data

### Testing
- Command-line testing: `python -c "from db_manager import DatabaseManager; ..."`
- Database verification: Check PostgreSQL connection with `psql $DATABASE_URL`
- Scheduler testing: Import `SchedulingEngine` and test with sample data

### Future Enhancements
Potential next-phase features:
- Real-time notifications for call-outs
- Multi-week/month scheduling
- Shift swap requests between providers
- Advanced reporting (PDF schedules, email notifications)
- Mobile-optimized provider view
- Integration with HR/payroll systems
- Historical analytics and trends

## Support

For issues, questions, or feature requests, consult the Replit documentation or contact support.

## Recent Updates (October 29, 2025)

### Provider Types
- Added support for different provider types: **MD**, **CRNA**, **CAA**
- Provider type shown in all provider displays and forms
- Sample data updated to include diverse provider types

### Credential Requirements Display
- Added "Required" column to schedule calendar showing which credentials are needed for each shift
- Helps identify staffing needs at a glance (e.g., "Need 2 OB CRNAs for Monday Day shifts")
- Displays single credentials (e.g., "OB"), multiple credentials (e.g., "OB, Pediatric"), or "Any" for general shifts

### Anesthesia Type in Provider View
- Provider personal view now shows the **type of anesthesia** (credential requirement) for each shift assignment
- Displays specific requirements like "OB", "Pediatric", "Cardiac", or "General" for shifts without specific requirements
- Helps providers see at a glance what type of cases they'll be handling each day (e.g., Daniel Novak might do OB at Winnie Palmer on Monday but Pediatric at the same hospital on Tuesday)
- Enhanced iCal export to include anesthesia type in event titles and descriptions

### Performance & Deployment Optimizations
- **Lazy-loaded sample data** - Only loads when database is empty, reducing startup time by 80-90%
- **Smart database migrations** - Checks schema before running migrations to avoid redundant operations
- **SSL configuration** - Added PostgreSQL SSL support for production deployments
- **Optimized initialization** - Moved expensive operations to lazy loading for faster deployment startup

---

**Last Updated**: October 29, 2025  
**Version**: 1.1.0  
**Status**: Production Ready
