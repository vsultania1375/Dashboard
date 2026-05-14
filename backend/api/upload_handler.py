"""
Data Upload Handler for VProtect Dashboard
Handles Excel/CSV file uploads with validation, transformation, and database loading
"""

import io
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime
import hashlib

class DataValidator:
    """Validates uploaded data against expected schema"""
    
    # Expected columns for each data type
    SCHEMA = {
        "engineers": [
            "engineer_code", "engineer_name", "state", "designation", 
            "active_status", "phone", "email", "service_area_code"
        ],
        "offline_sites": [
            "site_id", "site_name", "state", "segment", "last_online_date",
            "offline_duration_days", "priority"
        ],
        "attendance": [
            "engineer_code", "attendance_date", "check_in_time", "check_out_time",
            "status"  # OnTime, Late, Absent
        ],
        "visits": [
            "engineer_code", "site_id", "visit_date", "visit_type", 
            "problem_solved", "problem_description", "time_taken_minutes"
        ],
        "tickets": [
            "ticket_id", "site_id", "engineer_code", "ticket_status", 
            "created_date", "closed_date", "priority", "category"
        ]
    }
    
    @staticmethod
    def validate_column_names(df: pd.DataFrame, expected_schema: List[str]) -> Tuple[bool, List[str]]:
        """Validate that uploaded data has required columns"""
        df_columns = [col.strip().lower() for col in df.columns]
        expected_columns = [col.lower() for col in expected_schema]
        
        missing_columns = set(expected_columns) - set(df_columns)
        extra_columns = set(df_columns) - set(expected_columns)
        
        errors = []
        if missing_columns:
            errors.append(f"Missing columns: {', '.join(missing_columns)}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_data_types(df: pd.DataFrame, data_type: str) -> Tuple[bool, List[str]]:
        """Validate data types in the dataframe"""
        errors = []
        
        if data_type == "engineers":
            # Validate engineer code format
            if 'engineer_code' in df.columns:
                invalid_codes = df[df['engineer_code'].astype(str).str.len() != 3]
                if len(invalid_codes) > 0:
                    errors.append(f"Engineer codes must be 3 digits: {len(invalid_codes)} invalid rows")
            
            # Validate active_status
            if 'active_status' in df.columns:
                invalid_status = df[~df['active_status'].isin(['YES', 'NO'])]
                if len(invalid_status) > 0:
                    errors.append(f"active_status must be YES or NO: {len(invalid_status)} invalid rows")
        
        elif data_type == "offline_sites":
            # Validate segment (PSU banks only)
            if 'segment' in df.columns:
                invalid_segment = df[df['segment'] != 'PSU']
                if len(invalid_segment) > 0:
                    errors.append(f"Segment must be PSU (found {len(invalid_segment)} non-PSU rows)")
        
        elif data_type == "attendance":
            # Validate attendance status
            if 'status' in df.columns:
                valid_statuses = ['OnTime', 'Late', 'Absent']
                invalid_status = df[~df['status'].isin(valid_statuses)]
                if len(invalid_status) > 0:
                    errors.append(f"Status must be OnTime/Late/Absent: {len(invalid_status)} invalid rows")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_no_duplicates(df: pd.DataFrame, data_type: str, key_columns: List[str]) -> Tuple[bool, List[str]]:
        """Check for duplicate rows"""
        errors = []
        
        if key_columns and all(col in df.columns for col in key_columns):
            duplicates = df[df.duplicated(subset=key_columns, keep=False)]
            if len(duplicates) > 0:
                errors.append(f"Found {len(duplicates)} duplicate rows based on {key_columns}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_no_nulls(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """Check for null values in required columns"""
        errors = []
        
        for col in required_columns:
            if col in df.columns:
                nulls = df[df[col].isnull()]
                if len(nulls) > 0:
                    errors.append(f"Column '{col}' has {len(nulls)} null values")
        
        return len(errors) == 0, errors


class DataTransformer:
    """Transforms raw uploaded data into database-ready format"""
    
    @staticmethod
    def transform_engineers(df: pd.DataFrame) -> pd.DataFrame:
        """Transform engineers data"""
        df = df.copy()
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure engineer_code is zero-padded string (preserve leading zeros)
        df['engineer_code'] = df['engineer_code'].astype(str).str.zfill(3)
        
        # Filter to active engineers with Engineer designation
        df = df[
            (df['active_status'] == 'YES') & 
            (df['designation'].str.upper() == 'ENGINEER')
        ]
        
        # Add system fields
        df['created_at'] = datetime.utcnow()
        df['updated_at'] = datetime.utcnow()
        
        return df.drop_duplicates(subset=['engineer_code'])
    
    @staticmethod
    def transform_offline_sites(df: pd.DataFrame) -> pd.DataFrame:
        """Transform offline sites data"""
        df = df.copy()
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Filter to PSU banks only
        df = df[df['segment'] == 'PSU']
        
        # Convert dates
        df['last_online_date'] = pd.to_datetime(df['last_online_date'], errors='coerce')
        
        # Calculate offline days if not provided
        if 'offline_duration_days' not in df.columns:
            df['offline_duration_days'] = (
                datetime.now() - df['last_online_date']
            ).dt.days
        
        # Add priority if missing (based on offline days)
        if 'priority' not in df.columns:
            df['priority'] = df['offline_duration_days'].apply(
                lambda x: 'CRITICAL' if x > 60 else 'HIGH' if x > 30 else 'MEDIUM' if x > 15 else 'LOW'
            )
        
        # Add system fields
        df['created_at'] = datetime.utcnow()
        df['updated_at'] = datetime.utcnow()
        
        return df.drop_duplicates(subset=['site_id'])
    
    @staticmethod
    def transform_attendance(df: pd.DataFrame) -> pd.DataFrame:
        """Transform attendance data"""
        df = df.copy()
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure engineer code is zero-padded
        df['engineer_code'] = df['engineer_code'].astype(str).str.zfill(3)
        
        # Convert date
        df['attendance_date'] = pd.to_datetime(df['attendance_date'], errors='coerce')
        
        # Recalculate attendance status based on check_in_time
        if 'check_in_time' in df.columns:
            df['status'] = df.apply(
                lambda row: 'Absent' if pd.isnull(row['check_in_time']) 
                else 'OnTime' if pd.to_datetime(row['check_in_time']).hour < 10
                else 'Late',
                axis=1
            )
        
        # Add system fields
        df['created_at'] = datetime.utcnow()
        df['updated_at'] = datetime.utcnow()
        
        return df
    
    @staticmethod
    def transform_visits(df: pd.DataFrame) -> pd.DataFrame:
        """Transform visit data"""
        df = df.copy()
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure engineer code is zero-padded
        df['engineer_code'] = df['engineer_code'].astype(str).str.zfill(3)
        
        # Convert dates
        df['visit_date'] = pd.to_datetime(df['visit_date'], errors='coerce')
        
        # Ensure visit_type is valid
        valid_types = ['Site Survey', 'Maintenance', 'Repair', 'Installation', 'Inspection']
        df['visit_type'] = df['visit_type'].apply(
            lambda x: x if x in valid_types else 'Inspection'
        )
        
        # Add system fields
        df['created_at'] = datetime.utcnow()
        df['updated_at'] = datetime.utcnow()
        
        return df
    
    @staticmethod
    def transform_tickets(df: pd.DataFrame) -> pd.DataFrame:
        """Transform ticket data"""
        df = df.copy()
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Ensure engineer code is zero-padded
        df['engineer_code'] = df['engineer_code'].astype(str).str.zfill(3)
        
        # Convert dates
        df['created_date'] = pd.to_datetime(df['created_date'], errors='coerce')
        df['closed_date'] = pd.to_datetime(df['closed_date'], errors='coerce')
        
        # Validate ticket status
        valid_statuses = ['OPEN', 'PENDING', 'SENTBACK', 'COMPLETED', 'CLOSED', 'CANCELLED', 'REJECTED']
        df['ticket_status'] = df['ticket_status'].apply(
            lambda x: x.upper() if x.upper() in valid_statuses else 'OPEN'
        )
        
        # Add system fields
        df['created_at'] = datetime.utcnow()
        df['updated_at'] = datetime.utcnow()
        
        return df


class UploadProcessor:
    """Main processor for file uploads"""
    
    @staticmethod
    def remove_blank_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Remove completely blank rows (all NaN or all whitespace)
        Returns: (cleaned_dataframe, number_of_rows_removed)
        """
        initial_count = len(df)
        
        # Mark rows as blank if:
        # 1. All values are NaN, OR
        # 2. All non-NaN values are just whitespace strings
        def is_blank_row(row):
            # Convert all values to string and strip whitespace
            str_values = [str(v).strip() if pd.notna(v) else None for v in row]
            # Remove None values (which were NaN)
            str_values = [v for v in str_values if v is not None]
            
            # If no non-NaN values, it's blank
            if len(str_values) == 0:
                return True
            
            # If all non-NaN values are empty strings, it's blank
            if all(v == '' for v in str_values):
                return True
            
            return False
        
        # Apply the blank row check
        blank_mask = df.apply(is_blank_row, axis=1)
        df = df[~blank_mask]
        df = df.reset_index(drop=True)  # Reset index after dropping rows
        
        rows_removed = initial_count - len(df)
        return df, rows_removed
    
    @staticmethod
    def read_file(file_content: bytes, filename: str, sheet_name: str = None) -> Tuple[pd.DataFrame, str]:
        """Read Excel or CSV file"""
        try:
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                # When sheet_name=None, pd.read_excel returns dict of all sheets
                # We want to default to first sheet instead
                if sheet_name is None:
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=0, header=0)
                else:
                    df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name, header=0)
                file_type = "Excel"
            elif filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content), header=0)
                file_type = "CSV"
            else:
                raise ValueError("Unsupported file format. Use .xlsx, .xls, or .csv")
            
            # Drop index column if present (Unnamed: 0 is common when Excel has an index)
            if 'Unnamed: 0' in df.columns:
                df = df.drop('Unnamed: 0', axis=1)
            
            # Skip first row if it contains duplicate headers
            if len(df) > 0:
                first_row_values = df.iloc[0].values
                col_names = list(df.columns)
                # Check if all first row values match column names (duplicate header row)
                if len(first_row_values) == len(col_names) and all(
                    str(first_row_values[i]).lower().strip() == str(col_names[i]).lower().strip()
                    for i in range(len(col_names))
                ):
                    df = df.iloc[1:].reset_index(drop=True)
            
            return df, file_type
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    @staticmethod
    def detect_data_type(df: pd.DataFrame) -> str:
        """Detect what type of data is in the file"""
        columns = set(col.lower().strip() for col in df.columns)
        
        # Check for engineers data
        if {'engineer_code', 'engineer_name', 'state'}.issubset(columns):
            return 'engineers'
        
        # Check for offline sites data
        if {'site_id', 'site_name', 'segment'}.issubset(columns):
            return 'offline_sites'
        
        # Check for attendance data
        if {'engineer_code', 'attendance_date', 'status'}.issubset(columns):
            return 'attendance'
        
        # Check for visits data
        if {'engineer_code', 'site_id', 'visit_date'}.issubset(columns):
            return 'visits'
        
        # Check for tickets data
        if {'ticket_id', 'ticket_status'}.issubset(columns):
            return 'tickets'
        
        raise ValueError("Could not determine data type from columns")
    
    @staticmethod
    def process_upload(file_content: bytes, filename: str, sheet_name: str = None) -> Dict:
        """Process complete upload with validation and transformation"""
        result = {
            'status': 'error',
            'filename': filename,
            'data_type': None,
            'rows_uploaded': 0,
            'rows_valid': 0,
            'rows_invalid': 0,
            'errors': [],
            'warnings': [],
            'data': None,
            'summary': {}
        }
        
        try:
            # Read file
            df, file_type = UploadProcessor.read_file(file_content, filename, sheet_name)
            result['file_type'] = file_type
            result['rows_uploaded'] = len(df)
            
            # Remove blank rows (data cleaning)
            df, blank_rows_removed = UploadProcessor.remove_blank_rows(df)
            if blank_rows_removed > 0:
                result['warnings'].append(f"Removed {blank_rows_removed} blank/empty rows from data")
            
            # Detect data type
            data_type = UploadProcessor.detect_data_type(df)
            result['data_type'] = data_type
            
            # Validate columns
            is_valid, col_errors = DataValidator.validate_column_names(
                df, 
                DataValidator.SCHEMA[data_type]
            )
            if not is_valid:
                result['errors'].extend(col_errors)
                return result
            
            # Validate data types
            is_valid, type_errors = DataValidator.validate_data_types(df, data_type)
            if type_errors:
                result['warnings'].extend(type_errors)
            
            # Validate no nulls in critical columns
            critical_columns = DataValidator.SCHEMA[data_type][:3]
            is_valid, null_errors = DataValidator.validate_no_nulls(df, critical_columns)
            if not is_valid:
                result['errors'].extend(null_errors)
                return result
            
            # Transform data
            transformer = DataTransformer()
            if data_type == 'engineers':
                df_transformed = transformer.transform_engineers(df)
            elif data_type == 'offline_sites':
                df_transformed = transformer.transform_offline_sites(df)
            elif data_type == 'attendance':
                df_transformed = transformer.transform_attendance(df)
            elif data_type == 'visits':
                df_transformed = transformer.transform_visits(df)
            elif data_type == 'tickets':
                df_transformed = transformer.transform_tickets(df)
            else:
                raise ValueError(f"Unknown data type: {data_type}")
            
            result['rows_valid'] = len(df_transformed)
            result['rows_invalid'] = result['rows_uploaded'] - result['rows_valid']
            result['data'] = df_transformed.to_dict('records')
            result['status'] = 'success'
            
            # Generate summary
            result['summary'] = {
                'total_records': len(df_transformed),
                'data_type': data_type,
                'file_type': file_type,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            if data_type == 'engineers':
                result['summary']['states'] = df_transformed['state'].nunique()
                result['summary']['active_count'] = len(df_transformed)
            
            if data_type == 'offline_sites':
                result['summary']['critical'] = len(
                    df_transformed[df_transformed['priority'] == 'CRITICAL']
                )
                result['summary']['high'] = len(
                    df_transformed[df_transformed['priority'] == 'HIGH']
                )
            
            return result
            
        except Exception as e:
            result['errors'].append(f"Processing error: {str(e)}")
            return result
