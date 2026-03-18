#!/usr/bin/env python3
"""
SQL Report Helper - Execute parameter-driven SQL reports with proper output filenames.

This helper script:
- Takes a SQL file and parameter values
- Uses sqlite3's native parameter support via .parameter commands
- Outputs to a CSV file named <report_name>_<param1>_<paramN>.csv
"""

import subprocess
import sys
import os
import re
from pathlib import Path


def get_report_name(script_path: str) -> str:
    """Extract report name from script path (without extension)."""
    return Path(script_path).stem


def sanitize_param_value(value: str) -> str:
    """Sanitize parameter value for use in filename."""
    # Remove special characters that aren't valid in filenames
    return re.sub(r'[^\w\-]', '_', str(value))


def generate_output_filename(script_path: str, param_values: list) -> str:
    """Generate output filename based on report name and parameters."""
    report_name = get_report_name(script_path)
    sanitized_params = [sanitize_param_value(p) for p in param_values]
    
    if sanitized_params:
        return f"{report_name}_{'_'.join(sanitized_params)}.csv"
    return f"{report_name}.csv"


def execute_sql_report(
    script_path: str,
    db_path: str,
    param_values: list = None,
    output_dir: str = "."
) -> tuple:
    """
    Execute a parameter-driven SQL report.
    
    Args:
        script_path: Path to the SQL file
        db_path: Path to the SQLite database
        param_values: List of parameter values to substitute
        output_dir: Directory to save the output file
    
    Returns:
        tuple: (stdout, stderr, returncode, output_file_path)
    """
    if not os.path.exists(script_path):
        return ("", f"Error: Script file not found: {script_path}", 1, None)
    
    if not os.path.exists(db_path):
        return ("", f"Error: Database file not found: {db_path}", 1, None)
    
    # Generate output filename
    output_filename = generate_output_filename(script_path, param_values or [])
    output_path = os.path.join(output_dir, output_filename)
    
    # Build the SQL commands
    commands = [".parameter init", ".separator ','"]
    
    # Set parameters
    if param_values:
        # Read parameter names from the SQL file
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Extract parameter names (look for :param_name patterns)
        param_names = re.findall(r':(\w+)', content)
        
        # Match parameter names with values
        for i, param_name in enumerate(param_names):
            if i < len(param_values):
                value = param_values[i]
                # Escape single quotes in value
                escaped_value = str(value).replace("'", "''")
                commands.append(f".parameter set :{param_name} '{escaped_value}'")
    
    # Set output file and execute
    commands.append(f".out {output_path}")
    commands.append(f".read {script_path}")
    commands.append(".out")
    
    # Execute with sqlite3 via stdin
    sql_input = "\n".join(commands)
    
    try:
        result = subprocess.run(
            ['sqlite3', db_path],
            input=sql_input,
            capture_output=True,
            text=True,
            timeout=300
        )
        return (result.stdout, result.stderr, result.returncode, output_path)
    except subprocess.TimeoutExpired:
        return ("", "SQL execution timed out after 5 minutes", -1, None)
    except Exception as e:
        return ("", f"Error executing SQL: {str(e)}", -1, None)


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: python sql_report_helper.py <sql_script> <db_path> [param1 param2 ...]")
        print("Example: python sql_report_helper.py attendance_csv.sql bridge.db 20260319")
        sys.exit(1)
    
    script_path = sys.argv[1]
    db_path = sys.argv[2]
    param_values = sys.argv[3:] if len(sys.argv) > 3 else []
    
    stdout, stderr, returncode, output_file = execute_sql_report(
        script_path, db_path, param_values
    )
    
    if returncode == 0:
        print(f"Report executed successfully!")
        print(f"Output saved to: {output_file}")
        if stdout:
            print(f"\n{stdout}")
    else:
        print(f"Error executing report (exit code: {returncode})", file=sys.stderr)
        if stderr:
            print(f"Error details: {stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()