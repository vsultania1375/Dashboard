# VProtect Dashboard - Implementation Guide for Claude Code

**Version:** 1.0  
**Date:** May 13, 2026  
**Target AI:** Claude Code / Claude Sonnet  
**Purpose:** Step-by-step implementation roadmap with clear deliverables

---

## QUICK START

**Before Running:** Read these three documents in order:
1. ✅ `DATABASE_LOGIC.md` - Understand the data model, schemas, and ETL
2. ✅ `DASHBOARD_SPECIFICATION.md` - Understand the UI, filters, and metrics
3. ⬅️ `IMPLEMENTATION_GUIDE.md` (this file) - Build the application

**Tech Stack:**
- **Backend:** FastAPI + PostgreSQL
- **Frontend:** React 18 + TypeScript + Tailwind CSS
- **Deployment:** Docker Compose
- **Charts:** Recharts (or Chart.js)
- **Dates:** date-fns or Day.js

---

## PHASE 1: DATABASE & BACKEND (Week 1-2)

### Phase 1.1: Database Setup

**Deliverable:** PostgreSQL database with all tables, indexes, and sample data

**Steps:**

1. **Create PostgreSQL Database**
   ```bash
   # In docker-compose.yml, ensure PostgreSQL service is running
   docker-compose up postgres
   ```

2. **Execute Schema Creation (see DATABASE_LOGIC.md Section 2)**
   - Copy all CREATE TABLE statements from DATABASE_LOGIC.md
   - Create file: `backend/database/schema.sql`
   - Execute: `psql -U postgres -d vprotect < schema.sql`
   - Verify: `\dt` (list all tables)

3. **Create Indexes (Performance)**
   - Copy all CREATE INDEX statements
   - Create file: `backend/database/indexes.sql`
   - Execute: `psql -U postgres -d vprotect < indexes.sql`

4. **Load Sample Data**
   - Create sample CSV/SQL files for testing:
     - `backend/database/seed_engineer_master.sql` (50 engineers)
     - `backend/database/seed_offline_data.sql` (1000 offline sites)
     - `backend/database/seed_view_ticket.sql` (5000 tickets)
     - `backend/database/seed_attendance_log.sql` (1000 attendance records)
     - `backend/database/seed_visit_log.sql` (5000 visits)
   - Load: `psql -U postgres -d vprotect < seed_*.sql`
   - Query to verify: `SELECT COUNT(*) FROM engineer_master;`

**Acceptance Criteria:**
- [ ] All 8 tables created successfully
- [ ] All indexes created
- [ ] Sample data loaded (at least 50 engineers, 1000 sites)
- [ ] Foreign key relationships intact
- [ ] Zero referential integrity errors

---

### Phase 1.2: Backend API - Core Endpoints

**Deliverable:** FastAPI application with data access layer and core endpoints

**Directory Structure:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app init
│   ├── config.py               # Database config
│   ├── models.py               # Pydantic models for request/response
│   ├── database.py             # PostgreSQL connection
│   ├── database/
│   │   ├── __init__.py
│   │   ├── schema.sql          # Table creation
│   │   ├── indexes.sql         # Index creation
│   │   └── seed_*.sql          # Sample data
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── filters.py          # Filter/date range endpoints
│   │   ├── offline.py          # Offline data endpoints
│   │   ├── engineers.py        # Engineer performance endpoints
│   │   └── export.py           # Export endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── offline_service.py  # Offline data business logic
│   │   ├── engineer_service.py # Engineer metrics calculation
│   │   └── export_service.py   # Excel/CSV export
│   └── utils/
│       ├── __init__.py
│       ├── calculations.py     # Metric calculations
│       ├── date_helpers.py     # Date/time helpers
│       └── cache.py            # Caching layer
├── requirements.txt
└── docker-compose.yml
```

**Step 1: Database Connection Layer**
```python
# backend/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:password@postgres:5432/vprotect"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: Pydantic Models (Request/Response)**
```python
# backend/app/models.py

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

class FilterRequest(BaseModel):
    from_date: date
    to_date: date
    state: str = "All"  # "All" or specific state name
    service_area: Optional[str] = None
    show_active_only: bool = True

class EngineerMetrics(BaseModel):
    employee_id: int
    employee_name: str
    service_area: str
    att_days: int
    working_days: int
    att_percent: float
    prod_days: int
    zero_prod_days: int
    total_visits: int
    distinct_sites: int
    repeat_rate: float
    closed: int
    open: int
    pending: int
    completed: int
    offline_sites: int

class OfflineDistribution(BaseModel):
    bucket: str
    count: int
    percent: float

class EngineerPerformanceResponse(BaseModel):
    success: bool
    data: dict  # {summary, engineers, footer}
    cached: bool
    generated_at: datetime

class OfflineDistributionResponse(BaseModel):
    success: bool
    data: dict  # {summary, distribution}
    cached: bool
    generated_at: datetime
```

**Step 3: Core Endpoints**
```python
# backend/app/routes/engineers.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import FilterRequest, EngineerPerformanceResponse
from app.services import engineer_service

router = APIRouter(prefix="/api/engineers", tags=["engineers"])

@router.post("/performance", response_model=EngineerPerformanceResponse)
async def get_engineer_performance(
    filters: FilterRequest,
    db: Session = Depends(get_db)
):
    """
    Get engineer performance report for given filters
    
    Query Parameters (via FilterRequest):
    - from_date: YYYY-MM-DD
    - to_date: YYYY-MM-DD
    - state: "Tamil Nadu" or "All"
    - show_active_only: true/false
    
    Returns:
    - Engineer metrics table data
    - Summary statistics
    - Footer aggregations
    """
    return await engineer_service.get_engineer_performance(filters, db)

@router.post("/offline-distribution", response_model=OfflineDistributionResponse)
async def get_offline_distribution(
    filters: FilterRequest,
    db: Session = Depends(get_db)
):
    """
    Get offline sites distribution by bucket for chart
    
    Returns:
    - Distribution by offline_bucket
    - Counts and percentages
    """
    return await engineer_service.get_offline_distribution(filters, db)

@router.get("/states")
async def get_available_states(db: Session = Depends(get_db)):
    """
    Get list of all available states
    
    Returns:
    - ["All (PAN India)", "Tamil Nadu", "Karnataka", ...]
    """
    return engineer_service.get_states(db)

@router.get("/service-areas/{state}")
async def get_service_areas_by_state(
    state: str,
    db: Session = Depends(get_db)
):
    """
    Get service areas for a specific state
    
    Returns:
    - ["KA-BNG-001", "KA-BNG-002", ...]
    """
    return engineer_service.get_service_areas(state, db)
```

**Step 4: Business Logic Layer**
```python
# backend/app/services/engineer_service.py

from sqlalchemy.orm import Session
from datetime import date
from app.models import FilterRequest, EngineerMetrics
from app.utils.calculations import (
    calculate_attendance_metrics,
    calculate_productivity_metrics,
    calculate_ticket_metrics,
    get_working_days
)

async def get_engineer_performance(filters: FilterRequest, db: Session):
    """
    Main orchestration: Fetch and calculate engineer metrics
    """
    # 1. Validate filters
    validate_date_range(filters.from_date, filters.to_date)
    
    # 2. Get active engineers (optionally filtered by state)
    engineers = db.query(EngineerMaster).filter(
        EngineerMaster.active_status == 'YES',
        EngineerMaster.designation == 'Engineer'
    )
    
    if filters.state != "All":
        engineers = engineers.filter(EngineerMaster.service_state == filters.state)
    
    engineers = engineers.all()
    
    # 3. Calculate metrics for each engineer
    engineer_metrics = []
    for engineer in engineers:
        metrics = calculate_engineer_metrics(
            engineer.employee_id,
            filters.from_date,
            filters.to_date,
            db
        )
        engineer_metrics.append(metrics)
    
    # 4. Calculate footer (totals/averages)
    footer = calculate_state_summary(
        engineer_metrics,
        filters.state,
        filters.from_date,
        filters.to_date,
        db
    )
    
    # 5. Sort by Att. % descending
    engineer_metrics.sort(key=lambda x: x['att_percent'], reverse=True)
    
    return {
        "success": True,
        "data": {
            "summary": {
                "total_engineers": len(engineers),
                "date_range": f"{filters.from_date} to {filters.to_date}",
                "state": filters.state
            },
            "engineers": engineer_metrics,
            "footer": footer
        },
        "cached": False,
        "generated_at": datetime.now()
    }

def calculate_engineer_metrics(employee_id, from_date, to_date, db):
    """
    Calculate ALL metrics for single engineer
    
    Returns dict with all columns for EngineerMetrics
    """
    # Attendance Days
    att_days = db.query(func.count(distinct(AttendanceLog.attendance_date))).filter(
        AttendanceLog.employee_id == employee_id,
        AttendanceLog.attendance_date.between(from_date, to_date),
        AttendanceLog.attendance_status.in_(['OnTime', 'Late'])
    ).scalar() or 0
    
    # Working Days
    working_days = get_working_days(from_date, to_date)
    
    # Attendance %
    att_percent = (att_days / working_days * 100) if working_days > 0 else 0
    
    # Productive Days
    prod_days = db.query(func.count(distinct(VisitLog.visit_date))).filter(
        VisitLog.employee_id == employee_id,
        VisitLog.visit_date.between(from_date, to_date)
    ).scalar() or 0
    
    # Zero Prod Days
    zero_prod_days = att_days - prod_days
    
    # Total Visits
    total_visits = db.query(func.count(VisitLog.visit_id)).filter(
        VisitLog.employee_id == employee_id,
        VisitLog.visit_date.between(from_date, to_date)
    ).scalar() or 0
    
    # Distinct Sites (via ticket→site relationship)
    distinct_sites = db.query(func.count(distinct(ViewTicket.oracle_site_no))).join(
        VisitLog, VisitLog.ticket_id == ViewTicket.ticket_id
    ).filter(
        VisitLog.employee_id == employee_id,
        VisitLog.visit_date.between(from_date, to_date)
    ).scalar() or 0
    
    # Repeat Rate
    repeat_rate = (total_visits / distinct_sites) if distinct_sites > 0 else 0
    
    # Ticket Status Counts
    ticket_statuses = {
        'closed': db.query(func.count()).filter(ViewTicket.employee_id == employee_id, ViewTicket.ticket_status == 'CLOSED').scalar(),
        'open': db.query(func.count()).filter(ViewTicket.employee_id == employee_id, ViewTicket.ticket_status == 'OPEN').scalar(),
        'pending': db.query(func.count()).filter(ViewTicket.employee_id == employee_id, ViewTicket.ticket_status.in_(['PENDING', 'SENTBACK'])).scalar(),
        'completed': db.query(func.count()).filter(ViewTicket.employee_id == employee_id, ViewTicket.ticket_status == 'COMPLETED').scalar(),
    }
    
    # Offline Sites in service area
    engineer = db.query(EngineerMaster).filter(EngineerMaster.employee_id == employee_id).first()
    offline_sites = db.query(func.count(distinct(OfflineData.cs_id))).join(
        CustomerSiteMaster, OfflineData.cs_id == CustomerSiteMaster.cs_id
    ).filter(
        CustomerSiteMaster.service_area_code == engineer.service_area_code,
        OfflineData.aging_days > 3,
        OfflineData.segment == 'PSU',
        OfflineData.data_date == date.today()
    ).scalar() or 0
    
    return {
        'employee_id': employee_id,
        'employee_name': engineer.employee_name,
        'service_area': engineer.service_area_code,
        'att_days': att_days,
        'working_days': working_days,
        'att_percent': round(att_percent, 2),
        'prod_days': prod_days,
        'zero_prod_days': zero_prod_days,
        'total_visits': total_visits,
        'distinct_sites': distinct_sites,
        'repeat_rate': round(repeat_rate, 2),
        'closed': ticket_statuses['closed'],
        'open': ticket_statuses['open'],
        'pending': ticket_statuses['pending'],
        'completed': ticket_statuses['completed'],
        'offline_sites': offline_sites
    }
```

**Acceptance Criteria:**
- [ ] All endpoints return correct JSON structure
- [ ] Database queries execute without errors
- [ ] Sample data queries return realistic results
- [ ] Response times < 2s for state-level queries
- [ ] Caching mechanism functional

---

### Phase 1.3: ETL Pipeline

**Deliverable:** Data upload and transformation pipeline

**Steps:**

1. **Create File Upload Endpoint**
```python
# backend/app/routes/upload.py

from fastapi import APIRouter, UploadFile, File
from app.services import etl_service

router = APIRouter(prefix="/api/upload", tags=["upload"])

@router.post("/offline-data")
async def upload_offline_data(file: UploadFile = File(...)):
    """
    Upload B2B_Offline_DD-MM-YYYY.xlsx
    
    Processing:
    1. Validate file format (.xlsx)
    2. Extract B2B sheet
    3. Filter: segment = 'PSU'
    4. Transform dates and data types
    5. APPEND to offline_data table
    """
    return await etl_service.process_offline_data(file)

@router.post("/view-ticket")
async def upload_view_ticket(file: UploadFile = File(...)):
    """
    Upload view_ticket.xlsx
    
    Processing:
    1. Validate file format
    2. Filter: assigned_type = 'Engineer'
    3. Parse assigned_to column
    4. FULL REPLACE previous data
    """
    return await etl_service.process_view_ticket(file)

@router.post("/attendance")
async def upload_attendance(file: UploadFile = File(...)):
    """
    Upload Attendance_Data.xlsx
    
    Processing:
    1. Recalculate attendance_status from in_datetime
    2. APPEND to attendance_log
    """
    return await etl_service.process_attendance(file)

@router.post("/visits")
async def upload_visits(file: UploadFile = File(...)):
    """
    Upload visit_data.xlsx
    
    Processing:
    1. APPEND to visit_log (check for duplicates)
    """
    return await etl_service.process_visits(file)
```

2. **Create ETL Service**
```python
# backend/app/services/etl_service.py

from fastapi import UploadFile
import pandas as pd
from sqlalchemy.orm import Session
import openpyxl
from datetime import datetime

async def process_offline_data(file: UploadFile, db: Session):
    """
    ETL for offline data
    """
    try:
        # 1. Read Excel file
        df = pd.read_excel(file.file, sheet_name="B2B")
        
        # 2. Validate columns exist
        required_cols = ['B2B Code', 'site_name', 'cs_no', 'aging_days', 
                        'offline_bucket', 'state', 'segment']
        if not all(col in df.columns for col in required_cols):
            return {"success": False, "error": "Missing required columns"}
        
        # 3. Filter PSU only
        df = df[df['segment'] == 'PSU']
        
        # 4. Transform data types
        df['cs_id'] = df['cs_no'].astype(str)  # VARCHAR
        df['alarm_date'] = pd.to_datetime(df.get('alarm_date', None), format='%d-%m-%Y')
        df['offline_datetime'] = pd.to_datetime(df.get('Offline Date & Time', None), 
                                               format='%d-%m-%Y %H:%M')
        df['data_date'] = pd.Timestamp.today().date()
        
        # 5. Rename columns to match DB schema
        df = df.rename(columns={
            'B2B Code': 'b2b_code',
            'site_name': 'site_name',
            'cs_no': 'cs_id',
            'aging_days': 'aging_days',
            'offline_bucket': 'offline_bucket',
            'Branch Code': 'branch_code',
            'State': 'state',
            'Zone': 'zone',
            'segment': 'segment'
        })
        
        # 6. Quality checks
        if df[['site_name', 'cs_id', 'state']].isnull().any().any():
            return {"success": False, "error": "NULL in critical columns"}
        
        # 7. Insert to database (APPEND mode)
        for _, row in df.iterrows():
            offline_record = OfflineData(
                data_date=row['data_date'],
                alarm_date=row['alarm_date'],
                b2b_code=row['b2b_code'],
                site_name=row['site_name'],
                cs_id=row['cs_id'],
                aging_days=int(row['aging_days']),
                offline_bucket=row['offline_bucket'],
                branch_code=row['branch_code'],
                state=row['state'],
                offline_datetime=row['offline_datetime'],
                zone=row['zone'],
                segment=row['segment']
            )
            db.add(offline_record)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Loaded {len(df)} offline sites",
            "rows_loaded": len(df)
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Acceptance Criteria:**
- [ ] All file upload endpoints functional
- [ ] Data validates before insertion
- [ ] Error messages informative
- [ ] ETL logs tracking (success/failure)
- [ ] Data quality checks passing

---

## PHASE 2: FRONTEND (Week 2-3)

### Phase 2.1: React Setup & Base Layout

**Deliverable:** React app with base layout, routing, and filter component

**Structure:**
```
frontend/
├── src/
│   ├── App.tsx
│   ├── index.tsx
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── Filters/
│   │   │   ├── FilterPanel.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── StateSelect.tsx
│   │   │   └── ServiceAreaSelect.tsx
│   │   ├── Dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── MetricsCard.tsx
│   │   │   ├── TabNavigation.tsx
│   │   │   ├── OfflineDistributionChart.tsx
│   │   │   └── EngineerPerformanceTable.tsx
│   │   └── Export/
│   │       └── ExportButton.tsx
│   ├── pages/
│   │   └── DashboardPage.tsx
│   ├── services/
│   │   ├── api.ts
│   │   └── cache.ts
│   ├── hooks/
│   │   ├── useFilters.ts
│   │   ├── useEngineerData.ts
│   │   └── useOfflineData.ts
│   ├── utils/
│   │   ├── dateHelpers.ts
│   │   ├── formatters.ts
│   │   └── calculations.ts
│   └── styles/
│       └── globals.css (Tailwind imports)
├── package.json
└── tsconfig.json
```

**Step 1: App Component**
```tsx
// frontend/src/App.tsx

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import DashboardPage from './pages/DashboardPage';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
```

**Step 2: Filter Panel Component**
```tsx
// frontend/src/components/Filters/FilterPanel.tsx

import React, { useState } from 'react';
import DateRangePicker from './DateRangePicker';
import StateSelect from './StateSelect';
import ServiceAreaSelect from './ServiceAreaSelect';

interface FilterPanelProps {
  onFilterChange: (filters: FilterState) => void;
  isLoading?: boolean;
}

export interface FilterState {
  from_date: Date;
  to_date: Date;
  state: string;
  service_area?: string;
  show_active_only: boolean;
}

export default function FilterPanel({ onFilterChange, isLoading }: FilterPanelProps) {
  const [filters, setFilters] = useState<FilterState>({
    from_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    to_date: new Date(),
    state: 'All (PAN India)',
    show_active_only: true
  });

  const handleFilterChange = (newFilters: Partial<FilterState>) => {
    const updated = { ...filters, ...newFilters };
    setFilters(updated);
    onFilterChange(updated);
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow-md mb-4 sticky top-0 z-10">
      <div className="flex flex-wrap gap-4 items-end">
        <DateRangePicker
          from_date={filters.from_date}
          to_date={filters.to_date}
          onChange={(dates) => handleFilterChange(dates)}
        />
        
        <StateSelect
          value={filters.state}
          onChange={(state) => handleFilterChange({ state })}
        />
        
        {filters.state !== 'All (PAN India)' && (
          <ServiceAreaSelect
            state={filters.state}
            value={filters.service_area}
            onChange={(service_area) => handleFilterChange({ service_area })}
          />
        )}
        
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.show_active_only}
            onChange={(e) => handleFilterChange({ show_active_only: e.target.checked })}
          />
          <span className="text-sm text-gray-700">Show Active Only</span>
        </label>
        
        <button
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
    </div>
  );
}
```

**Step 3: Metrics Cards**
```tsx
// frontend/src/components/Dashboard/MetricsCard.tsx

interface MetricsData {
  total_engineers: number;
  total_visits: number;
  avg_repeat_rate: number;
  offline_sites_3days: number;
}

export default function MetricsCards({ data }: { data: MetricsData }) {
  const metrics = [
    {
      label: 'Total Engineers',
      value: data.total_engineers,
      icon: '👥'
    },
    {
      label: 'Total Visits',
      value: data.total_visits,
      icon: '📍'
    },
    {
      label: 'Avg Repeat Rate',
      value: `${data.avg_repeat_rate}x`,
      icon: '🔄'
    },
    {
      label: 'Offline Sites (>3d)',
      value: data.offline_sites_3days,
      icon: '⚠️'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {metrics.map((metric, idx) => (
        <div key={idx} className="bg-white p-6 rounded-lg shadow">
          <div className="text-4xl mb-2">{metric.icon}</div>
          <div className="text-gray-600 text-sm mb-2">{metric.label}</div>
          <div className="text-3xl font-bold text-blue-600">{metric.value}</div>
        </div>
      ))}
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] React app runs without errors
- [ ] Filter panel displays all controls
- [ ] Date picker works (7-day default)
- [ ] State select populated from API
- [ ] Metrics cards render (mock data ok for now)

---

### Phase 2.2: Dashboard Views - Chart & Table

**Deliverable:** Interactive chart and table components

**Step 1: Offline Distribution Chart**
```tsx
// frontend/src/components/Dashboard/OfflineDistributionChart.tsx

import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { getOfflineDistribution } from '../../services/api';

interface ChartData {
  bucket: string;
  count: number;
  percent: number;
}

const bucketColors: Record<string, string> = {
  '1-3 Days': '#22c55e',
  '4-7 Days': '#eab308',
  '8-15 Days': '#f97316',
  '16-30 Days': '#ef4444',
  '31-60 Days': '#dc2626',
  '61-90 Days': '#7c3aed',
  '90+ Days': '#1f2937'
};

export default function OfflineDistributionChart({ filters }) {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getOfflineDistribution(filters);
        if (response.success) {
          setData(response.data.distribution);
        }
      } catch (error) {
        console.error('Failed to load distribution:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [filters]);

  if (loading) return <div className="text-center py-8">Loading chart...</div>;

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-bold mb-4">Offline Sites Distribution by Bucket</h2>
      
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="bucket" />
          <YAxis label={{ value: 'Count of Sites', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            formatter={(value) => value}
            labelFormatter={(label) => `Bucket: ${label}`}
            contentStyle={{ backgroundColor: '#f9fafb', border: '1px solid #e5e7eb' }}
          />
          <Legend />
          
          <Bar
            dataKey="count"
            name="Sites"
            fill="#1e40af"
            radius={[8, 8, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Step 2: Engineer Performance Table**
```tsx
// frontend/src/components/Dashboard/EngineerPerformanceTable.tsx

import React, { useEffect, useState } from 'react';
import { getEngineerPerformance } from '../../services/api';

interface Engineer {
  employee_id: number;
  employee_name: string;
  service_area: string;
  phone_no: string;
  state: string;
  att_days: number;
  working_days: number;
  att_percent: number;
  prod_days: number;
  zero_prod_days: number;
  total_visits: number;
  distinct_sites: number;
  repeat_rate: number;
  closed: number;
  open: number;
  pending: number;
  completed: number;
  offline_sites: number;
}

export default function EngineerPerformanceTable({ filters }) {
  const [engineers, setEngineers] = useState<Engineer[]>([]);
  const [footer, setFooter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await getEngineerPerformance(filters);
        if (response.success) {
          // Sort by att_percent descending
          const sorted = response.data.engineers.sort(
            (a, b) => b.att_percent - a.att_percent
          );
          setEngineers(sorted);
          setFooter(response.data.footer);
        }
      } catch (error) {
        console.error('Failed to load engineers:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [filters]);

  if (loading) return <div className="text-center py-8">Loading table...</div>;

  // Pagination
  const startIdx = (page - 1) * perPage;
  const endIdx = startIdx + perPage;
  const paginatedEngineers = engineers.slice(startIdx, endIdx);

  const getRowColor = (engineer) => {
    if (engineer.att_percent < 80) return 'bg-red-100';
    if (engineer.zero_prod_days > 5) return 'bg-red-100';
    if (engineer.offline_sites > 20) return 'bg-orange-100';
    if (engineer.repeat_rate < 2.0) return 'bg-yellow-100';
    return 'bg-white';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4">Engineer Performance Report</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-blue-100 border-b">
              <th className="p-2 text-left">Service Area</th>
              <th className="p-2 text-left">Engineer Name</th>
              <th className="p-2 text-left">Code</th>
              <th className="p-2 text-left">Phone</th>
              <th className="p-2 text-left">State</th>
              <th className="p-2 text-center">Att. Days</th>
              <th className="p-2 text-center">Work Days</th>
              <th className="p-2 text-center">Att. %</th>
              <th className="p-2 text-center">Prod Days</th>
              <th className="p-2 text-center">Zero Prod</th>
              <th className="p-2 text-center">Total Visits</th>
              <th className="p-2 text-center">Distinct Sites</th>
              <th className="p-2 text-center">Repeat Rate</th>
              <th className="p-2 text-center">Closed</th>
              <th className="p-2 text-center">Open</th>
              <th className="p-2 text-center">Pending</th>
              <th className="p-2 text-center">Completed</th>
              <th className="p-2 text-center">Offline Sites</th>
            </tr>
          </thead>
          <tbody>
            {paginatedEngineers.map((eng) => (
              <tr key={eng.employee_id} className={`border-b ${getRowColor(eng)}`}>
                <td className="p-2">{eng.service_area}</td>
                <td className="p-2 font-medium">{eng.employee_name}</td>
                <td className="p-2">{eng.employee_id}</td>
                <td className="p-2">{eng.phone_no}</td>
                <td className="p-2">{eng.state}</td>
                <td className="p-2 text-center">{eng.att_days}</td>
                <td className="p-2 text-center">{eng.working_days}</td>
                <td className="p-2 text-center font-bold">{eng.att_percent.toFixed(1)}%</td>
                <td className="p-2 text-center">{eng.prod_days}</td>
                <td className="p-2 text-center">{eng.zero_prod_days}</td>
                <td className="p-2 text-center">{eng.total_visits}</td>
                <td className="p-2 text-center">{eng.distinct_sites}</td>
                <td className="p-2 text-center">{eng.repeat_rate.toFixed(2)}x</td>
                <td className="p-2 text-center">{eng.closed}</td>
                <td className="p-2 text-center">{eng.open}</td>
                <td className="p-2 text-center">{eng.pending}</td>
                <td className="p-2 text-center">{eng.completed}</td>
                <td className="p-2 text-center">{eng.offline_sites}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Section */}
      {footer && (
        <div className="mt-6 bg-gray-100 p-4 rounded">
          <h3 className="font-bold mb-2">Summary ({filters.state})</h3>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>Total Engineers: <span className="font-bold">{footer.total_engineers}</span></div>
            <div>Total Visits: <span className="font-bold">{footer.total_visits}</span></div>
            <div>Avg Repeat Rate: <span className="font-bold">{footer.avg_repeat_rate.toFixed(2)}x</span></div>
            <div>Avg Att. %: <span className="font-bold">{footer.avg_att_percent.toFixed(1)}%</span></div>
          </div>
        </div>
      )}

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between">
        <select
          value={perPage}
          onChange={(e) => {
            setPerPage(parseInt(e.target.value));
            setPage(1);
          }}
          className="border rounded px-2 py-1"
        >
          <option value="25">25 per page</option>
          <option value="50">50 per page</option>
          <option value="100">100 per page</option>
        </select>

        <div className="flex gap-2">
          <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1">Page {page} of {Math.ceil(engineers.length / perPage)}</span>
          <button
            disabled={endIdx >= engineers.length}
            onClick={() => setPage(page + 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Acceptance Criteria:**
- [ ] Chart renders with sample data
- [ ] Table displays all columns
- [ ] Pagination works
- [ ] Color coding applied
- [ ] Footer summary displays

---

### Phase 2.3: Export & Additional Features

**Deliverable:** Export to Excel/CSV, data refresh

**Step 1: Export Service**
```typescript
// frontend/src/services/export.ts

import * as XLSX from 'xlsx';
import { Engineer } from '../types';

export async function exportToExcel(
  engineers: Engineer[],
  footer: any,
  distribution: any,
  filters: FilterState
) {
  const workbook = XLSX.utils.book_new();

  // Sheet 1: Summary
  const summaryData = [
    ['Dashboard Generated:', new Date().toLocaleString()],
    [],
    ['Filters Applied:'],
    ['Date Range:', `${filters.from_date} to ${filters.to_date}`],
    ['State:', filters.state],
    [],
    ['Key Metrics:'],
    ['Total Engineers:', engineers.length],
    ['Total Visits:', footer.total_visits],
    ['Avg Repeat Rate:', footer.avg_repeat_rate.toFixed(2) + 'x'],
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');

  // Sheet 2: Engineer Details
  const engineersData = [
    ['Service Area', 'Engineer Name', 'Code', 'Phone', 'State', 
     'Att. Days', 'Work Days', 'Att. %', 'Prod Days', 'Zero Prod',
     'Total Visits', 'Distinct Sites', 'Repeat Rate', 'Closed', 'Open',
     'Pending', 'Completed', 'Offline Sites'],
    ...engineers.map(e => [
      e.service_area, e.employee_name, e.employee_id, e.phone_no, e.state,
      e.att_days, e.working_days, e.att_percent, e.prod_days, e.zero_prod_days,
      e.total_visits, e.distinct_sites, e.repeat_rate, e.closed, e.open,
      e.pending, e.completed, e.offline_sites
    ]),
    [],
    ['TOTAL', '', '', '', engineers.length, '', '', '', '', '',
     footer.total_visits, '', footer.avg_repeat_rate, '', '', '', '', '']
  ];
  const engineersSheet = XLSX.utils.aoa_to_sheet(engineersData);
  XLSX.utils.book_append_sheet(workbook, engineersSheet, 'Engineer Details');

  // Sheet 3: Offline Distribution
  const distributionData = [
    ['Offline Bucket', 'Count', '% of Total'],
    ...distribution.map(d => [d.bucket, d.count, d.percent])
  ];
  const distributionSheet = XLSX.utils.aoa_to_sheet(distributionData);
  XLSX.utils.book_append_sheet(workbook, distributionSheet, 'Offline Distribution');

  // Generate filename
  const filename = `VProtect_Engineer_Report_${filters.state}_${filters.from_date}_${filters.to_date}.xlsx`;

  // Download
  XLSX.writeFile(workbook, filename);
}

export function exportToCSV(engineers: Engineer[], filters: FilterState) {
  const csv = [
    ['Service Area', 'Engineer Name', 'Code', 'Phone', 'State', ...].join(','),
    ...engineers.map(e => [e.service_area, e.employee_name, e.employee_id, ...].join(','))
  ].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `VProtect_Engineer_Report_${filters.state}_${filters.from_date}_${filters.to_date}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
```

**Acceptance Criteria:**
- [ ] Excel export functional
- [ ] CSV export functional
- [ ] Filenames include date range
- [ ] Formatting applied (headers, colors, freeze panes)

---

## PHASE 3: INTEGRATION & DEPLOYMENT (Week 3-4)

### Phase 3.1: API Integration

**Checklist:**
- [ ] Frontend calls backend APIs correctly
- [ ] Error handling (network, validation, 500 errors)
- [ ] Loading states display
- [ ] Data caching working
- [ ] CORS configured

### Phase 3.2: Docker Deployment

**Deliverable:** docker-compose.yml with all services

**File:** `docker-compose.yml`
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: vprotect
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/vprotect
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      REACT_APP_API_URL: http://backend:8000

volumes:
  postgres_data:
```

**Acceptance Criteria:**
- [ ] `docker-compose up` starts all services
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend accessible at http://localhost:8000
- [ ] Database initialized with schema
- [ ] No container errors

---

## TOKEN OPTIMIZATION TIPS

Since you're using Claude Code with token limits, here are strategies:

### 1. **Chunked Implementation**
Give Claude one Phase at a time:
- Phase 1.1: "Build the database schema"
- Phase 1.2: "Build the backend API"
- Instead of all at once

### 2. **Use Clear Function Signatures**
```python
# Instead of full implementation, start with stubs:
def calculate_engineer_metrics(employee_id, from_date, to_date):
    """
    Calculate: att_days, working_days, att_percent, prod_days, zero_prod_days,
    total_visits, distinct_sites, repeat_rate, closed, open, pending, completed, offline_sites
    
    Returns: Dict[str, Any]
    """
    pass
```

Claude will understand structure without full code.

### 3. **Reference External Docs**
Instead of repeating schema in every prompt:
```
"Use the DATABASE_LOGIC.md file (in repo) for table definitions. Don't ask me to repeat."
```

### 4. **Use Existing Code as Template**
Once one endpoint is done:
```
"Create POST /api/offline-distribution endpoint following the same pattern as GET /api/engineers/performance"
```

### 5. **Focus on Logic, Not Boilerplate**
Ask Claude for:
- Complex calculations
- Database queries
- Business logic

Use templates/generators for:
- CRUD endpoints
- Table columns
- Form fields

### 6. **Batch Similar Tasks**
```
"Create these 3 Select components: StateSelect, ServiceAreaSelect, DateRangePicker.
Use this interface for all: interface SelectProps { value: string; onChange: (value: string) => void; }"
```

### 7. **Use Skeleton Code**
Give Claude the structure, let it fill logic:
```typescript
export async function getEngineerPerformance(filters: FilterRequest): Promise<Response> {
  // 1. Validate filters
  
  // 2. Query database (call service)
  
  // 3. Calculate metrics
  
  // 4. Return formatted response
}
```

---

## FINAL CHECKLIST

Before going live:

**Database:**
- [ ] All 8 tables created
- [ ] All indexes created
- [ ] Sample data loaded
- [ ] Referential integrity verified

**Backend:**
- [ ] All endpoints return correct data
- [ ] Error handling in place
- [ ] ETL pipeline functional
- [ ] Caching working
- [ ] API documentation complete

**Frontend:**
- [ ] All views render
- [ ] Filters work correctly
- [ ] Export functionality works
- [ ] Responsive design tested
- [ ] No console errors

**Integration:**
- [ ] Frontend calls backend APIs
- [ ] Data flows end-to-end
- [ ] Docker deployment working
- [ ] Manual testing completed

**Performance:**
- [ ] Page loads < 3s
- [ ] API responses < 2s
- [ ] No memory leaks
- [ ] DB queries optimized

---

## SUPPORT & TROUBLESHOOTING

### Common Issues:

1. **"Column XYZ not found"**
   - Check TABLE column names in DATABASE_LOGIC.md Section 2
   - Check ETL transformation mapping

2. **"Foreign key violation"**
   - Ensure master data loaded first (engineer_master, customer_site_master)
   - Check join conditions in queries

3. **"API timeout"**
   - Check database indexes are created
   - Consider query optimization (reduce JOINs)
   - Increase timeout in FastAPI config

4. **"React component not rendering"**
   - Check console for errors
   - Verify props passed correctly
   - Check API response structure

---

## QUESTIONS BEFORE STARTING?

If anything is unclear, ask:
- **Data:** "Can you clarify the cs_id vs oracle_site_no relationship?"
- **Logic:** "Should zero_prod_days calculation include Absent days?"
- **UI:** "Should the table be sortable by all columns?"
- **Performance:** "How many engineers typically in a state?"

---

**START WITH PHASE 1.1: DATABASE SETUP**

Once that's done, move to Phase 1.2, then 1.3, etc.

Good luck! 🚀
