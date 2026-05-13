import { useState } from "react";

const API = "/api";

export function ExportModule() {
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState("");

  const downloadFile = (data, filename, mimeType) => {
    const blob = new Blob([data], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const exportToCSV = async (dataType) => {
    setExporting(true);
    setMessage("");
    try {
      const endpoint = `/dashboard/${dataType === "engineers" ? "engineers" : "offline-buckets"}`;
      const response = await fetch(API + endpoint);
      const data = await response.json();

      let csvContent = "";
      let filename = `${dataType}_${new Date().toISOString().split("T")[0]}.csv`;

      if (dataType === "engineers") {
        csvContent = "Engineer Code,Engineer Name,State,Visits,Attendance %,Closed,Offline\n";
        if (data.engineers) {
          data.engineers.forEach((eng) => {
            csvContent += `${eng.engineer_code},${eng.engineer_name},${eng.state},${eng.total_visits},${eng.att_percent},${eng.closed},${eng.offline_sites}\n`;
          });
        }
      } else if (dataType === "offline") {
        csvContent = "Bucket,Count,Percentage\n";
        if (data.distribution) {
          data.distribution.forEach((item) => {
            csvContent += `${item.bucket},${item.count},${item.percent}%\n`;
          });
        }
      }

      downloadFile(csvContent, filename, "text/csv");
      setMessage(`✅ Exported ${dataType} as CSV`);
    } catch (err) {
      setMessage(`❌ Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  const exportToExcel = async (dataType) => {
    setExporting(true);
    setMessage("");
    try {
      // Import XLSX library dynamically
      const response = await fetch(
        "https://cdn.jsdelivr.net/npm/xlsx@latest/dist/xlsx.full.min.js"
      );
      const script = await response.text();
      eval(script);

      const endpoint = `/dashboard/${dataType === "engineers" ? "engineers" : "offline-buckets"}`;
      const apiResponse = await fetch(API + endpoint);
      const data = await apiResponse.json();

      const workbook = XLSX.utils.book_new();

      if (dataType === "engineers" && data.engineers) {
        const wsData = [
          ["Engineer Code", "Engineer Name", "State", "Visits", "Attendance %", "Closed", "Offline"],
          ...data.engineers.map((eng) => [
            eng.engineer_code,
            eng.engineer_name,
            eng.state,
            eng.total_visits,
            eng.att_percent,
            eng.closed,
            eng.offline_sites,
          ]),
        ];
        const ws = XLSX.utils.aoa_to_sheet(wsData);
        XLSX.utils.book_append_sheet(workbook, ws, "Engineers");
      } else if (dataType === "offline" && data.distribution) {
        const wsData = [
          ["Bucket", "Count", "Percentage"],
          ...data.distribution.map((item) => [item.bucket, item.count, `${item.percent}%`]),
        ];
        const ws = XLSX.utils.aoa_to_sheet(wsData);
        XLSX.utils.book_append_sheet(workbook, ws, "Offline Distribution");
      }

      const filename = `${dataType}_${new Date().toISOString().split("T")[0]}.xlsx`;
      XLSX.writeFile(workbook, filename);
      setMessage(`✅ Exported ${dataType} as Excel`);
    } catch (err) {
      setMessage(`❌ Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-bold mb-4">📥 Export Data</h2>

      <div className="space-y-4">
        {/* Engineers Export */}
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Engineer Performance</h3>
          <div className="flex gap-2">
            <button
              onClick={() => exportToCSV("engineers")}
              disabled={exporting}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              📄 CSV
            </button>
            <button
              onClick={() => exportToExcel("engineers")}
              disabled={exporting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              📊 Excel
            </button>
          </div>
        </div>

        {/* Offline Distribution Export */}
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Offline Distribution</h3>
          <div className="flex gap-2">
            <button
              onClick={() => exportToCSV("offline")}
              disabled={exporting}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              📄 CSV
            </button>
            <button
              onClick={() => exportToExcel("offline")}
              disabled={exporting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              📊 Excel
            </button>
          </div>
        </div>
      </div>

      {message && (
        <div
          className={`mt-4 p-3 rounded ${
            message.startsWith("✅")
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {message}
        </div>
      )}
    </div>
  );
}
