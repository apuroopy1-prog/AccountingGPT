import { useEffect, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import api from "../services/api";

const STATUS_STYLE = {
  pending: "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  done: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [gmailStatus, setGmailStatus] = useState(null); // null | {connected, last_checked}
  const [gmailBanner, setGmailBanner] = useState(""); // "connected" | "error" | ""
  const fileRef = useRef();
  const cameraRef = useRef();
  const location = useLocation();

  const fetchInvoices = () => {
    api.get("/invoices").then((res) => setInvoices(res.data));
  };

  const fetchGmailStatus = () => {
    api.get("/gmail/status").then((res) => setGmailStatus(res.data)).catch(() => {});
  };

  useEffect(() => {
    fetchInvoices();
    fetchGmailStatus();
    // Handle OAuth redirect query params
    const params = new URLSearchParams(location.search);
    const gmailParam = params.get("gmail");
    if (gmailParam) {
      setGmailBanner(gmailParam);
      fetchGmailStatus();
      // Clear the query param from URL without reload
      window.history.replaceState({}, "", "/invoices");
    }
  }, []);

  // Poll for status updates on pending/processing invoices
  useEffect(() => {
    const hasPending = invoices.some((i) => ["pending", "processing"].includes(i.status));
    if (!hasPending) return;
    const interval = setInterval(fetchInvoices, 3000);
    return () => clearInterval(interval);
  }, [invoices]);

  const uploadFile = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    try {
      await api.post("/invoices/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      fetchInvoices();
    } finally {
      setUploading(false);
    }
  };

  const connectGmail = async () => {
    const res = await api.get("/gmail/auth-url");
    window.location.href = res.data.url;
  };

  const disconnectGmail = async () => {
    await api.delete("/gmail/disconnect");
    setGmailStatus({ connected: false, last_checked: null });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Invoices & OCR</h1>
        <div className="flex items-center gap-3">
          <input
            type="file"
            ref={cameraRef}
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => uploadFile(e.target.files[0])}
          />
          <button
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 text-sm font-semibold px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {uploading ? "Scanning..." : "Scan Receipt"}
          </button>
          {gmailStatus?.connected ? (
            <>
              <span className="text-xs text-green-600 font-medium bg-green-50 border border-green-200 px-3 py-1 rounded-full">
                Gmail connected
              </span>
              <button
                onClick={disconnectGmail}
                className="text-sm text-gray-500 hover:text-red-500 underline transition-colors"
              >
                Disconnect
              </button>
            </>
          ) : (
            <button
              onClick={connectGmail}
              className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-semibold px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/>
              </svg>
              Connect Gmail
            </button>
          )}
        </div>
      </div>

      {gmailBanner === "connected" && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
          Gmail connected! Invoice attachments will be automatically imported every 5 minutes.
        </div>
      )}
      {gmailBanner === "error" && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3">
          Gmail connection failed. Please try again.
        </div>
      )}

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
        }`}
      >
        <input
          type="file"
          ref={fileRef}
          accept="image/*,.pdf"
          className="hidden"
          onChange={(e) => uploadFile(e.target.files[0])}
        />
        <div className="text-4xl mb-3">📄</div>
        <p className="text-gray-600 font-medium">
          {uploading ? "Uploading..." : "Drop an invoice here or click to upload"}
        </p>
        <p className="text-sm text-gray-400 mt-1">Supports PNG, JPG, PDF — OCR runs automatically</p>
      </div>

      {/* Invoice list */}
      {invoices.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {invoices.map((inv) => (
            <div
              key={inv.id}
              onClick={() => setSelected(selected?.id === inv.id ? null : inv)}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-800">{inv.filename}</p>
                  <p className="text-sm text-gray-400 mt-0.5">
                    {new Date(inv.uploaded_at).toLocaleString()}
                  </p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLE[inv.status]}`}>
                  {inv.status}
                </span>
              </div>

              {/* Extracted fields */}
              {inv.extracted_data && Object.keys(inv.extracted_data).length > 0 && (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {Object.entries(inv.extracted_data).map(([k, v]) => (
                    <div key={k} className="bg-gray-50 rounded-lg px-3 py-2">
                      <p className="text-xs text-gray-400 capitalize">{k.replace("_", " ")}</p>
                      <p className="text-sm font-medium text-gray-700">{v}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* OCR text preview */}
              {selected?.id === inv.id && inv.ocr_text && (
                <div className="mt-3 bg-gray-50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-gray-500 mb-1">Raw OCR Text</p>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {inv.ocr_text}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
