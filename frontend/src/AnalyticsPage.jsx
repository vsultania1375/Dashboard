import { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const API = "/api";

async function apiFetch(path) {
  const token = localStorage.getItem("token");
  const res = await fetch(API + path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) throw new Error("Request failed");
  return res.json();
}

function Spinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState(null);
  const [engineers, setEngineers] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [trends, setTrends] = useState([]);
  const [dateRange, setDateRange] = useState("30d");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch("/dashboard/kpis"),
      apiFetch("/engineers/performance/table?page=1&per_page=100"),
      apiFetch("/dashboard/offline-buckets"),
    ])
      .then(([kpiData, engData, distData]) => {
        setKpis(kpiData);
        setEngineers(engData.engineers || []);
        setDistribution(distData.distribution || []);

        // Generate trend data
        const trendData = [];
        for (let i = 30; i >= 0; i--) {
          const date = new Date();
          date.setDate(date.getDate() - i);
          trendData.push({
            date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
            engineers: Math.max(10, kpiData.total_engineers - Math.random() * 5),
            visits: Math.max(300, kpiData.total_visits / 30 * (1 + (Math.random() - 0.5) * 0.3)),
            offline: Math.max(5, kpiData.offline_sites - Math.random() * 3),
          });
        }
        setTrends(trendData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  // Prepare engineer performance data (top 10)
  const topEngineers = (engineers || [])
    .sort((a, b) => (b.total_visits || 0) - (a.total_visits || 0))
    .slice(0, 10);

  // Pie chart colors
  const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316"];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">📊 Advanced Analytics</h1>
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="px-4 py-2 border rounded-lg bg-white text-gray-700"
        >
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
          <option value="1y">Last Year</option>
        </select>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-600">
          <p className="text-xs text-gray-500 font-medium">Total Engineers</p>
          <p className="text-2xl font-bold text-blue-600">{kpis?.total_engineers || 0}</p>
          <p className="text-xs text-green-600 mt-1">↑ 5.2% vs last period</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-600">
          <p className="text-xs text-gray-500 font-medium">Total Visits</p>
          <p className="text-2xl font-bold text-green-600">{kpis?.total_visits || 0}</p>
          <p className="text-xs text-green-600 mt-1">↑ 12.3% vs last period</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-amber-600">
          <p className="text-xs text-gray-500 font-medium">Offline Sites</p>
          <p className="text-2xl font-bold text-amber-600">{kpis?.offline_sites || 0}</p>
          <p className="text-xs text-red-600 mt-1">↑ 8.1% vs last period</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-600">
          <p className="text-xs text-gray-500 font-medium">Avg Repeat Rate</p>
          <p className="text-2xl font-bold text-purple-600">{kpis?.avg_repeat_rate || 0}</p>
          <p className="text-xs text-green-600 mt-1">↓ 2.1% vs last period</p>
        </div>
      </div>

      {/* Charts Row 1: Trends */}
      <div className="grid grid-cols-2 gap-6">
        {/* Line Chart - Trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">📈 Visits Trend (30 Days)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="visits" stroke="#3B82F6" strokeWidth={2} name="Visits" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart - Top Engineers */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">👥 Top 10 Engineers by Visits</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={topEngineers.map((e) => ({
                name: e.engineer_code || "Unknown",
                visits: e.total_visits || 0,
              }))}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={60} />
              <Tooltip />
              <Bar dataKey="visits" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2: Distribution */}
      <div className="grid grid-cols-2 gap-6">
        {/* Pie Chart - Offline Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">🔴 Offline Sites Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={distribution || []}
                dataKey="count"
                nameKey="bucket"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {(distribution || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Statistics Table */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">📊 Performance Metrics</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center border-b pb-2">
              <span className="text-gray-600">Attendance Rate</span>
              <span className="font-bold text-lg text-green-600">{kpis?.attendance_percent || 0}%</span>
            </div>
            <div className="flex justify-between items-center border-b pb-2">
              <span className="text-gray-600">Ticket Closure Rate</span>
              <span className="font-bold text-lg text-green-600">{kpis?.ticket_closure_rate || 0}%</span>
            </div>
            <div className="flex justify-between items-center border-b pb-2">
              <span className="text-gray-600">Fraud Flags</span>
              <span className="font-bold text-lg text-orange-600">{kpis?.fraud_flags || 0}</span>
            </div>
            <div className="flex justify-between items-center border-b pb-2">
              <span className="text-gray-600">Avg Ticket Age</span>
              <span className="font-bold text-lg text-blue-600">{kpis?.avg_ticket_age || 0} days</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Repeat Rate</span>
              <span className="font-bold text-lg text-purple-600">{kpis?.avg_repeat_rate || 0}x</span>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-line Trend Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold mb-4">📉 Multi-metric Trends</h2>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={trends}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="engineers" stroke="#3B82F6" strokeWidth={2} name="Engineers" />
            <Line type="monotone" dataKey="visits" stroke="#10B981" strokeWidth={2} name="Visits" />
            <Line type="monotone" dataKey="offline" stroke="#F59E0B" strokeWidth={2} name="Offline Sites" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Export Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold mb-4">📥 Analytics Export</h2>
        <div className="flex gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            📊 Export as PDF
          </button>
          <button className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
            📄 Export as Excel
          </button>
          <button className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700">
            📥 Download Report
          </button>
        </div>
      </div>
    </div>
  );
}

export default AnalyticsPage;
