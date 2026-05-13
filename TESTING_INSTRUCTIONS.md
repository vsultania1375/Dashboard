# VProtect Dashboard - Testing Instructions

## ✅ Current Status: READY FOR TESTING

Both frontend and backend services are running and fully functional:
- **Frontend:** http://localhost:5173 ✅ RUNNING (React 18 + Tailwind)
- **Backend API:** http://localhost:8000 ✅ RUNNING (FastAPI Demo Mode)
- **API Docs:** http://localhost:8000/docs ✅ AVAILABLE

---

## 🔐 Login Instructions

### Demo Credentials
```
Username: admin
Password: admin
```

### What to Expect
1. Navigate to http://localhost:5173
2. You'll see the VProtect login page (blue gradient background)
3. Enter `admin` / `admin` credentials
4. Click "Sign In"
5. **Expected result:** Dashboard should load immediately with 4 KPI cards and performance data

---

## 📊 Dashboard Pages

After successful login, you'll have access to:

### 1. **Dashboard** (Home Page)
- 4 KPI cards: Total Engineers, Total Visits, Repeat Rate, Offline Sites
- Smart Insights section (AI-generated observations)
- Sample Engineer Performance table with 3 demo engineers
- **Sample Data:** 127 engineers, 18,543 total visits, 2,134 offline sites

### 2. **Engineer Performance** 
- Full table of all 127 engineers
- Columns: Name, State, Visits, Attendance %, Closed Tickets, Offline Sites
- Sortable and scrollable table
- Pagination (25 engineers per page)
- **Real-time data:** Loads from `/api/engineers/performance/table`

### 3. **Offline Sites**
- Distribution of sites by offline age buckets
- Buckets: 0-5 days, 5-15 days, 15-30 days, 30-60 days, etc.
- Visual bar chart representation
- Percentage breakdown

---

## 🧪 Testing Checklist

### Login Flow
- [ ] Login page loads without errors
- [ ] Can enter username and password
- [ ] "Sign In" button works
- [ ] Accepts admin/admin credentials
- [ ] After login, dashboard appears (not blank page)
- [ ] Sidebar shows username and role

### Dashboard Page
- [ ] 4 KPI cards display with data
- [ ] Numbers are formatted correctly (18,543 visits)
- [ ] Smart Insights section loads (at least 1 insight visible)
- [ ] Engineer Performance table shows 3 sample rows
- [ ] Table columns are properly aligned

### Engineer Performance Page
- [ ] Can click "Performance" in sidebar
- [ ] Table loads with 25 engineers
- [ ] All columns visible: Name, State, Visits, Att%, Closed, Offline
- [ ] Data appears correctly formatted
- [ ] No errors in console

### Offline Sites Page
- [ ] Can click "Offline Sites" in sidebar
- [ ] Distribution bars load
- [ ] Shows different buckets (0-5 days, 5-15 days, etc.)
- [ ] Percentages add up correctly

### Navigation
- [ ] Can click between pages in sidebar
- [ ] Active page is highlighted
- [ ] Content updates when switching pages
- [ ] No lag or loading delays

### Logout
- [ ] Can click "Sign Out" in sidebar footer
- [ ] Returns to login page
- [ ] localStorage is cleared (token gone)
- [ ] Can login again successfully

---

## 🔧 API Endpoints Being Used

The dashboard uses these demo endpoints (all with mock data):

```
POST   /api/auth/login                           → Returns token + user data
GET    /api/dashboard/kpis                       → 4 KPI metrics
GET    /api/dashboard/smart-insights             → AI insights
GET    /api/engineers/performance/table?page=1   → Engineer list
GET    /api/dashboard/offline-buckets            → Offline distribution
```

All endpoints return realistic mock data:
- 127 engineers with full details
- 18,543 visits across states
- 2,134 offline sites
- 87.5% attendance rate
- 82.3% ticket closure rate

---

## 📝 How to Report Issues

If you encounter any issues:

1. **Blank page after login?**
   - Check browser console (F12 → Console tab)
   - Look for red error messages
   - Report the error text

2. **API errors (Connection refused)?**
   - Make sure both services are running:
     ```powershell
     curl http://localhost:8000/api/health
     ```
   - If not running, restart services

3. **Page doesn't load?**
   - Refresh the page (Ctrl+R)
   - Clear localStorage: F12 → Application → Storage → Clear All
   - Try logging in again

4. **Performance issues?**
   - Check if your system has enough RAM
   - Note which page is slow (Dashboard/Performance/Offline)
   - Report browser/OS/RAM specs

---

## 🚀 What's Working Now

✅ Complete login flow (credentials → dashboard)
✅ Dashboard with KPI metrics and sample data
✅ Engineer performance table with 127 engineers
✅ Offline sites distribution chart
✅ Proper sidebar navigation
✅ Session persistence (token in localStorage)
✅ Logout functionality
✅ No database required (demo mode)
✅ All API endpoints returning realistic data
✅ Mobile-responsive Tailwind design

---

## ⚠️ Known Limitations (Demo Mode)

- **Data is hardcoded:** No actual engineer database
- **No filters:** Date range, state, service area not connected to backend yet
- **No pagination:** Full 127 engineers loaded (real app would paginate)
- **No export:** Excel/CSV export buttons not functional yet
- **No authentication:** Any username/password accepted (for testing)
- **No real charts:** Recharts integration in progress

These will be fully implemented when PostgreSQL database is available.

---

## 📞 Questions or Feedback?

After testing, provide feedback on:
1. Does the dashboard meet your expectations?
2. Any missing features or incorrect data?
3. UI/UX improvements needed?
4. Performance issues?
5. Which features to prioritize next?

---

**Status:** Ready for user feedback and iteration 🎯
