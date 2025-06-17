import React, { useState, useRef, useMemo } from "react";
import EditorCanvas from "./components/EditorCanvas";
import VinylIcon from "./components/VinylIcon";
import "./index.css";

const VERBS = [
  "Dreaming in pixels",
  "Composing wonders",
  "Weaving sound-scapes",
  "Painting ambience",
  "Brewing imagination",
  "Sketching possibilities",
  "Sculpting ideas",
];


function getPolarPosition(index, total, baseRadius, randomRange = 0) {
  const angle = (2 * Math.PI * index) / total;
  const randomOffset = (Math.random() - 0.5) * randomRange;
  const radius = baseRadius + randomOffset;
  const x = 50 + radius * Math.cos(angle);
  const y = 50 + radius * Math.sin(angle);
  return { x, y };
}

export default function App() {
  /* Toggles */
  const [doTags, setDoTags]     = useState(true);
  const [doMusic, setDoMusic]   = useState(true);
  const [doImages, setDoImages] = useState(true);

  /* Language */
  const [language, setLanguage] = useState("en");

  /* Stage */
  const [stage, setStage]             = useState("idle");
  const [loadingPhrase, setLoadingPhrase] = useState("");

  /* Data */
  const [tags, setTags]       = useState([]);
  const [audioUrl, setAudioUrl]   = useState("");
  const [images, setImages]   = useState([]);

  /* Audio */
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  /* Pagination */
  const [groupIdx, setGroupIdx] = useState(0);

  const captureAndGenerate = () => {
    const art = document.querySelector(".artboard");
    const [bgCanvas, inkCanvas] = art.querySelectorAll("canvas");
    const audioCanvas = document.querySelector(".wave-strip");

    const W = bgCanvas.width;
    const H = bgCanvas.height;
    const hasWave = !!audioCanvas;

    const finalHeight = hasWave ? H + audioCanvas.height : H;
    const off = document.createElement("canvas");
    off.width = W;
    off.height = finalHeight;
    const ctx = off.getContext("2d");

    ctx.drawImage(bgCanvas, 0, 0);
    ctx.drawImage(inkCanvas, 0, 0);

    art.querySelectorAll(".textbox").forEach(tb => {
      const style = window.getComputedStyle(tb);
      const fontSize = style.fontSize;
      const fontFamily = style.fontFamily;
      const color = style.color;

      const artRect = art.getBoundingClientRect();
      const tbRect = tb.getBoundingClientRect();
      const x = tbRect.left - artRect.left;
      const y = tbRect.top - artRect.top + parseInt(fontSize, 10);

      ctx.font = `${fontSize} ${fontFamily}`;
      ctx.fillStyle = color;
      ctx.textBaseline = "top";
      ctx.fillText(tb.innerText, x, y);
    });

    if (hasWave) {
      ctx.drawImage(audioCanvas, 0, H);
    }

    off.toBlob(blob => {
      const file = new File([blob], "canvas.jpg", { type: "image/jpeg" });
      handleFile(file);
    }, "image/jpeg", 0.92);
  };

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

  /* File upload + generate */
  async function handleFile(file) {
    if (!file || (!doTags && !doMusic && !doImages)) return;

    setTags([]);
    setAudioUrl("");
    setImages([]);
    setPlaying(false);
    setStage("loading");

    setLoadingPhrase(VERBS[Math.floor(Math.random() * VERBS.length)]);
    const intervalId = setInterval(() => {
      setLoadingPhrase(VERBS[Math.floor(Math.random() * VERBS.length)]);
    }, 3000);

    const data = new FormData();
    data.append("file", file);
    const modes = [doMusic && "music", doTags && "tags", doImages && "images"]
      .filter(Boolean)
      .join(",");

    try {
      const res = await fetch(`/generate?modes=${modes}&language=${language}`, {
        method: "POST",
        body: data,
      });
      const j = await res.json();

      if (j.tags) {
        const arr = j.tags.tags ?? j.tags;
        setTags(Array.isArray(arr) ? arr : []);
      }
      if (j.music) {
        setAudioUrl(j.music.audio_url);
      }
      if (j.images) {
        const arr = j.images.images ?? j.images;
        setImages(Array.isArray(arr) ? arr : []);
      }
    } catch (err) {
      console.error("Generation failed:", err);
    } finally {
      clearInterval(intervalId);
      setStage("done");
    }
  }

  /* Memoized slices */
  const visibleTags = useMemo(() => {
    const size = 8;
    const groups = Math.max(1, Math.ceil(tags.length / size));
    const idx = groupIdx % groups;
    return tags.slice(idx * size, idx * size + size);
  }, [tags, groupIdx]);

  const visibleImages = useMemo(() => {
    const size = 8;
    const groups = Math.max(1, Math.ceil(images.length / size));
    const idx = groupIdx % groups;
    return images.slice(idx * size, idx * size + size);
  }, [images, groupIdx]);

  /* Memoized random positions */
  const tagPositions = useMemo(() => {
    return visibleTags.map((_, i) => {
      const { x, y } = getPolarPosition(i, visibleTags.length, 50, 30);
      return { x, y };
    });
  }, [visibleTags]);

  const imagePositions = useMemo(() => {
    return visibleImages.map((_, i) => {
      const { x, y } = getPolarPosition(i, visibleImages.length, 50, 30);
      const rotation = Math.floor(Math.random() * 12 - 6);
      return { x, y, rotation };
    });
  }, [visibleImages]);

  /* RENDER */
  if (stage === "idle") {
    return (
      <div className="app-center-container">
        <div style={{ display: "flex", gap: "2rem", alignItems: "flex-start" }}>
          <EditorCanvas 
            onSubmit={handleFile}
            language={language}
            setLanguage={setLanguage}
          />
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem",
            background: "rgba(20, 20, 30, 0.9)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: "16px",
            padding: "24px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            minWidth: "200px",
            alignSelf: "flex-end",
          }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Options</h3>
            <div className="options-divider" />
            <label className="option-toggle">
              <input type="checkbox" checked={doTags}   onChange={onTagsToggle}   />
              <span>Tags</span>
            </label>
            <label className="option-toggle">
              <input type="checkbox" checked={doMusic}  onChange={onMusicToggle}  />
              <span>Music</span>
            </label>
            <label className="option-toggle">
              <input type="checkbox" checked={doImages} onChange={onImagesToggle} />
              <span>Images</span>
            </label>
            <button
              onClick={captureAndGenerate}
              className="generate-btn"
            >
              Generate
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (stage === "loading") {
    const modesLine = [doTags && "tagging", doMusic && "scoring", doImages && "illustrating"]
      .filter(Boolean)
      .join(" · ");
    return (
      <div className="loading-overlay" role="status" aria-live="polite">
        <div className="loader-ring"><div/><div/><div/><div/></div>
        <p className="loader-text">{loadingPhrase}…</p>
        {modesLine && <p className="loader-sub">{modesLine}</p>}
      </div>
    );
  }

  return (
    <div className="app-right-container">
      <div className="board-frame">
        <div className="center-cluster">

          {doMusic && (
            <>
              <VinylIcon
                playing={playing}
                onClick={() => {
                  if (!audioRef.current) return;
                  playing ? audioRef.current.pause() : audioRef.current.play();
                }}
              />
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
            </>
          )}

          {doImages && (
            <div className="image-cloud">
              {imagePositions.map(({ x, y, rotation }, i) => (
                <img
                  key={i}
                  src={visibleImages[i]}
                  alt=""
                  className="cloud-img"
                  draggable={false}
                  style={{
                    left: `${x}%`,
                    top: `${y}%`,
                    "--r": `${rotation}deg`,
                    userSelect: "none",
                    WebkitUserDrag: "none"
                  }}
                />
              ))}
            </div>
          )}

          {doTags && (
            <div className="tag-cloud">
              {tagPositions.map(({ x, y }, i) => (
                <span
                  key={i}
                  className="cloud-tag"
                  draggable={false}
                  style={{
                    left: `${x}%`, 
                    top: `${y}%`,
                    userSelect: "none"
                  }}
                >
                  {visibleTags[i]}
                </span>
              ))}
            </div>
          )}

          <div style={{
            position: "absolute",
            bottom: "-110px",
            display: "flex",
            gap: "1rem",
            zIndex: 9999,
          }}>
            <button
              onClick={() => {
                const groups = Math.max(1, Math.ceil(tags.length / 8));
                setGroupIdx(g => (g - 1 + groups) % groups);
              }}
              style={{
                fontSize: "1.2rem",
                padding: "0.3rem 0.6rem",
                borderRadius: "50%",
                border: "none",
                background: "rgba(255,255,255,0.15)",
                backdropFilter: "blur(10px)",
                color: "#fff",
                cursor: "pointer",
              }}
            >
              &#x276E;
            </button>
            <button
              onClick={() => {
                const groups = Math.max(1, Math.ceil(tags.length / 8));
                setGroupIdx(g => (g + 1) % groups);
              }}
              style={{
                fontSize: "1.2rem",
                padding: "0.3rem 0.6rem",
                borderRadius: "50%",
                border: "none",
                background: "rgba(255,255,255,0.15)",
                backdropFilter: "blur(10px)",
                color: "#fff",
                cursor: "pointer",
              }}
            >
              &#x276F;
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}

