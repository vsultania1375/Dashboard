"""
Mock/Demo API for testing frontend without database
Provides sample responses so UI can be tested
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json
import io
from upload_handler import UploadProcessor

app = FastAPI(title="Service Analysis Dashboard API (Demo Mode)", version="2.0-demo")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

# ─── DEMO/TEST DATA ───────────────────────────────────────

STATES = [
    "All (PAN India)",
    "Karnataka", "Tamil Nadu", "Maharashtra", "Telangana",
    "Rajasthan", "Gujarat", "Punjab", "Haryana", "Delhi",
    "Uttar Pradesh", "Madhya Pradesh", "Odisha", "West Bengal",
    "Andhra Pradesh", "Kerala", "Jharkhand", "Bihar", "Assam",
    "Himachal Pradesh", "Uttarakhand", "Goa", "Tripura", "Manipur",
    "Meghalaya", "Nagaland", "Mizoram", "Sikkim"
]

ENGINEERS = [
    {"id": f"ENG{i:03d}", "name": f"Engineer {i}", "state": STATES[i % 28], "code": f"E{i:04d}", "phone": f"9{i:09d}"[:10]}
    for i in range(1, 128)
]

# ─── HEALTH CHECK ─────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0",
        "mode": "DEMO (No Database)",
        "timestamp": datetime.now().isoformat()
    }

# ─── AUTH ENDPOINTS ───────────────────────────────────────
@app.post("/api/auth/login")
async def login(username: str = Query(...), password: str = Query(...)):
    """Demo login - accepts any credentials for testing"""
    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "access_token": "demo-token-for-testing",
        "token_type": "bearer",
        "role": "admin",
        "state_code": None,
        "force_password_change": False,
        "username": username
    }

# ─── DASHBOARD KPI ENDPOINTS ──────────────────────────────
@app.get("/api/dashboard/kpis")
async def dashboard_kpis():
    """Dashboard key performance indicators"""
    return {
        "total_engineers": 127,
        "total_visits": 18543,
        "avg_repeat_rate": 3.21,
        "offline_sites": 2134,
        "attendance_percent": 87.5,
        "ticket_closure_rate": 82.3,
        "fraud_flags": 12,
        "avg_ticket_age": 5.2
    }

@app.get("/api/dashboard/offline-buckets")
async def offline_distribution():
    """Offline sites distribution by aging bucket"""
    return {
        "distribution": [
            {"bucket": "1-3 Days", "count": 234, "percent": 10.9},
            {"bucket": "4-7 Days", "count": 456, "percent": 21.4},
            {"bucket": "8-15 Days", "count": 523, "percent": 24.5},
            {"bucket": "16-30 Days", "count": 412, "percent": 19.3},
            {"bucket": "31-60 Days", "count": 298, "percent": 14.0},
            {"bucket": "61-90 Days", "count": 156, "percent": 7.3},
            {"bucket": "90+ Days", "count": 55, "percent": 2.6},
        ]
    }

@app.get("/api/dashboard/smart-insights")
async def smart_insights():
    """Smart AI-powered insights"""
    return {
        "insights": [
            {
                "insight_text": "Raj Kumar in Karnataka has zero productivity for 5 days",
                "priority": "CRITICAL",
                "state": "Karnataka"
            },
            {
                "insight_text": "Repeat rate in Tamil Nadu dropped 30% from last week",
                "priority": "WARNING",
                "state": "Tamil Nadu"
            },
            {
                "insight_text": "5 offline sites approaching 90+ days threshold",
                "priority": "WARNING",
                "state": None
            },
            {
                "insight_text": "Attendance improved 5% across all engineers",
                "priority": "INFO",
                "state": None
            }
        ]
    }

# ─── ENGINEER PERFORMANCE ────────────────────────────────
@app.get("/api/engineers/performance/table")
async def engineer_performance(
    from_date: str = Query("2026-05-06"),
    to_date: str = Query("2026-05-13"),
    state: str = Query("All (PAN India)"),
    page: int = Query(1),
    per_page: int = Query(25)
):
    """Engineer performance table with all 18 columns"""
    
    # Filter engineers by state
    filtered = ENGINEERS if state == "All (PAN India)" else [e for e in ENGINEERS if e["state"] == state]
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    engineers_data = []
    for eng in paginated:
        engineers_data.append({
            "service_area": f"SA_{eng['state'][:3]}_{eng['id'][-3:]}",
            "engineer_name": eng["name"],
            "code": eng["code"],
            "phone": eng["phone"],
            "state": eng["state"],
            "att_days": 18,
            "working_days": 20,
            "att_percent": 90.0,
            "prod_days": 16,
            "zero_prod_days": 2,
            "total_visits": 45 + (hash(eng["id"]) % 50),
            "distinct_sites": 12 + (hash(eng["id"]) % 15),
            "repeat_rate": 3.5 + (hash(eng["id"]) % 10) / 10,
            "closed": 8,
            "open": 3,
            "pending": 2,
            "completed": 5,
            "offline_sites": 15
        })
    
    return {
        "engineers": engineers_data,
        "total": len(filtered),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(filtered) + per_page - 1) // per_page,
        "footer": {
            "att_days_avg": 18,
            "working_days_avg": 20,
            "att_percent_avg": 90.0,
            "prod_days_avg": 16,
            "zero_prod_days_avg": 2,
            "total_visits_sum": 5700,
            "distinct_sites_avg": 13.5,
            "repeat_rate_avg": 3.2
        }
    }

@app.get("/api/engineers/leaderboard")
async def engineer_leaderboard():
    """Top performing engineers"""
    return {
        "leaderboard": [
            {"rank": 1, "name": "Priya Singh", "state": "Tamil Nadu", "visits": 152, "repeat_rate": 4.1},
            {"rank": 2, "name": "Raj Kumar", "state": "Karnataka", "visits": 148, "repeat_rate": 4.0},
            {"rank": 3, "name": "Amit Patel", "state": "Maharashtra", "visits": 141, "repeat_rate": 3.9},
        ]
    }

# ─── OFFLINE DISTRIBUTION ─────────────────────────────────
@app.get("/api/dashboard/distribution")
async def offline_distribution_detail(
    state: str = Query("All (PAN India)"),
    from_date: str = Query("2026-05-06"),
    to_date: str = Query("2026-05-13")
):
    """Detailed offline distribution data"""
    return {
        "state": state,
        "period": {"from": from_date, "to": to_date},
        "distribution": [
            {"bucket": "1-3 Days", "count": 234},
            {"bucket": "4-7 Days", "count": 456},
            {"bucket": "8-15 Days", "count": 523},
            {"bucket": "16-30 Days", "count": 412},
            {"bucket": "31-60 Days", "count": 298},
            {"bucket": "61-90 Days", "count": 156},
            {"bucket": "90+ Days", "count": 55},
        ]
    }

# ─── MASTERS ──────────────────────────────────────────────
@app.get("/api/masters/service-areas")
async def service_areas():
    """List of all states"""
    return {"states": STATES}

# ─── FRAUD FLAGS ──────────────────────────────────────────
@app.get("/api/fraud/flags")
async def fraud_flags():
    """Suspected fraud flags"""
    return {
        "flags": [
            {
                "flag_id": "F001",
                "engineer_name": "Raj Kumar",
                "flag_type": "Zero Productivity",
                "description": "No visits for 5 consecutive days",
                "severity": "CRITICAL",
                "state": "Karnataka"
            },
            {
                "flag_id": "F002",
                "engineer_name": "Priya Singh",
                "flag_type": "Location Anomaly",
                "description": "Visited 3 sites in different cities same hour",
                "severity": "HIGH",
                "state": "Tamil Nadu"
            },
            {
                "flag_id": "F003",
                "engineer_name": "Amit Patel",
                "flag_type": "Repeat Site",
                "description": "Visited same site 4 times in one day",
                "severity": "MEDIUM",
                "state": "Maharashtra"
            }
        ]
    }

# ─── STATE COMPARISON ─────────────────────────────────────
@app.get("/api/states/comparison")
async def states_comparison():
    """State-wise performance comparison"""
    return {
        "states": [
            {
                "state": "Karnataka",
                "engineers": 15,
                "avg_att_percent": 88.5,
                "avg_repeat_rate": 3.2,
                "offline_sites": 234,
                "ticket_closure_rate": 84.5
            },
            {
                "state": "Tamil Nadu",
                "engineers": 12,
                "avg_att_percent": 91.2,
                "avg_repeat_rate": 3.5,
                "offline_sites": 156,
                "ticket_closure_rate": 87.3
            },
            {
                "state": "Maharashtra",
                "engineers": 18,
                "avg_att_percent": 86.4,
                "avg_repeat_rate": 3.0,
                "offline_sites": 289,
                "ticket_closure_rate": 81.2
            }
        ]
    }

# ─── VISITS ANALYSIS ──────────────────────────────────────
@app.get("/api/visits/analysis")
async def visits_analysis():
    """Visit activity analysis"""
    return {
        "total_visits": 18543,
        "avg_visits_per_engineer": 146,
        "peak_hours": ["09:00-10:00", "14:00-15:00"],
        "top_engineers": [
            {"name": "Priya Singh", "visits": 152},
            {"name": "Raj Kumar", "visits": 148},
            {"name": "Amit Patel", "visits": 141}
        ]
    }

@app.get("/api/visits/browse")
async def visits_browse():
    """Browse individual visits"""
    return {
        "visits": [
            {
                "visit_id": "V001",
                "engineer": "Raj Kumar",
                "ticket_id": "TIC001",
                "site": "SBI ATM Branch 1",
                "visit_date": "2026-05-13",
                "visit_time": "09:30",
                "duration_hours": 1.5
            },
            {
                "visit_id": "V002",
                "engineer": "Priya Singh",
                "ticket_id": "TIC002",
                "site": "SBI ATM Branch 2",
                "visit_date": "2026-05-13",
                "visit_time": "10:45",
                "duration_hours": 2.0
            }
        ]
    }

# ─── TICKETS ANALYSIS ────────────────────────────────────
@app.get("/api/tickets/analysis")
async def tickets_analysis():
    """Ticket analysis"""
    return {
        "total_tickets": 1234,
        "open": 123,
        "pending": 89,
        "closed": 987,
        "avg_aging_days": 5.2,
        "closure_rate_percent": 82.3
    }

@app.get("/api/tickets/chronic-pending")
async def chronic_pending():
    """Chronic pending tickets"""
    return {
        "chronic_tickets": [
            {
                "ticket_id": "TIC001",
                "site": "SBI ATM Branch 1",
                "status": "PENDING",
                "aging_days": 45,
                "assigned_to": "Raj Kumar",
                "state": "Karnataka"
            },
            {
                "ticket_id": "TIC002",
                "site": "SBI ATM Branch 2",
                "status": "PENDING",
                "aging_days": 38,
                "assigned_to": "Priya Singh",
                "state": "Tamil Nadu"
            }
        ]
    }

# ─── OPERATORS ────────────────────────────────────────────
@app.get("/api/ops/sites-visited-datewise")
async def sites_visited_datewise():
    """Sites visited by date"""
    return {
        "data": [
            {"date": "2026-05-07", "sites": 234},
            {"date": "2026-05-08", "sites": 245},
            {"date": "2026-05-09", "sites": 267},
            {"date": "2026-05-10", "sites": 256},
            {"date": "2026-05-11", "sites": 278},
            {"date": "2026-05-12", "sites": 289},
            {"date": "2026-05-13", "sites": 245}
        ]
    }

@app.get("/api/ops/engineers-used-app-datewise")
async def engineers_active_datewise():
    """Engineers using app by date"""
    return {
        "data": [
            {"date": "2026-05-07", "engineers": 89},
            {"date": "2026-05-08", "engineers": 92},
            {"date": "2026-05-09", "engineers": 95},
            {"date": "2026-05-10", "engineers": 91},
            {"date": "2026-05-11", "engineers": 96},
            {"date": "2026-05-12", "engineers": 97},
            {"date": "2026-05-13", "engineers": 93}
        ]
    }

# ─── UPLOAD ENDPOINTS ─────────────────────────────────────
upload_history = {}

@app.post("/api/upload/validate")
async def validate_upload(file: UploadFile = File(...)):
    """Validate uploaded file without loading to database"""
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

@app.post("/api/upload/preview")
async def preview_upload(file: UploadFile = File(...), rows: int = 10):
    """Preview uploaded file data"""
    try:
        import pandas as pd
        content = await file.read()
        
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

@app.post("/api/upload/confirm")
async def confirm_upload(upload_id: str, background_tasks: BackgroundTasks):
    """Confirm and load validated data"""
    try:
        if upload_id not in upload_history:
            raise HTTPException(status_code=404, detail=f"Upload ID not found: {upload_id}")
        
        upload_result = upload_history[upload_id]
        
        if upload_result['status'] != 'success':
            raise HTTPException(status_code=400, detail="Upload validation failed.")
        
        if len(upload_result['errors']) > 0:
            raise HTTPException(status_code=400, detail="Upload has errors.")
        
        return {
            "upload_id": upload_id,
            "status": "loading",
            "message": f"Starting to load {len(upload_result['data'])} records",
            "data_type": upload_result['data_type'],
            "rows_to_load": len(upload_result['data'])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Confirmation failed: {str(e)}")

@app.get("/api/upload/status/{upload_id}")
async def upload_status(upload_id: str):
    """Get status of upload"""
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

@app.get("/api/upload/history")
async def upload_history_list(limit: int = 20):
    """Get recent upload history"""
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

@app.post("/api/upload/template/{data_type}")
async def download_template(data_type: str):
    """Get template for data type"""
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
        raise HTTPException(status_code=404, detail=f"Template not found: {data_type}")
    
    return templates[data_type]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
