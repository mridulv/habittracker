import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import json
from collections import defaultdict
import requests
from github import Github
from github.InputFileContent import InputFileContent

# Set page configuration
st.set_page_config(page_title="Habit Tracker", layout="wide")

# GitHub Gist functionality
def initialize_github_connection():
    if 'github' not in st.session_state:
        if 'github_token' in st.session_state:
            try:
                st.session_state.github = Github(st.session_state.github_token)
                return True
            except Exception as e:
                st.error(f"Error connecting to GitHub: {e}")
                return False
        return False
    return True

def get_or_create_gist(filename, description="Habit Tracker Data"):
    """Get an existing gist or create a new one."""
    if not initialize_github_connection():
        return None
    
    # First, try to find an existing gist with our file
    user = st.session_state.github.get_user()
    
    for gist in user.get_gists():
        if filename in gist.files:
            return gist
    
    # If not found, create a new gist
    file_content = "{}"
    files = {filename: InputFileContent(file_content)}
    
    try:
        new_gist = user.create_gist(True, files, description)
        return new_gist
    except Exception as e:
        st.error(f"Error creating gist: {e}")
        return None

def load_from_gist(filename):
    """Load data from a GitHub Gist."""
    if not initialize_github_connection():
        return None
    
    gist = get_or_create_gist(filename)
    if gist:
        file_content = gist.files[filename].content
        return json.loads(file_content)
    
    return None

def save_to_gist(data, filename):
    """Save data to a GitHub Gist."""
    if not initialize_github_connection():
        return False
    
    gist = get_or_create_gist(filename)
    if gist:
        gist.edit(files={filename: InputFileContent(json.dumps(data, indent=2))})
        return True
    
    return False

# Function to load habits
def load_habits():
    if initialize_github_connection():
        habits = load_from_gist("habits.json")
        if habits:
            return habits
    
    # Default habits structure
    return {
        "daily": [],
        "weekly": [],
        "one_time": []
    }

# Function to save habits
def save_habits(habits):
    save_to_gist(habits, "habits.json")

# Function to load logs
def load_logs():
    if initialize_github_connection():
        logs = load_from_gist("logs.json")
        if logs:
            return logs
    
    return []

# Function to save logs
def save_logs(logs):
    save_to_gist(logs, "logs.json")

# Function to log a habit
def log_habit(habit_name, date, notes=""):
    logs = load_logs()
    logs.append({
        "habit": habit_name,
        "date": date,
        "notes": notes,
        "timestamp": datetime.datetime.now().isoformat()
    })
    save_logs(logs)

# GitHub authentication
if "github_token" not in st.session_state:
    st.sidebar.title("GitHub Authentication")
    st.sidebar.info("This app uses GitHub Gists to store your habit data. Please enter your GitHub Personal Access Token to continue.")
    st.sidebar.markdown("""
    To create a token:
    1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
    2. Generate a new token with 'gist' scope
    """)
    
    github_token = st.sidebar.text_input("GitHub Personal Access Token", type="password")
    
    if st.sidebar.button("Connect to GitHub"):
        if github_token:
            st.session_state.github_token = github_token
            try:
                # Test the connection
                g = Github(github_token)
                user = g.get_user()
                st.session_state.github = g
                st.sidebar.success(f"Connected to GitHub as {user.login}")
                st.experimental_rerun()
            except Exception as e:
                st.sidebar.error(f"Error connecting to GitHub: {e}")
        else:
            st.sidebar.error("Please enter a token")

# Initialize session state for habits and active tab
if 'habits' not in st.session_state and initialize_github_connection():
    st.session_state.habits = load_habits()

if not initialize_github_connection():
    st.warning("Please connect to GitHub using the sidebar to use this app.")
    st.stop()

# App header
st.title("Habit Tracker")

# Main navigation tabs
tabs = st.tabs(["Track", "Add Habits", "Analytics"])

# Track habits tab
with tabs[0]:
    st.header("Track Your Habits")
    
    # Get today's date
    today = datetime.date.today().isoformat()
    track_date = st.date_input("Date to track", datetime.date.today())
    date_str = track_date.isoformat()
    
    st.subheader("Daily Habits")
    if not st.session_state.habits["daily"]:
        st.info("No daily habits added yet. Go to 'Add Habits' tab to add some!")
    else:
        logs = load_logs()
        completed_today = {log["habit"] for log in logs if log["date"] == date_str}
        
        for habit in st.session_state.habits["daily"]:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(habit)
            with col2:
                if st.button("✓", key=f"daily_{habit}"):
                    log_habit(habit, date_str)
                    st.success(f"Logged {habit}")
                    st.experimental_rerun()
            
            # Show if already completed today
            if habit in completed_today:
                st.success("Completed today! ✓")
    
    st.subheader("Weekly Habits")
    if not st.session_state.habits["weekly"]:
        st.info("No weekly habits added yet. Go to 'Add Habits' tab to add some!")
    else:
        logs = load_logs()
        completed_this_week = set()
        
        # Get the start of the current week (Monday)
        today_date = datetime.date.fromisoformat(date_str)
        start_of_week = today_date - datetime.timedelta(days=today_date.weekday())
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        for log in logs:
            try:
                log_date = datetime.date.fromisoformat(log["date"])
                if start_of_week <= log_date <= end_of_week:
                    completed_this_week.add(log["habit"])
            except:
                pass
        
        for habit in st.session_state.habits["weekly"]:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(habit)
            with col2:
                if st.button("✓", key=f"weekly_{habit}"):
                    log_habit(habit, date_str)
                    st.success(f"Logged {habit}")
                    st.experimental_rerun()
            
            # Show if already completed this week
            if habit in completed_this_week:
                st.success("Completed this week! ✓")
                
    st.subheader("One-time Activities")
    if not st.session_state.habits["one_time"]:
        st.info("No one-time activities added yet. Go to 'Add Habits' tab to add some!")
    else:
        for activity in st.session_state.habits["one_time"]:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(activity)
            with col2:
                if st.button("✓", key=f"one_time_{activity}"):
                    log_habit(activity, date_str)
                    st.success(f"Logged {activity}")
                    st.experimental_rerun()
    
    # Add free-form tracking
    st.subheader("Track Something Else")
    with st.form("track_custom"):
        custom_activity = st.text_input("Activity name")
        custom_notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Track")
        
        if submitted and custom_activity:
            log_habit(custom_activity, date_str, custom_notes)
            st.success(f"Logged: {custom_activity}")
            st.experimental_rerun()

# Add habits tab
with tabs[1]:
    st.header("Add New Habits")
    
    # Add a new habit
    st.subheader("Add a New Habit")
    
    with st.form("add_habit"):
        new_habit = st.text_input("Habit name")
        habit_type = st.selectbox("Habit type", ["Daily", "Weekly", "One-time Activity"])
        submitted = st.form_submit_button("Add")
        
        if submitted and new_habit:
            habit_type_lower = habit_type.lower().replace("-", "_")
            if habit_type_lower == "daily":
                st.session_state.habits["daily"].append(new_habit)
            elif habit_type_lower == "weekly":
                st.session_state.habits["weekly"].append(new_habit)
            else:
                st.session_state.habits["one_time"].append(new_habit)
            
            save_habits(st.session_state.habits)
            st.success(f"Added {new_habit} as a {habit_type} habit!")
            st.experimental_rerun()
    
    # Display and manage current habits
    st.subheader("Current Habits")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Daily Habits**")
        for i, habit in enumerate(st.session_state.habits["daily"]):
            cols = st.columns([5, 1])
            cols[0].write(habit)
            if cols[1].button("🗑️", key=f"del_daily_{i}"):
                st.session_state.habits["daily"].pop(i)
                save_habits(st.session_state.habits)
                st.experimental_rerun()
    
    with col2:
        st.write("**Weekly Habits**")
        for i, habit in enumerate(st.session_state.habits["weekly"]):
            cols = st.columns([5, 1])
            cols[0].write(habit)
            if cols[1].button("🗑️", key=f"del_weekly_{i}"):
                st.session_state.habits["weekly"].pop(i)
                save_habits(st.session_state.habits)
                st.experimental_rerun()
    
    st.write("**One-time Activities**")
    for i, habit in enumerate(st.session_state.habits["one_time"]):
        cols = st.columns([5, 1])
        cols[0].write(habit)
        if cols[1].button("🗑️", key=f"del_onetime_{i}"):
            st.session_state.habits["one_time"].pop(i)
            save_habits(st.session_state.habits)
            st.experimental_rerun()

# Analytics tab
with tabs[2]:
    st.header("Habit Analytics")
    
    logs = load_logs()
    if not logs:
        st.info("No habit data recorded yet. Start tracking habits to see analytics!")
    else:
        # Convert logs to DataFrame for analysis
        logs_df = pd.DataFrame(logs)
        logs_df["date"] = pd.to_datetime(logs_df["date"])
        
        # Time period selection
        time_period = st.selectbox("View analytics for", ["Week", "Month", "Year", "All Time"])
        
        # Filter data based on time period
        today = datetime.datetime.now().date()
        if time_period == "Week":
            start_date = today - datetime.timedelta(days=today.weekday())
            filtered_df = logs_df[logs_df["date"] >= pd.Timestamp(start_date)]
            period_name = "This Week"
        elif time_period == "Month":
            start_date = datetime.date(today.year, today.month, 1)
            filtered_df = logs_df[logs_df["date"] >= pd.Timestamp(start_date)]
            period_name = "This Month"
        elif time_period == "Year":
            start_date = datetime.date(today.year, 1, 1)
            filtered_df = logs_df[logs_df["date"] >= pd.Timestamp(start_date)]
            period_name = "This Year"
        else:
            filtered_df = logs_df
            period_name = "All Time"
        
        # Count by habit
        if not filtered_df.empty:
            habit_counts = filtered_df["habit"].value_counts().reset_index()
            habit_counts.columns = ["Habit", "Completions"]
            
            # Show summary
            st.subheader(f"Summary for {period_name}")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Habits Tracked", len(habit_counts))
                
            with col2:
                st.metric("Total Completions", habit_counts["Completions"].sum())
            
            # Bar chart for habit completions
            st.subheader(f"Habit Completions ({period_name})")
            fig = px.bar(
                habit_counts.sort_values("Completions", ascending=False).head(10),
                x="Habit",
                y="Completions",
                color="Completions",
                color_continuous_scale="blues"
            )
            fig.update_layout(xaxis_title="Habit", yaxis_title="Number of Completions")
            st.plotly_chart(fig, use_container_width=True)
            
            # Streak analysis
            st.subheader("Habit Streaks & Consistency")
            
            # Get only habits that are daily
            daily_habits = st.session_state.habits["daily"]
            
            if daily_habits:
                # Filter for daily habits
                daily_logs = filtered_df[filtered_df["habit"].isin(daily_habits)]
                
                # Group by habit and date to get daily completions
                if not daily_logs.empty:
                    # Count completions per day per habit
                    daily_logs["date_only"] = daily_logs["date"].dt.date
                    daily_completions = daily_logs.groupby(["habit", "date_only"]).size().reset_index()
                    daily_completions.columns = ["Habit", "Date", "Count"]
                    
                    # Calculate consistency (days completed / total days in period)
                    habits_consistency = {}
                    date_range = pd.date_range(start=start_date, end=today)
                    
                    for habit in daily_habits:
                        habit_days = daily_completions[daily_completions["Habit"] == habit]["Date"].nunique()
                        consistency = (habit_days / len(date_range)) * 100 if len(date_range) > 0 else 0
                        habits_consistency[habit] = consistency
                    
                    # Display consistency
                    consistency_df = pd.DataFrame({
                        "Habit": list(habits_consistency.keys()),
                        "Consistency (%)": list(habits_consistency.values())
                    })
                    
                    fig = px.bar(
                        consistency_df.sort_values("Consistency (%)", ascending=False),
                        x="Habit",
                        y="Consistency (%)",
                        color="Consistency (%)",
                        color_continuous_scale="blues",
                        range_y=[0, 100]
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Calendar heatmap for selected habit
                    st.subheader("Habit Calendar")
                    selected_habit = st.selectbox("Select habit", daily_habits)
                    
                    habit_dates = daily_logs[daily_logs["habit"] == selected_habit]["date_only"].unique()
                    
                    # Create a dataframe for calendar heatmap
                    all_dates = pd.date_range(start=pd.Timestamp(start_date), end=pd.Timestamp(today))
                    calendar_df = pd.DataFrame({"date": all_dates})
                    calendar_df["day"] = calendar_df["date"].dt.day_name()
                    calendar_df["completed"] = calendar_df["date"].dt.date.isin(habit_dates).astype(int)
                    
                    # Display in a calendar-like format
                    fig = px.scatter(
                        calendar_df,
                        x=calendar_df["date"].dt.day_name(),
                        y=calendar_df["date"].dt.week,
                        color="completed",
                        color_continuous_scale=["white", "blue"],
                        title=f"Completion Calendar for {selected_habit}",
                        labels={"color": "Completed", "y": "Week", "x": "Day"}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data available for daily habits in the selected period.")
            else:
                st.info("No daily habits defined yet.")
            
            # Weekly habits analysis
            st.subheader("Weekly Habits Progress")
            weekly_habits = st.session_state.habits["weekly"]
            
            if weekly_habits:
                weekly_logs = filtered_df[filtered_df["habit"].isin(weekly_habits)]
                
                if not weekly_logs.empty:
                    # Group by habit and week
                    weekly_logs["week"] = weekly_logs["date"].dt.isocalendar().week
                    weekly_logs["year"] = weekly_logs["date"].dt.isocalendar().year
                    weekly_logs["year_week"] = weekly_logs["year"].astype(str) + "-W" + weekly_logs["week"].astype(str)
                    
                    # Count completions per week per habit
                    weekly_completions = weekly_logs.groupby(["habit", "year_week"]).size().reset_index()
                    weekly_completions.columns = ["Habit", "Week", "Count"]
                    
                    # Display weekly progress
                    pivot_weekly = weekly_completions.pivot(index="Habit", columns="Week", values="Count").fillna(0)
                    
                    st.table(pivot_weekly)
                else:
                    st.info("No data available for weekly habits in the selected period.")
            else:
                st.info("No weekly habits defined yet.")
        else:
            st.info(f"No habit data recorded for {period_name}.")

# Sidebar for settings and information
with st.sidebar:
    st.subheader("About")
    st.write("This habit tracker app allows you to track daily and weekly habits, as well as one-time activities.")
    st.write("Your data is stored in GitHub Gists, allowing you to access it from anywhere.")
    
    if initialize_github_connection():
        if st.button("Clear All Data"):
            if st.session_state.habits and (len(st.session_state.habits["daily"]) > 0 or 
                                          len(st.session_state.habits["weekly"]) > 0 or 
                                          len(st.session_state.habits["one_time"]) > 0):
                if st.button("Are you sure? This will delete all your habits and logs.", key="confirm_delete"):
                    # Reset data
                    st.session_state.habits = {"daily": [], "weekly": [], "one_time": []}
                    save_habits(st.session_state.habits)
                    save_logs([])
                    st.success("All data cleared!")
                    st.experimental_rerun()
            else:
                st.info("No data to clear.")
    
    st.subheader("Export Data")
    if initialize_github_connection():
        if st.button("Download Habit Data as JSON"):
            habits_json = json.dumps(st.session_state.habits, indent=2)
            st.download_button(
                label="Download Habits",
                data=habits_json,
                file_name="habits.json",
                mime="application/json"
            )
        
        if st.button("Download Logs as JSON"):
            logs = load_logs()
            logs_json = json.dumps(logs, indent=2)
            st.download_button(
                label="Download Logs",
                data=logs_json,
                file_name="logs.json",
                mime="application/json"
            )
