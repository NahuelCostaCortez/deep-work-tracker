#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import os

# Configuration file
CONFIG_FILE = os.path.expanduser("~/.dwt_config.json")

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    # Default configuration
    return {"daily_goal": 4.0}

def load_data():
    """Load the deep work data from JSON file, auto-create if missing"""
    try:
        with open('deep-work-data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Auto-create empty file
        empty_data = {"sessions": []}
        with open('deep-work-data.json', 'w') as f:
            json.dump(empty_data, f, indent=2)
        print(f"{Colors.YELLOW}No deep-work-data.json found. Created a new one for you!{Colors.RESET}")
        return empty_data
    except json.JSONDecodeError:
        print(f"{Colors.RED}Error: Invalid JSON in deep-work-data.json{Colors.RESET}")
        sys.exit(1)

def process_sessions(data):
    """Process sessions and group by date"""
    daily_hours = defaultdict(float)
    
    for session in data['sessions']:
        if session['completed'] and session['duration'] > 0:
            # Parse the start date
            start_time = datetime.fromisoformat(session['startTime'].replace('Z', '+00:00'))
            date_key = start_time.date()
            
            # Convert duration from minutes to hours
            hours = session['duration'] / 60.0
            daily_hours[date_key] += hours
    
    return daily_hours

def get_intensity_char(hours, goal=4.0):
    """Get the character representation based on hours worked"""
    if hours == 0:
        return '·'
    else:
        return '█'  # Use solid square for all activity levels, color will show intensity

def get_intensity_color(hours, goal=4.0):
    """Get the color based on hours worked - 256-color palette progression"""
    if hours == 0:
        return '\033[90m'        # Gray dot (no activity)
    elif hours < 2:
        return '\033[38;5;49m'   # Color 49 (1h)
    elif hours < 3:
        return '\033[38;5;47m'   # Color 47 (2h)
    elif hours < 4:
        return '\033[38;5;40m'   # Color 40 (3h)
    else:
        return '\033[38;5;28m'   # Color 28 (4h or more - highest intensity)

def create_contribution_graph(daily_hours, daily_goal=4.0, weeks=26):
    """Create a GitHub-like contribution graph"""
    today = datetime.now().date()
    start_date = today - timedelta(weeks=weeks)
    
    # Find the Monday of the week containing start_date
    days_since_monday = start_date.weekday()
    graph_start = start_date - timedelta(days=days_since_monday)
    
    print(f"\n{Colors.BOLD}Contribution Graph (Last 6 months){Colors.RESET}")
    print("─" * 80)
    
    # Day labels
    days = ['Mon', 'Wed', 'Fri']
    print("     ", end="")
    
    # Month labels - create proper month headers spanning correct number of weeks
    month_spans = []
    current_month = None
    month_start_week = 0
    
    for week in range(weeks):
        week_start = graph_start + timedelta(weeks=week)
        month = week_start.strftime('%b')
        
        if month != current_month:
            if current_month is not None:
                # Store the previous month's span
                month_spans.append((current_month, month_start_week, week - 1))
            current_month = month
            month_start_week = week
    
    # Add the last month
    if current_month is not None:
        month_spans.append((current_month, month_start_week, weeks - 1))
    
    # Print month headers with proper spacing
    week_pos = 0
    for month_name, start_week, end_week in month_spans:
        # Add padding for weeks before this month
        while week_pos < start_week:
            print("  ", end="")  # 2 chars for the week
            if week_pos < weeks - 1:  # space between weeks
                print(" ", end="")
            week_pos += 1
        
        # Calculate month span and center the month name (2 chars per week + spaces between)
        num_weeks = end_week - start_week + 1
        month_width = num_weeks * 2 + (num_weeks - 1)  # 2 chars per week + spaces between weeks
        month_label = month_name.center(month_width)
        print(month_label, end="")
        week_pos = end_week + 1
    
    # Add remaining padding
    while week_pos < weeks:
        print("  ", end="")  # 2 chars for the week
        if week_pos < weeks - 1:  # space between weeks
            print(" ", end="")
        week_pos += 1
    
    print()
    
    # Graph rows
    for day_idx in range(7):  # Monday to Sunday
        if day_idx % 2 == 0 and day_idx//2 < len(days):  # Show label only for Mon, Wed, Fri
            print(f"{days[day_idx//2]:>3}  ", end="")
        else:
            print("     ", end="")
        
        for week in range(weeks):
            current_date = graph_start + timedelta(weeks=week, days=day_idx)
            
            if current_date > today:
                print(f"{Colors.GRAY}··{Colors.RESET}", end="")
            else:
                hours = daily_hours.get(current_date, 0)
                # Use 4-hour goal for weekdays, 2-hour for weekends
                is_weekday = current_date.weekday() < 5
                goal = 4.0 if is_weekday else 2.0
                char = get_intensity_char(hours, goal)
                color = get_intensity_color(hours, goal)
                print(f"{color}{char}{char}{Colors.RESET}", end="")
            
            # Add space between weeks (except for the last week)
            if week < weeks - 1:
                print(" ", end="")
        
        print()  # New line after each day row
    
    # Legend with 256-color progression
    print(f"\n     Less \033[38;5;49m█{Colors.RESET} \033[38;5;47m█{Colors.RESET} \033[38;5;40m█{Colors.RESET} \033[38;5;28m█{Colors.RESET} More")
    if daily_goal == 0:
      print(f"     Goal: 🏖️ Vacation mode (no weekly goal)")
    else:
      print(f"     Goal: {daily_goal * 5:.0f} hours/week (weekdays)")

def calculate_weekly_deficit(daily_hours, current_week_start, daily_goal=4.0):
    """Calculate the deficit from previous weeks"""
    weekly_goal = daily_goal * 5  # daily_goal × 5 weekdays
    total_deficit = 0
    
    # Check the last 8 weeks (including current week)
    for week_offset in range(1, 9):  # Start from 1 to skip current week
        week_start = current_week_start - timedelta(weeks=week_offset)
        week_hours = 0
        
        # Calculate hours for this week (weekdays only)
        for day_offset in range(5):  # Monday to Friday
            day = week_start + timedelta(days=day_offset)
            if day in daily_hours:
                week_hours += daily_hours[day]
        
        # Add deficit if week didn't meet goal
        if week_hours < weekly_goal:
            week_deficit = weekly_goal - week_hours
            total_deficit += week_deficit

    return total_deficit

def create_weekly_progress(daily_hours, daily_goal=4.0):
    """Create this week's progress with progress bars"""
    today = datetime.now().date()
    
    # Find Monday of current week
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    
    # Calculate deficit from previous weeks
    weekly_deficit = calculate_weekly_deficit(daily_hours, week_start, daily_goal)
    
    print(f"\n{Colors.BOLD}This Week's Progress{Colors.RESET}")
    print("─" * 50)
    
    total_week_hours = 0
    weekday_hours = 0
    
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_name = current_date.strftime('%a')
        hours = daily_hours.get(current_date, 0)
        total_week_hours += hours
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        is_weekday = i < 5  # Monday to Friday
        if is_weekday:
            weekday_hours += hours
            if daily_goal == 0:
                goal_text = "🏖️"  # Vacation mode
            else:
                goal_text = f"{daily_goal:.1f}h"
        else:
            goal_text = "—"
        
        # Create progress bar
        if is_weekday and daily_goal > 0:
            base_progress = min(hours / daily_goal, 1.0)
            # Show overflow if hours > daily_goal
            overflow_progress = max(0, (hours - daily_goal) / daily_goal)
        else:
            # For weekends or vacation days, use 4h as visual scale
            base_progress = min(hours / 4.0, 1.0) if hours > 0 else 0
            overflow_progress = 0
        
        bar_length = 20
        base_filled = int(bar_length * base_progress)
        overflow_filled = min(bar_length - base_filled, int(bar_length * overflow_progress))
        empty_length = bar_length - base_filled - overflow_filled
        
        # Choose color based on progress - 256-color progression
        if not is_weekday and hours == 0:
            bar_color = '\033[90m'         # Dark gray
        elif not is_weekday and hours > 0:
            bar_color = '\033[38;5;28m'    # Highest intensity green for weekend work
        elif hours == 0:
            bar_color = '\033[90m'         # Dark gray
        elif hours >= 4:
            bar_color = '\033[38;5;28m'    # Color 28 (4h or more - highest intensity)
        elif hours >= 3:
            bar_color = '\033[38;5;40m'    # Color 40 (3h)
        elif hours >= 2:
            bar_color = '\033[38;5;47m'    # Color 47 (2h)
        elif hours > 0:
            bar_color = '\033[38;5;49m'    # Color 49 (1h)
        else:
            bar_color = '\033[90m'         # Dark gray
        
        # Create bar with overflow indication
        if overflow_filled > 0:
            bar = bar_color + '█' * base_filled + '\033[96m' + '█' * overflow_filled + Colors.RESET + '░' * empty_length
        else:
            bar = bar_color + '█' * base_filled + Colors.RESET + '░' * empty_length
        
        # Mark today
        today_marker = " ← Today" if current_date == today else ""
        
        # Add deficit reduction indicator for extra hours
        deficit_indicator = ""
        if is_weekday and daily_goal > 0 and hours > daily_goal:
            extra = hours - daily_goal
            deficit_indicator = f" (+{extra:.1f}h → deficit)"
        
        print(f"{day_name} {current_date.strftime('%m/%d')} │{bar}│ {hours:4.1f}h / {goal_text}{deficit_indicator}{today_marker}")
    
    # Calculate extra hours worked this week (beyond daily goals)
    extra_hours_this_week = 0
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        is_weekday = i < 5  # Monday to Friday
        if is_weekday and daily_goal > 0:
            hours = daily_hours.get(current_date, 0)
            if hours > daily_goal:
                extra_hours_this_week += (hours - daily_goal)
    
    # Weekly summary
    base_week_goal = daily_goal * 5  # daily_goal × 5 weekdays
    # This week's goal includes the FULL original deficit
    adjusted_week_goal = base_week_goal + weekly_deficit
    week_progress = weekday_hours / adjusted_week_goal if adjusted_week_goal > 0 else 1.0
    
    # Calculate remaining deficit after applying extra hours (for future weeks)
    remaining_deficit = max(0, weekly_deficit - extra_hours_this_week)
    
    print("─" * 50)
    
    if daily_goal == 0:
        print(f"{Colors.BOLD}🏖️  Vacation mode: No weekly goal set{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}Week Total: {weekday_hours:.1f}h / {adjusted_week_goal:.1f}h ({week_progress*100:.1f}%) - Weekdays{Colors.RESET}")
        remaining_hours = max(0, adjusted_week_goal - weekday_hours)
        if remaining_hours < 0:
            print(f"{Colors.GRAY}Goal exceeded by: {weekday_hours - adjusted_week_goal:.1f}h{Colors.RESET}")
        
        # Only show deficit information if there's still remaining deficit or if we applied extra hours this week
        if weekly_deficit > 0:
            if extra_hours_this_week > 0:
                deficit_reduced = min(weekly_deficit, extra_hours_this_week)
                if remaining_deficit > 0:
                    print(f"{Colors.GRAY}Deficit from previous weeks: {remaining_deficit:.1f}h (reduced by {deficit_reduced:.1f}h this week){Colors.RESET}")
                else:
                    print(f"\033[38;5;28m✅ All previous deficits cleared this week! (cleared {deficit_reduced:.1f}h){Colors.RESET}")
            else:
                print(f"{Colors.GRAY}Deficit from previous weeks: {weekly_deficit:.1f}h (work >{daily_goal:.1f}h/day to reduce){Colors.RESET}")
        
        if weekday_hours >= adjusted_week_goal:
            print(f"\033[38;5;28m🎉 Weekly goal achieved! Great work!{Colors.RESET}")
        elif weekday_hours >= adjusted_week_goal * 0.8:
            print(f"\033[38;5;40m💪 Almost there! {adjusted_week_goal - weekday_hours:.1f}h to go{Colors.RESET}")
        else:
            print(f"📈 Keep pushing! {adjusted_week_goal - weekday_hours:.1f}h remaining{Colors.RESET}")

def show_stats(daily_hours):
    """Show additional statistics"""
    if not daily_hours:
        return
    
    # Calculate yearly sessions and averages
    today = datetime.now().date()
    current_year = today.year
    
    # Calculate total sessions in current year
    year_sessions = 0
    for date, hours in daily_hours.items():
        if date.year == current_year and hours > 0:
            year_sessions += 1
    
    # Last 30 days average
    last_30_total = 0
    last_30_days = 0
    for i in range(30):
        check_date = today - timedelta(days=i)
        if check_date in daily_hours:
            last_30_total += daily_hours[check_date]
            last_30_days += 1
    
    avg_30_days = last_30_total / 30 if last_30_days > 0 else 0
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}Statistics{Colors.RESET}")
    print("─" * 30)
    print(f"Sessions this year: {year_sessions} days")
    print(f"30-day average: {avg_30_days:.1f} hours/day")

def main():
    """Main function"""
    print(f"{Colors.BOLD}{Colors.BLUE}🎯 Deep Work Tracker{Colors.RESET}")
    
    # Load configuration and data
    config = load_config()
    daily_goal = config.get('daily_goal', 4.0)
    data = load_data()
    daily_hours = process_sessions(data)
    
    # Display visualizations
    create_contribution_graph(daily_hours, daily_goal)
    create_weekly_progress(daily_hours, daily_goal)
    show_stats(daily_hours)
    
    #print(f"\n{Colors.GRAY}Data extracted: {data.get('extracted', 'Unknown')}{Colors.RESET}")
    #print(f"{Colors.GRAY}Total sessions in data: {data.get('totalSessions', 0)}{Colors.RESET}")

if __name__ == "__main__":
    main() 