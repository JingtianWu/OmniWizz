import React, { useState } from "react";
import UploadCanvas from "./components/UploadCanvas";
import AudioPlayer from "./components/AudioPlayer";
import "./index.css";

export default function App() {
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading]   = useState(false);

  async function handleFile(file) {
    if (!file) return;
    setLoading(true);
    const data = new FormData();
    data.append("file", file);

    try {
      const r = await fetch("/generate", { method: "POST", body: data });
      const j = await r.json();
      setAudioUrl(j.audio_url);
    } catch (err) {
      alert("Upload failed");
      console.error(err);
    }
    setLoading(false);
  }

  return (
    <div className="app-center">
      {loading
        ? <div>Generating&nbsp;music…</div>
        : audioUrl
          ? <AudioPlayer src={audioUrl} />
          : <UploadCanvas onDrop={handleFile} />
      }
    </div>
  );
}
