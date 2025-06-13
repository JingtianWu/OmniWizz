import React from "react";

export default function AudioPlayer({ src }) {
  return (
    <audio controls autoPlay src={src} className="w-96" />
  );
}
