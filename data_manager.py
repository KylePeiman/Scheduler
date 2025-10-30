from datetime import datetime, timedelta

class DataManager:
    def __init__(self):
        self.providers = []
        self.shifts = []
    
    def add_provider(self, name, credentials, preferred_sites, avoided_sites, target_hours, pto_dates):
        provider = {
            'name': name,
            'credentials': credentials,
            'preferred_sites': preferred_sites,
            'avoided_sites': avoided_sites,
            'target_hours': target_hours,
            'pto_dates': pto_dates
        }
        self.providers.append(provider)
        return provider
    
    def add_shift(self, date, site, shift_type, required_credentials, hours):
        shift = {
            'date': date,
            'site': site,
            'shift_type': shift_type,
            'required_credentials': required_credentials,
            'hours': hours
        }
        self.shifts.append(shift)
        return shift
    
    def load_sample_data(self):
        self.providers = [
            {
                'name': 'Dr. Sarah Johnson',
                'credentials': ['General', 'OB'],
                'preferred_sites': ['Winnie Palmer'],
                'avoided_sites': [],
                'target_hours': 40,
                'pto_dates': []
            },
            {
                'name': 'Dr. Michael Chen',
                'credentials': ['General', 'Pediatric'],
                'preferred_sites': ['Arnold Palmer', 'Winnie Palmer'],
                'avoided_sites': ['Health Central'],
                'target_hours': 45,
                'pto_dates': []
            },
            {
                'name': 'Dr. Emily Rodriguez',
                'credentials': ['General', 'OB', 'Cardiac'],
                'preferred_sites': ['Orlando Health'],
                'avoided_sites': [],
                'target_hours': 40,
                'pto_dates': []
            },
            {
                'name': 'Dr. Daniel Novak',
                'credentials': ['General', 'OB'],
                'preferred_sites': ['Winnie Palmer', 'Orlando Health'],
                'avoided_sites': [],
                'target_hours': 50,
                'pto_dates': []
            },
            {
                'name': 'Dr. Lisa Thompson',
                'credentials': ['General', 'Pediatric', 'Neuro'],
                'preferred_sites': ['Arnold Palmer'],
                'avoided_sites': ['Health Central'],
                'target_hours': 35,
                'pto_dates': []
            }
        ]
        
        self.shifts = []
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
            
            for site, required_creds, shift_types in sites:
                for shift_type in shift_types:
                    if shift_type == 'Day':
                        hours = 8
                        start_time = "08:00"
                        end_time = "16:00"
                    elif shift_type == 'Evening':
                        hours = 8
                        start_time = "16:00"
                        end_time = "00:00"
                    elif shift_type == 'Night':
                        hours = 10
                        start_time = "00:00"
                        end_time = "10:00"
                    elif shift_type == 'Call':
                        hours = 12
                        start_time = "00:00"
                        end_time = "12:00"
                    else:
                        hours = 8
                    
                    if shift_type == 'Call' and day_offset % 2 == 1:
                        continue
                    
                    self.shifts.append({
                        'date': date_str,
                        'start_time': start_time,
                        'end_time': end_time,
                        'site': site,
                        'shift_type': shift_type,
                        'required_credentials': required_creds,
                        'hours': hours
                    })
        
        # Assign providers to shifts in a round-robin fashion for demo
        for i, shift in enumerate(self.shifts):
            provider = self.providers[i % len(self.providers)]['name']
            shift['provider'] = provider
