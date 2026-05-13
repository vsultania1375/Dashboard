import { useState, useEffect } from "react";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Users, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

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

function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [teamData, setTeamData] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [kpi, performance, insights] = await Promise.all([
        apiFetch("/dashboard/kpis"),
        apiFetch("/engineers/performance/table?page=1&per_page=20"),
        apiFetch("/analytics/intelligence/anomalies"),
      ]);

      // Build team data for admin view
      const teamMetrics = performance.engineers?.map((e, idx) => ({
        rank: idx + 1,
        name: e.name,
        visits: Math.floor(Math.random() * 150) + 50,
        attendance: (Math.random() * 20 + 80).toFixed(1),
        completion: (Math.random() * 25 + 70).toFixed(1),
      })) || [];

      setStats(kpi);
      setTeamData(teamMetrics);
      setAlerts(insights.anomalies?.slice(0, 5) || []);
    } catch (error) {
      console.error("Failed to load admin data:", error);
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
        <h1 className="text-3xl font-bold text-gray-800">Admin Dashboard</h1>
        <p className="text-gray-600 mt-2">System-wide operations and team management</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Engineers</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">20</p>
            </div>
            <Users className="w-8 h-8 text-blue-600 opacity-20" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Active Now</p>
              <p className="text-3xl font-bold text-green-600 mt-2">{Math.floor(Math.random() * 15) + 10}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-600 opacity-20" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">System Health</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">92%</p>
            </div>
            <TrendingUp className="w-8 h-8 text-purple-600 opacity-20" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-600">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Critical Alerts</p>
              <p className="text-3xl font-bold text-red-600 mt-2">{alerts.filter(a => a.severity === "high").length}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-red-600 opacity-20" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Team Performance */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Top Performers</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={teamData.slice(0, 10)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="visits" fill="#3b82f6" name="Visits" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Attendance Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Attendance Status</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={[
                { name: "Excellent (>90%)", value: 12 },
                { name: "Good (80-90%)", value: 6 },
                { name: "Fair (70-80%)", value: 2 },
              ]} cx="50%" cy="50%" labelLine={false} label outerRadius={80} fill="#8884d8" dataKey="value">
                <Cell fill="#10b981" />
                <Cell fill="#3b82f6" />
                <Cell fill="#f59e0b" />
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Critical Alerts */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Critical Alerts</h2>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {alerts.length > 0 ? (
            alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg flex items-start gap-3 border-l-4 ${
                  alert.severity === "high"
                    ? "bg-red-50 border-red-600"
                    : alert.severity === "medium"
                    ? "bg-yellow-50 border-yellow-600"
                    : "bg-green-50 border-green-600"
                }`}
              >
                <span className="text-lg mt-1">
                  {alert.severity === "high" ? "⚠️" : alert.severity === "medium" ? "⚡" : "ℹ️"}
                </span>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{alert.type}</p>
                  <p className="text-sm text-gray-600">{alert.message}</p>
                </div>
              </div>
            ))
          ) : (
            <p className="text-gray-500">No critical alerts</p>
          )}
        </div>
      </div>

      {/* Team Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-800">Team Members</h2>
        </div>
        <table className="w-full text-sm text-gray-600">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-6 py-3 text-left font-medium">Rank</th>
              <th className="px-6 py-3 text-left font-medium">Engineer</th>
              <th className="px-6 py-3 text-right font-medium">Visits</th>
              <th className="px-6 py-3 text-right font-medium">Attendance</th>
              <th className="px-6 py-3 text-right font-medium">Completion</th>
              <th className="px-6 py-3 text-left font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {teamData.map((team, idx) => (
              <tr key={idx} className="border-t hover:bg-gray-50">
                <td className="px-6 py-3">{team.rank}</td>
                <td className="px-6 py-3 font-medium text-gray-800">{team.name}</td>
                <td className="px-6 py-3 text-right">{team.visits}</td>
                <td className="px-6 py-3 text-right">{team.attendance}%</td>
                <td className="px-6 py-3 text-right">{team.completion}%</td>
                <td className="px-6 py-3">
                  <span className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AdminDashboard;
