"""
Database module for Bridge Attendance Application.
Uses SQLite3 for data storage with new normalized schema.

New Schema:
- Users: Stores player information
- Games: Stores game dates (Thursday/Friday)
- Attendance: Links users to games with attendance status
"""

import sqlite3
import sys
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


class Database:
    """SQLite database manager for the bridge attendance application."""
    
    def __init__(self, db_path: str = None):
        if db_path is not None:
            self.db_path = db_path
        else:
            # Use bridge.db with the new normalized schema
            self.db_path = "bridge.db"
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
        
        # Users table - stores player information and preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first TEXT NOT NULL,
                last TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                prefer_email BOOLEAN DEFAULT 0,
                prefer_phone BOOLEAN DEFAULT 0,
                prefer_text BOOLEAN DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                play_thursdays BOOLEAN DEFAULT 0,
                play_fridays BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Games table - one row per game date (Thursday or Friday)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date TEXT NOT NULL UNIQUE,
                day_type TEXT NOT NULL CHECK(day_type IN ('Thursday', 'Friday')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance table - links Users to Games with attendance status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Unknown')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
                FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE,
                UNIQUE(user_id, game_id)
            )
        ''')
        
        # SQL_Report table - stores script reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SQL_Report (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                script_path TEXT NOT NULL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON Users(active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_play_thursdays ON Users(play_thursdays)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_play_fridays ON Users(play_fridays)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_date ON Games(game_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON Attendance(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_game_id ON Attendance(game_id)')
        
        self.conn.commit()
    
    def get_or_create_month(self, month: int, year: int) -> Dict[str, Any]:
        """Get or create games for a specific month.
        
        Returns dict with 'thursdays', 'fridays' as YYYYMMDD lists,
        and 'thursdays_str', 'fridays_str' as comma-separated strings for compatibility.
        """
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
        
        # Create games in database
        for date_str in thursdays:
            try:
                cursor.execute('''
                    INSERT INTO Games (game_date, day_type)
                    VALUES (?, 'Thursday')
                ''', (date_str,))
            except sqlite3.IntegrityError:
                # Game already exists
                pass
        
        for date_str in fridays:
            try:
                cursor.execute('''
                    INSERT INTO Games (game_date, day_type)
                    VALUES (?, 'Friday')
                ''', (date_str,))
            except sqlite3.IntegrityError:
                # Game already exists
                pass
        
        self.conn.commit()
        
        return {
            'thursdays': thursdays,
            'fridays': fridays,
            'thursdays_str': ','.join(thursdays),
            'fridays_str': ','.join(fridays)
        }
    
    def get_or_create_games_for_month(self, month: int, year: int) -> Dict[str, List[str]]:
        """Get or create games (game dates) for a specific month.
        
        Returns dict with 'thursdays' and 'fridays' lists of YYYYMMDD date strings.
        """
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
        
        # Create games in database
        for date_str in thursdays:
            try:
                cursor.execute('''
                    INSERT INTO Games (game_date, day_type)
                    VALUES (?, 'Thursday')
                ''', (date_str,))
            except sqlite3.IntegrityError:
                # Game already exists
                pass
        
        for date_str in fridays:
            try:
                cursor.execute('''
                    INSERT INTO Games (game_date, day_type)
                    VALUES (?, 'Friday')
                ''', (date_str,))
            except sqlite3.IntegrityError:
                # Game already exists
                pass
        
        self.conn.commit()
        
        return {
            'thursdays': thursdays,
            'fridays': fridays
        }
    
    def get_games_for_month(self, month: int, year: int) -> Dict[str, List[str]]:
        """Get game dates for a specific month.
        
        Returns dict with 'thursdays' and 'fridays' lists of YYYYMMDD date strings.
        """
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
        
        return {
            'thursdays': thursdays,
            'fridays': fridays
        }
    
    def get_game_id_by_date(self, date_str: str) -> Optional[int]:
        """Get game ID by date string (YYYYMMDD format)."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM Games WHERE game_date = ?', (date_str,))
        row = cursor.fetchone()
        return row['id'] if row else None
    
    def get_game_info_by_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """Get game info by date string (YYYYMMDD format)."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, game_date, day_type FROM Games WHERE game_date = ?', (date_str,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def create_user(self, first: str, last: str,
                   active: bool = True, play_thursdays: bool = False, play_fridays: bool = False,
                   email: Optional[str] = None, phone: Optional[str] = None,
                   prefer_email: bool = False, prefer_phone: bool = False, prefer_text: bool = False) -> Optional[int]:
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
        
        cursor.execute('''
            INSERT INTO Users (first, last, email, phone,
                            prefer_email, prefer_phone, prefer_text,
                            active, play_thursdays, play_fridays)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', (first, last, email, phone,
              prefer_email, prefer_phone, prefer_text,
              active, play_thursdays, play_fridays))
        
        result = cursor.fetchone()
        self.conn.commit()
        return result['id'] if result else None
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_name(self, first: str, last: str) -> Optional[Dict[str, Any]]:
        """Get a user by name."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE first = ? AND last = ?', (first, last))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get a user by phone number."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all users, optionally filtered by active status."""
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute('SELECT * FROM Users WHERE active = 1 ORDER BY last, first')
        else:
            cursor.execute('SELECT * FROM Users ORDER BY last, first')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """Search users by name, phone, or email.
        
        Searches:
        - First name alone
        - Last name alone
        - Full name (first + last)
        - Phone number
        - Email address
        """
        import re
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE active = 1 ORDER BY last, first')
        users = [dict(row) for row in cursor.fetchall()]
        
        if not search_term or not search_term.strip():
            return users
        
        try:
            pattern = re.compile(search_term, re.IGNORECASE)
            return [
                u for u in users 
                if pattern.search(u.get('first', '') or '')
                or pattern.search(u.get('last', '') or '')
                or pattern.search(f"{u['first']} {u['last']}")
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
        
        valid_fields = ['active', 'play_thursdays', 'play_fridays', 'first', 'last',
                       'email', 'phone', 'prefer_email', 'prefer_phone', 'prefer_text']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]
        
        cursor.execute(f'''
            UPDATE Users SET {set_clause}
            WHERE id = ?
        ''', values)
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user. Returns True if successful."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM Users WHERE id = ?', (user_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_or_create_attendance(self, user_id: int, game_id: int, 
                                  default_status: str = 'Present') -> str:
        """Get or create attendance record for a user at a game.
        
        Returns the attendance status ('Present', 'Absent', or 'Unknown').
        """
        cursor = self.conn.cursor()
        
        # Check if attendance exists
        cursor.execute('''
            SELECT status FROM Attendance 
            WHERE user_id = ? AND game_id = ?
        ''', (user_id, game_id))
        
        existing = cursor.fetchone()
        
        if existing:
            return existing['status']
        
        # Create default attendance record
        cursor.execute('''
            INSERT INTO Attendance (user_id, game_id, status)
            VALUES (?, ?, ?)
            RETURNING status
        ''', (user_id, game_id, default_status))
        
        result = cursor.fetchone()
        self.conn.commit()
        return result['status'] if result else default_status
    
    def update_attendance(self, user_id: int, game_id: int, status: str) -> Optional[int]:
        """Update or create attendance record. Returns the attendance ID."""
        cursor = self.conn.cursor()
        
        # Validate status
        if status not in ('Present', 'Absent', 'Unknown'):
            raise ValueError("Status must be 'Present', 'Absent', or 'Unknown'")
        
        # Check if attendance exists
        cursor.execute('SELECT id FROM Attendance WHERE user_id = ? AND game_id = ?', (user_id, game_id))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE Attendance 
                SET status = ?
                WHERE user_id = ? AND game_id = ?
            ''', (status, user_id, game_id))
            result_id = existing['id']
        else:
            cursor.execute('''
                INSERT INTO Attendance (user_id, game_id, status)
                VALUES (?, ?, ?)
                RETURNING id
            ''', (user_id, game_id, status))
            result = cursor.fetchone()
            result_id = result['id'] if result else None
        
        self.conn.commit()
        return result_id
    
    def get_attendance_status(self, user_id: int, game_id: int) -> Optional[str]:
        """Get attendance status for a user at a game."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT status FROM Attendance 
            WHERE user_id = ? AND game_id = ?
        ''', (user_id, game_id))
        
        row = cursor.fetchone()
        return row['status'] if row else None
    
    def get_month_attendance(self, month: int, year: int) -> List[Dict[str, Any]]:
        """Get attendance report for a specific month.
        
        Returns list of records with user info and attendance for each date.
        """
        cursor = self.conn.cursor()
        
        # Get games for this month
        games_info = self.get_games_for_month(month, year)
        thursday_dates = games_info['thursdays']
        friday_dates = games_info['fridays']
        
        # Build query to get all active users
        cursor.execute('''
            SELECT id, first, last, phone, email,
                   play_thursdays, play_fridays
            FROM Users
            WHERE active = 1
            ORDER BY last, first
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        
        results = []
        for user in users:
            record = {
                'user_id': user['id'],
                'first': user['first'],
                'last': user['last'],
                'phone': user['phone'],
                'email': user['email'],
                'play_thursdays': user['play_thursdays'],
                'play_fridays': user['play_fridays'],
                'att_thursdays': [],
                'att_fridays': [],
                'thursdays_list': thursday_dates,
                'fridays_list': friday_dates
            }
            
            # Get attendance for each Thursday
            for date_str in thursday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    status = self.get_attendance_status(user['id'], game_id)
                    record['att_thursdays'].append(status == 'Present')
                else:
                    record['att_thursdays'].append(None)  # Unknown
            
            # Get attendance for each Friday
            for date_str in friday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    status = self.get_attendance_status(user['id'], game_id)
                    record['att_fridays'].append(status == 'Present')
                else:
                    record['att_fridays'].append(None)  # Unknown
            
            results.append(record)
        
        return results
    
    def get_attendance_report(self, month: Optional[int] = None, year: Optional[int] = None,
                             play_thursdays: bool = False, play_fridays: bool = False,
                             active_only: bool = True) -> List[Dict[str, Any]]:
        """Get attendance report for a specific month/year and/or day preference.
        
        Only includes users who have attendance records for the specified month.
        """
        cursor = self.conn.cursor()
        
        # Get games for the month
        if month is not None and year is not None:
            games_info = self.get_games_for_month(month, year)
            thursday_dates = games_info['thursdays']
            friday_dates = games_info['fridays']
        else:
            thursday_dates = []
            friday_dates = []
        
        # Build query to get users with their attendance records
        query = '''
            SELECT u.id as user_id, u.first, u.last, u.phone, u.email,
                   u.play_thursdays, u.play_fridays
            FROM Users u
        '''
        
        params = []
        
        # Add active filter
        if active_only:
            query += ' WHERE u.active = 1'
        
        # Add day preference filters
        if play_thursdays and not play_fridays:
            if active_only:
                query += ' AND u.play_thursdays = 1'
            else:
                query += ' WHERE u.play_thursdays = 1'
        elif play_fridays and not play_thursdays:
            if active_only:
                query += ' AND u.play_fridays = 1'
            else:
                query += ' WHERE u.play_fridays = 1'
        
        query += ' ORDER BY u.last, u.first'
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            record = dict(row)
            
            # Get attendance for each date
            att_thursdays = []
            for date_str in thursday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    status = self.get_attendance_status(record['user_id'], game_id)
                    att_thursdays.append(status == 'Present' if status else None)
                else:
                    att_thursdays.append(None)
            
            att_fridays = []
            for date_str in friday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    status = self.get_attendance_status(record['user_id'], game_id)
                    att_fridays.append(status == 'Present' if status else None)
                else:
                    att_fridays.append(None)
            
            record['thursdays_list'] = thursday_dates
            record['fridays_list'] = friday_dates
            record['att_thursdays'] = att_thursdays
            record['att_fridays'] = att_fridays
            
            results.append(record)
        
        return results
    
    def create_attendance_for_all_month_users(self, month: int, year: int) -> int:
        """Create attendance records for all users with their default attendance.
        
        Returns the number of attendance records created.
        """
        cursor = self.conn.cursor()
        
        # Get games for this month
        games_info = self.get_games_for_month(month, year)
        thursday_dates = games_info['thursdays']
        friday_dates = games_info['fridays']
        
        # Get all active users
        cursor.execute('''
            SELECT id, play_thursdays, play_fridays, first, last 
            FROM Users 
            WHERE active = 1
        ''')
        users = cursor.fetchall()
        
        created_count = 0
        
        for user in users:
            user_id = user['id']
            play_thursdays = user['play_thursdays']
            play_fridays = user['play_fridays']
            
            # Create attendance records for each Thursday
            for date_str in thursday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    # Check if attendance already exists
                    cursor.execute('SELECT id FROM Attendance WHERE user_id = ? AND game_id = ?', 
                                  (user_id, game_id))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        status = 'Present' if play_thursdays else 'Absent'
                        cursor.execute('''
                            INSERT INTO Attendance (user_id, game_id, status)
                            VALUES (?, ?, ?)
                        ''', (user_id, game_id, status))
                        created_count += 1
            
            # Create attendance records for each Friday
            for date_str in friday_dates:
                game_id = self.get_game_id_by_date(date_str)
                if game_id:
                    # Check if attendance already exists
                    cursor.execute('SELECT id FROM Attendance WHERE user_id = ? AND game_id = ?', 
                                  (user_id, game_id))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        status = 'Present' if play_fridays else 'Absent'
                        cursor.execute('''
                            INSERT INTO Attendance (user_id, game_id, status)
                            VALUES (?, ?, ?)
                        ''', (user_id, game_id, status))
                        created_count += 1
        
        self.conn.commit()
        return created_count
    
    def get_all_games(self) -> List[Dict[str, Any]]:
        """Get all games in the database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM Games ORDER BY game_date')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_attendance(self, month: Optional[int] = None, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all attendance records, optionally filtered by month/year."""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT a.id, a.user_id, a.game_id, a.status, a.created_at,
                   u.first, u.last, u.phone, u.email,
                   g.game_date, g.day_type
            FROM Attendance a
            JOIN Users u ON a.user_id = u.id
            JOIN Games g ON a.game_id = g.id
        '''
        
        params = []
        
        if month is not None and year is not None:
            # Get games for this month
            games_info = self.get_games_for_month(month, year)
            all_dates = games_info['thursdays'] + games_info['fridays']
            
            # Build IN clause for date filtering
            placeholders = ','.join('?' * len(all_dates))
            query += f' WHERE g.game_date IN ({placeholders})'
            params.extend(all_dates)
        
        query += ' ORDER BY u.last, u.first, g.game_date'
        
        cursor.execute(query, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    # SQL Report CRUD methods (maintained from old schema for compatibility)
    
    def get_all_sql_reports(self) -> List[Dict[str, Any]]:
        """Get all script reports."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, description, script_path, parameters, created_at FROM SQL_Report ORDER BY name')
        reports = []
        for row in cursor.fetchall():
            record = dict(row)
            import json
            try:
                record['parameters'] = json.loads(record['parameters'])
            except (json.JSONDecodeError, TypeError):
                record['parameters'] = []
            reports.append(record)
        return reports
    
    def get_sql_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific script report by ID."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, description, script_path, parameters, created_at FROM SQL_Report WHERE id = ?', (report_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        record = dict(row)
        import json
        try:
            record['parameters'] = json.loads(record['parameters'])
        except (json.JSONDecodeError, TypeError):
            record['parameters'] = []
        return record
    
    def create_sql_report(self, name: str, script_path: str, description: str = None, parameters: List[Dict[str, Any]] = None) -> Optional[int]:
        """Create a new script report. Returns the report ID."""
        import json
        import os
        cursor = self.conn.cursor()
        
        if not name or not script_path:
            raise ValueError("Name and script_path are required")
        
        # Validate script path exists
        if not os.path.exists(script_path):
            raise ValueError(f"Script file not found: {script_path}")
        
        params_str = json.dumps(parameters if parameters else [])
        
        try:
            cursor.execute('''
                INSERT INTO SQL_Report (name, description, script_path, parameters)
                VALUES (?, ?, ?, ?)
                RETURNING id
            ''', (name, description, script_path, params_str))
            result = cursor.fetchone()
            self.conn.commit()
            return result['id'] if result else None
        except sqlite3.IntegrityError:
            raise ValueError(f"A report with name '{name}' already exists")
    
    def update_sql_report(self, report_id: int, name: str = None, script_path: str = None, 
                         description: str = None, parameters: List[Dict[str, Any]] = None) -> bool:
        """Update an existing script report."""
        import json
        import os
        cursor = self.conn.cursor()
        
        # Validate script path if provided
        if script_path is not None and not os.path.exists(script_path):
            raise ValueError(f"Script file not found: {script_path}")
        
        # Build update fields dynamically
        fields = []
        values = []
        
        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if script_path is not None:
            fields.append("script_path = ?")
            values.append(script_path)
        if description is not None:
            fields.append("description = ?")
            values.append(description)
        if parameters is not None:
            fields.append("parameters = ?")
            values.append(json.dumps(parameters))
        
        if not fields:
            return False
        
        values.append(report_id)
        
        try:
            cursor.execute(f'''
                UPDATE SQL_Report SET {', '.join(fields)}
                WHERE id = ?
            ''', values)
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValueError(f"A report with name '{name}' already exists")
    
    def delete_sql_report(self, report_id: int) -> bool:
        """Delete a script report."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM SQL_Report WHERE id = ?', (report_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def execute_sql_report(self, report_id: int, param_values: Dict[str, Any] = None) -> tuple:
        """Execute a script report (Python or SQL) and return (stdout, stderr, returncode)."""
        import subprocess
        import os
        import logging
        from pathlib import Path
        
        logger = logging.getLogger(__name__)
        
        report = self.get_sql_report(report_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")
        
        script_path = report['script_path']
        
        # Validate script exists
        if not os.path.exists(script_path):
            raise ValueError(f"Script file not found: {script_path}")
        
        # Detect if it's a SQL file (by extension)
        is_sql_file = script_path.lower().endswith('.sql')
        
        if is_sql_file:
            # Build list of parameter values from param_values dict and report parameters
            args = []
            if param_values:
                for param in report.get('parameters', []):
                    param_name = param.get('name')
                    if param_name and param_name in param_values:
                        args.append(str(param_values[param_name]))
            
            # Use sql_report_helper for SQL file execution
            # Note: param_values from report parameters are used first
            helper_param_values = args if args else None
            
            try:
                # Import and use the helper module
                import sql_report_helper
                stdout, stderr, returncode, output_file = sql_report_helper.execute_sql_report(
                    script_path=script_path,
                    db_path=self.db_path,
                    param_values=helper_param_values,
                    output_dir=str(Path(script_path).parent)
                )
                
                # Read the output file contents for stdout
                if output_file and os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        stdout_content = f.read()
                    return (stdout_content, stderr, returncode)
                else:
                    return (stdout, stderr, returncode)
            except Exception as e:
                return ("", f"Error executing SQL: {str(e)}", -1)
        else:
            # Execute Python script (original behavior)
            args = [script_path]
            if param_values:
                for param in report.get('parameters', []):
                    param_name = param.get('name')
                    if param_name and param_name in param_values:
                        args.append(str(param_values[param_name]))
            
            # Execute the script
            try:
                result = subprocess.run(
                    ['python', *args],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                return (result.stdout, result.stderr, result.returncode)
            except subprocess.TimeoutExpired:
                return ("", "Script execution timed out after 5 minutes", -1)
            except Exception as e:
                return ("", f"Error executing script: {str(e)}", -1)


def main():
    """Main entry point for the application."""
    db_path = Path(__file__).parent / "bridge.db"
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
            
            result = db.get_or_create_games_for_month(month, year)
            thursdays = result['thursdays']
            fridays = result['fridays']
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