import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from scheduler_engine import SchedulingEngine
from db_manager import DatabaseManager
import icalendar
from io import BytesIO

st.set_page_config(
    page_title="Smart Anesthesia Scheduler",
    page_icon="🏥",
    layout="wide"
)

if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()

if 'current_schedule_id' not in st.session_state:
    st.session_state.current_schedule_id = None

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'admin'

if 'sample_data_loaded' not in st.session_state:
    st.session_state.sample_data_loaded = False

dm = st.session_state.db_manager

if not st.session_state.sample_data_loaded:
    providers = dm.get_all_providers()
    if len(providers) == 0:
        dm.load_sample_data()
    st.session_state.sample_data_loaded = True

st.sidebar.title("🏥 Navigation")
view_mode = st.sidebar.radio("View Mode", ["Admin Dashboard", "Provider View"], index=0)
st.session_state.view_mode = 'provider' if view_mode == "Provider View" else 'admin'

if st.session_state.view_mode == 'provider':
    st.title("👤 Provider Personal View")
    
    providers = dm.get_all_providers()
    if providers:
        provider_names = [p['name'] for p in providers]
        selected_provider_name = st.selectbox("Select Provider", provider_names)
        selected_provider = next(p for p in providers if p['name'] == selected_provider_name)
        
        st.header(f"Welcome, {selected_provider['name']}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Provider Type", selected_provider.get('provider_type', 'MD'))
        with col2:
            st.metric("Target Hours/Week", selected_provider['target_hours'])
        with col3:
            st.metric("Credentials", len(selected_provider['credentials']))
        with col4:
            st.metric("PTO Days", len(selected_provider['pto_dates']))
        
        st.subheader("📅 Your Schedule")
        
        schedules = dm.get_all_schedules()
        if schedules:
            schedule_names = [f"{s['name']} ({s['status']})" for s in schedules]
            if schedule_names:
                selected_schedule_name = st.selectbox("Select Schedule", schedule_names)
                selected_schedule_idx = schedule_names.index(selected_schedule_name)
                selected_schedule = schedules[selected_schedule_idx]
                
                full_schedule = dm.get_schedule(selected_schedule['id'])
                
                if full_schedule and full_schedule.get('assignments'):
                    my_assignments = [a for a in full_schedule['assignments'] 
                                    if a['provider_id'] == selected_provider['id']]
                    
                    if my_assignments:
                        # Get required credentials (type of anesthesia) for each assignment
                        # Cache shifts lookup to avoid redundant queries
                        shifts = dm.get_all_shifts()
                        for my_assign in my_assignments:
                            # Get the shift details to find required credentials
                            shift_id = my_assign.get('shift_id')
                            if shift_id:
                                shift = next((s for s in shifts if s['id'] == shift_id), None)
                                if shift:
                                    creds = shift.get('required_credentials', [])
                                    if creds:
                                        my_assign['anesthesia_type'] = ', '.join(creds)
                                    else:
                                        my_assign['anesthesia_type'] = 'General'
                                else:
                                    my_assign['anesthesia_type'] = 'General'
                            else:
                                my_assign['anesthesia_type'] = 'General'
                        
                        df = pd.DataFrame(my_assignments)
                        st.dataframe(
                            df[['date', 'site', 'shift_type', 'anesthesia_type', 'hours']].rename(columns={'anesthesia_type': 'Anesthesia Type'}),
                            width='stretch',
                            hide_index=True
                        )
                        
                        total_hours = sum(a['hours'] for a in my_assignments)
                        st.info(f"📊 Total Hours: {total_hours}")
                        
                        st.subheader("📥 Export Options")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "Download as CSV",
                                csv,
                                f"{selected_provider['name']}_schedule.csv",
                                "text/csv",
                                width='stretch'
                            )
                        
                        with col2:
                            cal = icalendar.Calendar()
                            cal.add('prodid', '-//Smart Anesthesia Scheduler//EN')
                            cal.add('version', '2.0')
                            
                            for assignment in my_assignments:
                                event = icalendar.Event()
                                anesthesia_type = assignment.get('anesthesia_type', 'General')
                                event.add('summary', f"{assignment['shift_type']} - {assignment['site']} ({anesthesia_type})")
                                event.add('dtstart', datetime.strptime(assignment['date'], '%Y-%m-%d').date())
                                event.add('duration', timedelta(hours=assignment['hours']))
                                event.add('description', f"{anesthesia_type} anesthesia - {assignment['shift_type']} shift at {assignment['site']}")
                                cal.add_component(event)
                            
                            ical_data = cal.to_ical()
                            st.download_button(
                                "Download iCal",
                                ical_data,
                                f"{selected_provider['name']}_schedule.ics",
                                "text/calendar",
                                width='stretch'
                            )
                    else:
                        st.info("You have no assignments in this schedule")
                else:
                    st.info("This schedule has no assignments yet")
        else:
            st.info("No schedules available")
        
        st.subheader("⚙️ Your Preferences")
        with st.form("update_preferences"):
            new_target_hours = st.number_input("Target Hours/Week", 
                                              min_value=0, max_value=80, 
                                              value=int(selected_provider['target_hours']))
            
            new_pto = st.text_input("PTO Dates (comma-separated, YYYY-MM-DD)", 
                                   ",".join(selected_provider['pto_dates']))
            
            if st.form_submit_button("Update Preferences"):
                pto_list = [d.strip() for d in new_pto.split(",") if d.strip()]
                dm.update_provider(
                    selected_provider['id'],
                    target_hours=new_target_hours,
                    pto_dates=pto_list
                )
                st.success("Preferences updated!")
                st.rerun()
    else:
        st.info("No providers found in the system")
    
    st.stop()

st.title("🏥 Smart Anesthesia Scheduling Platform")
st.markdown("*Automated, fair, preference-aware scheduling using Google OR-Tools*")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard", 
    "👥 Providers", 
    "📅 Shifts", 
    "🎯 Generate Schedule",
    "✏️ Edit Schedule",
    "📈 Analytics"
])

with tab1:
    st.header("Dashboard Overview")
    
    providers = dm.get_all_providers()
    shifts = dm.get_all_shifts()
    schedules = dm.get_all_schedules()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Providers", len(providers))
    with col2:
        st.metric("Active Sites", len(set(s['site'] for s in shifts)) if shifts else 0)
    with col3:
        st.metric("Shifts to Fill", len(shifts))
    with col4:
        st.metric("Saved Schedules", len(schedules))
    
    st.subheader("Recent Schedules")
    if schedules:
        schedule_df = pd.DataFrame(schedules)
        st.dataframe(
            schedule_df[['name', 'start_date', 'end_date', 'status', 'optimization_score']],
            width='stretch',
            hide_index=True
        )
    else:
        st.info("No schedules generated yet")

with tab2:
    st.header("Provider Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Current Providers")
        providers = dm.get_all_providers()
        if providers:
            providers_df = pd.DataFrame(providers)
            st.dataframe(
                providers_df[['name', 'provider_type', 'credentials', 'preferred_sites', 'target_hours']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No providers added yet")
    
    with col2:
        st.subheader("Add New Provider")
        with st.form("add_provider"):
            name = st.text_input("Provider Name")
            provider_type = st.selectbox(
                "Provider Type",
                ["MD", "CRNA", "CAA"],
                index=0
            )
            credentials = st.multiselect(
                "Credentials",
                ["General", "OB", "Pediatric", "Cardiac", "Neuro"],
                default=["General"]
            )
            preferred_sites = st.multiselect(
                "Preferred Sites",
                ["Winnie Palmer", "Orlando Health", "Arnold Palmer", "Health Central"],
                default=[]
            )
            avoided_sites = st.multiselect(
                "Avoided Sites",
                ["Winnie Palmer", "Orlando Health", "Arnold Palmer", "Health Central"],
                default=[]
            )
            target_hours = st.number_input("Target Hours/Week", min_value=0, max_value=80, value=40)
            pto_dates = st.text_input("PTO Dates (comma-separated, YYYY-MM-DD)", "")
            
            st.subheader("Commute Distances (miles)")
            wp_distance = st.number_input("Winnie Palmer", min_value=0, max_value=100, value=10)
            oh_distance = st.number_input("Orlando Health", min_value=0, max_value=100, value=10)
            ap_distance = st.number_input("Arnold Palmer", min_value=0, max_value=100, value=10)
            hc_distance = st.number_input("Health Central", min_value=0, max_value=100, value=10)
            
            if st.form_submit_button("Add Provider"):
                pto_list = [d.strip() for d in pto_dates.split(",") if d.strip()]
                commute_distances = {
                    "Winnie Palmer": wp_distance,
                    "Orlando Health": oh_distance,
                    "Arnold Palmer": ap_distance,
                    "Health Central": hc_distance
                }
                dm.add_provider(
                    name=name,
                    credentials=credentials,
                    preferred_sites=preferred_sites,
                    avoided_sites=avoided_sites,
                    target_hours=target_hours,
                    pto_dates=pto_list,
                    commute_distances=commute_distances,
                    provider_type=provider_type
                )
                st.success(f"✅ Added {name}")
                st.rerun()

with tab3:
    st.header("Shift Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Current Shifts")
        shifts = dm.get_all_shifts()
        if shifts:
            shifts_df = pd.DataFrame(shifts)
            display_df = shifts_df[['date', 'site', 'shift_type', 'required_credentials', 'hours', 'is_weekend', 'is_locked']]
            st.dataframe(
                display_df,
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No shifts added yet")
    
    with col2:
        st.subheader("Add New Shift")
        with st.form("add_shift"):
            date = st.date_input("Date", datetime.now())
            site = st.selectbox(
                "Site",
                ["Winnie Palmer", "Orlando Health", "Arnold Palmer", "Health Central"]
            )
            shift_type = st.selectbox(
                "Shift Type",
                ["Day", "Evening", "Night", "Call"]
            )
            required_creds = st.multiselect(
                "Required Credentials",
                ["General", "OB", "Pediatric", "Cardiac", "Neuro"],
                default=["General"]
            )
            hours = st.number_input("Shift Hours", min_value=1, max_value=24, value=8)
            is_weekend = st.checkbox("Weekend Shift", value=date.weekday() >= 5)
            is_holiday = st.checkbox("Holiday Shift", value=False)
            
            if st.form_submit_button("Add Shift"):
                dm.add_shift(
                    date=str(date),
                    site=site,
                    shift_type=shift_type,
                    required_credentials=required_creds,
                    hours=hours,
                    is_weekend=is_weekend,
                    is_holiday=is_holiday
                )
                st.success(f"✅ Added {shift_type} shift at {site}")
                st.rerun()
        
        st.subheader("Bulk Actions")
        if st.button("🗑️ Clear All Shifts"):
            dm.clear_all_shifts()
            st.success("All shifts cleared")
            st.rerun()
        
        if st.button("📋 Load Sample Week"):
            dm.load_sample_data()
            st.success("Sample week loaded")
            st.rerun()

with tab4:
    st.header("Generate Schedule")
    
    st.markdown("""
    Create an optimal schedule that automatically:
    - Matches provider credentials to shift requirements
    - Respects PTO and ensures proper rest after call/night shifts
    - Distributes hours, weekends, and call shifts fairly
    - Considers site preferences and commute distances
    - Ensures each provider works only one shift per day
    """)
    
    schedule_name = st.text_input("Schedule Name", f"Schedule_{datetime.now().strftime('%Y%m%d')}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start Date", datetime.now())
    with col2:
        end_date = st.date_input("End Date", datetime.now() + timedelta(days=7))
    with col3:
        max_hours_per_week = st.number_input("Max Hours/Week", 40, 80, 60)
    
    # Static optimization weights - balanced for fairness and preferences
    fairness_weight = 5.0
    preference_weight = 3.0
    commute_weight = 2.0
    
    if st.button("🎯 Generate Optimal Schedule", type="primary", width='stretch'):
        providers = dm.get_all_providers()
        shifts = dm.get_all_shifts()
        
        if not providers:
            st.error("❌ No providers available. Please add providers first.")
        elif not shifts:
            st.error("❌ No shifts to schedule. Please add shifts first.")
        else:
            with st.spinner("Running optimization engine..."):
                engine = SchedulingEngine(
                    providers=providers,
                    shifts=shifts,
                    fairness_weight=fairness_weight,
                    preference_weight=preference_weight,
                    max_hours_per_week=max_hours_per_week,
                    commute_weight=commute_weight
                )
                
                result = engine.solve()
                
                if result['status'] == 'OPTIMAL' or result['status'] == 'FEASIBLE':
                    schedule_id = dm.create_schedule(
                        name=schedule_name,
                        start_date=str(start_date),
                        end_date=str(end_date),
                        fairness_weight=fairness_weight,
                        preference_weight=preference_weight,
                        max_hours_per_week=max_hours_per_week
                    )
                    
                    dm.save_assignments(schedule_id, result['assignments'], result['score'])
                    st.session_state.current_schedule_id = schedule_id
                    
                    st.success(f"✅ Schedule created successfully!")
                    
                    # Count filled vs unfilled shifts
                    total_shifts = len(result['assignments'])
                    filled_shifts = len([a for a in result['assignments'] if not a.get('is_unfilled', True)])
                    unfilled_shifts = total_shifts - filled_shifts
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Shifts", total_shifts)
                    with col2:
                        st.metric("Assigned", filled_shifts, delta=f"{(filled_shifts/total_shifts*100):.0f}%")
                    with col3:
                        st.metric("Unfilled", unfilled_shifts)
                    
                    st.subheader("📅 Schedule Calendar")
                    
                    # Create calendar grid view
                    assignments_df = pd.DataFrame(result['assignments'])
                    assignments_df['date'] = pd.to_datetime(assignments_df['date'])
                    assignments_df = assignments_df.sort_values('date')
                    
                    # Get unique sites for filtering
                    unique_sites = sorted(assignments_df['site'].unique())
                    
                    # Add site filter
                    selected_site = st.selectbox(
                        "Filter by Site",
                        ["All Sites"] + list(unique_sites),
                        key="schedule_site_filter"
                    )
                    
                    # Filter assignments by site if selected
                    if selected_site != "All Sites":
                        filtered_df = assignments_df[assignments_df['site'] == selected_site]
                    else:
                        filtered_df = assignments_df
                    
                    # Get unique dates
                    unique_dates = sorted(filtered_df['date'].dt.date.unique())
                    
                    # Define shift types with descriptions
                    shift_info = {
                        "Day": "7am-3pm (8hrs)",
                        "Evening": "3pm-11pm (8hrs)",
                        "Night": "11pm-7am (10hrs)",
                        "Call": "24hr coverage (12hrs)"
                    }
                    
                    # Build calendar grid: each slot gets its own row
                    # First, group assignments by shift type and date to find max slots
                    shift_type_order = ["Day", "Evening", "Night", "Call"]
                    calendar_data = []
                    
                    for shift_type in shift_type_order:
                        description = shift_info.get(shift_type, "")
                        
                        # Find the maximum number of slots for this shift type across all dates
                        max_slots = 0
                        for date in unique_dates:
                            shift_assignments = filtered_df[
                                (filtered_df['date'].dt.date == date) & 
                                (filtered_df['shift_type'] == shift_type)
                            ].copy()
                            max_slots = max(max_slots, len(shift_assignments))
                        
                        # Create a row for each slot
                        if max_slots == 0:
                            # If no shifts of this type exist, create one row showing dashes
                            row = {'Shift': shift_type, 'Slot': '-', 'Required': '-', 'Hours': description}
                            for date in unique_dates:
                                date_str = pd.to_datetime(date).strftime('%a\n%m/%d')
                                row[date_str] = '-'
                            calendar_data.append(row)
                        else:
                            for slot_num in range(1, max_slots + 1):
                                row = {'Shift': shift_type, 'Slot': slot_num, 'Required': '', 'Hours': description}
                                
                                for date in unique_dates:
                                    date_str = pd.to_datetime(date).strftime('%a\n%m/%d')
                                    
                                    # Get assignments for this shift type and date
                                    shift_assignments = filtered_df[
                                        (filtered_df['date'].dt.date == date) & 
                                        (filtered_df['shift_type'] == shift_type)
                                    ].copy()
                                    
                                    # Sort to ensure consistent slot ordering
                                    # Use id if available (from saved schedules), otherwise use shift_id, site, provider
                                    if 'id' in shift_assignments.columns and shift_assignments['id'].notna().all():
                                        shift_assignments = shift_assignments.sort_values('id')
                                    elif 'shift_id' in shift_assignments.columns:
                                        sort_cols = ['shift_id']
                                        if 'site' in shift_assignments.columns:
                                            sort_cols.append('site')
                                        if 'provider' in shift_assignments.columns:
                                            sort_cols.append('provider')
                                        shift_assignments = shift_assignments.sort_values(sort_cols)
                                    else:
                                        # Fallback: sort by site and provider
                                        sort_cols = []
                                        if 'site' in shift_assignments.columns:
                                            sort_cols.append('site')
                                        if 'provider' in shift_assignments.columns:
                                            sort_cols.append('provider')
                                        if sort_cols:
                                            shift_assignments = shift_assignments.sort_values(sort_cols)
                                    
                                    # Get provider for this specific slot (if exists)
                                    if len(shift_assignments) >= slot_num:
                                        assign = shift_assignments.iloc[slot_num - 1]
                                        provider = str(assign['provider'])
                                        is_unfilled = assign.get('is_unfilled', True)
                                        
                                        # Get required credentials from this assignment (same for all slots of same shift type)
                                        if not row['Required'] and 'required_credentials' in assign:
                                            creds = assign.get('required_credentials', [])
                                            if creds:
                                                row['Required'] = ', '.join(creds)
                                            else:
                                                row['Required'] = 'Any'
                                        
                                        if is_unfilled:
                                            row[date_str] = "UNFILLED"
                                        else:
                                            row[date_str] = provider
                                    else:
                                        row[date_str] = '-'
                                
                                # Ensure Required field is set
                                if not row['Required']:
                                    row['Required'] = 'Any'
                                
                                calendar_data.append(row)
                    
                    # Create DataFrame and display as table
                    calendar_df = pd.DataFrame(calendar_data)
                    
                    # Display the calendar grid
                    st.dataframe(
                        calendar_df,
                        width='stretch',
                        hide_index=True,
                        height=400
                    )
                    
                    # Legend explaining cell contents
                    st.caption("**Required:** Credentials needed for this shift type | **Cell Contents:** Provider name = Assigned | UNFILLED = Needs coverage | - = No shift this day")
                    
                    # Download button at the bottom
                    csv = assignments_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Full Schedule (CSV)",
                        data=csv,
                        file_name=f"{schedule_name}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
                else:
                    st.error("❌ Unable to create a complete schedule with the current providers and shifts.")
                    st.info("💡 Try adjusting the max hours per week, adding more providers, or reducing the number of shifts.")

with tab5:
    st.header("Edit Schedule")
    
    schedules = dm.get_all_schedules()
    if schedules:
        schedule_options = [f"{s['name']} (ID: {s['id']})" for s in schedules]
        selected_schedule_option = st.selectbox("Select Schedule to Edit", schedule_options)
        selected_schedule_id = int(selected_schedule_option.split("ID: ")[1].rstrip(")"))
        
        schedule = dm.get_schedule(selected_schedule_id)
        
        if schedule and schedule.get('assignments'):
            st.subheader("Manual Reassignments")
            
            assignments_df = pd.DataFrame(schedule['assignments'])
            st.dataframe(assignments_df, width='stretch', hide_index=True)
            
            st.subheader("Reassign Shift")
            assignment_options = [
                f"{a['date']} - {a['site']} {a['shift_type']} (Currently: {a['provider']})"
                for a in schedule['assignments']
            ]
            
            selected_assignment_str = st.selectbox("Select Shift to Reassign", assignment_options)
            selected_assignment_idx = assignment_options.index(selected_assignment_str)
            selected_assignment = schedule['assignments'][selected_assignment_idx]
            
            providers = dm.get_all_providers()
            provider_options = ["UNFILLED"] + [p['name'] for p in providers]
            
            current_provider = selected_assignment['provider']
            current_idx = provider_options.index(current_provider) if current_provider in provider_options else 0
            
            new_provider_name = st.selectbox("Assign to Provider", provider_options, index=current_idx)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Update Assignment"):
                    new_provider_id = None
                    if new_provider_name != "UNFILLED":
                        new_provider = next(p for p in providers if p['name'] == new_provider_name)
                        new_provider_id = new_provider['id']
                    
                    dm.update_assignment(selected_assignment['id'], new_provider_id, is_manual=True)
                    st.success(f"Assignment updated to {new_provider_name}")
                    st.rerun()
            
            with col2:
                if st.button("🔒 Lock This Shift"):
                    if new_provider_name != "UNFILLED":
                        new_provider = next(p for p in providers if p['name'] == new_provider_name)
                        dm.lock_shift(selected_assignment['shift_id'], new_provider['id'])
                        st.success(f"Shift locked to {new_provider_name}")
                        st.rerun()
            
            with col3:
                if st.button("🔓 Unlock Shift"):
                    dm.unlock_shift(selected_assignment['shift_id'])
                    st.success("Shift unlocked")
                    st.rerun()
            
            st.divider()
            st.subheader("Call-Out Management")
            
            with st.form("create_callout"):
                st.markdown("Report a provider calling out from their assigned shift")
                
                callout_assignment_str = st.selectbox(
                    "Select Assignment for Call-Out",
                    [f"{a['date']} - {a['site']} {a['shift_type']} - {a['provider']}" 
                     for a in schedule['assignments'] if not a['is_unfilled']]
                )
                
                reason = st.text_area("Reason for Call-Out")
                
                if st.form_submit_button("🚨 Submit Call-Out"):
                    assignment_idx = [f"{a['date']} - {a['site']} {a['shift_type']} - {a['provider']}" 
                                    for a in schedule['assignments'] if not a['is_unfilled']].index(callout_assignment_str)
                    callout_assignment = [a for a in schedule['assignments'] if not a['is_unfilled']][assignment_idx]
                    
                    dm.create_callout(
                        schedule_id=selected_schedule_id,
                        assignment_id=callout_assignment['id'],
                        provider_id=callout_assignment['provider_id'],
                        shift_id=callout_assignment['shift_id'],
                        reason=reason
                    )
                    
                    dm.update_assignment(callout_assignment['id'], None, is_manual=True)
                    
                    st.success("Call-out recorded and shift marked as unfilled")
                    st.info("💡 Tip: Use the 'Generate Schedule' tab to re-optimize with remaining providers")
                    st.rerun()
            
            pending_callouts = dm.get_pending_callouts(selected_schedule_id)
            if pending_callouts:
                st.subheader("Pending Call-Outs")
                callouts_df = pd.DataFrame(pending_callouts)
                st.dataframe(callouts_df, width='stretch', hide_index=True)
        else:
            st.info("This schedule has no assignments to edit")
    else:
        st.info("No schedules available to edit. Generate a schedule first.")

with tab6:
    st.header("Fairness Analytics")
    
    schedules = dm.get_all_schedules()
    if schedules:
        schedule_options = [f"{s['name']} (ID: {s['id']})" for s in schedules]
        selected_schedule_option = st.selectbox("Select Schedule for Analytics", schedule_options)
        selected_schedule_id = int(selected_schedule_option.split("ID: ")[1].rstrip(")"))
        
        schedule = dm.get_schedule(selected_schedule_id)
        
        if schedule and schedule.get('assignments'):
            assignments = [a for a in schedule['assignments'] if not a['is_unfilled']]
            
            if assignments:
                assignments_df = pd.DataFrame(assignments)
                
                st.subheader("Hours Distribution")
                hours_by_provider = assignments_df.groupby('provider')['hours'].sum().reset_index()
                hours_by_provider.columns = ['Provider', 'Total Hours']
                
                fig_hours = px.bar(
                    hours_by_provider,
                    x='Provider',
                    y='Total Hours',
                    title="Total Hours by Provider",
                    color='Total Hours',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_hours, width='stretch')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Shifts by Provider")
                    shifts_by_provider = assignments_df.groupby('provider').size().reset_index()
                    shifts_by_provider.columns = ['Provider', 'Shift Count']
                    
                    fig_shifts = px.pie(
                        shifts_by_provider,
                        values='Shift Count',
                        names='Provider',
                        title="Shift Distribution"
                    )
                    st.plotly_chart(fig_shifts, width='stretch')
                
                with col2:
                    st.subheader("Shift Types Distribution")
                    shift_type_dist = assignments_df.groupby('shift_type').size().reset_index()
                    shift_type_dist.columns = ['Shift Type', 'Count']
                    
                    fig_types = px.pie(
                        shift_type_dist,
                        values='Count',
                        names='Shift Type',
                        title="Shift Type Coverage"
                    )
                    st.plotly_chart(fig_types, width='stretch')
                
                st.subheader("Site Coverage")
                site_coverage = assignments_df.groupby(['site', 'provider']).size().reset_index()
                site_coverage.columns = ['Site', 'Provider', 'Shifts']
                
                fig_site = px.bar(
                    site_coverage,
                    x='Site',
                    y='Shifts',
                    color='Provider',
                    title="Provider Distribution Across Sites",
                    barmode='stack'
                )
                st.plotly_chart(fig_site, width='stretch')
                
                st.subheader("Detailed Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    avg_hours = hours_by_provider['Total Hours'].mean()
                    st.metric("Average Hours/Provider", f"{avg_hours:.1f}")
                
                with col2:
                    std_hours = hours_by_provider['Total Hours'].std()
                    st.metric("Hours Std Deviation", f"{std_hours:.1f}")
                
                with col3:
                    coverage_rate = len(assignments) / len(schedule['assignments']) * 100
                    st.metric("Coverage Rate", f"{coverage_rate:.1f}%")
            else:
                st.info("No assignments to analyze")
        else:
            st.info("This schedule has no assignments")
    else:
        st.info("Generate a schedule first to see analytics")

st.divider()
st.caption("Smart Anesthesia Scheduling Platform | Powered by Google OR-Tools")
