import streamlit as st
import pandas as pd
import json
import os
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import calendar
import numpy as np
from models import Habit, HabitLog, DailyHabitLog, WeeklyHabitLog
import uuid
import requests

# Set page configuration
st.set_page_config(page_title="Habit Tracker", layout="wide")

# Initialize session state variables if they don't exist
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Track Habits"

# GitHub Gist functions
def get_github_token():
    return st.secrets["github_token"]

def create_or_update_gist(filename, content, gist_id=None, description="Habit Tracker Data"):
    """Create a new gist or update an existing one"""
    token = get_github_token()
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    files = {filename: {"content": json.dumps(content, indent=2)}}
    
    if gist_id:
        # Update existing gist
        url = f"https://api.github.com/gists/{gist_id}"
        response = requests.patch(url, headers=headers, json={"files": files})
    else:
        # Create new gist
        url = "https://api.github.com/gists"
        response = requests.post(
            url, 
            headers=headers, 
            json={
                "description": description,
                "public": False,
                "files": files
            }
        )
    
    if response.status_code in [200, 201]:
        return response.json()["id"]
    else:
        st.error(f"Error with GitHub API: {response.status_code} - {response.text}")
        return None

def get_gist_content(gist_id, filename):
    """Get content from a specific file in a gist"""
    token = get_github_token()
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f"https://api.github.com/gists/{gist_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        gist_data = response.json()
        if filename in gist_data["files"]:
            file_content = gist_data["files"][filename]["content"]
            try:
                return json.loads(file_content)
            except json.JSONDecodeError:
                return None
    return None

# Function to convert model objects to dictionaries for JSON serialization
def model_to_dict(obj):
    if isinstance(obj, Habit):
        return {
            "id": obj.id if hasattr(obj, 'id') else str(uuid.uuid4()),
            "name": obj.name,
            "type": obj.type,
            "created_at": obj.created_at if hasattr(obj, 'created_at') else datetime.now().strftime("%Y-%m-%d")
        }
    elif isinstance(obj, HabitLog):
        return {
            "habit": obj.habit,
            "completed": obj.completed
        }
    elif isinstance(obj, DailyHabitLog):
        return {
            "date": obj.date.strftime("%Y-%m-%d") if isinstance(obj.date, datetime) else obj.date,
            "habits": [model_to_dict(h) for h in obj.habits]
        }
    elif isinstance(obj, WeeklyHabitLog):
        return {
            "week": obj.week,
            "habits": [model_to_dict(h) for h in obj.habits]
        }
    return obj

# Function to convert dictionaries back to model objects
def dict_to_model(data, model_type):
    if model_type == Habit:
        habit = Habit(name=data["name"], type=data["type"])
        habit.id = data.get("id", str(uuid.uuid4()))
        habit.created_at = data.get("created_at", datetime.now().strftime("%Y-%m-%d"))
        return habit
    elif model_type == HabitLog:
        return HabitLog(habit=data["habit"], completed=data["completed"])
    elif model_type == DailyHabitLog:
        date = data["date"]
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")
        return DailyHabitLog(
            date=date,
            habits=[dict_to_model(h, HabitLog) for h in data["habits"]]
        )
    elif model_type == WeeklyHabitLog:
        return WeeklyHabitLog(
            week=data["week"],
            habits=[dict_to_model(h, HabitLog) for h in data["habits"]]
        )
    return data

# Initialize or load gist IDs from session state
if 'gist_ids' not in st.session_state:
    st.session_state.gist_ids = {
        'habits': None,
        'daily_logs': None,
        'weekly_logs': None,
        'completed_activities': None
    }

# Function to load data from GitHub Gist or local file
def load_data(file_path, model_type=None, default_data=None, gist_key=None):
    if default_data is None:
        default_data = [] if isinstance(default_data, list) else {}
    
    # Try to load from GitHub Gist first if we have a gist ID
    if gist_key and st.session_state.gist_ids.get(gist_key):
        gist_id = st.session_state.gist_ids[gist_key]
        filename = os.path.basename(file_path)
        gist_data = get_gist_content(gist_id, filename)
        
        if gist_data is not None:
            if model_type:
                if isinstance(gist_data, list):
                    return [dict_to_model(item, model_type) for item in gist_data]
                elif isinstance(gist_data, dict):
                    result = {}
                    for key, value in gist_data.items():
                        if model_type == DailyHabitLog or model_type == WeeklyHabitLog:
                            habits = [dict_to_model(h, HabitLog) for h in value]
                            result[key] = habits
                        else:
                            result[key] = value
                    return result
            return gist_data
    
    # Fall back to local file if gist loading failed
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                if model_type:
                    if isinstance(data, list):
                        return [dict_to_model(item, model_type) for item in data]
                    elif isinstance(data, dict):
                        result = {}
                        for key, value in data.items():
                            if model_type == DailyHabitLog or model_type == WeeklyHabitLog:
                                habits = [dict_to_model(h, HabitLog) for h in value]
                                result[key] = habits
                            else:
                                result[key] = value
                        return result
                return data
        except json.JSONDecodeError:
            return default_data
    else:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # Create the file with default data
        with open(file_path, 'w') as file:
            json.dump(default_data, file)
        return default_data

# Function to save data to GitHub Gist and local file
def save_data(data, file_path, gist_key=None):
    # Save to local file first
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Convert model objects to dictionaries for JSON serialization
    if isinstance(data, list):
        serialized_data = [model_to_dict(item) if hasattr(item, '__dict__') else item for item in data]
    elif isinstance(data, dict):
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                serialized_data[key] = [model_to_dict(item) if hasattr(item, '__dict__') else item for item in value]
            else:
                serialized_data[key] = model_to_dict(value) if hasattr(value, '__dict__') else value
    else:
        serialized_data = model_to_dict(data) if hasattr(data, '__dict__') else data
    
    # Save to local file
    with open(file_path, 'w') as file:
        json.dump(serialized_data, file)
    
    # Save to GitHub Gist if gist_key is provided
    if gist_key:
        filename = os.path.basename(file_path)
        gist_id = st.session_state.gist_ids.get(gist_key)
        new_gist_id = create_or_update_gist(filename, serialized_data, gist_id)
        
        if new_gist_id:
            st.session_state.gist_ids[gist_key] = new_gist_id

# File paths
habits_file = "data/habits.json"
daily_logs_file = "data/daily_logs.json"
weekly_logs_file = "data/weekly_logs.json"
completed_activities_file = "data/completed_activities.json"

# Load data
habits = load_data(habits_file, Habit, [], 'habits')
daily_logs = load_data(daily_logs_file, DailyHabitLog, {}, 'daily_logs')
weekly_logs = load_data(weekly_logs_file, WeeklyHabitLog, {}, 'weekly_logs')
completed_activities = load_data(completed_activities_file, None, [], 'completed_activities')

# Main title
st.title("Habit Tracker")

# Create tabs for different sections
tabs = ["Track Habits", "Add Habits", "Analytics"]
selected_tab = st.radio("Navigation", tabs, index=tabs.index(st.session_state.current_tab))
st.session_state.current_tab = selected_tab

# Section 1: Track Habits
if selected_tab == "Track Habits":
    st.header("Track Your Habits")
    
    # Get current date
    today = datetime.now().strftime("%Y-%m-%d")
    current_week = datetime.now().strftime("%Y-W%U")
    
    # Create two columns for daily and weekly habits
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Daily Habits")
        daily_habits = [habit for habit in habits if habit.type == "daily"]
        
        if not daily_habits:
            st.info("No daily habits added yet. Go to 'Add Habits' to create some!")
        
        for habit in daily_habits:
            # Check if habit was completed today
            is_completed = False
            if today in daily_logs:
                for log in daily_logs[today]:
                    if log.habit == habit.id:
                        is_completed = log.completed
            
            # Create checkbox for habit
            if st.checkbox(habit.name, value=is_completed, key=f"daily_{habit.id}"):
                # If checked, add to completed
                if today not in daily_logs:
                    daily_logs[today] = []
                
                # Check if habit already exists in logs
                habit_exists = False
                for log in daily_logs[today]:
                    if log.habit == habit.id:
                        log.completed = True
                        habit_exists = True
                        break
                
                if not habit_exists:
                    daily_logs[today].append(HabitLog(habit=habit.id, completed=True))
                    
                    # Add to completed activities for analytics
                    completed_activities.append({
                        "habit_id": habit.id,
                        "date": today,
                        "type": "daily"
                    })
            else:
                # If unchecked, mark as not completed
                if today in daily_logs:
                    for log in daily_logs[today]:
                        if log.habit == habit.id:
                            log.completed = False
                            break
                    
                    # Remove from completed activities
                    completed_activities = [act for act in completed_activities 
                                           if not (act["habit_id"] == habit.id and act["date"] == today)]
    
    with col2:
        st.subheader("Weekly Habits")
        weekly_habits = [habit for habit in habits if habit.type == "weekly"]
        
        if not weekly_habits:
            st.info("No weekly habits added yet. Go to 'Add Habits' to create some!")
        
        for habit in weekly_habits:
            # Check if habit was completed this week
            is_completed = False
            if current_week in weekly_logs:
                for log in weekly_logs[current_week]:
                    if log.habit == habit.id:
                        is_completed = log.completed
            
            # Create checkbox for habit
            if st.checkbox(habit.name, value=is_completed, key=f"weekly_{habit.id}"):
                # If checked, add to completed
                if current_week not in weekly_logs:
                    weekly_logs[current_week] = []
                
                # Check if habit already exists in logs
                habit_exists = False
                for log in weekly_logs[current_week]:
                    if log.habit == habit.id:
                        log.completed = True
                        habit_exists = True
                        break
                
                if not habit_exists:
                    weekly_logs[current_week].append(HabitLog(habit=habit.id, completed=True))
                    
                    # Add to completed activities for analytics
                    completed_activities.append({
                        "habit_id": habit.id,
                        "date": today,
                        "type": "weekly"
                    })
            else:
                # If unchecked, mark as not completed
                if current_week in weekly_logs:
                    for log in weekly_logs[current_week]:
                        if log.habit == habit.id:
                            log.completed = False
                            break
                    
                    # Remove from completed activities
                    completed_activities = [act for act in completed_activities 
                                           if not (act["habit_id"] == habit.id and act["date"] == today and act["type"] == "weekly")]
    
    # Save data after changes
    save_data(daily_logs, daily_logs_file, 'daily_logs')
    save_data(weekly_logs, weekly_logs_file, 'weekly_logs')
    save_data(completed_activities, completed_activities_file, 'completed_activities')

# Section 2: Add Habits
elif selected_tab == "Add Habits":
    st.header("Add New Habits")
    
    # Form for adding new habits
    with st.form("add_habit_form"):
        habit_name = st.text_input("Habit Name")
        habit_type = st.selectbox("Frequency", ["daily", "weekly"])
        
        submitted = st.form_submit_button("Add Habit")
        
        if submitted and habit_name:
            # Create new habit
            new_habit = Habit(name=habit_name, type=habit_type)
            new_habit.id = str(uuid.uuid4())
            new_habit.created_at = datetime.now().strftime("%Y-%m-%d")
            
            # Add to habits list
            habits.append(new_habit)
            
            # Save updated habits
            save_data(habits, habits_file, 'habits')
            
            st.success(f"Habit '{habit_name}' added successfully!")
    
    # Display existing habits with delete option
    st.subheader("Existing Habits")
    
    if not habits:
        st.info("No habits added yet.")
    else:
        # Create two columns for daily and weekly habits
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Daily Habits")
            daily_habits = [habit for habit in habits if habit.type == "daily"]
            
            if not daily_habits:
                st.write("No daily habits added yet.")
            
            for habit in daily_habits:
                col1a, col1b = st.columns([3, 1])
                with col1a:
                    st.write(f"**{habit.name}**")
                with col1b:
                    if st.button("Delete", key=f"del_daily_{habit.id}"):
                        habits.remove(habit)
                        save_data(habits, habits_file, 'habits')
                        st.experimental_rerun()
                st.divider()
        
        with col2:
            st.write("Weekly Habits")
            weekly_habits = [habit for habit in habits if habit.type == "weekly"]
            
            if not weekly_habits:
                st.write("No weekly habits added yet.")
            
            for habit in weekly_habits:
                col2a, col2b = st.columns([3, 1])
                with col2a:
                    st.write(f"**{habit.name}**")
                with col2b:
                    if st.button("Delete", key=f"del_weekly_{habit.id}"):
                        habits.remove(habit)
                        save_data(habits, habits_file, 'habits')
                        st.experimental_rerun()
                st.divider()

# Section 3: Analytics
elif selected_tab == "Analytics":
    st.header("Habit Analytics")
    
    if not habits:
        st.info("No habits to analyze. Add some habits first!")
    else:
        # Get habit completion data for the last 4 weeks
        end_date = datetime.now()
        start_date = end_date - timedelta(days=28)  # 4 weeks
        
        # Create date range for the last 4 weeks
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        # Select habit for analysis
        habit_options = [(habit.id, habit.name) for habit in habits]
        selected_habit_id = st.selectbox(
            "Select Habit to Analyze",
            options=[opt[0] for opt in habit_options],
            format_func=lambda x: next((opt[1] for opt in habit_options if opt[0] == x), x)
        )
        
        selected_habit = next((h for h in habits if h.id == selected_habit_id), None)
        
        if selected_habit:
            st.subheader(f"Analytics for: {selected_habit.name}")
            
            # Determine if it's a daily or weekly habit
            is_daily = selected_habit.type == "daily"
            
            if is_daily:
                # Create data for daily habit
                completion_data = []
                for date in date_range:
                    is_completed = False
                    if date in daily_logs:
                        for log in daily_logs[date]:
                            if log.habit == selected_habit_id and log.completed:
                                is_completed = True
                                break
                    completion_data.append({"date": date, "completed": is_completed})
                
                # Convert to DataFrame for easier manipulation
                df = pd.DataFrame(completion_data)
                df["date"] = pd.to_datetime(df["date"])
                df["week"] = df["date"].dt.strftime("%U")
                df["day"] = df["date"].dt.strftime("%a")
                df["day_num"] = df["date"].dt.dayofweek
                df["completed_int"] = df["completed"].astype(int)
                
                # Create metrics for quick stats
                total_days = len(df)
                completed_days = df["completed_int"].sum()
                completion_percentage = (completed_days / total_days) * 100 if total_days > 0 else 0
                
                # Display metrics in a row
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Days Tracked", f"{total_days} days")
                with col2:
                    st.metric("Days Completed", f"{completed_days} days")
                with col3:
                    st.metric("Overall Completion", f"{completion_percentage:.1f}%")
                
                # Group by week and calculate completion rate
                weekly_completion = df.groupby("week")["completed"].mean() * 100
                
                # Create a more visually appealing weekly completion chart
                st.subheader("Weekly Completion Rate")
                
                # Use Streamlit's native chart capabilities for better interactivity
                weekly_df = pd.DataFrame({
                    "Week": [f"Week {w}" for w in weekly_completion.index],
                    "Completion Rate (%)": weekly_completion.values
                })
                
                # Create a bar chart with Streamlit
                st.bar_chart(weekly_df.set_index("Week"))
                
                # Create a daily view
                st.subheader("Daily Completion")
                
                # Create a more detailed daily view
                # Group by day of week to see patterns
                day_of_week_completion = df.groupby("day")["completed_int"].mean() * 100
                
                # Reorder days to start with Monday
                days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_of_week_completion = day_of_week_completion.reindex(days_order)
                
                day_df = pd.DataFrame({
                    "Day": day_of_week_completion.index,
                    "Completion Rate (%)": day_of_week_completion.values
                })
                
                # Create a bar chart for day of week patterns
                st.bar_chart(day_df.set_index("Day"))
                
                # Create a calendar heatmap view
                st.subheader("Calendar View")
                
                # Create a more visually appealing heatmap
                # Pivot data for heatmap
                pivot_df = df.pivot_table(
                    index=df["date"].dt.strftime("%U"),  # Week number
                    columns=df["date"].dt.strftime("%a"),  # Day name
                    values="completed_int",
                    aggfunc="first"
                )
                
                # Reorder columns to start with Monday
                pivot_df = pivot_df.reindex(columns=days_order)
                
                # Create a custom colormap
                fig, ax = plt.subplots(figsize=(10, 6))
                cmap = plt.cm.get_cmap("RdYlGn")
                
                # Create a more visually appealing heatmap
                heatmap = ax.pcolor(pivot_df, cmap=cmap, vmin=0, vmax=1, edgecolors='w', linewidths=2)
                
                # Set labels
                ax.set_xticks(np.arange(len(pivot_df.columns)) + 0.5)
                ax.set_yticks(np.arange(len(pivot_df.index)) + 0.5)
                ax.set_xticklabels(pivot_df.columns, fontweight='bold')
                ax.set_yticklabels([f"Week {w}" for w in pivot_df.index], fontweight='bold')
                
                # Rotate the tick labels and set alignment
                plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
                plt.setp(ax.get_yticklabels(), rotation=0, ha="right")
                
                # Add a title
                ax.set_title(f"Daily Completion for {selected_habit.name}", fontsize=16, fontweight='bold', pad=20)
                
                # Add colorbar
                cbar = plt.colorbar(heatmap)
                cbar.set_ticks([0.25, 0.75])
                cbar.set_ticklabels(["Not Completed", "Completed"])
                
                # Improve the appearance
                fig.tight_layout()
                
                # Display the heatmap
                st.pyplot(fig)
                
                # Calculate and display streak information
                st.subheader("Streak Information")
                
                # Calculate current streak
                current_streak = 0
                for entry in reversed(completion_data):
                    if entry["completed"]:
                        current_streak += 1
                    else:
                        break
                
                # Calculate longest streak
                longest_streak = 0
                current = 0
                for entry in completion_data:
                    if entry["completed"]:
                        current += 1
                        longest_streak = max(longest_streak, current)
                    else:
                        current = 0
                
                # Display streak metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Current Streak", f"{current_streak} days")
                with col2:
                    st.metric("Longest Streak", f"{longest_streak} days")
                
                # Create a line chart showing the streak over time
                streak_data = []
                current = 0
                for entry in completion_data:
                    if entry["completed"]:
                        current += 1
                    else:
                        current = 0
                    streak_data.append({"date": entry["date"], "streak": current})
                
                streak_df = pd.DataFrame(streak_data)
                streak_df["date"] = pd.to_datetime(streak_df["date"])
                
                # Create a line chart for streak visualization
                st.subheader("Streak Over Time")
                
                # Format for display
                streak_chart_df = pd.DataFrame({
                    "Date": streak_df["date"],
                    "Streak (days)": streak_df["streak"]
                }).set_index("Date")
                
                st.line_chart(streak_chart_df)
                
            else:  # Weekly habit
                # Get weeks in the date range
                weeks = []
                for date in date_range:
                    week = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-W%U")
                    if week not in weeks:
                        weeks.append(week)
                
                # Create data for weekly habit
                completion_data = []
                for week in weeks:
                    is_completed = False
                    if week in weekly_logs:
                        for log in weekly_logs[week]:
                            if log.habit == selected_habit_id and log.completed:
                                is_completed = True
                                break
                    completion_data.append({"week": week, "completed": is_completed})
                
                # Convert to DataFrame
                df = pd.DataFrame(completion_data)
                df["completed_int"] = df["completed"].astype(int)
                df["week_num"] = [w.split("-W")[1] for w in df["week"]]
                df["week_label"] = [f"Week {w}" for w in df["week_num"]]
                
                # Create metrics for quick stats
                total_weeks = len(df)
                completed_weeks = df["completed_int"].sum()
                completion_percentage = (completed_weeks / total_weeks) * 100 if total_weeks > 0 else 0
                
                # Display metrics in a row
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Weeks Tracked", f"{total_weeks} weeks")
                with col2:
                    st.metric("Weeks Completed", f"{completed_weeks} weeks")
                with col3:
                    st.metric("Overall Completion", f"{completion_percentage:.1f}%")
                
                # Create a more visually appealing weekly completion chart
                st.subheader("Weekly Completion")
                
                # Create a bar chart with Streamlit
                weekly_chart_df = pd.DataFrame({
                    "Week": df["week_label"],
                    "Completed": df["completed_int"]
                }).set_index("Week")
                
                st.bar_chart(weekly_chart_df)
                
                # Calculate and display streak information
                st.subheader("Streak Information")
                
                # Calculate current streak
                current_streak = 0
                for entry in reversed(completion_data):
                    if entry["completed"]:
                        current_streak += 1
                    else:
                        break
                
                # Calculate longest streak
                longest_streak = 0
                current = 0
                for entry in completion_data:
                    if entry["completed"]:
                        current += 1
                        longest_streak = max(longest_streak, current)
                    else:
                        current = 0
                
                # Display streak metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Current Streak", f"{current_streak} weeks")
                with col2:
                    st.metric("Longest Streak", f"{longest_streak} weeks")
                
                # Create a line chart showing the streak over time
                streak_data = []
                current = 0
                for entry in completion_data:
                    if entry["completed"]:
                        current += 1
                    else:
                        current = 0
                    streak_data.append({"week": entry["week"], "streak": current})
                
                streak_df = pd.DataFrame(streak_data)
                
                # Create a line chart for streak visualization
                st.subheader("Streak Over Time")
                
                # Format for display
                streak_chart_df = pd.DataFrame({
                    "Week": [f"Week {w}" for w in df["week_num"]],
                    "Streak (weeks)": streak_df["streak"]
                }).set_index("Week")
                
                st.line_chart(streak_chart_df)

# Add footer
st.markdown("---")
st.markdown("© 2023 Habit Tracker App")
