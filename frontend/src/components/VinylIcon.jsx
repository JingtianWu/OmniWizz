import React from "react";
import "../index.css";

export default function VinylIcon({ playing, onClick }) {
  return (
    <div className="vinyl-wrapper" onClick={onClick}>
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
      </div>
    </div>
  );
}

