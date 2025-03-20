import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import os

# Set page config
st.set_page_config(page_title="Habit Tracker", layout="wide")

# Initialize session state variables if they don't exist
if 'habits' not in st.session_state:
    st.session_state.habits = []
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'activities' not in st.session_state:
    st.session_state.activities = []

# File operations for data persistence
DATA_DIR = "data"
HABITS_FILE = os.path.join(DATA_DIR, "habits.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
ACTIVITIES_FILE = os.path.join(DATA_DIR, "activities.json")

def save_data():
    """Save all data to JSON files"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(HABITS_FILE, 'w') as f:
        json.dump(st.session_state.habits, f)
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(st.session_state.logs, f)
        
    with open(ACTIVITIES_FILE, 'w') as f:
        json.dump(st.session_state.activities, f)

def load_data():
    """Load data from JSON files if they exist"""
    try:
        if os.path.exists(HABITS_FILE):
            with open(HABITS_FILE, 'r') as f:
                st.session_state.habits = json.load(f)
        
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r') as f:
                st.session_state.logs = json.load(f)
                
        if os.path.exists(ACTIVITIES_FILE):
            with open(ACTIVITIES_FILE, 'r') as f:
                st.session_state.activities = json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")

# Load data at startup
load_data()

# App title and sidebar
st.title("📊 Habit Tracker")

# Sidebar navigation
page = st.sidebar.selectbox("Select Page", ["Manage Habits", "Track Habits", "View Statistics", "One-time Activities"])

if page == "Manage Habits":
    st.header("Manage Your Habits")
    
    # Add new habit form
    with st.form("new_habit_form"):
        col1, col2 = st.columns(2)
        with col1:
            habit_name = st.text_input("Habit Name")
        with col2:
            frequency = st.selectbox("Frequency", ["Daily", "Weekly"])
        
        description = st.text_area("Description (Optional)")
        
        submit_button = st.form_submit_button("Add Habit")
        
        if submit_button and habit_name:
            # Check if habit already exists
            if any(h["name"] == habit_name for h in st.session_state.habits):
                st.error(f"Habit '{habit_name}' already exists!")
            else:
                new_habit = {
                    "id": len(st.session_state.habits) + 1,
                    "name": habit_name,
                    "frequency": frequency,
                    "description": description,
                    "created_at": datetime.now().strftime("%Y-%m-%d")
                }
                st.session_state.habits.append(new_habit)
                save_data()
                st.success(f"Habit '{habit_name}' added successfully!")
    
    # Display existing habits
    if st.session_state.habits:
        st.subheader("Your Habits")
        habit_df = pd.DataFrame(st.session_state.habits)
        
        # Format for display
        display_cols = ["name", "frequency", "description", "created_at"]
        habit_df = habit_df[display_cols].rename(columns={
            "name": "Habit Name",
            "frequency": "Frequency",
            "description": "Description",
            "created_at": "Created At"
        })
        
        st.dataframe(habit_df, use_container_width=True)
        
        # Delete habit functionality
        habit_to_delete = st.selectbox("Select habit to delete", 
                                      [h["name"] for h in st.session_state.habits],
                                      index=None)
        if st.button("Delete Selected Habit") and habit_to_delete:
            # Remove the habit
            habit_id = next((h["id"] for h in st.session_state.habits if h["name"] == habit_to_delete), None)
            st.session_state.habits = [h for h in st.session_state.habits if h["name"] != habit_to_delete]
            
            # Remove associated logs
            if habit_id:
                st.session_state.logs = [log for log in st.session_state.logs if log["habit_id"] != habit_id]
            
            save_data()
            st.success(f"Habit '{habit_to_delete}' deleted successfully!")
            st.experimental_rerun()
    else:
        st.info("No habits added yet. Add your first habit using the form above.")

elif page == "Track Habits":
    st.header("Track Your Habits")
    
    if not st.session_state.habits:
        st.info("No habits to track. Please add habits first.")
    else:
        # Current date for tracking
        today = datetime.now().strftime("%Y-%m-%d")
        
        st.subheader(f"Track for {today}")
        
        # Filter habits based on frequency and today's day
        day_of_week = datetime.now().weekday()  # Monday is 0, Sunday is 6
        
        daily_habits = [h for h in st.session_state.habits if h["frequency"] == "Daily"]
        weekly_habits = [h for h in st.session_state.habits if h["frequency"] == "Weekly"]
        
        # Daily habits tracking
        if daily_habits:
            st.write("### Daily Habits")
            
            # Check for existing logs today for each habit
            for habit in daily_habits:
                habit_id = habit["id"]
                habit_name = habit["name"]
                
                # Check if already logged today
                already_logged = any(
                    log["habit_id"] == habit_id and log["date"] == today 
                    for log in st.session_state.logs
                )
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{habit_name}**")
                
                with col2:
                    if already_logged:
                        st.success("Completed")
                    else:
                        st.error("Not Completed")
                
                with col3:
                    # Allow toggling completion status
                    if st.button("Toggle", key=f"toggle_{habit_id}"):
                        if already_logged:
                            # Remove the log
                            st.session_state.logs = [
                                log for log in st.session_state.logs 
                                if not (log["habit_id"] == habit_id and log["date"] == today)
                            ]
                        else:
                            # Add new log
                            new_log = {
                                "id": len(st.session_state.logs) + 1,
                                "habit_id": habit_id,
                                "date": today,
                                "completed": True
                            }
                            st.session_state.logs.append(new_log)
                        
                        save_data()
                        st.experimental_rerun()
        
        # Weekly habits tracking
        if weekly_habits:
            st.write("### Weekly Habits")
            
            for habit in weekly_habits:
                habit_id = habit["id"]
                habit_name = habit["name"]
                
                # Check for logs in the current week
                current_week_start = (datetime.now() - timedelta(days=day_of_week)).strftime("%Y-%m-%d")
                current_week_end = (datetime.now() + timedelta(days=6-day_of_week)).strftime("%Y-%m-%d")
                
                already_logged_this_week = any(
                    log["habit_id"] == habit_id and 
                    current_week_start <= log["date"] <= current_week_end
                    for log in st.session_state.logs
                )
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{habit_name}**")
                
                with col2:
                    if already_logged_this_week:
                        st.success("Completed this week")
                    else:
                        st.error("Not completed this week")
                
                with col3:
                    if st.button("Toggle", key=f"toggle_weekly_{habit_id}"):
                        if already_logged_this_week:
                            # Remove the log from this week
                            st.session_state.logs = [
                                log for log in st.session_state.logs 
                                if not (log["habit_id"] == habit_id and 
                                       current_week_start <= log["date"] <= current_week_end)
                            ]
                        else:
                            # Add new log for today
                            new_log = {
                                "id": len(st.session_state.logs) + 1,
                                "habit_id": habit_id,
                                "date": today,
                                "completed": True
                            }
                            st.session_state.logs.append(new_log)
                        
                        save_data()
                        st.experimental_rerun()

elif page == "View Statistics":
    st.header("Habit Statistics")
    
    if not st.session_state.habits or not st.session_state.logs:
        st.info("No data to analyze yet. Start tracking your habits first!")
    else:
        # Time period selector
        period = st.selectbox("Select Time Period", ["Week", "Month", "Year", "All Time"])
        
        # Calculate date ranges based on selected period
        today = datetime.now()
        
        if period == "Week":
            start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
            end_date = (today + timedelta(days=6-today.weekday())).strftime("%Y-%m-%d")
            title = f"This Week ({start_date} to {end_date})"
        elif period == "Month":
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            # Last day of current month
            if today.month == 12:
                last_day = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = today.replace(month=today.month+1, day=1) - timedelta(days=1)
            end_date = last_day.strftime("%Y-%m-%d")
            title = f"This Month ({start_date} to {end_date})"
        elif period == "Year":
            start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = today.replace(month=12, day=31).strftime("%Y-%m-%d")
            title = f"This Year ({start_date} to {end_date})"
        else:  # All Time
            start_date = "2000-01-01"  # Arbitrary past date
            end_date = "2099-12-31"    # Arbitrary future date
            title = "All Time"
        
        # Convert logs to DataFrame for analysis
        logs_df = pd.DataFrame(st.session_state.logs)
        
        if not logs_df.empty:
            # Filter logs by date range
            filtered_logs = logs_df[
                (logs_df["date"] >= start_date) & 
                (logs_df["date"] <= end_date)
            ]
            
            habits_df = pd.DataFrame(st.session_state.habits)
            
            # Join habits with logs to get habit names
            if not filtered_logs.empty and not habits_df.empty:
                # Count completions by habit
                habit_counts = filtered_logs["habit_id"].value_counts().reset_index()
                habit_counts.columns = ["habit_id", "completions"]
                
                # Merge with habit names
                habit_stats = pd.merge(
                    habit_counts, 
                    habits_df[["id", "name", "frequency"]], 
                    left_on="habit_id", 
                    right_on="id",
                    how="left"
                )
                
                # Display summary statistics
                st.subheader(f"Habit Completion Summary - {title}")
                
                # Bar chart of completions
                fig = px.bar(
                    habit_stats, 
                    x="name", 
                    y="completions",
                    color="frequency",
                    title="Habit Completions",
                    labels={"name": "Habit", "completions": "Number of Completions", "frequency": "Frequency"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table with stats
                st.subheader("Detailed Statistics")
                
                # Calculate streak for each habit
                habit_streaks = {}
                for habit in st.session_state.habits:
                    habit_id = habit["id"]
                    habit_logs = logs_df[logs_df["habit_id"] == habit_id].sort_values("date")
                    
                    if not habit_logs.empty:
                        # Calculate current streak
                        dates = pd.to_datetime(habit_logs["date"])
                        
                        # For daily habits
                        if habit["frequency"] == "Daily":
                            # Convert to datetime for date math
                            dates = pd.to_datetime(habit_logs["date"])
                            
                            # Check if there's a log for today
                            has_today = datetime.now().strftime("%Y-%m-%d") in habit_logs["date"].values
                            
                            if has_today:
                                # Count backwards from today
                                streak = 1
                                current_date = datetime.now().date()
                                
                                while True:
                                    prev_date = (current_date - timedelta(days=1))
                                    prev_date_str = prev_date.strftime("%Y-%m-%d")
                                    
                                    if prev_date_str in habit_logs["date"].values:
                                        streak += 1
                                        current_date = prev_date
                                    else:
                                        break
                                
                                habit_streaks[habit_id] = streak
                            else:
                                habit_streaks[habit_id] = 0
                        
                        # For weekly habits - simplified streak calculation
                        else:
                            # Check if completed this week
                            today = datetime.now()
                            week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
                            completed_this_week = any(date >= week_start for date in habit_logs["date"])
                            
                            if completed_this_week:
                                # Count consecutive weeks (simplified)
                                habit_streaks[habit_id] = 1
                                # More complex streak logic could be implemented here
                            else:
                                habit_streaks[habit_id] = 0
                    else:
                        habit_streaks[habit_id] = 0
                
                # Add streaks to stats table
                stats_table = habit_stats.copy()
                stats_table["streak"] = stats_table["habit_id"].map(habit_streaks)
                
                # Format table for display
                display_stats = stats_table[["name", "frequency", "completions", "streak"]]
                display_stats.columns = ["Habit", "Frequency", "Completions", "Current Streak"]
                
                st.dataframe(display_stats, use_container_width=True)
                
                # Calendar heatmap for selected habit
                st.subheader("Habit Calendar")
                selected_habit = st.selectbox(
                    "Select habit to view calendar", 
                    [(h["id"], h["name"]) for h in st.session_state.habits],
                    format_func=lambda x: x[1]
                )
                
                if selected_habit:
                    habit_id, habit_name = selected_habit
                    
                    # Get all logs for this habit
                    habit_logs = logs_df[logs_df["habit_id"] == habit_id]
                    
                    if not habit_logs.empty:
                        # Convert dates to datetime for calendar
                        habit_logs["date"] = pd.to_datetime(habit_logs["date"])
                        
                        # Group by date and count
                        calendar_data = habit_logs.groupby(habit_logs["date"].dt.date).size().reset_index()
                        calendar_data.columns = ["date", "count"]
                        
                        # Create calendar heatmap
                        fig = px.scatter(
                            calendar_data,
                            x=calendar_data["date"],
                            y=[1] * len(calendar_data),  # Constant y value for all points
                            size="count",
                            color_discrete_sequence=["green"],
                            title=f"Calendar for '{habit_name}'",
                            labels={"x": "Date", "y": ""}
                        )
                        
                        # Update layout
                        fig.update_layout(
                            yaxis=dict(
                                showticklabels=False,
                                showgrid=False,
                            ),
                            height=200
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No data available for '{habit_name}'")
            else:
                st.info(f"No data available for the selected period ({title})")
        else:
            st.info("No logs available yet. Start tracking your habits!")

elif page == "One-time Activities":
    st.header("One-time Activities")
    
    # Add one-time activity
    with st.form("new_activity_form"):
        activity_name = st.text_input("Activity Name")
        activity_date = st.date_input("Date Completed", value=datetime.now())
        notes = st.text_area("Notes (Optional)")
        
        submit_button = st.form_submit_button("Add Activity")
        
        if submit_button and activity_name:
            new_activity = {
                "id": len(st.session_state.activities) + 1,
                "name": activity_name,
                "date": activity_date.strftime("%Y-%m-%d"),
                "notes": notes
            }
            st.session_state.activities.append(new_activity)
            save_data()
            st.success(f"Activity '{activity_name}' added successfully!")
    
    # Display activities
    if st.session_state.activities:
        st.subheader("Your Activities")
        
        # Convert to DataFrame for easier display
        activities_df = pd.DataFrame(st.session_state.activities)
        
        # Sort by date (most recent first)
        activities_df["date"] = pd.to_datetime(activities_df["date"])
        activities_df = activities_df.sort_values("date", ascending=False)
        
        # Format for display
        display_df = activities_df[["name", "date", "notes"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df.columns = ["Activity", "Date", "Notes"]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Delete activity
        activity_to_delete = st.selectbox(
            "Select activity to delete", 
            [(a["id"], a["name"]) for a in st.session_state.activities],
            format_func=lambda x: x[1],
            index=None
        )
        
        if st.button("Delete Selected Activity") and activity_to_delete:
            activity_id = activity_to_delete[0]
            st.session_state.activities = [a for a in st.session_state.activities if a["id"] != activity_id]
            save_data()
            st.success(f"Activity '{activity_to_delete[1]}' deleted successfully!")
            st.experimental_rerun()
    else:
        st.info("No activities added yet. Add your first activity using the form above.")
