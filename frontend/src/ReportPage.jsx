import { useState, useEffect } from "react";
import { FileText, Download } from "lucide-react";

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
  return res;
}

function ReportPage() {
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [exportFormat, setExportFormat] = useState("pdf");

  useEffect(() => {
    // Load report summary on component mount
    loadReport();
  }, []);

  const loadReport = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/analytics/reports/summary?period=${period}`);
      const data = await res.json();
      setReportData(data);
    } catch (error) {
      console.error("Failed to load report:", error);
    }
    setLoading(false);
  };

  const handleExport = async (format) => {
    setLoading(true);
    try {
      const res = await apiFetch(`/analytics/export/${format}?period=${period}`);
      const blob = await res.blob();
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const timestamp = new Date().toISOString().split("T")[0];
      link.download = `report-${period}-${timestamp}.${format === 'pdf' ? 'pdf' : format === 'excel' ? 'xlsx' : 'json'}`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(`Failed to export as ${format}:`, error);
    }
    setLoading(false);
  };

  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
  };

  const handleRefresh = () => {
    loadReport();
  };

  return (
    <div className="p-8 bg-gray-50">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Report Generation</h1>
          <p className="text-gray-600 mt-2">Generate and export comprehensive analytics reports</p>
        </div>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Period Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Report Period</h2>
        <div className="flex gap-4">
          {["weekly", "monthly", "quarterly"].map((p) => (
            <button
              key={p}
              onClick={() => handlePeriodChange(p)}
              className={`px-6 py-2 rounded-lg font-medium transition ${
                period === p
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-800 hover:bg-gray-300"
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics Summary */}
      {reportData && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-gray-600 text-sm font-medium">Total Visits</div>
            <div className="text-3xl font-bold text-blue-600 mt-2">
              {reportData.metrics.total_visits.toLocaleString()}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-gray-600 text-sm font-medium">Avg Attendance</div>
            <div className="text-3xl font-bold text-green-600 mt-2">
              {reportData.metrics.avg_attendance}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-gray-600 text-sm font-medium">Completion Rate</div>
            <div className="text-3xl font-bold text-purple-600 mt-2">
              {reportData.metrics.completion_rate}%
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-gray-600 text-sm font-medium">Offline Sites</div>
            <div className="text-3xl font-bold text-red-600 mt-2">
              {reportData.metrics.offline_sites}
            </div>
          </div>
        </div>
      )}

      {/* Export Options */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-800">PDF Report</h3>
          </div>
          <p className="text-gray-600 text-sm mb-4">
            Professional formatted report with charts and tables
          </p>
          <button
            onClick={() => handleExport("pdf")}
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download PDF
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-800">Excel Report</h3>
          </div>
          <p className="text-gray-600 text-sm mb-4">
            Multi-sheet workbook with detailed data tables
          </p>
          <button
            onClick={() => handleExport("excel")}
            disabled={loading}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download Excel
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-4">
            <FileText className="w-6 h-6 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-800">JSON Report</h3>
          </div>
          <p className="text-gray-600 text-sm mb-4">
            Raw data in JSON format for integration
          </p>
          <button
            onClick={() => handleExport("json")}
            disabled={loading}
            className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download JSON
          </button>
        </div>
      </div>

      {/* Report Preview */}
      {reportData && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">Report Preview</h2>

          {/* Alerts Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Key Alerts</h3>
            <div className="space-y-2">
              {reportData.alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg flex items-start gap-3 ${
                    alert.severity === "high"
                      ? "bg-red-50 border-l-4 border-red-600"
                      : alert.severity === "medium"
                      ? "bg-yellow-50 border-l-4 border-yellow-600"
                      : "bg-green-50 border-l-4 border-green-600"
                  }`}
                >
                  <span
                    className={`text-lg ${
                      alert.severity === "high"
                        ? "text-red-600"
                        : alert.severity === "medium"
                        ? "text-yellow-600"
                        : "text-green-600"
                    }`}
                  >
                    {alert.severity === "high" ? "⚠️" : alert.severity === "medium" ? "⚡" : "✅"}
                  </span>
                  <span className="text-gray-700">{alert.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top Performers */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Top Performers</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-gray-600">
                <thead>
                  <tr className="bg-gray-100 border-b">
                    <th className="px-4 py-2 text-left">Rank</th>
                    <th className="px-4 py-2 text-left">Name</th>
                    <th className="px-4 py-2 text-right">Visits</th>
                    <th className="px-4 py-2 text-right">Attendance</th>
                  </tr>
                </thead>
                <tbody>
                  {reportData.top_performers?.map((perf, idx) => (
                    <tr key={idx} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2">{idx + 1}</td>
                      <td className="px-4 py-2 font-medium text-gray-800">{perf.name}</td>
                      <td className="px-4 py-2 text-right">{perf.visits}</td>
                      <td className="px-4 py-2 text-right">{perf.attendance}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Report Info */}
          <div className="text-xs text-gray-500 pt-4 border-t">
            <p>Report Period: {reportData.period}</p>
            <p>Generated: {reportData.date_range}</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-8 flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-700 font-medium">Generating report...</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportPage;
