#!/usr/bin/env python3

import json
import time
import sys
import os
import signal
import subprocess
import uuid
import select
import termios
import tty
from datetime import datetime, timedelta
from pathlib import Path

# Timer state file
STATE_FILE = os.path.expanduser("~/.dwt_session_state.json")
# Configuration file
CONFIG_FILE = os.path.expanduser("~/.dwt_config.json")

class DeepWorkTimer:
    def __init__(self):
        self.state = self.load_state()
        self.config = self.load_config()
    
    def load_state(self):
        """Load timer state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_state(self, state):
        """Save timer state to file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
            self.state = state
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def clear_state(self):
        """Clear timer state"""
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        self.state = {}
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default configuration
        return {"daily_goal": 4.0}
    
    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self.config = config
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def set_daily_goal(self):
        """Set the daily goal interactively"""
        current_goal = self.config.get('daily_goal', 4.0)
        print(f"\n⚙️  Current daily goal: {current_goal} hours")
        print("💡 Tip: Set to 0 for vacation days, or lower for light days")
        
        try:
            new_goal = input(f"Enter new daily goal (hours, press Enter for {current_goal}): ").strip()
            
            if new_goal == "":
                print(f"✅ Keeping current goal: {current_goal} hours")
                return
                
            goal_float = float(new_goal)
            if goal_float < 0:
                print("❌ Goal cannot be negative")
                return
                
            config = self.config.copy()
            config['daily_goal'] = goal_float
            self.save_config(config)
            
            if goal_float == 0:
                print("🏖️  Daily goal set to 0 hours (vacation mode)")
            else:
                print(f"✅ Daily goal updated to {goal_float} hours")
                
        except ValueError:
            print("❌ Invalid number. Goal not changed.")
        except KeyboardInterrupt:
            print("\n❌ Goal change cancelled.")
    
    def run_shortcut(self, name):
        """Run a macOS shortcut"""
        try:
            result = subprocess.run(['shortcuts', 'run', name], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True
            else:
                print(f"❌ Shortcut failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"⏱️  Shortcut '{name}' timed out")
            return False
        except FileNotFoundError:
            print(f"❌ 'shortcuts' command not found. Make sure you're on macOS 12+ with Shortcuts app")
            return False
        except Exception as e:
            print(f"❌ Error running shortcut: {e}")
            return False
    
    def play_notification_sound(self):
        """Play a notification sound on macOS"""
        try:
            # Play system notification sound
            subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                         capture_output=True, timeout=5)
        except:
            try:
                # Fallback: use say command
                subprocess.run(['say', 'Deep work session complete'], 
                             capture_output=True, timeout=5)
            except:
                # Fallback: system beep
                print('\a')  # ASCII bell character
    
    def add_session_to_data(self, start_time, end_time, duration_minutes):
        """Add a completed session to the deep work data file"""
        # Get the script directory to find the data file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_file = os.path.join(script_dir, 'deep-work-data.json')
        
        # Load existing data
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ {data_file} not found. Cannot log session.")
            return False
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {data_file}. Cannot log session.")
            return False
        
        # Create new session entry
        new_session = {
            "id": str(uuid.uuid4()),
            "startTime": start_time.isoformat() + "Z",
            "endTime": end_time.isoformat() + "Z",
            "duration": duration_minutes,
            "completed": True
        }
        
        # Add to data
        data['sessions'].append(new_session)
        data['totalSessions'] = len(data['sessions'])
        data['extracted'] = datetime.now().isoformat() + "Z"
        
        # Save updated data
        try:
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\r\033[K📝 Session logged: {duration_minutes} minutes")
            return True
            
        except Exception as e:
            print(f"❌ Error saving session data: {e}")
            return False
    
    def format_time(self, seconds):
        """Format seconds into MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def check_keyboard_input(self):
        """Check for non-blocking keyboard input"""
        try:
            # Check if input is available without blocking
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                # Save terminal settings
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    # Set terminal to raw mode for single character input
                    tty.setraw(sys.stdin.fileno())
                    char = sys.stdin.read(1)
                    return char.lower()
                finally:
                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            return None
        except:
            return None
    
    def show_countdown(self, total_seconds, start_time, paused_duration=0):
        """Display countdown timer with interactive controls"""
        print("💡 Controls: [s]top, [q]uit, or Ctrl+C")
        print()
        import termios
        import tty
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            while True:
                elapsed = time.time() - start_time - paused_duration
                remaining = max(0, total_seconds - elapsed)
                if remaining <= 0:
                    print(f"\r\033[KGreat job!")
                    print()
                    # Play notification sound
                    try:
                        subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], 
                                     capture_output=True, timeout=2)
                    except:
                        print('\a')  # Fallback beep
                    return True

                # Display countdown
                time_str = self.format_time(remaining)
                progress = (total_seconds - remaining) / total_seconds
                bar_length = 30
                filled = int(bar_length * progress)
                bar = '█' * filled + '░' * (bar_length - filled)

                print(f"\r⏱️  {time_str} │{bar}│ [s]top [q]uit: ", end='', flush=True)

                # Check for keyboard input
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    char = sys.stdin.read(1).lower()
                    if char == 's':
                        print('\r\033[K', end='')  # Clear the timer line
                        print("⏸️  Session paused.")  # Print the pause message
                        print('\r\033[K')  # Clear the next line and move the cursor to the left
                        self.run_shortcut("stop deep")
                        sys.exit(1)
                    elif char == 'q':
                        return self.handle_quit_during_countdown(remaining, start_time, paused_duration)

                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n⏸️  Session paused at {self.format_time(remaining)}")
            self.run_shortcut("stop deep")
            return False
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    def handle_stop_during_countdown(self, remaining):
        """Handle stop command during countdown"""
        print("\n⏸️  Session paused.")
        self.run_shortcut("stop deep")
        return False
    
    def handle_quit_during_countdown(self, remaining, start_time, paused_duration):
        """Handle quit command during countdown"""
        # Quit session without logging anything
        
        # Run stop shortcut
        self.run_shortcut("stop deep")
        
        self.clear_state()
        print(f"\r\033[K🚪 Session quit. No time logged.")
        print('\r\033[K', end='')  # Clear the line again and leave cursor at start
        return "ended"
    
    def start_session(self):
        """Start a new deep work session"""
        if self.state.get('active'):
            print("❌ A session is already active. Use 'continue' to resume or 'stop' to end it.")
            sys.exit(1)
        
        # Run the shortcut
        if not self.run_shortcut("start deep"):
            print("❌ Failed to start shortcut. Continue anyway? (y/N): ", end='')
            if input().lower() != 'y':
                return
        
        # Start timer
        start_time = time.time()
        session_duration = 3600  # 1 hour in seconds
        
        # Save initial state
        state = {
            'active': True,
            'start_time': start_time,
            'duration': session_duration,
            'paused_duration': 0,
            'paused_at': None
        }
        self.save_state(state)
        
        print(f"🚀 Deep work session started!")
        print(f"📅 Start time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"⏰ Duration: 1 hour")
        print()
        
        # Show countdown
        result = self.show_countdown(session_duration, start_time)
        
        if result == True:
            # Session completed successfully
            end_time = datetime.now()
            actual_start = datetime.fromtimestamp(start_time)
            
            # Run stop shortcut
            self.run_shortcut("stop deep")
            
            # Log the session
            self.add_session_to_data(actual_start, end_time, 60)  # 60 minutes
            
            self.clear_state()
            print("🎉 Session completed successfully!")
        elif result == "ended":
            # Session was ended during countdown (already handled in method)
            pass
        elif result == "continue":
            # User chose to continue, restart countdown loop
            self.start_session()
        else:
            # Session was paused
            remaining = session_duration - (time.time() - start_time - state['paused_duration'])
            state['paused_at'] = time.time()
            state['remaining'] = remaining
            self.save_state(state)
            print("Session paused. Use 'continue' to resume.")
            sys.exit(1)
    
    def continue_session(self):
        """Continue a paused session or resume the timer UI if already running"""
        if not self.state.get('active'):
            print("❌ No active session to continue. Use 'start' to begin a new session.")
            sys.exit(1)
        
        if not self.state.get('paused_at'):
            # Session is running, resume the timer UI
            print("▶️  Resuming active session...")
            self.run_shortcut("start deep")  # Call the shortcut when continuing
            remaining = self.state['duration'] - (time.time() - self.state['start_time'] - self.state['paused_duration'])
            print(f"⏰ Remaining time: {self.format_time(remaining)}")
            print()
            result = self.show_countdown(self.state['duration'], self.state['start_time'], self.state['paused_duration'])
            if result == True:
                # Session completed successfully
                end_time = datetime.now()
                actual_start = datetime.fromtimestamp(self.state['start_time'])
                self.run_shortcut("stop deep")
                self.add_session_to_data(actual_start, end_time, 60)  # 60 minutes
                self.clear_state()
                print("🎉 Session completed successfully!")
            elif result == "ended":
                pass
            elif result == "continue":
                self.continue_session()
            else:
                new_remaining = self.state['duration'] - (time.time() - self.state['start_time'] - self.state['paused_duration'])
                self.state['paused_at'] = time.time()
                self.state['remaining'] = new_remaining
                self.save_state(self.state)
            sys.exit(0)
        else:
            # Session is paused, continue as before
            print("▶️  Continuing deep work session...")
            
            # Run start shortcut when continuing


            self.run_shortcut("start deep")
            
            # Calculate paused duration
            pause_duration = time.time() - self.state['paused_at']
            total_paused = self.state['paused_duration'] + pause_duration
            
            # Update state
            state = self.state.copy()
            state['paused_duration'] = total_paused
            state['paused_at'] = None
            self.save_state(state)
            
            remaining = state.get('remaining', state['duration'])
            print(f"⏰ Remaining time: {self.format_time(remaining)}")
            print()
            
            # Continue countdown
            result = self.show_countdown(state['duration'], state['start_time'], total_paused)
            
            if result == True:
                # Session completed successfully
                end_time = datetime.now()
                actual_start = datetime.fromtimestamp(state['start_time'])
                
                # Run stop shortcut
                self.run_shortcut("stop deep")
                
                # Log the session
                self.add_session_to_data(actual_start, end_time, 60)  # 60 minutes
                
                self.clear_state()
                print("🎉 Session completed successfully!")
            elif result == "ended":
                # Session was ended during countdown (already handled in method)
                pass
            elif result == "continue":
                # User chose to continue, restart countdown loop
                self.continue_session()
            else:
                # Session was paused again
                new_remaining = state['duration'] - (time.time() - state['start_time'] - total_paused)
                state['paused_at'] = time.time()
                state['remaining'] = new_remaining
                self.save_state(state)
    
    def stop_session(self):
        """Stop/pause the current session"""
        if not self.state.get('active'):
            print("❌ No active session to stop.")
            sys.exit(1)

        # Immediately pause session and call shortcut
        if not self.state.get('paused_at'):
            state = self.state.copy()
            state['paused_at'] = time.time()
            remaining = state['duration'] - (time.time() - state['start_time'] - state['paused_duration'])
            state['remaining'] = remaining
            self.save_state(state)
            print('\r\033[K', end='')  # Clear the timer line
            print("⏸️  Session paused.")
            print('\r\033[K')  # Clear the next line and move the cursor to the left
            self.run_shortcut("stop deep")
            sys.exit(1)
        else:
            print("ℹ️  Session is already paused.")
            sys.exit(1)
    
    def status(self):
        """Show current session status"""
        if not self.state.get('active'):
            print("💤 No active deep work session")
            return
        
        start_time = datetime.fromtimestamp(self.state['start_time'])
        duration = self.state['duration']
        paused_duration = self.state['paused_duration']
        
        if self.state.get('paused_at'):
            # Session is paused
            paused_since = datetime.fromtimestamp(self.state['paused_at'])
            remaining = self.state.get('remaining', duration)
            print(f"⏸️  Session PAUSED")
            print(f"📅 Started: {start_time.strftime('%H:%M:%S')}")
            print(f"⏸️  Paused at: {paused_since.strftime('%H:%M:%S')}")
            print(f"⏰ Time remaining: {self.format_time(remaining)}")
            print(f"💡 Use 'continue' to resume")
        else:
            # Session is running
            elapsed = time.time() - self.state['start_time'] - paused_duration
            remaining = max(0, duration - elapsed)
            print(f"🟢 Session ACTIVE")
            print(f"📅 Started: {start_time.strftime('%H:%M:%S')}")
            print(f"⏰ Time remaining: {self.format_time(remaining)}")
            print(f"💡 Use 'stop' to pause")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  start    - Start new deep work session")
        print("  stop     - Stop/pause current session") 
        print("  continue - Continue paused session")
        print("  status   - Show session status")
        print("  settings - Change daily goal and settings")
        return
    
    timer = DeepWorkTimer()
    command = sys.argv[1]
    
    if command == 'start':
        timer.start_session()
    elif command == 'stop':
        timer.stop_session()
    elif command == 'continue':
        timer.continue_session()
    elif command == 'status':
        timer.status()
    elif command == 'settings':
        timer.set_daily_goal()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main() 