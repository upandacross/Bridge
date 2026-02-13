"""
DearPyGUI Frontend for Bridge Attendance Application.
Provides CRUD operations and attendance tracking.
"""

import dearpygui.dearpygui as dpg
from database import Database
from pathlib import Path


class BridgeApp:
    """Main application class for the Bridge Attendance GUI."""
    
    def __init__(self, db_path: str = None):
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(__file__).parent / "bridge_attendance.db"
        self.db: Optional[Database] = None
        self.app_instance = None
        
    def run(self):
        """Run the DearPyGUI application."""
        if self.app_instance is not None:
            return  # Already running
            
        dpg.create_context()
        
        with dpg.window(label="Bridge Attendance", width=1200, height=800) as main_window:
            self.main_window_id = main_window
            
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
                
                with dpg.menu(label="View"):
                    dpg.add_menu_item(label="Users", callback=self.show_users_view)
                    dpg.add_menu_item(label="Attendance Report", callback=self.show_attendance_report)
                    dpg.add_menu_item(label="Month Schedule", callback=self.show_month_schedule)
                
                with dpg.menu(label="Help"):
                    dpg.add_menu_item(label="About", callback=self.show_about)
            
            with dpg.tab_bar() as self.tab_bar_id:
                with dpg.tab(label="Users") as self.users_tab_id:
                    self._build_users_view()
                
                with dpg.tab(label="Attendance Report") as self.attendance_tab_id:
                    self._build_attendance_report_view()
                
                with dpg.tab(label="Month Schedule") as self.month_schedule_tab_id:
                    self._build_month_schedule_view()
        
        dpg.create_viewport(title='Bridge Attendance', width=1200, height=800)
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
                dpg.add_text("Filter/Search Users")
                dpg.add_input_text(label="Search", tag="user_search_input",
                                  callback=lambda: self._filter_users())
                dpg.add_checkbox(label="Show Inactive", tag="show_inactive_checkbox",
                               callback=lambda: self._filter_users())
                
                dpg.add_spacer(height=20)
                dpg.add_button(label="Add New User", callback=self._show_add_user_dialog,
                              width=-1)
            
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
            
            # Add header row
            with dpg.table_row():
                dpg.add_text("ID")
                dpg.add_text("Name")
                dpg.add_text("Phone")
                dpg.add_text("Email")
                dpg.add_text("Active")
                dpg.add_text("Days")
            
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
                
                with dpg.table_row():
                    dpg.add_text(str(user['id']))
                    dpg.add_text(f"{user.get('first', '')} {user.get('last', '')}")
                    dpg.add_text(user.get('phone', 'N/A'))
                    dpg.add_text(user.get('email', 'N/A'))
                    dpg.add_text("Yes" if user.get('active', True) else "No")
                    dpg.add_text("/".join(days))
    
    def _show_add_user_dialog(self):
        """Show dialog to add a new user."""
        with dpg.window(label="Add New User", width=400, pos=(100, 100)) as window_id:
            with dpg.group():
                dpg.add_input_text(tag="new_user_first", label="First Name")
                dpg.add_input_text(tag="new_user_last", label="Last Name")
                
                dpg.add_checkbox(tag="new_user_active", label="Active", default_value=True)
                dpg.add_checkbox(tag="new_user_thursdays", label="Plays Thursdays", default_value=False)
                dpg.add_checkbox(tag="new_user_fridays", label="Plays Fridays", default_value=False)
                
                dpg.add_input_text(tag="new_user_phone", label="Phone Number")
                dpg.add_input_text(tag="new_user_email", label="Email")
                
                dpg.add_spacer(height=10)
                dpg.add_checkbox(tag="new_user_prefer_email", label="Prefer Email", default_value=False)
                dpg.add_checkbox(tag="new_user_prefer_phone", label="Prefer Phone", default_value=False)
                dpg.add_checkbox(tag="new_user_prefer_text", label="Prefer Text", default_value=False)
                
                dpg.add_spacer(height=10)
                dpg.add_checkbox(tag="new_user_all_month", label="All Month", default_value=True)
                dpg.add_checkbox(tag="new_user_select_days", label="Select Days", default_value=False)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=lambda: self._save_new_user(window_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
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
        all_month = dpg.get_value("new_user_all_month")
        select_days = dpg.get_value("new_user_select_days")
        
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
    
    def _build_attendance_report_view(self):
        """Build the attendance report view."""
        current_year = int(__import__('datetime').date.today().year)
        years = list(range(2020, current_year + 1))
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        
        with dpg.group(horizontal=True):
            with dpg.group(width=300):
                dpg.add_text("Filter by Month/Year")
                
                dpg.add_combo(tag="report_month", items=months, default_value=months[__import__('datetime').date.today().month - 1])
                dpg.add_combo(tag="report_year", items=[str(y) for y in years], default_value=str(current_year))
                
                dpg.add_spacer(height=10)
                dpg.add_button(label="Generate Report", callback=self._generate_attendance_report,
                              width=-1)
            
            with dpg.group():
                with dpg.table(tag="attendance_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    dpg.add_table_column(label="Name")
                    dpg.add_table_column(label="Phone")
                    dpg.add_table_column(label="Thursdays")
                    dpg.add_table_column(label="Fridays")
    
    def _generate_attendance_report(self):
        """Generate attendance report based on filters."""
        month_names = ["January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_map = {name: i + 1 for i, name in enumerate(month_names)}
        
        selected_month = month_map.get(dpg.get_value("report_month"), __import__('datetime').date.today().month)
        selected_year = int(dpg.get_value("report_year"))
        
        if not self.db:
            return
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("attendance_table"):
            dpg.delete_item("attendance_table")
        
        report = self.db.get_attendance_report(month=selected_month, year=selected_year)
        
        with dpg.table(tag="attendance_table", parent=self.attendance_tab_id, header_row=True, policy=dpg.mvTable_SizingFixedFit,
                      scrollX=True, scrollY=True, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Phone")
            dpg.add_table_column(label="Thursdays")
            dpg.add_table_column(label="Fridays")
            
            # Add header row
            with dpg.table_row():
                dpg.add_text("Name")
                dpg.add_text("Phone")
                dpg.add_text("Thursdays")
                dpg.add_text("Fridays")
            
            for record in report:
                name = f"{record.get('first', '')} {record.get('last', '')}"
                phone = record.get('phone', 'N/A')
                
                thursdays_attendance = []
                if record.get('play_thursdays'):
                    thursdays_list = record.get('thursdays_list', [])
                    att_thursdays = record.get('att_thursdays', [])
                    for i, present in enumerate(att_thursdays):
                        if present and i < len(thursdays_list):
                            date_str = thursdays_list[i][-2:]  # Get DD from YYYYMMDD
                            thursdays_attendance.append(f"Th{i+1}: {date_str}")
                
                fridays_attendance = []
                if record.get('play_fridays'):
                    fridays_list = record.get('fridays_list', [])
                    att_fridays = record.get('att_fridays', [])
                    for i, present in enumerate(att_fridays):
                        if present and i < len(fridays_list):
                            date_str = fridays_list[i][-2:]  # Get DD from YYYYMMDD
                            fridays_attendance.append(f"Fr{i+1}: {date_str}")
                
                with dpg.table_row():
                    dpg.add_text(name)
                    dpg.add_text(phone)
                    dpg.add_text(", ".join(thursdays_attendance))
                    dpg.add_text(", ".join(fridays_attendance))
    
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
                dpg.add_button(label="Generate Schedule", callback=self._generate_month_schedule,
                              width=-1)
            
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
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("schedule_table"):
            dpg.delete_item("schedule_table")
        
        thursdays = result.get('thursdays', '').split(',') if result.get('thursdays') else []
        fridays = result.get('fridays', '').split(',') if result.get('fridays') else []
        
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
                    # Format: YYYYMMDD -> MM/DD/YYYY
                    if len(date_str) >= 8:
                        year = date_str[:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        dpg.add_text(f"{month}/{day}/{year}")
    
    def show_users_view(self):
        """Switch to users view."""
        dpg.set_tab_item_open("Users", True)
    
    def show_attendance_report(self):
        """Switch to attendance report view."""
        dpg.set_tab_item_open("Attendance Report", True)
    
    def show_month_schedule(self):
        """Switch to month schedule view."""
        dpg.set_tab_item_open("Month Schedule", True)
    
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
                if result.get('duplicate'):
                    print(f"Month record already exists for {month}/{year}")
                else:
                    print(f"Created month record for {month}/{year}")
            
            elif choice == "5":
                break
        
        db.close()


if __name__ == "__main__":
    main()
else:
    # When imported, just expose the class without running
    pass
