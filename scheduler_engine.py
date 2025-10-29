from ortools.sat.python import cp_model
from datetime import datetime, timedelta

class SchedulingEngine:
    def __init__(self, providers, shifts, fairness_weight=5.0, preference_weight=3.0, max_hours_per_week=60, 
                 commute_weight=2.0, weekend_fairness_weight=3.0, call_fairness_weight=4.0):
        self.providers = providers
        self.shifts = shifts
        self.fairness_weight = fairness_weight
        self.preference_weight = preference_weight
        self.max_hours_per_week = max_hours_per_week
        self.commute_weight = commute_weight
        self.weekend_fairness_weight = weekend_fairness_weight
        self.call_fairness_weight = call_fairness_weight
        
    def solve(self):
        model = cp_model.CpModel()
        
        num_providers = len(self.providers)
        num_shifts = len(self.shifts)
        
        if num_providers == 0 or num_shifts == 0:
            return {
                'status': 'INFEASIBLE',
                'score': 0,
                'assignments': []
            }
        
        assignments = {}
        for p in range(num_providers):
            for s in range(num_shifts):
                assignments[(p, s)] = model.NewBoolVar(f'assign_p{p}_s{s}')
        
        for s in range(num_shifts):
            shift = self.shifts[s]
            if shift.get('is_locked') and shift.get('locked_provider_id'):
                locked_provider_idx = next(
                    (i for i, prov in enumerate(self.providers) if prov.get('id') == shift['locked_provider_id']),
                    None
                )
                if locked_provider_idx is not None:
                    model.Add(assignments[(locked_provider_idx, s)] == 1)
                    for p in range(num_providers):
                        if p != locked_provider_idx:
                            model.Add(assignments[(p, s)] == 0)
                    continue
            
            model.Add(sum(assignments[(p, s)] for p in range(num_providers)) <= 1)
        
        dates_by_provider = {}
        for p in range(num_providers):
            dates_by_provider[p] = {}
            for s in range(num_shifts):
                date = self.shifts[s]['date']
                if date not in dates_by_provider[p]:
                    dates_by_provider[p][date] = []
                dates_by_provider[p][date].append(s)
        
        for p in range(num_providers):
            for date, shift_indices in dates_by_provider[p].items():
                if len(shift_indices) > 1:
                    model.Add(sum(assignments[(p, s)] for s in shift_indices) <= 1)
        
        shift_dates = {}
        for s in range(num_shifts):
            shift = self.shifts[s]
            date_str = shift['date']
            if shift['shift_type'] == 'Call' or shift['shift_type'] == 'Night':
                shift_dates[s] = date_str
        
        for p in range(num_providers):
            for s in range(num_shifts):
                if s in shift_dates:
                    call_date = shift_dates[s]
                    try:
                        next_day = (datetime.strptime(call_date, '%Y-%m-%d').date() + timedelta(days=1)).strftime('%Y-%m-%d')
                        
                        next_day_shifts = [idx for idx in range(num_shifts) 
                                         if self.shifts[idx]['date'] == next_day]
                        
                        for next_shift in next_day_shifts:
                            model.Add(assignments[(p, s)] + assignments[(p, next_shift)] <= 1)
                    except:
                        pass
        
        for p in range(num_providers):
            total_hours = sum(
                assignments[(p, s)] * int(self.shifts[s]['hours'])
                for s in range(num_shifts)
            )
            model.Add(total_hours <= int(self.max_hours_per_week))
        
        objective_terms = []
        
        target_hours_per_provider = sum(shift['hours'] for shift in self.shifts) / max(num_providers, 1)
        
        hours_per_provider = []
        for p in range(num_providers):
            provider_hours = sum(
                assignments[(p, s)] * int(self.shifts[s]['hours'])
                for s in range(num_shifts)
            )
            hours_per_provider.append(provider_hours)
        
        for p in range(num_providers):
            provider_target = self.providers[p].get('target_hours', target_hours_per_provider)
            deviation = model.NewIntVar(-1000, 1000, f'deviation_p{p}')
            abs_deviation = model.NewIntVar(0, 1000, f'abs_deviation_p{p}')
            
            model.Add(deviation == hours_per_provider[p] - int(provider_target))
            model.AddAbsEquality(abs_deviation, deviation)
            
            objective_terms.append(-abs_deviation * int(self.fairness_weight * 100))
        
        weekend_shifts_by_provider = []
        call_shifts_by_provider = []
        
        for p in range(num_providers):
            weekend_shifts = sum(
                assignments[(p, s)]
                for s in range(num_shifts)
                if self.shifts[s].get('is_weekend', False)
            )
            weekend_shifts_by_provider.append(weekend_shifts)
            
            call_shifts = sum(
                assignments[(p, s)]
                for s in range(num_shifts)
                if self.shifts[s]['shift_type'] == 'Call'
            )
            call_shifts_by_provider.append(call_shifts)
        
        if num_providers > 1:
            for p in range(num_providers):
                weekend_deviation = model.NewIntVar(-100, 100, f'weekend_dev_p{p}')
                weekend_abs_dev = model.NewIntVar(0, 100, f'weekend_abs_dev_p{p}')
                
                avg_weekend = sum(1 for s in self.shifts if s.get('is_weekend', False)) / num_providers
                model.Add(weekend_deviation == weekend_shifts_by_provider[p] - int(avg_weekend))
                model.AddAbsEquality(weekend_abs_dev, weekend_deviation)
                
                objective_terms.append(-weekend_abs_dev * int(self.weekend_fairness_weight * 100))
                
                call_deviation = model.NewIntVar(-100, 100, f'call_dev_p{p}')
                call_abs_dev = model.NewIntVar(0, 100, f'call_abs_dev_p{p}')
                
                avg_call = sum(1 for s in self.shifts if s['shift_type'] == 'Call') / num_providers
                model.Add(call_deviation == call_shifts_by_provider[p] - int(avg_call))
                model.AddAbsEquality(call_abs_dev, call_deviation)
                
                objective_terms.append(-call_abs_dev * int(self.call_fairness_weight * 100))
        
        for p in range(num_providers):
            provider = self.providers[p]
            preferred_sites = provider.get('preferred_sites', [])
            avoided_sites = provider.get('avoided_sites', [])
            pto_dates = provider.get('pto_dates', [])
            credentials = provider.get('credentials', [])
            commute_distances = provider.get('commute_distances', {})
            
            for s in range(num_shifts):
                shift = self.shifts[s]
                
                if shift['date'] in pto_dates:
                    model.Add(assignments[(p, s)] == 0)
                    continue
                
                if shift.get('is_locked'):
                    continue
                
                required_creds = shift.get('required_credentials', [])
                has_credentials = any(cred in credentials for cred in required_creds) or not required_creds
                
                if not has_credentials:
                    model.Add(assignments[(p, s)] == 0)
                    continue
                
                if shift['site'] in preferred_sites:
                    objective_terms.append(assignments[(p, s)] * int(self.preference_weight * 100))
                
                if shift['site'] in avoided_sites:
                    objective_terms.append(assignments[(p, s)] * int(-self.preference_weight * 100))
                
                if commute_distances and shift['site'] in commute_distances:
                    distance = commute_distances[shift['site']]
                    commute_penalty = min(distance, 50)
                    objective_terms.append(assignments[(p, s)] * int(-commute_penalty * self.commute_weight))
        
        for s in range(num_shifts):
            assigned = sum(assignments[(p, s)] for p in range(num_providers))
            objective_terms.append(assigned * 1000)
        
        model.Maximize(sum(objective_terms))
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        status = solver.Solve(model)
        
        status_names = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
            cp_model.UNKNOWN: 'UNKNOWN'
        }
        
        result = {
            'status': status_names.get(status, 'UNKNOWN'),
            'score': solver.ObjectiveValue() / 100.0 if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else 0,
            'assignments': []
        }
        
        for s in range(num_shifts):
            shift = self.shifts[s]
            assigned_provider = None
            
            for p in range(num_providers):
                if solver.BooleanValue(assignments[(p, s)]):
                    assigned_provider = p
                    break
            
            if assigned_provider is not None:
                provider = self.providers[assigned_provider]
                reason = self._generate_reason(provider, shift)
                
                result['assignments'].append({
                    'shift_id': shift.get('id'),
                    'provider_id': provider.get('id'),
                    'date': shift['date'],
                    'site': shift['site'],
                    'shift_type': shift['shift_type'],
                    'hours': shift['hours'],
                    'required_credentials': shift.get('required_credentials', []),
                    'provider': provider['name'],
                    'is_unfilled': False,
                    'reason': reason
                })
            else:
                result['assignments'].append({
                    'shift_id': shift.get('id'),
                    'provider_id': None,
                    'date': shift['date'],
                    'site': shift['site'],
                    'shift_type': shift['shift_type'],
                    'hours': shift['hours'],
                    'required_credentials': shift.get('required_credentials', []),
                    'provider': 'UNFILLED',
                    'is_unfilled': True,
                    'reason': 'No available provider met all constraints'
                })
        
        return result
    
    def _generate_reason(self, provider, shift):
        reasons = []
        
        required_creds = shift.get('required_credentials', [])
        matching_creds = [c for c in required_creds if c in provider.get('credentials', [])]
        if matching_creds:
            reasons.append(f"✅ Has required credentials: {', '.join(matching_creds)}")
        
        if shift['site'] in provider.get('preferred_sites', []):
            reasons.append(f"⭐ Preferred site match")
        
        if shift['date'] not in provider.get('pto_dates', []):
            reasons.append(f"✅ Available (no PTO)")
        
        if shift.get('is_weekend'):
            reasons.append(f"📅 Weekend shift (fair distribution)")
        
        if shift['shift_type'] == 'Call':
            reasons.append(f"📞 Call shift (fair distribution)")
        
        commute_distances = provider.get('commute_distances', {})
        if commute_distances and shift['site'] in commute_distances:
            distance = commute_distances[shift['site']]
            reasons.append(f"🚗 Commute: {distance} miles")
        
        reasons.append(f"⚖️ Contributes to fair hours distribution")
        
        return " | ".join(reasons)
