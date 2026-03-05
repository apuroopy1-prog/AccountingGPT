import { useState } from "react";
import api from "../services/api";

function NotifForm({ title, icon, channel, endpoint, placeholder }) {
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const send = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post(endpoint, { recipient, message });
      setResult(res.data);
      setRecipient("");
      setMessage("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to send");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
        <span className="ml-auto text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-1">Mock</span>
      </div>
      <form onSubmit={send} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">{placeholder}</label>
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={channel === "sms" ? "+1 555 000 0000" : "client@firm.com"}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Message</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
            rows={3}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="Your invoice #1234 is due in 3 days..."
          />
        </div>
        {error && <div className="text-red-500 text-sm">{error}</div>}
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {loading ? "Sending..." : `Send ${title}`}
        </button>
      </form>

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-1">
          <p className="text-green-700 font-semibold text-sm">Sent successfully!</p>
          <p className="text-xs text-gray-500">Provider: {result.provider}</p>
          <p className="text-xs text-gray-500">To: {result.recipient}</p>
          <p className="text-xs text-gray-500">At: {new Date(result.sent_at).toLocaleString()}</p>
          <p className="text-xs text-gray-500">Preview: "{result.message_preview}"</p>
        </div>
      )}
    </div>
  );
}

export default function Notifications() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Notifications</h1>
        <p className="text-gray-500 text-sm mt-1">
          Send SMS via Twilio or email via SendGrid. Currently running in mock mode — messages are logged server-side.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <NotifForm
          title="SMS"
          icon="💬"
          channel="sms"
          endpoint="/notify/sms"
          placeholder="Phone Number"
        />
        <NotifForm
          title="Email"
          icon="✉️"
          channel="email"
          endpoint="/notify/email"
          placeholder="Email Address"
        />
      </div>
    </div>
  );
}
