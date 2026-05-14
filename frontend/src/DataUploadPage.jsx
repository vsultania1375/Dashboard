// Data Upload Page Component
// Handles file uploads for Engineers, Offline Sites, Attendance, Visits, and Tickets

import { useState } from "react";

export default function DataUploadPage() {
  const [activeTab, setActiveTab] = useState("upload");
  const [selectedFile, setSelectedFile] = useState(null);
  const [dataType, setDataType] = useState("engineers");
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [validation, setValidation] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [history, setHistory] = useState([]);
  const [availableSheets, setAvailableSheets] = useState([]);
  const [selectedSheet, setSelectedSheet] = useState(null);

  const dataTypes = [
    { id: "engineers", label: "👥 Engineers", description: "Engineer profiles and details" },
    { id: "offline_sites", label: "🔴 Offline Sites", description: "Sites that are offline/inactive" },
    { id: "attendance", label: "📋 Attendance", description: "Daily attendance records" },
    { id: "visits", label: "📍 Visits", description: "Engineer visit logs" },
    { id: "tickets", label: "🎫 Tickets", description: "Support tickets" },
  ];

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".csv") && !file.name.endsWith(".xls")) {
        alert("Please select a valid Excel (.xlsx/.xls) or CSV file");
        return;
      }
      setSelectedFile(file);
      setPreview(null);
      setValidation(null);
      setSelectedSheet(null);
      setAvailableSheets([]);

      // If Excel file, list available sheets
      if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        await listSheets(file);
      }
    }
  };

  const listSheets = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/upload/sheets", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        console.error("Failed to list sheets:", text);
        return;
      }

      const data = await response.json();
      setAvailableSheets(data.sheets || []);
      setSelectedSheet(data.default_sheet || null);
    } catch (error) {
      console.error("Error listing sheets:", error);
    }
  };

  const previewFile = async () => {
    if (!selectedFile) {
      alert("Please select a file first");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      // Add sheet parameter if selected
      const sheetParam = selectedSheet ? `&sheet=${encodeURIComponent(selectedSheet)}` : "";
      const response = await fetch(`/api/upload/preview?rows=10${sheetParam}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = `Server error: ${response.status}`;
        try {
          const text = await response.text();
          try {
            const errorData = JSON.parse(text);
            errorMsg = errorData.detail || errorMsg;
          } catch {
            errorMsg = text ? text.substring(0, 100) : errorMsg;
          }
        } catch (e) {
          errorMsg += " (Unable to read error details)";
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();
      setPreview(data);
    } catch (error) {
      alert("Error previewing file: " + error.message);
    } finally {
      setUploading(false);
    }
  };

  const validateFile = async () => {
    if (!selectedFile) {
      alert("Please select a file first");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      // Add sheet parameter if selected
      const sheetParam = selectedSheet ? `?sheet=${encodeURIComponent(selectedSheet)}` : "";
      const response = await fetch(`/api/upload/validate${sheetParam}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = `Server error: ${response.status}`;
        try {
          const text = await response.text();
          try {
            const errorData = JSON.parse(text);
            errorMsg = errorData.detail || errorMsg;
          } catch {
            errorMsg = text ? text.substring(0, 100) : errorMsg;
          }
        } catch (e) {
          errorMsg += " (Unable to read error details)";
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();
      setValidation(data);
      setUploadId(data.upload_id);
    } catch (error) {
      alert("Validation error: " + error.message);
    } finally {
      setUploading(false);
    }
  };

  const confirmUpload = async () => {
    if (!uploadId) {
      alert("Please validate file first");
      return;
    }

    setUploading(true);

    try {
      const response = await fetch(`/api/upload/confirm?upload_id=${uploadId}`, {
        method: "POST",
      });

      if (!response.ok) {
        let errorMsg = `Server error: ${response.status}`;
        try {
          const text = await response.text();
          try {
            const errorData = JSON.parse(text);
            errorMsg = errorData.detail || errorMsg;
          } catch {
            errorMsg = text ? text.substring(0, 100) : errorMsg;
          }
        } catch (e) {
          errorMsg += " (Unable to read error details)";
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();

      if (data.status === "loading" || data.status === "completed") {
        alert(`✅ Data confirmed! Loading ${data.rows_to_load || "data"} to database...`);
        setSelectedFile(null);
        setPreview(null);
        setValidation(null);
        setUploadId(null);
        loadHistory();
      }
    } catch (error) {
      alert("Confirmation error: " + error.message);
    } finally {
      setUploading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch("/api/upload/history?limit=10");
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      const data = await response.json();
      setHistory(data.recent_uploads || []);
    } catch (error) {
      console.error("Error loading history:", error);
    }
  };

  const downloadTemplate = async (type) => {
    try {
      const response = await fetch(`/api/upload/template/${type}`);
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      const template = await response.json();

      // Create CSV content
      const headers = template.columns.join(",");
      const sample = template.columns.map((col) => template.sample_row[col] || "").join(",");
      const notes = template.notes.map((n) => `# ${n}`).join("\n");

      const csv = `${notes}\n${headers}\n${sample}`;

      // Download
      const element = document.createElement("a");
      element.setAttribute("href", "data:text/csv;charset=utf-8," + encodeURIComponent(csv));
      element.setAttribute("download", `template_${type}.csv`);
      element.style.display = "none";
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    } catch (error) {
      alert("Error downloading template: " + error.message);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">📤 Data Upload</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {["upload", "history", "templates"].map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); if (tab === "history") loadHistory(); }}
            className={`px-4 py-2 font-medium transition ${
              activeTab === tab
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-600 hover:text-gray-800"
            }`}
          >
            {tab === "upload" && "Upload"}
            {tab === "history" && "History"}
            {tab === "templates" && "Templates"}
          </button>
        ))}
      </div>

      {/* Upload Tab */}
      {activeTab === "upload" && (
        <div className="space-y-6">
          {/* Data Type Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">Select Data Type</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {dataTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setDataType(type.id)}
                  className={`p-3 rounded-lg border-2 transition text-left ${
                    dataType === type.id
                      ? "border-blue-600 bg-blue-50"
                      : "border-gray-200 bg-white hover:border-blue-300"
                  }`}
                >
                  <div className="font-semibold">{type.label}</div>
                  <div className="text-xs text-gray-600">{type.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* File Upload */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4">Upload File</h2>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileSelect}
                className="hidden"
                id="fileInput"
              />
              <label htmlFor="fileInput" className="cursor-pointer">
                <div className="text-4xl mb-2">📁</div>
                <div className="font-semibold text-gray-800">
                  {selectedFile ? selectedFile.name : "Click to select file"}
                </div>
                <div className="text-sm text-gray-600 mt-1">or drag and drop</div>
                <div className="text-xs text-gray-500 mt-2">Supported: .xlsx, .xls, .csv</div>
              </label>
            </div>

            {selectedFile && (
              <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
                ✓ Selected: <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
              </div>
            )}

            {/* Sheet Selector for Excel Files */}
            {selectedFile && availableSheets.length > 0 && (
              <div className="mt-4 p-4 bg-yellow-50 rounded border border-yellow-200">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  📄 Select Sheet:
                </label>
                <select
                  value={selectedSheet || ""}
                  onChange={(e) => {
                    setSelectedSheet(e.target.value);
                    setPreview(null);
                    setValidation(null);
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded bg-white"
                >
                  {availableSheets.map((sheet) => (
                    <option key={sheet} value={sheet}>
                      {sheet}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Preview */}
          {!validation && (
            <button
              onClick={previewFile}
              disabled={!selectedFile || uploading}
              className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 disabled:opacity-50"
            >
              {uploading ? "Loading..." : "📊 Preview Data"}
            </button>
          )}

          {preview && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-3">Preview ({preview.total_rows} rows)</h3>
              <div className="mb-3 text-sm text-gray-600">
                <strong>Columns ({preview.total_columns}):</strong> {preview.columns.join(", ")}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-100">
                      {preview.columns.map((col) => (
                        <th key={col} className="px-2 py-1 text-left font-semibold text-xs">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview_data.map((row, idx) => (
                      <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                        {preview.columns.map((col) => (
                          <td key={col} className="px-2 py-1 text-xs border-b">
                            {String(row[col] || "").substring(0, 30)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Validation */}
          {!validation && preview && (
            <button
              onClick={validateFile}
              disabled={uploading}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {uploading ? "Validating..." : "✓ Validate Data"}
            </button>
          )}

          {validation && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold mb-3">Validation Report</h3>

              <div className="grid grid-cols-4 gap-3 mb-4">
                <div className="bg-blue-50 p-3 rounded">
                  <div className="text-2xl font-bold text-blue-600">{validation.rows_uploaded}</div>
                  <div className="text-xs text-gray-600">Total Rows</div>
                </div>
                <div className="bg-green-50 p-3 rounded">
                  <div className="text-2xl font-bold text-green-600">{validation.rows_valid}</div>
                  <div className="text-xs text-gray-600">Valid</div>
                </div>
                <div className="bg-red-50 p-3 rounded">
                  <div className="text-2xl font-bold text-red-600">{validation.rows_invalid}</div>
                  <div className="text-xs text-gray-600">Invalid</div>
                </div>
                <div className="bg-yellow-50 p-3 rounded">
                  <div className="text-2xl font-bold text-yellow-600">{validation.errors.length}</div>
                  <div className="text-xs text-gray-600">Errors</div>
                </div>
              </div>

              {validation.errors.length > 0 && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm">
                  <strong className="text-red-700">❌ Errors:</strong>
                  <ul className="list-disc ml-5 mt-1 text-red-600">
                    {validation.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validation.warnings.length > 0 && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                  <strong className="text-yellow-700">⚠️ Warnings:</strong>
                  <ul className="list-disc ml-5 mt-1 text-yellow-600">
                    {validation.warnings.map((warn, idx) => (
                      <li key={idx}>{warn}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validation.summary && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded text-sm mb-4">
                  <strong>Summary:</strong>
                  <div className="mt-2 space-y-1">
                    {Object.entries(validation.summary).map(([key, val]) => (
                      <div key={key}>
                        <span className="font-medium">{key}:</span> {String(val)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {validation.can_proceed && (
                <button
                  onClick={confirmUpload}
                  disabled={uploading}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 w-full"
                >
                  {uploading ? "Loading..." : "✅ Confirm & Load to Database"}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === "history" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold mb-4">Recent Uploads</h2>
          {history.length > 0 ? (
            <div className="space-y-2">
              {history.map((item, idx) => (
                <div key={idx} className="p-3 border rounded flex justify-between items-center">
                  <div>
                    <div className="font-semibold">{item.filename}</div>
                    <div className="text-xs text-gray-600">
                      Type: <span className="font-mono">{item.data_type}</span> | 
                      Rows: <span className="font-mono">{item.rows}</span> | 
                      Status: <span className={item.status === "success" ? "text-green-600" : "text-gray-600"}>{item.status}</span>
                    </div>
                  </div>
                  {item.errors > 0 && <div className="text-red-600 font-bold">{item.errors} errors</div>}
                  {item.errors === 0 && item.status === "success" && <div className="text-green-600">✓</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400">No uploads yet</p>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {activeTab === "templates" && (
        <div className="space-y-4">
          {dataTypes.map((type) => (
            <div key={type.id} className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-bold">{type.label}</div>
                  <div className="text-sm text-gray-600">{type.description}</div>
                </div>
                <button
                  onClick={() => downloadTemplate(type.id)}
                  className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                >
                  📥 Download Template
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
