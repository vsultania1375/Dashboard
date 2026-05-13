import { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { MapPin, Briefcase, BarChart3, AlertTriangle } from "lucide-react";

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

function ManagerDashboard() {
  const [loading, setLoading] = useState(true);
  const [regionStats, setRegionStats] = useState(null);
  const [regionData, setRegionData] = useState([]);
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    loadManagerData();
  }, []);

  const loadManagerData = async () => {
    setLoading(true);
    try {
      const [kpi, regions] = await Promise.all([
        apiFetch("/dashboard/kpis"),
        apiFetch("/analytics/performance-by-region"),
      ]);

      setRegionStats(kpi);
      setRegionData(regions.regions || []);

      // Sample tasks for manager
      setTasks([
        { id: 1, title: "Review Maharashtra team performance", priority: "high", status: "pending" },
        { id: 2, title: "Plan Karnataka deployment", priority: "medium", status: "in_progress" },
        { id: 3, title: "Address offline sites in Tamil Nadu", priority: "high", status: "pending" },
      ]);
    } catch (error) {
      console.error("Failed to load manager data:", error);
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
        <h1 className="text-3xl font-bold text-gray-800">Manager Dashboard</h1>
        <p className="text-gray-600 mt-2">Regional operations and team performance</p>
      </div>

      {/* Regional Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {regionData.map((region, idx) => (
          <div key={idx} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-4">
              <MapPin className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-800">{region.region}</h3>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <p>👥 Engineers: {region.engineers}</p>
              <p>📊 Avg Visits: {region.avg_visits_per_engineer}/eng</p>
              <p>✅ Attendance: {region.attendance_percent}%</p>
              <p>🔴 Offline Sites: {region.offline_sites}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Regional Attendance Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Attendance by Region</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={regionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="region" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="attendance_percent" fill="#10b981" name="Attendance %" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Visits Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Visits per Engineer</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={regionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="region" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="avg_visits_per_engineer" fill="#3b82f6" name="Visits/Engineer" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Manager Tasks */}
      <div className="grid grid-cols-2 gap-6">
        {/* Tasks */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">My Tasks</h2>
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="p-4 bg-gray-50 rounded-lg border-l-4 border-blue-600">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="font-medium text-gray-800">{task.title}</p>
                    <div className="flex gap-2 mt-2">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          task.priority === "high"
                            ? "bg-red-100 text-red-800"
                            : task.priority === "medium"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {task.priority}
                      </span>
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 font-medium">
                        {task.status === "pending" ? "Pending" : "In Progress"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Regional Summary */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Regional Summary</h2>
          <div className="space-y-4">
            {regionData.map((region, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-800">{region.region}</p>
                  <p className="text-sm text-gray-600">{region.engineers} engineers</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-blue-600">{region.attendance_percent}%</p>
                  <p className="text-xs text-gray-500">attendance</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ManagerDashboard;
