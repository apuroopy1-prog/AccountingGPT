import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import api from "../services/api";

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend, Filler);

const CURRENCY_SYMBOLS = { USD: "$", EUR: "€", GBP: "£", INR: "₹", AUD: "A$", CAD: "C$" };
const CURRENCY_RATES   = { USD: 1, EUR: 0.92, GBP: 0.79, INR: 83.5, AUD: 1.53, CAD: 1.36 };

export default function Forecasting() {
  const { user } = useAuth();
  const currencyCode   = user?.currency || "USD";
  const sym            = CURRENCY_SYMBOLS[currencyCode] || "$";
  const rate           = CURRENCY_RATES[currencyCode]   || 1;
  const fmt  = (v) => `${sym}${(v * rate).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  const fmtK = (v) => {
    const converted = v * rate;
    return Math.abs(converted) >= 1000
      ? `${sym}${(converted / 1000).toFixed(1)}k`
      : `${sym}${converted.toFixed(0)}`;
  };

  const [forecast, setForecast] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/forecast")
      .then((res) => setForecast(res.data))
      .catch(() => setError("Failed to load forecast"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center text-gray-400 mt-20">Running forecast model...</div>;
  if (error)   return <div className="text-red-500 text-center mt-20">{error}</div>;

  if (forecast.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-800">Cash Flow Forecast</h1>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-16 text-center">
          <p className="text-gray-500 font-medium">Not enough data to generate a forecast</p>
          <p className="text-sm text-gray-400 mt-2">Upload bank statements covering at least 2 months of transactions to enable forecasting.</p>
        </div>
      </div>
    );
  }

  const labels = forecast.map((p) => {
    const d = new Date(p.ds);
    return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  });

  const chartData = {
    labels,
    datasets: [
      {
        label: "Forecast",
        data: forecast.map((p) => p.yhat * rate),
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59,130,246,0.15)",
        fill: false,
        tension: 0.4,
        pointRadius: 5,
        borderWidth: 2,
      },
      {
        label: "Upper Bound",
        data: forecast.map((p) => p.yhat_upper * rate),
        borderColor: "rgba(59,130,246,0.3)",
        borderDash: [6, 3],
        fill: false,
        tension: 0.4,
        pointRadius: 0,
      },
      {
        label: "Lower Bound",
        data: forecast.map((p) => p.yhat_lower * rate),
        borderColor: "rgba(59,130,246,0.3)",
        borderDash: [6, 3],
        backgroundColor: "rgba(59,130,246,0.05)",
        fill: "-1",
        tension: 0.4,
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: "top" },
      title: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.raw / rate)}`,
        },
      },
    },
    scales: {
      y: {
        ticks: { callback: (v) => fmtK(v / rate) },
      },
    },
  };

  const totalNet = forecast.reduce((s, p) => s + p.yhat, 0);
  const avg      = totalNet / forecast.length;
  const positive = forecast.filter((p) => p.yhat >= 0).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Cash Flow Forecast</h1>
        <span className="text-sm text-gray-500 bg-blue-50 border border-blue-100 rounded-full px-3 py-1">
          Powered by Facebook Prophet
        </span>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-sm text-gray-500">Projected 12-Month Net</p>
          <p className={`text-2xl font-bold mt-1 ${totalNet >= 0 ? "text-blue-600" : "text-red-500"}`}>
            {fmt(totalNet)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-sm text-gray-500">Avg Monthly Net</p>
          <p className={`text-2xl font-bold mt-1 ${avg >= 0 ? "text-green-600" : "text-red-500"}`}>
            {fmt(avg)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <p className="text-sm text-gray-500">Positive Months</p>
          <p className="text-2xl font-bold text-purple-600 mt-1">{positive} / 12</p>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <Line data={chartData} options={options} />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Month</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600">Forecast</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600">Lower</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-600">Upper</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {forecast.map((p, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-700">{labels[i]}</td>
                <td className={`px-4 py-3 text-right font-semibold ${p.yhat >= 0 ? "text-blue-600" : "text-red-500"}`}>
                  {fmt(p.yhat)}
                </td>
                <td className="px-4 py-3 text-right text-gray-400">{fmt(p.yhat_lower)}</td>
                <td className="px-4 py-3 text-right text-gray-400">{fmt(p.yhat_upper)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
