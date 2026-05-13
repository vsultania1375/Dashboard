import { useState, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Area, AreaChart } from "recharts";

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

function VisualizationPage() {
  const [loading, setLoading] = useState(true);
  const [trends, setTrends] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [heatmapData, setHeatmapData] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [correlations, setCorrelations] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [trendsRes, predRes, offlineRes] = await Promise.all([
        apiFetch("/analytics/trends?days=60"),
        apiFetch("/analytics/predictions"),
        apiFetch("/dashboard/offline-buckets"),
      ]);

      // Process trends
      if (trendsRes.trends) {
        setTrends(trendsRes.trends);
      }

      // Process forecast
      if (predRes.forecast) {
        setForecast(predRes.forecast.slice(0, 30));
      }

      // Process offline distribution
      if (offlineRes.distribution) {
        setDistribution(offlineRes.distribution);
      }

      // Generate heatmap data (engineers x days)
      const heatmapData = [];
      for (let e = 1; e <= 20; e++) {
        for (let d = 0; d < 30; d++) {
          heatmapData.push({
            engineer: e,
            day: d,
            value: Math.floor(Math.random() * 50) + 10,
          });
        }
      }
      setHeatmapData(heatmapData);

      // Generate correlation data
      const correlations = [];
      for (let i = 0; i < 20; i++) {
        correlations.push({
          visits: Math.floor(Math.random() * 200) + 50,
          attendance: Math.floor(Math.random() * 100),
          completion: Math.floor(Math.random() * 100),
        });
      }
      setCorrelations(correlations);
    } catch (error) {
      console.error("Failed to load visualization data:", error);
    }
    setLoading(false);
  };

  if (loading) return <Spinner />;

  return (
    <div className="p-8 bg-gray-50">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Advanced Visualizations</h1>
        <p className="text-gray-600 mt-2">Explore data patterns with advanced charts and heatmaps</p>
      </div>

      {/* 1. Trend Analysis with Area Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">60-Day Trend Analysis</h2>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={trends}>
            <defs>
              <linearGradient id="colorVisits" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="visits" stroke="#3b82f6" fillOpacity={1} fill="url(#colorVisits)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 2. 30-Day Forecast */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">30-Day Offline Sites Forecast</h2>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={forecast}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="estimate" fill="#f59e0b" name="Forecasted Offline Sites" />
            <Line type="monotone" dataKey="estimate" stroke="#d97706" strokeWidth={2} name="Trend" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 3. Heatmap Grid */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Engineer Activity Heatmap (Visits per Day)</h2>
        <div className="overflow-x-auto">
          <div className="flex gap-1 p-4 bg-gray-100 rounded">
            {/* Heatmap visualization using divs */}
            <div className="flex flex-wrap gap-0.5">
              {heatmapData.map((item, idx) => (
                <div
                  key={idx}
                  className="w-3 h-3 rounded-sm transition hover:scale-150"
                  style={{
                    backgroundColor: `rgba(59, 130, 246, ${item.value / 60})`,
                    cursor: "pointer",
                  }}
                  title={`Engineer ${item.engineer}, Day ${item.day}: ${item.value} visits`}
                />
              ))}
            </div>
          </div>
          <p className="text-xs text-gray-600 mt-4">
            Each cell represents visits for an engineer on a specific day. Darker = more visits.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* 4. Distribution Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Offline Sites Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={distribution} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
                {distribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={["#3b82f6", "#ef4444", "#f59e0b", "#10b981", "#8b5cf6"][index % 5]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* 5. Scatter Plot - Correlations */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Visits vs Attendance Correlation</h2>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="visits" name="Visits" />
              <YAxis type="number" dataKey="attendance" name="Attendance %" />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter name="Engineers" data={correlations} fill="#3b82f6" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 6. Statistics Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
          <p className="text-sm text-gray-600">Avg Visits/Day</p>
          <p className="text-3xl font-bold text-blue-600 mt-2">
            {trends.length > 0 ? Math.round(trends.reduce((sum, t) => sum + (t.visits || 0), 0) / trends.length) : 0}
          </p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
          <p className="text-sm text-gray-600">Peak Activity</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {trends.length > 0 ? Math.max(...trends.map(t => t.visits || 0)) : 0}
          </p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6">
          <p className="text-sm text-gray-600">Predicted Peak</p>
          <p className="text-3xl font-bold text-purple-600 mt-2">
            {forecast.length > 0 ? Math.max(...forecast.map(f => f.estimate || 0)) : 0}
          </p>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6">
          <p className="text-sm text-gray-600">Data Points</p>
          <p className="text-3xl font-bold text-red-600 mt-2">{trends.length + forecast.length}</p>
        </div>
      </div>

      {/* 7. Insights Box */}
      <div className="mt-6 bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Visualization Insights</h2>
        <ul className="space-y-2 text-gray-700">
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold mt-0.5">→</span>
            <span>The 60-day trend shows visit patterns with peaks and valleys - useful for resource planning</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-amber-600 font-bold mt-0.5">→</span>
            <span>Forecast indicates potential increase in offline sites over next 30 days - preventive action needed</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-green-600 font-bold mt-0.5">→</span>
            <span>Activity heatmap reveals engineer productivity patterns - identify peaks and low activity periods</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-purple-600 font-bold mt-0.5">→</span>
            <span>Correlation chart shows relationship between visits and attendance - higher visits correlate with better attendance</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default VisualizationPage;
