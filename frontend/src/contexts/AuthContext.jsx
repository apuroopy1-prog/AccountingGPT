import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

const IDLE_TIMEOUT_MS = 30 * 60 * 1000;   // 30 minutes
const WARNING_BEFORE_MS = 2 * 60 * 1000;  // show warning 2 min before logout
const WARNING_DURATION_SECS = 120;
const ACTIVITY_EVENTS = ["mousemove", "keydown", "click", "scroll", "touchstart"];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(WARNING_DURATION_SECS);

  const idleTimerRef = useRef(null);
  const autoLogoutRef = useRef(null);
  const countdownRef = useRef(null);
  const showWarningRef = useRef(false);  // avoids stale closure in activity handler

  // Keep ref in sync with state
  useEffect(() => {
    showWarningRef.current = showWarning;
  }, [showWarning]);

  function clearTimers() {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    if (autoLogoutRef.current) clearTimeout(autoLogoutRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    idleTimerRef.current = null;
    autoLogoutRef.current = null;
    countdownRef.current = null;
  }

  const logout = useCallback(async () => {
    clearTimers();
    setShowWarning(false);
    try {
      await api.post("/auth/logout");
    } catch {
      // best-effort — local logout proceeds regardless
    }
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  function startCountdown() {
    setCountdown(WARNING_DURATION_SECS);
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function scheduleIdleTimers() {
    clearTimers();
    idleTimerRef.current = setTimeout(() => {
      setShowWarning(true);
      startCountdown();
      autoLogoutRef.current = setTimeout(() => {
        logout();
      }, WARNING_BEFORE_MS);
    }, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);
  }

  const handleStayLoggedIn = useCallback(async () => {
    setShowWarning(false);
    clearTimers();
    try {
      const res = await api.post("/auth/refresh");
      localStorage.setItem("token", res.data.access_token);
    } catch {
      logout();
      return;
    }
    scheduleIdleTimers();
  }, [logout]);

  // Attach activity listeners when user logs in, detach on logout
  useEffect(() => {
    if (!user) return;

    scheduleIdleTimers();

    let throttleTimeout = null;
    const throttledReset = () => {
      if (!throttleTimeout) {
        throttleTimeout = setTimeout(() => {
          if (showWarningRef.current) {
            setShowWarning(false);
          }
          scheduleIdleTimers();
          throttleTimeout = null;
        }, 500);
      }
    };

    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, throttledReset, { passive: true });
    });

    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, throttledReset);
      });
      clearTimers();
      if (throttleTimeout) clearTimeout(throttleTimeout);
    };
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Bootstrap: restore session on page load
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      api.get("/auth/me")
        .then((res) => setUser(res.data))
        .catch(async () => {
          // Access token expired — try silent refresh via cookie
          try {
            const refreshRes = await api.post("/auth/refresh");
            localStorage.setItem("token", refreshRes.data.access_token);
            const me = await api.get("/auth/me");
            setUser(me.data);
          } catch {
            localStorage.removeItem("token");
          }
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", res.data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
  };

  const register = async (email, password, full_name) => {
    const res = await api.post("/auth/register", { email, password, full_name });
    localStorage.setItem("token", res.data.access_token);
    const me = await api.get("/auth/me");
    setUser(me.data);
  };

  const updateUser = async (data) => {
    const res = await api.put("/auth/profile", data);
    setUser(res.data);
    return res.data;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, showWarning, countdown, handleStayLoggedIn, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
