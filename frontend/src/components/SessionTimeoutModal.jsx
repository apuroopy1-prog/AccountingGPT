export default function SessionTimeoutModal({ isOpen, countdown, onStayIn, onLogout }) {
  if (!isOpen) return null;

  const minutes = Math.floor(countdown / 60);
  const seconds = countdown % 60;
  const display = `${minutes}:${String(seconds).padStart(2, "0")}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm mx-4">
        <div className="flex justify-center mb-4">
          <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
            <svg
              className="w-7 h-7 text-amber-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
          </div>
        </div>

        <h2 className="text-center text-xl font-bold text-gray-800 mb-2">
          Session Expiring Soon
        </h2>
        <p className="text-center text-gray-500 mb-1">You'll be signed out in</p>
        <p className="text-center text-4xl font-mono font-bold text-amber-500 mb-6">
          {display}
        </p>

        <div className="flex gap-3">
          <button
            onClick={onLogout}
            className="flex-1 py-2 rounded-lg border border-gray-300 text-gray-600 font-medium hover:bg-gray-50 transition-colors"
          >
            Log out
          </button>
          <button
            onClick={onStayIn}
            className="flex-1 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
          >
            Stay logged in
          </button>
        </div>
      </div>
    </div>
  );
}
