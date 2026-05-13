import { useState, useEffect } from "react";
import { LineChart, Line, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Briefcase, MapPin, Clock, CheckCircle } from "lucide-react";

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

function EngineerDashboard() {
  const [loading, setLoading] = useState(true);
  const [engineerStats, setEngineerStats] = useState(null);
  const [performanceData, setPerformanceData] = useState([]);
  const [todayTasks, setTodayTasks] = useState([]);

  useEffect(() => {
    loadEngineerData();
  }, []);

  const loadEngineerData = async () => {
    setLoading(true);
    try {
      const [kpi, performance] = await Promise.all([
        apiFetch("/dashboard/kpis"),
        apiFetch("/engineers/performance/table?page=1&per_page=1"),
      ]);

      // Mock engineer stats
      const mockStats = {
        engineer_name: "Rajesh Kumar",
        engineer_code: "001",
        total_visits: 145,
        attendance_percent: 94.5,
        completion_rate: 92.3,
        avg_visit_time: "45 min",
      };

      setEngineerStats(mockStats);

      // Generate performance trend
      const trend = [];
      for (let i = 30; i > 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        trend.push({
          date: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          visits: Math.floor(Math.random() * 8) + 3,
          completion: Math.floor(Math.random() * 20) + 80,
        });
      }
      setPerformanceData(trend);

      // Generate today's tasks
      setTodayTasks([
        { id: 1, site: "SITE001 - Mumbai Office", status: "completed", time: "08:30 AM" },
        { id: 2, site: "SITE005 - Bandra Branch", status: "in_progress", time: "10:15 AM" },
        { id: 3, site: "SITE012 - Powai Hub", status: "scheduled", time: "02:00 PM" },
        { id: 4, site: "SITE018 - Dadar Center", status: "scheduled", time: "04:30 PM" },
      ]);
    } catch (error) {
      console.error("Failed to load engineer data:", error);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Engineer Dashboard</h1>
        <p className="text-gray-600 mt-2">My performance and daily tasks</p>
      </div>

      {/* Personal Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm font-medium">Name</p>
          <p className="text-2xl font-bold text-blue-600 mt-2">{engineerStats?.engineer_name}</p>
          <p className="text-xs text-gray-500 mt-1">Code: {engineerStats?.engineer_code}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-5 h-5 text-green-600" />
            <p className="text-gray-600 text-sm">Total Visits</p>
          </div>
          <p className="text-3xl font-bold text-green-600 mt-2">{engineerStats?.total_visits}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-purple-600" />
            <p className="text-gray-600 text-sm">Completion</p>
          </div>
          <p className="text-3xl font-bold text-purple-600 mt-2">{engineerStats?.completion_rate}%</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-blue-600" />
            <p className="text-gray-600 text-sm">Avg Time/Visit</p>
          </div>
          <p className="text-3xl font-bold text-blue-600 mt-2">{engineerStats?.avg_visit_time}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* 30-Day Performance */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">30-Day Performance</h2>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={performanceData}>
              <defs>
                <linearGradient id="colorCompletion" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="completion" stroke="#10b981" fillOpacity={1} fill="url(#colorCompletion)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Visit Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Daily Visits Trend</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="visits" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Today's Schedule */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Today's Schedule</h2>
        <div className="space-y-3">
          {todayTasks.map((task) => (
            <div key={task.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
              <div className="flex items-start gap-4 flex-1">
                <MapPin className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-800">{task.site}</p>
                  <p className="text-sm text-gray-600 mt-1">{task.time}</p>
                </div>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  task.status === "completed"
                    ? "bg-green-100 text-green-800"
                    : task.status === "in_progress"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                {task.status === "completed" ? "✓ Completed" : task.status === "in_progress" ? "● In Progress" : "○ Scheduled"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="mt-6 bg-blue-50 rounded-lg p-6 border-l-4 border-blue-600">
        <h3 className="font-semibold text-blue-900 mb-3">Performance Summary</h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start gap-2">
            <span className="mt-1">✓</span>
            <span>Attendance: {engineerStats?.attendance_percent}% - Excellent track record</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">✓</span>
            <span>Completion Rate: {engineerStats?.completion_rate}% - Above target</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1">✓</span>
            <span>Total Visits: {engineerStats?.total_visits} - Strong performance</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default EngineerDashboard;
