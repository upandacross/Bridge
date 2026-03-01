"""
SQL Reports module for Bridge Attendance Application.
Provides Python script report CRUD operations and execution.
"""

import dearpygui.dearpygui as dpg
from datetime import date
from typing import List, Dict, Any, Optional
import csv
import json
import re
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class SQLReportsManager:
    """Manages Python Script Reports UI and functionality."""
    
    def __init__(self, app, parent_tab_id):
        self.app = app
        self.parent_tab_id = parent_tab_id
        self.sql_reports_tab_id = None
    
    @property
    def db(self):
        """Get database connection from app."""
        return self.app.db if hasattr(self.app, 'db') else None
    
    def build_view(self):
        """Build the Script Reports view with execute and CRUD buttons."""
        with dpg.group(horizontal=True):
            with dpg.group(width=250):
                dpg.add_text("Python Script Reports")
                dpg.add_spacer(height=10)
                dpg.add_button(label="Create New Report", callback=self._show_create_dialog, width=-1)
                dpg.add_spacer(height=10)
                dpg.add_button(label="Refresh Reports", callback=self._populate_table, width=-1)
            
            with dpg.group():
                with dpg.table(tag="sql_reports_table", header_row=True, policy=dpg.mvTable_SizingFixedFit,
                              scrollX=True, scrollY=True, row_background=True,
                              borders_innerH=True, borders_outerH=True, borders_innerV=True,
                              borders_outerV=True):
                    dpg.add_table_column(label="ID")
                    dpg.add_table_column(label="Name")
                    dpg.add_table_column(label="Description")
                    dpg.add_table_column(label="Script Path")
                    dpg.add_table_column(label="Parameters")
                    dpg.add_table_column(label="Execute")
                    dpg.add_table_column(label="CRUD")
                
                self._populate_table()
    
    def _populate_table(self):
        """Populate the script reports table."""
        logger.debug(f"_populate_table called, db={self.db}, parent={self.parent_tab_id}")
        
        if not self.db:
            logger.error("Database connection is None")
            self._show_error("Database connection not available", width=400)
            return
        
        # Get existing table or rebuild it
        if dpg.does_item_exist("sql_reports_table"):
            dpg.delete_item("sql_reports_table")
        
        # Load reports from database first (outside of table context)
        try:
            reports = self.db.get_all_sql_reports()
            logger.debug(f"Loaded {len(reports)} reports from database")
        except Exception as e:
            reports = []
            logger.error(f"Error loading script reports: {e}")
        
        # Now build the table
        with dpg.table(tag="sql_reports_table", parent=self.parent_tab_id, header_row=True, 
                      policy=dpg.mvTable_SizingFixedFit,
                      scrollX=True, scrollY=True, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Description")
            dpg.add_table_column(label="Script Path")
            dpg.add_table_column(label="Parameters")
            dpg.add_table_column(label="Execute")
            dpg.add_table_column(label="CRUD")
            
            # Add header row
            with dpg.table_row():
                dpg.add_text("ID")
                dpg.add_text("Name")
                dpg.add_text("Description")
                dpg.add_text("Script Path")
                dpg.add_text("Parameters")
                dpg.add_text("Execute")
                dpg.add_text("CRUD")
            
            # Check for errors
            error_occurred = False
            try:
                self.db.get_all_sql_reports()
            except Exception as e:
                error_occurred = True
                # Show error in table
                with dpg.table_row():
                    dpg.add_text("Error")
                    dpg.add_text(str(e)[:50])
                    dpg.add_text("")
                    dpg.add_text("")
                    dpg.add_text("")
                    dpg.add_text("")
                    dpg.add_text("")
            
            if error_occurred:
                return
            
            if not reports:
                # Show message when no reports exist
                with dpg.table_row():
                    dpg.add_text("-")
                    dpg.add_text("No reports found")
                    dpg.add_text("Click 'Create New Report' to add one")
                    dpg.add_text("")
                    dpg.add_text("")
                    dpg.add_text("")
                    dpg.add_text("")
                return
            
            for report in reports:
                params_list = report.get('parameters', [])
                param_count = len(params_list) if params_list else 0
                param_text = f"{param_count} parameter(s)" if param_count > 0 else "None"
                script_path = report.get('script_path', 'N/A')
                # Truncate long paths
                display_path = script_path if len(script_path) < 40 else "..." + script_path[-37:]
                
                with dpg.table_row():
                    dpg.add_text(str(report['id']))
                    dpg.add_text(report.get('name', ''))
                    dpg.add_text(report.get('description', '') or 'N/A')
                    dpg.add_text(display_path)
                    dpg.add_text(param_text)
                    
                    # Execute button column
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Execute", user_data=report['id'], 
                                      callback=self._on_execute_clicked)
                    
                    # CRUD button column  
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="CRUD", user_data=report['id'],
                                      callback=self._on_crud_clicked)
    
    def _on_execute_clicked(self, sender, app_data):
        """Handle execute button click for script report."""
        report_id = dpg.get_item_user_data(sender)
        
        if report_id is None:
            self._show_error("Could not get report ID from button")
            return
        
        report = self.db.get_sql_report(report_id)
        
        if report is None:
            self._show_error(f"Report with ID {report_id} not found")
            return
        
        # Check if report has parameters
        params = report.get('parameters', [])
        if params:
            self._show_param_dialog(report)
        else:
            self._execute_report(report_id, {})
    
    def _show_param_dialog(self, report: Dict[str, Any]):
        """Show dialog to input parameters for script execution."""
        dialog_id = f"script_param_dialog_{report['id']}_{id(report)}"
        
        with dpg.window(label=f"Enter Parameters - {report['name']}", width=400, pos=(100, 100)) as window_id:
            dpg.add_text(f"Script: {report['name']}")
            dpg.add_text(f"Path: {report.get('script_path', 'N/A')}", color=(150, 150, 150))
            dpg.add_spacer(height=10)
            
            params = report.get('parameters', [])
            for i, param in enumerate(params):
                param_name = param.get('name', f'param_{i}')
                param_type = param.get('type', 'text')
                param_label = param.get('label', param_name)
                default_val = param.get('default', '')
                
                dpg.add_input_text(tag=f"{dialog_id}_param_{i}", label=param_label, 
                                  default_value=str(default_val))
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Execute", 
                              callback=lambda: self._execute_with_params(window_id, dialog_id, report['id'], params))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _execute_with_params(self, window_id, dialog_id: str, report_id: int, params: List[Dict[str, Any]]):
        """Execute script with collected parameter values."""
        param_values = {}
        
        for i, param in enumerate(params):
            param_name = param.get('name', f'param_{i}')
            param_value = dpg.get_value(f"{dialog_id}_param_{i}")
            param_values[param_name] = param_value
        
        dpg.delete_item(window_id)
        self._execute_report(report_id, param_values)
    
    def _execute_report(self, report_id: int, param_values: Dict[str, Any]):
        """Execute Python script and show results."""
        try:
            stdout, stderr, returncode = self.db.execute_sql_report(report_id, param_values)
            
            report = self.db.get_sql_report(report_id)
            self._show_execution_results_window(report['name'], stdout, stderr, returncode, report.get('script_path', ''))
            
        except Exception as e:
            self._show_error(f"Error executing script: {str(e)}", width=400)
    
    def _show_execution_results_window(self, report_name: str, stdout: str, stderr: str, returncode: int, script_path: str):
        """Show script execution results."""
        with dpg.window(label=f"Execution Results - {report_name}", width=800, height=600, pos=(100, 100)) as window_id:
            dpg.add_text(f"Script: {report_name}")
            dpg.add_text(f"Path: {script_path}", color=(150, 150, 150))
            dpg.add_text(f"Exit Code: {returncode}", color=(0, 255, 0) if returncode == 0 else (255, 100, 100))
            dpg.add_spacer(height=10)
            
            # Save output button
            dpg.add_button(label="Save Output to File", 
                          callback=lambda: self._save_output_to_file(report_name, stdout, stderr),
                          width=-1)
            dpg.add_spacer(height=10)
            
            # Output tabs
            with dpg.tab_bar():
                with dpg.tab(label="Standard Output"):
                    if stdout:
                        dpg.add_input_text(multiline=True, readonly=True, 
                                          default_value=stdout, height=400, width=-1)
                    else:
                        dpg.add_text("(No output)", color=(150, 150, 150))
                
                with dpg.tab(label="Standard Error"):
                    if stderr:
                        dpg.add_input_text(multiline=True, readonly=True,
                                          default_value=stderr, height=400, width=-1)
                    else:
                        dpg.add_text("(No errors)", color=(150, 150, 150))
    
    def _save_output_to_file(self, report_name: str, stdout: str, stderr: str):
        """Save script output to a file."""
        from datetime import datetime
        
        safe_name = re.sub(r'[^\w\s-]', '', report_name).strip().replace(' ', '_')
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Script: {report_name}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                f.write("STANDARD OUTPUT:\n")
                f.write("-" * 50 + "\n")
                f.write(stdout if stdout else "(No output)\n")
                f.write("\n\n")
                f.write("STANDARD ERROR:\n")
                f.write("-" * 50 + "\n")
                f.write(stderr if stderr else "(No errors)\n")
            
            self._show_success(f"Output saved to: {filename}")
        except Exception as e:
            self._show_error(f"Failed to save output: {str(e)}")
    
    def _on_crud_clicked(self, sender, app_data):
        """Handle CRUD button click for script report."""
        report_id = dpg.get_item_user_data(sender)
        
        if report_id is None:
            self._show_error("Could not get report ID from button")
            return
        
        report = self.db.get_sql_report(report_id)
        
        if report is None:
            self._show_error(f"Report with ID {report_id} not found")
            return
        
        self._show_crud_dialog(report)
    
    def _show_crud_dialog(self, report: Dict[str, Any]):
        """Show CRUD dialog for managing script reports."""
        dialog_id = f"script_crud_{report['id']}_{id(report)}"
        
        with dpg.window(label=f"CRUD - {report['name']}", width=600, height=500, pos=(50, 50)) as window_id:
            dpg.add_text("Script Report Management")
            dpg.add_spacer(height=10)
            
            # Report details
            dpg.add_input_text(tag=f"{dialog_id}_name", label="Name", 
                              default_value=report.get('name', ''), width=-1)
            dpg.add_input_text(tag=f"{dialog_id}_description", label="Description",
                              default_value=report.get('description', ''), width=-1, multiline=True)
            
            dpg.add_spacer(height=10)
            dpg.add_text("Script Path:")
            dpg.add_input_text(tag=f"{dialog_id}_script_path", label="", 
                              default_value=report.get('script_path', ''),
                              width=-1)
            
            dpg.add_spacer(height=10)
            
            # Parameters section
            with dpg.collapsing_header(label="Parameters"):
                dpg.add_text("Parameters (JSON format):")
                params_json = json.dumps(report.get('parameters', []), indent=2)
                dpg.add_input_text(tag=f"{dialog_id}_params", label="",
                                  default_value=params_json, multiline=True, height=100, width=-1)
                example = 'Example: [{\"name\": \"date\", \"type\": \"text\", \"label\": \"Date (DD/MM/YYYY)\", \"default\": \"01/01/2024\"}]'
                dpg.add_text(example, color=(150, 150, 150))
            
            dpg.add_spacer(height=15)
            
            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Update", 
                              callback=lambda: self._update_report(window_id, dialog_id, report['id']))
                dpg.add_button(label="Delete", 
                              callback=lambda: self._show_delete_dialog(window_id, report['id'], report['name']))
                dpg.add_button(label="Close", callback=lambda: dpg.delete_item(window_id))
    
    def _show_create_dialog(self):
        """Show dialog to create a new script report."""
        dialog_id = "script_create_new"
        
        with dpg.window(label="Create New Script Report", width=600, height=500, pos=(50, 50)) as window_id:
            dpg.add_text("Create New Script Report")
            dpg.add_spacer(height=10)
            
            dpg.add_input_text(tag=f"{dialog_id}_name", label="Name*", width=-1)
            dpg.add_input_text(tag=f"{dialog_id}_description", label="Description", width=-1, multiline=True)
            
            dpg.add_spacer(height=10)
            dpg.add_text("Script Path*:")
            dpg.add_input_text(tag=f"{dialog_id}_script_path", label="",
                              default_value="",
                              width=-1)
            dpg.add_text("Example: ./export_attendance_csv.py", color=(150, 150, 150))
            
            dpg.add_spacer(height=10)
            
            with dpg.collapsing_header(label="Parameters"):
                dpg.add_text("Parameters (JSON format):")
                dpg.add_input_text(tag=f"{dialog_id}_params", label="",
                                  default_value="[]",
                                  multiline=True, height=100, width=-1)
                example = 'Example: [{\"name\": \"date\", \"type\": \"text\", \"label\": \"Date (DD/MM/YYYY)\", \"default\": \"01/01/2024\"}]'
                dpg.add_text(example, color=(150, 150, 150))
            
            dpg.add_spacer(height=15)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=lambda: self._save_new_report(window_id, dialog_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _save_new_report(self, window_id, dialog_id: str):
        """Save a new script report."""
        name = dpg.get_value(f"{dialog_id}_name")
        script_path = dpg.get_value(f"{dialog_id}_script_path")
        description = dpg.get_value(f"{dialog_id}_description")
        params_json = dpg.get_value(f"{dialog_id}_params")
        
        if not name or not script_path:
            self._show_error("Name and Script Path are required.")
            return
        
        # Expand relative paths
        if script_path.startswith('./') or script_path.startswith('../'):
            script_path = os.path.abspath(script_path)
        
        try:
            # Parse parameters JSON
            params = json.loads(params_json) if params_json.strip() else []
            if not isinstance(params, list):
                raise ValueError("Parameters must be a JSON array")
            
            report_id = self.db.create_sql_report(name, script_path, description, params)
            dpg.delete_item(window_id)
            self._populate_table()
            
            self._show_success(f"Script Report created with ID: {report_id}")
        except json.JSONDecodeError as e:
            self._show_error(f"Invalid JSON in parameters: {str(e)}", width=400)
        except ValueError as e:
            self._show_error(str(e), width=400)
    
    def _update_report(self, window_id, dialog_id: str, report_id: int):
        """Update an existing script report."""
        name = dpg.get_value(f"{dialog_id}_name")
        script_path = dpg.get_value(f"{dialog_id}_script_path")
        description = dpg.get_value(f"{dialog_id}_description")
        params_json = dpg.get_value(f"{dialog_id}_params")
        
        # Expand relative paths
        if script_path.startswith('./') or script_path.startswith('../'):
            script_path = os.path.abspath(script_path)
        
        try:
            # Parse parameters JSON
            params = json.loads(params_json) if params_json.strip() else []
            if not isinstance(params, list):
                raise ValueError("Parameters must be a JSON array")
            
            self.db.update_sql_report(report_id, name=name, script_path=script_path, 
                                      description=description, parameters=params)
            dpg.delete_item(window_id)
            self._populate_table()
            
            self._show_success("Script Report updated successfully!")
        except json.JSONDecodeError as e:
            self._show_error(f"Invalid JSON in parameters: {str(e)}", width=400)
        except ValueError as e:
            self._show_error(str(e), width=400)
    
    def _show_delete_dialog(self, parent_window_id, report_id: int, report_name: str):
        """Show confirmation dialog before deleting a script report."""
        with dpg.window(label="Confirm Delete", width=400, pos=(200, 200)) as window_id:
            dpg.add_text(f"Are you sure you want to delete report:")
            dpg.add_spacer(height=5)
            dpg.add_text(f"  {report_name} (ID: {report_id})")
            dpg.add_spacer(height=10)
            dpg.add_text("This action cannot be undone!", color=(255, 100, 100))
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete", 
                              callback=lambda: self._confirm_delete(window_id, parent_window_id, report_id))
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_id))
    
    def _confirm_delete(self, window_id, parent_window_id, report_id: int):
        """Actually delete the script report after confirmation."""
        try:
            success = self.db.delete_sql_report(report_id)
            dpg.delete_item(window_id)
            dpg.delete_item(parent_window_id)
            
            if success:
                self._populate_table()
                self._show_success("Script Report deleted successfully!")
            else:
                self._show_error("Failed to delete Script Report.")
        except Exception as e:
            dpg.delete_item(window_id)
            self._show_error(f"Error: {str(e)}")
    
    # Utility methods for showing dialogs
    def _show_error(self, message: str, width: int = 300):
        """Show error dialog."""
        with dpg.window(label="Error", width=width, pos=(150, 150)):
            dpg.add_text(message, wrap=width-20)
    
    def _show_info(self, message: str, width: int = 300):
        """Show info dialog."""
        with dpg.window(label="Info", width=width, pos=(150, 150)):
            dpg.add_text(message, wrap=width-20)
    
    def _show_success(self, message: str, width: int = 300):
        """Show success dialog."""
        with dpg.window(label="Success", width=width, pos=(150, 150)):
            dpg.add_text(message, wrap=width-20)