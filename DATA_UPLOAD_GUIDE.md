# Data Upload Module - Complete Guide

## Overview

The Data Upload Module enables users to upload Excel and CSV files containing engineer data, offline site information, attendance records, visits, and support tickets. The system validates, transforms, and loads data into the PostgreSQL database.

---

## 📋 Data Types Supported

### 1. **Engineers** 👥
Upload engineer profile information with active status, state assignment, and contact details.

**Required Columns:**
- `engineer_code` - 3-digit code (e.g., "001", preserves leading zeros)
- `engineer_name` - Full name
- `state` - Indian state name
- `designation` - Job title (must be "Engineer")
- `active_status` - YES or NO
- `phone` - Contact number
- `email` - Email address
- `service_area_code` - Service area assignment

**Validation Rules:**
- Engineer code must be exactly 3 digits
- Only active engineers (active_status = "YES") with designation = "Engineer" are loaded
- Duplicate engineer codes are removed (keeps first occurrence)
- All fields except service_area_code are required

**Example:**
```
engineer_code,engineer_name,state,designation,active_status,phone,email,service_area_code
001,Raj Kumar,Karnataka,Engineer,YES,9876543210,raj.kumar@vprotect.com,KA-001
002,Priya Singh,Tamil Nadu,Engineer,YES,9876543211,priya.singh@vprotect.com,TN-002
```

---

### 2. **Offline Sites** 🔴
Upload information about sites that are currently offline or inactive.

**Required Columns:**
- `site_id` - Unique site identifier
- `site_name` - Site name/location
- `state` - Indian state
- `segment` - Bank segment (must be "PSU" - PSU banks only)
- `last_online_date` - Date format YYYY-MM-DD
- `offline_duration_days` - Days offline (optional, auto-calculated)
- `priority` - CRITICAL/HIGH/MEDIUM/LOW (optional, auto-calculated)

**Validation Rules:**
- Only PSU (Public Sector Unit) bank sites are loaded
- Non-PSU records are automatically filtered out
- Offline duration auto-calculated if not provided: `(today - last_online_date) days`
- Priority auto-calculated based on offline duration if not provided:
  - CRITICAL: > 60 days
  - HIGH: > 30 days
  - MEDIUM: > 15 days
  - LOW: ≤ 15 days

**Example:**
```
site_id,site_name,state,segment,last_online_date,offline_duration_days,priority
SITE001,Bank Branch Mumbai,Maharashtra,PSU,2026-04-01,42,HIGH
SITE002,ATM Center Chennai,Tamil Nadu,PSU,2026-03-15,60,CRITICAL
```

---

### 3. **Attendance** 📋
Upload daily attendance records with check-in/check-out times.

**Required Columns:**
- `engineer_code` - 3-digit engineer code
- `attendance_date` - Date format YYYY-MM-DD
- `check_in_time` - Time format HH:MM:SS
- `check_out_time` - Time format HH:MM:SS (optional)
- `status` - OnTime/Late/Absent (optional, auto-calculated)

**Validation Rules:**
- Engineer code must be 3 digits
- Status auto-calculated if not provided:
  - Check-in before 10 AM = "OnTime"
  - Check-in after 10 AM = "Late"
  - NULL check_in_time = "Absent"
- Dates must be valid ISO format (YYYY-MM-DD)
- Times must be valid 24-hour format (HH:MM:SS)

**Example:**
```
engineer_code,attendance_date,check_in_time,check_out_time,status
001,2026-05-13,09:30:00,17:30:00,OnTime
001,2026-05-12,10:15:00,17:30:00,Late
001,2026-05-11,,,"Absent"
```

---

### 4. **Visits** 📍
Upload field engineer visit logs.

**Required Columns:**
- `engineer_code` - 3-digit code
- `site_id` - Site identifier
- `visit_date` - Date format YYYY-MM-DD
- `visit_type` - Visit type (Site Survey/Maintenance/Repair/Installation/Inspection)
- `problem_solved` - YES or NO
- `problem_description` - Description text
- `time_taken_minutes` - Duration in minutes

**Validation Rules:**
- Engineer code must be 3 digits
- Valid visit types: Site Survey, Maintenance, Repair, Installation, Inspection
- Invalid types default to "Inspection"
- Problem_solved must be YES or NO
- Time must be numeric (minutes)

**Example:**
```
engineer_code,site_id,visit_date,visit_type,problem_solved,problem_description,time_taken_minutes
001,SITE001,2026-05-13,Maintenance,YES,Fixed network issue,45
001,SITE002,2026-05-12,Repair,NO,Server not responding,120
```

---

### 5. **Tickets** 🎫
Upload support ticket information.

**Required Columns:**
- `ticket_id` - Unique ticket identifier
- `site_id` - Site identifier
- `engineer_code` - 3-digit code
- `ticket_status` - Ticket status (OPEN/PENDING/SENTBACK/COMPLETED/CLOSED/CANCELLED/REJECTED)
- `created_date` - Date format YYYY-MM-DD
- `closed_date` - Date format YYYY-MM-DD (optional)
- `priority` - P1/P2/P3/P4
- `category` - Issue category

**Validation Rules:**
- Ticket status must be one of the fixed statuses (case-insensitive, converted to uppercase)
- Invalid statuses default to "OPEN"
- Dates must be valid ISO format
- Closed date is optional (only for closed tickets)
- Engineer code must be 3 digits

**Example:**
```
ticket_id,site_id,engineer_code,ticket_status,created_date,closed_date,priority,category
TKT001,SITE001,001,OPEN,2026-05-13,,P1,Network
TKT002,SITE002,001,CLOSED,2026-05-10,2026-05-12,P2,Power
```

---

## 🚀 How to Upload Data

### Step 1: Access Upload Page
1. Login to the dashboard with your credentials
2. Click **"📤 Data Upload"** in the sidebar navigation

### Step 2: Select Data Type
Choose which type of data you're uploading:
- 👥 Engineers
- 🔴 Offline Sites
- 📋 Attendance
- 📍 Visits
- 🎫 Tickets

### Step 3: Select File
1. Click the file upload area or drag & drop a file
2. Supported formats: `.xlsx`, `.xls`, `.csv`
3. Maximum file size: typically 50MB (depends on server)

### Step 4: Preview Data (Optional)
- Click **"📊 Preview Data"** to see first 10 rows
- Verify column names and sample values
- Check if data format looks correct

### Step 5: Validate Data
- Click **"✓ Validate Data"** to run comprehensive checks
- System validates:
  - All required columns present
  - Data types correct
  - Business rules met (e.g., segment = PSU)
  - No critical null values
  - No duplicate key values

### Step 6: Review Validation Report
The validation report shows:
- ✓ Total rows uploaded
- ✓ Valid rows (will be loaded)
- ✗ Invalid rows (will be skipped)
- ❌ Errors (if any)
- ⚠️ Warnings (filtered/transformed rows)

### Step 7: Confirm & Load
If validation is successful:
- Click **"✅ Confirm & Load to Database"**
- System will load valid records into PostgreSQL
- View upload history to track status

---

## 📊 Download Templates

To download a pre-formatted template:

1. Go to **"📤 Data Upload"** → **"Templates"** tab
2. Click **"📥 Download Template"** for your data type
3. Template includes:
   - Header row with column names
   - 1-2 sample data rows
   - Comments explaining data format and rules
4. Fill in your data using the template
5. Save as CSV or Excel (.xlsx)
6. Upload using the upload form

---

## ✅ Validation Rules Summary

| Field | Rule | Auto-Fix |
|-------|------|----------|
| engineer_code | Must be 3 digits | Zero-padded if shorter |
| segment (Offline) | Must be "PSU" | Non-PSU filtered out |
| active_status | Must be YES/NO | ❌ Rejected if invalid |
| designation | Must be Engineer | ❌ Non-engineers filtered |
| attendance_status | Must be OnTime/Late/Absent | ✓ Auto-calculated from check_in_time |
| ticket_status | Fixed list of 7 statuses | Defaults to "OPEN" if invalid |
| Dates | Valid ISO format (YYYY-MM-DD) | ❌ Rejected if invalid |
| Times | Valid 24-hour format (HH:MM:SS) | ❌ Rejected if invalid |
| Duplicates | One per key columns | First occurrence kept |
| Nulls | Not allowed in required columns | ❌ Rejected if null |

---

## 📈 Upload History

Track all previous uploads:

1. Go to **"📤 Data Upload"** → **"History"** tab
2. View recent uploads with:
   - Filename and date
   - Data type (Engineers, Visits, etc.)
   - Number of rows loaded
   - Status (Success/Error)
   - Error count if any

---

## 🔍 Common Issues & Fixes

### Issue: "Missing columns" error
**Fix:** Download the template and use the exact column names provided.

### Issue: "Invalid engineer code" 
**Fix:** Engineer codes must be exactly 3 digits (e.g., "001" not "1"). System will zero-pad shorter codes.

### Issue: "Segment must be PSU"
**Fix:** For Offline Sites, only PSU (Public Sector Unit) banks are supported. Non-PSU records are filtered out.

### Issue: "Invalid date format"
**Fix:** Use ISO format: YYYY-MM-DD (e.g., 2026-05-13, not 13-05-2026)

### Issue: "Too many invalid rows"
**Fix:** Preview the data first to check format. Download and use the template to ensure correct structure.

### Issue: "Duplicate records found"
**Fix:** Check for duplicate engineer codes or site IDs. System keeps first occurrence, removes duplicates.

---

## 📋 Bulk Upload Best Practices

1. **Prepare Data First**
   - Use template as base
   - Validate dates are ISO format (YYYY-MM-DD)
   - Ensure engineer codes are 3 digits
   - Remove test/duplicate rows

2. **Test Small First**
   - Upload 10-20 rows first
   - Check validation report
   - Fix any errors
   - Then upload full dataset

3. **Archive Files**
   - Keep copy of uploaded files
   - Name with date (engineers_2026-05-13.xlsx)
   - Track which file was loaded when

4. **Monitor Progress**
   - Check History tab after upload
   - Verify row counts match expectations
   - Look for warning messages

---

## 🛠️ Technical Details

**Upload Processing:**
1. File is read (Excel or CSV)
2. Data type is auto-detected from column names
3. Columns are validated against schema
4. Data types are validated (numbers, dates, etc.)
5. Business rules are applied (filters, transformations)
6. Valid rows are queued for database load
7. Invalid rows are reported with error messages

**Data Transformations Applied:**
- Leading zeros preserved in 3-digit codes
- Attendance status calculated from check-in time
- Offline priority calculated from offline days
- Invalid statuses corrected to defaults
- Duplicate rows removed
- Null values handled per column rules

---

## 📞 Support

For upload issues:
1. Check Common Issues section above
2. Download template and verify column names
3. Preview data to see what's being uploaded
4. Review validation report for specific errors
5. Contact admin with:
   - Error message text
   - File name and size
   - Number of rows in file
   - Data type being uploaded

---

**Data Upload Module v1.0** - Ready for production data ingestion
