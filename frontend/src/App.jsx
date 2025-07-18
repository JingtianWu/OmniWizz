import React, { useState, useRef, useMemo, useEffect } from "react";
import EditorCanvas from "./components/EditorCanvas";
import VinylIcon from "./components/VinylIcon";
import { MoreVertical } from "lucide-react";
import "./index.css";
import useOmniLogger from "./useOmniLogger";

const BACKEND_URL =
  process.env.NODE_ENV === "development"
    ? ""
    : "https://omniwizz.onrender.com";

function withBase(path) {
  if (!path) return path;
  try {
    return new URL(path, BACKEND_URL).toString();
  } catch {
    return path;
  }
}

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
  const log = useOmniLogger();
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
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showAudioMenu, setShowAudioMenu] = useState(false);

  /* Pagination */
  const [groupIdx, setGroupIdx] = useState(0);

  /* Saved canvas + prompt/lyrics */
  const [canvasUrl, setCanvasUrl] = useState("");
  const [canvasState, setCanvasState] = useState(null);
  const [runFolder, setRunFolder] = useState("");
  const [promptText, setPromptText] = useState("");
  const [lyricsText, setLyricsText] = useState("");
  const origPromptRef = useRef("");
  const origLyricsRef = useRef("");
  const promptModifiedRef = useRef(false);
  const lyricsModifiedRef = useRef(false);
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

    const finalHeight = H;
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

    // waveform is not drawn in the backend image

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

    // Send canvas without waveform for processing
    off.toBlob(blob => {
      const file = new File([blob], "canvas.jpg", { type: "image/jpeg" });
      const audioFile = editorRef.current?.getAudioFile?.();
      handleFile(file, audioFile);
    }, "image/jpeg", 0.92);
  };

  /* Toggle handlers */
  const onTagsToggle = e => {
    const v = e.target.checked;
    if (!v && !doMusic && !doImages) return;
    setDoTags(v);
    log("toggle_tags", { value: v });
  };
  const onMusicToggle = e => {
    const v = e.target.checked;
    if (!v && !doTags && !doImages) return;
    setDoMusic(v);
    log("toggle_music", { value: v });
  };
  const onImagesToggle = e => {
    const v = e.target.checked;
    if (!v && !doTags && !doMusic) return;
    setDoImages(v);
    log("toggle_images", { value: v });
  };

  /* File upload + generate */
  async function handleFile(file, audioFile) {
    if (!file || (!doTags && !doMusic && !doImages)) return;

    setTags([]);
    setAudioUrl("");
    setPendingMusic(false);
    setImages([]);
    setPlaying(false);
    setRunFolder("");
    setPromptText("");
    setLyricsText("");
    origPromptRef.current = "";
    origLyricsRef.current = "";
    promptModifiedRef.current = false;
    lyricsModifiedRef.current = false;
    setPendingPrompt(false);
    setPendingLyrics(false);
    setStage("loading");

    setLoadingPhrase(VERBS[Math.floor(Math.random() * VERBS.length)]);
    const intervalId = setInterval(() => {
      setLoadingPhrase(VERBS[Math.floor(Math.random() * VERBS.length)]);
    }, 3000);

    const data = new FormData();
    data.append("file", file);
    if (audioFile) data.append("audio", audioFile);
    const modes = [doMusic && "music", doTags && "tags", doImages && "images"]
      .filter(Boolean)
      .join(",");
    log("generate_click", { modes, language });

    try {
      const res = await fetch(`${BACKEND_URL}/generate?modes=${modes}&language=${language}`, {
        method: "POST",
        body: data,
      });
      const j = await res.json();

      if (j.tags) {
        const arr = j.tags.tags ?? j.tags;
        setTags(Array.isArray(arr) ? arr : []);
      }
      if (j.music) {
        setAudioUrl(withBase(j.music.audio_url));
        setPendingMusic(!!j.music.pending);
        setRunFolder(j.music.folder || "");
        setPendingPrompt(true);
        setPendingLyrics(true);
        try {
          const [prResp, lyrResp] = await Promise.all([
            fetch(withBase(j.music.prompt_url)),
            fetch(withBase(j.music.lyrics_url))
          ]);
          if (prResp.ok) {
            const txt = await prResp.text();
            origPromptRef.current = txt;
            promptModifiedRef.current = false;
            setPromptText(txt);
            setPendingPrompt(false);
          }
          if (lyrResp.ok) {
            const lyr = await lyrResp.text();
            origLyricsRef.current = lyr;
            lyricsModifiedRef.current = false;
            setLyricsText(lyr);
            setPendingLyrics(false);
          }
        } catch {}
      }
      if (j.images) {
        const arr = j.images.images ?? j.images;
        setImages(Array.isArray(arr) ? arr.map(withBase) : []);
      }
    } catch (err) {
      console.error("Generation failed:", err);
    } finally {
      clearInterval(intervalId);
      setStage("done");
    }
  }

  const returnToEditor = () => {
    log("reedit_canvas_click");
    // Preserve audio state
    const wasPlaying = playing;
    const currentAudioTime = currentTime;
    
    setStage("idle");
    setTimeout(() => {
      editorRef.current?.dismissHint?.();
    }, 0);
    
    // Store audio state for restoration
    if (audioRef.current && wasPlaying) {
      audioRef.current.currentTime = currentAudioTime;
      audioRef.current.pause();
      setPlaying(false);
    }
  };

  useEffect(() => {
    if (stage === "done" && audioRef.current && audioUrl) {
      // Restore audio element state
      audioRef.current.load();
    }
  }, [stage, audioUrl]);

  useEffect(() => {
    if (stage === "idle" && canvasState && editorRef.current?.loadSnapshot) {
      editorRef.current.loadSnapshot(canvasState);
    }
  }, [stage]);

  async function regenerateMusic() {
    if (!doMusic) {
      alert('Music option not selected.');
      return;
    }
    if (!runFolder) return;
    log("regenerate_click", { folder: runFolder });
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
      const res = await fetch(`${BACKEND_URL}/regenerate`, { method: "POST", body: data });
      const j = await res.json();
      if (j.audio_url) {
        setAudioUrl(withBase(j.audio_url) + `?t=${Date.now()}`);
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
    document.querySelectorAll('.cloud-img').forEach((img, i) => {
      if (imagePositions[i]) {
        img.style.setProperty('--x', imagePositions[i].x);
        img.style.setProperty('--y', imagePositions[i].y);
        img.style.setProperty('--rotation', `${imagePositions[i].rotation}deg`);
      }
    });
    document.querySelectorAll('.cloud-tag').forEach((tag, i) => {
      if (tagPositions[i]) {
        tag.style.setProperty('--x', tagPositions[i].x);
        tag.style.setProperty('--y', tagPositions[i].y);
      }
    });
  }, [imagePositions, tagPositions]);
  
  useEffect(() => {
    if (stage === "done") {
      // Re-trigger positioning when returning to done stage
      setTimeout(() => {
        document.querySelectorAll('.cloud-img').forEach((img, i) => {
          if (imagePositions[i]) {
            img.style.setProperty('--x', imagePositions[i].x);
            img.style.setProperty('--y', imagePositions[i].y);
            img.style.setProperty('--rotation', `${imagePositions[i].rotation}deg`);
          }
        });
        document.querySelectorAll('.cloud-tag').forEach((tag, i) => {
          if (tagPositions[i]) {
            tag.style.setProperty('--x', tagPositions[i].x);
            tag.style.setProperty('--y', tagPositions[i].y);
          }
        });
      }, 100);
    }
  }, [stage, imagePositions, tagPositions]);

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
          const r = await fetch(`${BACKEND_URL}/output/${runFolder}/prompt.txt`, { cache: "no-store" });
          if (r.ok) {
            const txt = await r.text();
            origPromptRef.current = txt;
            promptModifiedRef.current = false;
            setPromptText(txt);
            setPendingPrompt(false);
          }
        } catch {}
      }
      if (pendingLyrics) {
        try {
          const r = await fetch(`${BACKEND_URL}/output/${runFolder}/lyrics.lrc`, { cache: "no-store" });
          if (r.ok) {
            const lyr = await r.text();
            origLyricsRef.current = lyr;
            lyricsModifiedRef.current = false;
            setLyricsText(lyr);
            setPendingLyrics(false);
          }
        } catch {}
      }
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, [runFolder, pendingPrompt, pendingLyrics]);

  const progress = duration ? currentTime / duration : 0;
  const theta    = -Math.PI / 2 + 2 * Math.PI * progress;
  const R        = 90;
  const cx       = 100 + R * Math.cos(theta);
  const cy       = 100 + R * Math.sin(theta);
  const promptDisabled  = !doMusic || pendingPrompt;
  const lyricsDisabled  = !doMusic || pendingLyrics;
  const regenDisabled   = !doMusic || regenLoading || pendingMusic;

  const handleDownloadAudio = async () => {
    log("download_audio_click");
    if (!audioUrl) return;
    try {
      const resp = await fetch(audioUrl);
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "omniwizz_audio";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed", err);
    }
  };

  /* RENDER */
  if (stage === "idle") {
    return (
      <div className="app-center-container">

        {canvasUrl && (
          <div
            className="canvas-frame back-button"
            onClick={() => {
              log("back_to_results_click");
              const art = document.querySelector(".artboard");
              if (art) {
                const [bg, ink] = art.querySelectorAll("canvas");
                if (bg && ink) {
                  const w = bg.width, h = bg.height;
                  const c = document.createElement("canvas");
                  c.width = w;
                  c.height = h;
                  const ctx = c.getContext("2d");

                  ctx.drawImage(bg, 0, 0);
                  ctx.drawImage(ink, 0, 0);

                  art.querySelectorAll(".textbox").forEach(tb => {
                    const style = window.getComputedStyle(tb);
                    const fontSize   = style.fontSize;
                    const fontFamily = style.fontFamily;
                    const color      = style.color;

                    const artRect = art.getBoundingClientRect();
                    const tbRect  = tb.getBoundingClientRect();
                    const x = tbRect.left - artRect.left;
                    const y = tbRect.top  - artRect.top + parseInt(fontSize, 10);

                    ctx.font = `${fontSize} ${fontFamily}`;
                    ctx.fillStyle = color;
                    ctx.textBaseline = "top";
                    ctx.fillText(tb.innerText, x, y);
                  });

                  setCanvasUrl(c.toDataURL("image/png"));
                }
              }

              if (editorRef.current?.getSnapshot) {
                setCanvasState(editorRef.current.getSnapshot());
              }
              setStage("done");
            }}
            style={{
              position: "absolute",
              top: "2rem",
              right: "2rem",
              width: "340px",
              height: "240px",
              zIndex: 100
            }}
          >
            <div
              style={{
                width: "100%",
                height: "100%",
                background:
                  "linear-gradient(135deg, #161832 0%, #571c83 45%, #161832 100%)",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                overflow: "hidden"
              }}
            >
              <div
                className="board-frame"
                style={{ width: 300, height: 200, padding: "1rem", pointerEvents: "none" }}
              >
                <div className="center-cluster" style={{ width: 120, height: 120 }}>
                  <div className="vinyl-control-wrapper" style={{ width: 120, height: 120 }}>
                    <svg className="vinyl-progress-ring" viewBox="0 0 200 200">
                      <circle
                        cx="100"
                        cy="100"
                        r="90"
                        fill="none"
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth="4"
                      />
                      <circle
                        cx="100"
                        cy="100"
                        r="90"
                        fill="none"
                        stroke="url(#progressGradientMini)"
                        strokeWidth="4"
                        strokeDasharray={`${2 * Math.PI * 90}`}
                        strokeDashoffset={`${2 * Math.PI * 90 * (1 - 0)}`}
                        transform="rotate(-90 100 100)"
                        style={{ transition: 'stroke-dashoffset 0.1s linear' }}
                      />
                      <circle
                        cx="100"
                        cy="10"
                        r="6"
                        fill="#fff"
                        stroke="url(#progressGradientMini)"
                        strokeWidth="2"
                        style={{
                          filter: 'drop-shadow(0 0 6px rgba(0,255,209,0.6))'
                        }}
                      />
                      <defs>
                        <linearGradient id="progressGradientMini" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%"  style={{ stopColor: '#00ffd1', stopOpacity: 1 }} />
                          <stop offset="50%" style={{ stopColor: '#11cfff', stopOpacity: 1 }} />
                          <stop offset="100%" style={{ stopColor: '#c44cff', stopOpacity: 1 }} />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div style={{ transform: "scale(0.6)" }}>
                      <VinylIcon playing={false} loading={false} onClick={null} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="canvas-overlay">Back to results</div>
          </div>
        )}

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
          <label className="prompt-field">
            <div className="prompt-label">Prompt</div>
            <textarea
              value={promptText}
              onChange={e => {
                const v = e.target.value;
                setPromptText(v);
                const orig = origPromptRef.current;
                if (v !== orig) {
                  if (!promptModifiedRef.current) log("prompt_modified");
                  promptModifiedRef.current = true;
                } else if (promptModifiedRef.current) {
                  log("prompt_reset");
                  promptModifiedRef.current = false;
                }
              }}
              placeholder={
                !doMusic
                  ? "Music option not selected..."
                  : pendingPrompt
                    ? "Loading prompt..."
                    : "Enter music generation prompt"
              }
              disabled={promptDisabled}
              className="prompt-input"
            />
          </label>

          <label className="prompt-field">
            <div className="prompt-label">Lyrics</div>
            <textarea
              value={lyricsText}
              onChange={e => {
                const v = e.target.value;
                setLyricsText(v);
                const orig = origLyricsRef.current;
                if (v !== orig) {
                  if (!lyricsModifiedRef.current) log("lyrics_modified");
                  lyricsModifiedRef.current = true;
                } else if (lyricsModifiedRef.current) {
                  log("lyrics_reset");
                  lyricsModifiedRef.current = false;
                }
              }}
              placeholder={
                !doMusic
                  ? "Music option not selected..."
                  : pendingLyrics
                    ? "Loading lyrics..."
                    : "Enter lyrics (optional)"
              }
              disabled={lyricsDisabled}
              className="prompt-input lyrics-textarea"
              rows={8}
            />
          </label>

          <button
            className="regen-btn"
            onClick={regenerateMusic}
            disabled={regenDisabled}
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
              <div className="vinyl-control-wrapper">
                <svg className="vinyl-progress-ring" viewBox="0 0 200 200">
                  <circle
                    cx="100"
                    cy="100"
                    r="90"
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="4"
                  />
                  <circle
                    cx="100"
                    cy="100"
                    r="90"
                    fill="none"
                    stroke="url(#progressGradient)"
                    strokeWidth="4"
                    strokeDasharray={`${2 * Math.PI * 90}`}
                    strokeDashoffset={`${2 * Math.PI * 90 * (1 - (currentTime / duration || 0))}`}
                    transform="rotate(-90 100 100)"
                    style={{ transition: 'stroke-dashoffset 0.1s linear' }}
                  />
                  <circle
                    cx={cx}
                    cy={cy}
                    r="6"
                    fill="#fff"
                    stroke="url(#progressGradient)"
                    strokeWidth="2"
                    style={{
                      transition: 'cx 0.1s linear, cy 0.1s linear',
                      filter: 'drop-shadow(0 0 6px rgba(0,255,209,0.6))'
                    }}
                  />
                  <defs>
                    <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%"  style={{ stopColor: '#00ffd1', stopOpacity: 1 }} />
                      <stop offset="50%" style={{ stopColor: '#11cfff', stopOpacity: 1 }} />
                      <stop offset="100%" style={{ stopColor: '#c44cff', stopOpacity: 1 }} />
                    </linearGradient>
                  </defs>
                </svg>
                <div 
                  className="vinyl-seek-area"
                  onClick={(e) => {
                    if (!audioRef.current || !duration) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    const centerX = rect.width / 2;
                    const centerY = rect.height / 2;
                    const x = e.clientX - rect.left - centerX;
                    const y = e.clientY - rect.top - centerY;
                    const angle = Math.atan2(y, x) + Math.PI / 2;
                    const normalizedAngle = angle < 0 ? angle + 2 * Math.PI : angle;
                    const progress = normalizedAngle / (2 * Math.PI);
                    audioRef.current.currentTime = progress * duration;
                    log("audio_seek_click", { to: progress * duration });
                  }}
                />
                <VinylIcon
                  playing={playing}
                  loading={pendingMusic}
                  onClick={() => {
                    if (!audioRef.current) return;
                    playing ? audioRef.current.pause() : audioRef.current.play();
                  }}
                />
                {duration > 0 && !pendingMusic && (
                  <button
                    className="vinyl-menu-btn"
                    onClick={() => setShowAudioMenu(prev => !prev)}
                  >
                    <MoreVertical size={18} />
                  </button>
                )}
                {showAudioMenu && (
                  <div
                    className="vinyl-menu"
                    tabIndex={-1}
                    onBlur={() => setShowAudioMenu(false)}
                  >
                    <button
                      className="vinyl-menu-item"
                      onClick={() => { handleDownloadAudio(); setShowAudioMenu(false); }}
                    >
                      Download Audio
                    </button>
                  </div>
                )}
                {duration > 0 && !pendingMusic && (
                  <div className="vinyl-time-display">
                    {Math.floor(currentTime / 60)}:{(Math.floor(currentTime % 60)).toString().padStart(2, '0')} /
                    {Math.floor(duration / 60)}:{(Math.floor(duration % 60)).toString().padStart(2, '0')}
                  </div>
                )}
              </div>
              {audioUrl && (
                <audio
                  ref={audioRef}
                  src={audioUrl}
                  onPlay={() => { setPlaying(true); log("audio_play"); }}
                  onPause={() => { setPlaying(false); log("audio_pause"); }}
                  onEnded={() => setPlaying(false)}
                  onLoadedMetadata={() => setDuration(audioRef.current.duration)}
                  onTimeUpdate={() => setCurrentTime(audioRef.current.currentTime)}
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
                  data-x={x}
                  data-y={y}
                  data-rotation={rotation}
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
                  data-x={x}
                  data-y={y}
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
                setGroupIdx(g => {
                  const next = (g - 1 + groups) % groups;
                  log("carousel_prev_click", { index: next });
                  return next;
                });
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
                setGroupIdx(g => {
                  const next = (g + 1) % groups;
                  log("carousel_next_click", { index: next });
                  return next;
                });
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

