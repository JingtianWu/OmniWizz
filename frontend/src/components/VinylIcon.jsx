import React, { useState, useEffect, useRef } from "react";
import "../index.css";

// Expected generation time in milliseconds (≈ 240 s)
const EXPECTED_DURATION = 240_000;

export default function VinylIcon({ playing, loading = false, onClick }) {
  const [hint, setHint] = useState(loading ? null : "play");
  const [fade, setFade] = useState(false);
  const [progress, setProgress] = useState(0);

  // Refs so they persist between renders without triggering re-renders
  const startTimeRef = useRef(null);
  const intervalRef = useRef(null);

  // Handle the lifecycle of the progress bar
  useEffect(() => {
    if (loading) {
      // Reset & start a fresh timer for this run
      setHint(null);
      setFade(false);
      setProgress(0);
      startTimeRef.current = Date.now();

      // Advance the bar roughly every 200 ms
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        const computed = Math.min((elapsed / EXPECTED_DURATION) * 100, 99);
        // Always take the larger value so the bar never jumps backwards
        setProgress((prev) => (computed > prev ? computed : prev));
      }, 200);
    } else {
      // Loading finished → show 100 %, then gently reset
      setHint("play");
      setFade(false);
      setProgress(100);
      // Clear any running timer
      if (intervalRef.current) clearInterval(intervalRef.current);
      // After a short pause, drop back to 0 ready for the next job
      const reset = setTimeout(() => setProgress(0), 800);
      return () => clearTimeout(reset);
    }

    // Clean-up when the component unmounts or loading flag flips
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loading]);

  // A brief 'cool-down' period exists while progress > 0 after loading ends.
  // During this time the user should not be able to interact.
  const isBusy = loading || progress > 0;

  const handleClick = (e) => {
    if (isBusy) return; // block interaction during loading & cool-down

    if (hint === "play") {
      setHint("pause");
      setTimeout(() => setFade(true), 500);
      setTimeout(() => setHint(null), 1500);
    }
    if (onClick) onClick(e);
  };

  return (
    <div
      className="vinyl-wrapper"
      onClick={handleClick}
      style={{ pointerEvents: isBusy ? "none" : "auto" }} // extra protection
    >
      <div className={`vinyl-rotator ${playing ? "spin" : ""}`}>
        <svg viewBox="0 0 100 100" width="140" height="140">
          <circle cx="50" cy="50" r="48" fill="#111" stroke="#000" strokeWidth="1" />
          <circle cx="50" cy="50" r="40" fill="none" stroke="#333" strokeWidth="2" />
          <circle cx="50" cy="50" r="30" fill="none" stroke="#222" strokeWidth="2" />
          <circle cx="50" cy="50" r="5" fill="#000" />
        </svg>
        <div className="vinyl-indicator">
          {loading || progress === 100 ? (
            <div className="vinyl-progress">
              <div
                className="vinyl-progress-bar"
                style={{
                  width: `${progress}%`,
                  animation: "none",
                  transition: "width 0.2s linear",
                }}
              />
              <span className="vinyl-progress-label">Composing...</span>
            </div>
          ) : playing ? (
            <div className="dots">
              <div className="dot dot-1" />
              <div className="dot dot-2" />
              <div className="dot" />
            </div>
          ) : (
            <div className="paused" />
          )}
        </div>
        {/* Hint appears only when fully ready (not busy) */}
        {!isBusy && hint && (
          <div className={`vinyl-hint ${fade ? "fade" : ""}`}>
            {hint === "play" ? (
              <svg viewBox="0 0 64 64" width="40" height="40">
                <polygon points="16,8 16,56 56,32" fill="rgba(255,255,255,0.8)" />
              </svg>
            ) : (
              <svg viewBox="0 0 64 64" width="40" height="40">
                <rect x="16" y="8" width="10" height="48" fill="rgba(255,255,255,0.8)" />
                <rect x="38" y="8" width="10" height="48" fill="rgba(255,255,255,0.8)" />
              </svg>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
