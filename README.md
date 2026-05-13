# VProtect Field Service Management Intelligence Dashboard

**Complete Documentation Package for Claude Code Implementation**

**Created:** May 13, 2026  
**Status:** Production-Ready Specification  
**Build Time:** 4-6 weeks  

---

## 📋 WHAT'S IN THIS PACKAGE?

You have **4 comprehensive documents** that contain everything Claude Code needs to build your dashboard:

### 1. **QUICK_START.md** ⭐ START HERE
**Length:** 10 pages | **Read Time:** 10 minutes

Your 5-minute briefing document. Start here if you're short on time.

**Contains:**
- 30-second architecture overview
- Critical data rules (CS_ID, PSU filter, etc.)
- Key metrics (what to calculate)
- How to brief Claude Code for each phase
- Common gotchas
- Testing checklist

**When to Use:** Before every Claude Code session

---

### 2. **DATABASE_LOGIC.md** 📊 FOUNDATION
**Length:** 50 pages | **Read Time:** 45 minutes

The complete data model and database specification.

**Contains:**
- All 6 data sources (offline, tickets, engineers, sites, visits, attendance)
- Column-by-column schema for all 8 tables
- Data relationships & foreign keys
- Data transformation rules (ETL)
- Calculation formulas (attendance %, repeat rate, etc.)
- Daily ingestion process
- Performance optimization (indexes, partitioning)

**When to Use:** 
- When designing database (Phase 1.1)
- When writing backend queries (Phase 1.2)
- When understanding data flow

**Key Takeaway:**
```
offline_data (daily snapshot) 
    ↓ (cs_id)
customer_site_master 
    ↓ (oracle_site_no)
view_ticket 
    ↓ (employee_id)
engineer_master 
    ↓ (service_area_code = 1:1)
Service areas & sites
```

---

### 3. **DASHBOARD_SPECIFICATION.md** 🎨 UI/UX
**Length:** 40 pages | **Read Time:** 40 minutes

The exact specification for what users will see.

**Contains:**
- View 1: Offline Distribution Chart (bar chart)
  - Filters: Date range, State, Bank segment
  - X-axis: Offline buckets (1-3 Days, 4-7 Days, ..., 90+ Days)
  - Y-axis: Count of sites
  - Color coding by severity

- View 2: Engineer Performance Report (table)
  - 18 columns (service area, name, code, phone, state, att. days, working days, att. %, prod days, zero prod, visits, distinct sites, repeat rate, closed, open, pending, completed, offline sites)
  - Sortable, paginated (25/50/100 per page)
  - Color coding (red if att. % < 80%, yellow if repeat rate < 2x, etc.)
  - Footer summary (totals/averages)

- Filters: Date picker, State dropdown, Service area select, Active only toggle

- Export: Excel (3 sheets), CSV, PNG (for chart)

- Metrics: At-a-glance cards (Total Engineers, Total Visits, Avg Repeat Rate, Offline Sites)

- API response formats (JSON structure)

- Performance requirements (< 3s page load, < 2s API)

**When to Use:** 
- When designing frontend UI (Phase 2.1)
- When creating chart/table components (Phase 2.2)
- When designing API responses (Phase 1.2)

**Key Takeaway:**
```
Dashboard Layout:
┌─ Filter Bar (sticky, top)
├─ Metrics Cards (4 key numbers)
├─ Chart Tab: Offline distribution by bucket
├─ Table Tab: Engineer performance (18 cols)
├─ Footer: Totals/Averages by state
└─ Export: Excel/CSV/PNG buttons
```

---

### 4. **IMPLEMENTATION_GUIDE.md** 🛠️ CODE BLUEPRINT
**Length:** 60 pages | **Read Time:** 60 minutes

The complete step-by-step coding roadmap with examples.

**Contains:**
- **Phase 1: Database & Backend (2 weeks)**
  - 1.1: PostgreSQL schema (table creation, indexes, sample data)
  - 1.2: FastAPI endpoints (filters, metrics, export)
  - 1.3: ETL pipeline (file uploads, transformations)

- **Phase 2: Frontend (1-2 weeks)**
  - 2.1: React setup, layout, filter components
  - 2.2: Chart & table components
  - 2.3: Export functionality

- **Phase 3: Integration & Deployment (1 week)**
  - Docker Compose setup
  - End-to-end testing
  - Performance optimization

- Each task has:
  - Clear deliverables
  - Acceptance criteria (checklist)
  - Code examples/templates
  - File structure

- **Bonus:** Token optimization tips for Claude Code

**When to Use:** 
- During actual implementation (each phase)
- Reference code examples
- Know what to ask Claude Code to build

**Key Takeaway:**
```
Week 1-2: Build database (8 tables) + backend APIs
Week 2-3: Build frontend (React components)
Week 3-4: Integrate + test + deploy

Each phase builds on previous, don't skip!
```

---

## 🎯 HOW TO USE THESE DOCUMENTS

### SCENARIO 1: "I have 30 minutes"
1. Read **QUICK_START.md** (10 min)
2. Skim **DASHBOARD_SPECIFICATION.md** section 1-2 (10 min)
3. Note the critical rules from QUICK_START (10 min)

Then brief Claude Code on Phase 1.1

### SCENARIO 2: "I want to understand everything"
1. Read **QUICK_START.md** (10 min) - Big picture
2. Read **DATABASE_LOGIC.md** (45 min) - Data structure
3. Read **DASHBOARD_SPECIFICATION.md** (40 min) - UI/UX
4. Read **IMPLEMENTATION_GUIDE.md** (60 min) - How to build

Total: ~2.5 hours (well-spent!)

### SCENARIO 3: "I'm briefing Claude Code right now"
1. Open **QUICK_START.md** → copy the "How to Brief Claude Code" section
2. Paste into Claude Code prompt
3. Reference the specific file/section for details

Example:
```
"Create the PostgreSQL schema. Use DATABASE_LOGIC.md Section 2 for exact CREATE TABLE statements.
Create all 8 tables: offline_data, view_ticket, engineer_master, visit_log, 
attendance_log, customer_site_master, service_area_master, offline_sites_summary.
Load sample data: 50 engineers, 1000 offline sites, 5000 tickets."
```

---

## 📊 DOCUMENT MAP

```
START
  ↓
QUICK_START.md (5-minute overview)
  ↓
  ├─→ Need data model details? → DATABASE_LOGIC.md
  ├─→ Need UI mockups? → DASHBOARD_SPECIFICATION.md  
  ├─→ Ready to code? → IMPLEMENTATION_GUIDE.md
  └─→ Unsure about something? → Check relevant doc
```

---

## 🔑 CRITICAL RULES (READ FIRST!)

These rules appear in all docs because they're **non-negotiable**:

1. **CS_ID is VARCHAR, not INT**
   - "071" and "71" are DIFFERENT
   - Preserve leading zeros always

2. **Filter to PSU banks only**
   - Exclude private banks
   - `segment = 'PSU'` required

3. **Active engineers only**
   - `active_status = 'YES'`
   - `designation = 'Engineer'`

4. **Recalculate attendance status**
   - Before 10 AM → "OnTime"
   - After 10 AM → "Late"
   - NULL → "Absent"
   - Ignore original column!

5. **Service area = 1-to-1 with engineer**
   - One engineer per service area
   - One service area per engineer

6. **Ticket status is fixed vocabulary**
   - OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED
   - Invalid values → skip record

---

## 🚀 QUICK REFERENCE: KEY METRICS

These appear in the dashboard table:

| Metric | Calculation | Example | Unit |
|---|---|---|---|
| **Att. Days** | Count days with status = "OnTime" or "Late" | 20 | Days |
| **Working Days** | Count Mon-Fri in period (no weekends) | 22 | Days |
| **Att. %** | (Att. Days / Working Days) × 100 | 90.9% | % |
| **Prod Days** | Count days with ≥1 visit | 18 | Days |
| **Zero Prod Days** | Att. Days - Prod Days | 2 | Days |
| **Total Visits** | Count all visits in period | 145 | Count |
| **Distinct Sites** | Count unique sites visited | 45 | Count |
| **Repeat Rate** | Total Visits / Distinct Sites | 3.22x | Ratio |
| **Closed** | Count tickets with status = "CLOSED" | 12 | Count |
| **Open** | Count tickets with status = "OPEN" | 5 | Count |
| **Pending** | Count tickets with status IN ("PENDING", "SENTBACK") | 8 | Count |
| **Completed** | Count tickets with status = "COMPLETED" | 2 | Count |
| **Offline Sites** | Count offline sites > 3 days in engineer's service area | 15 | Count |

---

## 📁 FILE UPLOAD STRUCTURE

Users upload these daily:

| File | Sheet | Filter | Store | Frequency |
|---|---|---|---|---|
| B2B_Offline_DD-MM-YYYY.xlsx | B2B | segment = 'PSU' | APPEND | Daily |
| view_ticket.xlsx | (default) | assigned_type = 'Engineer' | FULL REPLACE | Daily |
| Attendance_Data.xlsx | (default) | - | APPEND | Daily |
| visit_data.xlsx | (default) | - | APPEND | Daily |
| EmployeeMaster.xlsx | (default) | active_status='YES' + designation='Engineer' | UPSERT | As-needed |
| customer_site_mst.csv | - | - | UPSERT | As-needed |

---

## 🧪 VALIDATION CHECKLIST

Before going live with Claude Code, verify:

### Database
- [ ] All 8 tables created
- [ ] All columns have correct data types
- [ ] All indexes created
- [ ] Foreign keys linked correctly
- [ ] Sample data loaded (50+ engineers, 1000+ offline sites)
- [ ] No NULL values in critical columns
- [ ] CS_ID stored as VARCHAR (leading zeros preserved)

### Backend
- [ ] All endpoints return correct JSON
- [ ] Filters work (state, date range, service area)
- [ ] Calculations correct (spot-check 1 engineer)
- [ ] ETL pipeline processes uploads
- [ ] Error handling in place
- [ ] API responses < 2 seconds
- [ ] Caching working (if implemented)

### Frontend
- [ ] All components render
- [ ] Filters update data
- [ ] Chart displays without errors
- [ ] Table shows all 18 columns
- [ ] Sorting/pagination work
- [ ] Export buttons functional
- [ ] No console errors
- [ ] Responsive design (mobile/tablet/desktop)

### Integration
- [ ] Frontend calls backend APIs
- [ ] Data flows end-to-end
- [ ] Docker Compose works
- [ ] No cross-origin errors

### Performance
- [ ] Page load < 3 seconds
- [ ] API response < 2 seconds
- [ ] Chart render < 500ms
- [ ] Table render < 1 second
- [ ] DB indexes present
- [ ] Memory stable (no leaks)

---

## 💡 TIPS FOR SUCCESS

1. **Read in order:** QUICK_START → DATABASE_LOGIC → DASHBOARD_SPEC → IMPLEMENTATION
2. **Don't skip database:** Many problems come from wrong schema
3. **Test calculations:** Spot-check at least 1 engineer's metrics
4. **Use sample data:** Load test data before real uploads
5. **Phase by phase:** Finish Phase 1 before Phase 2
6. **Ask Claude when unclear:** These docs can't cover everything

---

## ❓ COMMON QUESTIONS

**Q: Should I apply active_status filter?**  
A: Not yet. DATABASE_LOGIC.md says "DO NOT FILTER YET". Only filter on `active_status = 'YES'` in the engineer_master query.

**Q: What if CS_ID is NULL?**  
A: Skip that record. It's a critical field.

**Q: Should I track historical tickets?**  
A: No. Just store latest dump (full replace daily). Only offline_data should be historical.

**Q: How do I calculate working days?**  
A: Mon-Fri only in the date range. No holiday table yet, so just DAYOFWEEK NOT IN (1, 7).

**Q: Can an engineer have multiple service areas?**  
A: No. 1-to-1 mapping. One engineer = one service area = covers one geographic region.

---

## 📞 SUPPORT

If Claude Code asks questions or encounters issues:

1. **Data question:** Check DATABASE_LOGIC.md Section 1-3
2. **UI question:** Check DASHBOARD_SPECIFICATION.md Section 1-5
3. **Implementation question:** Check IMPLEMENTATION_GUIDE.md Phase-by-phase
4. **Calculation question:** Check DATABASE_LOGIC.md Section 5

If still unclear, ask Claude to flag the specific issue and you can clarify.

---

## 📈 NEXT STEPS

1. **Extract these 4 documents** to your project folder
2. **Read QUICK_START.md** (takes 10 min)
3. **Brief Claude Code** on Phase 1.1 using IMPLEMENTATION_GUIDE.md
4. **Wait** for Phase 1.1 completion
5. **Iterate** through Phase 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2

**Expected timeline:** 4-6 weeks for full build + testing

---

## 📝 VERSION

| Date | Version | Status |
|---|---|---|
| 2026-05-13 | 1.0 | Complete & Production-Ready |

---

## 🎓 WHAT YOU'LL HAVE AFTER BUILD

✅ PostgreSQL database (8 tables, 25,000+ site records, 300+ engineers)  
✅ FastAPI backend (7+ endpoints, ETL pipeline)  
✅ React dashboard (2 views, 4 filter types, export)  
✅ Docker deployment (one-command launch)  
✅ Fully functional system handling 250-296 engineers across 28 states  

---

**Ready? Start with QUICK_START.md → Brief Claude Code → Build! 🚀**
