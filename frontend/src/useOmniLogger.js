import { useEffect, useRef } from "react";

const BACKEND_URL =
  process.env.NODE_ENV === "development" ? "" : "https://omniwizz.onrender.com";

export default function useOmniLogger() {
  const queueRef = useRef([]);
  const timerRef = useRef(null);
  const sessionId = (() => {
    const k = localStorage.getItem("omniSession");
    if (k) return k;
    const id = crypto.randomUUID();
    localStorage.setItem("omniSession", id);
    return id;
  })();

  const flush = async () => {
    if (!queueRef.current.length) return;
    const events = queueRef.current.splice(0, queueRef.current.length);
    try {
      await fetch(`${BACKEND_URL}/log/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-omni-session": sessionId,
        },
        body: JSON.stringify(events),
      });
    } catch {}
  };

  const log = (type, payload = {}) => {
    queueRef.current.push({ type, payload });
    if (!timerRef.current) {
      timerRef.current = setTimeout(() => {
        flush();
        timerRef.current = null;
      }, 3000);
    }
  };

  useEffect(() => {
    const handle = () => {
      flush();
    };
    window.addEventListener("beforeunload", handle);
    const ping = setInterval(() => log("activity_ping"), 900000);
    return () => {
      window.removeEventListener("beforeunload", handle);
      clearInterval(ping);
    };
  }, []);

  return log;
}
