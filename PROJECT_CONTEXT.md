# SERVICE ANALYSIS DASHBOARD — COMPLETE PROJECT CONTEXT
## Version 2.0 | PAN India Alarm System Maintenance Company
### Last Updated: March 2026

---

## 1. COMPANY OVERVIEW

A PAN India B2B alarm system maintenance company servicing banks and ATMs across India.

- **25,000+ active B2B sites** (bank branches, ATMs, financial institutions)
- **250+ field engineers** across India
- **28+ states, 4 zones**
- **~100,000 tickets** in 4-month rolling window
- Engineers use **Service Connect** mobile app for all field operations
- Tech support team reviews and approves completed tickets

**Current problem being solved:** Operations team spends 1+ hour/day on Excel, data is 2 days old, no deep intelligence or fraud detection.

---

## 2. DATA SOURCES — COMPLETE SPECIFICATION

### 2.1 Universal Join Keys
- **CS ID** = Primary key for sites. Appears as `cs_no` in B2B Offline, `cs_id` in Customer Site Master, `CS ID` in View Ticket and Visit Form.
- **Employee Code** = Primary key for engineers. Appears across Attendance, Engineer Master, View Ticket, Visit Form (parsed from `Technician Name` field).
- **Service Area Code** = Links engineers to their geographic area and associated sites.

### 2.2 File 1: Customer Site Master
- **Source:** Service Connect (Oracle system)
- **Frequency:** Periodic full replace
- **Primary Key:** `cs_id`
- **Key columns:** `cs_id`, `customer_site_id`, `oracle_customer_name`, `oracle_site_name`, `oracle_site_number`, `service_area_code`, `service_delivery_type` (ENGINEER/VENDOR), `site_state`, `site_lat`, `site_long`, `site_pin_code`, `active_status`, `business_type` (B2B/B2C), `b2b_code`, `zone`, `territory_code`
- **Notes:**
  - 80% of sites have lat/long, of which ~80% is accurate
  - One CS ID = one site, always. No sub-site splitting.
  - `active_status` comes as 'Y'/'N' in raw data — map to 'active'/'inactive'
  - Service Area Code links site to engineer's area of responsibility

### 2.3 File 2: Engineer Master
- **Source:** Service Connect
- **Frequency:** Periodic full replace
- **Primary Key:** `Employee Code`
- **Key columns:** `Employee Code`, `Employee Name`, `Service Area Code`, `Service Area`, `State`, `Designation`
- **Coming soon:** `home_lat`, `home_long` (engineer's home/base location — will be added to this file)
- **Notes:**
  - All engineers are generalist — no specialisation, all can visit any site
  - Engineers rarely reassigned — Engineer Master updated when it happens
  - Employee Name format in other files: `"Name (EMP-CODE)"` — parse with regex `\(([^)]+)\)$`

### 2.4 File 3: View Ticket
- **Source:** Service Connect
- **Frequency:** Daily full replace + store as versioned daily snapshot
- **Primary Key:** `Ticket ID`
- **Key columns:** `Ticket ID`, `CS ID`, `Oracle Site No`, `State Name`, `Ticket Status`, `Ticket Status Reason`, `Aging Days`, `Total Visits`, `Ticket Type`, `Ticket Sub-Type`, `Create Date`, `Planned Date`, `Ticket Assigned Type` (ENGINEER/VENDOR), `Ticket Assigned To` (format: "Name (EMP-CODE)"), `Current Approver Name`, `Last Visit In Date-Time`, `Last Visit Out Date-Time`, `Last Submission Date Time`, `Ticket Closed Date & Time`, `Cancelled By Name`, `Cancelled Date-Time`
- **Notes:**
  - `Last Visit In/Out` = only the MOST RECENT visit timestamps (not full history)
  - Full visit history is in the separate Visit Form file
  - Daily snapshots required for Pattern #3 (chronic PENDING detection)
  - Retain snapshots for 90 days minimum

### 2.5 File 4: Attendance Report
- **Source:** Service Connect
- **Frequency:** Daily APPEND ONLY — never replace, never re-upload same date
- **Primary Key:** `Employee Code` + `Attendance Date`
- **Key columns:** `Employee Name`, `Employee Code`, `Service State`, `Attendance Date`, `Attendance Status`, `Attendance Month`, `In Date Time`, `Out Date Time`, `Outstation`, `Is Regularized`, `Working Hours`, `Start Latitude`, `Start Longitude`, `End Latitude`, `End Longitude`, `First Visit CS ID`, `Last Visit CS ID`, `First Visit Ticket ID`, `Last Visit Ticket ID`
- **CRITICAL — How Service Connect Attendance Works:**
  - Punch-in: Engineer selects ANY ticket (OPEN/PENDING/SENDBACK) from ANY area as location proof. Records GPS only. Does NOT log a visit on that ticket.
  - Punch-out: Engineer CANNOT punch out unless he has visited at least one ticket that day. Must be at physical location of his LAST VISITED ticket.
  - Minimum fraud pattern: Punch in near home → do ONE minimal visit (to unlock punch-out) → go home. Attendance shows Present 8hrs. Ticket data shows 1 visit.
  - `First Visit CS ID` = site used for punch-in (may be out of area)
  - `Last Visit CS ID` = site of last actual visit of the day

### 2.6 File 5: B2B Offline Data
- **Source:** EXTERNAL — NOT from Service Connect
- **Frequency:** Daily full replace
- **Primary Key:** `cs_no` (= CS ID)
- **Key columns:** `cs_no`, `Alarm Date`, `B2B Code`, `Site Name`, `No. Of Days` (offline days), `Bucket`, `Branch Code / ATM ID`, `State`, `Offline Date & Time`, `Zone`, `Segment` (PSU/PVT)
- **CRITICAL Integration Logic:**
  ```
  B2B Offline CS ID
      ├── EXISTS in Customer Site Master?
      │       ├── YES → Normal offline site — include in all calculations
      │       │         Check active tickets (OPEN/PENDING/SENDBACK/COMPLETED)
      │       │              ├── YES → Being worked on
      │       │              └── NO + offline 4+ days → ALERT: No ticket raised
      │       └── NO → "Missing / Not Added"
      │                 Show SEPARATELY in Offline Module
      │                 EXCLUDE from all offline % calculations
      │                 Do NOT count in state health metrics
  ```
- **Offline Buckets:** 1-3 days, 4-7 days, 8-15 days, 16-30 days, 31-60 days, 61-90 days, 90+ days

### 2.7 File 6: Visit Form (NEW — Phase 2)
- **Source:** Service Connect (engineer fills on mobile app at site)
- **Frequency:** Daily or periodic upload — separate Excel file
- **Primary Key:** `Ticket ID` + `Visit Date` (one row per visit — one ticket can have multiple rows)
- **Exact column names as in Excel:**
  `Technician Name`, `Ticket ID`, `Customer Name`, `Site Name`, `CS ID`, `Creation Date`, `Visit Date`, `Ticket Status`, `1. Site Status`, `1a. Inactive Reason`, `1b. Dismantle Material`, `2. Actual Problem found`, `3. Action taken to Solve`, `4. Problem Solved`, `5. Reason`, `6. Action to be taken`, `7. Nearest Police Station`, `8. SMPS Input`, `9. Hooter`, `10. Continuous Recording Days`, `11. PM Done`, `12. Two way working`, `13. Smoke Sensor Working`, `1. ATM ID`, `2. ATM ID`, `3. ATM ID`, `4. ATM ID`, `5. ATM ID`
- **Key fields for ML:**
  - `4. Problem Solved` = YES/NO → Primary FTFR signal
  - `5. Reason` → Why not solved → Chronic PENDING detection
  - `11. PM Done` → Preventive maintenance compliance
  - `8. SMPS Input`, `9. Hooter`, `10. Continuous Recording Days`, `12. Two way working`, `13. Smoke Sensor Working` → Equipment health for predictive maintenance ML
- **Notes:**
  - `Technician Name` is in same `"Name (EMP-CODE)"` format — parse same way
  - One ticket can have 2, 3, 4+ visit rows (engineer visits multiple times before resolution)
  - ATM ID fields (1-5) = ignore for now, one CS ID = one site

---

## 3. TICKET STATUS — COMPLETE DEFINITION

| Status | Meaning | Active? | Engineer's Bucket? | Fraud Detection |
|--------|---------|---------|-------------------|-----------------|
| OPEN | Raised, no visit yet | ✅ Yes | ✅ Yes | No-ticket alert |
| PENDING | Visited, unresolved, needs more work | ✅ Yes | ✅ Yes | Chronic PENDING check |
| SENDBACK | Tech support rejected → back to engineer (behaves like PENDING) | ✅ Yes | ✅ Yes | Same as PENDING |
| COMPLETED | Engineer done, waiting for tech support approval | ✅ Yes | ❌ No (at tech support) | NO FV flags |
| CLOSED | Tech support approved — fully resolved (FINAL) | ❌ No | ❌ No | FV-04, FV-06 apply |
| CANCELLED | Killed | ❌ No | ❌ No | Exclude everywhere |
| REJECTED | Rejected | ❌ No | ❌ No | Exclude everywhere |

**Active tickets = OPEN + PENDING + SENDBACK + COMPLETED**
**Engineer's responsibility bucket = OPEN + PENDING + SENDBACK**
**No-ticket offline alert = site offline 4+ days AND no OPEN/PENDING/SENDBACK ticket**
**FV-04 (no visit timestamp) = CLOSED only, NOT COMPLETED**

**Raw data variants:** `SENDBACK` and `SENTBACK` and `SENT BACK` all mean the same status — normalise to `SENTBACK` on ingestion.

---

## 4. WORKING PATTERN

- **Hours:** 10 AM to 6 PM (8-hour day)
- **Days:** Monday to Saturday
- **Holidays:** Captured in `Attendance Status` field — no separate holiday logic needed in ETL
- **Special rule — 2nd and 4th Saturdays:** Bank branches are CLOSED. Engineers visit offsite ATMs only. These need prior key arrangements. Detect automatically from calendar (2nd and 4th Saturday of each month).
- **Bank holidays:** Same rule as 2nd/4th Saturday — branches closed, offsite ATMs only. Managed via admin-configurable holiday list.
- **Punch-in deadline:** Engineer should punch in by 11 AM. After 11 AM = late.

---

## 5. ENGINEER AND SERVICE AREA

- **Service Area:** ~50–150 sites per engineer (varies by geography and density)
- **Area type:** 1–4 cities/districts per service area, balanced by site count
- **Travel:** Mostly bike. 200+ km/day → company policy says public transport
- **Skills:** All engineers are generalist — no specialisation, all can visit any site type
- **Reassignment:** Very rare. Engineer Master updated manually when it happens.

---

## 6. FRAUD DETECTION SYSTEM

### 6.1 FV Rules (Individual Ticket Anomalies)

| Rule | Trigger | Severity | Score Impact |
|------|---------|----------|-------------|
| FV-01 | Last Visit duration < 10 minutes | HIGH | -2 pts |
| FV-03 | Ticket created AND closed same day, lifecycle < 60 minutes | HIGH | -2 pts |
| FV-04 | Ticket CLOSED (not COMPLETED) but Last Visit In = NULL | HIGH | -2 pts |
| FV-06 | Ticket closed on date with no attendance record | HIGH | -2 pts |

### 6.2 Fraud Patterns (Behavioural)

| Pattern | Description | Severity |
|---------|-------------|----------|
| P1 | One-visit work day: Present, visited 0-1 tickets, large open backlog in area | CRITICAL/HIGH/MEDIUM |
| P2 | Same-day open+close: Site offline 2+ days before ticket raised, closed same day as opened, 1 visit | HIGH |
| P3 | Chronic PENDING: PENDING ticket with identical reason unchanged for 15+ days (non-stock reasons) | HIGH |
| P7 | Site offline 4+ days with NO active ticket raised (OPEN/PENDING/SENDBACK) | HIGH |
| P8 (NEW) | Repeat No-Resolve: Engineer visits same site 3+ times in 30 days, Problem Solved=NO each time, site keeps going offline within 3 days | HIGH |
| P9 (NEW-ML) | Form Fraud: Same visit form answers copied across 3+ tickets on same day (text similarity >85%) | MEDIUM |

### 6.3 Fraud Severity and Score Impact
- CRITICAL: -7 pts
- HIGH: -4 pts (FV rules: -2 pts each)
- MEDIUM: -2 pts
- 3+ HIGH/CRITICAL flags in a month → Engineer forced to RED (score capped at 35)
- Confirmed fake by reviewer → -5 pts each, no cap

### 6.4 Stock-Related PENDING Exceptions
Do NOT flag as chronic PENDING if reason contains: `stock`, `material`, `spare`, `part`, `component`, `inventory`, `power issue`, `under renovation`, `power cut`, `power failure`

### 6.5 SENDBACK Score Impact
Small negative effect. If same engineer has SENDBACK on same site repeatedly → escalating penalty. Single SENDBACK = -0.5 pts. 3+ SENDBACK on same site = -2 pts additional.

---

## 7. COMPOSITE ENGINEER SCORE (0–100)

| Component | Weight | Formula |
|-----------|--------|---------|
| Ticket Closure Rate | 25 pts | (CLOSED ÷ Total excl. CANCELLED/REJECTED) × 25 |
| Service Area Coverage | 20 pts | (Unique CS IDs with ≥1 CLOSED ÷ Total PoP CS IDs) × 20 |
| Avg Resolution Time | 20 pts | max(0, 20 − (avg_days × 2.5)) |
| Area Offline % + Trend | 15 pts | 10 pts for avg offline % + 5 pts if improving vs last month |
| Repeat Visit Rate (inverted) | 10 pts | max(0, 10 − (repeat_rate% × 0.33)) |
| Attendance & Punctuality | 7 pts | (attend_rate × 0.05 + (1−late_rate) × 0.02) × 100 ÷ 7 |
| Fraud Flags (inverted) | 3 pts | 3 − (HIGH_flags × 1) − (regularization_abuse × 0.5), floor 0 |

**Score Bands:** 90-100 Exceptional | 75-89 Good | 60-74 Average | 45-59 Below Average | <45 Poor

**FTFR (First Time Fix Rate):** Uses `4. Problem Solved = YES` from Visit Form AND site did not reappear in B2B Offline within 7 days of closure. Both conditions required.

---

## 8. PRODUCTIVE DAY — DEFINITION

A productive day = engineer meets ALL of these:
1. Punch-in before 11 AM
2. Closures ≥ state average for that day OR `PM Done = YES` on 2+ sites
3. At least one site stayed online 7+ days after closure (real quality signal)
4. Sites visited spread across service area (not clustering in one corner — use GPS spread)

- Meets ALL 4 → Productive Day = YES
- Meets 3 of 4 → Borderline (amber)
- Meets 0-2 → Not productive

---

## 9. STATE SCORE

**Base:** Average of all engineer scores in state

**Penalties:**
- -5 pts if >5% of sites offline >30 days
- -3 pts if carryforward ticket rate >10%
- -4 pts if state avg Productive Days rate <60%
- -2 pts if avg ticket creation lag >3 days (sites going offline without tickets being raised)

**Bonus:** +3 pts if mean resolution time <2 days

---

## 10. SMART INSIGHT RULES (Auto-Generated Alerts)

| Rule | Trigger | Priority |
|------|---------|----------|
| SI-01 | State offline rate >15% | CRITICAL |
| SI-02 | State offline rate 5-15% | WARNING |
| SI-03 | Engineer 0 productive visits in 21+ present days | CRITICAL |
| SI-04 | OPEN tickets with no Planned Date >3 days old | CRITICAL |
| SI-05 | Ticket closed on absent day | CRITICAL |
| SI-06 | Sites offline >90 days with open ticket | CRITICAL |
| SI-07 | SENTBACK rate up >10% week-over-week | WARNING |
| SI-08 | Top state by closure rate | INFO |
| SI-09 | Engineers with Score <40 | WARNING |
| SI-10 | Stock-PENDING tickets up >20% in 7 days | WARNING |
| SI-11 | Sites not visited 30+ days | WARNING |
| SI-12 | 3+ engineers one-visit-only days in same state | CRITICAL |

---

## 11. TODAY'S PROBLEMS DIGEST (5 Auto-Alerts)

1. Engineers with one-visit day AND large open backlog (Pattern #1)
2. Sites back offline within 1-2 days of closure
3. Chronic PENDING 15+ days same reason (non-stock)
4. Open tickets aging 7+ days with zero visits
5. Offline 4+ days with no ticket raised

---

## 12. PLAN MODULE SPECIFICATION

### 12.1 Overview
- **Purpose:** Generate optimised daily visit route for each engineer
- **Runs:** Automatically every day at 3:30 AM
- **Visible to:** Ops Manager and State Manager only (NOT shown to engineers)
- **Scope:** Fixed plan for the day (no real-time replanning in v1)

### 12.2 Priority Score Formula
```
Priority = (Site Offline Days × 3)
         + (Ticket Aging Days × 2)
         + (SENDBACK bonus: +10)
         + (Previous failed visits × 5)
         - PENDING-stock tickets < 10 days aging → EXCLUDED entirely
         - PENDING-stock tickets > 10-15 days aging → INCLUDED (parts may have arrived)
```

### 12.3 Route Algorithm
```
For each active engineer every morning at 3:30 AM:

Step 1: Load ticket bucket (OPEN + PENDING + SENDBACK)
Step 2: Remove PENDING-stock tickets with aging < 10 days
Step 3: Check date — if 2nd/4th Saturday or bank holiday:
        Remove bank branch sites, keep offsite ATMs only
Step 4: Score each ticket using Priority formula above
Step 5: If zero tickets → load sites not visited in 30+ days (PMS plan)
Step 6: Route optimisation:
        - Start: Engineer home location (home_lat, home_long)
        - Algorithm: Nearest-neighbour from home, weighted by priority score
        - Optimisation: 2-opt improvement pass to reduce total distance
        - No GPS sites: Insert at midday position (not first, not last)
        - End: Estimate return to home
Step 7: Store in plan table with estimated travel distances
Step 8: Available in dashboard by 4 AM
```

### 12.4 Optimisation Goal
Total service optimisation = minimise (travel distance/cost) + minimise (resolution time)

### 12.5 No Open Tickets Fallback
If engineer has zero open tickets → generate Preventive Maintenance plan:
Sites in engineer's service area not visited in the longest time, sorted by days since last visit.

---

## 13. ML/AI LAYER (Phase 3)

### Model 1: Resolution Probability
- **Input:** Ticket type, sub-type, problem found (from visit form), engineer ID, site history, visit count for this ticket, engineer's historical resolution rate for this problem type
- **Output:** Probability (0-1) this visit will resolve the ticket
- **Use:** Plan module prioritisation, manager alerts for stuck tickets

### Model 2: Repeat Offline Prediction
- **Input:** SMPS reading, recording days, action taken, site offline history, equipment health fields from visit form
- **Output:** Probability site goes offline again within 7 days of closure
- **Use:** Preventive maintenance scheduling, FTFR quality signal

### Model 3: Visit Duration Estimation
- **Input:** Ticket type, problem found, engineer historical visit durations for similar issues
- **Output:** Estimated minutes at this site
- **Use:** Plan module — how many sites can engineer realistically complete today

### Model 4: Form Fraud Detection (Pattern P9)
- **Input:** Visit form text answers across multiple visits on same day, same engineer
- **Output:** Text similarity score — are answers copy-pasted?
- **Threshold:** >85% similarity across 3+ forms = flag
- **Use:** New fraud flag FV-08 / Pattern P9

### Model 5: Engineer Skill Profiling
- **Input:** Problem types resolved, FTFR by category, visit duration by problem type
- **Output:** Engineer strength/weakness profile per problem category
- **Use:** Future intelligent ticket assignment, training recommendations

---

## 14. TECHNOLOGY STACK

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 15+ with monthly partitioning |
| ETL | Python + Pandas + SQLAlchemy |
| Backend API | Python FastAPI |
| Cache | Redis (15-min TTL, invalidated on upload) |
| Frontend | React.js + Tailwind CSS |
| Hosting | AWS EC2 t3.medium minimum |
| Auth | JWT RS256, 8hr expiry, role + state_code in payload |
| Storage | AWS S3 or local disk for uploaded files |

---

## 15. USER ROLES

| Role | Access |
|------|--------|
| Admin | Full access + data uploads + user management |
| Ops Manager | PAN India view, all states, all engineers, fraud review |
| State Manager | Own state only (server-enforced JWT), all engineers in state, fraud review |

Both Ops Manager and State Manager can review and mark fraud flags as Valid or Confirmed Fake.

---

## 16. DATA UPLOAD RULES

| File | Method | Notes |
|------|--------|-------|
| B2B Offline | Daily full replace | Delete today's data, insert fresh |
| View Ticket | Daily full replace + snapshot | Replace current + store versioned snapshot |
| Attendance | Daily APPEND ONLY | Never replace — system blocks duplicate dates |
| Engineer Master | Periodic full replace | |
| Customer Site Master | Periodic full replace | |
| Visit Form | Daily or periodic append | Append by ticket_id + visit_date |

---

## 17. CURRENT SYSTEM STATUS (as of March 2026)

### What is Built and Working
- Dashboard with KPI cards (offline sites, open tickets, attendance, fraud flags)
- State health map with offline % per state
- Offline bucket distribution chart
- Today's Problems Digest (5 alert types)
- Engineer Leaderboard with composite scores
- Engineer profile with attendance calendar, score breakdown, fraud flags
- Ticket Analysis (aging, breach list, SENTBACK, no-ticket sites, chronic PENDING)
- Fraud Flags page with P1, P2, P3, P7, FV-01, FV-03, FV-04, FV-06
- Smart Insights panel
- Data Upload page with ETL pipeline
- User Management
- Role-based access control

### Known Issues to Fix
1. FV-04 incorrectly flags COMPLETED tickets — should only flag CLOSED
2. No-ticket alert uses wrong active status set — fix to OPEN+PENDING+SENDBACK
3. B2B missing sites not shown separately — currently silently orphaned
4. Productive day definition too simple — needs full redefinition
5. FTFR estimated from B2B Offline reappearance — should use Visit Form `Problem Solved` field
6. State Intelligence page empty — monthly facts not populating correctly
7. Attendance upload via web UI has NaN lat/long bug (fixed in pipeline, needs container update)
8. Customer Site Master upload via web UI fails — workaround script exists

### What Needs to Be Built Next
- Phase 1: All bug fixes above
- Phase 2: Visit Form module, Missing Sites module, Plan Module
- Phase 3: ML models

---

## 18. DATABASE SCHEMA — KEY TABLES

### Existing Tables
- `customer_site_master` — 22,227 sites loaded
- `engineer_master` — 296 engineers loaded
- `view_ticket` — 10,811 tickets (daily replace + snapshot)
- `ticket_snapshot` — daily snapshots for 90 days (fraud detection)
- `attendance` — append-only, 157 rows loaded
- `b2b_offline` — 1,302 offline sites daily
- `fact_engineer_daily` — pre-aggregated daily KPIs per engineer
- `fact_engineer_monthly` — pre-aggregated monthly scores per engineer
- `fact_state_daily` — pre-aggregated daily KPIs per state
- `fact_state_monthly` — pre-aggregated monthly scores per state
- `fraud_flag` — all detected fraud patterns
- `smart_insight` — auto-generated alerts
- `upload_log` — audit trail of all uploads
- `app_user` — user accounts with roles
- `app_settings` — configurable system settings

### Tables to Add
- `visit_form` — one row per engineer visit (15-20 question form)
- `plan` — daily generated route plan header per engineer
- `plan_detail` — ordered site list for each plan
- `bank_holiday` — admin-configurable list of bank holidays

---

## 19. DEPLOYMENT

- **Docker Compose** — 3 containers: PostgreSQL, FastAPI backend, React frontend (Nginx)
- **Running on:** Local Mac (developer) with Docker Desktop
- **Target:** AWS EC2 t3.medium
- **Access:** `http://localhost` (local) or server IP
- **Default login:** admin / Admin@1234 (force change on first login)

---

## 20. IMPORTANT BUSINESS RULES SUMMARY

1. **One CS ID = one site, always.** No sub-site splitting.
2. **Attendance is APPEND ONLY.** Never re-upload the same date.
3. **View Ticket daily snapshot MUST be stored** — fraud Pattern P3 requires comparing today vs 15 days ago.
4. **B2B sites not in Site Master = "Missing / Not Added"** — exclude from all offline % metrics.
5. **COMPLETED ≠ CLOSED.** COMPLETED is at tech support. No fraud flags on COMPLETED.
6. **SENDBACK = PENDING** in all logic except scoring (SENDBACK gets small additional penalty if recurring).
7. **Stock PENDING < 10 days** = skip in Plan Module (waiting for parts, visit is wasted).
8. **2nd and 4th Saturday** = bank branches closed, offsite ATMs only.
9. **Punch-in selects ANY ticket for GPS** — does NOT create a visit on that ticket.
10. **Visit Form has one row per VISIT** — one ticket can have multiple visit rows.
11. **FTFR requires TWO conditions:** Visit Form `Problem Solved = YES` AND site did not reappear in B2B Offline within 7 days.
12. **No-ticket alert threshold = 4+ days offline** with no OPEN/PENDING/SENDBACK ticket.
13. **Plan generated at 3:30 AM daily** — fixed for the day, no real-time updates in v1.
14. **Plan visible to managers only** — engineers do NOT see their planned route.

---

## 21. OPEN QUESTIONS / FUTURE DECISIONS

1. Visit form upload frequency — daily or periodic? (answer: daily or periodic, separate Excel)
2. Bank holiday list management — admin screen to be built (Phase 2)
3. Engineer home lat/long — will be added to Engineer Master when available
4. `oracle_site_number` vs `CS ID` — confirmed same in this system, CS ID is the join key
5. Phase 3 ML models — require minimum 2-3 months of visit form data to train

---

*End of Context Document*
*Project: Service Analysis Dashboard v2.0*
*Company: PAN India Alarm System Maintenance*
*Built with: FastAPI + PostgreSQL + React + Docker*
