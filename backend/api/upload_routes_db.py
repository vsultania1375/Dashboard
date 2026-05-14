"""
Enhanced upload routes with database integration
Handles file uploads, validation, transformation, and database loading
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, List
from datetime import datetime
import io
import json

from upload_handler import UploadProcessor
from database import SessionLocal, DatabaseOps, get_db

# Initialize router
router = APIRouter(prefix="/api/upload", tags=["upload"])

# Store upload history and results
upload_history = {}

@router.post("/validate")
async def validate_upload(file: UploadFile = File(...)):
    """
    Validate uploaded file without loading to database
    Returns validation report
    """
    try:
        content = await file.read()
        result = UploadProcessor.process_upload(content, file.filename)
        
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
async def preview_upload(file: UploadFile = File(...), rows: int = 10):
    """
    Preview uploaded file data without validation/processing
    Returns first N rows
    """
    try:
        import pandas as pd
        
        content = await file.read()
        
        if not content:
            raise ValueError("File is empty")
        
        # Read file based on extension
        try:
            if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                df = pd.read_excel(io.BytesIO(content))
            elif file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                raise ValueError(f"Unsupported file format: {file.filename}. Supported formats: .xlsx, .xls, .csv")
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")
        
        return {
            "filename": file.filename,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "preview_data": df.head(rows).to_dict('records'),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/confirm")
async def confirm_upload(upload_id: str, background_tasks: BackgroundTasks):
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
        
        # Start background task to load data
        background_tasks.add_task(
            load_data_to_database,
            upload_id=upload_id,
            data_type=upload_result['data_type'],
            data=upload_result['data'],
            filename=upload_result['filename'],
            rows_uploaded=upload_result['rows_uploaded'],
            rows_valid=upload_result['rows_valid'],
            rows_invalid=upload_result['rows_invalid'],
            errors=upload_result['errors'],
            warnings=upload_result['warnings']
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
async def upload_status(upload_id: str):
    """
    Get status of a previous upload
    """
    if upload_id not in upload_history:
        raise HTTPException(status_code=404, detail=f"Upload ID not found: {upload_id}")
    
    result = upload_history[upload_id]
    
    return {
        "upload_id": upload_id,
        "status": result.get('status', 'unknown'),
        "filename": result['filename'],
        "data_type": result.get('data_type'),
        "rows_uploaded": result['rows_uploaded'],
        "rows_valid": result['rows_valid'],
        "rows_invalid": result['rows_invalid'],
        "errors": result['errors'],
        "summary": result.get('summary', {})
    }


@router.get("/history")
async def upload_history_list(limit: int = 20):
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
                "status": result.get('status', 'unknown'),
                "rows": result['rows_valid'],
                "errors": len(result['errors'])
            }
            for uid, result in recent
        ]
    }


@router.post("/template/{data_type}")
async def download_template(data_type: str):
    """
    Get template for a data type (shows expected columns and format)
    """
    templates = {
        "engineers": {
            "columns": ["engineer_code", "engineer_name", "state", "designation", "active_status", "phone", "email", "service_area_code"],
            "sample_row": {"engineer_code": "001", "engineer_name": "Raj Kumar", "state": "Karnataka", "designation": "Engineer", "active_status": "YES", "phone": "9876543210", "email": "raj.kumar@vprotect.com", "service_area_code": "KA-001"},
            "notes": ["engineer_code must be 3 digits", "active_status must be YES or NO", "only active Engineers will be loaded"]
        },
        "offline_sites": {
            "columns": ["site_id", "site_name", "state", "segment", "last_online_date", "offline_duration_days", "priority"],
            "sample_row": {"site_id": "SITE001", "site_name": "Bank Branch", "state": "Maharashtra", "segment": "PSU", "last_online_date": "2026-04-01", "offline_duration_days": 42, "priority": "HIGH"},
            "notes": ["segment must be PSU", "only PSU sites will be loaded", "priority auto-calculated if not provided"]
        },
        "attendance": {
            "columns": ["engineer_code", "attendance_date", "check_in_time", "check_out_time", "status"],
            "sample_row": {"engineer_code": "001", "attendance_date": "2026-05-13", "check_in_time": "09:30:00", "check_out_time": "17:30:00", "status": "OnTime"},
            "notes": ["before 10 AM = OnTime", "after 10 AM = Late", "status auto-calculated if not provided"]
        },
        "visits": {
            "columns": ["engineer_code", "site_id", "visit_date", "visit_type", "problem_solved", "problem_description", "time_taken_minutes"],
            "sample_row": {"engineer_code": "001", "site_id": "SITE001", "visit_date": "2026-05-13", "visit_type": "Maintenance", "problem_solved": "YES", "problem_description": "Fixed issue", "time_taken_minutes": 45},
            "notes": ["valid types: Site Survey, Maintenance, Repair, Installation, Inspection"]
        },
        "tickets": {
            "columns": ["ticket_id", "site_id", "engineer_code", "ticket_status", "created_date", "closed_date", "priority", "category"],
            "sample_row": {"ticket_id": "TKT001", "site_id": "SITE001", "engineer_code": "001", "ticket_status": "OPEN", "created_date": "2026-05-13", "closed_date": None, "priority": "P1", "category": "Network"},
            "notes": ["valid statuses: OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED"]
        }
    }
    
    if data_type not in templates:
        raise HTTPException(status_code=404, detail=f"Template not found for: {data_type}")
    
    return templates[data_type]


# ─── BACKGROUND TASK ──────────────────────────────────
async def load_data_to_database(
    upload_id: str,
    data_type: str,
    data: List[Dict],
    filename: str,
    rows_uploaded: int,
    rows_valid: int,
    rows_invalid: int,
    errors: List[str],
    warnings: List[str]
):
    """
    Background task to load data into database
    Runs asynchronously after upload confirmation
    """
    db = SessionLocal()
    
    try:
        print(f"\n📥 Starting to load {len(data)} {data_type} records...")
        
        # Convert data to database models (convert dates/times to proper format)
        db_records = []
        for record in data:
            # Convert string dates to datetime objects
            if 'attendance_date' in record and isinstance(record['attendance_date'], str):
                from datetime import datetime as dt
                record['attendance_date'] = dt.fromisoformat(record['attendance_date'].split('T')[0])
            
            if 'visit_date' in record and isinstance(record['visit_date'], str):
                from datetime import datetime as dt
                record['visit_date'] = dt.fromisoformat(record['visit_date'].split('T')[0])
            
            if 'last_online_date' in record and isinstance(record['last_online_date'], str):
                from datetime import datetime as dt
                record['last_online_date'] = dt.fromisoformat(record['last_online_date'].split('T')[0])
            
            if 'created_date' in record and isinstance(record['created_date'], str):
                from datetime import datetime as dt
                record['created_date'] = dt.fromisoformat(record['created_date'].split('T')[0])
            
            if 'closed_date' in record and isinstance(record['closed_date'], str):
                from datetime import datetime as dt
                record['closed_date'] = dt.fromisoformat(record['closed_date'].split('T')[0])
            
            db_records.append(record)
        
        # Load data based on type
        if data_type == 'engineers':
            inserted, _ = DatabaseOps.insert_engineers(db, db_records)
            status = "completed"
            message = f"✅ Loaded {inserted} engineers to database"
        
        elif data_type == 'offline_sites':
            inserted, _ = DatabaseOps.insert_offline_sites(db, db_records)
            status = "completed"
            message = f"✅ Loaded {inserted} offline sites to database"
        
        elif data_type == 'attendance':
            inserted, _ = DatabaseOps.insert_attendance(db, db_records)
            status = "completed"
            message = f"✅ Loaded {inserted} attendance records to database"
        
        elif data_type == 'visits':
            inserted, _ = DatabaseOps.insert_visits(db, db_records)
            status = "completed"
            message = f"✅ Loaded {inserted} visits to database"
        
        elif data_type == 'tickets':
            inserted, _ = DatabaseOps.insert_tickets(db, db_records)
            status = "completed"
            message = f"✅ Loaded {inserted} tickets to database"
        
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Update upload history with success
        if upload_id in upload_history:
            upload_history[upload_id]['status'] = status
            upload_history[upload_id]['message'] = message
            upload_history[upload_id]['loaded_at'] = datetime.utcnow().isoformat()
        
        print(message)
        
    except Exception as e:
        status = "error"
        message = f"❌ Error loading data: {str(e)}"
        print(message)
        
        if upload_id in upload_history:
            upload_history[upload_id]['status'] = status
            upload_history[upload_id]['error'] = str(e)
        
        # Rollback on error
        db.rollback()
    
    finally:
        db.close()
