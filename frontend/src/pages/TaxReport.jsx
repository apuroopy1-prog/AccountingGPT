import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import api from "../services/api";

const CURRENCY_SYMBOLS = { USD: "$", EUR: "€", GBP: "£", INR: "₹", AUD: "A$", CAD: "C$" };
const CURRENCY_RATES = { USD: 1, EUR: 0.92, GBP: 0.79, INR: 83.5, AUD: 1.53, CAD: 1.36 };

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = [CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2];

export default function TaxReport() {
  const { user } = useAuth();
  const currencyCode = user?.currency || "USD";
  const currencySymbol = CURRENCY_SYMBOLS[currencyCode] || "$";
  const currencyRate = CURRENCY_RATES[currencyCode] || 1;
  const fmt = (v) => (v * currencyRate).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const [year, setYear] = useState(CURRENT_YEAR);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/transactions/tax-summary?year=${year}`)
      .then((res) => setData(res.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [year]);

  const exportPDF = async () => {
    setExporting(true);
    try {
      const res = await api.get(`/reports/tax?year=${year}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tax-report-${year}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* silent */ }
    setExporting(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Tax Report</h1>
          <p className="text-xs text-gray-400 mt-0.5">IRS Schedule C expense categories — deductible transactions only</p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
          <button
            onClick={exportPDF}
            disabled={exporting || !data?.total_deductible}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5"
          >
            {exporting ? "Exporting..." : "Export PDF"}
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-800 flex gap-2">
        <span>⚠</span>
        <span>For informational purposes only. This report does not constitute tax advice. Consult a qualified tax professional before filing.</span>
      </div>

      {loading ? (
        <div className="text-center text-gray-400 mt-20">Loading...</div>
      ) : !data || data.total_deductible === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
          <p className="text-gray-400 text-sm mb-2">No deductible transactions for {year}.</p>
          <p className="text-gray-400 text-xs">Go to Transactions → click <strong>🧾 Auto-Tax</strong> to categorize your transactions first.</p>
        </div>
      ) : (
        <>
          {/* KPI */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-green-50 border border-green-200 rounded-xl p-5">
              <p className="text-sm text-green-600 font-medium">Total Deductible</p>
              <p className="text-3xl font-bold text-green-700 mt-1">{currencySymbol}{fmt(data.total_deductible)}</p>
              <p className="text-xs text-green-500 mt-1">Tax year {year}</p>
            </div>
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
              <p className="text-sm text-indigo-600 font-medium">IRS Categories</p>
              <p className="text-3xl font-bold text-indigo-700 mt-1">{Object.keys(data.by_category || {}).length}</p>
              <p className="text-xs text-indigo-500 mt-1">Schedule C</p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
              <p className="text-sm text-blue-600 font-medium">Top Category</p>
              <p className="text-lg font-bold text-blue-700 mt-1 truncate">
                {Object.entries(data.by_category || {})[0]?.[0] || "—"}
              </p>
              <p className="text-xs text-blue-500 mt-1">
                {currencySymbol}{fmt(Object.entries(data.by_category || {})[0]?.[1] || 0)}
              </p>
            </div>
          </div>

          {/* Category breakdown */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-700">Breakdown by IRS Category</h2>
            </div>
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">IRS Category</th>
                  <th className="text-right px-6 py-3 font-semibold text-gray-600">Deductible Amount</th>
                  <th className="text-left px-6 py-3 font-semibold text-gray-600">Note</th>
                  <th className="text-right px-6 py-3 font-semibold text-gray-600">% of Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(data.by_category || {}).map(([cat, amt]) => {
                  const pct = ((amt / data.total_deductible) * 100).toFixed(1);
                  return (
                    <tr key={cat} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-3 font-medium text-gray-800">{cat}</td>
                      <td className="px-6 py-3 text-right font-semibold text-green-600">
                        {currencySymbol}{fmt(amt)}
                      </td>
                      <td className="px-6 py-3 text-xs text-gray-400">
                        {cat === "Meals (50%)" ? "Only 50% deductible per IRS rules" : ""}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 bg-gray-100 rounded-full h-1.5">
                            <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="bg-gray-50 border-t border-gray-200">
                <tr>
                  <td className="px-6 py-3 font-bold text-gray-700">Total</td>
                  <td className="px-6 py-3 text-right font-bold text-green-700">{currencySymbol}{fmt(data.total_deductible)}</td>
                  <td />
                  <td className="px-6 py-3 text-right text-xs text-gray-400">100%</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
