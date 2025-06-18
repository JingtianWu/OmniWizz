import React, { useState } from "react";
import "../index.css";

export default function VinylIcon({ playing, onClick }) {
  const [hint, setHint] = useState("play");
  const [fade, setFade] = useState(false);

  const handleClick = (e) => {
    if (hint === "play") {
      setHint("pause");
      setTimeout(() => setFade(true), 500);
      setTimeout(() => setHint(null), 1500);
    }
    if (onClick) onClick(e);
  };

  return (
    <div className="vinyl-wrapper" onClick={handleClick}>
      <div className={`vinyl-rotator ${playing ? "spin" : ""}`}>
        <svg viewBox="0 0 100 100" width="140" height="140">
          <circle cx="50" cy="50" r="48" fill="#111" stroke="#000" strokeWidth="1" />
          <circle cx="50" cy="50" r="40" fill="none" stroke="#333" strokeWidth="2" />
          <circle cx="50" cy="50" r="30" fill="none" stroke="#222" strokeWidth="2" />
          <circle cx="50" cy="50" r="5" fill="#000" />
        </svg>
        <div className="vinyl-indicator">
          {playing ? (
            <div className="dots">
              <div className="dot dot-1" />
              <div className="dot dot-2" />
              <div className="dot" />
            </div>
          ) : (
            <div className="paused" />
          )}
        </div>
        {hint && (
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
