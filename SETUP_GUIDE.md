# Service Analysis Dashboard — Setup Guide
### Written for someone with no development background

---

## What You Will Have After This Guide

A working dashboard that opens in your browser showing:
- Live KPI cards (offline sites, ticket status, attendance)
- State-by-state health map
- Engineer leaderboard with fraud detection
- Upload page where you paste your Excel files every morning

---

## Step 1 — Install Docker Desktop (One-Time Only)

Docker is a free tool that packages the entire application so you don't need to install Python, Node.js, or PostgreSQL separately. It handles everything.

**On Windows:**
1. Go to: https://www.docker.com/products/docker-desktop/
2. Click "Download for Windows"
3. Run the installer — accept all defaults
4. Restart your computer when asked
5. After restart, Docker Desktop will open automatically. You'll see a whale icon in your taskbar.

**On Mac:**
1. Go to: https://www.docker.com/products/docker-desktop/
2. Download for Mac (choose Apple Silicon if your Mac is 2020 or newer, Intel if older)
3. Drag Docker to Applications folder and open it
4. Allow it when asked for permissions

**How to know Docker is ready:**
Open a terminal (on Windows: press Windows key, type "cmd", press Enter. On Mac: press Cmd+Space, type "terminal", press Enter) and type:
```
docker --version
```
You should see something like: `Docker version 24.0.0`

---

## Step 2 — Get the Dashboard Files

You should have received a ZIP file called `service-analysis-dashboard.zip`.

1. Unzip it anywhere — for example, your Desktop
2. You will see a folder called `dashboard` with this structure:
```
dashboard/
  backend/
  frontend/
  data/
  docker-compose.yml
  START.bat         ← Windows users double-click this
  start.sh          ← Mac/Linux users use this
  SETUP_GUIDE.md    ← This file
```

---

## Step 3 — Start the Dashboard (Every Time)

**On Windows:**
Double-click the file `START.bat` inside the dashboard folder.

A black window will appear. Wait 2-3 minutes. When you see:
```
✅ Dashboard is ready! Open your browser and go to: http://localhost
```
...it is ready.

**On Mac/Linux:**
Open Terminal, navigate to the dashboard folder:
```bash
cd ~/Desktop/dashboard
./start.sh
```

---

## Step 4 — Open the Dashboard

Open any web browser (Chrome recommended) and go to:
```
http://localhost
```

You will see a login page.

**Default login:**
- Username: `admin`
- Password: `Admin@1234`

You will be asked to change this password on first login.

---

## Step 5 — First-Time Setup (Uploading Master Data)

Before you can see any data, upload these two master files **once**:

1. Click **Data Upload** in the left menu
2. Upload **Customer Site Master** (your `Customer_site_mst.csv` file)
3. Upload **Engineer Data** (your engineer Excel file)
4. Wait for the green success message

---

## Step 6 — Daily Upload Routine (Every Morning)

Upload in this exact order before 9:00 AM:

| Order | File | How Often |
|-------|------|-----------|
| 1st | B2B Offline Data | Every day |
| 2nd | View Ticket Dump | Every day |
| 3rd | Attendance Report | Every day |

After each upload, the system runs ETL (data processing) automatically. This takes about 20-30 minutes. The dashboard updates in real time.

⚠️ **Important for Attendance:** This file is APPEND-ONLY. Never upload the same date twice. Only upload today's new attendance data.

---

## Step 7 — Create Logins for Your Team

1. Go to **User Mgmt** in the left menu
2. Click Create New User
3. For State Managers: select role "State Manager" and type the state name (e.g. "Karnataka")
4. State Managers will only see their own state's data — this is automatic

**Roles:**
- **Admin** — Full access + uploads + user management (you)
- **Ops Manager** — Full PAN India view, can review fraud flags
- **State Manager** — Can only see their assigned state

---

## Stopping the Dashboard

In the terminal where it's running, press `Ctrl + C`.
Or close Docker Desktop.

To start again next time: just run `START.bat` (Windows) or `./start.sh` (Mac) again.

---

## Troubleshooting

**"Cannot connect" in browser:**
Wait 3 more minutes. The database takes time to start on first run.

**"Port 80 already in use" error:**
Another application is using port 80. Edit `docker-compose.yml`, find `"80:80"` and change it to `"8080:80"`. Then open `http://localhost:8080` instead.

**"Docker not found" error:**
Docker Desktop is not running. Open Docker Desktop from your Start Menu / Applications and wait for the whale icon to stop animating.

**Data uploaded but dashboard shows zeros:**
ETL is still running. Wait 30 minutes and refresh.

**Forgot admin password:**
Open terminal in dashboard folder and run:
```
docker exec sad_db psql -U dashboard service_dashboard -c "UPDATE app_user SET password_hash='\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TiGiIoSA6GqDOwAzFtM1gGkXnrXi', force_password_change=TRUE WHERE username='admin';"
```
Password is reset to `Admin@1234`.

---

## What Each Page Shows

### 📊 Dashboard
- KPI cards: total offline sites, open tickets, engineer attendance, fraud flags
- Smart Insight Panel: auto-generated alerts (critical, warning, info)
- State Health: all states sorted by offline percentage (red = worst)
- Offline Bucket Chart: sites by how long they've been offline
- Today's Problems Digest: one-visit day engineers, chronic pending tickets, offline sites with no ticket

### 🎫 Ticket Analysis
- Status distribution (OPEN/PENDING/CLOSED/SENTBACK)
- Aging bands: how old are the pending/open tickets
- Breach List: tickets open longer than 3 days
- SENTBACK Analysis: which engineers have the most rejections
- No-Ticket Sites: offline sites with no ticket raised at all
- Chronic PENDING: PENDING tickets with same reason for 15+ days (fraud detection)

### 👷 Engineers
- Full leaderboard sorted by composite score (0-100)
- Click any engineer → full profile with:
  - Score breakdown (7 components)
  - Monthly trend (last 4 months)
  - Daily attendance calendar coloured by productive/flag/absent
  - All fraud flags with details
  - Their area (PoP) site list

### 🗺️ State Intelligence (Ops Manager only)
- All states compared: offline rate, closure rate, avg resolution time, fraud flag count
- State scores with penalties/bonuses applied

### 🚩 Fraud Flags
- All detected anomalies: one-visit days, fake visits, chronic pending, same-day close
- Ops Managers can mark each flag as "Valid" or "Confirmed Fake"
- Confirmed fake = -5 points deducted from engineer score

### 📤 Data Upload
- Upload all 5 file types
- See upload history with row count and ETL status

---

## Understanding the Fraud Detection

The system automatically checks for 7 patterns every day when data is uploaded:

| Pattern | What it catches |
|---------|----------------|
| P1 | Engineers who did only 1 visit but had 5+ tickets waiting |
| P2 | Tickets created and closed same day after site was offline for days |
| P3 | PENDING tickets with same excuse for 15+ days (not stock/spare) |
| P7 | Sites offline 4+ days with absolutely no ticket raised |
| FV-01 | Visit lasted less than 10 minutes |
| FV-03 | Ticket closed in under 1 hour of being created |
| FV-04 | Ticket closed but no visit timestamp exists |
| FV-06 | Ticket closed on a day the engineer was absent |

---

## Understanding the Engineer Score (0–100)

| Component | Max Points | What it measures |
|-----------|------------|-----------------|
| Ticket Closure Rate | 25 | How many tickets closed vs total |
| Service Area Coverage | 20 | What % of their sites visited |
| Resolution Time | 20 | How fast tickets closed |
| Area Offline % | 15 | How much of their area stays online |
| Repeat Visit Rate | 10 | Same site visited again (quality issue) |
| Attendance | 7 | Present days + punctuality |
| Fraud Flags | 3 | Clean flag record |

**Score bands:** 90-100 Exceptional · 75-89 Good · 60-74 Average · 45-59 Below Average · <45 Poor

Engineers with 3+ Critical/High fraud flags are forced to Red (score capped at 35).

---

## Data Files Expected Format

### B2B Offline (Excel, daily)
Columns needed: `cs_no`, `Bucket`, `No. Of Days`, `State`, `Zone`, `Offline Date & Time`, `Alarm Date`

### View Ticket (Excel, daily)
Columns needed: `Ticket ID`, `CS ID`, `Ticket Status`, `Create Date`, `Ticket Assigned To`, `Aging Days`, `Total Visits`, `Last Visit In Date-Time`, `Last Visit Out Date-Time`, `Ticket Closed Date & Time`

### Attendance (Excel, daily APPEND)
Columns needed: `Employee Name` (format: "Name (EMP-CODE)"), `Attendance Date`, `Attendance Status`, `In Date Time`, `Out Date Time`, `First_Visit_CS_ID`, `Last_Visit_CS_ID`

### Engineer Master (Excel, periodic)
Columns needed: `Employee Code`, `Employee Name`, `Service Area Code`, `State`, `Designation`

### Customer Site Master (CSV, periodic)
Columns needed: `cs_id`, `service_area_code`, `site_state`, `active_status`, `business_type`

---

*Service Analysis Dashboard v2.0 — Built for PAN India Alarm System Maintenance*
*25,000 Sites · 250 Engineers · 28+ States · 4 Zones*
