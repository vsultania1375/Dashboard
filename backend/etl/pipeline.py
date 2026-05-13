"""
ETL Pipeline — Service Analysis Dashboard v2.0
Source of truth: Architecture_v2.docx

Table mapping (v2.0):
  offline_data_master   ← daily B2B offline file (APPEND, never truncate)
  customer_site_master  ← site master (periodic full replace)
  view_ticket           ← current ticket state (TRUNCATE + INSERT daily)
  engineer_master       ← engineer list (periodic full replace)
  visit_master          ← visit records (APPEND)
  attendance_data       ← attendance (APPEND, ON CONFLICT DO NOTHING)
  service_area_master   ← service area lookup (periodic full replace)
"""
import os, re, uuid, logging, json, math, threading
from datetime import datetime, date, timedelta
from typing import Optional
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://dashboard:dashboard@localhost:5432/service_dashboard")

# ── In-memory job registry for async ETL polling ──────────
_jobs: dict = {}   # job_id → {"status": ..., "result": ..., "started_at": ...}

def get_engine() -> Engine:
    return create_engine(DB_URL, pool_pre_ping=True, pool_size=5)

# ══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════

def nn(v):
    """Return None for NaN/None, else value."""
    if v is None: return None
    if isinstance(v, float) and math.isnan(v): return None
    return v

def safe_str(val, max_len=None) -> str:
    if val is None: return ""
    if isinstance(val, float) and math.isnan(val): return ""
    s = str(val).strip()
    if max_len: s = s[:max_len]
    return s

def safe_date(val):
    if val is None: return None
    if isinstance(val, float) and math.isnan(val): return None
    try: return pd.to_datetime(val, dayfirst=True).date()
    except: return None

def safe_ts(val):
    if val is None or (isinstance(val, float) and math.isnan(val)): return None
    try:
        if pd.isna(val): return None
    except: pass
    try:
        result = pd.to_datetime(val, dayfirst=True)
        if pd.isna(result): return None
        return result.to_pydatetime()
    except: return None

def safe_int(val, default=0) -> int:
    try: return int(float(val))
    except: return default

def parse_employee_id(name_field):
    """Parse 'Rahul Sharma (EMP-1234)' → ('Rahul Sharma', 'EMP-1234')."""
    if not name_field or (isinstance(name_field, float) and math.isnan(name_field)):
        return ("", "")
    name_str = str(name_field).strip()
    match = re.search(r'\(([^)]+)\)\s*$', name_str)
    if match:
        code = match.group(1).strip()
        name = name_str[:match.start()].strip()
        return (name, code)
    return (name_str, "")

def normalize_bucket(days) -> str:
    try: d = int(float(days))
    except: return "Unknown"
    if d <= 3:  return "1-3"
    if d <= 7:  return "4-7"
    if d <= 15: return "8-15"
    if d <= 30: return "16-30"
    if d <= 60: return "31-60"
    if d <= 90: return "61-90"
    return "90+"

def normalize_status(status) -> str:
    """Normalise ticket status per v2.0 spec."""
    s = safe_str(status).upper().strip()
    if s in ('SENDBACK', 'SEND BACK', 'SENT BACK'): return 'SENTBACK'
    return s

def normalize_bank_name(b2b_code: str, site_name: str) -> str:
    """
    Derive bank_name_standard from b2b_code or site_name.
    Returns one of the exact values defined in Architecture_v2.docx §2.4.
    """
    text_ = (b2b_code + " " + site_name).upper()
    if any(k in text_ for k in ('SBI', 'STATE BANK')): return 'STATE BANK OF INDIA'
    if any(k in text_ for k in ('INDIAN BANK', 'IB ATM')): return 'INDIAN BANK'
    if any(k in text_ for k in ('CANARA', 'CB ATM')): return 'CANARA BANK'
    if any(k in text_ for k in ('CENTRAL BANK', 'CBI')): return 'CENTRAL BANK OF INDIA'
    if any(k in text_ for k in ('KERALA GRAMIN', 'KGB')): return 'KERALA GRAMIN BANK'
    if any(k in text_ for k in ('KARNATAKA GRAMIN', 'KGBO')): return 'KARNATAKA GRAMIN BANK'
    return 'OTHER'

def extract_atm_id(branch_code: str, bank_name_standard: str) -> str:
    """Extract ATM ID from branch_code for Indian Bank sites only (§2.4)."""
    if bank_name_standard != 'INDIAN BANK': return ''
    # Format: 'IB ATM_12345' or 'IB 12345'
    match = re.search(r'(?:IB\s+ATM[_\s]*|IB\s+)(\w+)', branch_code.upper())
    if match: return match.group(1).strip()
    # Fallback: return last word/number
    parts = branch_code.strip().split()
    return parts[-1] if parts else ''

def derive_attendance_status(in_datetime) -> str:
    """
    Derive attendance_status_derived per v2.0 spec §2.3:
      ON TIME : in_datetime NOT NULL AND time ≤ 10:00 (HOUR*60+MINUTE ≤ 600)
      LATE    : in_datetime NOT NULL AND time > 10:00
      ABSENT  : in_datetime IS NULL
    """
    if in_datetime is None: return 'ABSENT'
    try:
        if isinstance(in_datetime, str):
            in_datetime = pd.to_datetime(in_datetime)
        minutes = in_datetime.hour * 60 + in_datetime.minute
        return 'ON TIME' if minutes <= 600 else 'LATE'
    except: return 'ABSENT'

def stock_related(reason) -> bool:
    if not reason: return False
    keywords = ['stock','material','spare','part','component','inventory',
                'power issue','under renovation','power cut']
    return any(k in str(reason).lower() for k in keywords)

# ══════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════

class ValidationResult:
    def __init__(self):
        self.errors = []; self.warnings = []; self.row_count = 0; self.passed = True
    def add_error(self, msg): self.errors.append(msg); self.passed = False
    def add_warning(self, msg): self.warnings.append(msg)

def validate_b2b_offline(df):
    res = ValidationResult(); res.row_count = len(df)
    if df.empty: res.add_error("File has no data rows")
    cs_col = next((c for c in df.columns if c.lower() in ['cs_no','cs no','cs id','cs_id']), None)
    if not cs_col: res.add_warning("Could not find CS ID column — will use first column")
    return res

def validate_view_ticket(df, engine, prev_count):
    res = ValidationResult(); res.row_count = len(df)
    if 'Ticket ID' not in df.columns: res.add_error("Missing required column: Ticket ID")
    if prev_count > 0 and len(df) < prev_count * 0.60:
        res.add_warning(f"Row count ({len(df)}) is much less than previous ({prev_count})")
    valid_statuses = {'OPEN','COMPLETED','CLOSED','PENDING','SENTBACK','SENDBACK',
                      'SEND BACK','SENT BACK','CANCELLED','REJECTED'}
    if 'Ticket Status' in df.columns:
        bad = set(df['Ticket Status'].dropna().str.upper().str.strip().unique()) - valid_statuses
        if bad: res.add_warning(f"Unrecognised statuses (will be stored as-is): {bad}")
    return res

def validate_attendance(df, engine):
    res = ValidationResult(); res.row_count = len(df)
    if 'Attendance Date' not in df.columns:
        res.add_error("Missing required column: Attendance Date"); return res
    try:
        dates_in_file = pd.to_datetime(df['Attendance Date'], dayfirst=True).dt.date.dropna().unique()
        with engine.connect() as conn:
            for d in dates_in_file:
                count = conn.execute(
                    text("SELECT COUNT(*) FROM attendance_data WHERE attendance_date = :d"), {"d": d}
                ).scalar()
                if count and count > 0:
                    res.add_error(f"Attendance for {d} already exists (APPEND-ONLY — upload only new dates)")
    except Exception as e:
        res.add_warning(f"Could not check for duplicate dates: {e}")
    return res

def validate_engineer(df):
    res = ValidationResult(); res.row_count = len(df)
    if 'Employee Code' not in df.columns: res.add_error("Missing required column: Employee Code")
    return res

def validate_site_master(df):
    res = ValidationResult(); res.row_count = len(df)
    # oracle_site_no is the PK (per v2.0 §1.3)
    has_oracle = any(c.lower() in ('oracle_site_no', 'oracle_site_number', 'oracle site no') for c in df.columns)
    if not has_oracle: res.add_error("Missing required column: oracle_site_no")
    return res

def validate_visit_master(df):
    res = ValidationResult(); res.row_count = len(df)
    if 'Visit ID' not in df.columns and 'visit_id' not in df.columns:
        res.add_error("Missing required column: Visit ID")
    return res

def validate_visit_form(df):
    res = ValidationResult(); res.row_count = len(df)
    has_ticket = any(c.lower() in ('ticket id', 'ticket_id') for c in df.columns)
    has_date   = any(c.lower() in ('visit date', 'visit_date') for c in df.columns)
    if not has_ticket: res.add_error("Missing required column: Ticket ID")
    if not has_date:   res.add_error("Missing required column: Visit Date")
    return res

# ══════════════════════════════════════════════════════════
# LOAD FUNCTIONS
# ══════════════════════════════════════════════════════════

def load_offline_data(df, engine, data_date):
    """
    Load B2B offline file into offline_data_master.
    APPEND mode — never truncate. Deduplicate on (cs_id, data_date).
    cs_id ALWAYS stored as STRING — preserve leading zeros.
    data_date = date passed from caller (parsed from filename or today).
    """
    log.info(f"Loading B2B Offline data for data_date={data_date}...")
    # Build site lookup for enrichment
    with engine.connect() as conn:
        site_df = pd.read_sql(
            "SELECT oracle_site_number AS oracle_site_no, cs_id, site_state AS state, service_area_code FROM customer_site_master", conn
        )
    site_map = site_df.dropna(subset=['cs_id']).drop_duplicates(subset='cs_id').set_index('cs_id').to_dict('index')

    cs_col = next((c for c in df.columns if c.lower() in ['cs_no','cs no','cs id','cs_id']), df.columns[0])
    rows = []
    seen = set()
    for _, row in df.iterrows():
        # cs_id ALWAYS STRING, preserve leading zeros, trim whitespace
        cs_id = str(row.get(cs_col, '') or '').strip()
        if not cs_id or cs_id.lower() in ('nan','none',''): continue
        # Dedup on (cs_id, data_date)
        key = (cs_id, data_date)
        if key in seen: continue
        seen.add(key)

        aging_days = safe_int(row.get('No. Of Days', row.get('offline_days', row.get('Days', 0))))
        b2b_code   = safe_str(row.get('B2B Code', row.get('b2b_code', row.get('Customer', ''))), 100)
        site_name  = safe_str(row.get('Site Name', row.get('Site Name/ Location', '')), 490)
        branch_code = safe_str(row.get('Branch Code / ATM ID', row.get('Branch Code', '')), 100)
        bucket_raw = safe_str(row.get('Bucket', row.get('bucket', '')))
        bucket = bucket_raw if bucket_raw and bucket_raw not in ('nan', '') else normalize_bucket(aging_days)
        bank_std = normalize_bank_name(b2b_code, site_name)
        atm_id   = extract_atm_id(branch_code, bank_std)

        rows.append({
            'cs_id':              cs_id,
            'site_name':          site_name,
            'b2b_code':           b2b_code,
            'bank_name_standard': bank_std,
            'aging_days':         aging_days,
            'bucket':             bucket,
            'state':              safe_str(row.get('State', row.get('state', '')), 100),
            'zone':               safe_str(row.get('Zone', row.get('zone', '')), 20),
            'segment':            safe_str(row.get('Segment', row.get('segment', '')), 10),
            'branch_code':        branch_code,
            'atm_id':             atm_id,
            'offline_datetime':   safe_ts(row.get('Offline Date & Time', row.get('offline_datetime'))),
            'data_date':          data_date,
        })

    if not rows: return 0
    df_out = pd.DataFrame(rows)
    with engine.begin() as conn:
        # Delete existing rows for same (cs_id, data_date) combos to allow re-upload of same date
        conn.execute(
            text("DELETE FROM offline_data_master WHERE data_date = :d"), {"d": data_date}
        )
        df_out.to_sql('offline_data_master', conn, if_exists='append', index=False, method='multi', chunksize=500)
    log.info(f"Offline Data: {len(rows)} rows loaded for {data_date}")
    return len(rows)

# Legacy alias for upload handler compatibility
load_b2b_offline = load_offline_data


def load_site_master(df, engine):
    """
    Load customer site master — periodic full replace.
    oracle_site_no is PRIMARY KEY.
    cs_id is stored separately (unique index) for B2B joins.
    Do NOT filter on active_status. Include all sites.
    service_area_code is nullable — do not reject null values.
    """
    log.info("Loading Customer Site Master...")
    rows = []
    seen = set()
    for _, row in df.iterrows():
        # oracle_site_no is the PK
        oracle_site_no = safe_str(
            row.get('oracle_site_no', row.get('oracle_site_number', row.get('Oracle Site No', ''))), 50
        ).replace('.0', '').strip()
        if not oracle_site_no or oracle_site_no.lower() in ('nan','none',''): continue
        if oracle_site_no in seen: continue
        seen.add(oracle_site_no)

        # cs_id — B2B join key, STRING, preserve leading zeros
        cs_id = str(row.get('cs_id', row.get('CS ID', row.get('cs_no', ''))) or '').strip()
        if cs_id.lower() in ('nan','none',''): cs_id = ''

        lat = nn(pd.to_numeric(row.get('latitude', row.get('site_lat', row.get('Latitude'))), errors='coerce'))
        lon = nn(pd.to_numeric(row.get('longitude', row.get('site_long', row.get('Longitude'))), errors='coerce'))
        if lat is not None and abs(lat) > 90:  lat = None
        if lon is not None and abs(lon) > 180: lon = None

        sac = safe_str(row.get('service_area_code', row.get('Service Area Code', '')), 50)

        rows.append({
            'oracle_site_number': oracle_site_no,
            'cs_id':             cs_id or None,
            'site_name':         safe_str(row.get('site_name', row.get('oracle_site_name', row.get('Site Name', ''))), 490),
            'oracle_site_name':  safe_str(row.get('site_name', row.get('oracle_site_name', row.get('Site Name', ''))), 490),
            'customer_name_full':safe_str(row.get('customer_name_full', row.get('oracle_customer_name', row.get('Customer Name', ''))), 255),
            'oracle_customer_name': safe_str(row.get('customer_name_full', row.get('oracle_customer_name', row.get('Customer Name', ''))), 255),
            'service_area_code': sac or None,
            'state':             safe_str(row.get('state', row.get('site_state', row.get('State', ''))), 100),
            'site_state':        safe_str(row.get('state', row.get('site_state', row.get('State', ''))), 100),
            'city':              safe_str(row.get('city', row.get('City', '')), 100),
            'latitude':          lat,
            'longitude':         lon,
            'zone':              safe_str(row.get('zone', row.get('Zone', '')), 50),
            'active_status':     safe_str(row.get('active_status', row.get('Active Status', '')), 20),
            'business_type':     safe_str(row.get('business_type', row.get('Business Type', 'B2B')), 10),
            'b2b_code':          safe_str(row.get('b2b_code', row.get('B2B Code', '')), 100),
        })

    if not rows: return 0
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM customer_site_master"))
        pd.DataFrame(rows).to_sql('customer_site_master', conn, if_exists='append', index=False, method='multi', chunksize=500)
    log.info(f"Site Master: {len(rows)} rows loaded")
    return len(rows)


def load_view_ticket(df, engine, data_date):
    """
    Load view ticket — TRUNCATE entire table then INSERT.
    Filter on insert: assigned_type='ENGINEER' only (per §3.2).
    If oracle_site_no not in customer_site_master → skip row silently.
    assigned_employee_id parsed from assigned_to on ingestion.
    ticket_status normalised: SENDBACK/SENT BACK → SENTBACK.
    """
    log.info("Loading View Ticket data...")
    # Build oracle_site_no set for validation
    with engine.connect() as conn:
        valid_sites = set(
            r[0] for r in conn.execute(
                text("SELECT oracle_site_number FROM customer_site_master")
            ).fetchall()
        )
        # Also get cs_id → service_area_code for enrichment
        site_df = pd.read_sql(
            "SELECT oracle_site_number AS oracle_site_no, cs_id, site_state AS state, service_area_code FROM customer_site_master", conn
        )
    site_by_oracle = site_df.drop_duplicates(subset='oracle_site_no').set_index('oracle_site_no').to_dict('index')

    rows = []; snap_rows = []
    for _, row in df.iterrows():
        tid = safe_str(row.get('Ticket ID', ''))
        if not tid: continue

        # Filter: assigned_type = ENGINEER only
        assigned_type = safe_str(row.get('Ticket Assigned Type', row.get('assigned_type', 'ENGINEER'))).upper()
        if assigned_type != 'ENGINEER': continue

        oracle_site_no = safe_str(row.get('Oracle Site No', row.get('oracle_site_no', '')))
        # Skip if oracle_site_no not found in customer_site_master
        if oracle_site_no and oracle_site_no not in valid_sites: continue

        cs_id = safe_str(row.get('CS ID', row.get('cs_id', '')))
        assigned_raw = safe_str(row.get('Ticket Assigned To', row.get('assigned_to', '')))
        emp_name, emp_id = parse_employee_id(assigned_raw)
        status = normalize_status(row.get('Ticket Status', ''))
        reason = safe_str(row.get('Ticket Status Reason', ''))
        planned = safe_date(row.get('Planned Date'))
        aging = safe_int(row.get('Aging Days', 0))
        create_raw = row.get('Create Date')

        site_info = site_by_oracle.get(oracle_site_no, {})
        lvi = safe_ts(row.get('Last Visit In Date-Time', ''))
        r = {
            'ticket_id':               tid,
            'oracle_site_no':          oracle_site_no,
            'cs_id':                   cs_id,
            'ticket_status':           status,
            'ticket_status_reason':    reason,
            'aging_days':              aging,
            'ticket_type':             safe_str(row.get('Ticket Type', '')),
            'ticket_sub_type':         safe_str(row.get('Ticket Sub-Type', row.get('Sub-Type', ''))),
            'ticket_assigned_type':    assigned_type,
            'ticket_assigned_to':      assigned_raw,
            'assigned_employee_code':  emp_id,
            'last_visit_in':           lvi,
            'last_visit_out':          safe_ts(row.get('Last Visit Out Date-Time', '')),
            'create_date':             safe_date(create_raw),
            'create_datetime':         safe_ts(create_raw),
            'planned_date':            planned,
            'ticket_closed_datetime':  safe_ts(row.get('Ticket Closed Date & Time', '')),
            'last_submission_datetime':safe_ts(row.get('Last Submission Date Time', '')),
            'current_approver_name':   safe_str(row.get('Current Approver Name', '')),
            'state_name':              safe_str(row.get('State Name', '')),
            'total_visits':            safe_int(row.get('Total Visits', 0)),
            'service_area_code':       site_info.get('service_area_code', '') or None,
            'site_state_master':       site_info.get('state', '') or None,
            'upload_date':             data_date,
            'is_orphaned':             not bool(oracle_site_no and oracle_site_no in valid_sites),
        }
        rows.append(r)
        snap_rows.append({
            'snapshot_date':        date.today(),
            'ticket_id':            tid,
            'cs_id':                cs_id,
            'ticket_status':        status,
            'ticket_status_reason': reason,
            'planned_date':         planned,
            'aging_days':           aging,
            'total_visits':         safe_int(row.get('Total Visits', 0)),
            'assigned_employee_code': emp_id,
            'last_visit_in':        lvi,
        })

    if not rows: return 0
    today = date.today()
    with engine.begin() as conn:
        # TRUNCATE entire table (no history stored)
        conn.execute(text("TRUNCATE TABLE view_ticket"))
        pd.DataFrame(rows).to_sql('view_ticket', conn, if_exists='append', index=False, method='multi', chunksize=300)
        # Snapshot for fraud detection (retain 90 days)
        conn.execute(text("DELETE FROM ticket_snapshot WHERE snapshot_date = :d"), {"d": today})
        pd.DataFrame(snap_rows).to_sql('ticket_snapshot', conn, if_exists='append', index=False, method='multi', chunksize=500)
        conn.execute(text("DELETE FROM ticket_snapshot WHERE snapshot_date < CURRENT_DATE - INTERVAL '90 days'"))
    log.info(f"View Ticket: {len(rows)} rows loaded (ENGINEER-only, site-validated)")
    return len(rows)


def load_engineer_master(df, engine):
    """
    Load engineer master — periodic full replace.
    Filter on ingestion: designation='Engineer' AND is_active='YES'.
    PK: employee_id (parsed from Employee Code column).
    """
    log.info("Loading Engineer Master...")
    rows = []
    for _, row in df.iterrows():
        emp_id = safe_str(row.get('Employee Code', row.get('employee_id', '')))
        if not emp_id: continue
        designation = safe_str(row.get('Designation', ''))
        is_active   = safe_str(row.get('Active Status', row.get('is_active', 'Yes')))
        # Filter: designation=Engineer AND is_active=YES
        if designation.upper() != 'ENGINEER': continue
        if is_active.upper() not in ('YES', 'Y', '1', 'TRUE', 'ACTIVE'): continue

        doj = pd.to_datetime(row.get('Date Of Joining'), errors='coerce', dayfirst=True)
        base_lat = nn(pd.to_numeric(row.get('Base Latitude', row.get('base_latitude')), errors='coerce'))
        base_lon = nn(pd.to_numeric(row.get('Base Longitude', row.get('base_longitude')), errors='coerce'))
        if base_lat is not None and abs(base_lat) > 90:  base_lat = None
        if base_lon is not None and abs(base_lon) > 180: base_lon = None

        rows.append({
            'employee_id':        emp_id,
            'employee_code':      emp_id,
            'employee_name':      safe_str(row.get('Employee Name', '')),
            'service_area_code':  safe_str(row.get('Service Area Code', '')),
            'designation':        designation,
            'is_active':          'YES',
            'date_of_joining':    doj.date() if pd.notna(doj) else None,
            'service_state':      safe_str(row.get('Service State', row.get('State', ''))),
            'state':              safe_str(row.get('State', '')),
            'city':               safe_str(row.get('City', '')),
            'region':             safe_str(row.get('Region', '')),
            'company_name':       safe_str(row.get('Company Name', '')),
            'department':         safe_str(row.get('Department', '')),
            'address':            safe_str(row.get('Address', '')),
            'pin_code':           safe_str(row.get('Pin Code', '')).replace('.0', '')[:10],
            'email':              safe_str(row.get('Email Id', '')),
            'phone':              safe_str(row.get('Phone No', '')).replace('.0', '')[:20],
            'base_latitude':      base_lat,
            'base_longitude':     base_lon,
            'reporting_manager_1':safe_str(row.get('Reporting Manager 1', '')),
            'reporting_manager_2':safe_str(row.get('Reporting Manager 2', '')),
            'reporting_manager_3':safe_str(row.get('Reporting Manager 3', '')),
            'asset_type':         safe_str(row.get('Asset Type', '')),
            'serial_no':          safe_str(row.get('Serial No', '')),
            'asset_description':  safe_str(row.get('Asset Description', '')),
            'sick_leave':         nn(pd.to_numeric(row.get('Sick Leave'), errors='coerce')),
            'casual_leave':       nn(pd.to_numeric(row.get('Casual Leave'), errors='coerce')),
            'restricted_leave':   nn(pd.to_numeric(row.get('Restricted Leave'), errors='coerce')),
        })

    if not rows: return 0
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM engineer_master"))
        pd.DataFrame(rows).to_sql('engineer_master', conn, if_exists='append', index=False, method='multi', chunksize=500)
    log.info(f"Engineer Master: {len(rows)} engineers loaded (designation=Engineer, is_active=YES)")
    return len(rows)


def load_attendance_data(df, engine):
    """
    Load attendance into attendance_data — APPEND mode.
    Block re-upload: ON CONFLICT (employee_id, attendance_date) DO NOTHING.
    Parse employee_id from 'Employee Name (ID)' format using regex (§2.5).
    Derive attendance_status_derived on ingestion (ON TIME / LATE / ABSENT) per §2.3.
    """
    log.info("Loading Attendance data...")
    # Build employee_id → service_state lookup for enrichment
    with engine.connect() as conn:
        eng_df = pd.read_sql("SELECT employee_code AS employee_id, service_state FROM engineer_master", conn)
    eng_map = eng_df.set_index('employee_id')['service_state'].to_dict()

    rows = []
    for _, row in df.iterrows():
        # Parse employee_id — primary: Employee Code column; fallback: parse from Employee Name
        emp_id = safe_str(row.get('Employee Code', ''))
        if not emp_id:
            emp_name_raw = safe_str(row.get('Employee Name', ''))
            _, emp_id = parse_employee_id(emp_name_raw)
        if not emp_id: continue

        att_date = safe_date(row.get('Attendance Date'))
        if not att_date: continue

        in_dt = safe_ts(row.get('In Date Time', row.get('in_datetime')))
        att_status = derive_attendance_status(in_dt)

        rows.append({
            'employee_id':               emp_id,
            'employee_code':             emp_id,
            'attendance_date':           att_date,
            'in_datetime':               in_dt,
            'attendance_status_derived': att_status,
            'service_state':             eng_map.get(emp_id, safe_str(row.get('Service State', ''))),
        })

    if not rows:
        log.warning("No valid attendance rows found"); return 0

    inserted = 0
    with engine.begin() as conn:
        for r in rows:
            try:
                sp = conn.begin_nested()
                conn.execute(text("""
                    INSERT INTO attendance_data
                      (employee_id, attendance_date, in_datetime, attendance_status_derived, service_state)
                    VALUES (:eid, :ad, :in_dt, :status, :ss)
                    ON CONFLICT (employee_id, attendance_date) DO NOTHING
                """), {
                    'eid':    r['employee_id'],
                    'ad':     r['attendance_date'],
                    'in_dt':  r['in_datetime'],
                    'status': r['attendance_status_derived'],
                    'ss':     r['service_state'],
                })
                sp.commit()
                inserted += 1
            except Exception as e:
                sp.rollback()
                log.warning(f"Skip attendance {r['employee_id']} {r['attendance_date']}: {e}")

    log.info(f"Attendance: {inserted} rows inserted")
    return inserted

# Legacy alias
load_attendance = load_attendance_data


def load_visit_master(df, engine):
    """
    Load visit_master — APPEND mode. Deduplicate on visit_id.
    Store only: visit_id, ticket_id, employee_id, visit_date.
    """
    log.info("Loading Visit Master data...")
    rows = []
    seen = set()
    for _, row in df.iterrows():
        vid = safe_str(row.get('Visit ID', row.get('visit_id', '')))
        if not vid or vid in seen: continue
        seen.add(vid)
        # Parse employee_id if stored as 'Name (ID)' format
        emp_raw = safe_str(row.get('Employee Name', row.get('employee_id', '')))
        _, emp_id = parse_employee_id(emp_raw)
        if not emp_id: emp_id = emp_raw
        rows.append({
            'visit_id':   vid,
            'ticket_id':  safe_str(row.get('Ticket ID', row.get('ticket_id', ''))),
            'employee_id': emp_id,
            'employee_code': emp_id,
            'visit_date': safe_date(row.get('Visit Date', row.get('visit_date'))),
        })
    if not rows: return 0
    inserted = 0
    with engine.begin() as conn:
        for r in rows:
            try:
                sp = conn.begin_nested()
                conn.execute(text("""
                    INSERT INTO visit_master (visit_id, ticket_id, employee_id, visit_date)
                    VALUES (:vid, :tid, :eid, :vd)
                    ON CONFLICT (visit_id) DO NOTHING
                """), {'vid': r['visit_id'], 'tid': r['ticket_id'], 'eid': r['employee_id'], 'vd': r['visit_date']})
                sp.commit()
                inserted += 1
            except Exception as e:
                sp.rollback()
                log.warning(f"Skip visit {r['visit_id']}: {e}")
    log.info(f"Visit Master: {inserted} rows inserted")
    return inserted


def load_visit_form(df, engine):
    """Load visit_form — APPEND mode. Deduplicate on (ticket_id, visit_date, employee_code)."""
    log.info("Loading Visit Form data...")
    rows = []
    for _, row in df.iterrows():
        tid = safe_str(row.get('Ticket ID', row.get('ticket_id', '')))
        vd  = safe_date(row.get('Visit Date', row.get('visit_date')))
        if not tid or not vd: continue
        emp_raw  = safe_str(row.get('Technician Name', row.get('technician_name', '')))
        _, emp_code = parse_employee_id(emp_raw)
        if not emp_code:
            emp_code = safe_str(row.get('Employee Code', row.get('employee_code', '')))
        def _s(key, alt=None): return safe_str(row.get(key, row.get(alt or key, ''))) or None
        def _i(key):
            v = row.get(key)
            try: return int(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else None
            except: return None
        rows.append({
            'ticket_id': tid, 'cs_id': _s('CS ID','cs_id'), 'technician_name': _s('Technician Name','technician_name'),
            'employee_code': emp_code or None, 'customer_name': _s('Customer Name','customer_name'),
            'site_name': _s('Site Name','site_name'), 'creation_date': safe_date(row.get('Creation Date', row.get('creation_date'))),
            'visit_date': vd, 'ticket_status': _s('Ticket Status','ticket_status'),
            'site_status': _s('Site Status','site_status'), 'inactive_reason': _s('Inactive Reason','inactive_reason'),
            'dismantle_material': _s('Dismantle Material','dismantle_material'),
            'actual_problem': _s('Actual Problem','actual_problem'), 'action_taken': _s('Action Taken','action_taken'),
            'problem_solved': _s('Problem Solved','problem_solved'), 'reason_not_solved': _s('Reason Not Solved','reason_not_solved'),
            'action_to_be_taken': _s('Action To Be Taken','action_to_be_taken'),
            'nearest_police_station': _s('Nearest Police Station','nearest_police_station'),
            'smps_input': _s('SMPS Input','smps_input'), 'hooter': _s('Hooter','hooter'),
            'continuous_recording_days': _i('Continuous Recording Days'),
            'pm_done': _s('PM Done','pm_done'), 'two_way_working': _s('Two Way Working','two_way_working'),
            'smoke_sensor_working': _s('Smoke Sensor Working','smoke_sensor_working'),
        })
    if not rows: return 0
    import math as _math
    inserted = 0
    with engine.begin() as conn:
        for r in rows:
            try:
                sp = conn.begin_nested()
                conn.execute(text("""
                    INSERT INTO visit_form (ticket_id, cs_id, technician_name, employee_code,
                        customer_name, site_name, creation_date, visit_date, ticket_status,
                        site_status, inactive_reason, dismantle_material, actual_problem,
                        action_taken, problem_solved, reason_not_solved, action_to_be_taken,
                        nearest_police_station, smps_input, hooter, continuous_recording_days,
                        pm_done, two_way_working, smoke_sensor_working)
                    VALUES (:ticket_id, :cs_id, :technician_name, :employee_code,
                        :customer_name, :site_name, :creation_date, :visit_date, :ticket_status,
                        :site_status, :inactive_reason, :dismantle_material, :actual_problem,
                        :action_taken, :problem_solved, :reason_not_solved, :action_to_be_taken,
                        :nearest_police_station, :smps_input, :hooter, :continuous_recording_days,
                        :pm_done, :two_way_working, :smoke_sensor_working)
                    ON CONFLICT (ticket_id, visit_date, employee_code) DO NOTHING
                """), r)
                sp.commit(); inserted += 1
            except Exception as e:
                sp.rollback(); log.warning(f"Skip visit_form {r['ticket_id']}: {e}")
    log.info(f"Visit Form: {inserted} rows inserted")
    return inserted


def load_service_area_master(df, engine):
    """Load service_area_master — periodic full replace."""
    log.info("Loading Service Area Master...")
    rows = []
    seen = set()
    for _, row in df.iterrows():
        sac = safe_str(row.get('Service Area Code', row.get('service_area_code', '')))
        if not sac or sac in seen: continue
        seen.add(sac)
        rows.append({
            'service_area_code': sac,
            'service_area_name': safe_str(row.get('Service Area Name', row.get('service_area_name', ''))),
        })
    if not rows: return 0
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM service_area_master"))
        pd.DataFrame(rows).to_sql('service_area_master', conn, if_exists='append', index=False, method='multi', chunksize=500)
    log.info(f"Service Area Master: {len(rows)} rows loaded")
    return len(rows)

# ══════════════════════════════════════════════════════════
# FRAUD DETECTION
# ══════════════════════════════════════════════════════════

def run_fraud_detection(engine, analysis_date):
    log.info(f"Running fraud detection for {analysis_date}...")
    flags = []
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fraud_flag WHERE flag_date = :d"), {"d": analysis_date})
    try:
        flags += _fv_rules(engine, analysis_date)
        flags += _pattern_1(engine, analysis_date)
        flags += _pattern_2(engine, analysis_date)
        flags += _pattern_3(engine, analysis_date)
        flags += _pattern_7(engine, analysis_date)
        if flags:
            with engine.begin() as conn:
                for f in flags:
                    try:
                        conn.execute(text("""
                            INSERT INTO fraud_flag
                              (flag_date,employee_id,employee_code,employee_name,state,ticket_id,cs_id,
                               pattern_type,pattern_id,severity,description,data_evidence,score_impact)
                            VALUES (:fd,:ei,:ei,:en,:st,:tid,:cs,:pt,:pid,:sv,:desc,cast(:ev as jsonb),:si)
                        """), f)
                    except Exception as e:
                        log.warning(f"Flag insert error: {e}")
        log.info(f"Fraud detection: {len(flags)} flags generated")
    except Exception as e:
        log.error(f"Fraud detection error: {e}", exc_info=True)


def _fv_rules(engine, d):
    flags = []
    with engine.connect() as conn:
        # FV-01: Visit duration < 10 minutes
        for row in conn.execute(text("""
            SELECT vt.ticket_id, vt.cs_id, vt.assigned_employee_code,
                   em.employee_name, em.service_state,
                   EXTRACT(EPOCH FROM (vt.last_visit_out - vt.last_visit_in))/60 AS mins
            FROM view_ticket vt
            JOIN engineer_master em ON em.employee_code = vt.assigned_employee_code
            WHERE vt.ticket_assigned_type='ENGINEER'
              AND vt.last_visit_in IS NOT NULL AND vt.last_visit_out IS NOT NULL
              AND vt.last_visit_out > vt.last_visit_in
              AND EXTRACT(EPOCH FROM (vt.last_visit_out - vt.last_visit_in))/60 < 10
        """)).fetchall():
            flags.append({'fd':d,'ei':row.assigned_employee_code,'en':row.employee_name,'st':row.service_state,
                'tid':row.ticket_id,'cs':row.cs_id,'pt':'FV','pid':'FV-01','sv':'HIGH',
                'desc':f"Zero-duration visit: {round(float(row.mins or 0),1)} mins",
                'ev':json.dumps({'duration_mins':round(float(row.mins or 0),1)}),'si':-2.0})

        # FV-03: Ticket opened and closed same day, lifecycle < 60 mins
        for row in conn.execute(text("""
            SELECT vt.ticket_id, vt.cs_id, vt.assigned_employee_code,
                   em.employee_name, em.service_state,
                   EXTRACT(EPOCH FROM (vt.ticket_closed_datetime - vt.create_datetime))/60 AS mins
            FROM view_ticket vt
            JOIN engineer_master em ON em.employee_code = vt.assigned_employee_code
            WHERE vt.ticket_status IN ('CLOSED','COMPLETED')
              AND DATE(vt.create_datetime) = DATE(vt.ticket_closed_datetime)
              AND vt.ticket_closed_datetime IS NOT NULL AND vt.create_datetime IS NOT NULL
              AND EXTRACT(EPOCH FROM (vt.ticket_closed_datetime - vt.create_datetime))/60 < 60
        """)).fetchall():
            flags.append({'fd':d,'ei':row.assigned_employee_code,'en':row.employee_name,'st':row.service_state,
                'tid':row.ticket_id,'cs':row.cs_id,'pt':'FV','pid':'FV-03','sv':'HIGH',
                'desc':f"Instant lifecycle: {round(float(row.mins or 0),1)} mins",
                'ev':json.dumps({'lifecycle_mins':round(float(row.mins or 0),1)}),'si':-2.0})

        # FV-04: Ticket closed but no visit timestamp
        for row in conn.execute(text("""
            SELECT vt.ticket_id, vt.cs_id, vt.assigned_employee_code,
                   em.employee_name, em.service_state
            FROM view_ticket vt
            JOIN engineer_master em ON em.employee_code = vt.assigned_employee_code
            WHERE vt.ticket_status = 'CLOSED'
              AND vt.last_visit_in IS NULL
              AND vt.ticket_assigned_type='ENGINEER'
              AND vt.assigned_employee_code != ''
        """)).fetchall():
            flags.append({'fd':d,'ei':row.assigned_employee_code,'en':row.employee_name,'st':row.service_state,
                'tid':row.ticket_id,'cs':row.cs_id,'pt':'FV','pid':'FV-04','sv':'HIGH',
                'desc':'Ticket closed but no visit timestamp',
                'ev':json.dumps({}),'si':-2.0})

        # FV-06: Ticket closed on a day engineer had no attendance
        for row in conn.execute(text("""
            SELECT vt.ticket_id, vt.cs_id, vt.assigned_employee_code,
                   em.employee_name, em.service_state,
                   DATE(vt.ticket_closed_datetime) AS cd
            FROM view_ticket vt
            JOIN engineer_master em ON em.employee_code = vt.assigned_employee_code
            WHERE vt.ticket_status = 'CLOSED'
              AND vt.ticket_closed_datetime IS NOT NULL
              AND vt.assigned_employee_code != ''
              AND NOT EXISTS (
                SELECT 1 FROM attendance_data a
                WHERE a.employee_id = vt.assigned_employee_code
                  AND a.attendance_date = DATE(vt.ticket_closed_datetime)
                  AND a.attendance_status_derived IN ('ON TIME','LATE')
              )
        """)).fetchall():
            flags.append({'fd':d,'ei':row.assigned_employee_code,'en':row.employee_name,'st':row.service_state,
                'tid':row.ticket_id,'cs':row.cs_id,'pt':'FV','pid':'FV-06','sv':'HIGH',
                'desc':f"Ticket closed on {row.cd} but engineer not present",
                'ev':json.dumps({'close_date':str(row.cd)}),'si':-2.0})
    return flags


def _pattern_1(engine, d):
    """P1: One-visit day — present but ≤1 visit while area has ≥3 aging open tickets."""
    flags = []
    with engine.connect() as conn:
        rows = conn.execute(text("""
            WITH dv AS (
                SELECT assigned_employee_code, COUNT(*) AS vc
                FROM view_ticket
                WHERE last_visit_in IS NOT NULL AND DATE(last_visit_in) = :d
                GROUP BY assigned_employee_code
            ),
            pt AS (
                SELECT a.employee_id, em.service_state, em.service_area_code, em.employee_name
                FROM attendance_data a
                JOIN engineer_master em ON em.employee_code = a.employee_id
                WHERE a.attendance_date = :d
                  AND a.attendance_status_derived IN ('ON TIME','LATE')
            ),
            ab AS (
                SELECT service_area_code, COUNT(*) AS oa
                FROM view_ticket
                WHERE ticket_status = 'OPEN' AND aging_days >= 5
                GROUP BY service_area_code
            ),
            sa AS (
                SELECT pt.service_state, AVG(COALESCE(dv.vc, 0)) AS av
                FROM pt LEFT JOIN dv ON dv.assigned_employee_code = pt.employee_id
                GROUP BY pt.service_state
            )
            SELECT pt.employee_id, pt.employee_name, pt.service_state, pt.service_area_code,
                   COALESCE(dv.vc, 0) AS visits,
                   COALESCE(ab.oa, 0) AS backlog,
                   COALESCE(sa.av, 0) AS avg_v
            FROM pt
            LEFT JOIN dv ON dv.assigned_employee_code = pt.employee_id
            LEFT JOIN ab ON ab.service_area_code = pt.service_area_code
            LEFT JOIN sa ON sa.service_state = pt.service_state
            WHERE COALESCE(dv.vc, 0) <= 1 AND COALESCE(ab.oa, 0) >= 3
        """), {"d": d}).fetchall()
        for r in rows:
            v=int(r.visits or 0); b=int(r.backlog or 0); av=float(r.avg_v or 0)
            if v==1 and b>=5 and av>3 and v<av*0.4: sv,si='CRITICAL',-7.0
            elif v==1 and b>=5: sv,si='HIGH',-4.0
            else: sv,si='MEDIUM',-2.0
            flags.append({'fd':d,'ei':r.employee_id,'en':r.employee_name,'st':r.service_state,
                'tid':None,'cs':None,'pt':'PATTERN','pid':'P1','sv':sv,
                'desc':f"One-visit day: {v} visit(s), {b} OPEN aging tickets, state avg {round(av,1)}",
                'ev':json.dumps({'visits':v,'area_backlog':b,'state_avg_visits':round(av,1)}),'si':si})
    return flags


def _pattern_2(engine, d):
    """P2: Same-day open+close with long offline lag."""
    flags = []
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT vt.ticket_id, vt.cs_id, vt.assigned_employee_code,
                   em.employee_name, em.service_state,
                   EXTRACT(EPOCH FROM (vt.ticket_closed_datetime - vt.create_datetime))/60 AS speed,
                   EXTRACT(DAY FROM (vt.create_datetime - odm.offline_datetime)) AS lag
            FROM view_ticket vt
            JOIN engineer_master em ON em.employee_code = vt.assigned_employee_code
            LEFT JOIN (
                SELECT cs_id, MIN(offline_datetime) AS offline_datetime
                FROM offline_data_master
                WHERE data_date <= :d
                GROUP BY cs_id
            ) odm ON odm.cs_id = vt.cs_id
            WHERE vt.ticket_status IN ('CLOSED','COMPLETED')
              AND DATE(vt.create_datetime) = DATE(vt.ticket_closed_datetime)
              AND odm.offline_datetime IS NOT NULL
              AND vt.create_datetime > odm.offline_datetime + INTERVAL '2 days'
        """), {"d": d}).fetchall()
        for r in rows:
            lag=float(r.lag or 0); speed=float(r.speed or 0)
            sv='HIGH' if speed<60 else 'MEDIUM'; si=-6.0 if speed<60 else -3.0
            flags.append({'fd':d,'ei':r.assigned_employee_code,'en':r.employee_name,'st':r.service_state,
                'tid':r.ticket_id,'cs':r.cs_id,'pt':'PATTERN','pid':'P2','sv':sv,
                'desc':f"Same-day open+close: {round(lag):.0f}d lag, {round(speed):.0f} mins",
                'ev':json.dumps({'lag':round(lag,1),'speed':round(speed,1)}),'si':si})
    return flags


def _pattern_3(engine, d):
    """P3: PENDING ticket with same unchanged reason for 15+ days."""
    flags = []; old = d - timedelta(days=15)
    with engine.connect() as conn:
        if not conn.execute(text("SELECT COUNT(*) FROM ticket_snapshot WHERE snapshot_date=:d"), {"d":old}).scalar():
            log.info("P3: No 15-day snapshot available"); return flags
        rows = conn.execute(text("""
            SELECT t.ticket_id, t.cs_id, t.assigned_employee_code,
                   em.employee_name, em.service_state,
                   t.ticket_status_reason, t.aging_days
            FROM ticket_snapshot t
            JOIN ticket_snapshot o ON o.ticket_id = t.ticket_id AND o.snapshot_date = :old
            JOIN engineer_master em ON em.employee_code = t.assigned_employee_code
            WHERE t.snapshot_date = :today
              AND t.ticket_status = 'PENDING'
              AND o.ticket_status = 'PENDING'
              AND t.ticket_status_reason = o.ticket_status_reason
              AND t.ticket_status_reason IS NOT NULL
              AND t.ticket_status_reason != ''
              AND t.aging_days > 15
        """), {"today": d, "old": old}).fetchall()
        for r in rows:
            if stock_related(r.ticket_status_reason): continue
            flags.append({'fd':d,'ei':r.assigned_employee_code,'en':r.employee_name,'st':r.service_state,
                'tid':r.ticket_id,'cs':r.cs_id,'pt':'PATTERN','pid':'P3','sv':'HIGH',
                'desc':f"Chronic PENDING {r.aging_days}d, reason unchanged 15+ days",
                'ev':json.dumps({'reason':str(r.ticket_status_reason)[:200],'aging_days':int(r.aging_days or 0)}),'si':-2.0})
    return flags


def _pattern_7(engine, d):
    """P7: Site offline >= 4 days with no active ticket."""
    flags = []
    with engine.connect() as conn:
        latest_date = conn.execute(
            text("SELECT MAX(data_date) FROM offline_data_master")
        ).scalar()
        if not latest_date: return flags
        rows = conn.execute(text("""
            SELECT odm.cs_id, odm.state, odm.aging_days, csm.service_area_code,
                   em.employee_code AS employee_id, em.employee_name
            FROM offline_data_master odm
            LEFT JOIN customer_site_master csm ON csm.cs_id = odm.cs_id
            LEFT JOIN engineer_master em ON em.service_area_code = csm.service_area_code
            WHERE odm.data_date = :latest
              AND odm.aging_days >= 4
              AND odm.segment = 'PSU'
              AND NOT EXISTS (
                SELECT 1 FROM view_ticket vt
                WHERE vt.cs_id = odm.cs_id
                  AND vt.ticket_status IN ('OPEN','PENDING','SENTBACK','COMPLETED')
              )
        """), {"latest": latest_date}).fetchall()
        for r in rows:
            flags.append({'fd':d,'ei':r.employee_id or '','en':r.employee_name or 'Unknown','st':r.state or '',
                'tid':None,'cs':r.cs_id,'pt':'PATTERN','pid':'P7','sv':'HIGH',
                'desc':f"Site offline {r.aging_days}d with no active ticket",
                'ev':json.dumps({'cs_id':r.cs_id,'aging_days':int(r.aging_days or 0)}),'si':0.0})
    return flags

# ══════════════════════════════════════════════════════════
# FACT COMPUTATION
# ══════════════════════════════════════════════════════════

def compute_daily_facts(engine, fact_date):
    log.info(f"Computing daily facts for {fact_date}...")
    # Get latest offline data date
    with engine.connect() as conn:
        latest_offline = conn.execute(
            text("SELECT MAX(data_date) FROM offline_data_master")
        ).scalar() or fact_date

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_state_daily WHERE fact_date=:d"), {"d": fact_date})
        conn.execute(text("""
            INSERT INTO fact_state_daily
              (fact_date, state, total_sites, offline_sites, offline_rate,
               sites_bucket_1_3, sites_bucket_4_7, sites_bucket_8_15, sites_bucket_16_30,
               sites_bucket_31_60, sites_bucket_61_90, sites_bucket_90plus,
               open_tickets, pending_tickets, engineers_present, engineers_total,
               no_ticket_offline_sites)
            SELECT
              :d,
              csm.state,
              COUNT(DISTINCT csm.oracle_site_number),
              COUNT(DISTINCT odm.cs_id),
              ROUND(COUNT(DISTINCT odm.cs_id)::numeric / NULLIF(COUNT(DISTINCT csm.oracle_site_number),0)*100,2),
              COUNT(DISTINCT CASE WHEN odm.bucket='1-3'   THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='4-7'   THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='8-15'  THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='16-30' THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='31-60' THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='61-90' THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN odm.bucket='90+'   THEN odm.cs_id END),
              COUNT(DISTINCT CASE WHEN vt.ticket_status='OPEN'    THEN vt.ticket_id END),
              COUNT(DISTINCT CASE WHEN vt.ticket_status='PENDING' THEN vt.ticket_id END),
              (SELECT COUNT(*) FROM attendance_data a2
               JOIN engineer_master em2 ON em2.employee_code = a2.employee_id
               WHERE a2.attendance_date = :d
                 AND a2.attendance_status_derived IN ('ON TIME','LATE')
                 AND em2.service_state = csm.state),
              (SELECT COUNT(*) FROM engineer_master WHERE service_state = csm.state),
              COUNT(DISTINCT CASE
                WHEN odm.aging_days >= 4
                  AND odm.segment = 'PSU'
                  AND NOT EXISTS (
                    SELECT 1 FROM view_ticket vt2
                    WHERE vt2.cs_id = odm.cs_id
                      AND vt2.ticket_status IN ('OPEN','PENDING','SENTBACK','COMPLETED')
                  )
                THEN odm.cs_id END)
            FROM customer_site_master csm
            LEFT JOIN offline_data_master odm
              ON odm.cs_id = csm.cs_id AND odm.data_date = :latest_offline
            LEFT JOIN view_ticket vt
              ON vt.cs_id = csm.cs_id
            WHERE csm.state IS NOT NULL AND csm.state != ''
            GROUP BY csm.state
        """), {"d": fact_date, "latest_offline": latest_offline})
        log.info("State daily facts computed")

        # Engineer daily facts
        conn.execute(text("DELETE FROM fact_engineer_daily WHERE fact_date=:d"), {"d": fact_date})
        state_avgs = {r.service_state: float(r.av or 0) for r in conn.execute(text("""
            SELECT em.service_state, AVG(dv.vc) AS av
            FROM attendance_data a
            JOIN engineer_master em ON em.employee_code = a.employee_id
            JOIN (
                SELECT assigned_employee_code, COUNT(*) AS vc
                FROM view_ticket
                WHERE last_visit_in IS NOT NULL AND DATE(last_visit_in) = :d
                GROUP BY assigned_employee_code
            ) dv ON dv.assigned_employee_code = a.employee_id
            WHERE a.attendance_date = :d
              AND a.attendance_status_derived IN ('ON TIME','LATE')
            GROUP BY em.service_state
        """), {"d": fact_date}).fetchall()}

        for eng in conn.execute(text("""
            SELECT em.*, a.attendance_status_derived, a.in_datetime
            FROM engineer_master em
            LEFT JOIN attendance_data a
              ON a.employee_id = em.employee_code AND a.attendance_date = :d
        """), {"d": fact_date}).fetchall():
            is_present = eng.attendance_status_derived in ('ON TIME', 'LATE')
            dv = conn.execute(text("""
                SELECT COUNT(*) FROM view_ticket
                WHERE assigned_employee_code = :eid
                  AND last_visit_in IS NOT NULL AND DATE(last_visit_in) = :d
            """), {"d": fact_date, "eid": eng.employee_id}).scalar() or 0
            dc = conn.execute(text("""
                SELECT COUNT(*) FROM view_ticket
                WHERE assigned_employee_code = :eid
                  AND ticket_status IN ('CLOSED','COMPLETED')
                  AND DATE(ticket_closed_datetime) = :d
            """), {"d": fact_date, "eid": eng.employee_id}).scalar() or 0
            ab = conn.execute(text("""
                SELECT COUNT(*) FROM view_ticket vt
                JOIN customer_site_master csm ON csm.cs_id = vt.cs_id
                WHERE csm.service_area_code = :sac
                  AND vt.ticket_status = 'OPEN'
                  AND vt.aging_days >= 5
            """), {"sac": eng.service_area_code}).scalar() or 0
            sa = state_avgs.get(eng.service_state, 0)
            conn.execute(text("""
                INSERT INTO fact_engineer_daily
                  (fact_date, employee_id, employee_name, state, service_area_code,
                   is_present, in_time, attendance_status, daily_visits, daily_closures,
                   is_one_visit_day, area_open_backlog, state_avg_visits, is_productive_day)
                VALUES (:fd,:eid,:en,:st,:sac,:ip,:it,:as_,:dv,:dc,:iovd,:aob,:sav,:ipd)
                ON CONFLICT (fact_date, employee_id) DO UPDATE
                  SET daily_visits=EXCLUDED.daily_visits, is_productive_day=EXCLUDED.is_productive_day
            """), {
                'fd':fact_date,'eid':eng.employee_id,'en':eng.employee_name,'st':eng.service_state,
                'sac':eng.service_area_code,'ip':is_present,'it':eng.in_datetime,
                'as_':eng.attendance_status_derived,'dv':int(dv),'dc':int(dc),
                'iovd': is_present and int(dv)==1 and int(ab)>=3,
                'aob':int(ab),'sav':sa,'ipd': is_present and int(dv)>=max(sa,1),
            })
    log.info("Engineer daily facts computed")


def compute_monthly_facts(engine, year_month):
    log.info(f"Computing monthly facts for {year_month}...")
    ym_start = datetime.strptime(year_month+"-01","%Y-%m-%d").date()
    ym_end = (ym_start.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1)
    latest_offline = None

    with engine.connect() as conn:
        latest_offline = conn.execute(
            text("SELECT MAX(data_date) FROM offline_data_master")
        ).scalar()

    with engine.begin() as conn:
        for eng in conn.execute(text(
            "SELECT employee_code AS employee_id, employee_name, service_state, service_area_code FROM engineer_master"
        )).fetchall():
            att = conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE attendance_date BETWEEN :s AND :e) AS td,
                  COUNT(*) FILTER (WHERE attendance_status_derived IN ('ON TIME','LATE')) AS pd,
                  COUNT(*) FILTER (WHERE attendance_status_derived = 'LATE') AS ld
                FROM attendance_data
                WHERE employee_id=:eid AND attendance_date BETWEEN :s AND :e
            """), {"eid":eng.employee_id,"s":ym_start,"e":ym_end}).fetchone()

            prod = conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE is_productive_day=TRUE) AS p,
                  COUNT(*) FILTER (WHERE is_one_visit_day=TRUE) AS ov
                FROM fact_engineer_daily
                WHERE employee_id=:eid AND fact_date BETWEEN :s AND :e AND is_present=TRUE
            """), {"eid":eng.employee_id,"s":ym_start,"e":ym_end}).fetchone()

            tkts = conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE ticket_status NOT IN ('CANCELLED','REJECTED')) AS tot,
                  COUNT(*) FILTER (WHERE ticket_status='CLOSED') AS cl,
                  COUNT(*) FILTER (WHERE ticket_status='OPEN') AS op,
                  COUNT(*) FILTER (WHERE ticket_status='PENDING') AS pe,
                  COUNT(*) FILTER (WHERE ticket_status='SENTBACK') AS sb,
                  COUNT(*) FILTER (WHERE ticket_status='CANCELLED') AS ca,
                  AVG(CASE WHEN ticket_status='CLOSED' AND ticket_closed_datetime IS NOT NULL AND create_datetime IS NOT NULL
                      THEN EXTRACT(EPOCH FROM (ticket_closed_datetime-create_datetime))/86400 END) AS ar
                FROM view_ticket
                WHERE assigned_employee_code=:eid AND ticket_assigned_type='ENGINEER'
            """), {"eid":eng.employee_id}).fetchone()

            # Sites in engineer's area (no active_status filter per v2.0 §2.8)
            pop = conn.execute(text("""
                SELECT COUNT(*) FROM customer_site_master
                WHERE service_area_code=:sac
            """), {"sac":eng.service_area_code}).scalar() or 0

            uv = conn.execute(text("""
                SELECT COUNT(DISTINCT cs_id) FROM view_ticket
                WHERE assigned_employee_code=:eid AND ticket_status='CLOSED'
                  AND create_date BETWEEN :s AND :e
            """), {"eid":eng.employee_id,"s":ym_start,"e":ym_end}).scalar() or 0

            rep = conn.execute(text("""
                SELECT COUNT(*) FROM (
                  SELECT cs_id FROM view_ticket
                  WHERE assigned_employee_code=:eid AND ticket_status='CLOSED'
                    AND create_date BETWEEN :s AND :e
                  GROUP BY cs_id HAVING COUNT(*)>=2
                ) sub
            """), {"eid":eng.employee_id,"s":ym_start,"e":ym_end}).scalar() or 0

            ff = conn.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE severity IN ('HIGH','CRITICAL')) AS hf,
                  COUNT(*) FILTER (WHERE severity='MEDIUM') AS mf,
                  COUNT(*) FILTER (WHERE severity='CRITICAL') AS cf
                FROM fraud_flag
                WHERE employee_id=:eid AND flag_date BETWEEN :s AND :e
            """), {"eid":eng.employee_id,"s":ym_start,"e":ym_end}).fetchone()

            # Offline rate for engineer's area (uses latest offline data)
            ao = 0
            if latest_offline:
                ao = conn.execute(text("""
                    SELECT ROUND(COUNT(odm.cs_id)::numeric / NULLIF(COUNT(csm.oracle_site_number),0)*100,2)
                    FROM customer_site_master csm
                    LEFT JOIN offline_data_master odm
                      ON odm.cs_id = csm.cs_id AND odm.data_date = :lo
                    WHERE csm.service_area_code = :sac
                """), {"lo":latest_offline,"sac":eng.service_area_code}).scalar() or 0

            cl=int(tkts.cl or 0); tot=int(tkts.tot or 0); sb=int(tkts.sb or 0)
            cr=round(cl/tot*100,2) if tot>0 else 0
            cov=round(int(uv)/int(pop)*100,2) if pop>0 else 0
            rr=round(int(rep)/max(int(uv),1)*100,2)
            pd_=int(att.pd or 0); td=max(int(att.td or 1),1); ld=int(att.ld or 0)
            ar=round(pd_/td*100,2); lr=round(ld/max(pd_,1)*100,2); avg_r=float(tkts.ar or 0)
            hf=int(ff.hf or 0)
            sc=round(cr/100*25,2); scov=round(cov/100*20,2); sr=round(max(0,20-avg_r*2.5),2)
            sao=round(max(0,10-float(ao)*0.4),2); srep=round(max(0,10-rr*0.33),2)
            satt=round(min(7.0,ar*0.05+(100-lr)*0.02),2); sfr=round(max(0,3-hf*1),2)
            comp=round(min(100,sc+scov+sr+sao+srep+satt+sfr),2)
            red=hf>=3 or int(ff.cf or 0)>=2
            if red: comp=min(comp,35.0)
            band=('Exceptional' if comp>=90 else 'Good' if comp>=75 else
                  'Average' if comp>=60 else 'BelowAverage' if comp>=45 else 'Poor')

            conn.execute(text("""
                INSERT INTO fact_engineer_monthly
                  (year_month, employee_id, employee_name, state, service_area_code,
                   present_days, late_days, attendance_rate, late_rate,
                   productive_days, one_visit_days,
                   total_tickets, closed_tickets, open_tickets, pending_tickets,
                   sentback_tickets, cancelled_tickets, closure_rate, sentback_rate,
                   avg_resolution_days, pop_total_sites, unique_sites_visited, coverage_rate,
                   repeat_visit_rate, fv_high_flags, fv_medium_flags, pattern_critical_flags,
                   score_closure, score_coverage, score_resolution, score_area_offline,
                   score_repeat, score_attendance, score_fraud, composite_score,
                   score_band, is_forced_red)
                VALUES
                  (:ym,:eid,:en,:st,:sac,:pd,:ld,:ar,:lr,:prod,:ov,
                   :tt,:ct,:ot,:pt,:sb,:ca,:cr,:sbr,:avg_r,:pop,:uv,:cov,
                   :rr,:hf,:mf,:cf,:sc,:scov,:sr,:sao,:srep,:satt,:sfr,:comp,:band,:red)
                ON CONFLICT (year_month, employee_id) DO UPDATE
                  SET composite_score=EXCLUDED.composite_score, score_band=EXCLUDED.score_band,
                      is_forced_red=EXCLUDED.is_forced_red, closure_rate=EXCLUDED.closure_rate,
                      coverage_rate=EXCLUDED.coverage_rate, present_days=EXCLUDED.present_days,
                      productive_days=EXCLUDED.productive_days
            """), {
                'ym':year_month,'eid':eng.employee_id,'en':eng.employee_name,'st':eng.service_state,
                'sac':eng.service_area_code,'pd':pd_,'ld':ld,'ar':ar,'lr':lr,
                'prod':int(prod.p or 0),'ov':int(prod.ov or 0),
                'tt':tot,'ct':cl,'ot':int(tkts.op or 0),'pt':int(tkts.pe or 0),
                'sb':sb,'ca':int(tkts.ca or 0),'cr':cr,'sbr':round(sb/max(cl+sb,1)*100,2),
                'avg_r':round(avg_r,2),'pop':int(pop),'uv':int(uv),'cov':cov,'rr':rr,
                'hf':hf,'mf':int(ff.mf or 0),'cf':int(ff.cf or 0),
                'sc':sc,'scov':scov,'sr':sr,'sao':float(sao),'srep':srep,
                'satt':satt,'sfr':sfr,'comp':comp,'band':band,'red':red,
            })

        # State monthly facts
        conn.execute(text("DELETE FROM fact_state_monthly WHERE year_month=:ym"), {"ym":year_month})
        conn.execute(text("""
            INSERT INTO fact_state_monthly
              (year_month, state, avg_engineer_score, total_engineers, closure_rate,
               productive_days_rate, fraud_flags_count, state_score, score_band)
            SELECT
              :ym, state,
              AVG(composite_score),
              COUNT(*),
              AVG(closure_rate),
              AVG(productive_days_rate),
              SUM(fv_high_flags + pattern_critical_flags),
              ROUND(AVG(composite_score)
                - SUM(fv_high_flags + pattern_critical_flags) * 0.5, 2),
              CASE
                WHEN AVG(composite_score) >= 90 THEN 'Exceptional'
                WHEN AVG(composite_score) >= 75 THEN 'Good'
                WHEN AVG(composite_score) >= 60 THEN 'Average'
                WHEN AVG(composite_score) >= 45 THEN 'BelowAverage'
                ELSE 'Poor'
              END
            FROM fact_engineer_monthly
            WHERE year_month = :ym
            GROUP BY state
            ON CONFLICT (year_month, state) DO UPDATE
              SET avg_engineer_score=EXCLUDED.avg_engineer_score,
                  state_score=EXCLUDED.state_score, score_band=EXCLUDED.score_band
        """), {"ym": year_month})
    log.info(f"Monthly facts computed for {year_month}")


def generate_smart_insights(engine, insight_date):
    log.info("Generating smart insights...")
    insights = []
    with engine.connect() as conn:
        for r in conn.execute(text("""
            SELECT state, offline_rate FROM fact_state_daily
            WHERE fact_date=:d AND offline_rate>15 AND total_sites>5
            ORDER BY offline_rate DESC
        """), {"d": insight_date}).fetchall():
            insights.append({'insight_date':insight_date,'rule_id':'SI-01','priority':'CRITICAL',
                'insight_text':f"{r.state} has critical offline rate: {r.offline_rate:.1f}%",
                'data_payload':json.dumps({'state':r.state}),'state':r.state})

        # Offline but No Ticket — Super Insight (§5)
        no_tkt = conn.execute(text("""
            SELECT COUNT(*) FROM offline_data_master odm
            JOIN customer_site_master csm ON csm.cs_id = odm.cs_id
            WHERE odm.data_date = (SELECT MAX(data_date) FROM offline_data_master)
              AND odm.segment = 'PSU' AND odm.aging_days > 2
              AND NOT EXISTS (
                SELECT 1 FROM view_ticket vt
                WHERE vt.oracle_site_no = csm.oracle_site_number
                  AND vt.ticket_status IN ('OPEN','PENDING','SENTBACK','COMPLETED')
              )
        """)).scalar() or 0
        if no_tkt:
            insights.append({'insight_date':insight_date,'rule_id':'SI-02','priority':'CRITICAL',
                'insight_text':f"{no_tkt} PSU sites offline >2 days with NO active ticket",
                'data_payload':json.dumps({'count':int(no_tkt)}),'state':None})

        # P1 clustering
        for r in conn.execute(text("""
            SELECT state, COUNT(*) AS cnt FROM fraud_flag
            WHERE flag_date=:d AND pattern_id='P1'
            GROUP BY state HAVING COUNT(*)>=3
        """), {"d": insight_date}).fetchall():
            insights.append({'insight_date':insight_date,'rule_id':'SI-12','priority':'CRITICAL',
                'insight_text':f"{r.cnt} engineers in {r.state} flagged for one-visit days today",
                'data_payload':json.dumps({'state':r.state,'count':int(r.cnt)}),'state':r.state})

        conn.execute(text("DELETE FROM smart_insight WHERE insight_date=:d"), {"d":insight_date})
        for ins in insights:
            conn.execute(text("""
                INSERT INTO smart_insight (insight_date,rule_id,priority,insight_text,data_payload,state)
                VALUES (:insight_date,:rule_id,:priority,:insight_text,cast(:data_payload as jsonb),:state)
            """), ins)
    log.info(f"Smart insights: {len(insights)} generated")

# ══════════════════════════════════════════════════════════
# ASYNC ETL (background tasks per §3.3)
# ══════════════════════════════════════════════════════════

def start_etl_job(engine, upload_date=None) -> str:
    """
    Start ETL as a background thread. Returns job_id immediately.
    Frontend polls /api/upload/status/{job_id} for completion.
    """
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "RUNNING", "result": None, "started_at": datetime.now().isoformat()}

    def _run():
        try:
            success = run_full_etl(engine, upload_date)
            _jobs[job_id]["status"] = "COMPLETE" if success else "FAILED"
            _jobs[job_id]["result"] = {"success": success}
        except Exception as e:
            _jobs[job_id]["status"] = "FAILED"
            _jobs[job_id]["result"] = {"error": str(e)}
            log.error(f"Async ETL job {job_id} failed: {e}", exc_info=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    log.info(f"ETL job {job_id} started in background")
    return job_id


def get_job_status(job_id: str) -> dict:
    return _jobs.get(job_id, {"status": "NOT_FOUND"})


def run_full_etl(engine, upload_date=None) -> bool:
    if not upload_date: upload_date = date.today()
    year_month = upload_date.strftime("%Y-%m")
    log.info(f"=== ETL Starting for {upload_date} ===")
    t0 = datetime.now()
    try:
        run_fraud_detection(engine, upload_date)
        compute_daily_facts(engine, upload_date)
        compute_monthly_facts(engine, year_month)
        generate_smart_insights(engine, upload_date)
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE app_settings SET value=:v, updated_at=NOW() WHERE key='last_etl_run'"
            ), {"v": datetime.now().isoformat()})
        log.info(f"=== ETL Complete in {(datetime.now()-t0).total_seconds():.1f}s ===")
        return True
    except Exception as e:
        log.error(f"ETL failed: {e}", exc_info=True)
        return False
