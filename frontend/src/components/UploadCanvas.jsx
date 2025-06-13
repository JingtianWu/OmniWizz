import React, { useState, useEffect } from "react";

export default function UploadCanvas({ onDrop }) {
  const [dragging, setDragging] = useState(false);

  /* prevent browser from opening file */
  useEffect(() => {
    const stop = e => { e.preventDefault(); e.stopPropagation(); };
    ["dragenter","dragover","dragleave","drop"].forEach(ev =>
      window.addEventListener(ev, stop, false)
    );
    return () => {
      ["dragenter","dragover","dragleave","drop"].forEach(ev =>
        window.removeEventListener(ev, stop, false)
      );
    };
  }, []);

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onDrop(file);
  }

  return (
    <div
      className={`drop-box${dragging ? " drag" : ""}`}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      Drop your image here
    </div>
  );
}
