#!/usr/bin/env python3
"""
Migration script to transfer data from bridge_attendance.db to bridge.db
Migrates: Users, Games (from Month_Year_Thursday_Friday), and Attendance
"""

import sqlite3
import os
from datetime import datetime

def migrate_data():
    old_db = "bridge_attendance.db"
    new_db = "bridge.db"
    
    # Verify old database exists
    if not os.path.exists(old_db):
        print(f"Error: {old_db} not found")
        return False
    
    # Connect to both databases
    old_conn = sqlite3.connect(old_db)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    new_conn = sqlite3.connect(new_db)
    new_conn.row_factory = sqlite3.Row
    new_cursor = new_conn.cursor()
    
    print("=" * 60)
    print("Starting database migration...")
    print("=" * 60)
    
    # 1. Migrate Users
    print("\n1. Migrating Users...")
    old_cursor.execute('''
        SELECT id, active, play_thursdays, play_fridays, first, last,
               email, phone, prefer_email, prefer_phone, prefer_text,
               created_at
        FROM User
        ORDER BY id
    ''')
    users = old_cursor.fetchall()
    
    for user in users:
        new_cursor.execute('''
            INSERT INTO Users (id, first, last, email, phone,
                              prefer_email, prefer_phone, prefer_text,
                              active, play_thursdays, play_fridays, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['id'],
            user['first'],
            user['last'],
            user['email'],
            user['phone'],
            user['prefer_email'],
            user['prefer_phone'],
            user['prefer_text'],
            user['active'],
            user['play_thursdays'],
            user['play_fridays'],
            user['created_at']
        ))
    
    print(f"   Migrated {len(users)} users")
    
    # 2. Migrate Games (from Month_Year_Thursday_Friday)
    print("\n2. Migrating Games...")
    old_cursor.execute('SELECT * FROM Month_Year_Thursday_Friday ORDER BY id')
    months = old_cursor.fetchall()
    
    games_created = 0
    for month in months:
        # Parse Thursday dates
        if month['thursdays']:
            for date_str in month['thursdays'].split(','):
                if date_str.strip():
                    new_cursor.execute('''
                        INSERT INTO Games (game_date, day_type, created_at)
                        VALUES (?, 'Thursday', ?)
                    ''', (date_str.strip(), month['created_at']))
                    games_created += 1
        
        # Parse Friday dates
        if month['fridays']:
            for date_str in month['fridays'].split(','):
                if date_str.strip():
                    new_cursor.execute('''
                        INSERT INTO Games (game_date, day_type, created_at)
                        VALUES (?, 'Friday', ?)
                    ''', (date_str.strip(), month['created_at']))
                    games_created += 1
    
    print(f"   Migrated {games_created} game dates from {len(months)} month records")
    
    # 3. Migrate Attendance
    print("\n3. Migrating Attendance...")
    old_cursor.execute('''
        SELECT a.id, a.MYTF_id, a.user_id, a.thursdays, a.fridays, a.created_at
        FROM Attendance a
        ORDER BY a.id
    ''')
    attendance_records = old_cursor.fetchall()
    
    # Get all month-game mappings
    month_games = {}  # {mytf_id: {date_str: game_id}}
    old_cursor.execute('SELECT id, thursdays, fridays FROM Month_Year_Thursday_Friday')
    for month in old_cursor.fetchall():
        month_games[month['id']] = {}
        if month['thursdays']:
            for date_str in month['thursdays'].split(','):
                if date_str.strip():
                    month_games[month['id']][date_str.strip()] = 'Thursday'
        if month['fridays']:
            for date_str in month['fridays'].split(','):
                if date_str.strip():
                    month_games[month['id']][date_str.strip()] = 'Friday'
    
    attendance_migrated = 0
    for record in attendance_records:
        mytf_id = record['MYTF_id']
        user_id = record['user_id']
        thursdays_att = record['thursdays']
        fridays_att = record['fridays']
        
        # Process Thursday attendance
        if thursdays_att and mytf_id in month_games:
            dates = [d for d in month_games[mytf_id].keys() if month_games[mytf_id][d] == 'Thursday']
            for i, date_str in enumerate(dates):
                if i < len(thursdays_att):
                    status = 'Present' if thursdays_att[i] == '1' else 'Absent'
                    
                    # Find game_id for this date
                    new_cursor.execute('SELECT id FROM Games WHERE game_date = ?', (date_str,))
                    game = new_cursor.fetchone()
                    if game:
                        new_cursor.execute('''
                            INSERT INTO Attendance (user_id, game_id, status, created_at)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, game['id'], status, record['created_at']))
                        attendance_migrated += 1
        
        # Process Friday attendance
        if fridays_att and mytf_id in month_games:
            dates = [d for d in month_games[mytf_id].keys() if month_games[mytf_id][d] == 'Friday']
            for i, date_str in enumerate(dates):
                if i < len(fridays_att):
                    status = 'Present' if fridays_att[i] == '1' else 'Absent'
                    
                    # Find game_id for this date
                    new_cursor.execute('SELECT id FROM Games WHERE game_date = ?', (date_str,))
                    game = new_cursor.fetchone()
                    if game:
                        new_cursor.execute('''
                            INSERT INTO Attendance (user_id, game_id, status, created_at)
                            VALUES (?, ?, ?, ?)
                        ''', (user_id, game['id'], status, record['created_at']))
                        attendance_migrated += 1
    
    print(f"   Migrated {attendance_migrated} attendance records")
    
    # Commit and verify
    new_conn.commit()
    
    # Verification
    print("\n" + "=" * 60)
    print("Migration Summary:")
    print("=" * 60)
    new_cursor.execute('SELECT COUNT(*) FROM Users')
    print(f"   Total Users: {new_cursor.fetchone()[0]}")
    new_cursor.execute('SELECT COUNT(*) FROM Games')
    print(f"   Total Games: {new_cursor.fetchone()[0]}")
    new_cursor.execute('SELECT COUNT(*) FROM Attendance')
    print(f"   Total Attendance Records: {new_cursor.fetchone()[0]}")
    print("=" * 60)
    
    old_conn.close()
    new_conn.close()
    
    print("\nMigration completed successfully!")
    return True

if __name__ == "__main__":
    migrate_data()