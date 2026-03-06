#!/usr/bin/env python3
"""
Export attendance CSV from bridge_attendance.db

This script exports attendance data for a specific game date (Thursday or Friday).

Usage: python export_attendance_csv.py [DD/MM[/YYYY]] [output.csv]

Parameters:
  DD/MM/YYYY - Date to export attendance for. Must be a Thursday or Friday 
               that exists in the database schedule. 
               Defaults to current month/year if not specified.
               Examples: 05/02/2026, 20/02 (uses current year)
  
  output.csv   - Optional output filename. Defaults to attendance_DDMMYYYY.csv

Examples:
  python export_attendance_csv.py 15/02/2024
  python export_attendance_csv.py 20/02/2026 my_export.csv
  python export_attendance_csv.py 20/02           (uses current year)
  python export_attendance_csv.py                 (uses today's date)
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path


def parse_date(date_str: str = None) -> tuple:
    """
    Parse date string in various formats.
    
    Supports:
    - DD/MM/YYYY (full date)
    - DD/MM (uses current year)
    - None/empty (uses today's date)
    
    Returns: (day, month, year)
    """
    from datetime import date as date_module
    
    if not date_str:
        # Use today's date
        today = date_module.today()
        return today.day, today.month, today.year
    
    # Try DD/MM/YYYY format first
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.day, dt.month, dt.year
    except ValueError:
        pass
    
    # Try DD/MM format (use current year)
    try:
        dt = datetime.strptime(date_str, "%d/%m")
        current_year = date_module.today().year
        return dt.day, dt.month, current_year
    except ValueError:
        pass
    
    print(f"Error: Invalid date format '{date_str}'. Use DD/MM/YYYY or DD/MM")
    sys.exit(1)


def get_contact_preference(user: dict) -> str:
    """Get contact preference string."""
    if user['prefer_email']:
        return 'email'
    elif user['prefer_text']:
        return 'text'
    elif user['prefer_phone']:
        return 'phone'
    return 'none'


def get_attendance_for_date(db: sqlite3.Connection, target_day: int, target_month: int, target_year: int) -> list:
    """
    Get attendance records for a specific date.
    Returns list of dicts with user info and attendance status.
    """
    
    cursor = db.cursor()
    
    # Get the month record
    cursor.execute("""
        SELECT id, thursdays, fridays 
        FROM Month_Year_Thursday_Friday 
        WHERE MM = ? AND YYYY = ?
    """, (target_month, target_year))
    
    month_record = cursor.fetchone()
    if not month_record:
        print(f"No schedule found for {target_month}/{target_year}")
        return []
    
    mytf_id, thursdays_str, fridays_str = month_record
    
    # Format target date as YYYYMMDD string for comparison
    target_date_str = f"{target_year:04d}{target_month:02d}{target_day:02d}"
    
    # Parse Thursday dates
    thursday_dates = [d.strip() for d in thursdays_str.split(',') if d.strip()] if thursdays_str else []
    friday_dates = [d.strip() for d in fridays_str.split(',') if d.strip()] if fridays_str else []
    
    # Check if target date is Thursday or Friday
    is_thursday = target_date_str in thursday_dates
    is_friday = target_date_str in friday_dates
    
    if not (is_thursday or is_friday):
        print(f"Date {target_day}/{target_month}/{target_year} is not a Thursday or Friday in the schedule")
        return []
    
    day_type = 'Thursday' if is_thursday else 'Friday'
    dates_list = thursday_dates if is_thursday else friday_dates
    position = dates_list.index(target_date_str) if target_date_str in dates_list else -1
    
    if position < 0:
        return []
    
    # Get all active users who play on this day (LEFT JOIN to include users without attendance records)
    day_filter = 'play_thursdays' if is_thursday else 'play_fridays'
    cursor.execute(f"""
        SELECT u.id, u.first, u.last, u.phone, u.email,
               u.prefer_email, u.prefer_text, u.prefer_phone,
               a.thursdays as att_thursdays, a.fridays as att_fridays
        FROM User u
        LEFT JOIN Attendance a ON u.id = a.user_id AND a.MYTF_id = ?
        WHERE u.active = 1 
          AND u.{day_filter} = 1
        ORDER BY u.last COLLATE NOCASE, u.first COLLATE NOCASE
    """, (mytf_id,))
    
    results = []
    for row in cursor.fetchall():
        user = dict(row)
        
        # Check attendance for this specific date
        # Handle case where user has no attendance record (NULL)
        att_thursdays = user.get('att_thursdays') or ''
        att_fridays = user.get('att_fridays') or ''
        
        if is_thursday:
            att_list = att_thursdays.split(',') if att_thursdays else []
            if att_list:
                attended = position < len(att_list) and att_list[position] == '1'
                attendance_status = 'Present' if attended else 'Absent'
            else:
                attendance_status = 'Unknown'
        else:
            att_list = att_fridays.split(',') if att_fridays else []
            if att_list:
                attended = position < len(att_list) and att_list[position] == '1'
                attendance_status = 'Present' if attended else 'Absent'
            else:
                attendance_status = 'Unknown'
        
        results.append({
            'name': f"{user['last']}, {user['first']}",
            'phone': user['phone'] or '',
            'email': user['email'] or '',
            'preference': get_contact_preference(user),
            'date': f"{target_day:02d}/{target_month:02d}/{target_year}",
            'attendance': attendance_status,
            'day_type': day_type
        })
    
    return results


def sort_by_preference(records: list) -> list:
    """Sort records by preference priority."""
    preference_order = {'email': 1, 'text': 2, 'phone': 3, 'none': 4}
    return sorted(records, key=lambda x: preference_order.get(x['preference'], 5))


def export_to_csv(records: list, output_file: str):
    """Export records to CSV file."""
    if not records:
        print("No records to export")
        return
    
    fieldnames = ['Name', 'Phone', 'Email', 'Preference', 'Date', 'Day Type', 'Attendance']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for record in records:
            writer.writerow({
                'Name': record['name'],
                'Phone': record['phone'],
                'Email': record['email'],
                'Preference': record['preference'],
                'Date': record['date'],
                'Day Type': record['day_type'],
                'Attendance': record['attendance']
            })
    
    print(f"Exported {len(records)} records to {output_file}")


def main():
    # Determine if first argument is a date or output file
    date_str = None
    output_file = None
    
    if len(sys.argv) >= 2:
        # Check if first argument looks like a date (contains /)
        if '/' in sys.argv[1]:
            date_str = sys.argv[1]
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
        else:
            # First arg is output file, use today's date
            output_file = sys.argv[1]
    
    # Parse date (will use today if not provided)
    target_day, target_month, target_year = parse_date(date_str)
    
    # Generate default output filename if not provided
    if not output_file:
        output_file = f"attendance_{target_day:02d}{target_month:02d}{target_year:04d}.csv"
    
    # Connect to database
    db_path = Path(__file__).parent / "bridge_attendance.db"
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Get attendance records
        records = get_attendance_for_date(conn, target_day, target_month, target_year)
        
        if records:
            # Sort by preference
            records = sort_by_preference(records)
            
            # Export to CSV
            export_to_csv(records, output_file)
        else:
            print("No attendance records found for the specified date")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()