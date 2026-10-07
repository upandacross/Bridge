#!/usr/bin/env python3
"""
Test script to validate attendance CSV against new database schema.

This script:
1. Runs the attendance_csv.sql report for each game date in bridge.db
2. Validates field types and values
3. Stores validation results for future testing
"""

import sqlite3
import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Test directory
TEST_DIR = Path(__file__).parent
BRIDGE_DB = Path(__file__).parent.parent / "bridge.db"


def validate_attendance_record(record: dict, date_str: str) -> list:
    """
    Validate a single attendance record against schema rules.
    
    Schema rules:
    - Name: string, not empty
    - Phone: string (can be empty)
    - Email: string (can be empty)
    - Preference: one of 'email', 'text', 'phone', 'none'
    - Date: YYYYMMDD format
    - Day Type: 'Thursday' or 'Friday'
    - Attendance: 'Present', 'Absent', or 'Unknown'
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    # Validate Name
    name = record.get('Name', '').strip()
    if not name:
        errors.append(f"Name is empty for date {date_str}")
    
    # Validate Preference
    preference = record.get('Preference', '').strip().lower()
    valid_preferences = ['email', 'text', 'phone', 'none']
    if preference not in valid_preferences:
        errors.append(f"Invalid preference '{preference}' for date {date_str}")
    
    # Validate Day Type
    day_type = record.get('Day Type', '').strip()
    valid_day_types = ['Thursday', 'Friday']
    if day_type not in valid_day_types:
        errors.append(f"Invalid day type '{day_type}' for date {date_str}")
    
    # Validate Attendance
    attendance = record.get('Attendance', '').strip().lower()
    valid_attendance = ['present', 'absent', 'unknown']
    if attendance not in valid_attendance:
        errors.append(f"Invalid attendance status '{attendance}' for date {date_str}")
    
    # Validate Date format (YYYYMMDD)
    if len(date_str) != 8 or not date_str.isdigit():
        errors.append(f"Invalid date format '{date_str}' (expected YYYYMMDD)")
    
    return errors


def run_validation() -> dict:
    """
    Run the attendance CSV SQL report and validate results.
    
    Returns dict with validation results.
    """
    results = {
        'start_time': datetime.now().isoformat(),
        'db_path': str(BRIDGE_DB),
        'validations': [],
        'errors': [],
        'summary': {}
    }
    
    if not BRIDGE_DB.exists():
        results['errors'].append(f"Database file not found: {BRIDGE_DB}")
        return results
    
    conn = sqlite3.connect(str(BRIDGE_DB))
    conn.row_factory = sqlite3.Row
    
    try:
        # Get all games from the database
        cursor = conn.cursor()
        cursor.execute('SELECT game_date, day_type FROM Games ORDER BY game_date')
        games = cursor.fetchall()
        
        results['summary']['total_games'] = len(games)
        
        for game in games:
            game_date = game['game_date']
            day_type = game['day_type']
            
            # Run the attendance_csv.sql for this date
            cursor.execute('''
                WITH input_date AS (
                    SELECT COALESCE(:target_date, '20260205') AS target_date
                ),
                game_info AS (
                    SELECT 
                        g.id AS game_id,
                        g.game_date,
                        g.day_type
                    FROM Games g
                    CROSS JOIN input_date id
                    WHERE g.game_date = id.target_date
                )
                SELECT 
                    u.last || ', ' || u.first AS "Name",
                    u.phone AS "Phone",
                    u.email AS "Email",
                    CASE 
                        WHEN u.prefer_email = 1 THEN 'email'
                        WHEN u.prefer_text = 1 THEN 'text'
                        WHEN u.prefer_phone = 1 THEN 'phone'
                        ELSE 'none'
                    END AS "Preference",
                    gi.game_date AS "Date",
                    gi.day_type AS "Day Type",
                    COALESCE(a.status, 'Absent') AS "Attendance"
                FROM Users u
                CROSS JOIN game_info gi
                LEFT JOIN Attendance a ON u.id = a.user_id AND a.game_id = gi.game_id
                WHERE u.active = 1
                  AND (
                      (u.play_thursdays = 1 AND gi.day_type = 'Thursday')
                      OR (u.play_fridays = 1 AND gi.day_type = 'Friday')
                  )
                ORDER BY "Name"
            ''', {'target_date': game_date})
            
            records = cursor.fetchall()
            
            game_validation = {
                'date': game_date,
                'day_type': day_type,
                'total_records': len(records),
                'valid': True,
                'record_errors': []
            }
            
            # Validate each record
            for record in records:
                record_dict = dict(record)
                errors = validate_attendance_record(record_dict, game_date)
                if errors:
                    game_validation['valid'] = False
                    game_validation['record_errors'].extend(errors)
                    for error in errors:
                        results['errors'].append(error)
            
            results['validations'].append(game_validation)
            
        # Calculate summary
        results['summary']['valid_games'] = sum(1 for v in results['validations'] if v['valid'])
        results['summary']['invalid_games'] = len(results['validations']) - results['summary']['valid_games']
        results['summary']['total_records'] = sum(v['total_records'] for v in results['validations'])
        results['summary']['total_errors'] = len(results['errors'])
        
    finally:
        conn.close()
    
    return results


def save_validation_results(results: dict):
    """Save validation results to CSV file in test_dir."""
    output_file = TEST_DIR / "attendance_validation.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Validation Timestamp', 'Database Path', 'Total Games', 
                        'Valid Games', 'Invalid Games', 'Total Records', 'Total Errors'])
        
        # Write summary row
        summary = results['summary']
        writer.writerow([
            results['start_time'],
            results['db_path'],
            summary.get('total_games', 0),
            summary.get('valid_games', 0),
            summary.get('invalid_games', 0),
            summary.get('total_records', 0),
            summary.get('total_errors', 0)
        ])
        
        # Write validation details
        writer.writerow([])
        writer.writerow(['Date', 'Day Type', 'Total Records', 'Valid', 'Errors'])
        
        for validation in results['validations']:
            errors_str = '; '.join(validation.get('record_errors', [])) if validation.get('record_errors') else ''
            writer.writerow([
                validation['date'],
                validation['day_type'],
                validation['total_records'],
                'Yes' if validation['valid'] else 'No',
                errors_str
            ])
    
    print(f"Validation results saved to: {output_file}")
    return output_file


def main():
    """Main entry point."""
    print("=" * 60)
    print("Attendance Schema Validation Test")
    print("=" * 60)
    
    results = run_validation()
    
    # Print summary
    print(f"\nDatabase: {results['db_path']}")
    print(f"Start Time: {results['start_time']}")
    print(f"\nSummary:")
    print(f"  Total Games: {results['summary'].get('total_games', 0)}")
    print(f"  Valid Games: {results['summary'].get('valid_games', 0)}")
    print(f"  Invalid Games: {results['summary'].get('invalid_games', 0)}")
    print(f"  Total Records: {results['summary'].get('total_records', 0)}")
    print(f"  Total Errors: {results['summary'].get('total_errors', 0)}")
    
    # Print sample of records from first game for inspection
    if results['validations']:
        first_game = results['validations'][0]
        print(f"\nSample from first game ({first_game['date']}):")
        print(f"  Day: {first_game['day_type']}")
        print(f"  Records: {first_game['total_records']}")
        print(f"  Valid: {first_game['valid']}")
    
    # Save results
    output_file = save_validation_results(results)
    
    # Print any errors
    if results['errors']:
        print("\nErrors Found:")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
    
    print("\n" + "=" * 60)
    if results['summary'].get('invalid_games', 0) == 0:
        print("All validations passed!")
    else:
        print(f"WARNING: {results['summary']['invalid_games']} game(s) had validation errors")
    print("=" * 60)
    
    return 0 if results['summary'].get('invalid_games', 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())