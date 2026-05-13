-- ============================================================
-- SERVICE ANALYSIS DASHBOARD — DATABASE SCHEMA v2.0
-- PostgreSQL 15+
-- Source of truth: Architecture_v2.docx
-- All table names, column names, join logic per v2.0 spec.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ══════════════════════════════════════════════════════════
-- MASTER TABLES (periodic full replace)
-- ══════════════════════════════════════════════════════════

-- Hub of all joins.
-- Two entry paths:
--   offline_data_master.cs_id  →  customer_site_master.cs_id
--   view_ticket.oracle_site_no →  customer_site_master.oracle_site_no
-- RULE: Do NOT filter on active_status anywhere. Include all sites.
CREATE TABLE IF NOT EXISTS customer_site_master (
    oracle_site_no          VARCHAR(50)  NOT NULL,   -- PK — Service Connect join key
    cs_id                   VARCHAR(50),             -- B2B join key. UNIQUE INDEX below.
    site_name               VARCHAR(500),
    customer_name_full      VARCHAR(255),
    service_area_code       VARCHAR(50),             -- Nullable — do not reject nulls
    state                   VARCHAR(100),
    city                    VARCHAR(100),
    latitude                NUMERIC(10,6),           -- Clamped: abs > 90  → NULL
    longitude               NUMERIC(10,6),           -- Clamped: abs > 180 → NULL
    zone                    VARCHAR(50),
    active_status           VARCHAR(20),             -- Stored but NOT used for any filter
    business_type           VARCHAR(10),
    b2b_code                VARCHAR(100),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (oracle_site_no)
);

-- cs_id is the B2B join key — unique index (nullable rows excluded)
CREATE UNIQUE INDEX IF NOT EXISTS idx_csm_cs_id
    ON customer_site_master(cs_id) WHERE cs_id IS NOT NULL AND cs_id != '';
CREATE INDEX IF NOT EXISTS idx_csm_service_area  ON customer_site_master(service_area_code);
CREATE INDEX IF NOT EXISTS idx_csm_state         ON customer_site_master(state);

-- ─────────────────────────────────────────────────────────
-- Engineers — filter on ingestion: designation='Engineer' AND is_active='YES'
-- Only filtered engineers enter the system.
CREATE TABLE IF NOT EXISTS engineer_master (
    employee_id             VARCHAR(50)  NOT NULL PRIMARY KEY,
    employee_name           VARCHAR(255) NOT NULL,
    service_area_code       VARCHAR(50),
    designation             VARCHAR(100),
    is_active               VARCHAR(10),
    date_of_joining         DATE,
    service_state           VARCHAR(100),
    state                   VARCHAR(100),
    city                    VARCHAR(100),
    region                  VARCHAR(100),
    company_name            VARCHAR(255),
    department              VARCHAR(100),
    address                 TEXT,
    pin_code                VARCHAR(10),
    email                   VARCHAR(255),
    phone                   VARCHAR(20),
    base_latitude           DECIMAL(12,6),
    base_longitude          DECIMAL(12,6),
    reporting_manager_1     VARCHAR(255),
    reporting_manager_2     VARCHAR(255),
    reporting_manager_3     VARCHAR(255),
    asset_type              VARCHAR(100),
    serial_no               VARCHAR(100),
    asset_description       VARCHAR(255),
    sick_leave              DECIMAL(5,1),
    casual_leave            DECIMAL(5,1),
    restricted_leave        DECIMAL(5,1),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eng_service_area  ON engineer_master(service_area_code);
CREATE INDEX IF NOT EXISTS idx_eng_service_state ON engineer_master(service_state);
CREATE INDEX IF NOT EXISTS idx_eng_designation   ON engineer_master(designation);
CREATE INDEX IF NOT EXISTS idx_eng_active        ON engineer_master(is_active);

-- ─────────────────────────────────────────────────────────
-- Service Area Master — maps service_area_code to a human name
CREATE TABLE IF NOT EXISTS service_area_master (
    service_area_code       VARCHAR(50)  NOT NULL PRIMARY KEY,
    service_area_name       VARCHAR(255)
);

-- ══════════════════════════════════════════════════════════
-- HISTORICAL / APPEND TABLES
-- ══════════════════════════════════════════════════════════

-- B2B Offline tracker — APPEND mode, NEVER truncate.
-- Each daily file adds new rows: data_date = date parsed from filename.
-- All historical dates are preserved.
-- cs_id is ALWAYS STRING. Preserve leading zeros. NEVER cast to numeric.
-- Default filters on every query: segment='PSU' AND aging_days>2 AND data_date=MAX(data_date)
CREATE TABLE IF NOT EXISTS offline_data_master (
    id                      SERIAL PRIMARY KEY,
    cs_id                   VARCHAR(50)  NOT NULL,   -- Join key → customer_site_master.cs_id
    site_name               VARCHAR(500),
    b2b_code                VARCHAR(100),
    bank_name_standard      VARCHAR(100),            -- DERIVED — normalised bank name
    aging_days              INTEGER,
    bucket                  VARCHAR(20),             -- 1-3, 4-7, 8-15, 16-30, 31-60, 61-90, 90+
    state                   VARCHAR(100),
    zone                    VARCHAR(20),
    segment                 VARCHAR(10),             -- PSU or PVT
    branch_code             VARCHAR(100),
    atm_id                  VARCHAR(100),            -- DERIVED — Indian Bank ATM ID only
    offline_datetime        TIMESTAMP,
    data_date               DATE NOT NULL,           -- Date of source file (from filename)
    UNIQUE(cs_id, data_date)
);

CREATE INDEX IF NOT EXISTS idx_odm_cs_id         ON offline_data_master(cs_id);
CREATE INDEX IF NOT EXISTS idx_odm_data_date     ON offline_data_master(data_date);
CREATE INDEX IF NOT EXISTS idx_odm_state         ON offline_data_master(state);
CREATE INDEX IF NOT EXISTS idx_odm_bucket        ON offline_data_master(bucket);
CREATE INDEX IF NOT EXISTS idx_odm_segment       ON offline_data_master(segment);
CREATE INDEX IF NOT EXISTS idx_odm_aging         ON offline_data_master(aging_days);

-- ─────────────────────────────────────────────────────────
-- Visit Master — APPEND mode. One row per visit.
-- Use ONLY for visit counts. Do NOT use for duration, distance, or geo.
CREATE TABLE IF NOT EXISTS visit_master (
    visit_id                VARCHAR(100) NOT NULL PRIMARY KEY,
    ticket_id               VARCHAR(100),            -- FK → view_ticket.ticket_id
    employee_id             VARCHAR(50),             -- FK → engineer_master.employee_id
    visit_date              DATE
);

CREATE INDEX IF NOT EXISTS idx_vm_ticket_id      ON visit_master(ticket_id);
CREATE INDEX IF NOT EXISTS idx_vm_employee_id    ON visit_master(employee_id);
CREATE INDEX IF NOT EXISTS idx_vm_visit_date     ON visit_master(visit_date);

-- ─────────────────────────────────────────────────────────
-- Attendance Data — APPEND mode. One row per employee per date.
-- Block re-upload: (employee_id, attendance_date) conflict → skip (ON CONFLICT DO NOTHING).
-- attendance_status_derived is computed on ingestion — do NOT re-derive at query time.
CREATE TABLE IF NOT EXISTS attendance_data (
    id                      SERIAL PRIMARY KEY,
    employee_id             VARCHAR(50)  NOT NULL,   -- Parsed from 'Name (ID)' format
    attendance_date         DATE         NOT NULL,
    in_datetime             TIMESTAMP,               -- NULL means ABSENT
    attendance_status_derived VARCHAR(20),           -- ON TIME / LATE / ABSENT
    service_state           VARCHAR(100),
    UNIQUE(employee_id, attendance_date)
);

CREATE INDEX IF NOT EXISTS idx_ad_employee       ON attendance_data(employee_id);
CREATE INDEX IF NOT EXISTS idx_ad_date           ON attendance_data(attendance_date);
CREATE INDEX IF NOT EXISTS idx_ad_state          ON attendance_data(service_state);
CREATE INDEX IF NOT EXISTS idx_ad_status         ON attendance_data(attendance_status_derived);

-- ══════════════════════════════════════════════════════════
-- DAILY REPLACE TABLE
-- ══════════════════════════════════════════════════════════

-- View Ticket — TRUNCATE + INSERT daily. No historical storage.
-- Filter on insert: assigned_type='ENGINEER' only.
-- If oracle_site_no not in customer_site_master → skip row silently.
-- ticket_status normalisation: SENDBACK/SENT BACK/SEND BACK → SENTBACK on ingestion.
-- Active ticket filter for all queries:
--   assigned_type='ENGINEER' AND ticket_status IN ('OPEN','PENDING','SENTBACK','COMPLETED')
CREATE TABLE IF NOT EXISTS view_ticket (
    ticket_id               VARCHAR(100) NOT NULL PRIMARY KEY,
    oracle_site_no          VARCHAR(50),             -- FK → customer_site_master.oracle_site_no
    cs_id                   VARCHAR(50),             -- Denormalised for convenience
    ticket_status           VARCHAR(30),
    ticket_aging_days       INTEGER,
    ticket_type             VARCHAR(100),
    ticket_sub_type         VARCHAR(100),
    assigned_type           VARCHAR(20),             -- ENGINEER or VENDOR
    assigned_to             VARCHAR(255),            -- 'Name (EMP_ID)' raw format
    assigned_employee_id    VARCHAR(50),             -- DERIVED — parsed from assigned_to
    last_visit_in           TIMESTAMP,
    last_visit_out          TIMESTAMP,
    create_date             DATE,
    create_datetime         TIMESTAMP,
    planned_date            DATE,
    ticket_closed_datetime  TIMESTAMP,
    last_submission_datetime TIMESTAMP,
    ticket_status_reason    TEXT,
    current_approver_name   VARCHAR(255),
    state_name              VARCHAR(100),
    -- enriched from customer_site_master
    service_area_code       VARCHAR(50),
    site_state_master       VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_vt_cs_id          ON view_ticket(cs_id);
CREATE INDEX IF NOT EXISTS idx_vt_oracle_site    ON view_ticket(oracle_site_no);
CREATE INDEX IF NOT EXISTS idx_vt_status         ON view_ticket(ticket_status);
CREATE INDEX IF NOT EXISTS idx_vt_emp_id         ON view_ticket(assigned_employee_id);
CREATE INDEX IF NOT EXISTS idx_vt_aging          ON view_ticket(ticket_aging_days);
CREATE INDEX IF NOT EXISTS idx_vt_create_date    ON view_ticket(create_date);
CREATE INDEX IF NOT EXISTS idx_vt_planned        ON view_ticket(planned_date);
CREATE INDEX IF NOT EXISTS idx_vt_closed         ON view_ticket(ticket_closed_datetime);
CREATE INDEX IF NOT EXISTS idx_vt_sac            ON view_ticket(service_area_code);

-- ══════════════════════════════════════════════════════════
-- TICKET SNAPSHOT (for fraud detection — last 90 days)
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ticket_snapshot (
    id                      SERIAL PRIMARY KEY,
    snapshot_date           DATE         NOT NULL,
    ticket_id               VARCHAR(100) NOT NULL,
    cs_id                   VARCHAR(50),
    ticket_status           VARCHAR(30),
    ticket_status_reason    TEXT,
    planned_date            DATE,
    ticket_aging_days       INTEGER,
    assigned_employee_id    VARCHAR(50),
    last_visit_in           TIMESTAMP,
    UNIQUE(snapshot_date, ticket_id)
);

CREATE INDEX IF NOT EXISTS idx_snap_date         ON ticket_snapshot(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snap_ticket_id    ON ticket_snapshot(ticket_id);
CREATE INDEX IF NOT EXISTS idx_snap_emp          ON ticket_snapshot(assigned_employee_id);
CREATE INDEX IF NOT EXISTS idx_snap_status       ON ticket_snapshot(ticket_status);

-- ══════════════════════════════════════════════════════════
-- PRE-AGGREGATED FACT TABLES (computed post-upload by ETL)
-- Dashboard queries ONLY these — never raw tables directly.
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fact_engineer_daily (
    id                      SERIAL PRIMARY KEY,
    fact_date               DATE         NOT NULL,
    employee_id             VARCHAR(50)  NOT NULL,
    employee_name           VARCHAR(255),
    state                   VARCHAR(100),
    service_area_code       VARCHAR(50),
    -- attendance
    is_present              BOOLEAN,
    in_time                 TIMESTAMP,
    out_time                TIMESTAMP,
    work_hours              DECIMAL(5,2),
    attendance_status       VARCHAR(20),             -- ON TIME / LATE / ABSENT
    -- ticket activity
    daily_visits            INTEGER DEFAULT 0,
    daily_closures          INTEGER DEFAULT 0,
    -- fraud signals
    first_visit_cs_id       VARCHAR(50),
    last_visit_cs_id        VARCHAR(50),
    is_one_visit_day        BOOLEAN,
    area_open_backlog       INTEGER,
    state_avg_visits        DECIMAL(5,2),
    is_productive_day       BOOLEAN,
    UNIQUE(fact_date, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_fed_date          ON fact_engineer_daily(fact_date);
CREATE INDEX IF NOT EXISTS idx_fed_emp           ON fact_engineer_daily(employee_id);
CREATE INDEX IF NOT EXISTS idx_fed_state         ON fact_engineer_daily(state);

-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_engineer_monthly (
    id                      SERIAL PRIMARY KEY,
    year_month              VARCHAR(7)   NOT NULL,
    employee_id             VARCHAR(50)  NOT NULL,
    employee_name           VARCHAR(255),
    state                   VARCHAR(100),
    service_area_code       VARCHAR(50),
    -- attendance
    total_working_days      INTEGER,
    present_days            INTEGER,
    absent_days             INTEGER,
    late_days               INTEGER,
    attendance_rate         DECIMAL(5,2),
    late_rate               DECIMAL(5,2),
    productive_days         INTEGER,
    productive_days_rate    DECIMAL(5,2),
    one_visit_days          INTEGER,
    -- ticket performance
    total_tickets           INTEGER,
    closed_tickets          INTEGER,
    open_tickets            INTEGER,
    pending_tickets         INTEGER,
    sentback_tickets        INTEGER,
    cancelled_tickets       INTEGER,
    closure_rate            DECIMAL(5,2),
    sentback_rate           DECIMAL(5,2),
    avg_resolution_days     DECIMAL(5,2),
    -- coverage
    pop_total_sites         INTEGER,
    unique_sites_visited    INTEGER,
    coverage_rate           DECIMAL(5,2),
    -- quality
    repeat_visit_rate       DECIMAL(5,2),
    total_visits            INTEGER,
    -- fraud flags
    fv_high_flags           INTEGER DEFAULT 0,
    fv_medium_flags         INTEGER DEFAULT 0,
    pattern_critical_flags  INTEGER DEFAULT 0,
    -- composite score
    score_closure           DECIMAL(5,2),
    score_coverage          DECIMAL(5,2),
    score_resolution        DECIMAL(5,2),
    score_area_offline      DECIMAL(5,2),
    score_repeat            DECIMAL(5,2),
    score_attendance        DECIMAL(5,2),
    score_fraud             DECIMAL(5,2),
    composite_score         DECIMAL(5,2),
    score_band              VARCHAR(20),
    is_forced_red           BOOLEAN DEFAULT FALSE,
    calculated_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE(year_month, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_fem_ym            ON fact_engineer_monthly(year_month);
CREATE INDEX IF NOT EXISTS idx_fem_emp           ON fact_engineer_monthly(employee_id);
CREATE INDEX IF NOT EXISTS idx_fem_state         ON fact_engineer_monthly(state);
CREATE INDEX IF NOT EXISTS idx_fem_score         ON fact_engineer_monthly(composite_score);

-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_state_daily (
    id                      SERIAL PRIMARY KEY,
    fact_date               DATE         NOT NULL,
    state                   VARCHAR(100) NOT NULL,
    total_sites             INTEGER,
    offline_sites           INTEGER,
    offline_rate            DECIMAL(5,2),
    sites_bucket_1_3        INTEGER DEFAULT 0,
    sites_bucket_4_7        INTEGER DEFAULT 0,
    sites_bucket_8_15       INTEGER DEFAULT 0,
    sites_bucket_16_30      INTEGER DEFAULT 0,
    sites_bucket_31_60      INTEGER DEFAULT 0,
    sites_bucket_61_90      INTEGER DEFAULT 0,
    sites_bucket_90plus     INTEGER DEFAULT 0,
    open_tickets            INTEGER DEFAULT 0,
    pending_tickets         INTEGER DEFAULT 0,
    closed_tickets_mtd      INTEGER DEFAULT 0,
    engineers_present       INTEGER DEFAULT 0,
    engineers_total         INTEGER DEFAULT 0,
    no_ticket_offline_sites INTEGER DEFAULT 0,
    UNIQUE(fact_date, state)
);

CREATE INDEX IF NOT EXISTS idx_fsd_date          ON fact_state_daily(fact_date);
CREATE INDEX IF NOT EXISTS idx_fsd_state         ON fact_state_daily(state);

-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_state_monthly (
    id                      SERIAL PRIMARY KEY,
    year_month              VARCHAR(7)   NOT NULL,
    state                   VARCHAR(100) NOT NULL,
    avg_engineer_score      DECIMAL(5,2),
    total_engineers         INTEGER,
    total_sites             INTEGER,
    avg_offline_rate        DECIMAL(5,2),
    sites_offline_30plus    INTEGER,
    closure_rate            DECIMAL(5,2),
    avg_resolution_days     DECIMAL(5,2),
    productive_days_rate    DECIMAL(5,2),
    fraud_flags_count       INTEGER DEFAULT 0,
    state_score             DECIMAL(5,2),
    score_band              VARCHAR(20),
    calculated_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE(year_month, state)
);

CREATE INDEX IF NOT EXISTS idx_fsm_ym            ON fact_state_monthly(year_month);
CREATE INDEX IF NOT EXISTS idx_fsm_state         ON fact_state_monthly(state);
CREATE INDEX IF NOT EXISTS idx_fsm_score         ON fact_state_monthly(state_score);

-- ══════════════════════════════════════════════════════════
-- FRAUD FLAGS
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS fraud_flag (
    id                      SERIAL PRIMARY KEY,
    flag_date               DATE         NOT NULL,
    employee_id             VARCHAR(50),
    employee_name           VARCHAR(255),
    state                   VARCHAR(100),
    ticket_id               VARCHAR(100),
    cs_id                   VARCHAR(50),
    pattern_type            VARCHAR(20),  -- FV or PATTERN
    pattern_id              VARCHAR(10),  -- FV-01, P1, P3 etc
    severity                VARCHAR(10),  -- CRITICAL, HIGH, MEDIUM
    description             TEXT,
    data_evidence           JSONB,
    review_status           VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, VALID, CONFIRMED_FAKE
    reviewed_by             VARCHAR(100),
    reviewed_at             TIMESTAMP,
    review_note             TEXT,
    score_impact            DECIMAL(5,2),
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ff_emp            ON fraud_flag(employee_id);
CREATE INDEX IF NOT EXISTS idx_ff_date           ON fraud_flag(flag_date);
CREATE INDEX IF NOT EXISTS idx_ff_state          ON fraud_flag(state);
CREATE INDEX IF NOT EXISTS idx_ff_pattern        ON fraud_flag(pattern_id);
CREATE INDEX IF NOT EXISTS idx_ff_severity       ON fraud_flag(severity);
CREATE INDEX IF NOT EXISTS idx_ff_status         ON fraud_flag(review_status);

-- ══════════════════════════════════════════════════════════
-- SMART INSIGHTS
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS smart_insight (
    id                      SERIAL PRIMARY KEY,
    insight_date            DATE         NOT NULL,
    rule_id                 VARCHAR(10)  NOT NULL,
    priority                VARCHAR(10),  -- CRITICAL, WARNING, INFO
    insight_text            TEXT,
    data_payload            JSONB,
    state                   VARCHAR(100),
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_si_date           ON smart_insight(insight_date);
CREATE INDEX IF NOT EXISTS idx_si_priority       ON smart_insight(priority);
CREATE INDEX IF NOT EXISTS idx_si_active         ON smart_insight(is_active);

-- ══════════════════════════════════════════════════════════
-- UPLOAD AUDIT LOG
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS upload_log (
    id                      SERIAL PRIMARY KEY,
    file_type               VARCHAR(30)  NOT NULL,
    original_filename       VARCHAR(500),
    upload_datetime         TIMESTAMP    DEFAULT NOW(),
    uploaded_by             VARCHAR(100),
    row_count               INTEGER,
    validation_status       VARCHAR(20),  -- SUCCESS, FAILED, WARNING
    validation_errors       JSONB,
    validation_warnings     JSONB,
    etl_status              VARCHAR(20),  -- PENDING, RUNNING, COMPLETE, FAILED
    etl_started_at          TIMESTAMP,
    etl_completed_at        TIMESTAMP,
    etl_errors              TEXT,
    job_id                  VARCHAR(50),  -- for async ETL polling
    upload_date             DATE DEFAULT CURRENT_DATE
);

-- ══════════════════════════════════════════════════════════
-- USER & SETTINGS
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS app_user (
    id                      SERIAL PRIMARY KEY,
    username                VARCHAR(100) UNIQUE NOT NULL,
    password_hash           VARCHAR(255) NOT NULL,
    role                    VARCHAR(20)  NOT NULL CHECK (role IN ('ops_manager','state_manager','admin')),
    state_code              VARCHAR(100),
    is_active               BOOLEAN DEFAULT TRUE,
    force_password_change   BOOLEAN DEFAULT TRUE,
    last_login              TIMESTAMP,
    created_at              TIMESTAMP DEFAULT NOW(),
    created_by              VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key                     VARCHAR(100) PRIMARY KEY,
    value                   TEXT,
    description             TEXT,
    updated_at              TIMESTAMP DEFAULT NOW()
);

INSERT INTO app_settings (key, value, description) VALUES
    ('working_days',            'MON-SAT',   'Working days for attendance calculation'),
    ('late_threshold',          '10:00',     'Time after which punch-in is LATE (HH:MM). Per v2.0 spec: 10:00 AM'),
    ('productive_days_method',  'STATE_AVG', 'Productive day threshold: STATE_AVG or FIXED'),
    ('productive_days_fixed',   '3',         'Fixed visit count for productive day (if method=FIXED)'),
    ('snapshot_retention_days', '90',        'Days to retain daily ticket snapshots'),
    ('last_upload_b2b',         '',          'Timestamp of last B2B Offline upload'),
    ('last_upload_ticket',      '',          'Timestamp of last View Ticket upload'),
    ('last_upload_attendance',  '',          'Timestamp of last Attendance upload'),
    ('last_etl_run',            '',          'Timestamp of last ETL run completion')
ON CONFLICT (key) DO NOTHING;

-- Default admin user (password: Admin@1234)
INSERT INTO app_user (username, password_hash, role, state_code, force_password_change)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGiIoSA6GqDOwAzFtM1gGkXnrXi', 'admin', NULL, TRUE)
ON CONFLICT (username) DO NOTHING;
