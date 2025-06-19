import React, { useState, useRef, useMemo, useEffect } from "react";
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


function getPolarPosition(index, total, baseRadius, randomRange = 0, aspectX = 1.5, aspectY = 1) {
  const angle = (2 * Math.PI * index) / total;
  const randomOffset = (Math.random() - 0.5) * randomRange;
  const radius = baseRadius + randomOffset;
  const x = 50 + aspectX * radius * Math.cos(angle);
  const y = 50 + aspectY * radius * Math.sin(angle);
  return { x, y };
}

export default function App() {
  const editorRef = useRef(null);
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
  const [pendingMusic, setPendingMusic] = useState(false);
  const [images, setImages]   = useState([]);

  /* Audio */
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  /* Pagination */
  const [groupIdx, setGroupIdx] = useState(0);

  /* Saved canvas + prompt/lyrics */
  const [canvasUrl, setCanvasUrl] = useState("");
  const [canvasState, setCanvasState] = useState(null);
  const [runFolder, setRunFolder] = useState("");
  const [promptText, setPromptText] = useState("");
  const [lyricsText, setLyricsText] = useState("");
  const [regenLoading, setRegenLoading] = useState(false);
  const [pendingPrompt, setPendingPrompt] = useState(false);
  const [pendingLyrics, setPendingLyrics] = useState(false);

  const captureAndGenerate = () => {
    const art = document.querySelector(".artboard");
    const [bgCanvas, inkCanvas] = art.querySelectorAll("canvas");
    const audioCanvas = document.querySelector(".wave-strip");

    const W = bgCanvas.width;
    const H = bgCanvas.height;
    const hasWave = !!(audioCanvas && editorRef.current?.hasUserAudio?.());

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

    // Create a separate canvas for display (main part only)
    const displayCanvas = document.createElement("canvas");
    displayCanvas.width = W;
    displayCanvas.height = H;
    const displayCtx = displayCanvas.getContext("2d");

    displayCtx.drawImage(bgCanvas, 0, 0);
    displayCtx.drawImage(inkCanvas, 0, 0);

    art.querySelectorAll(".textbox").forEach(tb => {
      const style = window.getComputedStyle(tb);
      const fontSize = style.fontSize;
      const fontFamily = style.fontFamily;
      const color = style.color;

      const artRect = art.getBoundingClientRect();
      const tbRect = tb.getBoundingClientRect();
      const x = tbRect.left - artRect.left;
      const y = tbRect.top - artRect.top + parseInt(fontSize, 10);

      displayCtx.font = `${fontSize} ${fontFamily}`;
      displayCtx.fillStyle = color;
      displayCtx.textBaseline = "top";
      displayCtx.fillText(tb.innerText, x, y);
    });

    // Set canvas URL to display canvas (main part only)
    setCanvasUrl(displayCanvas.toDataURL("image/png"));
    if (editorRef.current && editorRef.current.getSnapshot) {
      setCanvasState(editorRef.current.getSnapshot());
    }

    // Send full canvas (with waveform if present) for processing
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
    setPendingMusic(false);
    setImages([]);
    setPlaying(false);
    setRunFolder("");
    setPromptText("");
    setLyricsText("");
    setPendingPrompt(false);
    setPendingLyrics(false);
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
        setPendingMusic(!!j.music.pending);
        setRunFolder(j.music.folder || "");
        setPendingPrompt(true);
        setPendingLyrics(true);
        try {
          const [prResp, lyrResp] = await Promise.all([
            fetch(j.music.prompt_url),
            fetch(j.music.lyrics_url)
          ]);
          if (prResp.ok) {
            setPromptText(await prResp.text());
            setPendingPrompt(false);
          }
          if (lyrResp.ok) {
            setLyricsText(await lyrResp.text());
            setPendingLyrics(false);
          }
        } catch {}
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

  const returnToEditor = () => {
    setStage("idle");
    setTimeout(() => {
      editorRef.current?.dismissHint?.();
    }, 0);
  };

  useEffect(() => {
    if (stage === "idle" && canvasState && editorRef.current?.loadSnapshot) {
      editorRef.current.loadSnapshot(canvasState);
    }
  }, [stage]);

  async function regenerateMusic() {
    if (!runFolder) return;
    setRegenLoading(true);
    setPendingMusic(true);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.load();
    }
    setPlaying(false);
    try {
      const data = new FormData();
      data.append("folder", runFolder);
      data.append("prompt", promptText);
      data.append("lyrics", lyricsText);
      const res = await fetch("/regenerate", { method: "POST", body: data });
      const j = await res.json();
      if (j.audio_url) {
        setAudioUrl(j.audio_url + `?t=${Date.now()}`);
      }
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setRegenLoading(false);
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
      const { x, y } = getPolarPosition(i, visibleTags.length, 50, 30, 1.4, 0.9);
      return { x, y };
    });
  }, [visibleTags]);

  const imagePositions = useMemo(() => {
    return visibleImages.map((_, i) => {
      const { x, y } = getPolarPosition(i, visibleImages.length, 50, 30, 1.4, 0.9);
      const rotation = Math.floor(Math.random() * 12 - 6);
      return { x, y, rotation };
    });
  }, [visibleImages]);

  useEffect(() => {
    if (!pendingMusic || !audioUrl) return;
    const id = setInterval(async () => {
      try {
        const resp = await fetch(audioUrl, { cache: "no-store" });
        if (resp.ok) {
          setPendingMusic(false);
          setAudioUrl(audioUrl + `?t=${Date.now()}`);
          clearInterval(id);
        }
      } catch {}
    }, 10000);
    return () => clearInterval(id);
  }, [pendingMusic, audioUrl]);

  useEffect(() => {
    if (!runFolder || (!pendingPrompt && !pendingLyrics)) return;
    const check = async () => {
      if (pendingPrompt) {
        try {
          const r = await fetch(`/output/${runFolder}/prompt.txt`, { cache: "no-store" });
          if (r.ok) {
            setPromptText(await r.text());
            setPendingPrompt(false);
          }
        } catch {}
      }
      if (pendingLyrics) {
        try {
          const r = await fetch(`/output/${runFolder}/lyrics.lrc`, { cache: "no-store" });
          if (r.ok) {
            setLyricsText(await r.text());
            setPendingLyrics(false);
          }
        } catch {}
      }
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, [runFolder, pendingPrompt, pendingLyrics]);

  /* RENDER */
  if (stage === "idle") {
    return (
      <div className="app-center-container">
        <div style={{ display: "flex", gap: "2rem", alignItems: "flex-start" }}>
          <EditorCanvas
            ref={editorRef}
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
    <div className="done-container">
      <div className="done-left">
        {canvasUrl && (
          <div className="canvas-frame" onClick={returnToEditor}>
            <img src={canvasUrl} alt="final canvas" style={{ width: "100%" }} />
            <div className="canvas-overlay">Click to re-edit</div>
          </div>
        )}
        <div className="prompt-box">
          <label>
            <div className="prompt-label">Prompt</div>
            <textarea
              value={promptText}
              onChange={e => setPromptText(e.target.value)}
              placeholder={pendingPrompt ? "Loading prompt..." : "Music prompt"}
              disabled={pendingPrompt}
              className="styled-textarea"
            />
          </label>
          <label>
            <div className="prompt-label">Lyrics</div>
            <textarea
              value={lyricsText}
              onChange={e => setLyricsText(e.target.value)}
              placeholder={pendingLyrics ? "Loading lyrics..." : "Lyrics"}
              disabled={pendingLyrics}
              className="styled-textarea"
            />
          </label>
          <button
            className="generate-btn"
            onClick={regenerateMusic}
            disabled={regenLoading || pendingMusic}
          >
            {regenLoading ? "Regenerating..." : "Regenerate Music"}
          </button>
        </div>
      </div>
      <div className="app-right-container">
        <div className="board-frame">
          <div className="center-cluster">

          {doMusic && (
            <>
              <VinylIcon
                playing={playing}
                loading={pendingMusic}
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
  </div>
  );
}

