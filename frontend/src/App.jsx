import React, { useState, useRef } from "react";
import UploadCanvas from "./components/UploadCanvas";
import "./index.css";

export default function App() {
  /* Toggles */
  const [doTags,   setDoTags]   = useState(true);
  const [doMusic,  setDoMusic]  = useState(true);
  const [doImages, setDoImages] = useState(true);

  /* Language */
  const [language, setLanguage] = useState("en");

  /* Stage */
  const [stage,    setStage]    = useState("idle");

  /* Data */
  const [tags,     setTags]     = useState([]);
  const [audioUrl, setAudioUrl] = useState("");
  const [images,   setImages]   = useState([]);

  /* Audio */
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  /* Loading */
  const [loading, setLoading] = useState(false);

  /* Group index for tags */
  const [groupIdx, setGroupIdx] = useState(0);

  /* Toggle handlers */
  const onTagsToggle = e => {
    const v = e.target.checked;
    if (!v && !doMusic && !doImages) return;
    setDoTags(v);
  };
  const onMusicToggle = e => {
    const v = e.target.checked;
    if (!v && !doTags && !doImages) return;
    setDoMusic(v);
  };
  const onImagesToggle = e => {
    const v = e.target.checked;
    if (!v && !doTags && !doMusic) return;
    setDoImages(v);
  };

  /* Helpers */
  function fileToFormData(file) {
    const d = new FormData();
    d.append("file", file);
    return d;
  }

  /* Upload + Generate */
  async function handleFile(file) {
    if (!file || (!doTags && !doMusic && !doImages)) return;

    // reset
    setTags([]);
    setAudioUrl("");
    setImages([]);
    setPlaying(false);
    setStage("loading");
    setLoading(true);

    const data = fileToFormData(file);
    // build modes param
    const modesList = [
      doMusic  ? "music"  : null,
      doTags   ? "tags"   : null,
      doImages ? "images" : null,
    ].filter(Boolean).join(",");

    try {
      const res = await fetch(
        `/generate?modes=${modesList}&language=${language}`,
        {
          method: "POST",
          body: data,
        }
      );
      const j = await res.json();

      // parse tags
      if (j.tags) {
        const arr = j.tags.tags ?? j.tags;
        setTags(Array.isArray(arr) ? arr : []);
      }
      // parse music
      if (j.music) {
        setAudioUrl(j.music.audio_url);
      }
      // parse images
      if (j.images) {
        const arr = j.images.images ?? j.images;
        setImages(Array.isArray(arr) ? arr : []);
      }
    } catch (err) {
      console.error("Generation failed:", err);
    }

    setLoading(false);
    setStage("done");
  }

  /* Tag grouping */
  function currentGroup() {
    const size = 8;
    const groups = Math.ceil(tags.length / size) || 1;
    const idx = groupIdx % groups;
    const start = idx * size;
    return tags.slice(start, start + size);
  }
  const visibleTags = currentGroup();

  /* Idle state */
  if (stage === "idle") {
    return (
      <div className="app-center">
        <div className="toggles">
          <label>
            <input type="checkbox" checked={doTags}   onChange={onTagsToggle}  /> Tags
          </label>
          <label>
            <input type="checkbox" checked={doMusic}  onChange={onMusicToggle} /> Music
          </label>
          <label>
            <input type="checkbox" checked={doImages} onChange={onImagesToggle}/> Images
          </label>
          <label className="language-selector">
            Language:
            <select value={language} onChange={e => setLanguage(e.target.value)}>
              <option value="en">English</option>
              <option value="zh">中文</option>
            </select>
          </label>
        </div>
        <UploadCanvas onDrop={handleFile} />
      </div>
    );
  }

  /* Loading state */
  if (stage === "loading") {
    return (
      <div className="app-center">
        {doTags   && <div>Generating tags…</div>}
        {doMusic  && <div>Generating music…</div>}
        {doImages && <div>Generating images…</div>}
      </div>
    );
  }

  /* Done state */
  return (
    <div className="app-center">
      <div className="mood-board">
        {/* Music center */}
        {doMusic && (
          <div
            className={`play-circle ${playing ? "playing" : ""}`}
            onClick={() => {
              const groups = Math.ceil(tags.length / 8) || 1;
              setGroupIdx(g => (g + 1) % groups);
              if (!audioRef.current) return;
              playing ? audioRef.current.pause() : audioRef.current.play();
            }}
          >
            {playing ? "⏸" : "▶️"}
          </div>
        )}
        {audioUrl && (
          <audio
            ref={audioRef}
            src={audioUrl}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
            style={{ display: "none" }}
          />
        )}

        {/* Tags ring */}
        {doTags &&
          visibleTags.map((tag, i) => {
            const angle = (2 * Math.PI * i) / visibleTags.length + (Math.random() - 0.5) * 0.3;
            const radius = 25 + Math.random() * 23;
            const x = 50 + radius * Math.cos(angle);
            const y = 50 + radius * Math.sin(angle);
            return (
              <div key={`tag-${i}`} className="tag-item" style={{ left: `${x}%`, top: `${y}%` }}>
                {tag}
              </div>
            );
          })}

        {/* Images ring */}
        {doImages &&
          images.map((src, i) => {
            const angle = (2 * Math.PI * i) / images.length + (Math.random() - 0.5) * 0.3;
            const radius = 25 + Math.random() * 23;
            const x = 50 + radius * Math.cos(angle);
            const y = 50 + radius * Math.sin(angle);
            return (
              <img
                key={`img-${i}`}
                src={src}
                alt=""
                className="image-item"
                style={{ left: `${x}%`, top: `${y}%` }}
              />
            );
          })}
      </div>
    </div>
  );
}