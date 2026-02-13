"""
Database module for Bridge Attendance Application.
Uses SQLite3 for data storage.
"""

import sqlite3
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


class Database:
    """SQLite database manager for the bridge attendance application."""
    
    def __init__(self, db_path: str = "bridge_attendance.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self) -> sqlite3.Connection:
        """Connect to the SQLite database and return connection."""
        # Use check_same_thread=False to allow cross-thread operations (needed for DearPyGUI callbacks)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        self.conn.execute('PRAGMA journal_mode=WAL')
        self._create_tables()
        return self.conn
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _create_tables(self):
        """Create all required tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Month_Year_Thursday_Friday table - stores schedule for each month
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Month_Year_Thursday_Friday (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                MM NUMERIC NOT NULL,
                YYYY NUMERIC NOT NULL,
                thursdays TEXT DEFAULT '',
                fridays TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(MM, YYYY)
            )
        ''')
        
        # User table - stores player information and preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS User (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                active BOOLEAN DEFAULT 1 NOT NULL,
                play_thursdays BOOLEAN DEFAULT 0 NOT NULL,
                play_fridays BOOLEAN DEFAULT 0 NOT NULL,
                first TEXT NOT NULL,
                last TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                prefer_email BOOLEAN DEFAULT 0,
                prefer_phone BOOLEAN DEFAULT 0,
                prefer_text BOOLEAN DEFAULT 0,
                all_month BOOLEAN DEFAULT 1,
                select_days BOOLEAN DEFAULT 0,
                will_come BOOLEAN DEFAULT 0,
                will_leave BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance table - tracks actual attendance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                MYTF_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                thursdays TEXT DEFAULT '',
                fridays TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (MYTF_id) REFERENCES Month_Year_Thursday_Friday(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE,
                UNIQUE(MYTF_id, user_id)
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_active ON User(active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_play_thursdays ON User(play_thursdays)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_play_fridays ON User(play_fridays)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_mytf_id ON Attendance(MYTF_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON Attendance(user_id)')
        
        self.conn.commit()
    
    def get_or_create_month(self, month: int, year: int) -> Dict[str, Any]:
        """Get existing month record or create new one. Returns the month data."""
        cursor = self.conn.cursor()
        
        thursdays = []
        fridays = []
        
        current_date = date(year, month, 1)
        
        # Find first Thursday (weekday() returns 3 for Thursday)
        while current_date.weekday() != 3:
            current_date += timedelta(days=1)
        
        # Collect all Thursdays in the month
        while current_date.month == month:
            thursdays.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=7)
        
        # Find first Friday (weekday() returns 4 for Friday)
        current_date = date(year, month, 1)
        while current_date.weekday() != 4:
            current_date += timedelta(days=1)
        
        # Collect all Fridays in the month
        while current_date.month == month:
            fridays.append(current_date.strftime('%Y%m%d'))
            current_date += timedelta(days=7)
        
        thursdays_str = ','.join(thursdays) if thursdays else ''
        fridays_str = ','.join(fridays) if fridays else ''
        
        # Check if record exists
        cursor.execute('''
            SELECT id, thursdays, fridays, created_at FROM Month_Year_Thursday_Friday 
            WHERE MM = ? AND YYYY = ?
        ''', (month, year))
        
        existing = cursor.fetchone()
        
        if existing:
            return {
                'id': existing['id'],
                'MM': month,
                'YYYY': year,
                'thursdays': thursdays_str,
                'fridays': fridays_str,
                'created_at': str(existing['created_at']),
                'duplicate': True
            }
        
        # Create new record
        cursor.execute('''
            INSERT INTO Month_Year_Thursday_Friday (MM, YYYY, thursdays, fridays)
            VALUES (?, ?, ?, ?)
            RETURNING id, created_at
        ''', (month, year, thursdays_str, fridays_str))
        
        result = cursor.fetchone()
        self.conn.commit()
        
        return {
            'id': result['id'],
            'MM': month,
            'YYYY': year,
            'thursdays': thursdays_str,
            'fridays': fridays_str,
            'created_at': str(result['created_at']),
            'duplicate': False
        }
    
    def create_user(self, first: str, last: str,
                   active: bool = True, play_thursdays: bool = False, play_fridays: bool = False,
                   email: Optional[str] = None, phone: Optional[str] = None,
                   prefer_email: bool = False, prefer_phone: bool = False, prefer_text: bool = False,
                   all_month: bool = True, select_days: bool = False,
                   will_come: bool = False, will_leave: bool = False) -> Optional[int]:
        """Create a new user. Returns the user ID."""
        cursor = self.conn.cursor()
        
        if not first or not last:
            raise ValueError("First name and last name are required")
        
        # Validate communication preferences
        pref_count = sum([prefer_email, prefer_phone, prefer_text])
        if pref_count > 1:
            raise ValueError("Only one communication preference can be selected at a time")
        if pref_count == 0 and not email and not phone:
            raise ValueError("At least one contact method (email or phone) is required")
        
        # Validate day preferences
        if not play_thursdays and not play_fridays:
            raise ValueError("User must play on Thursday, Friday, or both")
        
        # Validate all_month/select_days
        if all_month and select_days:
            raise ValueError("Cannot have both all_month and select_days enabled")
        
        cursor.execute('''
            INSERT INTO User (active, play_thursdays, play_fridays, first, last,
                            email, phone, prefer_email, prefer_phone, prefer_text,
                            all_month, select_days, will_come, will_leave)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', (active, play_thursdays, play_fridays, first, last,
              email, phone, prefer_email, prefer_phone, prefer_text,
              all_month, select_days, will_come, will_leave))
        
        result = cursor.fetchone()
        self.conn.commit()
        return result['id'] if result else None
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM User WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_name(self, first: str, last: str) -> Optional[Dict[str, Any]]:
        """Get a user by name."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM User WHERE first = ? AND last = ?', (first, last))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get a user by phone number."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM User WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all users, optionally filtered by active status."""
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute('SELECT * FROM User WHERE active = 1 ORDER BY last, first')
        else:
            cursor.execute('SELECT * FROM User ORDER BY last, first')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """Search users by name, phone, or email."""
        import re
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM User WHERE active = 1 ORDER BY last, first')
        users = [dict(row) for row in cursor.fetchall()]
        
        try:
            pattern = re.compile(search_term, re.IGNORECASE)
            return [
                u for u in users 
                if pattern.search(f"{u['first']} {u['last']}")
                or pattern.search(u.get('phone', '') or '')
                or pattern.search(u.get('email', '') or '')
            ]
        except re.error:
            return users
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information. Returns True if successful."""
        cursor = self.conn.cursor()
        
        # Validate communication preferences
        pref_fields = ['prefer_email', 'prefer_phone', 'prefer_text']
        pref_values = [kwargs.get(f, False) for f in pref_fields]
        pref_count = sum(pref_values)
        
        if pref_count > 1:
            raise ValueError("Only one communication preference can be selected at a time")
        
        # Validate day preferences
        if kwargs.get('play_thursdays') and kwargs.get('play_fridays'):
            pass  # Both can be true
        
        if kwargs.get('all_month') and kwargs.get('select_days'):
            raise ValueError("Cannot have both all_month and select_days enabled")
        
        valid_fields = ['active', 'play_thursdays', 'play_fridays', 'first', 'last',
                       'email', 'phone', 'prefer_email', 'prefer_phone', 'prefer_text',
                       'all_month', 'select_days', 'will_come', 'will_leave']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]
        
        cursor.execute(f'''
            UPDATE User SET {set_clause}
            WHERE id = ?
        ''', values)
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user. Returns True if successful."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM User WHERE id = ?', (user_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_or_create_attendance(self, mytf_id: int, user_id: int,
                                  num_thursdays: int, num_fridays: int) -> Dict[str, List[bool]]:
        """Get or create attendance record for a user in a month."""
        cursor = self.conn.cursor()
        
        # Check if attendance exists
        cursor.execute('''
            SELECT thursdays, fridays FROM Attendance 
            WHERE MYTF_id = ? AND user_id = ?
        ''', (mytf_id, user_id))
        
        existing = cursor.fetchone()
        
        if existing:
            thursdays = [bool(int(x)) for x in existing['thursdays'].split(',') if x] if existing['thursdays'] else []
            fridays = [bool(int(x)) for x in existing['fridays'].split(',') if x] if existing['fridays'] else []
        else:
            thursdays = [False] * num_thursdays
            fridays = [False] * num_fridays
        
        return {
            'thursdays': thursdays,
            'fridays': fridays
        }
    
    def update_attendance(self, mytf_id: int, user_id: int,
                          thursdays: List[bool], fridays: List[bool]) -> Optional[int]:
        """Update or create attendance record. Returns the attendance ID."""
        cursor = self.conn.cursor()
        
        # Check if attendance exists
        cursor.execute('SELECT id FROM Attendance WHERE MYTF_id = ? AND user_id = ?', (mytf_id, user_id))
        existing = cursor.fetchone()
        
        thursdays_str = ','.join(str(int(b)) for b in thursdays) if thursdays else ''
        fridays_str = ','.join(str(int(b)) for b in fridays) if fridays else ''
        
        if existing:
            cursor.execute('''
                UPDATE Attendance 
                SET thursdays = ?, fridays = ?
                WHERE MYTF_id = ? AND user_id = ?
            ''', (thursdays_str, fridays_str, mytf_id, user_id))
            result_id = existing['id']
        else:
            cursor.execute('''
                INSERT INTO Attendance (MYTF_id, user_id, thursdays, fridays)
                VALUES (?, ?, ?, ?)
                RETURNING id
            ''', (mytf_id, user_id, thursdays_str, fridays_str))
            result = cursor.fetchone()
            result_id = result['id'] if result else None
        
        self.conn.commit()
        return result_id
    
    def get_month_by_date(self, month: int, year: int) -> Optional[Dict[str, Any]]:
        """Get a month record by MM and YYYY."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM Month_Year_Thursday_Friday 
            WHERE MM = ? AND YYYY = ?
        ''', (month, year))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_months(self) -> List[Dict[str, Any]]:
        """Get all months in the database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Month_Year_Thursday_Friday ORDER BY YYYY DESC, MM DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_month(self, month: int, year: int) -> bool:
        """Delete a month record and associated attendance records."""
        cursor = self.conn.cursor()
        
        # First get the month ID
        cursor.execute('SELECT id FROM Month_Year_Thursday_Friday WHERE MM = ? AND YYYY = ?', (month, year))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        month_id = row['id']
        
        # Delete attendance records for this month
        cursor.execute('DELETE FROM Attendance WHERE MYTF_id = ?', (month_id,))
        
        # Delete the month record
        cursor.execute('DELETE FROM Month_Year_Thursday_Friday WHERE id = ?', (month_id,))
        
        self.conn.commit()
        return True
    
    def get_attendance_report(self, month: Optional[int] = None, year: Optional[int] = None,
                             play_thursdays: bool = False, play_fridays: bool = False,
                             active_only: bool = True) -> List[Dict[str, Any]]:
        """Get attendance report for a specific month/year and/or day preference."""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT u.id as user_id, u.first, u.last, u.phone, u.email,
                   m.MM as month, m.YYYY as year, m.thursdays, m.fridays,
                   a.thursdays as attendance_thursdays, a.fridays as attendance_fridays
            FROM User u
            JOIN Attendance a ON u.id = a.user_id
            JOIN Month_Year_Thursday_Friday m ON a.MYTF_id = m.id
        '''
        
        params = []
        
        if month is not None and year is not None:
            query += ' WHERE m.MM = ? AND m.YYYY = ?'
            params.extend([month, year])
        elif month is not None:
            query += ' WHERE m.MM = ?'
            params.append(month)
        elif year is not None:
            query += ' WHERE m.YYYY = ?'
            params.append(year)
        
        if active_only:
            query += ' AND u.active = 1' if len(params) == 0 else ' AND u.active = 1'
        
        # Add day preference filters
        if play_thursdays and not play_fridays:
            query += ' WHERE u.play_thursdays = 1' if len(params) == 0 else ' AND u.play_thursdays = 1'
        elif play_fridays and not play_thursdays:
            query += ' WHERE u.play_fridays = 1' if len(params) == 0 else ' AND u.play_fridays = 1'
        
        query += ' ORDER BY u.last, u.first'
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            record = dict(row)
            
            # Parse thursdays dates
            thursdays_list = record.get('thursdays', '').split(',') if record.get('thursdays') else []
            
            # Parse attendance
            att_thursdays = [bool(int(x)) for x in record.get('attendance_thursdays', '').split(',') if x] if record.get('attendance_thursdays') else []
            att_fridays = [bool(int(x)) for x in record.get('attendance_fridays', '').split(',') if x] if record.get('attendance_fridays') else []
            
            record['thursdays_list'] = thursdays_list
            record['fridays_list'] = record.get('fridays', '').split(',') if record.get('fridays') else []
            record['att_thursdays'] = att_thursdays
            record['att_fridays'] = att_fridays
            
            results.append(record)
        
        return results
    
    def get_user_months(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all months a user has attendance records for."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT m.MM as month, m.YYYY as year
            FROM Attendance a
            JOIN Month_Year_Thursday_Friday m ON a.MYTF_id = m.id
            WHERE a.user_id = ?
            ORDER BY m.YYYY DESC, m.MM DESC
        ''', (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_month_attendance(self, mytf_id: int) -> List[Dict[str, Any]]:
        """Get all attendance records for a specific month."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.id as user_id, u.first, u.last, u.play_thursdays, u.play_fridays,
                   a.thursdays, a.fridays
            FROM Attendance a
            JOIN User u ON a.user_id = u.id
            WHERE a.MYTF_id = ?
            ORDER BY u.last, u.first
        ''', (mytf_id,))
        
        results = []
        for row in cursor.fetchall():
            record = dict(row)
            
            # Parse attendance arrays
            thursdays_str = record.get('thursdays', '')
            fridays_str = record.get('fridays', '')
            
            record['att_thursdays'] = [bool(int(x)) for x in thursdays_str.split(',') if x] if thursdays_str else []
            record['att_fridays'] = [bool(int(x)) for x in fridays_str.split(',') if x] if fridays_str else []
            
            results.append(record)
        
        return results


def main():
    """Main entry point for the application."""
    db_path = Path(__file__).parent / "bridge_attendance.db"
    db = Database(str(db_path))
    db.connect()
    
    print("=" * 50)
    print("Bridge Attendance Application - Console Mode")
    print("=" * 50)
    
    while True:
        print("\n1. View Users")
        print("2. Add User")
        print("3. Search Users")
        print("4. Generate Month Schedule")
        print("5. View Attendance Report")
        print("6. Exit")
        
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
                    phone=input("Phone (optional): ").strip() or None,
                    prefer_email=input("Prefer email? (y/n): ").lower() == 'y',
                    prefer_phone=False,
                    prefer_text=False
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
                print(f"Latest dates created: {result['created_at']}")
            else:
                print(f"Created month record for {month}/{year}")
                thursdays = result['thursdays'].split(',') if result['thursdays'] else []
                fridays = result['fridays'].split(',') if result['fridays'] else []
                print(f"Thursdays: {', '.join(thursdays)}")
                print(f"Fridays: {', '.join(fridays)}")
        
        elif choice == "5":
            month = int(input("Month (1-12): ").strip())
            year = int(input("Year: ").strip())
            
            report = db.get_attendance_report(month=month, year=year)
            print(f"\nAttendance Report for {month}/{year}")
            print("-" * 50)
            
            for record in report:
                name = f"{record['first']} {record['last']}"
                thursdays_att = [i+1 for i, v in enumerate(record['att_thursdays']) if v]
                fridays_att = [i+1 for i, v in enumerate(record['att_fridays']) if v]
                
                print(f"{name}:")
                if record.get('play_thursdays') and thursdays_att:
                    print(f"  Thursdays: {', '.join(map(str, thursdays_att))}")
                if record.get('play_fridays') and fridays_att:
                    print(f"  Fridays: {', '.join(map(str, fridays_att))}")
        
        elif choice == "6":
            break
    
    db.close()


if __name__ == "__main__":
    main()