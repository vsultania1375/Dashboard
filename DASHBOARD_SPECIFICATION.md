# VProtect Dashboard - UI/UX Specification & Requirements

**Version:** 1.0  
**Last Updated:** May 13, 2026  
**Purpose:** Complete specification for Field Service Management Intelligence Dashboard Views

---

## TABLE OF CONTENTS
1. [Dashboard Overview](#dashboard-overview)
2. [View 1: Offline Sites Distribution (Graph)](#view-1-offline-sites-distribution-graph)
3. [View 2: Engineer Performance Report (Table)](#view-2-engineer-performance-report-table)
4. [View 3: Supporting Calculations](#view-3-supporting-calculations)
5. [Filters & Date Range Selection](#filters--date-range-selection)
6. [Export Functionality](#export-functionality)
7. [UI/UX Design Guidelines](#uiux-design-guidelines)
8. [Performance Requirements](#performance-requirements)

---

## DASHBOARD OVERVIEW

### Purpose
Provide VProtect operations team with actionable insights into:
1. **Offline Infrastructure Health:** Identify high-risk sites offline for extended periods
2. **Engineer Productivity:** Track visit counts, distinct sites, attendance, and ticket status
3. **State-Level Performance:** Compare metrics across all 28 Indian states
4. **Data-Driven Decisions:** Support ticket assignment, resource allocation, and penalty avoidance

### Target Users
- **Ops Managers:** Monitor team performance across states
- **State Managers:** Track engineer activity within their state
- **Admin:** View PAN-India trends and data quality metrics

### Key Metrics (At-a-Glance)
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  Total Engineers │  Total Visits   │ Avg Repeat Rate │ Offline Sites   │
│      (State)    │    (Period)     │    (x visits)   │    (>3 days)    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## VIEW 1: OFFLINE SITES DISTRIBUTION (GRAPH)

### Purpose
Visualize the distribution of offline sites across aging buckets, filterable by state and date range.

### Graph Type
**Bar Chart** (Distribution of sites by offline bucket)

### Data Source
`offline_data` table (daily snapshots)

### Filters
1. **Date Range:** "From Date" → "To Date" (date pickers)
   - Default: Last 7 days
   - Min Range: 1 day, Max Range: 365 days
   - Format: DD-MM-YYYY

2. **State Filter:** Dropdown
   - Options: "All (PAN India)" + [State1, State2, ..., State28]
   - Default: "All (PAN India)"

3. **Bank Segment:** (Already pre-filtered to PSU only, optional display toggle)

### Graph Axes & Data

**X-Axis:** Offline Buckets (sorted by aging)
```
1-3 Days | 4-7 Days | 8-15 Days | 16-30 Days | 31-60 Days | 61-90 Days | 90+ Days
```

**Y-Axis:** Count of Sites (Number of offline sites)

**Data Calculation:**
```sql
SELECT
    offline_bucket,
    COUNT(DISTINCT cs_id) as site_count
FROM offline_data
WHERE data_date BETWEEN from_date AND to_date
  AND segment = 'PSU'
  AND (state = selected_state OR selected_state = 'All')
GROUP BY offline_bucket
ORDER BY FIELD(offline_bucket, '1-3 Days', '4-7 Days', '8-15 Days', 
                               '16-30 Days', '31-60 Days', '61-90 Days', '90+ Days')
```

### Chart Properties
- **Chart Type:** Vertical Bar Chart (Column Chart)
- **Color Scheme:**
  - 1-3 Days: Green (#22c55e) - Acceptable
  - 4-7 Days: Yellow (#eab308) - Monitor
  - 8-15 Days: Orange (#f97316) - Action needed
  - 16-30 Days: Red (#ef4444) - Critical
  - 31-60 Days: Dark Red (#dc2626) - Critical
  - 61-90 Days: Purple (#7c3aed) - Critical
  - 90+ Days: Black (#1f2937) - Critical
- **Hover Info:** Site count + percentage of total
- **Click Action:** Drill-down to site list (optional for v1)
- **Legend:** Show bucket labels with color code

### Example Output
```
Distribution of Offline Sites - Last 7 Days (Tamil Nadu)

  Count
    |
 800 |     ┌───┐
     |     │   │
 600 |     │   │     ┌───┐
     |     │   │     │   │
 400 |  ┌──┤   │  ┌──┤   │
     |  │  │   │  │  │   │
 200 |  │  │   │  │  │   │     ┌───┐
     |  │  │   │  │  │   │  ┌──┤   │
   0 |──┴──┴───┴──┴──┴───┴──┴──┴───┴──
       1-3  4-7  8-15 16-30 31-60 61-90 90+
       Days Days Days Days  Days  Days  Days
```

### Interactivity
- **Toggle:** Show/hide specific buckets (checkboxes)
- **Export:** Export chart as PNG/SVG
- **Zoom:** Hover to see exact values
- **Comparison:** Option to compare two date ranges side-by-side (v2 feature)

---

## VIEW 2: ENGINEER PERFORMANCE REPORT (TABLE)

### Purpose
Comprehensive tabular report of engineer performance metrics (attendance, productivity, tickets, offline sites).

### Data Source
Joins: `engineer_master`, `attendance_log`, `visit_log`, `view_ticket`, `offline_data`, `customer_site_master`

### Filters
1. **Date Range:** "From Date" → "To Date" (same as above)
2. **State Filter:** Dropdown (same as above)
   - Default: "All (PAN India)"
   - If State selected: Show only engineers in that state
3. **Service Area:** Optional multi-select (show after state selection)
4. **Show Active Only:** Toggle (default: ON)

### Table Columns (in order)

| # | Column Name | Data Type | Source | Formula/Logic | Units | Notes |
|---|---|---|---|---|---|---|
| 1 | **Service Area** | TEXT | engineer_master | service_area_code | - | Link to service_area_name in future |
| 2 | **Engineer Name** | TEXT | engineer_master | employee_name | - | Only if active_status = 'YES' |
| 3 | **Employee Code** | INT | engineer_master | employee_id | - | For reference |
| 4 | **Phone No** | TEXT | engineer_master | phone_no | - | Contact info |
| 5 | **State** | TEXT | engineer_master | service_state | - | Engineer's assigned state |
| 6 | **Att. Days** | INT | attendance_log | COUNT(DISTINCT attendance_date) WHERE attendance_status IN ('OnTime', 'Late') | Days | Days marked present |
| 7 | **Working Days** | INT | CALCULATED | COUNT(DISTINCT date) WHERE DAYOFWEEK(date) NOT IN (1,7) AND date BETWEEN from_date AND to_date | Days | Mon-Fri only (no holiday table yet) |
| 8 | **Att. %** | DECIMAL(5,2) | CALCULATED | (Att. Days / Working Days) * 100 | % | Attendance percentage |
| 9 | **Prod. Days** | INT | visit_log | COUNT(DISTINCT visit_date) | Days | Days with at least one visit |
| 10 | **Zero Prod Days** | INT | CALCULATED | Att. Days - Prod. Days | Days | Days present but no visit |
| 11 | **Total Visits** | INT | visit_log | COUNT(*) | Count | All visits in period |
| 12 | **Distinct Sites** | INT | visit_log + view_ticket | COUNT(DISTINCT oracle_site_no) | Count | Unique sites visited |
| 13 | **Repeat Rate (x)** | DECIMAL(5,2) | CALCULATED | Total Visits / Distinct Sites | x | Avg visits per site |
| 14 | **Closed** | INT | view_ticket | COUNT(*) WHERE ticket_status = 'CLOSED' AND employee_id = ? | Count | Current closed tickets |
| 15 | **Open** | INT | view_ticket | COUNT(*) WHERE ticket_status = 'OPEN' AND employee_id = ? | Count | Current open tickets |
| 16 | **Pending** | INT | view_ticket | COUNT(*) WHERE ticket_status IN ('PENDING', 'SENTBACK') AND employee_id = ? | Count | Current pending + sentback |
| 17 | **Completed** | INT | view_ticket | COUNT(*) WHERE ticket_status = 'COMPLETED' AND employee_id = ? | Count | Sent for approval |
| 18 | **Offline Sites (>3d)** | INT | offline_data + customer_site_master | COUNT(DISTINCT cs_id) WHERE service_area_code = eng.service_area_code AND aging_days > 3 AND segment = 'PSU' AND data_date = TODAY | Count | High-risk offline sites in area |

### Example Table
```
Service Area │ Engineer Name    │ Employee │ Phone      │ State  │ Att. │ Work │ Att │ Prod │ Zero │ Total │ Dist │ Repeat │ Closed │ Open │ Pend │ Comp │ Offline
             │                  │ Code     │            │        │ Days │ Days │  %  │ Days │ Prod │ Visits│ Sites│  Rate  │        │      │      │      │ Sites
─────────────┼──────────────────┼──────────┼────────────┼────────┼──────┼──────┼─────┼──────┼──────┼───────┼──────┼────────┼────────┼──────┼──────┼──────┼──────
KA-BNG-001  │ Rajesh Kumar     │ 1001     │ 98765-43210│ KA     │ 20   │ 22   │ 91% │ 18   │  2   │  145  │ 45   │ 3.22x  │ 12     │ 5    │ 8    │ 2    │ 15
KA-BNG-002  │ Priya Sharma     │ 1002     │ 98765-43211│ KA     │ 19   │ 22   │ 86% │ 15   │  4   │  98   │ 32   │ 3.06x  │ 8      │ 7    │ 12   │ 1    │ 22
MH-PUN-001  │ Amit Patel       │ 1003     │ 98765-43212│ MH     │ 21   │ 22   │ 95% │ 20   │  1   │ 167   │ 52   │ 3.21x  │ 15     │ 3    │ 5    │ 0    │ 8
TN-CHN-001  │ Vijay Reddy      │ 1004     │ 98765-43213│ TN     │ 18   │ 22   │ 82% │ 14   │  4   │  76   │ 28   │ 2.71x  │ 5      │ 11   │ 18   │ 4    │ 45
...
─────────────┴──────────────────┴──────────┴────────────┴────────┴──────┴──────┴─────┴──────┴──────┴───────┴──────┴────────┴────────┴──────┴──────┴──────┴──────
TOTAL (State) │ 127 engineers    │          │            │ PAN    │ 2540 │ 2794 │ 91% │ 2245 │ 295  │ 18547 │ 4123 │ 4.50x  │ 892    │ 456  │ 623  │ 89   │ 2156
AVERAGE       │ (per engineer)   │          │            │        │ 20   │ 22   │ 91% │ 18   │ 2.3  │ 146   │ 32   │ 3.21x  │ 7      │ 4    │ 5    │ 1    │ 17
```

### Row Level Actions
- **Click Engineer Name:** Drill-down to engineer detail page (v2)
  - Engineer's ticket list
  - Engineer's visit history
  - Engineer's attendance calendar
- **Color Coding (Conditional Formatting):**
  - Att. % < 80%: Red background
  - Zero Prod Days > 5: Red background
  - Offline Sites > 20: Orange background
  - Repeat Rate < 2.0x: Yellow background

### FOOTER SECTION: STATE/PAN-INDIA SUMMARY

**When State is selected:**
```
TOTAL (Selected State)
└─ Sum of all engineers' metrics for that state

AVERAGE (per Engineer in State)
└─ Totals / Count of engineers
```

**Calculation:**
```sql
-- For "Tamil Nadu" state selected:

SELECT
    'TOTAL' as row_label,
    COUNT(DISTINCT em.employee_id) as total_engineers,
    SUM(att_days) as total_att_days,
    SUM(working_days) as total_working_days,
    (SUM(att_days) / SUM(working_days)) * 100 as avg_att_percent,
    SUM(total_visits) as total_visits,
    SUM(distinct_sites) as total_distinct_sites,
    SUM(total_visits) / SUM(distinct_sites) as avg_repeat_rate,
    SUM(prod_days) as total_prod_days,
    SUM(closed_tickets) as total_closed,
    SUM(open_tickets) as total_open,
    SUM(pending_tickets) as total_pending,
    SUM(offline_sites) as total_offline
FROM engineer_master em
WHERE em.service_state = 'Tamil Nadu'
  AND em.active_status = 'YES'
```

**For PAN India (All selected):**
```
TOTAL (PAN India)
└─ 28 states aggregated
└─ 250-296 engineers

AVERAGE (per Engineer, PAN India)
└─ Total metrics / 250-296
```

### Key Insight Calculation (New Row - Optional v1)
```sql
-- VISITS_PER_ENGINEER_PER_DAY at state level
Per_Engineer_Per_Day_Visits = 
    SUM(Total_Visits) / (COUNT(Engineers) * Working_Days)

Example for Tamil Nadu:
- Total Visits (all engineers, period): 18,547
- Total Engineers (active): 127
- Working Days in period: 22
- Metric = 18,547 / (127 * 22) = 6.6 visits/engineer/day
```

### Sorting
- Default Sort: By Att. % (descending)
- User Can Sort By: Any column (ascending/descending)
- Multi-sort: Shift+Click to add secondary sort

### Pagination
- Rows per page: 25, 50, 100 (user selectable)
- Total rows: 25-296 (all active engineers in selected state/PAN India)
- Navigation: Previous, Next, Page indicator (Page 1 of 12)

---

## VIEW 3: SUPPORTING CALCULATIONS

### Calculation Engine Requirements

#### 3.1 Date Helpers
```python
# Python/JavaScript helper functions:

def get_working_days(from_date, to_date, holidays=[]):
    """
    Count Monday-Friday between dates (excluding Sundays, Saturdays, holidays)
    
    Args:
        from_date: DATE
        to_date: DATE
        holidays: List of DATE (future: holiday table)
    
    Returns: INT (working days count)
    """
    working_days = 0
    current = from_date
    while current <= to_date:
        if current.weekday() < 5:  # 0-4 = Mon-Fri
            if current not in holidays:
                working_days += 1
        current += timedelta(days=1)
    return working_days

def parse_datetime(dt_str, format_in="DD-MM-YYYY HH:MM"):
    """
    Parse various datetime formats to ISO format (YYYY-MM-DD HH:MM:SS)
    
    Supports:
    - "DD-MM-YYYY HH:MM"
    - "DD-MM-YYYY HH:MM AM/PM"
    - "DD_MM_YYYY HH:MM"
    """
    # Implementation with fallback parsing
    pass

def calculate_age(date_from, days_since=None):
    """
    Calculate aging in days
    
    Args:
        date_from: Start date
        days_since: Override (use if available directly)
    
    Returns: INT (days aged)
    """
    if days_since is not None:
        return days_since
    return (today() - date_from).days
```

#### 3.2 Metrics Calculation Cache
```python
# Cache engineer metrics at query time (or pre-compute nightly)

def calculate_engineer_metrics(employee_id, from_date, to_date):
    """
    Calculate ALL metrics for an engineer in a date range
    
    Returns: Dict with keys:
    {
        'att_days': INT,
        'working_days': INT,
        'att_percent': DECIMAL,
        'prod_days': INT,
        'zero_prod_days': INT,
        'total_visits': INT,
        'distinct_sites': INT,
        'repeat_rate': DECIMAL,
        'closed_tickets': INT,
        'open_tickets': INT,
        'pending_tickets': INT,
        'completed_tickets': INT,
        'offline_sites': INT
    }
    """
    # Multi-query aggregation
    pass

def calculate_state_summary(state, from_date, to_date):
    """
    Calculate aggregated metrics for all engineers in a state
    
    Returns: Dict
    {
        'total_engineers': INT,
        'total_att_days': INT,
        'total_working_days': INT,
        'avg_att_percent': DECIMAL,
        'total_visits': INT,
        'avg_repeat_rate': DECIMAL,
        'visits_per_engineer_per_day': DECIMAL,
        ...
    }
    """
    # Aggregation query
    pass
```

#### 3.3 Bucket Assignment
```python
# Assign offline sites to buckets based on aging

def assign_offline_bucket(aging_days):
    """
    Assign aging_days to bucket
    
    Args:
        aging_days: INT
    
    Returns: VARCHAR ("1-3 Days", "4-7 Days", etc.)
    """
    if aging_days <= 3:
        return "1-3 Days"
    elif aging_days <= 7:
        return "4-7 Days"
    elif aging_days <= 15:
        return "8-15 Days"
    elif aging_days <= 30:
        return "16-30 Days"
    elif aging_days <= 60:
        return "31-60 Days"
    elif aging_days <= 90:
        return "61-90 Days"
    else:
        return "90+ Days"
```

---

## FILTERS & DATE RANGE SELECTION

### Filter Panel (Top of Dashboard)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📊 VPROTECT FIELD SERVICE INTELLIGENCE DASHBOARD                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  From Date: [📅 DD-MM-YYYY ▼]    To Date: [📅 DD-MM-YYYY ▼]               │
│                                                                              │
│  State: [All (PAN India) ▼]  Service Area: [All ▼]  Show Active: [✓]       │
│                                                                              │
│  [🔄 Refresh]  [📥 Download Data]  [⚙️ Settings]                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Filter Specifications

#### 1. From Date & To Date
- **Control:** Date picker (calendar widget)
- **Format Display:** DD-MM-YYYY
- **Format Internal:** YYYY-MM-DD
- **Default Range:** Last 7 days
- **Min Range:** 1 day
- **Max Range:** 365 days
- **Validation:**
  - to_date must be >= from_date
  - Not future dates (max = today)
  - Show error if max range exceeded

#### 2. State Filter
- **Control:** Dropdown select
- **Default:** "All (PAN India)"
- **Options:**
  ```
  - All (PAN India)
  - Andhra Pradesh
  - Arunachal Pradesh
  - Assam
  - Bihar
  - Chhattisgarh
  - Goa
  - Gujarat
  - Haryana
  - Himachal Pradesh
  - Jharkhand
  - Karnataka
  - Kerala
  - Madhya Pradesh
  - Maharashtra
  - Manipur
  - Meghalaya
  - Mizoram
  - Nagaland
  - Odisha
  - Punjab
  - Rajasthan
  - Sikkim
  - Tamil Nadu
  - Telangana
  - Tripura
  - Uttar Pradesh
  - Uttarakhand
  - West Bengal
  ```
- **Action:** Filter both views (graph + table) by state
  - If state selected: Show only engineers in that state
  - If "All": Show PAN India data

#### 3. Service Area Filter (Optional)
- **Control:** Multi-select dropdown
- **Visibility:** Appears ONLY if a state is selected
- **Options:** Dynamically loaded based on selected state
- **Behavior:** Further filter engineers in that state by service area

#### 4. Show Active Only (Toggle)
- **Control:** Checkbox
- **Default:** Checked (ON)
- **Effect:**
  - ON: Show only active_status = 'YES' engineers
  - OFF: Show all engineers (including inactive)

#### 5. Refresh & Download
- **Refresh Button:** Re-query data, update charts/tables
  - Typically auto-refresh every 5 minutes
  - Manual refresh clears cache
- **Download Button:** Export current filtered data
  - See [Export Functionality](#export-functionality) below

### Filter Persistence
- Save filter state to browser localStorage
- Auto-restore on page reload
- Clear all filters: "Reset to Default" button

---

## EXPORT FUNCTIONALITY

### Export Options (via Download Button)

#### 1. Export as Excel (.xlsx)
**Format:** Engineer Performance Report table

- **File Name:** `VProtect_Engineer_Report_[State]_[FromDate]_[ToDate].xlsx`
  - Example: `VProtect_Engineer_Report_TamilNadu_2026-05-01_2026-05-13.xlsx`

- **Sheet 1: Summary**
  ```
  Dashboard Generated: 2026-05-13 14:30 IST
  Filters Applied:
    - Date Range: 2026-05-01 to 2026-05-13 (13 days)
    - State: Tamil Nadu
    - Active Engineers Only: Yes
  
  Key Metrics:
    - Total Engineers: 127
    - Total Visits: 18,547
    - Avg Repeat Rate: 3.21x
    - Offline Sites (>3 days): 2,156
  ```

- **Sheet 2: Engineer Details**
  ```
  Same columns as table view above
  All rows included (no pagination)
  Sorted by Att. % descending
  Footer rows:
    - TOTAL (State)
    - AVERAGE (per Engineer)
  ```

- **Sheet 3: Offline Sites Distribution**
  ```
  Offline Bucket │ Count │ % of Total
  ───────────────┼───────┼──────────
  1-3 Days       │ 450   │ 20.9%
  4-7 Days       │ 380   │ 17.6%
  ...
  ```

- **Formatting:**
  - Header row: Bold, light blue background (#E3F2FD)
  - Footer rows: Bold, light gray background (#F5F5F5)
  - Number columns: Right-aligned, 2 decimal places
  - Percentage columns: Format as percentage (%)
  - Currency: Not applicable
  - Freeze panes: Top row

#### 2. Export as CSV (.csv)
**Format:** Engineer Performance Report (CSV)

- **File Name:** `VProtect_Engineer_Report_[State]_[FromDate]_[ToDate].csv`
- **Delimiter:** Comma
- **Encoding:** UTF-8
- **Contents:** Same data as Excel Sheet 2 (Engineer Details)
- **Notes:** No formatting, plain text

#### 3. Export Chart as PNG
**Via:** Right-click on chart → "Download as PNG"

- **File Name:** `VProtect_Offline_Distribution_[State]_[FromDate]_[ToDate].png`
- **Resolution:** 1200x600 pixels
- **Format:** PNG with transparency

#### 4. Export Chart as SVG
**Via:** Right-click on chart → "Download as SVG"

- **File Name:** `VProtect_Offline_Distribution_[State]_[FromDate]_[ToDate].svg`
- **Format:** Scalable Vector Graphics
- **Use Case:** For reports, presentations, further editing

---

## UI/UX DESIGN GUIDELINES

### Layout & Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  HEADER: VProtect Dashboard Logo | User Name | Logout              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FILTER PANEL (Sticky)                                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ From: [📅] To: [📅] | State: [▼] | [🔄] [📥]              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  KEY METRICS (At-a-Glance)                                          │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐    │
│  │ Total        │ Total        │ Avg Repeat   │ Offline      │    │
│  │ Engineers    │ Visits       │ Rate         │ Sites (>3d)  │    │
│  │ [127]        │ [18,547]     │ [3.21x]      │ [2,156]      │    │
│  └──────────────┴──────────────┴──────────────┴──────────────┘    │
│                                                                      │
│  TAB 1: DISTRIBUTION                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  📊 Offline Sites Distribution by Bucket                   │   │
│  │  (Bar Chart)                                               │   │
│  │  ┌────────────────────────────────────────────────────┐    │   │
│  │  │                                                    │    │   │
│  │  │  [Chart renders here]                             │    │   │
│  │  │                                                    │    │   │
│  │  └────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  TAB 2: PERFORMANCE REPORT                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  📋 Engineer Performance Report                            │   │
│  │  ┌────────────────────────────────────────────────────┐    │   │
│  │  │ Service │ Name    │ Code │ Phone │ State │ Att │...│    │   │
│  │  │ Area    │         │      │       │       │ Days│   │    │   │
│  │  ├─────────┼─────────┼──────┼───────┼───────┼─────┼───┤    │   │
│  │  │ KA-...  │ Rajesh  │ 1001 │ 9876..│ KA    │ 20  │...│    │   │
│  │  │ KA-...  │ Priya   │ 1002 │ 9876..│ KA    │ 19  │...│    │   │
│  │  │ ...     │ ...     │ ...  │ ...   │ ...   │ ... │...│    │   │
│  │  ├─────────┴─────────┴──────┴───────┴───────┴─────┴───┤    │   │
│  │  │ TOTAL (Tamil Nadu): [127 engineers] | [Results...]   │    │   │
│  │  └────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  FOOTER: Data Last Refreshed: [time] | © VProtect 2026            │
└─────────────────────────────────────────────────────────────────────┘
```

### Color Palette

| Element | Color | Hex Code | Usage |
|---|---|---|---|
| Primary Brand | Blue | #1e40af | Buttons, headers, active states |
| Success | Green | #22c55e | Good metrics (Att. % > 90%), bucket 1-3 Days |
| Warning | Orange | #f97316 | Caution metrics, bucket 8-15 Days |
| Danger | Red | #ef4444 | Poor metrics, bucket 16+ Days |
| Neutral | Gray | #6b7280 | Text, borders, inactive states |
| Background | Light Gray | #f9fafb | Card backgrounds |
| Border | Light Gray | #e5e7eb | Dividers, table borders |
| Offline Buckets | (as specified in View 1) | - | Chart colors |

### Typography

| Element | Font | Size | Weight | Color |
|---|---|---|---|---|
| Page Title | Roboto | 32px | Bold (700) | #1f2937 |
| Section Title | Roboto | 20px | Bold (700) | #1f2937 |
| Column Header (Table) | Roboto | 14px | Bold (600) | #1f2937 |
| Body Text | Roboto | 14px | Regular (400) | #6b7280 |
| Metric Value | Roboto | 28px | Bold (700) | #1e40af |
| Metric Label | Roboto | 12px | Regular (400) | #9ca3af |

### Responsive Design

- **Desktop (1200px+):** Full layout as shown above
- **Tablet (768px-1199px):** Single column for filters, stacked metrics
- **Mobile (< 768px):** 
  - Filters collapsed into accordion
  - Chart: Horizontal scroll
  - Table: Horizontal scroll with sticky first column
  - Metrics: Vertical scroll

### Accessibility (A11y)

- **Color Contrast:** All text meets WCAG AA standard (4.5:1)
- **Keyboard Navigation:** Tab through all interactive elements
- **ARIA Labels:** All buttons, inputs, charts have descriptive labels
- **Screen Reader:** Table structure marked with proper th/td elements
- **Focus Indicators:** Clear blue outline on focus (2px solid #1e40af)

---

## PERFORMANCE REQUIREMENTS

### Page Load Time
- Initial page load: < 3 seconds (target)
- After filter change: < 1 second (via API cache)
- Chart render: < 500ms
- Table render: < 1 second

### Query Performance
- Offline distribution query: < 500ms (indexed on state, segment, data_date)
- Engineer performance query: < 2s per engineer
- State summary query: < 1s (cached)
- PAN India aggregation: < 3s (cached)

### Caching Strategy
- **In-Memory Cache:**
  - Engineer metrics: Cache for 1 hour
  - State summaries: Cache for 1 hour
  - Offline data summaries: Cache for 30 minutes
- **Browser Cache:**
  - Static assets (CSS, JS): 30 days
  - API responses: 5 minutes
- **Cache Invalidation:**
  - On data refresh (manual or scheduled)
  - On filter change (partial invalidation)

### Database Indexes (Required)

```sql
-- For offline distribution query
CREATE INDEX idx_offline_data_state_segment_date 
  ON offline_data(state, segment, data_date DESC);

-- For engineer performance aggregation
CREATE INDEX idx_visit_log_employee_visit_date 
  ON visit_log(employee_id, visit_date);

CREATE INDEX idx_attendance_log_employee_date 
  ON attendance_log(employee_id, attendance_date);

CREATE INDEX idx_view_ticket_employee_status 
  ON view_ticket(employee_id, ticket_status);

-- For offline sites in service area
CREATE INDEX idx_offline_data_cs_id_aging 
  ON offline_data(cs_id, aging_days DESC);

CREATE INDEX idx_customer_site_service_area 
  ON customer_site_master(service_area_code);
```

### API Response Format

#### Request (Filter Parameters)
```json
{
  "from_date": "2026-05-01",
  "to_date": "2026-05-13",
  "state": "Tamil Nadu",  // or "All" for PAN India
  "service_area": null,     // optional
  "show_active_only": true,
  "view": "performance"     // or "distribution"
}
```

#### Response (Engineer Performance)
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_engineers": 127,
      "date_range": "2026-05-01 to 2026-05-13",
      "state": "Tamil Nadu"
    },
    "engineers": [
      {
        "employee_id": 1001,
        "employee_name": "Rajesh Kumar",
        "service_area": "KA-BNG-001",
        "att_days": 20,
        "working_days": 22,
        "att_percent": 90.9,
        "prod_days": 18,
        "zero_prod_days": 2,
        "total_visits": 145,
        "distinct_sites": 45,
        "repeat_rate": 3.22,
        "closed": 12,
        "open": 5,
        "pending": 8,
        "completed": 2,
        "offline_sites": 15
      },
      // ... more engineers
    ],
    "footer": {
      "total_att_days": 2540,
      "total_working_days": 2794,
      "avg_att_percent": 90.9,
      "total_visits": 18547,
      "avg_repeat_rate": 4.50
    }
  },
  "cached": false,
  "generated_at": "2026-05-13T14:30:00Z"
}
```

#### Response (Offline Distribution)
```json
{
  "success": true,
  "data": {
    "summary": {
      "date_range": "2026-05-01 to 2026-05-13",
      "state": "Tamil Nadu",
      "total_offline_sites": 2156
    },
    "distribution": [
      { "bucket": "1-3 Days", "count": 450, "percent": 20.9 },
      { "bucket": "4-7 Days", "count": 380, "percent": 17.6 },
      { "bucket": "8-15 Days", "count": 285, "percent": 13.2 },
      { "bucket": "16-30 Days", "count": 340, "percent": 15.8 },
      { "bucket": "31-60 Days", "count": 420, "percent": 19.5 },
      { "bucket": "61-90 Days", "count": 140, "percent": 6.5 },
      { "bucket": "90+ Days", "count": 161, "percent": 7.5 }
    ]
  },
  "cached": true,
  "generated_at": "2026-05-13T14:30:00Z"
}
```

---

## VERSION HISTORY

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-05-13 | Initial complete UI/UX specification with all views, filters, exports, and performance requirements |

---

**END OF DOCUMENT**
