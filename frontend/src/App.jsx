import { useState, useEffect, useCallback, createContext, useContext } from "react";

// ─── API CONFIG ───────────────────────────────────────────
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
  if (res.status === 401) { localStorage.clear(); window.location.reload(); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ─── AUTH CONTEXT ─────────────────────────────────────────
const AuthCtx = createContext(null);
function useAuth() { return useContext(AuthCtx); }

// ─── COLOUR HELPERS ───────────────────────────────────────
const RAG = {
  score: (v) => v >= 75 ? "text-green-600" : v >= 45 ? "text-amber-500" : "text-red-600",
  scoreBg: (v) => v >= 75 ? "bg-green-100 text-green-800" : v >= 45 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800",
  offline: (v) => v < 5 ? "text-green-600" : v < 15 ? "text-amber-500" : "text-red-600",
  offlineBg: (v) => v < 5 ? "bg-green-50 border-green-200" : v < 15 ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200",
  closure: (v) => v >= 80 ? "text-green-600" : v >= 50 ? "text-amber-500" : "text-red-600",
  severity: (s) => s === "CRITICAL" ? "bg-red-600 text-white" : s === "HIGH" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800",
};

const fmt = {
  pct: (v) => `${(+v || 0).toFixed(1)}%`,
  num: (v) => (+v || 0).toLocaleString("en-IN"),
  dec: (v, d = 1) => (+v || 0).toFixed(d),
};

// ─── SHARED COMPONENTS ───────────────────────────────────
function Spinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function KPICard({ label, value, unit = "", sub, color = "text-blue-700", alert }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border p-4 ${alert ? "border-red-300 bg-red-50" : "border-gray-100"}`}>
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}<span className="text-sm ml-1">{unit}</span></div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  );
}

function Badge({ label, color = "bg-gray-100 text-gray-700" }) {
  return <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>{label}</span>;
}

function InsightCard({ insight }) {
  const colors = {
    CRITICAL: "bg-red-50 border-l-4 border-red-500",
    WARNING: "bg-amber-50 border-l-4 border-amber-500",
    INFO: "bg-blue-50 border-l-4 border-blue-500",
  };
  const icons = { CRITICAL: "🚨", WARNING: "⚠️", INFO: "✅" };
  return (
    <div className={`p-3 rounded ${colors[insight.priority] || colors.INFO} mb-2`}>
      <span className="mr-2">{icons[insight.priority]}</span>
      <span className="text-sm font-medium">{insight.insight_text}</span>
      {insight.state && <Badge label={insight.state} color="bg-white text-gray-600 ml-2" />}
    </div>
  );
}

function DataTable({ headers, rows, emptyMsg = "No data" }) {
  if (!rows || rows.length === 0) {
    return <div className="text-center text-gray-400 py-8 text-sm">{emptyMsg}</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-blue-900 text-white">
            {headers.map((h, i) => (
              <th key={i} className="px-3 py-2 text-left font-medium text-xs whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-gray-50"}>
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-2 text-xs">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Simple bar chart with divs (no library needed)
function BarChart({ data, colorFn }) {
  const max = Math.max(...Object.values(data).map(Number), 1);
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([label, val]) => (
        <div key={label} className="flex items-center gap-2">
          <div className="text-xs text-gray-600 w-20 text-right shrink-0">{label}</div>
          <div className="flex-1 bg-gray-100 rounded h-5 relative">
            <div
              className={`h-5 rounded ${colorFn ? colorFn(label) : "bg-blue-500"}`}
              style={{ width: `${(Number(val) / max) * 100}%` }}
            />
          </div>
          <div className="text-xs text-gray-700 w-12 font-medium">{fmt.num(val)}</div>
        </div>
      ))}
    </div>
  );
}

// ─── LOGIN PAGE ───────────────────────────────────────────
function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const body = new URLSearchParams({ username: form.username, password: form.password });
      const res = await fetch(`${API}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Invalid credentials"); return; }
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("state_code", data.state_code || "");
      localStorage.setItem("username", data.username);
      onLogin(data);
    } catch { setError("Connection error. Is the server running?"); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 to-blue-700 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <div className="text-3xl font-bold text-blue-900">Service Analysis</div>
          <div className="text-gray-500 text-sm mt-1">Dashboard — PAN India Intelligence Platform</div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <input
            className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Username" value={form.username}
            onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required
          />
          <input
            type="password"
            className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Password" value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required
          />
          {error && <div className="text-red-600 text-sm bg-red-50 p-3 rounded">{error}</div>}
          <button
            type="submit" disabled={loading}
            className="w-full bg-blue-900 text-white py-3 rounded-lg font-semibold hover:bg-blue-800 disabled:opacity-50 transition"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
        <div className="text-center text-xs text-gray-400 mt-4">
          25,000 Sites · 250 Engineers · PAN India
        </div>
      </div>
    </div>
  );
}

// ─── SIDEBAR NAV ─────────────────────────────────────────
const NAV_ITEMS = [
  { id: "dashboard",    label: "Dashboard",       icon: "📊", roles: ["ops_manager","state_manager","admin"] },
  { id: "ops",          label: "Daily Ops",       icon: "📋", roles: ["ops_manager","state_manager","admin"] },
  { id: "distribution", label: "Activity Graph",  icon: "📉", roles: ["ops_manager","state_manager","admin"] },
  { id: "performance",  label: "Field Performance",icon: "📈", roles: ["ops_manager","state_manager","admin"] },
  { id: "tickets",      label: "Ticket Analysis", icon: "🎫", roles: ["ops_manager","state_manager","admin"] },
  { id: "engineers",    label: "Engineers",       icon: "👷", roles: ["ops_manager","state_manager","admin"] },
  { id: "states",       label: "State Intel",     icon: "🗺️", roles: ["ops_manager","admin"] },
  { id: "fraud",        label: "Fraud Flags",     icon: "🚩", roles: ["ops_manager","state_manager","admin"] },
  { id: "upload",       label: "Data Upload",     icon: "📤", roles: ["admin"] },
  { id: "users",        label: "User Mgmt",       icon: "👥", roles: ["admin"] },
];

function Sidebar({ page, setPage, role, username, onLogout, fraudCount }) {
  const items = NAV_ITEMS.filter(n => n.roles.includes(role));
  return (
    <div className="w-56 bg-blue-900 text-white flex flex-col h-screen fixed left-0 top-0 z-30">
      <div className="p-4 border-b border-blue-800">
        <div className="font-bold text-sm">Service Analysis</div>
        <div className="text-xs text-blue-300 mt-0.5">Dashboard v2.0</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {items.map(item => (
          <button
            key={item.id}
            onClick={() => setPage(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition ${page === item.id
              ? "bg-blue-700 text-white font-semibold" : "text-blue-200 hover:bg-blue-800"}`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
            {item.id === "fraud" && fraudCount > 0 && (
              <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {fraudCount > 99 ? "!" : fraudCount}
              </span>
            )}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-blue-800">
        <div className="text-xs text-blue-300">{username}</div>
        <div className="text-xs text-blue-400">{role?.replace("_", " ")}</div>
        <button onClick={onLogout} className="text-xs text-blue-400 hover:text-white mt-2">Sign out</button>
      </div>
    </div>
  );
}

// ─── DASHBOARD PAGE ───────────────────────────────────────
function DashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [insights, setInsights] = useState([]);
  const [stateHealth, setStateHealth] = useState([]);
  const [buckets, setBuckets] = useState({});
  const [digest, setDigest] = useState(null);
  const [worstEngineers, setWorstEngineers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    setLoading(true);
    apiFetch("/dashboard/smart-insights")
      .then(setInsights)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  const criticals = insights.filter(i => i.priority === "CRITICAL");
  const warnings  = insights.filter(i => i.priority === "WARNING");
  const infos     = insights.filter(i => i.priority === "INFO");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Dashboard Overview</h1>
        <div className="text-sm text-gray-500">{new Date().toLocaleDateString("en-IN", { dateStyle: "full" })}</div>
      </div>

      {/* Smart Insights */}
      {insights.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center text-gray-400 text-sm">
          No insights generated yet. Upload today's data files to trigger the ETL pipeline.
        </div>
      ) : (
        <div className="space-y-3">
          {criticals.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-red-200 p-4">
              <div className="text-sm font-bold text-red-700 mb-3">CRITICAL ({criticals.length}) — Action Required Today</div>
              <div className="space-y-2">
                {criticals.map((ins, i) => <InsightCard key={i} insight={ins} />)}
              </div>
            </div>
          )}
          {warnings.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-amber-200 p-4">
              <div className="text-sm font-bold text-amber-700 mb-3">WARNING ({warnings.length})</div>
              <div className="space-y-2">
                {warnings.map((ins, i) => <InsightCard key={i} insight={ins} />)}
              </div>
            </div>
          )}
          {infos.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-4">
              <div className="text-sm font-bold text-blue-700 mb-3">INFO ({infos.length})</div>
              <div className="space-y-2">
                {infos.map((ins, i) => <InsightCard key={i} insight={ins} />)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TODO: KPI cards, state health, offline buckets, digest — commented out until data is ready
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4"> ... </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100"> ... </div>
      */}
    </div>
  );
}

// ─── ENGINEER LEADERBOARD PAGE ────────────────────────────
function EngineersPage() {
  const [data, setData] = useState(null);
  const [profile, setProfile] = useState(null);
  const [sortBy, setSortBy] = useState("composite_score");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [profLoading, setProfLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    apiFetch(`/engineers/leaderboard?sort_by=${sortBy}&sort_dir=asc&page=${page}`)
      .then(setData).catch(console.error).finally(() => setLoading(false));
  }, [sortBy, page]);

  useEffect(() => { load(); }, [load]);

  const openProfile = (code) => {
    setProfLoading(true);
    apiFetch(`/engineers/${code}/profile`)
      .then(setProfile).catch(console.error).finally(() => setProfLoading(false));
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Engineer Leaderboard</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sort by:</span>
          {["composite_score","closure_rate","coverage_rate","avg_resolution_days"].map(s => (
            <button key={s} onClick={() => setSortBy(s)}
              className={`text-xs px-2 py-1 rounded ${sortBy === s ? "bg-blue-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-blue-900 text-white">
                {["#","Name","State","Score","Productive Days","Closure","Coverage","Visits (Eff/Tot)","Fraud Flags","Actions"].map((h, i) => (
                  <th key={i} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.engineers.map((eng, i) => (
                <tr key={i}
                  className={`border-b ${i % 2 === 0 ? "bg-white" : "bg-gray-50"} ${eng.is_forced_red ? "border-l-4 border-red-500" : ""}`}>
                  <td className="px-3 py-2 text-gray-400">{(page - 1) * 25 + i + 1}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-800">{eng.employee_name}</div>
                    <div className="text-gray-400">{eng.employee_code}</div>
                  </td>
                  <td className="px-3 py-2 text-gray-600">{eng.state}</td>
                  <td className="px-3 py-2">
                    <span className={`font-bold text-base ${RAG.score(eng.composite_score)}`}>{fmt.dec(eng.composite_score, 0)}</span>
                    <div><Badge label={eng.score_band || "—"} color={RAG.scoreBg(eng.composite_score)} /></div>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`font-bold ${eng.productive_days < eng.present_days * 0.6 ? "text-red-600" : "text-green-600"}`}>
                      {eng.productive_days}/{eng.present_days}
                    </span>
                  </td>
                  <td className={`px-3 py-2 font-medium ${RAG.closure(eng.closure_rate)}`}>{fmt.pct(eng.closure_rate)}</td>
                  <td className={`px-3 py-2 ${eng.coverage_rate < 50 ? "text-red-600" : "text-gray-700"}`}>{fmt.pct(eng.coverage_rate)}</td>
                  <td className="px-3 py-2">
                    <span className={eng.effective_visits < eng.total_visits * 0.5 ? "text-red-600 font-medium" : ""}>
                      {eng.effective_visits}/{eng.total_visits}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    {(eng.fv_high_flags + eng.pattern_critical_flags) > 0 && (
                      <Badge label={`${eng.fv_high_flags + eng.pattern_critical_flags} flags`}
                        color={RAG.severity(eng.pattern_critical_flags > 0 ? "CRITICAL" : "HIGH")} />
                    )}
                    {eng.fv_high_flags + eng.pattern_critical_flags === 0 && <span className="text-green-600">✓ Clear</span>}
                  </td>
                  <td className="px-3 py-2">
                    <button onClick={() => openProfile(eng.employee_code)}
                      className="text-blue-600 hover:underline">Profile</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-4 border-t">
          <div className="text-xs text-gray-500">{data?.total} engineers total</div>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}
              className="px-3 py-1 text-xs bg-gray-100 rounded disabled:opacity-40">← Prev</button>
            <span className="text-xs text-gray-600 py-1">Page {page}</span>
            <button onClick={() => setPage(p => p+1)} disabled={data?.engineers.length < 25}
              className="px-3 py-1 text-xs bg-gray-100 rounded disabled:opacity-40">Next →</button>
          </div>
        </div>
      </div>

      {/* Engineer Profile Modal */}
      {(profile || profLoading) && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-8 pb-8 px-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                {profLoading ? <Spinner /> : <>
                  <div className="font-bold text-lg">{profile?.engineer?.employee_name}</div>
                  <div className="text-sm text-gray-500">{profile?.engineer?.state} · {profile?.engineer?.service_area_name}</div>
                </>}
              </div>
              <button onClick={() => setProfile(null)} className="text-gray-400 hover:text-gray-600 text-2xl">×</button>
            </div>
            {profile && !profLoading && (
              <div className="p-4 space-y-4">
                {/* Headline Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <KPICard label="Composite Score" value={fmt.dec(profile.engineer.composite_score, 0)} unit="/100"
                    color={RAG.score(profile.engineer.composite_score)} />
                  <KPICard label="Productive / Present"
                    value={`${profile.engineer.productive_days}/${profile.engineer.present_days}`}
                    color={profile.engineer.productive_days < profile.engineer.present_days * 0.6 ? "text-red-600" : "text-green-600"} />
                  <KPICard label="Effective / Total Visits"
                    value={`${profile.engineer.effective_visits}/${profile.engineer.total_visits}`}
                    color={profile.engineer.effective_visits < profile.engineer.total_visits * 0.5 ? "text-red-600" : "text-blue-700"} />
                  <KPICard label="Fraud Flags"
                    value={profile.engineer.fv_high_flags + profile.engineer.pattern_critical_flags}
                    color={profile.engineer.pattern_critical_flags > 0 ? "text-red-600" : "text-green-600"} />
                </div>

                {/* Score Components */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs font-bold text-gray-700 mb-2">Score Breakdown</div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    {[
                      ["Closure Rate", profile.engineer.score_closure, 25],
                      ["Coverage", profile.engineer.score_coverage, 20],
                      ["Resolution Time", profile.engineer.score_resolution, 20],
                      ["Area Offline", profile.engineer.score_area_offline, 15],
                      ["Repeat Rate", profile.engineer.score_repeat, 10],
                      ["Attendance", profile.engineer.score_attendance, 7],
                      ["Fraud Flags", profile.engineer.score_fraud, 3],
                    ].map(([label, score, max], i) => (
                      <div key={i} className="bg-white rounded p-2">
                        <div className="text-gray-500">{label}</div>
                        <div className="font-bold text-blue-700">{fmt.dec(score, 1)}<span className="text-gray-400">/{max}</span></div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Monthly Trend */}
                {profile.monthly_trend?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-gray-700 mb-2">Monthly Score Trend</div>
                    <div className="flex gap-3">
                      {[...profile.monthly_trend].reverse().map((m, i) => (
                        <div key={i} className="flex-1 bg-gray-50 rounded p-2 text-center">
                          <div className="text-xs text-gray-500">{m.year_month}</div>
                          <div className={`text-lg font-bold ${RAG.score(m.composite_score)}`}>{fmt.dec(m.composite_score, 0)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Attendance Calendar */}
                {profile.attendance_calendar?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-gray-700 mb-2">Attendance Calendar (Current Month)</div>
                    <div className="grid grid-cols-7 gap-1">
                      {profile.attendance_calendar.map((day, i) => {
                        const isPresent = day.attendance_status?.toLowerCase().includes("present");
                        const isOneVisit = day.is_one_visit_day;
                        const bg = !isPresent ? "bg-red-100" :
                          isOneVisit ? "bg-amber-200 border-2 border-red-400" :
                          day.is_productive_day ? "bg-green-100" : "bg-blue-50";
                        return (
                          <div key={i} title={`${day.attendance_date}: ${day.attendance_status}, ${day.daily_visits} visits`}
                            className={`rounded p-1 text-center text-xs ${bg}`}>
                            <div className="text-gray-500">{new Date(day.attendance_date).getDate()}</div>
                            <div className="font-bold">{day.daily_visits || 0}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex gap-3 mt-2 text-xs text-gray-500">
                      <span className="flex items-center gap-1"><span className="w-3 h-3 bg-green-100 rounded" /> Productive</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-200 border border-red-400 rounded" /> One-Visit Flag</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 bg-red-100 rounded" /> Absent</span>
                    </div>
                  </div>
                )}

                {/* Fraud Flags */}
                {profile.fraud_flags?.length > 0 && (
                  <div>
                    <div className="text-xs font-bold text-red-700 mb-2">Fraud Flags ({profile.fraud_flags.length})</div>
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                      {profile.fraud_flags.map((f, i) => (
                        <div key={i} className="flex items-start gap-2 p-2 bg-red-50 rounded text-xs">
                          <Badge label={f.pattern_id} color={RAG.severity(f.severity)} />
                          <span className="text-gray-700">{f.description}</span>
                          <Badge label={f.review_status} color="bg-gray-100 text-gray-600 ml-auto shrink-0" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── TICKET ANALYSIS PAGE ─────────────────────────────────
function TicketsPage() {
  const [data, setData] = useState(null);
  const [chronic, setChronic] = useState([]);
  const [activeTab, setActiveTab] = useState("status");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiFetch("/tickets/analysis"),
      apiFetch("/tickets/chronic-pending"),
    ]).then(([ta, cp]) => { setData(ta); setChronic(cp); })
      .catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  const tabs = ["status","aging","breach","sentback","no-ticket","chronic-pending"];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Ticket Analysis</h1>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="border-b flex overflow-x-auto">
          {tabs.map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap capitalize transition ${activeTab === tab ? "border-b-2 border-blue-700 text-blue-700" : "text-gray-500 hover:text-gray-700"}`}>
              {tab.replace(/-/g, " ")}
            </button>
          ))}
        </div>
        <div className="p-4">
          {activeTab === "status" && (
            <DataTable
              headers={["Status","Count","% of Total"]}
              rows={(data?.status_distribution || []).map(r => [
                <Badge label={r.ticket_status}
                  color={r.ticket_status === "CLOSED" ? "bg-green-100 text-green-800" :
                    r.ticket_status === "OPEN" ? "bg-blue-100 text-blue-800" :
                    r.ticket_status === "SENTBACK" ? "bg-red-100 text-red-800" :
                    "bg-gray-100 text-gray-700"} />,
                fmt.num(r.count), fmt.pct(r.pct)
              ])}
            />
          )}
          {activeTab === "aging" && data?.aging_bands && (
            <BarChart data={{
              "0-1 Days": data.aging_bands.d0_1,
              "2-3 Days": data.aging_bands.d2_3,
              "4-7 Days": data.aging_bands.d4_7,
              "8-15 Days": data.aging_bands.d8_15,
              "15+ Days": data.aging_bands.d15plus,
            }} colorFn={(label) =>
              label === "0-1 Days" ? "bg-green-400" : label === "2-3 Days" ? "bg-yellow-400" :
              label === "4-7 Days" ? "bg-amber-500" : label === "8-15 Days" ? "bg-orange-500" : "bg-red-600"
            } />
          )}
          {activeTab === "breach" && (
            <DataTable
              headers={["Ticket ID","CS ID","Site","State","Status","Aging","Planned","Engineer"]}
              rows={(data?.breach_list || []).map(r => [
                r.ticket_id, r.cs_id,
                <span className="text-xs">{r.oracle_site_name?.substring(0, 30)}</span>,
                r.state_name,
                <Badge label={r.ticket_status} color="bg-amber-100 text-amber-800" />,
                <span className={`font-bold ${r.aging_days >= 7 ? "text-red-600" : "text-amber-500"}`}>{r.aging_days}d</span>,
                r.planned_date || <span className="text-red-400">Not set</span>,
                r.ticket_assigned_to?.substring(0, 25)
              ])}
              emptyMsg="No SLA breaches — great work!"
            />
          )}
          {activeTab === "sentback" && (
            <DataTable
              headers={["Engineer","SENTBACK Count","Closed Tickets"]}
              rows={(data?.sentback_by_engineer || []).map(r => [
                r.ticket_assigned_to?.substring(0, 30),
                <span className="font-bold text-red-600">{r.sentback_count}</span>,
                r.closed_count
              ])}
              emptyMsg="No SENTBACK tickets — quality is good!"
            />
          )}
          {activeTab === "no-ticket" && (
            <div>
              <div className="text-xs text-gray-500 mb-3">Sites offline 4+ days with no active ticket. Sorted by days offline.</div>
              <DataTable
                headers={["CS ID","Site Name","State","Days Offline","Bucket","Engineer"]}
                rows={(data?.no_ticket_offline_sites || []).map(r => [
                  r.cs_no,
                  <span className="text-xs">{r.site_name?.substring(0, 30)}</span>,
                  r.state,
                  <span className="font-bold text-red-600">{r.offline_days}</span>,
                  <Badge label={r.bucket} color="bg-red-100 text-red-800" />,
                  r.employee_name || <span className="text-gray-400">Not assigned</span>
                ])}
                emptyMsg="All offline sites have active tickets — good!"
              />
            </div>
          )}
          {activeTab === "chronic-pending" && (
            <div>
              <div className="text-xs text-gray-500 mb-3">PENDING tickets with identical reason unchanged for 15+ days (non-stock). Detected via daily snapshot comparison.</div>
              <DataTable
                headers={["Ticket ID","CS ID","Engineer","Reason (unchanged)","Aging (days)"]}
                rows={chronic.map(r => [
                  r.ticket_id, r.cs_id, r.employee_name,
                  <span className="italic text-gray-600">{r.description?.substring(r.description.indexOf("'") + 1, r.description.lastIndexOf("'")) || "—"}</span>,
                  <span className="font-bold text-amber-600">{JSON.parse(r.data_evidence || "{}").aging_days || "—"}</span>
                ])}
                emptyMsg="No chronic PENDING tickets detected (or snapshots not yet 15 days old)"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── STATE INTELLIGENCE PAGE ──────────────────────────────
function StatesPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/states/comparison").then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">State Intelligence — PAN India Comparison</h1>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-blue-900 text-white">
              {["#","State","Zone","State Score","Avg Eng Score","Offline %","Sites>30D","Closure","Avg Res(d)","Engineers","Fraud Flags"].map((h, i) => (
                <th key={i} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((s, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                <td className="px-3 py-2 text-gray-400">{i + 1}</td>
                <td className="px-3 py-2 font-medium">{s.state}</td>
                <td className="px-3 py-2 text-gray-500">{s.zone}</td>
                <td className={`px-3 py-2 font-bold ${RAG.score(s.state_score)}`}>{fmt.dec(s.state_score, 0)}</td>
                <td className={`px-3 py-2 ${RAG.score(s.avg_engineer_score)}`}>{fmt.dec(s.avg_engineer_score, 0)}</td>
                <td className={`px-3 py-2 font-medium ${RAG.offline(s.avg_offline_rate)}`}>{fmt.pct(s.avg_offline_rate)}</td>
                <td className={`px-3 py-2 ${s.sites_offline_30plus > 100 ? "text-red-600 font-bold" : ""}`}>{s.sites_offline_30plus}</td>
                <td className={`px-3 py-2 ${RAG.closure(s.closure_rate)}`}>{fmt.pct(s.closure_rate)}</td>
                <td className={`px-3 py-2 ${s.avg_resolution_days >= 7 ? "text-red-600" : ""}`}>{fmt.dec(s.avg_resolution_days)}</td>
                <td className="px-3 py-2">{s.total_engineers}</td>
                <td className={`px-3 py-2 ${s.fraud_flags_count > 5 ? "text-red-600 font-bold" : ""}`}>{s.fraud_flags_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── FRAUD FLAGS PAGE ─────────────────────────────────────
function FraudPage() {
  const auth = useAuth();
  const [flags, setFlags] = useState([]);
  const [filter, setFilter] = useState({ pattern: "ALL", severity: "ALL" });
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(null);

  const load = () => {
    setLoading(true);
    const q = new URLSearchParams({ review_status: "PENDING" });
    if (filter.pattern !== "ALL") q.set("pattern_id", filter.pattern);
    if (filter.severity !== "ALL") q.set("severity", filter.severity);
    apiFetch(`/fraud/flags?${q}`).then(setFlags).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  const review = async (id, action, note = "") => {
    const body = new FormData();
    body.append("action", action); body.append("note", note);
    await fetch(`${API}/fraud/flags/${id}/review`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      body
    });
    setReviewing(null); load();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Fraud & Compliance Flags</h1>

      <div className="flex gap-3 flex-wrap">
        {["ALL","P1","P2","P3","P7","FV-01","FV-03","FV-04","FV-06"].map(p => (
          <button key={p} onClick={() => setFilter(f => ({ ...f, pattern: p }))}
            className={`text-xs px-3 py-1 rounded-full ${filter.pattern === p ? "bg-blue-900 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {p}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          {["ALL","CRITICAL","HIGH","MEDIUM"].map(s => (
            <button key={s} onClick={() => setFilter(f => ({ ...f, severity: s }))}
              className={`text-xs px-3 py-1 rounded ${filter.severity === s ? "bg-red-700 text-white" : "bg-gray-100 text-gray-600"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {loading ? <Spinner /> : (
        <div className="space-y-2">
          {flags.length === 0 && (
            <div className="text-center text-green-600 py-12 bg-white rounded-xl border">
              ✅ No pending fraud flags for the current filter.
            </div>
          )}
          {flags.map((f, i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge label={f.pattern_id} color={RAG.severity(f.severity)} />
                  <Badge label={f.severity} color={RAG.severity(f.severity)} />
                  <span className="font-medium text-sm">{f.employee_name}</span>
                  <span className="text-xs text-gray-500">[{f.employee_code}]</span>
                  <Badge label={f.state} color="bg-blue-50 text-blue-700" />
                  {f.ticket_id && <span className="text-xs text-gray-400">Ticket: {f.ticket_id}</span>}
                </div>
                {auth?.role !== "state_manager" && (
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => review(f.id, "VALID", "Reviewed and confirmed as valid")}
                      className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded hover:bg-green-200">✓ Valid</button>
                    <button onClick={() => setReviewing(f)}
                      className="text-xs bg-red-100 text-red-700 px-3 py-1 rounded hover:bg-red-200">🚩 Confirm Fake</button>
                  </div>
                )}
              </div>
              <div className="mt-2 text-sm text-gray-700">{f.description}</div>
              <div className="mt-1 text-xs text-gray-400">{f.flag_date} · Score impact: {f.score_impact}</div>
            </div>
          ))}
        </div>
      )}

      {/* Review modal */}
      {reviewing && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="font-bold text-red-700 mb-2">Confirm as Fake Visit</div>
            <div className="text-sm text-gray-600 mb-4">{reviewing.description}</div>
            <textarea id="review-note" rows={3} placeholder="Required: Reason for confirming as fake..."
              className="w-full border rounded p-2 text-sm mb-4" />
            <div className="flex gap-3">
              <button onClick={() => review(reviewing.id, "CONFIRMED_FAKE", document.getElementById("review-note").value)}
                className="flex-1 bg-red-600 text-white py-2 rounded font-medium hover:bg-red-700">
                Confirm Fake (–5 pts)
              </button>
              <button onClick={() => setReviewing(null)}
                className="flex-1 bg-gray-100 text-gray-700 py-2 rounded font-medium">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── UPLOAD PAGE ──────────────────────────────────────────
function UploadPage() {
  const [history, setHistory] = useState([]);
  const [uploading, setUploading] = useState({});
  const [results, setResults] = useState({});

  useEffect(() => {
    apiFetch("/upload/history").then(setHistory).catch(console.error);
  }, []);

  const uploadFile = async (fileType, file) => {
    setUploading(u => ({ ...u, [fileType]: true }));
    setResults(r => ({ ...r, [fileType]: null }));
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/upload/${fileType}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        body: form
      });
      const data = await res.json();
      setResults(r => ({ ...r, [fileType]: { ...data, ok: res.ok } }));
      if (res.ok) apiFetch("/upload/history").then(setHistory).catch(console.error);
    } catch (e) {
      setResults(r => ({ ...r, [fileType]: { ok: false, status: "ERROR", errors: [e.message] } }));
    }
    setUploading(u => ({ ...u, [fileType]: false }));
  };

  const FILE_TYPES = [
    { key: "b2b_offline",  label: "B2B Offline Data",      mode: "Daily — Full Replace",   required: "B2B Offline DD-MM-YYYY.xlsx" },
    { key: "view_ticket",  label: "View Ticket Dump",       mode: "Daily — Full Replace + Snapshot", required: "View Ticket.xlsx" },
    { key: "attendance",   label: "Attendance Report",      mode: "Daily — APPEND ONLY ⚠️", required: "AttendanceReport.xlsx" },
    { key: "engineer",            label: "Engineer Data",          mode: "Periodic — Full Replace", required: "EngineerData.xlsx" },
    { key: "site_master",         label: "Customer Site Master",   mode: "Periodic — Full Replace", required: "Customer_site_mst.csv" },
    { key: "visit_master",        label: "Visit Master",           mode: "Periodic — APPEND ONLY ⚠️", required: "VisitMaster.xlsx" },
    { key: "service_area_master", label: "Service Area Master",    mode: "Periodic — Full Replace", required: "ServiceAreaMaster.xlsx" },
    { key: "visit_form",          label: "Visit Form Data",        mode: "Daily — APPEND ONLY ⚠️",  required: "VisitForm.xlsx" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Data Upload & Management</h1>

      <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-sm">
        <strong>Daily Upload Order:</strong> 1. B2B Offline → 2. View Ticket → 3. Attendance. Upload all 3 before 9:00 AM.
        ETL pipeline runs automatically after each upload (~20-30 minutes).
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {FILE_TYPES.map(ft => {
          const res = results[ft.key];
          const loading = uploading[ft.key];
          return (
            <div key={ft.key} className={`bg-white rounded-xl border p-4 shadow-sm ${ft.key === "attendance" ? "border-amber-300" : "border-gray-100"}`}>
              <div className="font-semibold text-sm text-gray-800">{ft.label}</div>
              <div className={`text-xs mt-0.5 mb-3 ${ft.key === "attendance" ? "text-amber-700 font-bold" : "text-gray-500"}`}>{ft.mode}</div>
              <div className="text-xs text-gray-400 mb-3">Expected: {ft.required}</div>
              <input type="file" accept=".xlsx,.xls,.csv"
                disabled={loading}
                onChange={e => e.target.files[0] && uploadFile(ft.key, e.target.files[0])}
                className="block w-full text-xs text-gray-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
              />
              {loading && <div className="mt-2 text-xs text-blue-600 flex items-center gap-1"><div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" /> Processing & running ETL...</div>}
              {res && (
                <div className={`mt-2 p-2 rounded text-xs ${res.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                  {res.ok ? (
                    <div>✅ {res.rows_loaded} rows loaded. ETL: {res.etl_status}.
                      {res.warnings?.length > 0 && <div className="mt-1 text-amber-600">Warnings: {res.warnings.join("; ")}</div>}
                    </div>
                  ) : (
                    <div>❌ {(res.errors || []).join("; ")}</div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Upload History */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className="p-4 border-b font-semibold text-sm text-gray-700">Upload History (Last 50)</div>
        <DataTable
          headers={["File Type","Filename","Uploaded","By","Rows","Status","ETL"]}
          rows={history.map(h => [
            <Badge label={h.file_type} color="bg-blue-50 text-blue-800" />,
            h.original_filename?.substring(0, 30),
            new Date(h.upload_datetime).toLocaleString("en-IN"),
            h.uploaded_by,
            fmt.num(h.row_count),
            <Badge label={h.validation_status}
              color={h.validation_status === "SUCCESS" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"} />,
            <Badge label={h.etl_status}
              color={h.etl_status === "COMPLETE" ? "bg-green-100 text-green-700" :
                h.etl_status === "RUNNING" ? "bg-blue-100 text-blue-700" : "bg-red-100 text-red-700"} />
          ])}
          emptyMsg="No uploads yet"
        />
      </div>
    </div>
  );
}

// ─── USER MANAGEMENT PAGE ─────────────────────────────────
function UsersPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ username: "", password: "", role: "state_manager", state_code: "" });
  const [msg, setMsg] = useState("");

  const load = () => apiFetch("/users").then(setUsers).catch(console.error);
  useEffect(load, []);

  const create = async (e) => {
    e.preventDefault(); setMsg("");
    try {
      await apiFetch("/users", { method: "POST", body: JSON.stringify(form) });
      setMsg("User created successfully"); setForm({ username: "", password: "", role: "state_manager", state_code: "" });
      load();
    } catch (err) { setMsg("Error: " + err.message); }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">User Management</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <div className="font-semibold text-sm mb-4">Create New User</div>
          <form onSubmit={create} className="space-y-3">
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Username"
              value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required />
            <input type="password" className="w-full border rounded px-3 py-2 text-sm" placeholder="Password (min 10 chars)"
              value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required minLength={10} />
            <select className="w-full border rounded px-3 py-2 text-sm"
              value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option value="state_manager">State Manager</option>
              <option value="ops_manager">Ops Manager</option>
              <option value="admin">Admin</option>
            </select>
            {form.role === "state_manager" && (
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="State Code (e.g. Karnataka)"
                value={form.state_code} onChange={e => setForm(f => ({ ...f, state_code: e.target.value }))} required />
            )}
            {msg && <div className={`text-xs p-2 rounded ${msg.startsWith("Error") ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600"}`}>{msg}</div>}
            <button type="submit" className="w-full bg-blue-900 text-white py-2 rounded text-sm font-medium hover:bg-blue-800">Create User</button>
          </form>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="p-4 border-b font-semibold text-sm">Active Users</div>
          <DataTable
            headers={["Username","Role","State","Last Login","Active"]}
            rows={users.map(u => [
              u.username,
              <Badge label={u.role.replace("_"," ")} color="bg-blue-50 text-blue-800" />,
              u.state_code || <span className="text-gray-400">All states</span>,
              u.last_login ? new Date(u.last_login).toLocaleDateString("en-IN") : <span className="text-gray-400">Never</span>,
              u.is_active ? "✅" : "❌"
            ])}
          />
        </div>
      </div>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────
export default function App() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const username = localStorage.getItem("username");
    const state_code = localStorage.getItem("state_code");
    return token ? { token, role, username, state_code } : null;
  });
  const [page, setPage] = useState("dashboard");
  const [fraudCount, setFraudCount] = useState(0);

  const handleLogin = (data) => {
    setAuth({ token: data.access_token, role: data.role, username: data.username, state_code: data.state_code });
  };

  const handleLogout = () => {
    localStorage.clear(); setAuth(null);
  };

  useEffect(() => {
    if (!auth) return;
    apiFetch("/fraud/flags?review_status=PENDING")
      .then(flags => setFraudCount(flags.length)).catch(() => {});
  }, [auth, page]);

  if (!auth) return <LoginPage onLogin={handleLogin} />;

  const PAGE_MAP = {
    dashboard:   <DashboardPage />,
    tickets:     <TicketsPage />,
    engineers:   <EngineersPage />,
    performance: <PerformanceTablePage />,
    distribution: <DistributionGraphPage />,
    states:      <StatesPage />,
    fraud:       <FraudPage />,
    ops:         <DailyOpsPage />,
    visits:      <VisitFormsPage />,
    upload:      <UploadPage />,
    users:       <UsersPage />,
  };

  return (
    <AuthCtx.Provider value={auth}>
      <div className="min-h-screen bg-gray-50 flex">
        <Sidebar
          page={page} setPage={setPage}
          role={auth.role} username={auth.username}
          onLogout={handleLogout} fraudCount={fraudCount}
        />
        <div className="ml-56 flex-1 p-6 max-w-screen-xl">
          {PAGE_MAP[page] || <DashboardPage />}
        </div>
      </div>
    </AuthCtx.Provider>
  );
}

// ─── DAILY OPS REPORT PAGE ────────────────────────────────
function DailyOpsPage() {
  const auth = useAuth();
  const [sitesData, setSitesData] = useState([]);
  const [engData, setEngData] = useState([]);
  const [stateData, setStateData] = useState(null);
  const [attData, setAttData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [attDate, setAttDate] = useState("");

  const loadAtt = (d) => {
    const q = d ? `?target_date=${d}` : "";
    apiFetch(`/ops/attendance-analysis${q}`).then(setAttData).catch(console.error);
  };

  useEffect(() => {
    setLoading(true);
    const promises = [
      apiFetch("/ops/sites-visited-datewise").then(setSitesData),
      apiFetch("/ops/engineers-used-app-datewise").then(setEngData),
      apiFetch("/ops/attendance-analysis").then(setAttData),
    ];
    if (auth.role !== "state_manager") {
      promises.push(apiFetch("/ops/statewise-visits").then(setStateData));
    }
    Promise.all(promises).catch(console.error).finally(() => setLoading(false));
  }, []);

  const pctColor = (v) => v >= 80 ? "bg-green-100 text-green-800" : v >= 60 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
  const avgColor = (v) => v >= 2.5 ? "bg-green-100 text-green-800" : v >= 1 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";

  if (loading) return <div className="flex items-center justify-center p-8"><div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /></div>;

  const maxSites = Math.max(...sitesData.map(r => r.sites_visited), 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Daily Operations Report</h1>
        <div className="text-sm text-gray-500">{new Date().toLocaleDateString("en-IN", { dateStyle: "full" })}</div>
      </div>

      {/* Row 1: Sites Visited + Engineers Used App */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Sites Visited Date Wise */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="text-sm font-bold text-gray-700 mb-4">📍 No. of Sites Visited — Date Wise (Last 7 Days)</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-blue-900 text-white">
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-center">Sites Visited</th>
                <th className="px-3 py-2 text-left">Bar</th>
              </tr>
            </thead>
            <tbody>
              {sitesData.map((r, i) => {
                const isYesterday = i === sitesData.length - 1;
                const barW = Math.round((r.sites_visited / maxSites) * 100);
                const barColor = r.sites_visited >= 300 ? "bg-green-400" : r.sites_visited >= 200 ? "bg-yellow-400" : "bg-red-400";
                return (
                  <tr key={i} className={`${isYesterday ? "font-bold bg-blue-50" : i % 2 === 0 ? "bg-white" : "bg-gray-50"}`}>
                    <td className="px-3 py-2 text-xs">{r.day_label}{isYesterday && <span className="ml-1 text-blue-600 text-xs">(Yesterday)</span>}</td>
                    <td className="px-3 py-2 text-center font-bold">{r.sites_visited}</td>
                    <td className="px-3 py-2">
                      <div className="bg-gray-100 rounded h-4 w-full">
                        <div className={`h-4 rounded ${barColor}`} style={{ width: `${barW}%` }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Engineers Used App */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="text-sm font-bold text-gray-700 mb-4">👷 No. of Engineers Used App — Date Wise (Last 7 Days)</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-blue-900 text-white">
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-center">Engineers</th>
                <th className="px-3 py-2 text-center">% Usage</th>
              </tr>
            </thead>
            <tbody>
              {engData.map((r, i) => {
                const isYesterday = i === engData.length - 1;
                return (
                  <tr key={i} className={`${isYesterday ? "font-bold bg-blue-50" : i % 2 === 0 ? "bg-white" : "bg-gray-50"}`}>
                    <td className="px-3 py-2 text-xs">{r.day_label}{isYesterday && <span className="ml-1 text-blue-600 text-xs">(Yesterday)</span>}</td>
                    <td className="px-3 py-2 text-center font-bold">{r.engineers_used_app}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${pctColor(r.percentage)}`}>
                        {r.percentage.toFixed(3)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* State Wise Visits Table */}
      {stateData && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="text-sm font-bold text-gray-700 mb-4">
            🗺️ No. of Sites Visited — State Wise
            <span className="ml-2 text-xs font-normal text-gray-500">
              {stateData.day_before} vs {stateData.yesterday}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-blue-900 text-white">
                  <th className="px-3 py-2 text-left">State</th>
                  <th className="px-3 py-2 text-center">{new Date(stateData.day_before).toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric" })}</th>
                  <th className="px-3 py-2 text-center">{new Date(stateData.yesterday).toLocaleDateString("en-IN", { day: "2-digit", month: "2-digit", year: "numeric" })}</th>
                  <th className="px-3 py-2 text-center">Offline &gt; 3 Days</th>
                  <th className="px-3 py-2 text-center">Total Eng.</th>
                  <th className="px-3 py-2 text-center">AVG TKT Closure / Eng</th>
                </tr>
              </thead>
              <tbody>
                {stateData.data.map((r, i) => {
                  const isTotal = r.state === "Grand Total";
                  return (
                    <tr key={i} className={isTotal ? "bg-blue-900 text-white font-bold" : i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                      <td className="px-3 py-2 font-medium">{r.state}</td>
                      <td className="px-3 py-2 text-center">{r.visited_day_before}</td>
                      <td className="px-3 py-2 text-center font-bold">{r.visited_yesterday}</td>
                      <td className="px-3 py-2 text-center text-red-600 font-semibold">{r.offline_gt3 || 0}</td>
                      <td className="px-3 py-2 text-center">{r.total_engineers}</td>
                      <td className="px-3 py-2 text-center">
                        {isTotal ? (
                          <span className="font-bold">{r.avg_closure_per_engineer}</span>
                        ) : (
                          <span className={`px-2 py-0.5 rounded font-bold ${avgColor(r.avg_closure_per_engineer)}`}>
                            {r.avg_closure_per_engineer}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Attendance Analysis */}
      {attData && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-bold text-gray-700">
              🕐 Attendance Analysis — {new Date(attData.date + "T00:00:00").toLocaleDateString("en-IN", { dateStyle: "full" })}
              <span className="ml-2 text-xs font-normal text-gray-500">(ON TIME = before 10:30 AM)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Select date:</span>
              <input
                type="date"
                className="border rounded px-2 py-1 text-xs"
                value={attDate}
                onChange={e => { setAttDate(e.target.value); loadAtt(e.target.value); }}
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-blue-900 text-white">
                  <th className="px-3 py-2 text-left">States</th>
                  <th className="px-3 py-2 text-center">Total Eng</th>
                  <th className="px-3 py-2 text-center">Total Punched IN</th>
                  <th className="px-3 py-2 text-center">Late (10:30)</th>
                  <th className="px-3 py-2 text-center">Present</th>
                  <th className="px-3 py-2 text-center">Not Punched</th>
                  <th className="px-3 py-2 text-center">% Punched</th>
                  <th className="px-3 py-2 text-center">% ON TIME</th>
                </tr>
              </thead>
              <tbody>
                {attData.data.map((r, i) => {
                  const isTotal = r.state === "Grand Total";
                  return (
                    <tr key={i} className={isTotal ? "bg-blue-900 text-white font-bold" : i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                      <td className="px-3 py-2 font-medium">{r.state}</td>
                      <td className="px-3 py-2 text-center">{r.total_engineers}</td>
                      <td className="px-3 py-2 text-center">{r.total_punched_in}</td>
                      <td className={`px-3 py-2 text-center ${r.late > 0 && !isTotal ? "text-orange-600 font-bold" : ""}`}>{r.late}</td>
                      <td className="px-3 py-2 text-center">{r.present}</td>
                      <td className={`px-3 py-2 text-center ${r.not_punched > 0 && !isTotal ? "text-red-600 font-bold" : ""}`}>{r.not_punched}</td>
                      <td className="px-3 py-2 text-center">
                        {isTotal ? <span className="font-bold">{r.pct_punched}</span> : (
                          <span className={`px-2 py-0.5 rounded font-bold ${pctColor(r.pct_punched)}`}>{r.pct_punched}</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {isTotal ? <span className="font-bold">{r.pct_on_time}</span> : (
                          <span className={`px-2 py-0.5 rounded font-bold ${pctColor(r.pct_on_time)}`}>{r.pct_on_time}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── ENGINEER PERFORMANCE TABLE PAGE ──────────────────────
function PerformanceTablePage() {
  const auth = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [state, setState] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("employee_name");
  const [sortDir, setSortDir] = useState("asc");

  useEffect(() => {
    setLoading(true);
    const stateParam = state || (auth.state_code || "");
    apiFetch(`/engineers/performance/table?start_date=${startDate}&end_date=${endDate}&state=${stateParam}&sort_by=${sortBy}&sort_dir=${sortDir}&page=${page}`)
      .then(setData)
      .catch(err => { console.error(err); setData(null); })
      .finally(() => setLoading(false));
  }, [startDate, endDate, state, page, sortBy, sortDir]);

  const handleExport = () => {
    const stateParam = state || (auth.state_code || "");
    window.location.href = `/api/engineers/performance/export?start_date=${startDate}&end_date=${endDate}&state=${stateParam}`;
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Engineer Performance Table</h1>
      
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold mb-1">From Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1">To Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1">State</label>
            <input type="text" placeholder="Leave empty for all" value={state} onChange={(e) => setState(e.target.value)} className="w-full px-3 py-2 border rounded text-sm" />
          </div>
          <div className="flex gap-2 items-end">
            <button onClick={handleExport} className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm font-semibold">📥 Export</button>
          </div>
        </div>
      </div>

      {data && (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm">
          <span className="font-semibold">Visits Efficiency: </span>{fmt.dec(data.visits_efficiency_metric, 3)} | 
          <span className="font-semibold ml-4">Working Days: </span>{data.working_days} | 
          <span className="font-semibold ml-4">Total Engineers: </span>{data.total_engineers}
        </div>
      )}

      {loading ? <Spinner /> : data && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-blue-900 text-white">
                  <th className="px-2 py-2 text-left cursor-pointer" onClick={() => { setSortBy("employee_name"); setSortDir(sortDir === "asc" ? "desc" : "asc"); }}>Name</th>
                  <th className="px-2 py-2 text-left">Employee ID</th>
                  <th className="px-2 py-2 text-left">Service Area</th>
                  <th className="px-2 py-2 text-left">State</th>
                  <th className="px-2 py-2 text-center">Att. Days</th>
                  <th className="px-2 py-2 text-center">Working Days</th>
                  <th className="px-2 py-2 text-center">Att. %</th>
                  <th className="px-2 py-2 text-center">Prod. Days</th>
                  <th className="px-2 py-2 text-center">Zero Prod Days</th>
                  <th className="px-2 py-2 text-center">Total Visits</th>
                  <th className="px-2 py-2 text-center">Distinct Sites</th>
                  <th className="px-2 py-2 text-center">Repeat Rate (x)</th>
                  <th className="px-2 py-2 text-center">Closed</th>
                  <th className="px-2 py-2 text-center">Open</th>
                  <th className="px-2 py-2 text-center">Pending</th>
                  <th className="px-2 py-2 text-center">Complete</th>
                  <th className="px-2 py-2 text-center">Offline Sites</th>
                </tr>
              </thead>
              <tbody>
                {data.engineers.map((e, i) => (
                  <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="px-2 py-1 font-medium">{e.employee_name}</td>
                    <td className="px-2 py-1">{e.employee_id}</td>
                    <td className="px-2 py-1">{e.service_area_name}</td>
                    <td className="px-2 py-1">{e.service_state}</td>
                    <td className="px-2 py-1 text-center">{e.att_days}</td>
                    <td className="px-2 py-1 text-center">{e.working_days}</td>
                    <td className="px-2 py-1 text-center font-semibold">{fmt.pct(e.att_percentage)}</td>
                    <td className="px-2 py-1 text-center">{e.prod_days}</td>
                    <td className="px-2 py-1 text-center">{e.zero_prod_days}</td>
                    <td className="px-2 py-1 text-center">{e.total_visits}</td>
                    <td className="px-2 py-1 text-center">{e.distinct_sites}</td>
                    <td className="px-2 py-1 text-center">{fmt.dec(e.repeat_rate, 2)}</td>
                    <td className="px-2 py-1 text-center text-green-600 font-semibold">{e.closed_tickets}</td>
                    <td className="px-2 py-1 text-center text-red-600 font-semibold">{e.open_tickets}</td>
                    <td className="px-2 py-1 text-center text-amber-600 font-semibold">{e.pending_tickets}</td>
                    <td className="px-2 py-1 text-center">{e.completed_tickets}</td>
                    <td className="px-2 py-1 text-center text-red-600">{e.offline_sites}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 bg-gray-50 text-xs text-gray-600 flex items-center justify-between">
            <span>Page {page} of {Math.ceil(data.total / 50)} ({data.total} engineers)</span>
            <div className="space-x-1">
              <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-2 py-1 bg-gray-300 rounded disabled:opacity-50">◀</button>
              <button onClick={() => setPage(page + 1)} disabled={page * 50 >= data.total} className="px-2 py-1 bg-gray-300 rounded disabled:opacity-50">▶</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── DISTRIBUTION GRAPH PAGE ──────────────────────────────
function DistributionGraphPage() {
  const auth = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [state, setState] = useState("");
  const [metric, setMetric] = useState("visits");

  useEffect(() => {
    setLoading(true);
    const stateParam = state || (auth.state_code || "");
    apiFetch(`/dashboard/distribution?start_date=${startDate}&end_date=${endDate}&state=${stateParam}&metric=${metric}`)
      .then(setData)
      .catch(err => { console.error(err); setData(null); })
      .finally(() => setLoading(false));
  }, [startDate, endDate, state, metric]);

  const maxValue = data?.data ? Math.max(...data.data.map(d => d.value), 1) : 1;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Distribution Graph</h1>
      
      <div className="bg-white rounded-lg shadow p-4 space-y-4">
        <div className="grid grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-semibold mb-1">From Date</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1">To Date</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1">State</label>
            <input type="text" placeholder="Leave empty for all" value={state} onChange={(e) => setState(e.target.value)} className="w-full px-3 py-2 border rounded text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1">Metric</label>
            <select value={metric} onChange={(e) => setMetric(e.target.value)} className="w-full px-3 py-2 border rounded text-sm">
              <option value="visits">Visits</option>
              <option value="tickets">Tickets</option>
              <option value="offline_sites">Offline Sites</option>
            </select>
          </div>
          <div className="flex gap-2 items-end">
            <span className="text-sm font-semibold">Total: <span className="text-blue-600">{data?.total || 0}</span></span>
          </div>
        </div>
      </div>

      {loading ? <Spinner /> : data?.data && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">{metric.replace('_', ' ').toUpperCase()} Activity ({data.date_range.start} to {data.date_range.end})</h2>
          <div className="flex items-end gap-1 h-64 bg-gray-50 p-4 rounded border border-gray-200 overflow-x-auto">
            {data.data.map((d, i) => (
              <div key={i} className="flex-1 min-w-[40px] flex flex-col items-center group">
                <div className="w-full bg-blue-500 rounded-t" style={{ height: `${(d.value / maxValue) * 100}%` }} title={`${d.date}: ${d.value}`}></div>
                <div className="text-xs text-gray-600 mt-2 rotate-45 origin-left" style={{ fontSize: "10px" }}>{d.date.split('-')[2]}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-600">
            State: <span className="font-semibold">{data.state}</span> |
            Max Value: <span className="font-semibold">{maxValue}</span> |
            Data Points: <span className="font-semibold">{data.data.length}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── VISIT FORMS PAGE ─────────────────────────────────────────
function VisitFormsPage() {
  const auth = useAuth();
  const [summary, setSummary] = useState(null);
  const [browseData, setBrowseData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [browseLoading, setBrowseLoading] = useState(false);
  const [tab, setTab] = useState("summary");
  const [filters, setFilters] = useState({ problem_solved: "", pm_done: "", employee_code: "" });
  const [startDate, setStartDate] = useState(() => { const d = new Date(); d.setDate(d.getDate() - 29); return d.toISOString().split("T")[0]; });
  const [endDate, setEndDate]     = useState(new Date().toISOString().split("T")[0]);

  const stateParam = auth.state_code ? `&state=${auth.state_code}` : "";

  useEffect(() => {
    setLoading(true);
    apiFetch(`/visits/analysis?start_date=${startDate}&end_date=${endDate}${stateParam}`)
      .then(setSummary).catch(console.error).finally(() => setLoading(false));
  }, [startDate, endDate]);

  const loadBrowse = (pg = 1) => {
    setBrowseLoading(true);
    const f = filters;
    const q = [
      `start_date=${startDate}`, `end_date=${endDate}`, `page=${pg}`, `page_size=50`,
      stateParam.replace("&",""),
      f.problem_solved && `problem_solved=${f.problem_solved}`,
      f.pm_done        && `pm_done=${f.pm_done}`,
      f.employee_code  && `employee_code=${encodeURIComponent(f.employee_code)}`,
    ].filter(Boolean).join("&");
    apiFetch(`/visits/browse?${q}`)
      .then(r => { setBrowseData(r.data); setTotal(r.total); setPage(pg); })
      .catch(console.error).finally(() => setBrowseLoading(false));
  };

  useEffect(() => { if (tab === "browse") loadBrowse(1); }, [tab, startDate, endDate]);

  if (loading) return <div className="flex items-center justify-center p-8"><div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /></div>;

  const s = summary?.summary || {};
  const maxVisits = summary?.daily?.length ? Math.max(...summary.daily.map(d => d.visits), 1) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-800">Visit Forms Analysis</h1>
        <div className="flex gap-2 items-center text-sm">
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="border rounded px-2 py-1 text-xs" />
          <span className="text-gray-400">to</span>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="border rounded px-2 py-1 text-xs" />
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Total Visits",       value: s.total_visits?.toLocaleString() ?? "–" },
          { label: "Unique Sites",        value: s.unique_sites?.toLocaleString() ?? "–" },
          { label: "Engineers Active",    value: s.unique_engineers?.toLocaleString() ?? "–" },
          { label: "FTFR (Problem Solved)", value: s.ftfr_pct != null ? `${s.ftfr_pct}%` : "–", highlight: s.ftfr_pct >= 70 ? "green" : s.ftfr_pct >= 50 ? "yellow" : "red" },
          { label: "PM Done",             value: s.pm_done_pct != null ? `${s.pm_done_pct}%` : "–", highlight: s.pm_done_pct >= 60 ? "green" : s.pm_done_pct >= 40 ? "yellow" : "red" },
        ].map((c, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="text-xs text-gray-500 mb-1">{c.label}</div>
            <div className={`text-2xl font-bold ${c.highlight === "green" ? "text-green-600" : c.highlight === "yellow" ? "text-yellow-600" : c.highlight === "red" ? "text-red-600" : "text-gray-800"}`}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {[["summary","Trends & Top Engineers"],["status","Ticket Status"],["browse","Browse Records"]].map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === id ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      {/* SUMMARY TAB */}
      {tab === "summary" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily visits bar chart */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="text-sm font-bold text-gray-700 mb-3">Daily Visit Trend</div>
            {summary?.daily?.length ? (
              <div className="flex items-end gap-1 h-40 overflow-x-auto">
                {summary.daily.map((d, i) => (
                  <div key={i} className="flex-1 min-w-[20px] flex flex-col items-center group">
                    <div title={`${d.date}: ${d.visits} visits`}
                      className="w-full bg-blue-500 rounded-t hover:bg-blue-400 transition-colors"
                      style={{ height: `${Math.round((d.visits / maxVisits) * 100)}%` }} />
                    <div className="text-xs text-gray-400 mt-1 rotate-45 origin-left" style={{ fontSize: "9px" }}>{d.date.slice(5)}</div>
                  </div>
                ))}
              </div>
            ) : <div className="text-sm text-gray-400 py-8 text-center">No data for selected range</div>}
          </div>

          {/* Top Engineers */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="text-sm font-bold text-gray-700 mb-3">Top Engineers by Visits</div>
            <div className="overflow-auto max-h-56">
              <table className="w-full text-xs">
                <thead><tr className="bg-blue-900 text-white">
                  <th className="px-2 py-1 text-left">Engineer</th>
                  <th className="px-2 py-1 text-left">State</th>
                  <th className="px-2 py-1 text-center">Visits</th>
                  <th className="px-2 py-1 text-center">FTFR%</th>
                  <th className="px-2 py-1 text-center">PM Done</th>
                </tr></thead>
                <tbody>
                  {(summary?.top_engineers || []).map((e, i) => (
                    <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                      <td className="px-2 py-1 font-medium">{e.name}</td>
                      <td className="px-2 py-1 text-gray-500">{e.state}</td>
                      <td className="px-2 py-1 text-center font-bold">{e.visits}</td>
                      <td className="px-2 py-1 text-center"><span className={`px-1 py-0.5 rounded text-xs font-semibold ${e.ftfr >= 70 ? "bg-green-100 text-green-800" : e.ftfr >= 50 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800"}`}>{e.ftfr}%</span></td>
                      <td className="px-2 py-1 text-center">{e.pm_done}</td>
                    </tr>
                  ))}
                  {!summary?.top_engineers?.length && <tr><td colSpan={5} className="py-6 text-center text-gray-400">No data</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* STATUS TAB */}
      {tab === "status" && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
          <div className="text-sm font-bold text-gray-700 mb-3">Ticket Status from Visit Forms</div>
          <div className="space-y-2">
            {(summary?.status_breakdown || []).map((s, i) => {
              const max = summary.status_breakdown[0]?.count || 1;
              return (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <div className="w-32 text-right text-xs text-gray-600 shrink-0">{s.status}</div>
                  <div className="flex-1 bg-gray-100 rounded h-5">
                    <div className="bg-blue-500 h-5 rounded" style={{ width: `${Math.round(s.count/max*100)}%` }} />
                  </div>
                  <div className="w-12 text-xs font-bold text-gray-700 shrink-0">{s.count.toLocaleString()}</div>
                </div>
              );
            })}
            {!summary?.status_breakdown?.length && <div className="text-sm text-gray-400 py-8 text-center">No data</div>}
          </div>
        </div>
      )}

      {/* BROWSE TAB */}
      {tab === "browse" && (
        <div className="space-y-3">
          {/* Filters */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <div className="text-xs text-gray-500 mb-1">Problem Solved</div>
                <select value={filters.problem_solved} onChange={e => setFilters(f => ({...f, problem_solved: e.target.value}))}
                  className="border rounded px-2 py-1 text-xs">
                  <option value="">All</option><option value="YES">Yes</option><option value="NO">No</option>
                </select>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">PM Done</div>
                <select value={filters.pm_done} onChange={e => setFilters(f => ({...f, pm_done: e.target.value}))}
                  className="border rounded px-2 py-1 text-xs">
                  <option value="">All</option><option value="YES">Yes</option><option value="NO">No</option>
                </select>
              </div>
              <div>
                <div className="text-xs text-gray-500 mb-1">Engineer Code</div>
                <input value={filters.employee_code} onChange={e => setFilters(f => ({...f, employee_code: e.target.value}))}
                  placeholder="e.g. HBSVP00001" className="border rounded px-2 py-1 text-xs w-36" />
              </div>
              <button onClick={() => loadBrowse(1)} className="bg-blue-600 text-white px-3 py-1 rounded text-xs font-semibold hover:bg-blue-700">Apply</button>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="p-3 border-b text-xs text-gray-500">{total.toLocaleString()} records</div>
            {browseLoading ? (
              <div className="flex justify-center p-8"><div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" /></div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead><tr className="bg-blue-900 text-white">
                    {["Date","Ticket ID","CS ID","Site","Engineer","State","Ticket Status","Solved?","PM Done?","Problem","Action Taken"].map(h => (
                      <th key={h} className="px-2 py-2 text-left whitespace-nowrap">{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {browseData.map((r, i) => (
                      <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                        <td className="px-2 py-1 whitespace-nowrap">{r.visit_date}</td>
                        <td className="px-2 py-1 font-mono text-xs">{r.ticket_id}</td>
                        <td className="px-2 py-1">{r.cs_id}</td>
                        <td className="px-2 py-1 max-w-[120px] truncate" title={r.site_name}>{r.site_name}</td>
                        <td className="px-2 py-1 max-w-[100px] truncate" title={r.engineer_name}>{r.engineer_name}</td>
                        <td className="px-2 py-1">{r.state}</td>
                        <td className="px-2 py-1"><Badge label={r.ticket_status || "–"} color="bg-gray-100 text-gray-700" /></td>
                        <td className="px-2 py-1 text-center"><span className={`px-1 rounded text-xs font-bold ${r.problem_solved?.toUpperCase()==="YES" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{r.problem_solved || "–"}</span></td>
                        <td className="px-2 py-1 text-center"><span className={`px-1 rounded text-xs font-bold ${r.pm_done?.toUpperCase()==="YES" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>{r.pm_done || "–"}</span></td>
                        <td className="px-2 py-1 max-w-[150px] truncate" title={r.actual_problem}>{r.actual_problem || "–"}</td>
                        <td className="px-2 py-1 max-w-[150px] truncate" title={r.action_taken}>{r.action_taken || "–"}</td>
                      </tr>
                    ))}
                    {!browseData.length && <tr><td colSpan={11} className="py-8 text-center text-gray-400">No records. Apply filters and click Apply, or upload Visit Form data first.</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
            {/* Pagination */}
            {total > 50 && (
              <div className="p-3 border-t flex items-center gap-2 text-xs text-gray-600">
                <button disabled={page <= 1} onClick={() => loadBrowse(page - 1)} className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">Prev</button>
                <span>Page {page} of {Math.ceil(total / 50)}</span>
                <button disabled={page >= Math.ceil(total / 50)} onClick={() => loadBrowse(page + 1)} className="px-2 py-1 border rounded disabled:opacity-40 hover:bg-gray-50">Next</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
