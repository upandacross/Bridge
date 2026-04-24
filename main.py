#!/bin/env python
"""
DearPyGUI Frontend for Bridge Attendance Application.
Provides CRUD operations and attendance tracking.
"""

import dearpygui.dearpygui as dpg
from database import Database
from sql_reports import SQLReportsManager
from pathlib import Path
from datetime import date
from typing import Optional, List, Dict, Any
import logging

# Color palette constants for consistent theming
COLORS = {
    'primary': (52, 152, 219),      # Blue
    'primary_dark': (41, 128, 185), # Dark Blue
    'success': (46, 204, 113),      # Green
    'warning': (241, 196, 15),      # Yellow/Orange
    'danger': (231, 76, 60),        # Red
    'info': (52, 152, 219),         # Cyan
    'header': (44, 62, 80),         # Dark Blue-Grey
    'header_text': (236, 240, 241), # Light Gray-White
    'bg_light': (245, 247, 249),    # Light background
    'text_main': (44, 62, 80),      # Dark text
    'text_secondary': (127, 140, 141), # Lighter text
}

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bridge_app.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# Theme IDs for colors
theme_button_primary = None
theme_button_success = None

def create_themes():
    """Create custom themes with colors for buttons and other widgets."""
    global theme_button_primary, theme_button_success
    
    with dpg.theme() as theme_button_primary:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (52, 152, 219))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (52, 162, 235))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (41, 128, 185))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    
    with dpg.theme() as theme_button_success:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (46, 204, 113))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (65, 214, 131))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (39, 174, 96))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    
    with dpg.theme() as theme_button_warning:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (241, 196, 15))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (245, 205, 32))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (230, 190, 13))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    
    with dpg.theme() as theme_button_danger:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (231, 76, 60))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (240, 88, 73))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (208, 64, 50))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
    
    return {
        'primary': theme_button_primary,
        'success': theme_button_success,
        'warning': theme_button_warning,
        'danger': theme_button_danger
    }


class BridgeApp:
    """Main application class for the Bridge Attendance GUI."""
    
    def __init__(self, db_path: str = None):
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            # Use new schema database (bridge.db) with Users, Games, Attendance tables
            self.db_path = Path(__file__).parent / "bridge.db"
        self.db: Optional[Database] = None
        self.app_instance = None
        self.all_users_sort_column = "last"  # Default sort by last name
        self.all_users_sort_reverse = False  # Default ascending order
        
    def run(self):
        """Run the DearPyGUI application."""
        if self.app_instance is not None:
            return  # Already running
            
        dpg.create_context()
        
        # Create custom themes with colors
        self.button_themes = create_themes()
        
        with dpg.window(label="Bridge Attendance", width=1200, height=800) as main_window:
            self.main_window_id = main_window
            
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
                
                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Users", callback=self.show_users_view)
                    dpg.add_menu_item(label="Attendance Report", callback=self.show_attendance_report)
                    dpg.add_menu_item(label="All Users Report", callback=self.show_all_users_report)
                    dpg.add_menu_item(label="Month Schedule", callback=self.show_month_schedule)
                
                with dpg.menu(label="Help"):
                    dpg.add_menu_item(label="About", callback=self.show_about)
            
            with dpg.tab_bar() as self.tab_bar_id:
                with dpg.tab(label="Users") as self.users_tab_id:
                    self._build_users_view()
                
                with dpg.tab(label="Attendance Report") as self.attendance_tab_id:
                    self._build_attendance_report_view()
                
                with dpg.tab(label="All Users Report") as self.all_users_tab_id:
                    self._build_all_users_report_view()
                
                with dpg.tab(label="Month Schedule") as self.month_schedule_tab_id:
                    self._build_month_schedule_view()
                
                with dpg.tab(label="Edit Attendance") as self.edit_attendance_tab_id:
                    self._build_edit_attendance_view()
                
                with dpg.tab(label="SQL Reports") as self.sql_reports_tab_id:
                    self._build_sql_reports_view()
        
        # Configure viewport theme
        dpg.create_viewport(title='Bridge Attendance', width=1200, height=800)
        
        # Set viewport clear color (background)
        dpg.set_viewport_clear_color(COLORS['bg_light'])
        
        dpg.setup_dearpygui()
        dpg.show_viewport()
        
        self.db = Database(str(self.db_path))
        self.db.connect()
        
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        
        if self.db:
            self.db.close()
        dpg.destroy_context()
        self.app_instance = None
    
    def _build_users_view(self):
        """Build the users view."""
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                # Header with color
                dpg.add_text("Filter/Search Users", color=COLORS['header'])
                dpg.add_input_text(label="Search", tag="user_search_input",
                                  callback=lambda: self._filter_users(), width=-1)
                dpg.add_checkbox(label="Show Inactive", tag="show_inactive_checkbox",
                               callback=lambda: self._filter_users())
                
                dpg.add_spacer(height=15)
                # Add New User button - primary color
                btn_add_user = dpg.add_button(label="Add New User", callback=self._show_add_user_dialog,
                                              width=-1, indent=0)
                dpg.bind_item_theme(btn_add_user, self.button_themes['primary'])
            
            with dpg.group():
                with dpg.table(tag="users_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    dpg.add_table_column(label="ID")
                    dpg.add_table_column(label="Name")
                    dpg.add_table_column(label="Phone")
                    dpg.add_table_column(label="Email")
                    dpg.add_table_column(label="Active")
                    dpg.add_table_column(label="Days")
                
                self._populate_users_table()
    
    def _filter_users(self):
        """Filter users based on search input."""
        search_text = dpg.get_value("user_search_input") if dpg.does_item_exist("user_search_input") else ""
        show_inactive = dpg.get_value("show_inactive_checkbox") if dpg.does_item_exist("show_inactive_checkbox") else False
        
        self._populate_users_table(search=search_text, show_inactive=show_inactive)
    
    def _populate_users_table(self, search: str = "", show_inactive: bool = False):
        """Populate the users table."""
        if not self.db:
            return
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("users_table"):
            dpg.delete_item("users_table")
        
        with dpg.table(tag="users_table", parent=self.users_tab_id, header_row=True, policy=dpg.mvTable_SizingFixedFit,
                      scrollX=True, scrollY=True, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Phone")
            dpg.add_table_column(label="Email")
            dpg.add_table_column(label="Active")
            dpg.add_table_column(label="Days")
            dpg.add_table_column(label="Actions")
            
            # Add header row
            with dpg.table_row():
                dpg.add_text("ID")
                dpg.add_text("Name")
                dpg.add_text("Phone")
                dpg.add_text("Email")
                dpg.add_text("Active")
                dpg.add_text("Days")
                dpg.add_text("Actions")
            
            if search:
                users = self.db.search_users(search)
            else:
                users = self.db.get_all_users(active_only=not show_inactive)
            
            for user in users:
                days = []
                if user.get('play_thursdays'):
                    days.append("Thu")
                if user.get('play_fridays'):
                    days.append("Fri")
                
                # Create a copy of the user dict to capture in the lambda
                user_copy = {
                    'id': user['id'],
                    'first': user.get('first', ''),
                    'last': user.get('last', ''),
                    'active': user.get('active', True),
                    'play_thursdays': user.get('play_thursdays', False),
                    'play_fridays': user.get('play_fridays', False),
                    'phone': user.get('phone'),
                    'email': user.get('email'),
                    'prefer_email': user.get('prefer_email', False),
                    'prefer_phone': user.get('prefer_phone', False),
                    'prefer_text': user.get('prefer_text', False),
                    'all_month': user.get('all_month', True),
                    'select_days': user.get('select_days', False)
                }
                
                with dpg.table_row():
                    dpg.add_text(str(user['id']))
                    dpg.add_text(f"{user.get('first', '')} {user.get('last', '')}")
                    dpg.add_text(user.get('phone', 'N/A'))
                    dpg.add_text(user.get('email', 'N/A'))
                    dpg.add_text("Yes" if user.get('active', True) else "No")
                    dpg.add_text("/".join(days))
                    # Actions column with Edit, Duplicate, and Delete buttons
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Edit", user_data=user['id'], callback=self._on_edit_user_clicked)
                        dpg.add_button(label="Duplicate", user_data=user['id'], callback=self._on_duplicate_user_clicked)
                        dpg.add_button(label="Delete", user_data=user['id'], callback=self._on_delete_user_clicked)
    
    def _show_add_user_dialog(self):
        """Show dialog to add a new user."""
        with dpg.window(label="Add New User", width=400, pos=(100, 100)) as window_id:
            with dpg.group():
                # Tab order: first, last, active, thurs, fri, phone, email
                dpg.add_input_text(tag="new_user_first", label="First Name")
                dpg.add_input_text(tag="new_user_last", label="Last Name")
                
                dpg.add_checkbox(tag="new_user_active", label="Active", default_value=True)
                dpg.add_checkbox(tag="new_user_thursdays", label="Plays Thursdays", default_value=False)
                dpg.add_checkbox(tag="new_user_fridays", label="Plays Fridays", default_value=False)
                
                dpg.add_input_text(tag="new_user_phone", label="Phone Number")
                dpg.add_input_text(tag="new_user_email", label="Email")
                
                dpg.add_spacer(height=10)
                # Tab order: pref email, pref phone, pref text
                dpg.add_checkbox(tag="new_user_prefer_email", label="Prefer Email", default_value=False)
                dpg.add_checkbox(tag="new_user_prefer_phone", label="Prefer Phone", default_value=False)
                dpg.add_checkbox(tag="new_user_prefer_text", label="Prefer Text", default_value=False)
                
                dpg.add_spacer(height=10)
                # All Month and Select Days as radio buttons
                dpg.add_radio_button(tag="new_user_month_option", 
                                    items=["All Month", "Select Days"],
                                    default_value="All Month",
                                    callback=self._on_add_month_option_changed)
            
            with dpg.group(horizontal=True):
                # Tab order: save, cancel
                dpg.add_button(label="Save", callback=lambda: self._save_new_user(window_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _on_add_month_option_changed(self, sender, app_data):
        """Handle change in month option radio button for add dialog."""
        # The value is already stored in the radio button, nothing additional needed
        pass
    
    def _save_new_user(self, window_id):
        """Save a new user."""
        first = dpg.get_value("new_user_first")
        last = dpg.get_value("new_user_last")
        active = dpg.get_value("new_user_active")
        play_thursdays = dpg.get_value("new_user_thursdays")
        play_fridays = dpg.get_value("new_user_fridays")
        phone = dpg.get_value("new_user_phone") or None
        email = dpg.get_value("new_user_email") or None
        prefer_email = dpg.get_value("new_user_prefer_email")
        prefer_phone = dpg.get_value("new_user_prefer_phone")
        prefer_text = dpg.get_value("new_user_prefer_text")
        
        # Handle radio button for All Month / Select Days
        month_option = dpg.get_value("new_user_month_option")
        all_month = (month_option == "All Month")
        select_days = (month_option == "Select Days")
        
        try:
            user_id = self.db.create_user(
                first=first,
                last=last,
                active=active,
                play_thursdays=play_thursdays,
                play_fridays=play_fridays,
                email=email,
                phone=phone,
                prefer_email=prefer_email,
                prefer_phone=prefer_phone,
                prefer_text=prefer_text,
                all_month=all_month,
                select_days=select_days
            )
            
            dpg.delete_item(window_id)
            self._populate_users_table()
        except ValueError as e:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(str(e))
    
    def _on_delete_user_clicked(self, sender, app_data):
        """Handle delete button click - show confirmation dialog."""
        # Get the user_id from the button's user_data
        user_id = dpg.get_item_user_data(sender)
        
        if user_id is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("Error: Could not get user ID from button")
            return
        
        # Fetch user data from database for the confirmation message
        user = self.db.get_user(user_id)
        
        if user is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User with ID {user_id} not found in database")
            return
        
        # Show confirmation dialog
        self._show_delete_confirmation_dialog(user)
    
    def _show_delete_confirmation_dialog(self, user: Dict[str, Any]):
        """Show confirmation dialog before deleting a user."""
        user_id = user['id']
        user_name = f"{user.get('first', '')} {user.get('last', '')}"
        
        with dpg.window(label="Confirm Delete", width=400, pos=(200, 200)) as window_id:
            dpg.add_text(f"Are you sure you want to delete user:")
            dpg.add_spacer(height=5)
            dpg.add_text(f"  {user_name} (ID: {user_id})")
            dpg.add_spacer(height=10)
            dpg.add_text("This action cannot be undone!", color=(255, 100, 100))
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete", callback=lambda: self._confirm_delete_user(window_id, user_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _confirm_delete_user(self, window_id, user_id: int):
        """Actually delete the user after confirmation."""
        try:
            success = self.db.delete_user(user_id)
            
            dpg.delete_item(window_id)
            
            if success:
                self._populate_users_table()
                with dpg.window(label="Success", width=300, pos=(150, 150)):
                    dpg.add_text("User deleted successfully!")
            else:
                with dpg.window(label="Error", width=300, pos=(150, 150)):
                    dpg.add_text("Failed to delete user.")
        except Exception as e:
            dpg.delete_item(window_id)
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error deleting user: {str(e)}")
    
    def _on_edit_user_clicked(self, sender, app_data):
        """Handle edit button click - fetch user from database using user_data."""
        # Get the user_id from the button's user_data
        user_id = dpg.get_item_user_data(sender)
        
        if user_id is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("Error: Could not get user ID from button")
            return
        
        # Fetch fresh user data from database
        user = self.db.get_user(user_id)
        
        if user is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User with ID {user_id} not found in database")
            return
        
        # Show the edit dialog with the fresh user data
        self._show_edit_user_dialog(user)
    
    def _on_duplicate_user_clicked(self, sender, app_data):
        """Handle duplicate button click - fetch user and show duplicate dialog."""
        # Get the user_id from the button's user_data
        user_id = dpg.get_item_user_data(sender)
        
        if user_id is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("Error: Could not get user ID from button")
            return
        
        # Fetch fresh user data from database
        user = self.db.get_user(user_id)
        
        if user is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User with ID {user_id} not found in database")
            return
        
        # Show the duplicate dialog with the user's data
        self._show_duplicate_user_dialog(user)
    
    def _show_duplicate_user_dialog(self, user: Dict[str, Any]):
        """Show dialog to duplicate an existing user with duplicate detection."""
        # Check if user is None or invalid
        if user is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("Error: User data is None")
            return
        
        if not isinstance(user, dict):
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User data is not a dict, it's {type(user)}")
            return
        
        if 'first' not in user or 'last' not in user:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User data missing required fields. Keys: {list(user.keys())}")
            return
        
        # Determine default radio button value based on user's current settings
        if user.get('select_days', False):
            month_option_default = "Select Days"
        else:
            month_option_default = "All Month"
        
        with dpg.window(label=f"Duplicate User: {user['first']} {user['last']}", width=500, pos=(100, 100)) as window_id:
            dpg.add_text("Duplicate Detection: Check for existing users with similar information")
            dpg.add_spacer(height=10)
            
            # Add duplicate check button
            dpg.add_button(label="Check for Duplicates", 
                          callback=lambda: self._check_for_duplicates(
                              window_id,
                              dpg.get_value("dup_user_first"),
                              dpg.get_value("dup_user_last"),
                              dpg.get_value("dup_user_phone")
                          ),
                          width=-1)
            
            dpg.add_separator()
            dpg.add_spacer(height=10)
            
            with dpg.group():
                # Tab order: first, last, active, thurs, fri, phone, email
                dpg.add_input_text(tag="dup_user_first", label="First Name", 
                                  default_value=user.get('first', ''))
                dpg.add_input_text(tag="dup_user_last", label="Last Name", 
                                  default_value=user.get('last', ''))
                
                dpg.add_checkbox(tag="dup_user_active", label="Active", 
                                default_value=bool(user.get('active', True)))
                dpg.add_checkbox(tag="dup_user_thursdays", label="Plays Thursdays", 
                                default_value=bool(user.get('play_thursdays', False)))
                dpg.add_checkbox(tag="dup_user_fridays", label="Plays Fridays", 
                                default_value=bool(user.get('play_fridays', False)))
                
                dpg.add_input_text(tag="dup_user_phone", label="Phone Number", 
                                  default_value=user.get('phone', '') or '')
                dpg.add_input_text(tag="dup_user_email", label="Email", 
                                  default_value=user.get('email', '') or '')
                
                dpg.add_spacer(height=10)
                # Tab order: pref email, pref phone, pref text
                dpg.add_checkbox(tag="dup_user_prefer_email", label="Prefer Email", 
                                default_value=bool(user.get('prefer_email', False)))
                dpg.add_checkbox(tag="dup_user_prefer_phone", label="Prefer Phone", 
                                default_value=bool(user.get('prefer_phone', False)))
                dpg.add_checkbox(tag="dup_user_prefer_text", label="Prefer Text", 
                                default_value=bool(user.get('prefer_text', False)))
                
                dpg.add_spacer(height=10)
                # All Month and Select Days as radio buttons
                dpg.add_radio_button(tag="dup_user_month_option", 
                                    items=["All Month", "Select Days"],
                                    default_value=month_option_default)
                
                # Placeholder for duplicate check results
                dpg.add_spacer(height=10)
                with dpg.group(tag="dup_check_results", show=False):
                    dpg.add_separator()
                    dpg.add_text("Duplicate Check Results:", color=(255, 200, 100))
            
            with dpg.group(horizontal=True):
                # Tab order: save, cancel
                dpg.add_button(label="Save as New User", 
                              callback=lambda: self._save_duplicate_user(window_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _check_for_duplicates(self, parent_window_id, first, last, phone):
        """Check for existing users that might be duplicates."""
        if not self.db:
            return
        
        # Clear previous results
        if dpg.does_item_exist("dup_check_results_group"):
            dpg.delete_item("dup_check_results_group")
        
        with dpg.group(tag="dup_check_results_group", parent="dup_check_results"):
            dpg.show_item("dup_check_results")
            
            found_duplicates = False
            
            # Check by name similarity
            if first or last:
                all_users = self.db.get_all_users(active_only=False)
                for user in all_users:
                    # Check for exact first+last match
                    name_match = (user.get('first', '').lower() == first.lower() and 
                                  user.get('last', '').lower() == last.lower())
                    
                    # Check for partial matches
                    partial_match = (first.lower() in user.get('first', '').lower() or 
                                    last.lower() in user.get('last', '').lower() or
                                    user.get('first', '').lower() in first.lower() or 
                                    user.get('last', '').lower() in last.lower())
                    
                    if name_match:
                        found_duplicates = True
                        dpg.add_text(f"⚠️ EXACT DUPLICATE: {user['first']} {user['last']} (ID: {user['id']})", 
                                    color=(255, 100, 100))
                        dpg.add_text(f"   Phone: {user.get('phone', 'N/A')}, Email: {user.get('email', 'N/A')}")
                    elif partial_match:
                        found_duplicates = True
                        dpg.add_text(f"⚠️ SIMILAR NAME: {user['first']} {user['last']} (ID: {user['id']})", 
                                    color=(255, 200, 100))
                        dpg.add_text(f"   Phone: {user.get('phone', 'N/A')}, Email: {user.get('email', 'N/A')}")
            
            # Check by phone
            if phone and len(phone) >= 7:
                phone_user = self.db.get_user_by_phone(phone)
                if phone_user:
                    found_duplicates = True
                    dpg.add_text(f"⚠️ PHONE DUPLICATE: {phone_user['first']} {phone_user['last']} (ID: {phone_user['id']})", 
                                color=(255, 100, 100))
                    dpg.add_text(f"   This phone number is already registered.")
            
            if not found_duplicates:
                dpg.add_text("✓ No duplicates found - this appears to be a unique record.", 
                            color=(100, 255, 100))
            
            dpg.add_spacer(height=10)
    
    def _save_duplicate_user(self, window_id):
        """Save the duplicated user as a new record."""
        first = dpg.get_value("dup_user_first")
        last = dpg.get_value("dup_user_last")
        active = dpg.get_value("dup_user_active")
        play_thursdays = dpg.get_value("dup_user_thursdays")
        play_fridays = dpg.get_value("dup_user_fridays")
        phone = dpg.get_value("dup_user_phone") or None
        email = dpg.get_value("dup_user_email") or None
        prefer_email = dpg.get_value("dup_user_prefer_email")
        prefer_phone = dpg.get_value("dup_user_prefer_phone")
        prefer_text = dpg.get_value("dup_user_prefer_text")
        
        # Handle radio button for All Month / Select Days
        month_option = dpg.get_value("dup_user_month_option")
        all_month = (month_option == "All Month")
        select_days = (month_option == "Select Days")
        
        try:
            # Try to create the user - this will fail if it's a true duplicate
            user_id = self.db.create_user(
                first=first,
                last=last,
                active=active,
                play_thursdays=play_thursdays,
                play_fridays=play_fridays,
                email=email,
                phone=phone,
                prefer_email=prefer_email,
                prefer_phone=prefer_phone,
                prefer_text=prefer_text,
                all_month=all_month,
                select_days=select_days
            )
            
            dpg.delete_item(window_id)
            self._populate_users_table()
            with dpg.window(label="Success", width=300, pos=(150, 150)):
                dpg.add_text(f"User duplicated successfully with ID: {user_id}")
        except Exception as e:
            # Show error if it's a duplicate
            error_msg = str(e)
            if "UNIQUE constraint failed" in error_msg or "unique index" in error_msg.lower():
                with dpg.window(label="Duplicate Found", width=400, pos=(150, 150)) as error_window:
                    dpg.add_text("Cannot save: Duplicate user detected!", color=(255, 100, 100))
                    dpg.add_spacer(height=10)
                    dpg.add_text("A user with this First Name, Last Name, and Phone combination already exists.")
                    dpg.add_spacer(height=10)
                    dpg.add_text("Please modify the information before saving.")
                    dpg.add_button(label="OK", callback=lambda: dpg.delete_item(error_window))
            else:
                with dpg.window(label="Error", width=300, pos=(150, 150)):
                    dpg.add_text(f"Error: {error_msg}")
    
    def _show_edit_user_dialog(self, user: Dict[str, Any]):
        """Show dialog to edit an existing user."""
        # Debug: Check if user is None or invalid
        if user is None:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("Error: User data is None")
            return
        
        if not isinstance(user, dict):
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User data is not a dict, it's {type(user)}")
            return
        
        if 'first' not in user or 'last' not in user:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(f"Error: User data missing required fields. Keys: {list(user.keys())}")
            return
        
        # Determine default radio button value based on user's current settings
        if user.get('select_days', False):
            month_option_default = "Select Days"
        else:
            month_option_default = "All Month"
        
        # Generate unique tags for this dialog instance
        dialog_id = f"edit_user_{user['id']}_{id(user)}"
        
        with dpg.window(label=f"Edit User: {user['first']} {user['last']}", width=400, pos=(100, 100)) as window_id:
            with dpg.group():
                # Tab order: first, last, active, thurs, fri, phone, email
                dpg.add_input_text(tag=f"{dialog_id}_first", label="First Name", default_value=user.get('first', ''))
                dpg.add_input_text(tag=f"{dialog_id}_last", label="Last Name", default_value=user.get('last', ''))
                
                dpg.add_checkbox(tag=f"{dialog_id}_active", label="Active", default_value=bool(user.get('active', True)))
                dpg.add_checkbox(tag=f"{dialog_id}_thursdays", label="Plays Thursdays", default_value=bool(user.get('play_thursdays', False)))
                dpg.add_checkbox(tag=f"{dialog_id}_fridays", label="Plays Fridays", default_value=bool(user.get('play_fridays', False)))
                
                dpg.add_input_text(tag=f"{dialog_id}_phone", label="Phone Number", default_value=user.get('phone', '') or '')
                dpg.add_input_text(tag=f"{dialog_id}_email", label="Email", default_value=user.get('email', '') or '')
                
                dpg.add_spacer(height=10)
                # Tab order: pref email, pref phone, pref text
                dpg.add_checkbox(tag=f"{dialog_id}_prefer_email", label="Prefer Email", default_value=bool(user.get('prefer_email', False)))
                dpg.add_checkbox(tag=f"{dialog_id}_prefer_phone", label="Prefer Phone", default_value=bool(user.get('prefer_phone', False)))
                dpg.add_checkbox(tag=f"{dialog_id}_prefer_text", label="Prefer Text", default_value=bool(user.get('prefer_text', False)))
                
                dpg.add_spacer(height=10)
                # All Month and Select Days as radio buttons
                dpg.add_radio_button(tag=f"{dialog_id}_month_option", 
                                    items=["All Month", "Select Days"],
                                    default_value=month_option_default,
                                    callback=self._on_edit_month_option_changed)
            
            with dpg.group(horizontal=True):
                # Tab order: save, cancel
                dpg.add_button(label="Save", callback=lambda: self._save_edit_user(window_id, dialog_id, user['id']))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _on_edit_month_option_changed(self, sender, app_data):
        """Handle change in month option radio button for edit dialog."""
        # The value is already stored in the radio button, nothing additional needed
        pass
    
    def _save_edit_user(self, window_id, dialog_id: str, user_id: int):
        """Save changes to an existing user."""
        first = dpg.get_value(f"{dialog_id}_first")
        last = dpg.get_value(f"{dialog_id}_last")
        active = dpg.get_value(f"{dialog_id}_active")
        play_thursdays = dpg.get_value(f"{dialog_id}_thursdays")
        play_fridays = dpg.get_value(f"{dialog_id}_fridays")
        phone = dpg.get_value(f"{dialog_id}_phone") or None
        email = dpg.get_value(f"{dialog_id}_email") or None
        prefer_email = dpg.get_value(f"{dialog_id}_prefer_email")
        prefer_phone = dpg.get_value(f"{dialog_id}_prefer_phone")
        prefer_text = dpg.get_value(f"{dialog_id}_prefer_text")
        
        # Handle radio button for All Month / Select Days
        month_option = dpg.get_value(f"{dialog_id}_month_option")
        all_month = (month_option == "All Month")
        select_days = (month_option == "Select Days")
        
        try:
            success = self.db.update_user(
                user_id,
                first=first,
                last=last,
                active=active,
                play_thursdays=play_thursdays,
                play_fridays=play_fridays,
                email=email,
                phone=phone,
                prefer_email=prefer_email,
                prefer_phone=prefer_phone,
                prefer_text=prefer_text,
                all_month=all_month,
                select_days=select_days
            )
            
            if success:
                dpg.delete_item(window_id)
                self._populate_users_table()
                with dpg.window(label="Success", width=300, pos=(150, 150)):
                    dpg.add_text("User updated successfully!")
            else:
                with dpg.window(label="Error", width=300, pos=(150, 150)):
                    dpg.add_text("Failed to update user.")
        except ValueError as e:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text(str(e))
    
    def _build_attendance_report_view(self):
        """Build the attendance report view."""
        current_year = int(__import__('datetime').date.today().year)
        years = list(range(2020, current_year + 1))
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                dpg.add_text("Filter by Month/Year")
                
                with dpg.group(horizontal=True):
                    dpg.add_combo(tag="report_month", items=months, 
                                default_value=months[__import__('datetime').date.today().month - 1])
                    dpg.add_combo(tag="report_year", items=[str(y) for y in years], 
                                default_value=str(current_year))
                
                dpg.add_spacer(height=10)
                btn_load_dates = dpg.add_button(label="Load Dates", callback=self._load_available_dates, width=-1)
                dpg.bind_item_theme(btn_load_dates, self.button_themes['primary'])
                
                dpg.add_spacer(height=15)
                
                # Filter by Day (radio button in a row)
                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by Day:")
                    dpg.add_radio_button(tag="report_day_filter", items=["All", "Thursday", "Friday"], 
                                        default_value="All", callback=self._generate_attendance_report)
                
                # Filter by Attendance (radio button in a row)
                with dpg.group(horizontal=True):
                    dpg.add_text("Filter by Attendance:")
                    dpg.add_radio_button(tag="report_attendance_filter", items=["All", "Attending", "Non-attended"], 
                                        default_value="All", callback=self._generate_attendance_report)
                
                dpg.add_spacer(height=15)
                btn_generate_report = dpg.add_button(label="Generate Report", callback=self._generate_attendance_report, width=-1)
                dpg.bind_item_theme(btn_generate_report, self.button_themes['primary'])
                
                dpg.add_spacer(height=10)
                btn_export_csv = dpg.add_button(label="Save to CSV", callback=self._export_attendance_report_csv, width=-1)
                dpg.bind_item_theme(btn_export_csv, self.button_themes['success'])
                
                if HAS_REPORTLAB:
                    dpg.add_spacer(height=10)
                    btn_export_pdf = dpg.add_button(label="Export to PDF", callback=self._export_attendance_report_pdf, width=-1)
                    dpg.bind_item_theme(btn_export_pdf, self.button_themes['success'])
            
            with dpg.group(tag="attendance_report_container"):
                with dpg.table(tag="attendance_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    dpg.add_table_column(label="Name")
                    dpg.add_table_column(label="Phone")
                    dpg.add_table_column(label="Thursdays")
                    dpg.add_table_column(label="Fridays")
    
    def _load_available_dates(self):
        """Load available dates for the selected month/year."""
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("report_month"), __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("report_year"))
        
        if not self.db:
            return
        
        # Get month record to find all dates
        month_record = self.db.get_or_create_month(selected_month, selected_year)
        thursday_dates = month_record.get('thursdays', [])
        friday_dates = month_record.get('fridays', [])
        
        # Build date options for logging (no longer displayed in UI)
        date_options = ["All Dates"]
        
        for date_str in thursday_dates:
            if len(date_str) >= 8:
                # Format: YYYYMMDD -> Thu MM/DD
                month = date_str[4:6]
                day = date_str[6:8]
                display = f"Thu {month}/{day}"
                date_options.append(display)
        
        for date_str in friday_dates:
            if len(date_str) >= 8:
                # Format: YYYYMMDD -> Fri MM/DD
                month = date_str[4:6]
                day = date_str[6:8]
                display = f"Fri {month}/{day}"
                date_options.append(display)
        
        # Note: This method is now a no-op as the specific date filter has been removed
    
    def _generate_attendance_report(self):
        """Generate attendance report based on filters."""
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("report_month"), __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("report_year"))
        day_filter = dpg.get_value("report_day_filter") if dpg.does_item_exist("report_day_filter") else "All"
        attendance_filter = dpg.get_value("report_attendance_filter") if dpg.does_item_exist("report_attendance_filter") else "All"
        
        if not self.db:
            return
        
        # Clear the entire container including totals and table
        if dpg.does_item_exist("attendance_report_container"):
            dpg.delete_item("attendance_report_container")
        
        with dpg.group(tag="attendance_report_container", parent=self.attendance_tab_id):
            # Get the report data
            report = self.db.get_attendance_report(month=selected_month, year=selected_year)
            
            # Get month record to find all dates
            month_record = self.db.get_or_create_month(selected_month, selected_year)
            thursday_dates = month_record.get('thursdays', [])
            friday_dates = month_record.get('fridays', [])
            
            # Calculate totals by day and filter records based on attendance
            thursday_totals = {}
            friday_totals = {}
            total_thursday_attendance = 0
            total_friday_attendance = 0
            
            filtered_report = []
            for record in report:
                # Count attendance for this record
                att_thursdays = record.get('att_thursdays', [])
                att_fridays = record.get('att_fridays', [])
                
                # Calculate attended days based on day filter
                thursdays_attended = sum(1 for i, present in enumerate(att_thursdays) 
                                        if present and i < len(thursday_dates)) if record.get('play_thursdays') else 0
                fridays_attended = sum(1 for i, present in enumerate(att_fridays) 
                                      if present and i < len(friday_dates)) if record.get('play_fridays') else 0
                
                # Apply attendance filter across all dates
                if attendance_filter == "Attending":
                    # Must have attended at least one day
                    if day_filter == "All":
                        if thursdays_attended == 0 and fridays_attended == 0:
                            continue
                    elif day_filter == "Thursday":
                        if thursdays_attended == 0:
                            continue
                    elif day_filter == "Friday":
                        if fridays_attended == 0:
                            continue
                elif attendance_filter == "Non-attended":
                    # Must not have attended any days
                    if day_filter == "All":
                        if thursdays_attended > 0 or fridays_attended > 0:
                            continue
                    elif day_filter == "Thursday":
                        if thursdays_attended > 0:
                            continue
                    elif day_filter == "Friday":
                        if fridays_attended > 0:
                            continue
                
                filtered_report.append(record)
            
            # Sort by last name, then first name
            filtered_report.sort(key=lambda r: (r.get('last', '').lower(), r.get('first', '').lower()))
            
            # Process Thursdays for totals
            for record in filtered_report:
                att_thursdays = record.get('att_thursdays', [])
                att_fridays = record.get('att_fridays', [])
                
                if record.get('play_thursdays'):
                    thursdays_list = record.get('thursdays_list', [])
                    for i, present in enumerate(att_thursdays):
                        if i < len(thursdays_list):
                            date_str = thursdays_list[i]
                            if present:
                                thursday_totals[date_str] = thursday_totals.get(date_str, 0) + 1
                                total_thursday_attendance += 1
                
                # Process Fridays for totals
                if record.get('play_fridays'):
                    fridays_list = record.get('fridays_list', [])
                    for i, present in enumerate(att_fridays):
                        if i < len(fridays_list):
                            date_str = fridays_list[i]
                            if present:
                                friday_totals[date_str] = friday_totals.get(date_str, 0) + 1
                                total_friday_attendance += 1
            
            # Display totals summary
            dpg.add_text(f"Attendance Report - {month_names[selected_month - 1]} {selected_year}", 
                        color=(100, 200, 255))
            
            dpg.add_spacer(height=10)
            
            if day_filter in ["All", "Thursday"]:
                dpg.add_text(f"Thursday Total: {total_thursday_attendance} attendees")
                if thursday_totals:
                    thursday_details = []
                    for date_str in sorted(thursday_totals.keys()):
                        day = date_str[6:8]  # Get DD from YYYYMMDD
                        count = thursday_totals[date_str]
                        thursday_details.append(f"{day}: {count}")
                    dpg.add_text(f"  By Date: {', '.join(thursday_details)}")
            
            if day_filter in ["All", "Friday"]:
                dpg.add_text(f"Friday Total: {total_friday_attendance} attendees")
                if friday_totals:
                    friday_details = []
                    for date_str in sorted(friday_totals.keys()):
                        day = date_str[6:8]  # Get DD from YYYYMMDD
                        count = friday_totals[date_str]
                        friday_details.append(f"{day}: {count}")
                    dpg.add_text(f"  By Date: {', '.join(friday_details)}")
            
            dpg.add_spacer(height=15)
            
            # Create grid-style attendance table like Edit Attendance
            # Determine which dates to show based on filter
            show_thursdays = day_filter in ["All", "Thursday"]
            show_fridays = day_filter in ["All", "Friday"]
            
            # Calculate total columns needed
            num_thursdays = len(thursday_dates) if show_thursdays else 0
            num_fridays = len(friday_dates) if show_fridays else 0
            max_dates = max(num_thursdays, num_fridays)
            
            with dpg.table(tag="attendance_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                           scrollX=True, scrollY=True, row_background=True,
                           borders_innerH=True, borders_outerH=True, borders_innerV=True,
                           borders_outerV=True):
                # Fixed columns for name and day type - reduced widths
                dpg.add_table_column(label="Name", width_fixed=True, init_width_or_weight=120)
                dpg.add_table_column(label="Type", width_fixed=True, init_width_or_weight=60)
                
                # Date columns - combine Thursday and Friday dates
                all_dates = []
                if show_thursdays:
                    for date_str in thursday_dates:
                        if len(date_str) >= 8:
                            month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                            all_dates.append(('Thu', month_day, date_str))
                if show_fridays:
                    for date_str in friday_dates:
                        if len(date_str) >= 8:
                            month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                            all_dates.append(('Fri', month_day, date_str))
                
                # Sort by date
                all_dates.sort(key=lambda x: x[2])
                
                # Add date columns - reduced width for more compact display
                for day_type, month_day, date_str in all_dates:
                    dpg.add_table_column(label=f"{day_type} {month_day}", width_fixed=True, init_width_or_weight=60)
                
                # Add header row with totals
                with dpg.table_row():
                    dpg.add_text("Date")
                    dpg.add_text("Total")
                    for day_type, month_day, date_str in all_dates:
                        # Show total for this date
                        if day_type == 'Thu':
                            total = thursday_totals.get(date_str, 0)
                        else:
                            total = friday_totals.get(date_str, 0)
                        dpg.add_text(str(total))
                
                # Add player rows
                for record in filtered_report:
                    # Apply day filter
                    if day_filter == "Thursday" and not record.get('play_thursdays'):
                        continue
                    if day_filter == "Friday" and not record.get('play_fridays'):
                        continue
                    
                    name = f"{record.get('first', '')} {record.get('last', '')}"
                    
                    # Add Thursday row if applicable
                    if record.get('play_thursdays') and show_thursdays:
                        att_thursdays = record.get('att_thursdays', [])
                        # Use thursdays_list from the record which has the same dates used to build att_thursdays
                        thursday_dates_from_record = record.get('thursdays_list', [])
                        with dpg.table_row():
                            dpg.add_text(name)
                            dpg.add_text("Thursday")
                            # Add attendance for each Thursday date
                            for day_type, month_day, date_str in all_dates:
                                if day_type == 'Thu':
                                    # Find index of this date in thursday_dates from record
                                    try:
                                        idx = thursday_dates_from_record.index(date_str)
                                        present = att_thursdays[idx] if idx < len(att_thursdays) else False
                                        dpg.add_text("X" if present else "")
                                    except ValueError:
                                        dpg.add_text("")
                                else:
                                    dpg.add_text("")
                    
                    # Add Friday row if applicable
                    if record.get('play_fridays') and show_fridays:
                        att_fridays = record.get('att_fridays', [])
                        # Use fridays_list from the record which has the same dates used to build att_fridays
                        friday_dates_from_record = record.get('fridays_list', [])
                        with dpg.table_row():
                            dpg.add_text(name)
                            dpg.add_text("Friday")
                            # Add attendance for each Friday date
                            for day_type, month_day, date_str in all_dates:
                                if day_type == 'Fri':
                                    # Find index of this date in friday_dates from record
                                    try:
                                        idx = friday_dates_from_record.index(date_str)
                                        present = att_fridays[idx] if idx < len(att_fridays) else False
                                        dpg.add_text("X" if present else "")
                                    except ValueError:
                                        dpg.add_text("")
                                else:
                                    dpg.add_text("")
    
    def _build_month_schedule_view(self):
        """Build the month schedule view."""
        current_year = int(__import__('datetime').date.today().year)
        years = list(range(2020, current_year + 1))
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                dpg.add_text("Month Schedule")
                
                dpg.add_combo(tag="schedule_month", items=months, default_value=months[__import__('datetime').date.today().month - 1])
                dpg.add_combo(tag="schedule_year", items=[str(y) for y in years], default_value=str(current_year))
                
                dpg.add_spacer(height=10)
                btn_generate_schedule = dpg.add_button(label="Generate Schedule", callback=self._generate_month_schedule, width=-1)
                dpg.bind_item_theme(btn_generate_schedule, self.button_themes['primary'])
            
            with dpg.group():
                with dpg.table(tag="schedule_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    dpg.add_table_column(label="Day")
                    dpg.add_table_column(label="Date")
    
    def _generate_month_schedule(self):
        """Generate month schedule."""
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("schedule_month"), __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("schedule_year"))
        
        if not self.db:
            return
        
        # Get or create the month record
        result = self.db.get_or_create_month(selected_month, selected_year)
        thursday_dates = result.get('thursdays', [])
        friday_dates = result.get('fridays', [])
        
        # Create attendance for users who play on those days
        created_count = self.db.create_attendance_for_all_month_users(selected_month, selected_year)
        if created_count > 0:
            with dpg.window(label="Attendance Created", width=400, pos=(200, 200)):
                dpg.add_text(f"Created attendance records for {created_count} 'all month' users")
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("schedule_table"):
            dpg.delete_item("schedule_table")
        
        thursdays = result.get('thursdays', [])
        fridays = result.get('fridays', [])
        
        with dpg.table(tag="schedule_table", parent=self.month_schedule_tab_id, header_row=True, policy=dpg.mvTable_SizingFixedFit,
                      scrollX=True, scrollY=True, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            dpg.add_table_column(label="Day")
            dpg.add_table_column(label="Date")
            
            # Add header row
            with dpg.table_row():
                dpg.add_text("Day")
                dpg.add_text("Date")
            
            # Parse and display Thursdays
            for i, date_str in enumerate(thursdays):
                with dpg.table_row():
                    dpg.add_text(f"Thursday {i+1}")
                    # Format: YYYYMMDD -> MM/DD/YYYY
                    if len(date_str) >= 8:
                        year = date_str[:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        dpg.add_text(f"{month}/{day}/{year}")
            
            # Parse and display Fridays
            for i, date_str in enumerate(fridays):
                with dpg.table_row():
                    dpg.add_text(f"Friday {i+1}")
                    # Format: YYYYMMDD -> MM/YYYY
                    if len(date_str) >= 8:
                        year = date_str[:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        dpg.add_text(f"{month}/{day}/{year}")
    
    def show_users_view(self):
        """Switch to users view."""
        if hasattr(self, 'tab_bar_id'):
            dpg.set_value(self.tab_bar_id, "Users")
    
    def show_attendance_report(self):
        """Switch to attendance report view."""
        if hasattr(self, 'tab_bar_id'):
            dpg.set_value(self.tab_bar_id, "Attendance Report")
    
    def show_month_schedule(self):
        """Switch to month schedule view."""
        if hasattr(self, 'tab_bar_id'):
            dpg.set_value(self.tab_bar_id, "Month Schedule")
    
    def show_all_users_report(self):
        """Switch to all users report view."""
        if hasattr(self, 'tab_bar_id'):
            dpg.set_value(self.tab_bar_id, "All Users Report")
    
    def _build_all_users_report_view(self):
        """Build the all users report view."""
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                dpg.add_text("Filter Options")
                
                dpg.add_spacer(height=10)
                dpg.add_checkbox(tag="all_users_active_only", label="Active Only", default_value=True)
                
                dpg.add_spacer(height=10)
                dpg.add_text("Play Days Filter:")
                dpg.add_combo(tag="all_users_day_filter", items=["All", "Thursdays Only", "Fridays Only"], 
                             default_value="All")
                
                dpg.add_spacer(height=10)
                dpg.add_button(label="Generate Report", callback=self._generate_all_users_report,
                              width=-1)
                
                dpg.add_spacer(height=10)
                btn_export_csv = dpg.add_button(label="Save to CSV", callback=self._export_all_users_csv, width=-1)
                dpg.bind_item_theme(btn_export_csv, self.button_themes['success'])
                
                dpg.add_spacer(height=10)
                if HAS_REPORTLAB:
                    dpg.add_button(label="Export to PDF", callback=lambda: self._export_all_users_pdf(),
                                  width=-1)
            
            with dpg.group():
                # Table without header_row=True since we'll add headers as clickable rows
                with dpg.table(tag="all_users_table", header_row=False, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    # Add columns with user data keys for sorting
                    dpg.add_table_column(label="ID", width_fixed=True, init_width_or_weight=60)
                    dpg.add_table_column(label="Last Name", width_fixed=True, init_width_or_weight=120)
                    dpg.add_table_column(label="First Name", width_fixed=True, init_width_or_weight=120)
                    dpg.add_table_column(label="Phone", width_fixed=True, init_width_or_weight=120)
                    dpg.add_table_column(label="Email", width_fixed=True, init_width_or_weight=180)
                    dpg.add_table_column(label="Active", width_fixed=True, init_width_or_weight=60)
                    dpg.add_table_column(label="Days", width_fixed=True, init_width_or_weight=80)
                    dpg.add_table_column(label="Contact Pref", width_fixed=True, init_width_or_weight=100)
                
                self._populate_all_users_table()
    
    def _on_all_users_header_clicked(self, sender, app_data, user_data):
        """Handle click on column header to sort."""
        column = user_data
        
        # Toggle sort direction if clicking same column
        if self.all_users_sort_column == column:
            self.all_users_sort_reverse = not self.all_users_sort_reverse
        else:
            self.all_users_sort_column = column
            self.all_users_sort_reverse = False
        
        # Re-populate the table with new sort
        self._generate_all_users_report()
    
    def _generate_all_users_report(self):
        """Generate all users report based on filters."""
        active_only = dpg.get_value("all_users_active_only") if dpg.does_item_exist("all_users_active_only") else True
        day_filter = dpg.get_value("all_users_day_filter") if dpg.does_item_exist("all_users_day_filter") else "All"
        
        play_thursdays = None
        play_fridays = None
        
        if day_filter == "Thursdays Only":
            play_thursdays = True
        elif day_filter == "Fridays Only":
            play_fridays = True
        
        self._populate_all_users_table(active_only=active_only, 
                                       play_thursdays=play_thursdays,
                                       play_fridays=play_fridays)
    
    def _populate_all_users_table(self, active_only: bool = True,
                                  play_thursdays: Optional[bool] = None,
                                  play_fridays: Optional[bool] = None):
        """Populate the all users table."""
        if not self.db:
            return
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("all_users_table"):
            dpg.delete_item("all_users_table")
        
        # Define column headers and their sort keys
        columns = [
            ("ID", "id"),
            ("Last Name", "last"),
            ("First Name", "first"),
            ("Phone", "phone"),
            ("Email", "email"),
            ("Active", "active"),
            ("Days", "days"),
            ("Contact Pref", "contact_pref")
        ]
        
        with dpg.table(tag="all_users_table", parent=self.all_users_tab_id, header_row=False, policy=dpg.mvTable_SizingFixedFit,
                      scrollX=True, scrollY=True, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            dpg.add_table_column(label="ID", width_fixed=True, init_width_or_weight=60)
            dpg.add_table_column(label="Last Name", width_fixed=True, init_width_or_weight=120)
            dpg.add_table_column(label="First Name", width_fixed=True, init_width_or_weight=120)
            dpg.add_table_column(label="Phone", width_fixed=True, init_width_or_weight=120)
            dpg.add_table_column(label="Email", width_fixed=True, init_width_or_weight=180)
            dpg.add_table_column(label="Active", width_fixed=True, init_width_or_weight=60)
            dpg.add_table_column(label="Days", width_fixed=True, init_width_or_weight=80)
            dpg.add_table_column(label="Contact Pref", width_fixed=True, init_width_or_weight=100)
            
            # Add clickable header row
            with dpg.table_row():
                for header_text, sort_key in columns:
                    # Add sort indicator
                    if self.all_users_sort_column == sort_key:
                        indicator = " ▼" if self.all_users_sort_reverse else " ▲"
                    else:
                        indicator = ""
                    
                    dpg.add_button(label=f"{header_text}{indicator}", 
                                  callback=self._on_all_users_header_clicked,
                                  user_data=sort_key,
                                  width=-1)
            
            users = self.db.get_all_users(active_only=active_only)
            
            # Apply day preference filters
            if play_thursdays is not None:
                users = [u for u in users if u.get('play_thursdays') == play_thursdays]
            if play_fridays is not None:
                users = [u for u in users if u.get('play_fridays') == play_fridays]
            
            # Prepare users with computed fields for sorting
            users_with_data = []
            for user in users:
                days = []
                if user.get('play_thursdays'):
                    days.append("Thu")
                if user.get('play_fridays'):
                    days.append("Fri")
                
                contact_pref = []
                if user.get('prefer_email'):
                    contact_pref.append("Email")
                elif user.get('prefer_phone'):
                    contact_pref.append("Phone")
                elif user.get('prefer_text'):
                    contact_pref.append("Text")
                
                user['days'] = "/".join(days)
                user['contact_pref'] = ", ".join(contact_pref) if contact_pref else "None"
                users_with_data.append(user)
            
            # Sort users based on current sort settings
            sort_column = self.all_users_sort_column
            reverse = self.all_users_sort_reverse
            
            try:
                if sort_column in ['id', 'last', 'first', 'phone', 'email']:
                    # String/numeric sorts
                    users_with_data.sort(key=lambda u: str(u.get(sort_column, "")).lower(), reverse=reverse)
                elif sort_column == 'active':
                    # Boolean sort (Yes/No)
                    users_with_data.sort(key=lambda u: bool(u.get('active', True)), reverse=reverse)
                elif sort_column == 'days':
                    # Days string sort
                    users_with_data.sort(key=lambda u: u.get('days', ""), reverse=reverse)
                elif sort_column == 'contact_pref':
                    # Contact preference sort
                    users_with_data.sort(key=lambda u: u.get('contact_pref', ""), reverse=reverse)
            except Exception as e:
                logger.error(f"Error sorting users: {e}")
            
            for user in users_with_data:
                with dpg.table_row():
                    dpg.add_text(str(user['id']))
                    dpg.add_text(user.get('last', '') or "")
                    dpg.add_text(user.get('first', '') or "")
                    dpg.add_text(user.get('phone', 'N/A') or "N/A")
                    dpg.add_text(user.get('email', 'N/A') or "N/A")
                    dpg.add_text("Yes" if user.get('active', True) else "No")
                    dpg.add_text(user.get('days', ''))
                    dpg.add_text(user.get('contact_pref', 'None'))
    
    def _export_all_users_csv(self):
        """Export all users report to CSV with headers."""
        active_only = dpg.get_value("all_users_active_only") if dpg.does_item_exist("all_users_active_only") else True
        day_filter = dpg.get_value("all_users_day_filter") if dpg.does_item_exist("all_users_day_filter") else "All"
        
        play_thursdays = None
        play_fridays = None
        
        if day_filter == "Thursdays Only":
            play_thursdays = True
        elif day_filter == "Fridays Only":
            play_fridays = True
        
        users = self.db.get_all_users(active_only=active_only)
        
        # Apply day preference filters
        if play_thursdays is not None:
            users = [u for u in users if u.get('play_thursdays') == play_thursdays]
        if play_fridays is not None:
            users = [u for u in users if u.get('play_fridays') == play_fridays]
        
        # Build CSV headers
        headers = ["ID", "First Name", "Last Name", "Phone", "Email", "Active", "Days", "Contact Pref"]
        
        # Build CSV content
        csv_lines = [",".join(headers)]
        
        for user in users:
            days = []
            if user.get('play_thursdays'):
                days.append("Thu")
            if user.get('play_fridays'):
                days.append("Fri")
            
            contact_pref = []
            if user.get('prefer_email'):
                contact_pref.append("Email")
            elif user.get('prefer_phone'):
                contact_pref.append("Phone")
            elif user.get('prefer_text'):
                contact_pref.append("Text")
            
            row = [
                str(user.get('id', '')),
                f'"{user.get("first", "")}"',
                f'"{user.get("last", "")}"',
                f'"{user.get("phone", "")}"',
                f'"{user.get("email", "")}"',
                "Yes" if user.get('active', True) else "No",
                "/".join(days),
                ", ".join(contact_pref) if contact_pref else "None"
            ]
            csv_lines.append(",".join(row))
        
        # Create filename
        active_name = "Active" if active_only else "All"
        day_filter_name = day_filter.replace(" ", "_").replace("Only", "Only")
        filename = f"users_{active_name}_{day_filter_name}.csv"
        
        # Write CSV file
        with open(filename, 'w') as f:
            f.write('\n'.join(csv_lines) + '\n')
        
        with dpg.window(label="Success", width=300, pos=(150, 150)):
            dpg.add_text(f"CSV exported successfully: {filename}")
    
    def _export_all_users_pdf(self):
        """Export all users report to PDF."""
        if not HAS_REPORTLAB:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("reportlab library is required for PDF export.")
                dpg.add_text("Install with: pip install reportlab")
            return
        
        active_only = dpg.get_value("all_users_active_only") if dpg.does_item_exist("all_users_active_only") else True
        day_filter = dpg.get_value("all_users_day_filter") if dpg.does_item_exist("all_users_day_filter") else "All"
        
        users = self.db.get_all_users(active_only=active_only)
        
        # Apply day preference filters
        play_thursdays = None
        play_fridays = None
        
        if day_filter == "Thursdays Only":
            play_thursdays = True
        elif day_filter == "Fridays Only":
            play_fridays = True
        
        if play_thursdays is not None:
            users = [u for u in users if u.get('play_thursdays') == play_thursdays]
        if play_fridays is not None:
            users = [u for u in users if u.get('play_fridays') == play_fridays]
        
        # Create filename
        day_filter_name = "All_Days"
        if day_filter == "Thursdays Only":
            day_filter_name = "Thursdays_Only"
        elif day_filter == "Fridays Only":
            day_filter_name = "Fridays_Only"
        
        active_name = "Active" if active_only else "All"
        filename = f"users_{active_name}_{day_filter_name}.pdf"
        
        # Generate PDF
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 50, f"Bridge Attendance - All Users Report")
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 70, f"Active Only: {'Yes' if active_only else 'No'} | Filter: {day_filter}")
        
        # Subtitle
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, height - 100, "User List")
        c.setFont("Helvetica", 10)
        
        y_position = height - 130
        
        for user in users:
            if y_position < 50:  # Need new page
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 50
            
            days = []
            if user.get('play_thursdays'):
                days.append("Thu")
            if user.get('play_fridays'):
                days.append("Fri")
            
            contact_pref = []
            if user.get('prefer_email'):
                contact_pref.append("Email")
            elif user.get('prefer_phone'):
                contact_pref.append("Phone")
            elif user.get('prefer_text'):
                contact_pref.append("Text")
            
            c.drawString(72, y_position, f"{user.get('first', '')} {user.get('last', '')}")
            y_position -= 15
            c.drawString(90, y_position, f"Phone: {user.get('phone', 'N/A')} | Email: {user.get('email', 'N/A')}")
            y_position -= 15
            c.drawString(90, y_position, f"Days: {'/'.join(days)} | Contact: {', '.join(contact_pref) if contact_pref else 'None'}")
            y_position -= 20
        
        c.save()
        
        with dpg.window(label="Success", width=300, pos=(150, 150)):
            dpg.add_text(f"PDF exported successfully: {filename}")
    
    def show_about(self):
        """Show about dialog."""
        with dpg.window(label="About", width=300, pos=(200, 200)):
            dpg.add_text("Bridge Attendance Application")
            dpg.add_spacer(height=10)
            dpg.add_text("Version: 1.0.0")
            dpg.add_spacer(height=10)
            dpg.add_text("A simple attendance tracking system for bridge players.")
            dpg.add_spacer(height=10)
            dpg.add_text("Database Schema:")
            dpg.add_text("- Month_Year_Thursday_Friday: Stores schedule")
            dpg.add_text("- User: Stores player info and preferences")
            dpg.add_text("- Attendance: Tracks actual attendance")

    def _export_attendance_report_csv(self):
        """Export the filtered attendance report to CSV with headers."""
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("report_month"), date.today().month)
        selected_year = int(dpg.get_value("report_year"))
        day_filter = dpg.get_value("report_day_filter") if dpg.does_item_exist("report_day_filter") else "All"
        attendance_filter = dpg.get_value("report_attendance_filter") if dpg.does_item_exist("report_attendance_filter") else "All"
        
        if not self.db:
            return
        
        # Get the report data
        report = self.db.get_attendance_report(month=selected_month, year=selected_year)
        # Calculate totals by day and filter records based on attendance
        # Use dates from the report data (thursdays_list and fridays_list from each record)
        filtered_report = []
        for record in report:
            att_thursdays = record.get('att_thursdays', [])
            att_fridays = record.get('att_fridays', [])
            thursdays_list = record.get('thursdays_list', [])
            fridays_list = record.get('fridays_list', [])
            
            thursdays_attended = sum(1 for i, present in enumerate(att_thursdays) 
                                    if present and i < len(thursdays_list)) if record.get('play_thursdays') else 0
            fridays_attended = sum(1 for i, present in enumerate(att_fridays) 
                                  if present and i < len(fridays_list)) if record.get('play_fridays') else 0
            
            if attendance_filter == "Attending":
                if day_filter == "All":
                    if thursdays_attended == 0 and fridays_attended == 0:
                        continue
                elif day_filter == "Thursday":
                    if thursdays_attended == 0:
                        continue
                elif day_filter == "Friday":
                    if fridays_attended == 0:
                        continue
            elif attendance_filter == "Non-attended":
                if day_filter == "All":
                    if thursdays_attended > 0 or fridays_attended > 0:
                        continue
                elif day_filter == "Thursday":
                    if thursdays_attended > 0:
                        continue
                elif day_filter == "Friday":
                    if fridays_attended > 0:
                        continue
            
            filtered_report.append(record)
        
        # Sort by last name, then first name
        filtered_report.sort(key=lambda r: (r.get('last', '').lower(), r.get('first', '').lower()))
        
        # Build CSV headers using dates from the first record's thursdays_list and fridays_list
        headers = ["Name", "Phone"]
        
        # Get the combined date list for the header (from filtered records)
        # We need to use the dates that were used to build the attendance data
        combined_thursdays = []
        combined_fridays = []
        for record in filtered_report:
            combined_thursdays = record.get('thursdays_list', [])
            combined_fridays = record.get('fridays_list', [])
            if combined_thursdays or combined_fridays:
                break
        
        if day_filter in ["All", "Thursday"]:
            for date_str in combined_thursdays:
                if len(date_str) >= 8:
                    month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                    headers.append(f"Thu {month_day}")
        if day_filter in ["All", "Friday"]:
            for date_str in combined_fridays:
                if len(date_str) >= 8:
                    month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                    headers.append(f"Fri {month_day}")
        
        # Build CSV content
        csv_lines = [",".join(headers)]
        
        for record in filtered_report:
            row = [f'"{record.get("last", "")}, {record.get("first", "")}"', 
                   f'"{record.get("phone", "")}"']
            
            if day_filter in ["All", "Thursday"]:
                att_thursdays = record.get('att_thursdays', [])
                thursdays_list = record.get('thursdays_list', [])
                for date_str in combined_thursdays:
                    if len(date_str) >= 8:
                        try:
                            idx = thursdays_list.index(date_str)
                            present = att_thursdays[idx] if idx < len(att_thursdays) else False
                            row.append("X" if present else "")
                        except ValueError:
                            row.append("")
                    else:
                        row.append("")
            
            if day_filter in ["All", "Friday"]:
                att_fridays = record.get('att_fridays', [])
                fridays_list = record.get('fridays_list', [])
                for date_str in combined_fridays:
                    if len(date_str) >= 8:
                        try:
                            idx = fridays_list.index(date_str)
                            present = att_fridays[idx] if idx < len(att_fridays) else False
                            row.append("X" if present else "")
                        except ValueError:
                            row.append("")
                    else:
                        row.append("")
            
            csv_lines.append(",".join(row))
        
        # Create filename
        month_name = date(selected_year, selected_month, 1).strftime('%B')
        day_filter_suffix = day_filter.lower().replace(" ", "_")
        filename = f"attendance_{month_name}_{selected_year}_{day_filter_suffix}.csv"
        
        # Write CSV file
        with open(filename, 'w') as f:
            f.write('\n'.join(csv_lines) + '\n')
        
        with dpg.window(label="Success", width=300, pos=(150, 150)):
            dpg.add_text(f"CSV exported successfully: {filename}")
    
    def _export_attendance_report_pdf(self):
        """Export the filtered attendance report to PDF."""
        if not HAS_REPORTLAB:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("reportlab library is required for PDF export.")
                dpg.add_text("Install with: pip install reportlab")
            return
        
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("report_month"), date.today().month)
        selected_year = int(dpg.get_value("report_year"))
        day_filter = dpg.get_value("report_day_filter") if dpg.does_item_exist("report_day_filter") else "All"
        
        if not self.db:
            return
        
        # Get the report data
        report = self.db.get_attendance_report(month=selected_month, year=selected_year)
        
        # Calculate totals
        thursday_totals = {}
        friday_totals = {}
        total_thursday_attendance = 0
        total_friday_attendance = 0
        
        for record in report:
            if record.get('play_thursdays'):
                thursdays_list = record.get('thursdays_list', [])
                att_thursdays = record.get('att_thursdays', [])
                for i, present in enumerate(att_thursdays):
                    if i < len(thursdays_list):
                        date_str = thursdays_list[i]
                        if present:
                            thursday_totals[date_str] = thursday_totals.get(date_str, 0) + 1
                            total_thursday_attendance += 1
            
            if record.get('play_fridays'):
                fridays_list = record.get('fridays_list', [])
                att_fridays = record.get('att_fridays', [])
                for i, present in enumerate(att_fridays):
                    if i < len(fridays_list):
                        date_str = fridays_list[i]
                        if present:
                            friday_totals[date_str] = friday_totals.get(date_str, 0) + 1
                            total_friday_attendance += 1
        
        # Create filename
        month_name = date(selected_year, selected_month, 1).strftime('%B')
        day_filter_suffix = day_filter.lower().replace(" ", "_")
        filename = f"attendance_{month_name}_{selected_year}_{day_filter_suffix}.pdf"
        
        # Generate PDF
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 50, f"Bridge Attendance Report")
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 70, f"{month_name} {selected_year}")
        c.drawString(72, height - 85, f"Day Filter: {day_filter}")
        
        # Totals section
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, height - 115, "Attendance Totals")
        c.setFont("Helvetica", 10)
        y_position = height - 135
        
        if day_filter in ["All", "Thursday"]:
            c.drawString(72, y_position, f"Thursday Total: {total_thursday_attendance} attendees")
            y_position -= 15
            if thursday_totals:
                thursday_details = []
                for date_str in sorted(thursday_totals.keys()):
                    day = date_str[6:8]
                    count = thursday_totals[date_str]
                    thursday_details.append(f"{day}: {count}")
                c.drawString(90, y_position, f"By Date: {', '.join(thursday_details)}")
                y_position -= 15
        
        if day_filter in ["All", "Friday"]:
            c.drawString(72, y_position, f"Friday Total: {total_friday_attendance} attendees")
            y_position -= 15
            if friday_totals:
                friday_details = []
                for date_str in sorted(friday_totals.keys()):
                    day = date_str[6:8]
                    count = friday_totals[date_str]
                    friday_details.append(f"{day}: {count}")
                c.drawString(90, y_position, f"By Date: {', '.join(friday_details)}")
                y_position -= 15
        
        y_position -= 20
        
        # Player attendance section
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, y_position, "Player Attendance")
        c.setFont("Helvetica", 10)
        y_position -= 25
        
        for record in report:
            if y_position < 50:  # Need new page
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 50
            
            # Apply day filter
            if day_filter == "Thursday" and not record.get('play_thursdays'):
                continue
            if day_filter == "Friday" and not record.get('play_fridays'):
                continue
            
            name = f"{record.get('first', '')} {record.get('last', '')}"
            phone = record.get('phone', 'N/A')
            
            c.drawString(72, y_position, f"Name: {name}")
            y_position -= 15
            c.drawString(90, y_position, f"Phone: {phone}")
            y_position -= 15
            
            # Thursdays attendance
            if record.get('play_thursdays') and day_filter in ["All", "Thursday"]:
                thursdays_list = record.get('thursdays_list', [])
                att_thursdays = record.get('att_thursdays', [])
                present_days = []
                for i, present in enumerate(att_thursdays):
                    if present and i < len(thursdays_list):
                        date_str = thursdays_list[i][-2:]
                        present_days.append(date_str)
                if present_days:
                    c.drawString(90, y_position, f"Thursdays: {', '.join(present_days)}")
                    y_position -= 15
            
            # Fridays attendance
            if record.get('play_fridays') and day_filter in ["All", "Friday"]:
                fridays_list = record.get('fridays_list', [])
                att_fridays = record.get('att_fridays', [])
                present_days = []
                for i, present in enumerate(att_fridays):
                    if present and i < len(fridays_list):
                        date_str = fridays_list[i][-2:]
                        present_days.append(date_str)
                if present_days:
                    c.drawString(90, y_position, f"Fridays: {', '.join(present_days)}")
                    y_position -= 15
            
            y_position -= 10
        
        c.save()
        
        with dpg.window(label="Success", width=300, pos=(150, 150)):
            dpg.add_text(f"PDF exported successfully: {filename}")

    def export_attendance_pdf(self, month: int, year: int):
        """Export attendance report to PDF."""
        if not HAS_REPORTLAB:
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("reportlab library is required for PDF export.")
                dpg.add_text("Install with: pip install reportlab")
            return
        
        # Get attendance data
        report = self.db.get_attendance_report(month=month, year=year)
        
        # Create filename
        month_name = date(year, month, 1).strftime('%B')
        filename = f"attendance_{month_name}_{year}.pdf"
        
        # Generate PDF
        c = canvas.Canvas(filename, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 50, f"Bridge Attendance Report")
        c.setFont("Helvetica", 12)
        c.drawString(72, height - 70, f"{month_name} {year}")
        
        # Subtitle
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, height - 100, "Player Attendance")
        c.setFont("Helvetica", 10)
        
        y_position = height - 130
        
        for record in report:
            if y_position < 50:  # Need new page
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 50
            
            name = f"{record.get('first', '')} {record.get('last', '')}"
            phone = record.get('phone', 'N/A')
            
            c.drawString(72, y_position, f"Name: {name}")
            y_position -= 15
            c.drawString(90, y_position, f"Phone: {phone}")
            y_position -= 15
            
            # Thursdays attendance
            if record.get('play_thursdays'):
                thursdays_list = record.get('thursdays_list', [])
                att_thursdays = record.get('att_thursdays', [])
                present_days = []
                for i, present in enumerate(att_thursdays):
                    if present and i < len(thursdays_list):
                        date_str = thursdays_list[i][-2:]
                        present_days.append(date_str)
                if present_days:
                    c.drawString(90, y_position, f"Thursdays: {', '.join(present_days)}")
                    y_position -= 15
            
            # Fridays attendance
            if record.get('play_fridays'):
                fridays_list = record.get('fridays_list', [])
                att_fridays = record.get('att_fridays', [])
                present_days = []
                for i, present in enumerate(att_fridays):
                    if present and i < len(fridays_list):
                        date_str = fridays_list[i][-2:]
                        present_days.append(date_str)
                if present_days:
                    c.drawString(90, y_position, f"Fridays: {', '.join(present_days)}")
                    y_position -= 15
            
            y_position -= 10
        
        c.save()
        
        with dpg.window(label="Success", width=300, pos=(150, 150)):
            dpg.add_text(f"PDF exported successfully: {filename}")

    def _show_quick_attendance_dialog(self):
        """Show dialog for quick attendance update via phone or name."""
        current_year = int(date.today().year)
        current_month = date.today().month
        years = list(range(2020, current_year + 1))
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.window(label="Quick Attendance Update", width=500, pos=(100, 100)) as window_id:
            with dpg.group():
                dpg.add_combo(tag="quick_attendance_month", items=months, 
                             default_value=months[current_month - 1])
                dpg.add_combo(tag="quick_attendance_year", items=[str(y) for y in years], 
                             default_value=str(current_year))
                
                dpg.add_spacer(height=10)
                dpg.add_text("Search by Name or Phone:")
                dpg.add_input_text(tag="quick_attendance_search", label="Name or Phone")
                
                dpg.add_button(label="Find User", callback=lambda: self._quick_attendance_find_user(
                    window_id, "quick_attendance_search"))
                
                # Placeholder for user selection
                with dpg.group(tag="quick_attendance_user_section", show=False):
                    dpg.add_spacer(height=10)
                    dpg.add_text("Select User:", tag="quick_attendance_user_label")
                    
                    dpg.add_spacer(height=10)
                    dpg.add_text("Attendance Options:")
                    dpg.add_checkbox(tag="quick_attendance_thursdays", label="Attending Thursday")
                    dpg.add_checkbox(tag="quick_attendance_fridays", label="Attending Friday")
                    
                    dpg.add_button(label="Save Attendance", 
                                  callback=lambda: self._quick_attendance_save(window_id))
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))

    def _quick_attendance_find_user(self, window_id, search_tag):
        """Find user for quick attendance update."""
        search_text = dpg.get_value(search_tag)
        
        if not search_text:
            return
        
        # Search by phone or name
        users = []
        if len(search_text) >= 3 and search_text.isdigit():
            user = self.db.get_user_by_phone(search_text)
            if user:
                users.append(user)
        else:
            users = self.db.search_users(search_text)
        
        if not users:
            with dpg.window(label="Not Found", width=300, pos=(150, 150)):
                dpg.add_text("No user found matching search criteria.")
                return
        
        # Show user selection
        user_section = "quick_attendance_user_section"
        
        if dpg.does_item_exist(user_section):
            dpg.show_item(user_section)
            
            # Update user label with options
            user_options = [f"{u['first']} {u['last']} ({u.get('phone', 'N/A')})" for u in users]
            dpg.delete_item("quick_attendance_user_label")
            
            with dpg.group(parent=window_id, before="quick_attendance_thursdays"):
                dpg.add_text("Select User:", tag="quick_attendance_user_label")
                dpg.add_combo(tag="quick_attendance_user_select", items=user_options, width=-1)
    
    def _quick_attendance_save(self, window_id):
        """Save quick attendance update."""
        user_select = "quick_attendance_user_select"
        
        if not dpg.does_item_exist(user_select):
            return
        
        selected_index = dpg.get_value(user_select)
        # Parse the selected user info
        # This would need to be implemented based on actual selection mechanism

    def _build_edit_attendance_view(self):
        """Build the edit attendance view."""
        current_year = int(__import__('datetime').date.today().year)
        years = list(range(2020, current_year + 1))
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                dpg.add_text("Edit Attendance")
                
                dpg.add_combo(tag="edit_attendance_month", items=months, 
                             default_value=months[__import__('datetime').date.today().month - 1])
                dpg.add_combo(tag="edit_attendance_year", items=[str(y) for y in years], 
                             default_value=str(current_year))
                
                dpg.add_spacer(height=10)
                dpg.add_text("Select User:")
                dpg.add_input_text(tag="edit_attendance_search", label="Name or Phone")
                dpg.add_button(label="Find User", callback=self._edit_attendance_find_user, width=-1)
                
                # Placeholder for user selection and attendance table
                with dpg.group(tag="edit_attendance_user_section", show=False):
                    dpg.add_spacer(height=10)
                    dpg.add_text("Selected User:", tag="edit_attendance_user_label_static")
                    dpg.add_spacer(height=10)
                    dpg.add_text("Attendance Data:")
                    # This will be populated dynamically
                    
                dpg.add_spacer(height=20)
                # Create the save button with a proper tag
                dpg.add_button(label="Save Changes", callback=self._save_edit_attendance, 
                              width=-1, show=False, tag="edit_attendance_save_button")
            
            # Right side container for the attendance table
            with dpg.group(tag="edit_attendance_right_panel"):
                dpg.add_text("Select a user to edit attendance")
        
        # Initialize the attendance data storage
        self.edit_attendance_data = {'thursdays': [], 'fridays': []}
        self.edit_attendance_original = {'thursdays': [], 'fridays': []}  # For tracking changes
        self.edit_attendance_dirty = False  # Track if there are unsaved changes
        self.current_edit_user = None  # Track the current user being edited
    
    def _edit_attendance_find_user(self):
        """Find user for attendance editing."""
        logger.debug("Edit Attendance Find User called")
        # Check if there are unsaved changes before searching for a new user
        if self._check_unsaved_changes():
            logger.debug("Unsaved changes detected, showing confirmation dialog")
            # Show confirmation dialog
            self._show_unsaved_changes_dialog(
                self._do_find_user
            )
        else:
            logger.debug("No unsaved changes, proceeding with search")
            # No unsaved changes, proceed directly
            self._do_find_user()
    
    def _do_find_user(self):
        """Actually find user after any confirmation dialogs."""
        search_text = dpg.get_value("edit_attendance_search")
        logger.debug(f"Do Find User called with search text: '{search_text}'")
        
        if not search_text:
            return
        
        # Search by phone or name
        users = []
        if len(search_text) >= 3 and search_text.isdigit():
            user = self.db.get_user_by_phone(search_text)
            if user:
                users.append(user)
                logger.debug(f"Found user by phone: {user['first']} {user['last']}")
        else:
            users = self.db.search_users(search_text)
            logger.debug(f"Found {len(users)} users by name search")
        
        if not users:
            logger.debug("No users found matching search criteria")
            with dpg.window(label="Not Found", width=300, pos=(150, 150)):
                dpg.add_text("No user found matching search criteria.")
            return
        
        # Store the users for later use
        self.edit_attendance_users = users
        
        # Show user selection
        user_section = "edit_attendance_user_section"
        
        if dpg.does_item_exist(user_section):
            dpg.show_item(user_section)
            
            # Update user label with options
            user_options = [f"{u['first']} {u['last']} ({u.get('phone', 'N/A')})" for u in users]
            
            # Check if the group already exists and delete it if so
            if dpg.does_item_exist("edit_attendance_user_combo_group"):
                dpg.delete_item("edit_attendance_user_combo_group")
            
            # Check if the combo already exists and delete it if so
            if dpg.does_item_exist("edit_attendance_user_select"):
                dpg.delete_item("edit_attendance_user_select")
            
            if dpg.does_item_exist("edit_attendance_user_label"):
                dpg.delete_item("edit_attendance_user_label")
            
            with dpg.group(parent=user_section, tag="edit_attendance_user_combo_group"):
                dpg.add_text("Select from results:", tag="edit_attendance_user_label")
                dpg.add_combo(tag="edit_attendance_user_select", items=user_options, width=-1,
                             callback=self._on_user_selected, default_value=user_options[0])
        
        # Show the save button
        if dpg.does_item_exist("edit_attendance_save_button"):
            dpg.show_item("edit_attendance_save_button")
        
        # If only one user found, automatically select them
        if len(users) == 1:
            self._on_user_selected("edit_attendance_user_select", None)
    
    def _on_user_selected(self, sender, app_data):
        """Handle user selection from combo box."""
        if not hasattr(self, 'edit_attendance_users'):
            return
        
        # Get the selected value - dpg.get_value returns the selected item text, not index
        selected_value = dpg.get_value("edit_attendance_user_select")
        
        # Find the user by matching the combo box text
        selected_user = None
        for user in self.edit_attendance_users:
            user_text = f"{user['first']} {user['last']} ({user.get('phone', 'N/A')})"
            if user_text == selected_value:
                selected_user = user
                break
        
        if not selected_user:
            return
        
        # Check if the selected user is the same as the current user (no change)
        if hasattr(self, 'current_edit_user') and self.current_edit_user == selected_user['id']:
            return
        
        # Check if there are unsaved changes before switching users
        if self._check_unsaved_changes():
            # Store the new user ID for later use
            new_user_id = selected_user['id']
            
            # Show confirmation dialog with the previous user ID to restore if canceled
            previous_user_id = self.current_edit_user
            self._show_unsaved_changes_dialog_with_restore(
                self._do_build_attendance_table,
                new_user_id,
                previous_user_id
            )
        else:
            # No unsaved changes, proceed directly
            self._do_build_attendance_table(selected_user['id'])
    
    def _do_build_attendance_table(self, user_id: int):
        """Actually build the attendance table after any confirmation dialogs."""
        # Get the selected month and year
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("edit_attendance_month"), 
                                      __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("edit_attendance_year"))
        
        # Get or create the month record
        month_record = self.db.get_or_create_month(selected_month, selected_year)
        
        # Build the attendance table for this user and month
        self._build_attendance_table(month_record, user_id)
    
    def _save_edit_attendance(self):
        """Save attendance changes."""
        logger.debug("_save_edit_attendance called")
        
        # Use the current user being edited instead of trying to find from combo box
        if not hasattr(self, 'current_edit_user') or self.current_edit_user is None:
            logger.error("No user is currently selected for editing")
            with dpg.window(label="Error", width=300, pos=(150, 150)):
                dpg.add_text("No user is currently selected for editing.")
            return
        
        user_id = self.current_edit_user
        logger.debug(f"Saving attendance for user_id: {user_id}")
        
        # Get the selected month and year
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("edit_attendance_month"), 
                                      __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("edit_attendance_year"))
        
        logger.debug(f"Selected month: {selected_month}, year: {selected_year}")
        
        # Get dates from month
        result = self.db.get_or_create_month(selected_month, selected_year)
        thursday_dates = result.get('thursdays', [])
        friday_dates = result.get('fridays', [])
        
        logger.debug(f"Thursdays: {thursday_dates}, Fridays: {friday_dates}")
        
        # Update the attendance data with what's in our edit_attendance_data
        if hasattr(self, 'edit_attendance_data') and 'thursdays' in self.edit_attendance_data and 'fridays' in self.edit_attendance_data:
            thursdays = self.edit_attendance_data['thursdays']
            fridays = self.edit_attendance_data['fridays']
            
            logger.debug(f"Attendance data to save - Thursdays: {thursdays}, Fridays: {fridays}")
            logger.debug(f"Data types - thursdays: {type(thursdays)}, fridays: {type(fridays)}")
            
            # Save attendance for each Thursday
            for idx, is_present in enumerate(thursdays):
                if idx < len(thursday_dates):
                    date_str = thursday_dates[idx]
                    game_id = self.db.get_game_id_by_date(date_str)
                    if game_id:
                        status = 'Present' if is_present else 'Absent'
                        self.db.update_attendance(user_id, game_id, status)
            
            # Save attendance for each Friday
            for idx, is_present in enumerate(fridays):
                if idx < len(friday_dates):
                    date_str = friday_dates[idx]
                    game_id = self.db.get_game_id_by_date(date_str)
                    if game_id:
                        status = 'Present' if is_present else 'Absent'
                        self.db.update_attendance(user_id, game_id, status)
            
            # Update original data to match saved data and reset dirty flag
            self.edit_attendance_original = {
                'thursdays': thursdays[:],
                'fridays': fridays[:]
            }
            self.edit_attendance_dirty = False
            
            logger.info(f"Successfully saved attendance for user {user_id} in month {selected_month}/{selected_year}")
            
            with dpg.window(label="Success", width=300, pos=(150, 150)):
                dpg.add_text("Attendance saved successfully!")
        else:
            logger.error("edit_attendance_data not properly initialized or missing thursdays/fridays keys")
            logger.debug(f"hasattr edit_attendance_data: {hasattr(self, 'edit_attendance_data')}")
            if hasattr(self, 'edit_attendance_data'):
                logger.debug(f"edit_attendance_data keys: {self.edit_attendance_data.keys() if isinstance(self.edit_attendance_data, dict) else 'not a dict'}")
    
    
    def _build_attendance_table(self, month_record: Dict[str, Any], user_id: int):
        """Build the attendance table for the given month and user."""
        # Clear the right panel
        right_panel = "edit_attendance_right_panel"
        if dpg.does_item_exist(right_panel):
            dpg.delete_item(right_panel, children_only=True)
        
        # Get the user info
        user = self.db.get_user(user_id)
        if not user:
            return
        
        # Track the current user being edited
        self.current_edit_user = user_id
        
        # Get dates from month record
        thursday_dates = month_record.get('thursdays', [])
        friday_dates = month_record.get('fridays', [])
        
        # Filter dates based on user preferences
        if not user.get('play_thursdays'):
            thursday_dates = []
        if not user.get('play_fridays'):
            friday_dates = []
        
        # Get selected month and year for display
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("edit_attendance_month"), 
                                      __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("edit_attendance_year"))
        
        # Get game IDs for this month's dates
        game_ids = {}
        for date_str in thursday_dates:
            game_id = self.db.get_game_id_by_date(date_str)
            if game_id:
                game_ids[f'thursday_{date_str}'] = game_id
        
        for date_str in friday_dates:
            game_id = self.db.get_game_id_by_date(date_str)
            if game_id:
                game_ids[f'friday_{date_str}'] = game_id
        
        # Build attendance data dict with presence flags for each date
        attendance_data = {'thursdays': [], 'fridays': []}
        
        # Get attendance status for each Thursday
        for date_str in thursday_dates:
            game_id = self.db.get_game_id_by_date(date_str)
            if game_id:
                status = self.db.get_attendance_status(user_id, game_id)
                attendance_data['thursdays'].append(status == 'Present' if status else None)
            else:
                attendance_data['thursdays'].append(None)
        
        # Get attendance status for each Friday
        for date_str in friday_dates:
            game_id = self.db.get_game_id_by_date(date_str)
            if game_id:
                status = self.db.get_attendance_status(user_id, game_id)
                attendance_data['fridays'].append(status == 'Present' if status else None)
            else:
                attendance_data['fridays'].append(None)
        
        # Store the data for later use in saving
        self.edit_attendance_data = {
            'thursdays': attendance_data['thursdays'][:],
            'fridays': attendance_data['fridays'][:]
        }
        
        # Store original data for change detection
        self.edit_attendance_original = {
            'thursdays': attendance_data['thursdays'][:],
            'fridays': attendance_data['fridays'][:]
        }
        
        # Reset dirty flag since we just loaded fresh data
        self.edit_attendance_dirty = False
        
        # Create the table with proper headers in the right panel
        with dpg.group(parent=right_panel):
            dpg.add_text(f"Editing attendance for {user['first']} {user['last']}")
            dpg.add_spacer(height=10)
            
            with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit,
                           scrollX=True, scrollY=True, row_background=True,
                           borders_innerH=True, borders_outerH=True, borders_innerV=True,
                           borders_outerV=True, width=600, height=400):
                
                # Add columns for User, Month/Year, Day, and then the dates
                dpg.add_table_column(label="User", width_fixed=True, init_width_or_weight=100)
                dpg.add_table_column(label="Month", width_fixed=True, init_width_or_weight=60)
                dpg.add_table_column(label="Day", width_fixed=True, init_width_or_weight=50)
                
                # Determine max number of columns needed
                max_dates = max(len(thursday_dates), len(friday_dates)) if (thursday_dates or friday_dates) else 0
                
                # Add columns for each date position
                for i in range(max_dates):
                    dpg.add_table_column(label=f"Date {i+1}", width_fixed=True, init_width_or_weight=80)
                
                # Add the Thursday row if user plays Thursdays
                if user.get('play_thursdays') and thursday_dates:
                    with dpg.table_row():
                        dpg.add_text(f"{user['first'][0]} {user['last']}")
                        dpg.add_text(f"{selected_month:02d}/{selected_year}")
                        dpg.add_text("Thursday")
                        
                        # Add thursday attendance checkboxes
                        for i, date_str in enumerate(thursday_dates):
                            if len(date_str) >= 8:
                                month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                                checked = attendance_data['thursdays'][i] if i < len(attendance_data['thursdays']) else False
                                dpg.add_checkbox(tag=f"thursday_{i}_{user_id}", 
                                               default_value=bool(checked),
                                               label=month_day,
                                               user_data={'day_type': 'thursday', 'index': i, 'date_str': date_str},
                                               callback=self._update_attendance_checkboxes)
                        
                        # Fill remaining columns if fridays has more dates
                        for i in range(len(thursday_dates), max_dates):
                            dpg.add_text("")
                
                # Add the Friday row if user plays Fridays
                if user.get('play_fridays') and friday_dates:
                    with dpg.table_row():
                        dpg.add_text(f"{user['first'][0]} {user['last']}")
                        dpg.add_text(f"{selected_month:02d}/{selected_year}")
                        dpg.add_text("Friday")
                        
                        # Add friday attendance checkboxes
                        for i, date_str in enumerate(friday_dates):
                            if len(date_str) >= 8:
                                month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                                checked = attendance_data['fridays'][i] if i < len(attendance_data['fridays']) else False
                                dpg.add_checkbox(tag=f"friday_{i}_{user_id}", 
                                               default_value=bool(checked),
                                               label=month_day,
                                               user_data={'day_type': 'friday', 'index': i, 'date_str': date_str},
                                               callback=self._update_attendance_checkboxes)
                        
                        # Fill remaining columns if thursdays has more dates
                        for i in range(len(friday_dates), max_dates):
                            dpg.add_text("")
    
    def _update_attendance_checkboxes(self, sender: str, app_data: Any, user_data: Any):
        """Update the attendance data when checkboxes are changed."""
        # Get the current checkbox state
        is_checked = dpg.get_value(sender)
        
        # Extract day_type and index from user_data
        day_type = user_data.get('day_type') if isinstance(user_data, dict) else None
        index = user_data.get('index') if isinstance(user_data, dict) else None
        
        logger.debug(f"_update_attendance_checkboxes called: sender={sender}, day_type={day_type}, index={index}, is_checked={is_checked}")
        
        # Initialize edit_attendance_data if it doesn't exist or is invalid
        if not hasattr(self, 'edit_attendance_data') or not isinstance(self.edit_attendance_data, dict):
            logger.debug("Initializing edit_attendance_data")
            self.edit_attendance_data = {'thursdays': [], 'fridays': []}
        
        # Ensure the lists exist and are not None
        if 'thursdays' not in self.edit_attendance_data or self.edit_attendance_data['thursdays'] is None:
            logger.debug("Initializing thursdays list")
            self.edit_attendance_data['thursdays'] = []
        if 'fridays' not in self.edit_attendance_data or self.edit_attendance_data['fridays'] is None:
            logger.debug("Initializing fridays list")
            self.edit_attendance_data['fridays'] = []
        
        # Validate that day_type and index are valid
        if day_type is None or index is None:
            logger.warning(f"Invalid user_data: day_type={day_type}, index={index}, returning without update")
            return
        
        # Update the edit_attendance_data
        if day_type == 'thursday':
            # Ensure the list is long enough
            while len(self.edit_attendance_data['thursdays']) <= index:
                self.edit_attendance_data['thursdays'].append(False)
            self.edit_attendance_data['thursdays'][index] = is_checked
            logger.debug(f"Updated thursday[{index}] to {is_checked}. Thursdays list: {self.edit_attendance_data['thursdays']}")
        elif day_type == 'friday':
            # Ensure the list is long enough
            while len(self.edit_attendance_data['fridays']) <= index:
                self.edit_attendance_data['fridays'].append(False)
            self.edit_attendance_data['fridays'][index] = is_checked
            logger.debug(f"Updated friday[{index}] to {is_checked}. Fridays list: {self.edit_attendance_data['fridays']}")
        
        # Mark as dirty (has unsaved changes)
        self.edit_attendance_dirty = True
        logger.debug(f"edit_attendance_dirty set to True")
    
    def _check_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes in the attendance data."""
        if not hasattr(self, 'edit_attendance_dirty') or not self.edit_attendance_dirty:
            return False
        
        # Also compare current data with original
        if hasattr(self, 'edit_attendance_data') and hasattr(self, 'edit_attendance_original'):
            current_thurs = self.edit_attendance_data.get('thursdays', [])
            current_fri = self.edit_attendance_data.get('fridays', [])
            original_thurs = self.edit_attendance_original.get('thursdays', [])
            original_fri = self.edit_attendance_original.get('fridays', [])
            
            if current_thurs != original_thurs or current_fri != original_fri:
                return True
        
        return self.edit_attendance_dirty
    
    def _show_unsaved_changes_dialog(self, callback, *args, **kwargs):
        """Show a dialog asking the user what to do with unsaved changes.
        
        Args:
            callback: The function to call if user chooses to proceed
            *args, **kwargs: Arguments to pass to the callback
        """
        with dpg.window(label="Unsaved Changes", width=400, pos=(200, 200)) as window_id:
            dpg.add_text("You have unsaved changes.")
            dpg.add_spacer(height=10)
            dpg.add_text("Do you want to discard them and continue?")
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Discard & Continue", 
                              callback=lambda: self._discard_and_proceed(window_id, callback, *args, **kwargs))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _discard_and_proceed(self, window_id, callback, *args, **kwargs):
        """Discard unsaved changes and proceed with the callback."""
        self.edit_attendance_dirty = False
        dpg.delete_item(window_id)
        callback(*args, **kwargs)
    
    def _show_unsaved_changes_dialog_with_restore(self, callback, new_user_id: int, previous_user_id: int):
        """Show a dialog asking the user what to do with unsaved changes.
        
        Args:
            callback: The function to call if user chooses to proceed
            new_user_id: The new user ID to switch to
            previous_user_id: The previous user ID to restore if canceled
        """
        with dpg.window(label="Unsaved Changes", width=400, pos=(200, 200)) as window_id:
            dpg.add_text("You have unsaved changes.")
            dpg.add_spacer(height=10)
            dpg.add_text("Do you want to discard them and continue?")
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Discard & Continue", 
                              callback=lambda: self._discard_and_proceed(window_id, callback, new_user_id))
                dpg.add_button(label="Cancel", 
                              callback=lambda: self._restore_user_selection(window_id, previous_user_id))
    
    def _restore_user_selection(self, window_id, previous_user_id: int):
        """Restore the dropdown to the previous user selection when canceled."""
        dpg.delete_item(window_id)
        
        # Find the previous user in the list and restore the dropdown selection
        if hasattr(self, 'edit_attendance_users') and previous_user_id is not None:
            for user in self.edit_attendance_users:
                if user['id'] == previous_user_id:
                    user_text = f"{user['first']} {user['last']} ({user.get('phone', 'N/A')})"
                    dpg.set_value("edit_attendance_user_select", user_text)
                    break

    # SQL Reports functionality - delegated to SQLReportsManager
    def _build_sql_reports_view(self):
        """Build the SQL Reports view using SQLReportsManager."""
        if not hasattr(self, '_sql_reports_manager'):
            # Pass the app instance so manager can access db after it's connected
            self._sql_reports_manager = SQLReportsManager(self, self.sql_reports_tab_id)
        self._sql_reports_manager.build_view()


def main():
    """Main entry point for the application."""
    try:
        import dearpygui.dearpygui as dpg
        app = BridgeApp()
        app.run()
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install dearpygui: pip install dearpygui")
        from database import Database
        db_path = Path(__file__).parent / "bridge_attendance.db"
        db = Database(str(db_path))
        db.connect()
        
        print("\nRunning in console mode...")
        while True:
            print("\n1. View Users")
            print("2. Add User (console only)")
            print("3. Search Users")
            print("4. Generate Month Schedule")
            print("5. Exit")
            
            choice = input("\nEnter your choice: ").strip()
            
            if choice == "1":
                users = db.get_all_users()
                for user in users:
                    days = []
                    if user['play_thursdays']:
                        days.append("Thu")
                    if user['play_fridays']:
                        days.append("Fri")
                    print(f"ID: {user['id']}, Name: {user['first']} {user['last']}, "
                          f"Active: {'Yes' if user['active'] else 'No'}, Days: {','.join(days)}")
            
            elif choice == "2":
                first = input("First name: ").strip()
                last = input("Last name: ").strip()
                
                try:
                    user_id = db.create_user(
                        first=first,
                        last=last,
                        active=True,
                        play_thursdays=input("Plays Thursdays? (y/n): ").lower() == 'y',
                        play_fridays=input("Plays Friday? (y/n): ").lower() == 'y',
                        email=input("Email (optional): ").strip() or None,
                        phone=input("Phone (optional): ").strip() or None
                    )
                    print(f"User created with ID: {user_id}")
                except ValueError as e:
                    print(f"Error: {e}")
            
            elif choice == "3":
                search = input("Search term: ").strip()
                users = db.search_users(search)
                for user in users:
                    print(f"ID: {user['id']}, Name: {user['first']} {user['last']}")
            
            elif choice == "4":
                month = int(input("Month (1-12): ").strip())
                year = int(input("Year: ").strip())
                
                result = db.get_or_create_month(month, year)
                print(f"Thursdays: {', '.join(result['thursdays'])}")
                print(f"Fridays: {', '.join(result['fridays'])}")
            
            elif choice == "5":
                break
        
        db.close()


if __name__ == "__main__":
    main()
else:
    # When imported, just expose the class without running
    pass
