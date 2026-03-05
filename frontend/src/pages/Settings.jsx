import { useState, useEffect } from "react";
import { useTheme } from "../contexts/ThemeContext";
import { useAuth } from "../contexts/AuthContext";
import api from "../services/api";

const COMMON_CATEGORIES = ["Food & Dining", "Shopping", "Entertainment", "Travel", "Healthcare", "Utilities", "Rent", "Software", "Other"];

const CURRENCIES = [
  { code: "USD", symbol: "$", label: "USD — US Dollar" },
  { code: "EUR", symbol: "€", label: "EUR — Euro" },
  { code: "GBP", symbol: "£", label: "GBP — British Pound" },
  { code: "INR", symbol: "₹", label: "INR — Indian Rupee" },
  { code: "AUD", symbol: "A$", label: "AUD — Australian Dollar" },
  { code: "CAD", symbol: "C$", label: "CAD — Canadian Dollar" },
];

export default function Settings() {
  const { theme, toggleTheme } = useTheme();
  const { user, updateUser } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwStatus, setPwStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  // Currency state
  const [currency, setCurrency] = useState(user?.currency || "USD");
  const [currencySaving, setCurrencySaving] = useState(false);

  const saveCurrency = async (code) => {
    setCurrency(code);
    setCurrencySaving(true);
    try { await updateUser({ currency: code }); } finally { setCurrencySaving(false); }
  };

  // Budget Goals state
  const [goals, setGoals] = useState([]);
  const [budgetCategory, setBudgetCategory] = useState(COMMON_CATEGORIES[0]);
  const [budgetLimit, setBudgetLimit] = useState("");
  const [budgetSaving, setBudgetSaving] = useState(false);

  useEffect(() => {
    api.get("/budgets").then((res) => setGoals(res.data)).catch(() => {});
  }, []);

  const addGoal = async (e) => {
    e.preventDefault();
    if (!budgetLimit || isNaN(budgetLimit) || Number(budgetLimit) <= 0) return;
    setBudgetSaving(true);
    try {
      const res = await api.post("/budgets", { category: budgetCategory, monthly_limit: Number(budgetLimit) });
      setGoals((prev) => [...prev, res.data]);
      setBudgetLimit("");
    } finally {
      setBudgetSaving(false);
    }
  };

  const deleteGoal = async (id) => {
    await api.delete(`/budgets/${id}`);
    setGoals((prev) => prev.filter((g) => g.id !== id));
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPwStatus({ type: "error", message: "New passwords do not match" });
      return;
    }
    setLoading(true);
    setPwStatus(null);
    try {
      await api.put("/auth/password", { current_password: currentPassword, new_password: newPassword });
      setPwStatus({ type: "success", message: "Password changed successfully" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to change password";
      setPwStatus({ type: "error", message: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

      {/* Theme */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Appearance</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Currently using <span className="font-medium capitalize">{theme}</span> mode
            </p>
          </div>
          <button
            onClick={toggleTheme}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
          >
            {theme === "dark" ? (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 7a5 5 0 100 10A5 5 0 0012 7z" />
                </svg>
                Switch to Light
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
                Switch to Dark
              </>
            )}
          </button>
        </div>
      </div>

      {/* Currency */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Display Currency</h2>
        <div className="flex items-center gap-3">
          <select
            value={currency}
            onChange={(e) => saveCurrency(e.target.value)}
            disabled={currencySaving}
            className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
          >
            {CURRENCIES.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
          </select>
          {currencySaving && <span className="text-xs text-gray-400">Saving...</span>}
        </div>
        <p className="text-xs text-gray-400 mt-2">Amounts are displayed using this currency symbol. Conversion uses approximate static rates.</p>
      </div>

      {/* Budget Goals */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Monthly Budget Goals</h2>

        <form onSubmit={addGoal} className="flex gap-3 mb-5">
          <select
            value={budgetCategory}
            onChange={(e) => setBudgetCategory(e.target.value)}
            className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {COMMON_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          <input
            type="number"
            value={budgetLimit}
            onChange={(e) => setBudgetLimit(e.target.value)}
            placeholder="Limit ($)"
            min="1"
            className="w-32 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={budgetSaving || !budgetLimit}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            {budgetSaving ? "Adding..." : "Add Goal"}
          </button>
        </form>

        {goals.length === 0 ? (
          <p className="text-sm text-gray-400">No budget goals yet. Add one above.</p>
        ) : (
          <div className="space-y-3">
            {goals.map((g) => {
              const pct = Math.min((g.spent / g.monthly_limit) * 100, 100);
              const over = g.spent > g.monthly_limit;
              return (
                <div key={g.id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-700 dark:text-gray-200">{g.category}</span>
                    <div className="flex items-center gap-3">
                      <span className={over ? "text-red-500 font-semibold" : "text-gray-500 dark:text-gray-400"}>
                        ${g.spent.toFixed(0)} / ${g.monthly_limit.toFixed(0)}
                      </span>
                      <button onClick={() => deleteGoal(g.id)} className="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none">×</button>
                    </div>
                  </div>
                  <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${over ? "bg-red-500" : pct > 80 ? "bg-yellow-400" : "bg-blue-500"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Password Change */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Change Password</h2>
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Current Password
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              New Password
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {pwStatus && (
            <p className={`text-sm font-medium ${pwStatus.type === "success" ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
              {pwStatus.message}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium transition-colors"
          >
            {loading ? "Saving..." : "Update Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
