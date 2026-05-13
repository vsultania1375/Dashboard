import { useState, useEffect, createContext, useContext } from "react";
import DataUploadPage from "./DataUploadPage";
import { ExportModule } from "./ExportModule";
import AnalyticsPage from "./AnalyticsPage";
import ReportPage from "./ReportPage";
import VisualizationPage from "./VisualizationPage";

// ─── CONFIG ───────────────────────────────────────────
const API = "/api";

async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(API + path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts.headers,
    },
    ...opts,
  });
  if (res.status === 401) {
    localStorage.clear();
    window.location.reload();
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ─── AUTH CONTEXT ─────────────────────────────────────
const AuthCtx = createContext(null);
function useAuth() {
  return useContext(AuthCtx);
}

// ─── COMPONENTS ───────────────────────────────────────
function Spinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function KPICard({ label, value, unit = "" }) {
  return (
    <div className="bg-white rounded-lg shadow border border-gray-100 p-4">
      <div className="text-xs text-gray-500 font-medium">{label}</div>
      <div className="text-2xl font-bold text-blue-700 mt-2">
        {value}
        {unit && <span className="text-sm ml-1">{unit}</span>}
      </div>
    </div>
  );
}

// ─── LOGIN PAGE ───────────────────────────────────────
function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const query = new URLSearchParams({
        username: form.username,
        password: form.password,
      });
      const res = await fetch(`${API}/auth/login?${query}`, {
        method: "POST",
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Invalid credentials");
        return;
      }

      // Store auth data
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);
      localStorage.setItem("state_code", data.state_code || "");

      // Trigger login handler
      onLogin({
        token: data.access_token,
        role: data.role,
        username: data.username,
        state_code: data.state_code,
      });
    } catch (err) {
      setError("Connection error. Is the server running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 to-blue-700 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-900">VProtect</h1>
          <p className="text-gray-500 text-sm mt-2">Field Service Dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              placeholder="Username"
              value={form.username}
              onChange={(e) =>
                setForm((f) => ({ ...f, username: e.target.value }))
              }
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) =>
                setForm((f) => ({ ...f, password: e.target.value }))
              }
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-900 text-white py-3 rounded-lg font-semibold hover:bg-blue-800 disabled:opacity-50 transition"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className="text-center text-xs text-gray-400 mt-6">
          Demo Credentials: admin / admin
        </div>
      </div>
    </div>
  );
}

// ─── DASHBOARD PAGE ───────────────────────────────────
function DashboardPage() {
  const auth = useAuth();
  const [kpis, setKpis] = useState(null);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch("/dashboard/kpis").catch(console.error),
      apiFetch("/dashboard/smart-insights").catch(console.error),
    ])
      .then(([kpiData, insightData]) => {
        setKpis(kpiData);
        setInsights(insightData?.insights || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis ? (
          <>
            <KPICard
              label="Total Engineers"
              value={kpis.total_engineers || 0}
            />
            <KPICard
              label="Total Visits"
              value={(kpis.total_visits || 0).toLocaleString()}
            />
            <KPICard label="Repeat Rate" value={kpis.avg_repeat_rate || 0} />
            <KPICard label="Offline Sites" value={kpis.offline_sites || 0} />
          </>
        ) : (
          <div className="col-span-4 text-center text-gray-400">
            No data available
          </div>
        )}
      </div>

      {/* Insights */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold mb-4">Smart Insights</h2>
        <div className="space-y-2">
          {insights.length > 0 ? (
            insights.map((insight, idx) => (
              <div
                key={idx}
                className="p-3 bg-blue-50 border-l-4 border-blue-500 rounded"
              >
                <p className="text-sm text-gray-800">{insight.insight_text}</p>
              </div>
            ))
          ) : (
            <p className="text-gray-400 text-sm">No insights available</p>
          )}
        </div>
      </div>

      {/* Sample Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold mb-4">Engineer Performance</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100 border-b">
                <th className="px-4 py-2 text-left">Engineer</th>
                <th className="px-4 py-2 text-left">State</th>
                <th className="px-4 py-2 text-right">Visits</th>
                <th className="px-4 py-2 text-right">Attendance %</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b hover:bg-gray-50">
                <td className="px-4 py-2">Raj Kumar</td>
                <td className="px-4 py-2">Karnataka</td>
                <td className="px-4 py-2 text-right">45</td>
                <td className="px-4 py-2 text-right">90%</td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="px-4 py-2">Priya Singh</td>
                <td className="px-4 py-2">Tamil Nadu</td>
                <td className="px-4 py-2 text-right">52</td>
                <td className="px-4 py-2 text-right">95%</td>
              </tr>
              <tr className="border-b hover:bg-gray-50">
                <td className="px-4 py-2">Amit Patel</td>
                <td className="px-4 py-2">Maharashtra</td>
                <td className="px-4 py-2 text-right">38</td>
                <td className="px-4 py-2 text-right">88%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── PERFORMANCE PAGE ──────────────────────────────────
function PerformancePage() {
  const [engineers, setEngineers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch("/engineers/performance/table?page=1&per_page=25")
      .then((data) => setEngineers(data.engineers || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Engineer Performance</h1>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-blue-900 text-white">
              <th className="px-4 py-3 text-left">Engineer Name</th>
              <th className="px-4 py-3 text-left">State</th>
              <th className="px-4 py-3 text-right">Visits</th>
              <th className="px-4 py-3 text-right">Att %</th>
              <th className="px-4 py-3 text-right">Closed</th>
              <th className="px-4 py-3 text-right">Offline</th>
            </tr>
          </thead>
          <tbody>
            {engineers.length > 0 ? (
              engineers.map((eng, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-4 py-3">{eng.engineer_name}</td>
                  <td className="px-4 py-3">{eng.state}</td>
                  <td className="px-4 py-3 text-right">{eng.total_visits}</td>
                  <td className="px-4 py-3 text-right">{eng.att_percent?.toFixed(1)}%</td>
                  <td className="px-4 py-3 text-right">{eng.closed}</td>
                  <td className="px-4 py-3 text-right">{eng.offline_sites}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6" className="px-4 py-3 text-center text-gray-400">
                  No data
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── OFFLINE PAGE ──────────────────────────────────────
function OfflineDistributionPage() {
  const [distribution, setDistribution] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch("/dashboard/offline-buckets")
      .then((data) => setDistribution(data.distribution || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Offline Distribution</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="space-y-3">
          {distribution && distribution.length > 0 ? (
            distribution.map((item, idx) => {
              const max = Math.max(...distribution.map((d) => d.count), 1);
              return (
                <div key={idx}>
                  <div className="flex justify-between mb-1">
                    <span className="font-medium text-sm">{item.bucket}</span>
                    <span className="text-sm text-gray-600">
                      {item.count} ({item.percent}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${(item.count / max) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })
          ) : (
            <p className="text-gray-400">No data</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────
export default function App() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("token");
    if (token) {
      return {
        token,
        role: localStorage.getItem("role") || "admin",
        username: localStorage.getItem("username") || "",
        state_code: localStorage.getItem("state_code") || "",
      };
    }
    return null;
  });

  const [currentPage, setCurrentPage] = useState("dashboard");

  const handleLogin = (userData) => {
    setAuth(userData);
    setCurrentPage("dashboard");
  };

  const handleLogout = () => {
    localStorage.clear();
    setAuth(null);
    setCurrentPage("dashboard");
  };

  if (!auth) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <AuthCtx.Provider value={auth}>
      <div className="flex h-screen bg-gray-50">
        {/* Sidebar */}
        <div className="w-56 bg-blue-900 text-white flex flex-col">
          <div className="p-4 border-b border-blue-800">
            <h2 className="font-bold">VProtect Dashboard</h2>
            <p className="text-xs text-blue-300">v2.0</p>
          </div>

          <nav className="flex-1 overflow-y-auto py-4">
            {[
              { id: "dashboard", label: "📊 Dashboard" },
              { id: "analytics", label: "📈 Analytics" },
              { id: "visualizations", label: "📉 Visualizations" },
              { id: "reports", label: "📄 Reports" },
              { id: "performance", label: "👥 Performance" },
              { id: "offline", label: "🔴 Offline Sites" },
              { id: "upload", label: "📤 Data Upload" },
              { id: "export", label: "📥 Export Data" },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`w-full text-left px-4 py-2 text-sm transition ${
                  currentPage === item.id
                    ? "bg-blue-700 font-semibold"
                    : "text-blue-200 hover:bg-blue-800"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="p-4 border-t border-blue-800">
            <p className="text-xs text-blue-300">{auth.username}</p>
            <p className="text-xs text-blue-400 mb-3">{auth.role}</p>
            <button
              onClick={handleLogout}
              className="text-xs text-blue-300 hover:text-white transition"
            >
              Sign Out
            </button>
          </div>
        </div>

          {/* Main Content */}
          <div className="flex-1 overflow-auto">
            <div className="p-6">
              {currentPage === "dashboard" && <DashboardPage />}
              {currentPage === "analytics" && <AnalyticsPage />}
              {currentPage === "visualizations" && <VisualizationPage />}
              {currentPage === "reports" && <ReportPage />}
              {currentPage === "performance" && <PerformancePage />}
              {currentPage === "offline" && <OfflineDistributionPage />}
              {currentPage === "upload" && <DataUploadPage />}
              {currentPage === "export" && <ExportModule />}
            </div>
          </div>
      </div>
    </AuthCtx.Provider>
  );
}
