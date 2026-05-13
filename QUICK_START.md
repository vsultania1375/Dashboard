# VProtect Dashboard - Quick Start Guide

**For:** Claude Code / Claude Sonnet  
**Time to Read:** 5 minutes  
**Before You Start:** Make sure you have DATABASE_LOGIC.md, DASHBOARD_SPECIFICATION.md, and IMPLEMENTATION_GUIDE.md in the project

---

## WHAT ARE WE BUILDING?

A **Field Service Management Intelligence Dashboard** that shows:
1. **Offline Sites Heatmap** - Where are sites offline? (For how long?)
2. **Engineer Performance Report** - Who's productive? Who's missing?
3. **Real-time Insights** - Attendance, visits, tickets, productivity

**Users:** Operations managers tracking 250-296 engineers across 28 Indian states  
**Data:** Daily uploads (5 Excel files) → Database → Dashboard

---

## ARCHITECTURE (30-Second Overview)

```
Daily Uploads (Excel files)
         ↓
   ETL Pipeline
         ↓
 PostgreSQL Database
         ↓
   FastAPI Backend
         ↓
   React Frontend (Dashboard)
         ↓
   User sees: Charts, Tables, Export
```

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Frontend: React 18 + TypeScript + Tailwind + Recharts
- Deployment: Docker Compose

---

## 3 DOCUMENTS YOU NEED

1. **DATABASE_LOGIC.md** (40 pages)
   - What tables exist
   - What columns are in each table
   - How data flows in (ETL)
   - Calculation formulas
   - **Read this when:** Building backend queries

2. **DASHBOARD_SPECIFICATION.md** (30 pages)
   - What the UI looks like
   - What filters exist
   - Chart specifications
   - Table columns & calculations
   - Export formats
   - **Read this when:** Building frontend, designing API responses

3. **IMPLEMENTATION_GUIDE.md** (50 pages)
   - Phased breakdown (3 phases, 9 tasks)
   - Code examples for each task
   - File structure
   - Acceptance criteria for each phase
   - **Read this when:** Starting actual coding

---

## YOUR JOB (SIMPLE VERSION)

### Phase 1: Database & Backend (2 weeks)
1. Create PostgreSQL schema (8 tables, 50 indexes)
2. Build FastAPI routes for filters, data fetch, export
3. Implement ETL pipeline for file uploads
4. Calculate engineer metrics (attendance, visits, productivity)

### Phase 2: Frontend (1-2 weeks)
1. Build React dashboard with filter panel
2. Create offline distribution bar chart
3. Create engineer performance table (18 columns)
4. Implement pagination and sorting
5. Add export to Excel/CSV

### Phase 3: Integration (1 week)
1. Connect frontend to backend APIs
2. Test end-to-end data flow
3. Optimize performance
4. Deploy with Docker

---

## CRITICAL DATA RULES (READ CAREFULLY!)

### ⚠️ MUST DO:

1. **CS_ID is VARCHAR, NOT INT**
   - Some values: "071", "00123" (leading zeros matter!)
   - Store as `VARCHAR(20)` everywhere
   - Don't convert to integer

2. **Filter to PSU Banks ONLY**
   - In offline_data: `segment = 'PSU'`
   - Private banks excluded
   - Don't process Vendor bank records

3. **Active Engineers ONLY**
   - `active_status = 'YES'` REQUIRED
   - `designation = 'Engineer'` REQUIRED
   - Don't show inactive/non-engineer roles

4. **Attendance Status is RECALCULATED**
   - Don't use original column
   - Recalculate from `in_datetime`:
     - Before 10 AM → "OnTime"
     - After 10 AM → "Late"
     - NULL → "Absent"

5. **Service Area Code is 1:1 with Engineer**
   - Each engineer has ONE service area
   - Each service area has ONE engineer
   - Use this to map engineers ↔ sites

6. **Ticket Status Values** (must be exact):
   ```
   'OPEN', 'PENDING', 'SENTBACK', 'COMPLETED', 
   'CLOSED', 'CANCELLED', 'REJECTED'
   ```
   Invalid values → skip that record

---

## KEY METRICS (What to Calculate)

**For Each Engineer:**
- `att_days` - Days marked present (OnTime OR Late)
- `working_days` - Mon-Fri only (no Sundays/Saturdays)
- `att_percent` - (att_days / working_days) × 100
- `prod_days` - Days with at least one visit
- `zero_prod_days` - att_days - prod_days
- `total_visits` - Count of all visits
- `distinct_sites` - Count of unique sites visited
- `repeat_rate` - total_visits / distinct_sites

**For Each Ticket:**
- `ticket_status` - Current status (OPEN, CLOSED, etc.)
- `aging_days` - Days since created

**For Offline Sites:**
- `aging_days` - Days since last activity
- `offline_bucket` - "1-3 Days", "4-7 Days", etc.
- Filter: Only `aging_days > 3` for insights

---

## FILE UPLOAD STRUCTURE

Users will upload these files DAILY:

1. **B2B_Offline_DD-MM-YYYY.xlsx**
   - Sheet: "B2B"
   - Filter: `segment = 'PSU'`
   - Store: APPEND to `offline_data` table (historic tracking)

2. **view_ticket.xlsx**
   - Filter: `assigned_type = 'Engineer'`
   - Store: FULL REPLACE `view_ticket` (latest state)
   - Note: Parse `assigned_to` column to extract employee_id

3. **Attendance_Data.xlsx**
   - Store: APPEND to `attendance_log`
   - Recalculate: `attendance_status` from `in_datetime`

4. **visit_data.xlsx**
   - Store: APPEND to `visit_log` (check for duplicates)

5. **EmployeeMaster.xlsx** (as-needed)
   - Filter: `active_status = 'YES'` AND `designation = 'Engineer'`
   - Store: UPSERT to `engineer_master`

6. **customer_site_mst.csv** (as-needed)
   - Store: UPSERT to `customer_site_master`

---

## DASHBOARD LAYOUT (Bird's Eye View)

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: VProtect Dashboard                                 │
├─────────────────────────────────────────────────────────────┤
│  FILTERS: From Date [ ] To Date [ ] State [▼] [Refresh]    │
├─────────────────────────────────────────────────────────────┤
│  KEY METRICS:                                               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 127 Eng │ │ 18.5K V │ │ 3.21x R │ │ 2.1K OS │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│  TAB: Distribution | Performance Report | ...               │
├─────────────────────────────────────────────────────────────┤
│  [Chart: Offline Sites by Bucket]                           │
├─────────────────────────────────────────────────────────────┤
│  [Table: Engineer Performance (18 columns)]                 │
│  PAGINATION: 25 per page | Page 1 of 12 | EXPORT           │
└─────────────────────────────────────────────────────────────┘
```

---

## FILTERS

**User can select:**
1. **Date Range** - "From" and "To" (default: last 7 days)
2. **State** - "All (PAN India)" or one of 28 states
3. **Service Area** - (appears only if state selected)
4. **Active Only** - Checkbox (default: checked)

**Result:** Dashboard updates to show data for selected filters

---

## THE MAIN TABLE (18 COLUMNS)

```
| Service Area | Engineer Name | Code | Phone | State | 
| Att. Days | Working Days | Att. % | Prod. Days | Zero Prod Days |
| Total Visits | Distinct Sites | Repeat Rate |
| Closed | Open | Pending | Completed | Offline Sites |
```

**Conditional Coloring:**
- Red if: Att. % < 80% OR Zero Prod Days > 5 OR Offline Sites > 20
- Yellow if: Repeat Rate < 2.0x

---

## EXPORT OPTIONS

User clicks [📥 Download]:
1. **Excel** - 3 sheets (Summary, Engineer Details, Offline Distribution)
2. **CSV** - Engineer details table
3. **PNG** - Chart as image

Filename format:
```
VProtect_Engineer_Report_[State]_[FromDate]_[ToDate].xlsx
VProtect_Offline_Distribution_[State]_[FromDate]_[ToDate].png
```

---

## HOW TO BRIEF CLAUDE CODE

### For Phase 1.1 (Database):
```
"Create PostgreSQL schema with these tables:
1. offline_data - daily offline site records
2. view_ticket - FSM tickets
3. engineer_master - engineer info
4. visit_log - engineer visits
5. attendance_log - daily attendance
6. customer_site_master - site reference
7. service_area_master - service areas
8. offline_sites_summary - materialized view

Use DATABASE_LOGIC.md Section 2 for exact CREATE TABLE statements.
Create indexes from Section 2.3.
Load sample data (50 engineers, 1000 offline sites, 5000 tickets)."
```

### For Phase 1.2 (Backend):
```
"Build FastAPI application with these endpoints:

POST /api/engineers/performance
  - Input: {from_date, to_date, state, show_active_only}
  - Returns: {engineers: [18-column metrics], footer: {totals}}

POST /api/offline-distribution
  - Input: {from_date, to_date, state}
  - Returns: {distribution: [{bucket, count, percent}]}

GET /api/states
  - Returns: ['All (PAN India)', 'Karnataka', 'Tamil Nadu', ...]

POST /api/upload/offline-data
  - Handle file upload, validate, transform, insert
  - (see DATABASE_LOGIC.md Section 4 for ETL logic)

Similar for upload/view-ticket, upload/attendance, upload/visits

Use IMPLEMENTATION_GUIDE.md Phase 1.2 for code templates.
All queries follow calculations in DATABASE_LOGIC.md Section 5."
```

### For Phase 2.1 (Frontend):
```
"Create React dashboard with:
1. FilterPanel (date range, state select, refresh button)
2. MetricsCards (4 key metrics)
3. TabNavigation (Distribution | Performance Report)
4. OfflineDistributionChart (bar chart using Recharts)
5. EngineerPerformanceTable (18 columns, sortable, paginated)
6. ExportButton (Excel, CSV, PNG)

Layout: Sticky filter bar → Metrics → Chart → Table with footer

Use DASHBOARD_SPECIFICATION.md for exact column names and calculations.
Use Tailwind for styling (see color palette in Section 7)."
```

---

## COMMON GOTCHAS

1. **CS_ID Leading Zeros**
   - "071" ≠ 71
   - Always VARCHAR, never INT

2. **Attendance Status Recalculation**
   - Don't trust the "Attendance Status" column in file
   - Always recalculate from `in_datetime`

3. **State Filtering**
   - State must match between engineer_master and customer_site_master
   - Engineer sees only sites in their state

4. **Service Area = Engineer**
   - 1-to-1 relationship
   - Can't have 2 engineers with same service_area_code
   - Can't have service_area_code with no engineer

5. **Offline Data = Historical**
   - Don't delete old records
   - New day = APPEND new rows (same sites may reappear)
   - Enables trend analysis

6. **Tickets = Latest Snapshot**
   - Daily overwrite (FULL REPLACE)
   - Don't append old tickets
   - Only current state matters

7. **Date Format**
   - Input: DD-MM-YYYY or DD-MM-YYYY HH:MM or DD-MM-YYYY HH:MM AM/PM
   - Internal DB: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
   - Always validate on ingest

---

## PERFORMANCE TARGETS

- Page load: < 3 seconds
- API response: < 1-2 seconds per state
- Chart render: < 500ms
- Table render: < 1 second
- Export: < 10 seconds

**Optimizations:**
- Index on (state, segment, data_date) for offline queries
- Index on (employee_id, visit_date) for visit queries
- Cache state summaries (1 hour)
- Pagination (25 rows default)

---

## TESTING CHECKLIST

Before handoff, verify:

```
✓ Database
  - All 8 tables created
  - Sample data loaded
  - Queries execute correctly
  - No NULL in critical columns

✓ Backend
  - All endpoints return data
  - Filters work (by state, date range)
  - Calculations correct (spot-check 1 engineer)
  - Export endpoints functional
  - Error handling in place

✓ Frontend
  - Filter panel working
  - Chart renders without errors
  - Table displays all 18 columns
  - Pagination works
  - Export buttons work
  - Responsive (mobile/tablet/desktop)
  - No console errors

✓ Integration
  - Frontend calls backend APIs
  - Data flows end-to-end
  - Docker runs all services
  - Manual test: Select state → see data update

✓ Performance
  - Page load < 3s
  - API < 2s per query
  - No memory leaks
  - DB indexes present
```

---

## NEXT STEPS

1. **READ** DATABASE_LOGIC.md completely
2. **READ** DASHBOARD_SPECIFICATION.md completely
3. **BRIEF** Claude Code on Phase 1.1 (Database)
4. **WAIT** for Phase 1.1 completion
5. **BRIEF** Claude Code on Phase 1.2 (Backend)
6. ...and so on

**Expected Timeline:** 4-6 weeks for full build + testing

---

## QUESTIONS? 

Ask Claude:
- "Is this calculation correct for repeat_rate?"
- "Should Absent days count toward att_days?"
- "What if engineer has no visits on a day?"
- "Can service_area be NULL?"

All questions are documented in DATABASE_LOGIC.md or DASHBOARD_SPECIFICATION.md.

---

**READY?** Start Phase 1.1! 🚀
