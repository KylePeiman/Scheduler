from database import get_db_session, Provider, Shift, Schedule, Assignment, CallOut, init_db
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

class DatabaseManager:
    def __init__(self):
        init_db()
        self._run_migrations()
    
    def _run_migrations(self):
        """Run database migrations to add new columns to existing tables."""
        db = get_db_session()
        try:
            # Check if migration is needed by querying table schema
            result = db.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='providers' AND column_name='provider_type'"
            ).fetchone()
            
            if not result:
                # Migration 1: Add provider_type column if it doesn't exist
                from sqlalchemy import text
                db.execute(text("ALTER TABLE providers ADD COLUMN provider_type TEXT DEFAULT 'MD'"))
                db.commit()
        except Exception as e:
            # Silently handle migration errors (likely already exists)
            db.rollback()
        finally:
            db.close()
    
    def add_provider(self, name, credentials, preferred_sites, avoided_sites, target_hours, pto_dates, commute_distances=None, provider_type='MD'):
        db = get_db_session()
        try:
            provider = Provider(
                name=name,
                provider_type=provider_type,
                credentials=credentials,
                preferred_sites=preferred_sites,
                avoided_sites=avoided_sites,
                target_hours=target_hours,
                pto_dates=pto_dates,
                commute_distances=commute_distances or {}
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)
            return self._provider_to_dict(provider)
        finally:
            db.close()
    
    def get_all_providers(self):
        db = get_db_session()
        try:
            providers = db.query(Provider).all()
            return [self._provider_to_dict(p) for p in providers]
        finally:
            db.close()
    
    def update_provider(self, provider_id, **kwargs):
        db = get_db_session()
        try:
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                for key, value in kwargs.items():
                    setattr(provider, key, value)
                provider.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(provider)
                return self._provider_to_dict(provider)
        finally:
            db.close()
    
    def delete_provider(self, provider_id):
        db = get_db_session()
        try:
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                db.delete(provider)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def add_shift(self, date, site, shift_type, required_credentials, hours, is_weekend=False, is_holiday=False):
        db = get_db_session()
        try:
            shift = Shift(
                date=date,
                site=site,
                shift_type=shift_type,
                required_credentials=required_credentials,
                hours=hours,
                is_weekend=is_weekend,
                is_holiday=is_holiday
            )
            db.add(shift)
            db.commit()
            db.refresh(shift)
            return self._shift_to_dict(shift)
        finally:
            db.close()
    
    def get_all_shifts(self):
        db = get_db_session()
        try:
            shifts = db.query(Shift).all()
            return [self._shift_to_dict(s) for s in shifts]
        finally:
            db.close()
    
    def lock_shift(self, shift_id, provider_id):
        db = get_db_session()
        try:
            shift = db.query(Shift).filter(Shift.id == shift_id).first()
            if shift:
                shift.is_locked = True
                shift.locked_provider_id = provider_id
                db.commit()
                db.refresh(shift)
                return self._shift_to_dict(shift)
        finally:
            db.close()
    
    def unlock_shift(self, shift_id):
        db = get_db_session()
        try:
            shift = db.query(Shift).filter(Shift.id == shift_id).first()
            if shift:
                shift.is_locked = False
                shift.locked_provider_id = None
                db.commit()
                db.refresh(shift)
                return self._shift_to_dict(shift)
        finally:
            db.close()
    
    def delete_shift(self, shift_id):
        db = get_db_session()
        try:
            shift = db.query(Shift).filter(Shift.id == shift_id).first()
            if shift:
                db.delete(shift)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def clear_all_shifts(self):
        db = get_db_session()
        try:
            db.query(Shift).delete()
            db.commit()
            return True
        finally:
            db.close()
    
    def create_schedule(self, name, start_date, end_date, fairness_weight, preference_weight, max_hours_per_week):
        db = get_db_session()
        try:
            schedule = Schedule(
                name=name,
                start_date=start_date,
                end_date=end_date,
                fairness_weight=fairness_weight,
                preference_weight=preference_weight,
                max_hours_per_week=max_hours_per_week
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            return schedule.id
        finally:
            db.close()
    
    def save_assignments(self, schedule_id, assignments, optimization_score):
        db = get_db_session()
        try:
            db.query(Assignment).filter(Assignment.schedule_id == schedule_id).delete()
            
            for assignment_data in assignments:
                assignment = Assignment(
                    schedule_id=schedule_id,
                    shift_id=assignment_data['shift_id'],
                    provider_id=assignment_data.get('provider_id'),
                    is_unfilled=assignment_data.get('is_unfilled', False),
                    reason=assignment_data.get('reason', ''),
                    is_manual=assignment_data.get('is_manual', False)
                )
                db.add(assignment)
            
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if schedule:
                schedule.optimization_score = optimization_score
                schedule.status = 'generated'
                schedule.updated_at = datetime.utcnow()
            
            db.commit()
            return True
        finally:
            db.close()
    
    def get_schedule(self, schedule_id):
        db = get_db_session()
        try:
            schedule = db.query(Schedule).options(
                joinedload(Schedule.assignments).joinedload(Assignment.shift_rel),
                joinedload(Schedule.assignments).joinedload(Assignment.provider_rel)
            ).filter(Schedule.id == schedule_id).first()
            
            if schedule:
                return self._schedule_to_dict(schedule)
            return None
        finally:
            db.close()
    
    def get_all_schedules(self):
        db = get_db_session()
        try:
            schedules = db.query(Schedule).all()
            return [self._schedule_to_dict(s, include_assignments=False) for s in schedules]
        finally:
            db.close()
    
    def update_assignment(self, assignment_id, provider_id, is_manual=True):
        db = get_db_session()
        try:
            assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            if assignment:
                assignment.provider_id = provider_id
                assignment.is_unfilled = False if provider_id else True
                assignment.is_manual = is_manual
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def create_callout(self, schedule_id, assignment_id, provider_id, shift_id, reason):
        db = get_db_session()
        try:
            callout = CallOut(
                schedule_id=schedule_id,
                assignment_id=assignment_id,
                provider_id=provider_id,
                shift_id=shift_id,
                reason=reason,
                status='pending'
            )
            db.add(callout)
            db.commit()
            db.refresh(callout)
            return callout.id
        finally:
            db.close()
    
    def resolve_callout(self, callout_id, replacement_provider_id):
        db = get_db_session()
        try:
            callout = db.query(CallOut).filter(CallOut.id == callout_id).first()
            if callout:
                callout.replacement_provider_id = replacement_provider_id
                callout.status = 'resolved'
                callout.resolved_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    def get_pending_callouts(self, schedule_id):
        db = get_db_session()
        try:
            callouts = db.query(CallOut).filter(
                CallOut.schedule_id == schedule_id,
                CallOut.status == 'pending'
            ).all()
            return [self._callout_to_dict(c) for c in callouts]
        finally:
            db.close()
    
    def load_sample_data(self):
        db = get_db_session()
        try:
            if db.query(Provider).count() > 0:
                return
            
            providers = [
                Provider(
                    name='Sarah Johnson',
                    provider_type='CRNA',
                    credentials=['General', 'OB'],
                    preferred_sites=['Winnie Palmer'],
                    avoided_sites=[],
                    target_hours=40,
                    pto_dates=[],
                    commute_distances={'Winnie Palmer': 5, 'Orlando Health': 15, 'Arnold Palmer': 20, 'Health Central': 25}
                ),
                Provider(
                    name='Michael Chen',
                    provider_type='CAA',
                    credentials=['General', 'Pediatric'],
                    preferred_sites=['Arnold Palmer', 'Winnie Palmer'],
                    avoided_sites=['Health Central'],
                    target_hours=45,
                    pto_dates=[],
                    commute_distances={'Winnie Palmer': 10, 'Orlando Health': 12, 'Arnold Palmer': 5, 'Health Central': 30}
                ),
                Provider(
                    name='Dr. Emily Rodriguez',
                    provider_type='MD',
                    credentials=['General', 'OB', 'Cardiac'],
                    preferred_sites=['Orlando Health'],
                    avoided_sites=[],
                    target_hours=40,
                    pto_dates=[],
                    commute_distances={'Winnie Palmer': 18, 'Orlando Health': 5, 'Arnold Palmer': 15, 'Health Central': 22}
                ),
                Provider(
                    name='Daniel Novak',
                    provider_type='CRNA',
                    credentials=['General', 'OB'],
                    preferred_sites=['Winnie Palmer', 'Orlando Health'],
                    avoided_sites=[],
                    target_hours=50,
                    pto_dates=[],
                    commute_distances={'Winnie Palmer': 8, 'Orlando Health': 10, 'Arnold Palmer': 25, 'Health Central': 28}
                ),
                Provider(
                    name='Lisa Thompson',
                    provider_type='CRNA',
                    credentials=['General', 'Pediatric', 'Neuro'],
                    preferred_sites=['Arnold Palmer'],
                    avoided_sites=['Health Central'],
                    target_hours=35,
                    pto_dates=[],
                    commute_distances={'Winnie Palmer': 12, 'Orlando Health': 20, 'Arnold Palmer': 6, 'Health Central': 35}
                )
            ]
            
            for provider in providers:
                db.add(provider)
            
            start_date = datetime.now().date()
            sites = [
                ('Winnie Palmer', ['OB'], ['Day', 'Evening', 'Night', 'Call']),
                ('Orlando Health', ['General'], ['Day', 'Evening', 'Call']),
                ('Arnold Palmer', ['Pediatric'], ['Day', 'Evening', 'Night']),
                ('Health Central', ['General'], ['Day', 'Call'])
            ]
            
            for day_offset in range(7):
                current_date = start_date + timedelta(days=day_offset)
                date_str = str(current_date)
                is_weekend = current_date.weekday() >= 5
                
                for site, required_creds, shift_types in sites:
                    for shift_type in shift_types:
                        if shift_type == 'Day':
                            hours = 8
                        elif shift_type == 'Evening':
                            hours = 8
                        elif shift_type == 'Night':
                            hours = 10
                        elif shift_type == 'Call':
                            hours = 12
                        else:
                            hours = 8
                        
                        if shift_type == 'Call' and day_offset % 2 == 1:
                            continue
                        
                        shift = Shift(
                            date=date_str,
                            site=site,
                            shift_type=shift_type,
                            required_credentials=required_creds,
                            hours=hours,
                            is_weekend=is_weekend,
                            is_holiday=False
                        )
                        db.add(shift)
            
            db.commit()
            return True
        finally:
            db.close()
    
    def _provider_to_dict(self, provider):
        return {
            'id': provider.id,
            'name': provider.name,
            'provider_type': provider.provider_type,
            'credentials': provider.credentials,
            'preferred_sites': provider.preferred_sites,
            'avoided_sites': provider.avoided_sites,
            'target_hours': provider.target_hours,
            'pto_dates': provider.pto_dates,
            'commute_distances': provider.commute_distances
        }
    
    def _shift_to_dict(self, shift):
        return {
            'id': shift.id,
            'date': shift.date,
            'site': shift.site,
            'shift_type': shift.shift_type,
            'required_credentials': shift.required_credentials,
            'hours': shift.hours,
            'is_weekend': shift.is_weekend,
            'is_holiday': shift.is_holiday,
            'is_locked': shift.is_locked,
            'locked_provider_id': shift.locked_provider_id
        }
    
    def _schedule_to_dict(self, schedule, include_assignments=True):
        result = {
            'id': schedule.id,
            'name': schedule.name,
            'start_date': schedule.start_date,
            'end_date': schedule.end_date,
            'status': schedule.status,
            'optimization_score': schedule.optimization_score,
            'created_at': schedule.created_at.isoformat() if schedule.created_at else None
        }
        
        if include_assignments and schedule.assignments:
            result['assignments'] = []
            for assignment in schedule.assignments:
                result['assignments'].append({
                    'id': assignment.id,
                    'date': assignment.shift_rel.date if assignment.shift_rel else None,
                    'site': assignment.shift_rel.site if assignment.shift_rel else None,
                    'shift_type': assignment.shift_rel.shift_type if assignment.shift_rel else None,
                    'hours': assignment.shift_rel.hours if assignment.shift_rel else None,
                    'provider': assignment.provider_rel.name if assignment.provider_rel else 'UNFILLED',
                    'provider_id': assignment.provider_id,
                    'shift_id': assignment.shift_id,
                    'is_unfilled': assignment.is_unfilled,
                    'reason': assignment.reason,
                    'is_manual': assignment.is_manual
                })
        
        return result
    
    def _callout_to_dict(self, callout):
        return {
            'id': callout.id,
            'schedule_id': callout.schedule_id,
            'assignment_id': callout.assignment_id,
            'provider_id': callout.provider_id,
            'shift_id': callout.shift_id,
            'reason': callout.reason,
            'status': callout.status,
            'created_at': callout.created_at.isoformat() if callout.created_at else None
        }
