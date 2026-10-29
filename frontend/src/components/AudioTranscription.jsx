import React from "react";
import Panel from "./Panel.jsx";

export default function AudioTranscription({ result }) {
  if (!result) return null;
  return (
    <Panel eyebrow="WHISPER · SPEECH TRANSCRIPTION" title="Audio findings" aside={result.language && <span className="count-chip">LANG · {result.language}</span>}>
      <span className="field-label">TRANSCRIPTION</span>
      <blockquote className="transcription-text">{result.transcription || "No transcription text was returned."}</blockquote>
      <p className="small-muted">Source file: {result.audio}</p>
    </Panel>
  );
}
