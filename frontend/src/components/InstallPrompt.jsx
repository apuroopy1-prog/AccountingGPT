import { useEffect, useState } from "react";

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showAndroid, setShowAndroid] = useState(false);
  const [showIOS, setShowIOS] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("pwa-dismissed")) return;

    // Android / Chrome — capture install prompt
    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowAndroid(true);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // iOS detection — show manual instructions
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches;
    if (isIOS && !isStandalone) setShowIOS(true);

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const dismiss = () => {
    localStorage.setItem("pwa-dismissed", "1");
    setShowAndroid(false);
    setShowIOS(false);
  };

  const install = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") localStorage.setItem("pwa-dismissed", "1");
    setShowAndroid(false);
    setDeferredPrompt(null);
  };

  if (!showAndroid && !showIOS) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-sm px-4">
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-xl p-4 flex gap-3 items-start">
        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shrink-0">
          <span className="text-white font-bold text-sm">CF</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 dark:text-white">Add ClearFlow AI to your home screen</p>
          {showIOS ? (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Tap <strong>Share</strong> → <strong>Add to Home Screen</strong>
            </p>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Install for quick access, offline support</p>
          )}
          {showAndroid && (
            <button
              onClick={install}
              className="mt-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
            >
              Install App
            </button>
          )}
        </div>
        <button onClick={dismiss} className="text-gray-400 hover:text-gray-600 text-xl leading-none shrink-0">×</button>
      </div>
    </div>
  );
}
