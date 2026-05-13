"""
Mock/Demo API for testing frontend without database
Provides sample responses so UI can be tested
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
