# Service Analysis Dashboard — Full Project Context for Cursor AI

## What Are We Building?

A full-stack web dashboard for a PAN India alarm system maintenance company.

- **25,000 B2B sites** (banks/ATMs) across India
- **250 field engineers** across 28+ states, 4 zones
- Engineers use a mobile app called **Service Connect** for attendance and ticket management
- Current problem: management spends 1hr/day on Excel, data is 2 days old, no fraud detection

The dashboard gives real-time visibility into:
- Which sites are offline and for how long
- Engineer performance scores (0-100)
- Fraud detection (fake visits, one-visit days, chronic pending tickets)
- State-by-state health comparison

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 15 (Docker) |
| Backend | Python FastAPI |
| ETL Pipeline | Python + Pandas + SQLAlchemy |
| Frontend | React + Tailwind CSS (Vite) |
| Auth | JWT (bcrypt passwords) |
| Deployment | Docker Compose (3 containers) |

---

## Project Folder Structure

```
dashboard/
├── backend/
│   ├── api/
│   │   └── main.py          ← FastAPI — all API endpoints
│   ├── etl/
│   │   └── pipeline.py      ← ETL pipeline — data loading, fraud detection, KPI computation
│   ├── models/
│   │   └── schema.sql       ← PostgreSQL schema — all tables
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx          ← Complete React app — all 7 pages in one file
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── Dockerfile
│   └── nginx.conf
├── data/
│   └── uploads/             ← Uploaded Excel files stored here
├── docker-compose.yml
├── START.bat                ← Windows start script
└── start.sh                 ← Mac/Linux start script
```

---

## 5 Data Sources (Excel Files)

All data comes from Excel files uploaded daily via the dashboard UI.

| File | Upload Type | Key Column | Description |
|---|---|---|---|
| B2B Offline Data | Daily full replace | cs_no | All currently offline sites with bucket/days |
| View Ticket Dump | Daily full replace + snapshot | Ticket ID + CS ID | All tickets (4 month rolling) |
| Attendance Report | **APPEND ONLY** — never replace | Employee Code + Date | Engineer punch-in/out with GPS |
| Engineer Master | Periodic full replace | Employee Code | Engineer details + area mapping |
| Customer Site Master | Periodic full replace | cs_id | All 25,000 site details |

**Universal join key:** CS ID (appears as cs_no, cs_id, CS ID across datasets)

---

## How Attendance Works (Critical Business Logic)

- Engineer selects ANY open ticket as location for **punch-in** (records GPS only, does NOT log a visit)
- Engineer **cannot punch out** unless he visited at least one ticket that day
- Must be at physical location of his LAST VISITED ticket to punch out
- **Fraud implication:** Minimum fraud = punch in near home, do ONE visit (to unlock punch-out), go home. Attendance shows Present 8-9hrs. Ticket data shows 1 visit.

---

## Database Tables

### Raw Data Tables
- `customer_site_master` — all 25,000 sites
- `engineer_master` — all 250 engineers
- `b2b_offline` — today's offline sites (full replace daily)
- `view_ticket` — all tickets (full replace daily + snapshot stored)
- `attendance` — attendance records (append only, never replace)
- `ticket_snapshot` — daily snapshot of ticket states for fraud detection (90 day retention)

### Pre-Aggregated Facts Tables (computed by ETL after each upload)
- `fact_engineer_daily` — per engineer per day: visits, closures, fraud signals
- `fact_engineer_monthly` — per engineer per month: composite score (0-100), all KPIs
- `fact_state_daily` — per state per day: offline %, bucket breakdown
- `fact_state_monthly` — per state per month: state score, penalties/bonuses

### Intelligence Tables
- `fraud_flag` — all detected fraud patterns with severity, evidence, review status
- `smart_insight` — auto-generated daily alerts (CRITICAL/WARNING/INFO)
- `upload_log` — audit trail of all file uploads
- `app_user` — user accounts with roles
- `app_settings` — configurable settings

---

## Engineer Composite Score (0-100)

| Component | Weight | Formula |
|---|---|---|
| Ticket Closure Rate | 25 pts | Closed ÷ Total × 25 |
| Service Area Coverage | 20 pts | Unique sites visited ÷ PoP sites × 20 |
| Avg Resolution Time | 20 pts | max(0, 20 - avg_days × 2.5) |
| Area Offline % + Trend | 15 pts | 10 pts offline % + 5 pts if improving |
| Repeat Visit Rate (inverted) | 10 pts | max(0, 10 - repeat_rate × 0.33) |
| Attendance & Punctuality | 7 pts | attend_rate × 0.05 + (1-late_rate) × 0.02 |
| Fraud Flags (inverted) | 3 pts | 3 - (HIGH_flags × 1), floor 0 |

**Score bands:** 90-100 Exceptional · 75-89 Good · 60-74 Average · 45-59 Below Average · <45 Poor

Engineers with 3+ Critical/High fraud flags → **forced RED** (score capped at 35)

---

## 7 Fraud Detection Patterns

| ID | Name | Detection Logic |
|---|---|---|
| P1 | One-Visit Work Day | Present + visits=1 + area backlog ≥3 open aging tickets |
| P2 | Same-Day Open+Close | Ticket created and closed same day, site was offline 2+ days before |
| P3 | Chronic PENDING | PENDING reason unchanged for 15+ days (requires daily snapshot comparison) |
| P7 | No-Ticket Offline | Site offline 4+ days with no active ticket raised |
| FV-01 | Zero Duration Visit | Visit lasted < 10 minutes |
| FV-03 | Instant Lifecycle | Ticket created and closed in < 1 hour |
| FV-04 | Missing Visit Timestamp | Ticket CLOSED but no Last Visit In timestamp |
| FV-06 | Closed on Absent Day | Ticket closed on a date engineer has no attendance record |

---

## API Endpoints (main.py)

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/auth/login | Login, returns JWT token |
| POST | /api/auth/change-password | Change password |
| POST | /api/upload/{file_type} | Upload Excel file (admin only) |
| GET | /api/upload/history | Upload audit log |
| GET | /api/dashboard/kpis | Main KPI cards |
| GET | /api/dashboard/smart-insights | Auto-generated alerts |
| GET | /api/dashboard/state-health | All states offline/ticket status |
| GET | /api/dashboard/today-digest | Today's problem alerts |
| GET | /api/dashboard/offline-buckets | Offline sites by duration bucket |
| GET | /api/engineers/leaderboard | Engineer scores list (paginated) |
| GET | /api/engineers/{code}/profile | Full engineer profile |
| GET | /api/tickets/analysis | Ticket status/aging/breach analysis |
| GET | /api/tickets/chronic-pending | Chronic PENDING tickets |
| GET | /api/fraud/flags | All fraud flags (filterable) |
| POST | /api/fraud/flags/{id}/review | Mark flag as Valid or Confirmed Fake |
| GET | /api/states/comparison | PAN India state comparison |
| GET | /api/users | List users (admin) |
| POST | /api/users | Create user (admin) |
| GET | /api/settings | App settings |

---

## User Roles

| Role | Access |
|---|---|
| admin | Everything + uploads + user management |
| ops_manager | Full PAN India view + fraud flag review |
| state_manager | Own state only (server-enforced via JWT state_code) |

---

## Frontend Pages (App.jsx)

All in one file `frontend/src/App.jsx`:

1. **LoginPage** — JWT login
2. **DashboardPage** — KPI cards, smart insights, state health bar chart, offline buckets, today's digest
3. **EngineersPage** — Leaderboard table + click-to-open engineer profile modal (score breakdown, attendance calendar, fraud flags)
4. **TicketsPage** — 6 tabs: status distribution, aging bands, breach list, SENTBACK analysis, no-ticket sites, chronic pending
5. **StatesPage** — PAN India state comparison table (ops manager only)
6. **FraudPage** — All fraud flags with filter by pattern/severity + review workflow
7. **UploadPage** — File upload UI + upload history table
8. **UsersPage** — Create and list users (admin only)

---

## Docker Setup

Three containers:
- `sad_db` — PostgreSQL 15 (port 5432)
- `sad_backend` — FastAPI on port 8000
- `sad_frontend` — React built with Vite, served by Nginx on port 80

**Database credentials:**
- Host: db (inside Docker network) / localhost (from outside)
- DB: service_dashboard
- User: dashboard
- Password: dashboard123

**Default admin login:**
- Username: admin
- Password: Admin@1234 (after password reset — see below)

---

## Current Status — What's Working

✅ Docker Compose running (all 3 containers healthy)
✅ Login working (after manual password reset)
✅ B2B Offline upload — working (1,302 rows loaded, ETL complete)
✅ View Ticket upload — working (10,811 rows loaded, ETL complete)
✅ Fraud detection running after upload (892 flags detected)
✅ Dashboard KPI cards loading
✅ Smart insights generating
✅ Engineer leaderboard loading
✅ Fraud flags page loading

---

## Current Problem — Where We Are Stuck

**Attendance file upload returns 0 rows loaded.**

### File Details
- Filename: `AttendanceReport (22).xlsx`
- Rows: 157
- Actual columns in file:
```
['Employee Name', 'Employee Code', 'Service State', 'Attendance Date',
 'Attendance Status', 'Attendance Month', 'In Date Time', 'Out Date Time',
 'Outstation', 'Is Regularized', 'Working Hours', 'Start Latitude',
 'Start Longitude', 'End Latitude', 'End Longitude', 'First Visit CS ID',
 'First Visit Ticket ID', 'Last Visit CS ID', 'Last Visit Ticket ID']
```

### Sample Data
```
Employee Name: "Afjal (HBSVP00737)"
Employee Code: "HBSVP00737"
Attendance Date: "19-Mar-2026"
Attendance Status: "Half Day"
Start Latitude: 28.698626
End Latitude: NaN  ← problem! pandas NaN not handled
```

### Root Cause Identified
The `load_attendance()` function in `pipeline.py` is silently failing on rows where `End Latitude` or `End Longitude` is `NaN` (pandas float NaN). PostgreSQL rejects NaN values for DECIMAL columns. The `try/except` block catches the error silently and logs a warning, so 0 rows get inserted.

When we test the insert manually with `None` instead of `NaN` it works perfectly.

### Fix Required in `pipeline.py`

In the `load_attendance()` function, replace the coordinate fields with NaN-safe versions:

```python
# WRONG — current code:
'start_lat': row.get('Start Latitude', row.get('Start Lat')) or None,
'start_long': row.get('Start Longitude', row.get('Start Long')) or None,
'end_lat': row.get('End Latitude', row.get('End Lat')) or None,
'end_long': row.get('End Longitude', row.get('End Long')) or None,

# CORRECT — NaN-safe version:
import math
def nn(v): return None if v is None or (isinstance(v, float) and math.isnan(v)) else v

'start_lat': nn(row.get('Start Latitude', row.get('Start Lat'))),
'start_long': nn(row.get('Start Longitude', row.get('Start Long'))),
'end_lat': nn(row.get('End Latitude', row.get('End Lat'))),
'end_long': nn(row.get('End Longitude', row.get('End Long'))),
```

Also the column names in the original code were wrong. The file uses:
- `Employee Code` (separate column) — not embedded in name
- `First Visit CS ID` (with spaces) — not `First_Visit_CS_ID`
- `Last Visit CS ID` (with spaces) — not `Last_Visit_CS_ID`
- `Start Latitude` — not `Start Lat`
- `Start Longitude` — not `Start Long`
- `End Latitude` — not `End Lat`
- `End Longitude` — not `End Long`
- `Is Regularized` (with space) — not `Is_Regularized`

### Secondary Issue
The attendance validation in `main.py` checks if the date already exists in the database and blocks re-upload with error:
`"Attendance for 2026-03-19 already exists in database. This is an APPEND-ONLY file."`

During debugging, 2 test rows were inserted manually. These need to be deleted before uploading:
```sql
DELETE FROM attendance;
```

---

## Other Known Issues Already Fixed (in current codebase)

1. ✅ Password hash was wrong in schema.sql — fixed by running password reset command
2. ✅ `::jsonb` cast syntax error in upload_log insert — fixed to `cast(:warns as jsonb)`
3. ✅ `::jsonb` cast in fraud_flag insert — fixed to `cast(:ev as jsonb)`
4. ✅ Smart insights insert parameter name mismatch — fixed
5. ✅ View Ticket snapshot insert was row-by-row (slow/timeout) — fixed to bulk insert
6. ✅ `SENDBACK` vs `SENTBACK` status normalization — fixed in pipeline
7. ✅ MTD closure rate query missing `ym` parameter — fixed

---

## How to Start the App (Mac)

```bash
cd ~/Downloads/dashboard
docker-compose up -d --build
```

Wait 3-4 minutes, then reset the admin password:
```bash
docker exec sad_backend python3 -c "import bcrypt; from sqlalchemy import create_engine, text; h = bcrypt.hashpw(b'Admin@1234', bcrypt.gensalt()).decode(); engine = create_engine('postgresql://dashboard:dashboard123@db:5432/service_dashboard'); conn = engine.connect(); conn.execute(text(\"UPDATE app_user SET password_hash = '\" + h + \"' WHERE username = 'admin'\")); conn.commit(); print('Done')"
```

Open http://localhost — login with admin / Admin@1234

---

## What Needs To Be Done Next

### Immediate (fix attendance upload)
1. Fix `load_attendance()` in `pipeline.py` — NaN coordinates + correct column names
2. Clear test rows: `docker exec -it sad_db psql -U dashboard -d service_dashboard -c "DELETE FROM attendance;"`
3. Rebuild: `docker-compose up -d --build`
4. Upload attendance file — should show ✅ 157 rows loaded

### After Attendance Works
1. Upload Engineer Master file
2. Upload Customer Site Master file
3. Verify dashboard shows real data
4. Test engineer leaderboard scores
5. Test fraud flags

### Known Column Name Issues to Check in Other Files
The B2B offline file also had 1302 orphaned rows (all rows showed `is_orphaned=True`) — this means the CS IDs in B2B offline don't match the cs_id values in customer_site_master. Either:
- Customer site master hasn't been uploaded yet (most likely)
- The cs_no format in B2B offline differs from cs_id in site master

Upload the site master first, then re-upload B2B offline to fix this.

---

## File to Fix Right Now

**File:** `backend/etl/pipeline.py`

**Function:** `load_attendance()` starting around line 370

**Exact fix needed:**

```python
def load_attendance(df: pd.DataFrame, engine: Engine) -> int:
    """Append-only — new rows only"""
    import math
    def nn(v): return None if v is None or (isinstance(v, float) and math.isnan(v)) else v
    
    log.info("Loading Attendance data...")
    rows = []
    for _, row in df.iterrows():
        emp_code = safe_str(row.get('Employee Code', ''))
        emp_name = safe_str(row.get('Employee Name', ''))
        if not emp_code:
            emp_name, emp_code = parse_employee_id(emp_name)
        if not emp_code and not emp_name: continue

        att_date = safe_date(row.get('Attendance Date'))
        if not att_date: continue

        r = {
            'employee_code': emp_code,
            'employee_name': emp_name,
            'service_state': safe_str(row.get('Service State', '')),
            'attendance_date': att_date,
            'attendance_status': safe_str(row.get('Attendance Status', '')),
            'attendance_month': safe_str(row.get('Attendance Month', '')),
            'in_datetime': safe_ts(row.get('In Date Time', '')),
            'out_datetime': safe_ts(row.get('Out Date Time', '')),
            'first_visit_cs_id': safe_str(row.get('First Visit CS ID', row.get('First_Visit_CS_ID', ''))),
            'last_visit_cs_id': safe_str(row.get('Last Visit CS ID', row.get('Last_Visit_CS_ID', ''))),
            'start_lat': nn(row.get('Start Latitude', row.get('Start Lat'))),
            'start_long': nn(row.get('Start Longitude', row.get('Start Long'))),
            'end_lat': nn(row.get('End Latitude', row.get('End Lat'))),
            'end_long': nn(row.get('End Longitude', row.get('End Long'))),
            'is_regularized': bool(str(row.get('Is Regularized', row.get('Is_Regularized', ''))).lower() in ['yes','true','1','y']),
            'regularized_status': safe_str(row.get('Regularized_Status', row.get('Regularized Status', ''))),
        }
        rows.append(r)
```

After fixing this function, rebuild the backend container:
```bash
docker-compose up -d --build backend
```

Then clear any test data and upload the attendance file again.
