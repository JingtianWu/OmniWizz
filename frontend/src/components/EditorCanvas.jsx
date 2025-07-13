import React, { useRef, useState, useEffect, forwardRef, useImperativeHandle } from "react";
import "./EditorCanvas.css";
import {
  Pencil,
  Eraser,
  Type,
  Undo2,
  Redo2,
  Trash2,
  Palette,
  Move
} from "lucide-react";

/* canvas sizes */
const W = 896, H = 504, AUDIO_H = 100, MAX_HISTORY = 50;

/* font size limits */
const MIN_FONT_SIZE = 1;
const MAX_FONT_SIZE = 200;

const EditorCanvas = forwardRef(function EditorCanvas({ onSubmit, language, setLanguage }, ref) {
  /* refs ----------------------------------------------------------- */
  const bgRef = useRef(null);   // background layer
  const inkRef = useRef(null);  // pen / eraser
  const audRef = useRef(null);  // waveform strip
  const audioFileRef = useRef(null);
  const imgRef = useRef(null);  // <img> for background
  const contRef = useRef(null); // overall container
  const dragRef = useRef(null); // {id,dx,dy} while dragging text
  const histRef = useRef({ states: [], idx: -1 }); // undo stack

  /* state ---------------------------------------------------------- */
  const [bgSrc, setBg] = useState(null);
  const [mode, setMode] = useState("move");
  const [color, setColor] = useState("#222222");
  const [penSize, setPenSize] = useState(4);
  const [eraserSize, setEraserSize] = useState(10);
  const [textSize, setTextSize] = useState(24);
  const drawingRef = useRef(false); // track active stroke without state lag

  const [boxes, setBoxes] = useState([]);       // text boxes {id,x,y,fs,color,width,height,text,editing}
  const [selId, setSel]  = useState(null);

  const [hasWave, setWave] = useState(false);   // waveform present?
  const [showHint, setShowHint] = useState(true); // show start hint?
  const [showTrashMenu, setShowTrashMenu] = useState(false);

  /* helpers -------------------------------------------------------- */
  const bgCtx  = () => bgRef.current .getContext("2d");
  const inkCtx = () => inkRef.current.getContext("2d");
  const audCtx = () => audRef.current.getContext("2d");
  const ptr = e => {
    const r = inkRef.current.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };

  /* -------------- History snapshots -------------- */
  const makeSnapshot = () => (
    inkRef.current.toDataURL("image/png")
  );

  const snapshot = () => {
    histRef.current.states = histRef.current.states.slice(0, histRef.current.idx + 1);
    histRef.current.states.push(makeSnapshot());
    if (histRef.current.states.length > MAX_HISTORY) histRef.current.states.shift();
    histRef.current.idx = histRef.current.states.length - 1;
  };
  const restore = dataUrl => {
    const ctx = inkCtx();
    ctx.save();                                // isolate current composite mode
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, W, H);

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      ctx.restore();                           // return to the tool’s active mode
    };
    img.src = dataUrl;
  };
  const undo = () => { const h=histRef.current; if(h.idx>0) restore(h.states[--h.idx]); };
  const redo = () => { const h=histRef.current; if(h.idx<h.states.length-1) restore(h.states[++h.idx]); };
  useEffect(snapshot, []);                               // save blank initial

  useImperativeHandle(ref, () => ({
    getSnapshot: () => ({
      ink: makeSnapshot(),
      bg: bgSrc,
      boxes,
      hasWave,
      audio: hasWave ? audRef.current.toDataURL("image/png") : null
    }),
    getAudioFile: () => audioFileRef.current,
    loadSnapshot: snap => {
      if (!snap) return;

      if (snap.ink) {
        restore(snap.ink);
        histRef.current.states = [snap.ink];
        histRef.current.idx = 0;
      }

      if (snap.bg) {
        const im = new Image();
        im.onload = () => { imgRef.current = im; setBg(snap.bg); };
        im.src = snap.bg;
      } else {
        setBg(null);
        imgRef.current = null;
      }

      setBoxes(Array.isArray(snap.boxes) ? snap.boxes : []);

      if (snap.audio) {
        const im = new Image();
        im.onload = () => { audCtx().drawImage(im, 0, 0); };
        im.src = snap.audio;
        setWave(true);
      } else {
        audCtx().clearRect(0, 0, W, AUDIO_H);
        setWave(false);
      }
    },
    dismissHint: () => setShowHint(false),
    hasUserAudio: () => hasWave
  }));

  // Close any active text editing when switching tools
  useEffect(() => {
    if (mode !== "text") {
      let editedIds = [];
      setBoxes(bs => {
        editedIds = bs.filter(b => b.editing).map(b => b.id);
        if (editedIds.length === 0) return bs;
        return bs.map(b => b.editing ? { ...b, editing: false } : b);
      });
      if (editedIds.length) {
        editedIds.forEach(id => {
          const el = document.getElementById(`tb-${id}`);
          if (el) el.blur();
        });
      }
    }

    if (mode === "pen" || mode === "erase") {
      setSel(null);
    }
  }, [mode]);

  /* -------------- Keyboard shortcuts -------------- */
  useEffect(()=>{
    const key = e => {
      if ((e.metaKey||e.ctrlKey)&&e.key==="z" && !e.shiftKey){ e.preventDefault(); undo(); }
      if ((e.metaKey||e.ctrlKey)&&e.key==="z" &&  e.shiftKey){ e.preventDefault(); redo(); }
      if (e.key==="Escape") setSel(null);
      if ((e.key === "Delete" || e.key === "Backspace") && selId !== null) {
        const active = document.activeElement;
        if (active && active.isContentEditable) {
          return; // don't delete if actively editing text
        }
        setBoxes(bs => bs.filter(b => b.id !== selId));
        setSel(null);
      }
    };
    document.addEventListener("keydown", key);
    return ()=>document.removeEventListener("keydown", key);
  }, [selId]);

  /* -------------- Paint / update background -------------- */
  const paintBg = src => {
    const cx = bgCtx(); cx.clearRect(0,0,W,H);
    cx.fillStyle="#ffffff"; cx.fillRect(0,0,W,H);
    if (!src || !imgRef.current) return;
    const r = Math.min(W/imgRef.current.width, H/imgRef.current.height);
    const w = imgRef.current.width*r, h = imgRef.current.height*r;
    cx.drawImage(imgRef.current, (W-w)/2, (H-h)/2, w, h);
  };
  useEffect(()=>paintBg(bgSrc), [bgSrc]);

  /* -------------- Global drag for text boxes -------------- */
  useEffect(()=>{
    const move = e => {
      if(!dragRef.current) return;
      const { id, dx, dy, width, height } = dragRef.current;
      const pr = contRef.current.getBoundingClientRect();

      const nxRaw = e.clientX - pr.left + dx;
      const nyRaw = e.clientY - pr.top  + dy;

      // clamp inside canvas
      const nx = Math.max(0, Math.min(W - width, nxRaw));
      const ny = Math.max(0, Math.min(H - height, nyRaw));

      setBoxes(bs => bs.map(b => b.id === id ? { ...b, x: nx, y: ny } : b));
    };
    const up = () => { if(dragRef.current){ dragRef.current=null; } };
    document.addEventListener("mousemove", move);
    document.addEventListener("mouseup",   up);
    return ()=>{ document.removeEventListener("mousemove", move);
                 document.removeEventListener("mouseup",   up); };
  }, []);

  useEffect(() => {
    boxes.forEach(b => {
      const el = document.getElementById(`tb-${b.id}`);
      if (el) {
        el.style.setProperty('--font-size', b.fs);
        el.style.setProperty('--color', b.color);
        if (b.width != null) el.style.setProperty('--width', `${b.width}px`);
        if (b.height != null) el.style.setProperty('--height', `${b.height}px`);
        const parent = el.parentElement;
        if (parent) {
          parent.style.setProperty('--x', b.x);
          parent.style.setProperty('--y', b.y);
        }
      }
    });
  }, [boxes]);

  /* -------------- Drop image on artboard -------------- */
  const onBgDrop = e => {
    e.preventDefault();
    if (showHint) setShowHint(false);
    const f = e.dataTransfer.files[0];
    if(!f?.type.startsWith("image/")) return;
    const r = new FileReader();
    r.onload = ev=>{
      const im=new Image();
      im.onload = ()=>{ imgRef.current=im; setBg(ev.target.result); };
      im.src = ev.target.result;
    };
    r.readAsDataURL(f);
  };

  /* -------------- Pen / Erase / Text -------------- */
  const startStroke = e => {
    if (showHint) setShowHint(false);
    const {x,y} = ptr(e);
    
    if (mode === "pen" || mode === "erase") {
      const cx = inkCtx();
      cx.save();                                 // snapshot context state
      cx.lineCap = cx.lineJoin = "round";
      cx.lineWidth = mode === "pen" ? penSize : eraserSize;
      cx.globalCompositeOperation = mode === "pen" ? "source-over" : "destination-out";
      if (mode === "pen") cx.strokeStyle = color;
      cx.beginPath();
      cx.moveTo(x, y);
      drawingRef.current = true;
      return;
    }
    
    if (mode==="text"){
      if(e.target.classList.contains("textbox") ||
        e.target.classList.contains("resize-handle") ||
        e.target.classList.contains("size-toolbar") ||
        e.target.closest(".size-toolbar")) {
        return;
      }
      
      // purge empties
      setBoxes(bs=>bs.filter(b=>{
        const el=document.getElementById(`tb-${b.id}`); 
        return el && el.innerText.trim() && el.innerText !== "Type here...";
      }));
      
      const id = Date.now();
      setBoxes(bs => [
        ...bs,
        {
          id,
          x,
          y,
          fs: textSize,
          color,
          editing: true,
          width: 200,
          height: textSize * 1.2 + 10,
          text: ""
        }
      ]);
      setSel(id);
      
      // Auto-focus the new text box
      setTimeout(() => {
        const el = document.getElementById(`tb-${id}`);
        if (el) el.focus();
      }, 10);
      
      // Switch back to move mode after creating textbox
      setMode("move");
      return;
    }
    
    // If in move mode, handle selection/deselection
    if (mode === "move") setSel(null);
  };
  const drawMove = e => {
    if (drawingRef.current) {
      const { x, y } = ptr(e);
      inkCtx().lineTo(x, y);
      inkCtx().stroke();
    }
  };

  const endStroke = () => {
    if (drawingRef.current) {
      drawingRef.current = false;
      inkCtx().restore();
      snapshot();
    }
  };

  /* -------------- Drop audio on waveform strip -------------- */
  const onAudDrop = e => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if(!f?.type.startsWith("audio/")) return;
    audioFileRef.current = f;
    const AC = new (window.AudioContext||window.webkitAudioContext)();
    const rd = new FileReader();
    rd.onload = ev=>{
      AC.decodeAudioData(ev.target.result).then(buf=>{
        renderWave(buf);
        setWave(true);
      });
    };
    rd.readAsArrayBuffer(f);
  };
  const renderWave = buf => {
    const c = audCtx(); 
    c.clearRect(0,0,W,AUDIO_H);
    
    // Draw background gradient
    const bgGrad = c.createLinearGradient(0,0,0,AUDIO_H);
    bgGrad.addColorStop(0, "rgba(20, 20, 30, 0.9)");
    bgGrad.addColorStop(1, "rgba(10, 10, 20, 0.95)");
    c.fillStyle = bgGrad;
    c.fillRect(0, 0, W, AUDIO_H);
    
    // Draw grid lines (time markers)
    c.strokeStyle = "rgba(255, 255, 255, 0.05)";
    c.lineWidth = 1;
    for(let i = 0; i < W; i += 60) {
      c.beginPath();
      c.moveTo(i, 0);
      c.lineTo(i, AUDIO_H);
      c.stroke();
    }
    
    // Draw horizontal grid lines
    for(let i = 0; i < AUDIO_H; i += 20) {
      c.beginPath();
      c.moveTo(0, i);
      c.lineTo(W, i);
      c.stroke();
    }
    
    // Process channels
    const numChannels = Math.min(buf.numberOfChannels, 2);
    const channelHeight = AUDIO_H / numChannels;
    
    for(let ch = 0; ch < numChannels; ch++) {
      const data = buf.getChannelData(ch);
      const step = Math.floor(data.length/W);
      const yOffset = ch * channelHeight + channelHeight/2;
      
      // Draw waveform fill (RMS)
      const rmsGrad = c.createLinearGradient(0,yOffset-channelHeight/2,0,yOffset+channelHeight/2);
      rmsGrad.addColorStop(0, "rgba(0, 200, 255, 0.3)");
      rmsGrad.addColorStop(0.5, "rgba(0, 150, 255, 0.5)");
      rmsGrad.addColorStop(1, "rgba(0, 200, 255, 0.3)");
      
      c.beginPath();
      c.moveTo(0, yOffset);
      
      // Draw RMS envelope
      for(let i=0;i<W;i++){
        let sum=0; 
        for(let j=0;j<step;j++) {
          sum += data[i*step+j] * data[i*step+j];
        }
        const rms = Math.sqrt(sum/step);
        const h = rms * channelHeight * 0.35;
        c.lineTo(i, yOffset - h);
      }
      
      // Complete the shape
      for(let i=W-1;i>=0;i--){
        let sum=0; 
        for(let j=0;j<step;j++) {
          sum += data[i*step+j] * data[i*step+j];
        }
        const rms = Math.sqrt(sum/step);
        const h = rms * channelHeight * 0.35;
        c.lineTo(i, yOffset + h);
      }
      
      c.closePath();
      c.fillStyle = rmsGrad;
      c.fill();
      
      // Draw peak waveform outline
      c.strokeStyle = "rgba(100, 200, 255, 0.8)";
      c.lineWidth = 1.5;
      c.beginPath();
      
      for(let i=0;i<W;i++){
        let max = 0, min = 0;
        for(let j=0;j<step;j++) {
          const sample = data[i*step+j];
          max = Math.max(max, sample);
          min = Math.min(min, sample);
        }
        
        const maxH = max * channelHeight * 0.45;
        
        if(i === 0) {
          c.moveTo(i, yOffset - maxH);
        } else {
          c.lineTo(i, yOffset - maxH);
        }
      }
      
      c.stroke();
      
      // Draw negative peaks
      c.beginPath();
      for(let i=0;i<W;i++){
        let min = 0;
        for(let j=0;j<step;j++) {
          min = Math.min(min, data[i*step+j]);
        }
        
        const minH = min * channelHeight * 0.45;
        
        if(i === 0) {
          c.moveTo(i, yOffset - minH);
        } else {
          c.lineTo(i, yOffset - minH);
        }
      }
      
      c.stroke();
      
      // Draw center line
      c.strokeStyle = "rgba(255, 255, 255, 0.2)";
      c.lineWidth = 1;
      c.setLineDash([5, 5]);
      c.beginPath();
      c.moveTo(0, yOffset);
      c.lineTo(W, yOffset);
      c.stroke();
      c.setLineDash([]);
    }
    
    // Draw channel separator if stereo
    if(numChannels > 1) {
      c.strokeStyle = "rgba(255, 255, 255, 0.1)";
      c.lineWidth = 1;
      c.beginPath();
      c.moveTo(0, AUDIO_H/2);
      c.lineTo(W, AUDIO_H/2);
      c.stroke();
    }
  };

  /* -------------- Export -------------- */
  const generate = () => {
    const fullH = H + (hasWave?AUDIO_H:0);
    const off = document.createElement("canvas"); off.width=W; off.height=fullH;
    const oc = off.getContext("2d");
    oc.drawImage(bgRef.current,0,0);
    oc.drawImage(inkRef.current,0,0);
    /* text */
    boxes.forEach(b=>{
      const el=document.getElementById(`tb-${b.id}`); if(!el) return;
      const pr=contRef.current.getBoundingClientRect();
      const r = el.getBoundingClientRect();
      const x=r.left-pr.left, y=r.top-pr.top+parseInt(el.style.fontSize||b.fs,10);
      oc.font=`${parseInt(el.style.fontSize||b.fs,10)}px Arial`; oc.fillStyle=b.color;
      oc.fillText(el.innerText,x,y);
    });
    if(hasWave) oc.drawImage(audRef.current,0,H);
    off.toBlob(blob=>onSubmit(new File([blob],"canvas.jpg",{type:"image/jpeg"})),"image/jpeg",0.92);
  };

  /* -------------- Clear all -------------- */
  const clearAll = () => {
    inkCtx().clearRect(0,0,W,H); audCtx().clearRect(0,0,W,AUDIO_H);
    setWave(false); audioFileRef.current=null; paintBg(null); setBg(null); imgRef.current=null;
    setBoxes([]); setSel(null);
  };

  const clearImage = () => {
    paintBg(null);
    setBg(null);
    imgRef.current = null;
  };

  const clearAudio = () => {
    audCtx().clearRect(0, 0, W, AUDIO_H);
    setWave(false);
    audioFileRef.current = null;
  };

  /* -------------- Handle font size changes -------------- */
const handleFontSizeChange = (boxId, newSize) => {
  setBoxes(bs => bs.map(x => x.id === boxId ? { ...x, fs: Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, newSize)) } : x));
};

  /* JSX -------------------------------------------------------------- */
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      {/* toolbar */}
      <div className="toolbar">
        <div className="toolbar-left">
          <div className="tool-group">
            <button className={`tool-btn ${mode === "move" ? "active" : ""}`} onClick={() => setMode("move")} title="Move/Select Tool">
              <Move size={20} />
            </button>

            <div className="tool-wrapper">
              <button className={`tool-btn ${mode === "pen" ? "active" : ""}`} onClick={() => setMode("pen")} title="Pen Tool">
                <Pencil size={20} />
              </button>
              {mode === "pen" && (
                <div className="tool-slider">
                  <input type="range" min="1" max="20" value={penSize} onChange={(e) => setPenSize(+e.target.value)} />
                </div>
              )}
            </div>

            <div className="tool-wrapper">
              <button className={`tool-btn ${mode === "erase" ? "active" : ""}`} onClick={() => setMode("erase")} title="Eraser Tool">
                <Eraser size={20} />
              </button>
              {mode === "erase" && (
                <div className="tool-slider">
                  <input type="range" min="1" max="20" value={eraserSize} onChange={(e) => setEraserSize(+e.target.value)} />
                </div>
              )}
            </div>

            <button className={`tool-btn ${mode === "text" ? "active" : ""}`} onClick={() => setMode("text")} title="Text Tool">
              <Type size={20} />
            </button>
          </div>

          <div className="divider" />

          <div className="tool-group">
            <button className="tool-btn" onClick={undo} title="Undo">
              <Undo2 size={20} />
            </button>
            <button className="tool-btn" onClick={redo} title="Redo">
              <Redo2 size={20} />
            </button>
          </div>

          <div className="divider" />

          <div style={{ position: "relative" }}>
            <button
              className="tool-btn"
              onClick={() => setShowTrashMenu(prev => !prev)}
              title="Clear…"
            >
              <Trash2 size={20} />
            </button>

            {showTrashMenu && (
              <div
                className="trash-menu"
                tabIndex={-1}
                onBlur={() => setShowTrashMenu(false)}
                style={{
                  position: "absolute",
                  top: "110%",
                  left: 0,
                  background: "rgba(30,30,40,0.95)",
                  border: "1px solid rgba(255,255,255,0.15)",
                  borderRadius: "6px",
                  padding: "6px 0",
                  minWidth: "140px",
                  zIndex: 50
                }}
              >
                <button
                  className="trash-item"
                  onClick={() => { clearAll(); setShowTrashMenu(false); }}
                >
                  Clear&nbsp;All
                </button>
                <button
                  className="trash-item"
                  onClick={() => { clearImage(); setShowTrashMenu(false); }}
                >
                  Clear&nbsp;Image
                </button>
                <button
                  className="trash-item"
                  onClick={() => { clearAudio(); setShowTrashMenu(false); }}
                >
                  Clear&nbsp;Audio
                </button>
              </div>
            )}
          </div>

          <div className="color-picker-wrapper" title="Choose Color">
            <input type="color" className="color-picker" value={color} onChange={(e) => setColor(e.target.value)} />
            <div className="color-preview">
              <Palette size={25} color="#ffffff" />
            </div>
          </div>
        </div>

        <div className="toolbar-right">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'white', fontSize: '16px' }}>
            Language:
            <select 
              value={language} 
              onChange={e => setLanguage(e.target.value)}
              style={{ 
                background: 'rgba(255, 255, 255, 0.1)', 
                border: '1px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '14px',
                color: 'white',
                outline: 'none'
              }}
            >
              <option value="en" style={{ background: '#333' }}>English</option>
              <option value="zh" style={{ background: '#333' }}>中文</option>
            </select>
          </label>
        </div>
      </div>

      {/* board shadow wrapper */}
      <div ref={contRef} className="board-container">
        {/* artboard (top) */}
        <div className="artboard" style={{ width: W, height: H }}>
          <canvas ref={bgRef} width={W} height={H} style={{ position: 'absolute' }} />
          <canvas
            ref={inkRef}
            width={W}
            height={H}
            className={`ink-canvas cursor-${mode}`}
            onMouseDown={startStroke}
            onMouseMove={drawMove}
            onMouseUp={endStroke}
            onMouseLeave={endStroke}
            onDrop={onBgDrop}
            onDragOver={(e) => e.preventDefault()}
          />
          
          {!bgSrc && showHint && (
            <div className="drop-zone">
              <div className="drop-text">
                Draw or do anything you like!
                <br />
                You can drop an image file here to set it as the background.
              </div>
            </div>
          )}

          {/* text boxes */}
          {boxes.map((b) => {
            const sel = selId === b.id;
            return (
              <div
                key={b.id}
                className={`textbox-container ${mode === "pen" || mode === "erase" ? "no-pointer" : ""}`}
                data-x={b.x}
                data-y={b.y}
                onMouseDown={(ev) => {
                  if (b.editing || mode !== "move") return;
                  const pr = contRef.current.getBoundingClientRect();
                  dragRef.current = {
                    id: b.id,
                    dx: b.x - (ev.clientX - pr.left),
                    dy: b.y - (ev.clientY - pr.top),
                    width: b.width ?? 200,
                    height: b.height ?? 50
                  };
                }}
              >
                {sel && (
                  <div className="size-toolbar">
                    <button
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => handleFontSizeChange(b.id, b.fs - 2)}
                    >
                      A-
                    </button>
                    <input
                      type="text"
                      className="font-size-input"
                      value={b.tempFs !== undefined ? b.tempFs : b.fs}
                      onChange={(e) => {
                        setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, tempFs: e.target.value } : x));
                      }}
                      onKeyDown={(e) => {
                        e.stopPropagation();
                        if (e.key === 'Enter') {
                          const val = parseInt(e.target.value);
                          if (!isNaN(val) && val >= MIN_FONT_SIZE && val <= MAX_FONT_SIZE) {
                            setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, fs: val, tempFs: undefined } : x));
                          } else {
                            setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, tempFs: undefined } : x));
                          }
                          e.target.blur();
                        }
                        if (e.key === 'Escape') {
                          setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, tempFs: undefined } : x));
                          e.target.blur();
                        }
                      }}
                      onFocus={(e) => {
                        e.stopPropagation();
                        e.target.select();
                      }}
                      onBlur={(e) => {
                        const val = parseInt(e.target.value);
                        if (!isNaN(val) && val >= MIN_FONT_SIZE && val <= MAX_FONT_SIZE) {
                          setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, fs: val, tempFs: undefined } : x));
                        } else {
                          setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, tempFs: undefined } : x));
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      onMouseDown={(e) => e.stopPropagation()}
                    />
                    <button
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => handleFontSizeChange(b.id, b.fs + 2)}
                    >
                      A+
                    </button>
                  </div>
                )}

                {/* Resize handle - bottom right for reshaping textbox dimensions */}
                {sel && (
                  <div
                    className="resize-handle"
                    onMouseDown={(ev) => {
                      ev.preventDefault();
                      ev.stopPropagation();
                      const startX = ev.clientX;
                      const startY = ev.clientY;
                      const textboxEl = document.getElementById(`tb-${b.id}`);
                      const currentWidth = b.width || (textboxEl ? textboxEl.offsetWidth : 100);
                      const currentHeight = b.height || (textboxEl ? textboxEl.offsetHeight : 30);
                      
                      const handleResize = (e) => {
                        const deltaX = e.clientX - startX;
                        const deltaY = e.clientY - startY;
                        const maxWidth = W - b.x;
                        const maxHeight = H - b.y;

                        const newWidth = Math.max(50, Math.min(maxWidth, currentWidth + deltaX));
                        const newHeight = Math.max(20, Math.min(maxHeight, currentHeight + deltaY));
                        
                        setBoxes(bs => bs.map(x => x.id === b.id ? { 
                          ...x, 
                          width: newWidth,
                          height: newHeight
                        } : x));
                      };
                      
                      const handleMouseUp = () => {
                        document.removeEventListener('mousemove', handleResize);
                        document.removeEventListener('mouseup', handleMouseUp);
                      };
                      
                      document.addEventListener('mousemove', handleResize);
                      document.addEventListener('mouseup', handleMouseUp);
                    }}
                  >
                    ⤡
                  </div>
                )}

                <div
                  id={`tb-${b.id}`}
                  className={`textbox ${sel ? "active" : ""} ${b.editing ? "editing" : ""} ${mode === "pen" || mode === "erase" ? "no-pointer" : ""}`}
                  contentEditable={b.editing}
                  suppressContentEditableWarning
                  data-font-size={b.fs}
                  data-color={b.color}
                  data-width={b.width}
                  data-height={b.height}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (mode === "move" && !sel) setSel(b.id);
                  }}
                  onDoubleClick={(e) => {
                    e.stopPropagation();
                    setBoxes(bs => bs.map(x => x.id === b.id ? { ...x, editing: true } : x));
                    setTimeout(() => {
                      const el = document.getElementById(`tb-${b.id}`);
                      if (el) {
                        el.focus();
                        const range = document.createRange();
                        range.selectNodeContents(el);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                      }
                    }, 10);
                  }}
                  onBlur={(e) => {
                    const textContent = e.target.innerText.trim();

                    if (!textContent) {
                      setBoxes(bs => bs.filter(x => x.id !== b.id));
                      setSel(null);
                    } else {
                      const rect = e.target.getBoundingClientRect();
                      setBoxes(bs => bs.map(x => x.id === b.id ? {
                        ...x,
                        editing: false,
                        width: Math.max(50, Math.ceil(rect.width)),
                        height: Math.max(20, Math.ceil(rect.height)),
                        text: textContent
                      } : x));
                    }

                  }}
                  onInput={(e) => {
                    const el = e.target;
                    const newWidth = Math.ceil(el.scrollWidth);
                    const newHeight = Math.ceil(el.scrollHeight);

                    setBoxes(bs => bs.map(x =>
                      x.id === b.id
                        ? {
                            ...x,
                            width: Math.min(W - x.x, Math.max(x.width || 0, newWidth)),
                            height: Math.min(H - x.y, Math.max(x.height || 0, newHeight))
                          }
                        : x
                    ));
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') e.target.blur();
                    if (b.editing) e.stopPropagation();
                  }}
                >
                  {b.text}
                </div>
              </div>
            );
          })}
        </div>

        {/* waveform strip (bottom) */}
        <div style={{ position: 'relative', width: W, height: AUDIO_H }}>
          <canvas
            ref={audRef}
            className="wave-strip"
            width={W}
            height={AUDIO_H}
            onDrop={onAudDrop}
            onDragOver={(e) => e.preventDefault()}
          />
          {!hasWave && (
            <div className="wave-drop-hint">Drop an audio file (WAV, MP3, etc.) to include it in the final canvas.</div>
          )}
        </div>
      </div>
    </div>
  );
});

export default EditorCanvas;