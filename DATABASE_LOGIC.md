# VProtect Dashboard - Database Logic & Schema Documentation

**Version:** 1.0  
**Last Updated:** May 13, 2026  
**Purpose:** Complete data model specification for Field Service Management Intelligence Dashboard

---

## TABLE OF CONTENTS
1. [Data Sources & File Mappings](#data-sources--file-mappings)
2. [Database Tables & Schema](#database-tables--schema)
3. [Data Relationships (Entity Relationships)](#data-relationships-entity-relationships)
4. [Data Transformation & ETL Rules](#data-transformation--etl-rules)
5. [Calculation & Business Logic](#calculation--business-logic)
6. [Daily Data Ingestion Process](#daily-data-ingestion-process)

---

## 1. DATA SOURCES & FILE MAPPINGS

### 1.1 **OFFLINE_DATA_DD_MM_YYYY.xlsx** → `offline_data`
**Update Frequency:** Daily  
**Processing:** Extract only **B2B Sheet**, filter for **PSU banks only**

| Column Name (Excel) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| alarm_date | alarm_date | DATE | Date when last alarm was received | Parse to YYYY-MM-DD |
| B2B Code | b2b_code | VARCHAR(255) | Bank name / Customer name | PSU filter here |
| descr | - | - | NO USE | Ignore |
| site_name | site_name | VARCHAR(255) | Name of the site | Key identifier |
| cs_no | cs_id | VARCHAR(20) | CS ID of the site (as STRING) | **IMPORTANT: Store as VARCHAR to preserve leading zeros (e.g., "071" ≠ 71)** |
| No. Of Days | aging_days | INT | Offline aging in days | Derived or direct |
| Bucket | offline_bucket | VARCHAR(50) | Aging bucket classification | Values: 1-3, 4-7, 8-15, 16-30, 31-60, 61-90, 90+ Days |
| Branch Code | branch_code | VARCHAR(255) | Format: "IB ATM_ID" | Indian Bank ATM ID |
| State | state | VARCHAR(50) | State of site | E.g., "Karnataka", "Tamil Nadu" |
| Offline Date & Time | offline_datetime | DATETIME | Last alert received | Format: DD-MM-YYYY HH:MM → Convert to YYYY-MM-DD HH:MM:SS |
| Zone | zone | VARCHAR(50) | Zone of state | Regional grouping |
| Segment | segment | VARCHAR(50) | PSU or PVT | **Filter: PSU only** |

**Key Rules:**
- **Filter Condition:** `segment = 'PSU'` (Private banks excluded)
- **Date Threshold:** Consider only sites with `aging_days >= 3` for insights
- **Historical Tracking:** Store each daily dump with date partition for trend analysis
- **CS_ID Format:** Always VARCHAR to preserve leading zeros

---

### 1.2 **view_ticket.xlsx** → `view_ticket`
**Update Frequency:** Daily (latest dump)  
**Purpose:** Current state of all tickets in Field Service Management (FSM) system

| Column Name (Excel) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| Ticket ID | ticket_id | VARCHAR(50) | Unique ticket identifier | Primary key |
| Oracle Site Name | oracle_site_name | VARCHAR(255) | Site name in FSM | Can match offline_data.site_name |
| Oracle Site No | oracle_site_no | INT / VARCHAR | Oracle primary key | Foreign key to customer_site_master |
| CS ID | cs_id | VARCHAR(20) | CS ID of site | Match with offline_data.cs_id (VARCHAR) |
| Primary Customer Name | customer_name | VARCHAR(255) | Full bank/customer name | FSM format (longer than B2B Code) |
| Customer Ticket No | - | - | NO USE | Ignore |
| ATM ID | atm_id | VARCHAR(50) | ATM ID for Indian Bank sites only | **Map:** "INDIAN BANK" tickets use this field |
| Service Area | service_area | VARCHAR(100) | Service area code/name | Links to engineer assignment |
| State Name | state | VARCHAR(50) | State of site | Match with offline_data.state |
| Ticket Status | ticket_status | VARCHAR(50) | Status of ticket | **Valid Values:** OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED |
| Ticket Status Reason | - | - | NO USE | Ignore |
| Aging Days | aging_days | INT | Ticket aging in days | Used for TAT (Turnaround Time) calculation |
| Total Visits | total_visits | INT | Number of engineer visits | Counter of engineer activities |
| Ticket Type | ticket_type | VARCHAR(50) | Issue type | **Valid Values:** Camera, Customer Complaint, False Alarm, Footage, Incident, Offline, PM Visit, RECORDING GAP, Re-Installation, System Issue |
| Ticket Sub-Type | ticket_subtype | VARCHAR(100) | Sub-category of issue | Optional detail field |
| Create Date | create_date | DATE | Ticket creation date | Format: DD-MM-YYYY → YYYY-MM-DD |
| Planned Date | planned_date | DATE | Last planned visit date | Latest date engineer scheduled |
| Ticket Assigned Type | assigned_type | VARCHAR(50) | "Vendor" or "Engineer" | **Focus:** Engineer tickets only for now |
| Ticket Assigned To | assigned_to | VARCHAR(255) | Engineer assignment | Format: "Engineer_Name (Engineer_EMP_ID)" → Parse both name & ID |
| Current Approver Name | approver_name | VARCHAR(255) | Approver in workflow | Tech support approval |
| Last Visit In Date-Time | last_visit_in | DATETIME | Last visit start time | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Last Visit Out Date-Time | last_visit_out | DATETIME | Last visit end time | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Last Submission Date Time | last_submission_datetime | DATETIME | Last submission time | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Ticket Closed Date & Time | ticket_closed_datetime | DATETIME | Closure timestamp | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Cancelled By Name | cancelled_by | VARCHAR(255) | Who cancelled | NULL if not cancelled |
| Cancelled Date-Time | cancelled_datetime | DATETIME | When cancelled | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |

**Key Rules:**
- **Latest Dump:** Overwrites previous day's data (not historical tracking per se, but stores current state)
- **Assigned Type Filter:** `assigned_type = 'Engineer'` (Vendor tickets ignored initially)
- **Active Tickets Definition:** `ticket_status IN ('OPEN', 'PENDING', 'SENTBACK', 'COMPLETED')`
- **Customer Name Mapping:** 
  - "State Bank Of India ATM" → "STATE BANK OF INDIA"
  - "Karela Gramin Bank ATM" → "KERALA GRAMIN BANK" or "KARNATAKA GRAMIN BANK"
  - "Indian Bank ATM" → "INDIAN BANK"
  - "Central Bank of India" → "CENTRAL BANK OF INDIA"
  - "Canara Bank ATM OPEX" or "Canara Bank ATM" → "CANARA BANK"
- **Parse Logic:** Extract `employee_name` and `employee_id` from `assigned_to` field using regex: `(.*?)\s*\((\d+)\)`

---

### 1.3 **customer_site_master.csv** → `customer_site_master`
**Update Frequency:** As-needed (reference data)  
**Purpose:** Master reference for all customer sites

| Column Name (CSV) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| customer_site_id | customer_site_id | INT | Unique identifier | Primary key |
| account_source_ref | account_source_ref | VARCHAR(100) | Source reference | Optional |
| bill_to_location | bill_to_location | VARCHAR(255) | Billing location | Optional |
| bill_to_site_number | bill_to_site_number | VARCHAR(50) | Billing site code | Optional |
| bill_to_site_use_id | bill_to_site_use_id | VARCHAR(50) | Billing use ID | Optional |
| business_type | business_type | VARCHAR(100) | Type of business | Optional |
| contact_email_id | contact_email_id | VARCHAR(255) | Contact email | Optional |
| contact_name | contact_name | VARCHAR(255) | Contact person | Optional |
| contact_phone_number | contact_phone_number | VARCHAR(20) | Contact phone | Optional |
| contract_code | contract_code | VARCHAR(50) | Contract identifier | Optional |
| cs_id | cs_id | VARCHAR(20) | CS ID | **MUST be VARCHAR to match offline_data.cs_id** |
| customer_id | customer_id | INT | Oracle customer ID | Optional |
| oracle_account_number | oracle_account_number | VARCHAR(50) | Account number | Optional |
| oracle_customer_name | oracle_customer_name | VARCHAR(255) | Full customer name | Can match view_ticket.customer_name |
| oracle_site_name | oracle_site_name | VARCHAR(255) | Site name | Matches view_ticket.oracle_site_name |
| oracle_site_number | oracle_site_number | INT / VARCHAR | **CRITICAL: Foreign Key for view_ticket.oracle_site_no** | Primary key in FSM |
| service_area_code | service_area_code | VARCHAR(50) | Service area code | **Maps to engineer via 1:1 relationship** |
| service_delivery_type | service_delivery_type | VARCHAR(100) | Delivery type | Optional |
| site_address1 | site_address1 | TEXT | Primary address | Optional |
| site_address2 | site_address2 | TEXT | Secondary address | Optional |
| site_address3 | site_address3 | TEXT | Tertiary address | Optional |
| site_city | site_city | VARCHAR(100) | City | Optional |
| site_end_date | site_end_date | DATE | Service end date | Optional, for active filtering in future |
| site_gst_number | site_gst_number | VARCHAR(50) | GST number | Optional |
| site_lat | site_lat | DECIMAL(10, 8) | Latitude | For future route planning AI |
| site_long | site_long | DECIMAL(10, 8) | Longitude | For future route planning AI |
| site_pin_code | site_pin_code | VARCHAR(10) | Postal code | Optional |
| site_source_ref | site_source_ref | VARCHAR(100) | Source reference | Optional |
| site_start_date | site_start_date | DATE | Service start date | Optional |
| site_use_code | site_use_code | VARCHAR(50) | Site use classification | Optional |
| state_code | state_code | VARCHAR(10) | State code | Optional |
| territory_code | territory_code | VARCHAR(50) | Territory | Optional |
| active_status | active_status | VARCHAR(10) | Active/Inactive flag | **DO NOT FILTER YET** |
| site_state_gst_code | site_state_gst_code | VARCHAR(50) | State GST code | Optional |
| create_by | create_by | VARCHAR(100) | Created by | Audit field |
| create_time | create_time | DATETIME | Creation timestamp | Audit field |
| update_by | update_by | VARCHAR(100) | Updated by | Audit field |
| update_time | update_time | DATETIME | Update timestamp | Audit field |

**Key Rules:**
- **CS_ID:** Always VARCHAR to preserve leading zeros
- **Oracle Site No:** Use this as primary join key with view_ticket
- **Service Area Code:** Maps to engineer_master via 1:1 relationship
- **No Filter Yet:** Don't apply active_status filter until explicitly asked

---

### 1.4 **EmployeeMaster.xlsx** → `engineer_master`
**Update Frequency:** As-needed (reference data)  
**Purpose:** Master list of all field engineers

| Column Name (Excel) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| Service Area Code | service_area_code | VARCHAR(50) | Service area code | **Unique per engineer (1:1 mapping with engineer)** |
| Employee Code | employee_id | INT / VARCHAR | Unique engineer ID | Primary key |
| Employee Name | employee_name | VARCHAR(255) | Engineer's full name | Used in assigned_to parsing |
| Company Name | company_name | VARCHAR(255) | Company name | Optional |
| Location | location | VARCHAR(255) | Location | Optional |
| Department | department | VARCHAR(100) | Department | Optional |
| Designation | designation | VARCHAR(100) | Job title | **Filter: "Engineer" only** |
| Region | region | VARCHAR(100) | Region | Optional |
| State | service_state | VARCHAR(50) | Service state | **Each engineer assigned to ONE state** |
| Service State | service_state_2 | VARCHAR(50) | Duplicate of above | Use one column consistently |
| City | city | VARCHAR(100) | City | Optional |
| Address | address | TEXT | Address | Optional |
| Pin Code | pin_code | VARCHAR(10) | Postal code | Optional |
| Date Of Joining | date_of_joining | DATE | Joining date | Used for seniority/experience calc |
| Email Id | email_id | VARCHAR(255) | Work email | Optional |
| Phone No | phone_no | VARCHAR(20) | Work phone | Optional |
| Reporting Manager 1-5 | reporting_manager_1 to 5 | VARCHAR(255) | Manager hierarchy | Optional |
| Substitute Engineer | substitute_engineer | VARCHAR(255) | Backup engineer | Optional |
| Asset Issue Date | asset_issue_date | DATE | When asset issued | Optional |
| Asset Type | asset_type | VARCHAR(100) | Type of asset | Optional |
| Serial No Asset Description | serial_no | VARCHAR(255) | Asset serial | Optional |
| Active Status | active_status | VARCHAR(10) | "YES" or "NO" | **Filter: active_status = 'YES' only** |
| Base Latitude | base_lat | DECIMAL(10, 8) | Engineer's base location lat | For route planning |
| Base Longitude | base_long | DECIMAL(10, 8) | Engineer's base location long | For route planning |
| Sick Leave | sick_leave | INT | Sick leave balance | Optional |
| Casual Leave | casual_leave | INT | Casual leave balance | Optional |
| Restricted Leave | restricted_leave | INT | Restricted leave balance | Optional |
| Create By | create_by | VARCHAR(100) | Created by | Audit field |
| Create Time | create_time | DATETIME | Creation timestamp | Audit field |
| Last Update By | last_update_by | VARCHAR(100) | Updated by | Audit field |
| Last Update Time | last_update_time | DATETIME | Update timestamp | Audit field |

**Key Rules:**
- **Active Filter:** `active_status = 'YES'` REQUIRED
- **Designation Filter:** `designation = 'Engineer'` REQUIRED
- **Service Area Code:** 1:1 mapping with each engineer (unique per engineer)
- **State Assignment:** Each engineer linked to single state (matches engineer's service_state with site's state)

---

### 1.5 **Visit_Data.xlsx** (Daily) → `visit_log`
**Update Frequency:** Daily (append-only log)  
**Purpose:** Track all site visits by engineers

| Column Name (Excel) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| visit_id | visit_id | INT / VARCHAR | Unique visit identifier | Primary key |
| create_by | create_by | VARCHAR(100) | Created by | Audit field |
| create_time | create_time | DATETIME | Creation timestamp | Audit field |
| update_by | update_by | VARCHAR(100) | Updated by | Audit field |
| update_time | update_time | DATETIME | Update timestamp | Audit field |
| distance_covered | distance_covered | DECIMAL(8, 2) | Distance in km | Optional |
| end_lat | end_lat | DECIMAL(10, 8) | End latitude | Location of site |
| end_long | end_long | DECIMAL(10, 8) | End longitude | Location of site |
| engineer_code | employee_id | INT / VARCHAR | Engineer ID | Links to engineer_master |
| is_claimed | is_claimed | VARCHAR(10) | Claimed/Not claimed | Optional |
| start_lat | start_lat | DECIMAL(10, 8) | Start latitude | Optional |
| start_long | start_long | DECIMAL(10, 8) | Start longitude | Optional |
| ticket_no | ticket_id | VARCHAR(50) | Ticket ID | Links to view_ticket |
| visit_date | visit_date | DATE | Date of visit | Format: DD_MM_YYYY → YYYY-MM-DD |
| visit_in_time | visit_in_time | DATETIME | Visit start time | Format: DD_MM_YYYY HH:MM → YYYY-MM-DD HH:MM:SS |
| visit_number | visit_number | INT | Visit counter on ticket | 1st visit, 2nd visit, etc. |
| visit_out_time | visit_out_time | DATETIME | Visit end time | **IGNORE FOR NOW** (not used in analysis) |

**Key Rules:**
- **Append-Only:** New visits added daily, never delete/update
- **Visit Number:** Counter for each visit on a specific ticket
- **Period Analysis:** Aggregate visits for specific date ranges only
- **Visit Out Time:** Ignore this field for current analysis phase

---

### 1.6 **Attendance_Data.xlsx** (Daily) → `attendance_log`
**Update Frequency:** Daily  
**Purpose:** Track engineer attendance and first/last site visited

| Column Name (Excel) | Database Name | Data Type | Description | Notes |
|---|---|---|---|---|
| Employee Name | employee_name | VARCHAR(255) | Engineer name | Links to engineer_master |
| Employee Code | employee_id | INT / VARCHAR | Engineer ID | Links to engineer_master |
| Service State | service_state | VARCHAR(50) | Engineer's state | Should match engineer_master.service_state |
| Attendance Date | attendance_date | DATE | Date of attendance | Format: DD-MM-YYYY → YYYY-MM-DD |
| Attendance Status | attendance_status | VARCHAR(50) | Original status field | **DO NOT USE** - Recalculate instead |
| Attendance Month | attendance_month | VARCHAR(20) | Month reference | E.g., "May 2026" |
| In Date Time | in_datetime | DATETIME | Clock-in timestamp | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Out Date Time | out_datetime | DATETIME | Clock-out timestamp | Format: DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS |
| Outstation | outstation_flag | VARCHAR(10) | Outstation flag | Optional |
| Is Regularized | is_regularized | VARCHAR(10) | Regularization flag | Optional |
| Working Hours | working_hours | DECIMAL(5, 2) | Hours worked | Optional |
| Start Latitude | start_lat | DECIMAL(10, 8) | Start location lat | Optional |
| Start Longitude | start_long | DECIMAL(10, 8) | Start location long | Optional |
| End Latitude | end_lat | DECIMAL(10, 8) | End location lat | Optional |
| End Longitude | end_long | DECIMAL(10, 8) | End location long | Optional |
| First Visit CS ID | first_visit_cs_id | VARCHAR(20) | First site CS ID | Links to customer_site_master.cs_id |
| First Visit Ticket ID | first_visit_ticket_id | VARCHAR(50) | First ticket visited | Links to view_ticket.ticket_id |
| Last Visit CS ID | last_visit_cs_id | VARCHAR(20) | Last site CS ID | For route verification |
| Last Visit Ticket ID | last_visit_ticket_id | VARCHAR(50) | Last ticket visited | For route verification |

**Recalculation Rules:**
```
NEW attendance_status = CASE
  WHEN in_datetime IS NULL THEN 'Absent'
  WHEN HOUR(in_datetime) < 10 THEN 'OnTime'
  ELSE 'Late'
END
```

**Key Rules:**
- **Ignore Original Status:** Recalculate based on in_datetime logic
- **Append-Only:** New attendance records daily
- **Future Use:** Will validate if first visit matches engineer's assigned route (geographic verification)

---

## 2. DATABASE TABLES & SCHEMA

### Table Creation SQL (PostgreSQL)

```sql
-- 1. OFFLINE DATA (Partitioned by date for fast queries)
CREATE TABLE offline_data (
    offline_data_id SERIAL PRIMARY KEY,
    data_date DATE NOT NULL,  -- Partition column (YYYY-MM-DD of data load)
    alarm_date DATE,
    b2b_code VARCHAR(255),
    site_name VARCHAR(255) NOT NULL,
    cs_id VARCHAR(20) NOT NULL,  -- VARCHAR to preserve leading zeros
    aging_days INT,
    offline_bucket VARCHAR(50),  -- "1-3 Days", "4-7 Days", etc.
    branch_code VARCHAR(255),
    state VARCHAR(50),
    offline_datetime DATETIME,
    zone VARCHAR(50),
    segment VARCHAR(50),  -- Filter: 'PSU' only
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cs_id (cs_id),
    INDEX idx_data_date (data_date),
    INDEX idx_state (state),
    INDEX idx_segment (segment)
) PARTITION BY RANGE (YEAR(data_date));  -- Partition by year for large data

-- 2. VIEW TICKET (Latest state of tickets)
CREATE TABLE view_ticket (
    ticket_id VARCHAR(50) PRIMARY KEY,
    oracle_site_no INT,  -- FK to customer_site_master
    oracle_site_name VARCHAR(255),
    cs_id VARCHAR(20),  -- FK to offline_data/customer_site_master
    customer_name VARCHAR(255),
    atm_id VARCHAR(50),
    service_area VARCHAR(100),
    state VARCHAR(50),
    ticket_status VARCHAR(50),  -- OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED
    aging_days INT,
    total_visits INT,
    ticket_type VARCHAR(50),  -- Camera, Offline, Incident, etc.
    ticket_subtype VARCHAR(100),
    create_date DATE,
    planned_date DATE,
    assigned_type VARCHAR(50),  -- "Engineer" or "Vendor"
    assigned_to VARCHAR(255),  -- "Engineer_Name (Employee_ID)"
    employee_id INT,  -- Extracted from assigned_to
    employee_name VARCHAR(255),  -- Extracted from assigned_to
    approver_name VARCHAR(255),
    last_visit_in DATETIME,
    last_visit_out DATETIME,
    last_submission_datetime DATETIME,
    ticket_closed_datetime DATETIME,
    cancelled_by VARCHAR(255),
    cancelled_datetime DATETIME,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cs_id (cs_id),
    INDEX idx_oracle_site_no (oracle_site_no),
    INDEX idx_employee_id (employee_id),
    INDEX idx_ticket_status (ticket_status),
    INDEX idx_state (state),
    FOREIGN KEY (oracle_site_no) REFERENCES customer_site_master(oracle_site_number)
);

-- 3. CUSTOMER SITE MASTER
CREATE TABLE customer_site_master (
    customer_site_id INT PRIMARY KEY,
    oracle_site_number INT UNIQUE NOT NULL,  -- FK in view_ticket
    cs_id VARCHAR(20),  -- VARCHAR to preserve leading zeros
    oracle_customer_name VARCHAR(255),
    oracle_site_name VARCHAR(255),
    service_area_code VARCHAR(50),  -- 1:1 with engineer_master
    site_lat DECIMAL(10, 8),
    site_long DECIMAL(10, 8),
    site_address1 TEXT,
    site_city VARCHAR(100),
    site_state VARCHAR(50),
    site_pin_code VARCHAR(10),
    site_start_date DATE,
    site_end_date DATE,
    active_status VARCHAR(10),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_cs_id (cs_id),
    INDEX idx_oracle_site_number (oracle_site_number),
    INDEX idx_service_area_code (service_area_code),
    INDEX idx_site_state (site_state)
);

-- 4. ENGINEER MASTER
CREATE TABLE engineer_master (
    employee_id INT PRIMARY KEY,
    employee_name VARCHAR(255) NOT NULL,
    service_area_code VARCHAR(50) UNIQUE NOT NULL,  -- 1:1 mapping
    service_state VARCHAR(50),  -- Each engineer assigned to ONE state
    active_status VARCHAR(10),  -- Filter: 'YES' only
    designation VARCHAR(100),  -- Filter: 'Engineer' only
    date_of_joining DATE,
    phone_no VARCHAR(20),
    email_id VARCHAR(255),
    base_lat DECIMAL(10, 8),
    base_long DECIMAL(10, 8),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_service_area_code (service_area_code),
    INDEX idx_service_state (service_state),
    INDEX idx_active_status (active_status),
    UNIQUE KEY unique_active_engineer (employee_id, active_status)
);

-- 5. VISIT LOG (Append-only, immutable)
CREATE TABLE visit_log (
    visit_id INT / VARCHAR PRIMARY KEY,
    employee_id INT,  -- FK to engineer_master
    ticket_id VARCHAR(50),  -- FK to view_ticket
    visit_date DATE,
    visit_in_time DATETIME,
    visit_number INT,
    distance_covered DECIMAL(8, 2),
    end_lat DECIMAL(10, 8),
    end_long DECIMAL(10, 8),
    is_claimed VARCHAR(10),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_employee_id (employee_id),
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_visit_date (visit_date),
    FOREIGN KEY (employee_id) REFERENCES engineer_master(employee_id),
    FOREIGN KEY (ticket_id) REFERENCES view_ticket(ticket_id)
);

-- 6. ATTENDANCE LOG (Append-only daily)
CREATE TABLE attendance_log (
    attendance_id SERIAL PRIMARY KEY,
    employee_id INT,  -- FK to engineer_master
    attendance_date DATE NOT NULL,
    in_datetime DATETIME,
    out_datetime DATETIME,
    attendance_status VARCHAR(50),  -- RECALCULATED: Absent, OnTime, Late
    working_hours DECIMAL(5, 2),
    first_visit_cs_id VARCHAR(20),
    first_visit_ticket_id VARCHAR(50),
    last_visit_cs_id VARCHAR(20),
    last_visit_ticket_id VARCHAR(50),
    created_at TIMESTAMP,
    INDEX idx_employee_id (employee_id),
    INDEX idx_attendance_date (attendance_date),
    FOREIGN KEY (employee_id) REFERENCES engineer_master(employee_id)
);

-- 7. SERVICE AREA MASTER (Reference)
CREATE TABLE service_area_master (
    service_area_code VARCHAR(50) PRIMARY KEY,
    service_area_name VARCHAR(255),
    state VARCHAR(50),
    zone VARCHAR(50),
    created_at TIMESTAMP
);

-- 8. DAILY OFFLINE SITES SUMMARY (Materialized View for Performance)
CREATE TABLE offline_sites_summary (
    summary_date DATE NOT NULL,
    cs_id VARCHAR(20),
    site_name VARCHAR(255),
    service_area_code VARCHAR(50),
    service_state VARCHAR(50),
    offline_days INT,
    offline_bucket VARCHAR(50),
    is_psu BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (summary_date, cs_id),
    INDEX idx_service_area (service_area_code),
    INDEX idx_state (service_state),
    INDEX idx_offline_days (offline_days)
);
```

---

## 3. DATA RELATIONSHIPS (Entity Relationships)

### ER Diagram (Text Format)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA RELATIONSHIPS                           │
└─────────────────────────────────────────────────────────────────────┘

engineer_master
    │
    ├─→ (1:1) ─→ service_area_code → customer_site_master
    │
    ├─→ (1:M) ─→ employee_id → view_ticket (assigned_to)
    │
    ├─→ (1:M) ─→ employee_id → visit_log
    │
    └─→ (1:M) ─→ employee_id → attendance_log


customer_site_master
    │
    ├─→ (1:1) ─→ oracle_site_number → view_ticket
    │
    ├─→ (M:1) ─→ service_area_code → engineer_master
    │
    ├─→ (1:M) ─→ cs_id → offline_data
    │
    └─→ (1:M) ─→ cs_id → offline_sites_summary


view_ticket
    │
    ├─← (1:1) ← oracle_site_no ← customer_site_master
    │
    ├─← (M:1) ← employee_id ← engineer_master
    │
    └─→ (1:M) ─→ ticket_id → visit_log


offline_data
    │
    ├─→ (M:1) ─→ cs_id → customer_site_master
    │
    └─→ (M:1) ─→ state → service_area_master


visit_log (append-only)
    │
    ├─← (M:1) ← employee_id ← engineer_master
    │
    └─← (M:1) ← ticket_id ← view_ticket


attendance_log (append-only)
    │
    └─← (M:1) ← employee_id ← engineer_master
```

### Key Join Conditions

| Join | Condition | Notes |
|---|---|---|
| engineer → service area | `engineer_master.service_area_code = customer_site_master.service_area_code` | 1:1 mapping |
| engineer → sites in state | `engineer_master.service_state = customer_site_master.site_state` | Filters sites by engineer's state |
| site master → tickets | `customer_site_master.oracle_site_number = view_ticket.oracle_site_no` | Primary join |
| offline data → sites | `offline_data.cs_id = customer_site_master.cs_id` | Match offline sites to master |
| ticket → visits | `view_ticket.ticket_id = visit_log.ticket_id` | Track visits per ticket |
| ticket → engineer | `view_ticket.employee_id = engineer_master.employee_id` | Ticket assignment |

---

## 4. DATA TRANSFORMATION & ETL RULES

### 4.1 Offline Data ETL

**Input:** B2B_Offline_DD-MM-YYYY.xlsx (B2B Sheet)  
**Output:** offline_data table

```yaml
Transformation Steps:
  1. Load Sheet:
     - Sheet Name: "B2B"
  
  2. Filter:
     - Condition: segment == "PSU"
     - Remove: All non-PSU records
  
  3. Data Type Conversion:
     - alarm_date: Text → DATE (DD-MM-YYYY → YYYY-MM-DD)
     - cs_id: Preserve as VARCHAR(20) (DON'T convert to INT)
     - aging_days: INT
     - offline_datetime: TEXT → DATETIME (DD-MM-YYYY HH:MM → YYYY-MM-DD HH:MM:SS)
  
  4. New Columns (Derived):
     - data_date: TODAY's date (partition column)
  
  5. Insert:
     - Mode: APPEND to offline_data table
     - Partition: By data_date (YYYY-MM-DD)
  
  6. Quality Checks:
     - No NULL in: site_name, cs_id, state, segment
     - aging_days >= 0
```

### 4.2 View Ticket ETL

**Input:** view_ticket.xlsx  
**Output:** view_ticket table

```yaml
Transformation Steps:
  1. Load Sheet:
     - Sheet Name: "Sheet1" (or default)
  
  2. Filter:
     - Condition: assigned_type == "Engineer"
     - Remove: Vendor tickets
  
  3. Data Type Conversion:
     - ticket_status: Text → VARCHAR(50)
     - ticket_type: Text → VARCHAR(50)
     - last_visit_in: Text → DATETIME (DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS)
     - last_visit_out: Text → DATETIME
     - last_submission_datetime: Text → DATETIME
     - ticket_closed_datetime: Text → DATETIME
     - cancelled_datetime: Text → DATETIME
  
  4. Column Parsing:
     - assigned_to: "Engineer_Name (Employee_ID)"
       ├─ Extract: employee_name = Substring before "("
       └─ Extract: employee_id = Substring inside "()" as INT
  
  5. Data Validation:
     - ticket_status must be in: OPEN, PENDING, SENTBACK, COMPLETED, CLOSED, CANCELLED, REJECTED
     - ticket_type must be in valid list (see schema above)
  
  6. Update Strategy:
     - Mode: FULL REPLACE (overwrite previous day's data)
     - Reason: Latest dump of current ticket status
  
  7. Quality Checks:
     - No NULL in: ticket_id, ticket_status
     - oracle_site_no matches customer_site_master.oracle_site_number
```

### 4.3 Engineer Master ETL

**Input:** EmployeeMaster.xlsx  
**Output:** engineer_master table

```yaml
Transformation Steps:
  1. Load Sheet:
     - Sheet Name: "Sheet1"
  
  2. Filter:
     - Condition 1: active_status == "YES"
     - Condition 2: designation == "Engineer"
     - Remove: Inactive / Non-Engineer records
  
  3. Data Type Conversion:
     - employee_id: INT (primary key)
     - date_of_joining: Text → DATE (DD-MM-YYYY → YYYY-MM-DD)
     - base_lat, base_long: DECIMAL(10, 8)
  
  4. Column Mapping:
     - service_state = State OR Service State (use whichever is populated)
  
  5. Unique Constraint:
     - service_area_code must be UNIQUE (1:1 with engineer)
  
  6. Update Strategy:
     - Mode: UPSERT (merge)
     - ON DUPLICATE KEY UPDATE: updated_at, phone_no, email_id, service_area_code
  
  7. Quality Checks:
     - No NULL in: employee_id, employee_name, service_area_code, service_state
     - employee_id is unique
     - service_area_code is unique
```

### 4.4 Customer Site Master ETL

**Input:** customer_site_mst.csv  
**Output:** customer_site_master table

```yaml
Transformation Steps:
  1. Load Format:
     - File Type: CSV
  
  2. No Filter:
     - Load all records initially
     - active_status filtering comes LATER in queries
  
  3. Data Type Conversion:
     - oracle_site_number: INT (from oracle_site_no)
     - cs_id: VARCHAR(20) (preserve leading zeros)
     - site_lat, site_long: DECIMAL(10, 8)
     - site_start_date, site_end_date: DATE
  
  4. Update Strategy:
     - Mode: UPSERT
     - Key: customer_site_id OR oracle_site_number
     - ON DUPLICATE: UPDATE all columns except primary key
  
  5. Quality Checks:
     - No NULL in: customer_site_id, oracle_site_number
     - oracle_site_number is unique
     - service_area_code NOT NULL (will be NULL initially, flag for review)
```

### 4.5 Visit Log ETL

**Input:** visit_data.xlsx (Daily)  
**Output:** visit_log table

```yaml
Transformation Steps:
  1. Load Sheet:
     - Sheet Name: "Sheet1"
  
  2. No Filter:
     - Load all visits
  
  3. Data Type Conversion:
     - visit_date: Text → DATE (DD_MM_YYYY → YYYY-MM-DD)
     - visit_in_time: Text → DATETIME (DD_MM_YYYY HH:MM → YYYY-MM-DD HH:MM:SS)
     - visit_out_time: Text → DATETIME (IGNORE in analysis)
     - engineer_code: INT (rename to employee_id)
     - ticket_no: VARCHAR(50) (rename to ticket_id)
  
  4. Insert Strategy:
     - Mode: APPEND (append-only log, never update)
     - Check: visit_id not already in table (prevent duplicates)
  
  5. FK Validation:
     - employee_id must exist in engineer_master
     - ticket_id must exist in view_ticket
  
  6. Quality Checks:
     - No NULL in: visit_id, employee_id, ticket_id, visit_date
     - visit_number >= 1
```

### 4.6 Attendance Log ETL

**Input:** Attendance_Data.xlsx (Daily)  
**Output:** attendance_log table

```yaml
Transformation Steps:
  1. Load Sheet:
     - Sheet Name: "Sheet1"
  
  2. No Filter:
     - Load all attendance records
  
  3. Data Type Conversion:
     - attendance_date: Text → DATE (DD-MM-YYYY → YYYY-MM-DD)
     - in_datetime: Text → DATETIME (DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS)
     - out_datetime: Text → DATETIME (DD-MM-YYYY HH:MM AM/PM → YYYY-MM-DD HH:MM:SS)
     - employee_code: INT (rename to employee_id)
  
  4. Recalculate Status:
     ```
     NEW attendance_status = CASE
       WHEN in_datetime IS NULL THEN 'Absent'
       WHEN HOUR(in_datetime) < 10 THEN 'OnTime'
       ELSE 'Late'
     END
     ```
     ├─ IGNORE the original "Attendance Status" column
     └─ Always recalculate from in_datetime
  
  5. Insert Strategy:
     - Mode: APPEND (daily append-only log)
     - Uniqueness: (employee_id, attendance_date) should be UNIQUE
  
  6. FK Validation:
     - employee_id must exist in engineer_master
  
  7. Quality Checks:
     - No NULL in: employee_id, attendance_date
     - attendance_date is reasonable (not future dates)
```

---

## 5. CALCULATION & BUSINESS LOGIC

### 5.1 Engineer Performance Metrics

**For a given Period (from_date, to_date) and Engineer (employee_id):**

#### Attendance Calculations

```sql
-- Attendance Days (actual days marked)
Att_Days = COUNT(DISTINCT attendance_date) 
  FROM attendance_log 
  WHERE employee_id = ? 
    AND attendance_date BETWEEN from_date AND to_date
    AND attendance_status IN ('OnTime', 'Late')  -- Exclude Absent

-- Working Days (Monday-Friday, excluding holidays)
-- NOTE: No holidays table provided yet, implement simple Mon-Fri logic
Working_Days = COUNT(DISTINCT attendance_date) 
  FROM (SELECT ? as date UNION ...) dates
  WHERE DAYOFWEEK(date) NOT IN (1, 7)  -- 1=Sunday, 7=Saturday
    AND date BETWEEN from_date AND to_date
  -- FUTURE: Add holiday table for more accuracy

-- Attendance % = (Att_Days / Working_Days) * 100
Attendance_Percent = (Att_Days / NULLIF(Working_Days, 0)) * 100

-- Zero Productivity Days = Att_Days - Prod_Days (see below)
```

#### Productivity Calculations

```sql
-- Productive Days (days with at least one visit)
Prod_Days = COUNT(DISTINCT visit_date) 
  FROM visit_log 
  WHERE employee_id = ?
    AND visit_date BETWEEN from_date AND to_date

-- Total Visits
Total_Visits = COUNT(*) 
  FROM visit_log 
  WHERE employee_id = ?
    AND visit_date BETWEEN from_date AND to_date

-- Distinct Sites Visited
Distinct_Sites = COUNT(DISTINCT ticket_id)  -- via ticket→site relationship
  FROM visit_log vl
  JOIN view_ticket vt ON vl.ticket_id = vt.ticket_id
  WHERE vl.employee_id = ?
    AND vl.visit_date BETWEEN from_date AND to_date

-- Repeat Rate (x) = Total_Visits / Distinct_Sites
Repeat_Rate = Total_Visits / NULLIF(Distinct_Sites, 0)

-- Zero Productivity Days = Att_Days - Prod_Days
Zero_Prod_Days = Att_Days - Prod_Days
```

#### Ticket Status Metrics

```sql
-- Closed Tickets (engineer's tickets with status CLOSED)
Closed_Tickets = COUNT(*) 
  FROM view_ticket 
  WHERE employee_id = ?
    AND ticket_status = 'CLOSED'

-- Open Tickets
Open_Tickets = COUNT(*) 
  FROM view_ticket 
  WHERE employee_id = ?
    AND ticket_status = 'OPEN'

-- Pending Tickets (includes SENTBACK)
Pending_Tickets = COUNT(*) 
  FROM view_ticket 
  WHERE employee_id = ?
    AND ticket_status IN ('PENDING', 'SENTBACK')

-- Completed Tickets (sent for approval)
Completed_Tickets = COUNT(*) 
  FROM view_ticket 
  WHERE employee_id = ?
    AND ticket_status = 'COMPLETED'

-- Total Active Tickets = OPEN + PENDING + SENTBACK + COMPLETED
Active_Tickets = Open_Tickets + Pending_Tickets + Completed_Tickets
```

#### Offline Sites Calculation

```sql
-- Offline Sites in Engineer's Service Area > 3 Days
Offline_Sites_Count = COUNT(DISTINCT cs_id)
  FROM offline_data od
  JOIN customer_site_master csm ON od.cs_id = csm.cs_id
  WHERE csm.service_area_code = engineer_master.service_area_code
    AND od.aging_days > 3
    AND od.segment = 'PSU'
    AND od.data_date = CURRENT_DATE  -- Today's offline data
    AND od.state = engineer_master.service_state
```

### 5.2 Team/State Level Aggregations

**For a State and Period (from_date, to_date):**

```sql
-- Total Engineers in State (active)
Total_Engineers = COUNT(DISTINCT employee_id)
  FROM engineer_master
  WHERE service_state = ?
    AND active_status = 'YES'

-- Total Visits in State (period)
Total_Visits_State = SUM(Total_Visits per engineer)
  = COUNT(*) FROM visit_log vl
  WHERE vl.visit_date BETWEEN from_date AND to_date
    AND vl.employee_id IN (
      SELECT employee_id FROM engineer_master
      WHERE service_state = ?
    )

-- Visits per Engineer per Working Day
Visits_Per_Engineer_Per_Day = Total_Visits_State / (Total_Engineers * Working_Days)

-- Average Repeat Rate (x) = SUM(Total_Visits) / SUM(Distinct_Sites)
Avg_Repeat_Rate = Total_Visits_State / Total_Distinct_Sites_State
```

### 5.3 Date/Time Calculations

```sql
-- TAT (Turnaround Time) in Days
TAT_Days = DATEDIFF(day, create_date, ticket_closed_datetime)

-- Last Visit Days Ago
Days_Since_Last_Visit = DATEDIFF(day, last_visit_in, CURRENT_DATE)

-- Days of Experience (seniority)
Days_Experience = DATEDIFF(day, date_of_joining, CURRENT_DATE)
```

---

## 6. DAILY DATA INGESTION PROCESS

### 6.1 Daily ETL Pipeline

**Schedule:** Run daily at 00:30 UTC (6:00 AM IST)

```
┌───────────────────────────────────────────────────────────────┐
│                   DAILY ETL PIPELINE                          │
└───────────────────────────────────────────────────────────────┘

Step 1: DATA UPLOAD
  └─ Receive files in /uploads folder:
     ├─ B2B_Offline_DD-MM-YYYY.xlsx (NEW - daily)
     ├─ view_ticket.xlsx (NEW - daily)
     ├─ Attendance_Data.xlsx (NEW - daily)
     ├─ visit_data.xlsx (NEW - daily)
     ├─ EmployeeMaster.xlsx (UPDATE - as needed)
     └─ customer_site_mst.csv (UPDATE - as needed)

Step 2: VALIDATE INPUTS
  ├─ Check file format (XLSX, CSV, correct sheet names)
  ├─ Check required columns exist
  ├─ Check data types (dates, numbers, strings)
  └─ Flag missing/malformed data

Step 3: TRANSFORM & LOAD
  ├─ Process offline_data:
  │   ├─ Filter: segment = 'PSU'
  │   ├─ Convert dates, cs_id as VARCHAR
  │   └─ APPEND to offline_data table (with data_date partition)
  │
  ├─ Process view_ticket:
  │   ├─ Filter: assigned_type = 'Engineer'
  │   ├─ Parse assigned_to column
  │   ├─ Validate ticket_status values
  │   └─ FULL REPLACE previous data
  │
  ├─ Process attendance_log:
  │   ├─ Recalculate attendance_status from in_datetime
  │   └─ APPEND to attendance_log
  │
  ├─ Process visit_log:
  │   └─ APPEND to visit_log (validate FK)
  │
  ├─ Process engineer_master (if provided):
  │   ├─ Filter: active_status = 'YES' AND designation = 'Engineer'
  │   └─ UPSERT to engineer_master
  │
  └─ Process customer_site_master (if provided):
      └─ UPSERT to customer_site_master

Step 4: REFRESH MATERIALIZED VIEWS
  ├─ Refresh offline_sites_summary (today's offline sites by service area)
  └─ Refresh engineer_performance_cache (if using)

Step 5: GENERATE ALERTS
  ├─ FLAG: Tickets with last_visit > 30 days ago
  ├─ FLAG: Engineers with Att_Days < 80% in period
  ├─ FLAG: Sites offline > 90 days
  └─ LOG: Data quality issues

Step 6: VALIDATION & QA
  ├─ Record count checks:
  │   ├─ offline_data: Should be 100-10000 rows (depending on day)
  │   ├─ view_ticket: Should be 1000-50000 rows
  │   └─ visit_log: Should be 100-5000 new rows
  │
  ├─ Referential integrity:
  │   ├─ All ticket_id in visit_log exist in view_ticket
  │   ├─ All employee_id exist in engineer_master
  │   └─ All oracle_site_no match customer_site_master
  │
  └─ Data quality:
      ├─ No NULL in critical columns
      ├─ Dates are reasonable (not future)
      └─ Status values are in allowed list

Step 7: DASHBOARD CACHE UPDATE
  └─ Pre-compute common queries:
     ├─ Engineer performance by state
     ├─ Ticket status distribution
     ├─ Offline sites by bucket
     └─ Attendance trends

Step 8: LOG & NOTIFY
  ├─ Log: ETL success/failure
  ├─ Email: Data quality summary
  └─ Metrics: Rows loaded, errors, warnings
```

### 6.2 ETL Error Handling

```yaml
Error Scenarios:
  
  1. Missing File:
     - Action: SKIP processing, LOG warning
     - Continue with other files
  
  2. Data Type Mismatch:
     - Action: ATTEMPT conversion, flag rows
     - If fails: SKIP row, increment error count
  
  3. FK Violation:
     - Action: Log ticket_id/employee_id not found
     - Skip insertion, flag data quality issue
  
  4. Duplicate Key:
     - Scenario: visit_id already in visit_log
     - Action: SKIP (idempotent), don't duplicate
  
  5. NULL in Required Column:
     - Action: Flag row, SKIP insertion
     - Example: NULL ticket_id in view_ticket
  
  6. Invalid Status Value:
     - Action: Flag row, SKIP insertion
     - Example: ticket_status = "UNKNOWN"
  
  Report:
    - Summary: Total rows processed, inserted, skipped, errors
    - Details: CSV of problematic rows for manual review
```

### 6.3 Query Performance Optimization

```sql
-- Create indexes for common queries:

-- 1. Engineer productivity queries
CREATE INDEX idx_visit_log_employee_date ON visit_log(employee_id, visit_date);
CREATE INDEX idx_attendance_employee_date ON attendance_log(employee_id, attendance_date);

-- 2. Offline data queries
CREATE INDEX idx_offline_data_state_age ON offline_data(state, aging_days, segment);
CREATE INDEX idx_offline_data_service_area ON offline_data(service_area_code);

-- 3. Ticket queries
CREATE INDEX idx_view_ticket_employee_status ON view_ticket(employee_id, ticket_status);
CREATE INDEX idx_view_ticket_state ON view_ticket(state);

-- 4. Time range queries
CREATE INDEX idx_visit_date_range ON visit_log(visit_date, employee_id);
CREATE INDEX idx_attendance_date_range ON attendance_log(attendance_date, employee_id);

-- Partitioning:
-- offline_data: PARTITION BY RANGE (YEAR(data_date)) - for fast historical queries
-- visit_log: PARTITION BY RANGE (MONTH(visit_date)) - for fast date range queries
-- attendance_log: PARTITION BY RANGE (MONTH(attendance_date)) - for fast date range queries
```

---

## APPENDIX: KEY FIELD GLOSSARY

| Term | Definition | Example |
|---|---|---|
| **cs_id** | Customer Site ID - unique site identifier | "071", "00123" |
| **oracle_site_no** | Oracle primary key for site in FSM | 12345 |
| **employee_id** | Unique engineer identifier | 1001, 1002 |
| **ticket_id** | Unique ticket identifier in FSM | "T-2026-00123" |
| **service_area_code** | Geographic area assigned to engineer (1:1) | "KA-BANG-001" |
| **aging_days** | Days since last activity (offline) or days in current status (ticket) | 5, 45, 120 |
| **offline_bucket** | Age-based classification for offline sites | "1-3 Days", "90+ Days" |
| **TAT** | Turnaround Time - days to resolve ticket | 7, 14, 30 |
| **Attendance %** | Percentage of days present vs working days | 85%, 92% |
| **Repeat Rate** | Average visits per distinct site | 1.5x, 2.3x |
| **Prod Days** | Days with at least one visit | 18, 22 |
| **OPEX** | Operational Expense (Canara Bank contract type) | Segment value |
| **PSU** | Public Sector Undertaking (filter criterion) | Bank segment |

---

## VERSION HISTORY

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-05-13 | Initial complete schema, ETL logic, and business rules documentation |

---

**END OF DOCUMENT**
