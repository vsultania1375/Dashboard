"""
FastAPI routes for data upload functionality
Handles file uploads, validation, and database ingestion
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Dict, List
import io
from datetime import datetime

from upload_handler import UploadProcessor

# Initialize router
router = APIRouter(prefix="/api/upload", tags=["upload"])

# Store upload history and results
upload_history = {}

@router.post("/validate")
async def validate_upload(file: UploadFile = File(...)) -> Dict:
    """
    Validate uploaded file without loading to database
    Returns validation report
    """
    try:
        # Read file
        content = await file.read()
        
        # Process upload with validation
        result = UploadProcessor.process_upload(content, file.filename)
        
        # Store upload result
        upload_id = datetime.utcnow().isoformat()
        upload_history[upload_id] = result
        
        return {
            "upload_id": upload_id,
            "status": result['status'],
            "filename": result['filename'],
            "data_type": result.get('data_type'),
            "rows_uploaded": result['rows_uploaded'],
            "rows_valid": result['rows_valid'],
            "rows_invalid": result['rows_invalid'],
            "errors": result['errors'],
            "warnings": result['warnings'],
            "summary": result['summary'],
            "can_proceed": result['status'] == 'success' and len(result['errors']) == 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload validation failed: {str(e)}")


@router.post("/preview")
async def preview_upload(file: UploadFile = File(...), rows: int = 10) -> Dict:
    """
    Preview uploaded file data without validation/processing
    Returns first N rows
    """
    try:
        import pandas as pd
        
        content = await file.read()
        
        # Read file
        if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise ValueError("Unsupported file format")
        
        return {
            "filename": file.filename,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "preview_data": df.head(rows).to_dict('records'),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview failed: {str(e)}")


@router.post("/confirm")
async def confirm_upload(upload_id: str, background_tasks: BackgroundTasks) -> Dict:
    """
    Confirm and load validated data into database
    Returns confirmation and loading status
    """
    try:
        if upload_id not in upload_history:
            raise HTTPException(status_code=404, detail=f"Upload ID not found: {upload_id}")
        
        upload_result = upload_history[upload_id]
        
        if upload_result['status'] != 'success':
            raise HTTPException(status_code=400, detail="Upload validation failed. Cannot confirm.")
        
        if len(upload_result['errors']) > 0:
            raise HTTPException(status_code=400, detail="Upload has errors. Cannot confirm.")
        
        # In background, would load to database
        # For now, just mark as confirmed
        background_tasks.add_task(
            load_data_to_database,
            upload_id=upload_id,
            data_type=upload_result['data_type'],
            data=upload_result['data']
        )
        
        return {
            "upload_id": upload_id,
            "status": "loading",
            "message": f"Starting to load {len(upload_result['data'])} records to database",
            "data_type": upload_result['data_type'],
            "rows_to_load": len(upload_result['data'])
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload confirmation failed: {str(e)}")


@router.get("/status/{upload_id}")
async def upload_status(upload_id: str) -> Dict:
    """
    Get status of a previous upload
    """
    if upload_id not in upload_history:
        raise HTTPException(status_code=404, detail=f"Upload ID not found: {upload_id}")
    
    result = upload_history[upload_id]
    
    return {
        "upload_id": upload_id,
        "status": result['status'],
        "filename": result['filename'],
        "data_type": result.get('data_type'),
        "rows_uploaded": result['rows_uploaded'],
        "rows_valid": result['rows_valid'],
        "rows_invalid": result['rows_invalid'],
        "errors": result['errors'],
        "summary": result['summary']
    }


@router.get("/history")
async def upload_history_list(limit: int = 20) -> Dict:
    """
    Get recent upload history
    """
    recent = sorted(upload_history.items(), key=lambda x: x[0], reverse=True)[:limit]
    
    return {
        "total_uploads": len(upload_history),
        "recent_uploads": [
            {
                "upload_id": uid,
                "filename": result['filename'],
                "data_type": result.get('data_type'),
                "status": result['status'],
                "rows": result['rows_valid'],
                "errors": len(result['errors'])
            }
            for uid, result in recent
        ]
    }


@router.get("/template/{data_type}")
async def download_template(data_type: str) -> Dict:
    """
    Get template for a data type (shows expected columns and format)
    """
    templates = {
        "engineers": {
            "columns": [
                "engineer_code",      # 3-digit code (e.g., "001")
                "engineer_name",      # Full name
                "state",              # Indian state
                "designation",        # Job title (must be "Engineer")
                "active_status",      # YES or NO
                "phone",              # Phone number
                "email",              # Email address
                "service_area_code"   # Service area code
            ],
            "sample_row": {
                "engineer_code": "001",
                "engineer_name": "Raj Kumar",
                "state": "Karnataka",
                "designation": "Engineer",
                "active_status": "YES",
                "phone": "9876543210",
                "email": "raj.kumar@vprotect.com",
                "service_area_code": "KA-001"
            },
            "notes": [
                "engineer_code must be exactly 3 digits",
                "active_status must be YES or NO",
                "designation must be Engineer",
                "state must be a valid Indian state"
            ]
        },
        "offline_sites": {
            "columns": [
                "site_id",                 # Unique site identifier
                "site_name",               # Site name/location
                "state",                   # Indian state
                "segment",                 # Must be PSU (PSU banks only)
                "last_online_date",        # Last date site was online (YYYY-MM-DD)
                "offline_duration_days",   # Days offline (optional, calculated if missing)
                "priority"                 # CRITICAL/HIGH/MEDIUM/LOW (optional)
            ],
            "sample_row": {
                "site_id": "SITE001",
                "site_name": "Bank Branch Mumbai",
                "state": "Maharashtra",
                "segment": "PSU",
                "last_online_date": "2026-04-01",
                "offline_duration_days": 42,
                "priority": "HIGH"
            },
            "notes": [
                "segment must be PSU (non-PSU records will be filtered out)",
                "only PSU bank sites will be loaded",
                "priority auto-calculated based on offline duration if not provided"
            ]
        },
        "attendance": {
            "columns": [
                "engineer_code",      # 3-digit code
                "attendance_date",    # Date (YYYY-MM-DD)
                "check_in_time",      # Time (HH:MM:SS)
                "check_out_time",     # Time (HH:MM:SS, optional)
                "status"              # OnTime/Late/Absent (auto-calculated if not provided)
            ],
            "sample_row": {
                "engineer_code": "001",
                "attendance_date": "2026-05-13",
                "check_in_time": "09:30:00",
                "check_out_time": "17:30:00",
                "status": "OnTime"
            },
            "notes": [
                "check-in before 10 AM = OnTime",
                "check-in after 10 AM = Late",
                "NULL check_in_time = Absent",
                "status auto-calculated if not provided"
            ]
        },
        "visits": {
            "columns": [
                "engineer_code",         # 3-digit code
                "site_id",               # Site identifier
                "visit_date",            # Date (YYYY-MM-DD)
                "visit_type",            # Site Survey/Maintenance/Repair/Installation/Inspection
                "problem_solved",        # YES/NO
                "problem_description",   # Problem text
                "time_taken_minutes"     # Duration in minutes
            ],
            "sample_row": {
                "engineer_code": "001",
                "site_id": "SITE001",
                "visit_date": "2026-05-13",
                "visit_type": "Maintenance",
                "problem_solved": "YES",
                "problem_description": "Fixed network issue",
                "time_taken_minutes": 45
            },
            "notes": [
                "visit_type must be one of: Site Survey, Maintenance, Repair, Installation, Inspection"
            ]
        },
        "tickets": {
            "columns": [
                "ticket_id",        # Unique ticket identifier
                "site_id",          # Site identifier
                "engineer_code",    # 3-digit code
                "ticket_status",    # OPEN/PENDING/SENTBACK/COMPLETED/CLOSED/CANCELLED/REJECTED
                "created_date",     # Date (YYYY-MM-DD)
                "closed_date",      # Date (YYYY-MM-DD, optional)
                "priority",         # P1/P2/P3/P4
                "category"          # Issue category
            ],
            "sample_row": {
                "ticket_id": "TKT001",
                "site_id": "SITE001",
                "engineer_code": "001",
                "ticket_status": "OPEN",
                "created_date": "2026-05-13",
                "closed_date": None,
                "priority": "P1",
                "category": "Network"
            },
            "notes": [
                "ticket_status must be one of: OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED",
                "closed_date is optional and only for closed tickets"
            ]
        }
    }
    
    if data_type not in templates:
        raise HTTPException(status_code=404, detail=f"Template not found for: {data_type}")
    
    return templates[data_type]


# Background task to load data
async def load_data_to_database(upload_id: str, data_type: str, data: List[Dict]):
    """
    Background task to load data into database
    TODO: Implement actual database loading
    """
    print(f"Starting to load {len(data)} records of type {data_type}...")
    
    # This is where you would:
    # 1. Connect to PostgreSQL
    # 2. Insert/update records in appropriate table
    # 3. Update upload_history with final status
    # 4. Log any issues
    
    upload_history[upload_id]['status'] = 'completed'
    print(f"Completed loading {len(data)} records")
