import React, { useRef, useState } from "react";
import { getEvidenceType } from "../services/api.js";
import Panel from "./Panel.jsx";

const ACCEPTED = ".png,.jpg,.jpeg,.webp,.mp4,.avi,.mov,.mkv,.mp3,.wav,.m4a,.aac,.pdf";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function EvidenceUploader({ file, onFileChange, onSubmit, busy, backendOnline }) {
  const inputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const evidenceType = getEvidenceType(file);

  const acceptFile = (candidate) => {
    if (candidate) onFileChange(candidate);
  };

  return (
    <Panel
      eyebrow="CASE INTAKE / 01"
      title="Evidence upload"
      aside={<span className="small-muted">MAX FILE SIZE · 100 MB</span>}
      className="upload-panel"
    >
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept={ACCEPTED}
        onChange={(event) => acceptFile(event.target.files?.[0])}
      />
      <div
        className={`dropzone ${dragActive ? "dropzone-active" : ""} ${file ? "has-file" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setDragActive(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          acceptFile(event.dataTransfer.files?.[0]);
        }}
      >
        <button
          type="button"
          className="dropzone-trigger"
          onClick={() => inputRef.current?.click()}
          aria-label="Choose evidence file or drop it here"
        >
          <span className="upload-icon" aria-hidden="true">↑</span>
          <span className="dropzone-title">{file ? "Evidence selected" : "Drop evidence to begin"}</span>
          <span className="dropzone-subtitle">or <u>browse files</u> from your device</span>
        </button>
      </div>

      <div className="accepted-formats">
        <span>SUPPORTED FORMATS</span>
        <p>PNG · JPG · JPEG · WEBP &nbsp;/&nbsp; MP4 · AVI · MOV · MKV &nbsp;/&nbsp; MP3 · WAV · M4A · AAC · PDF</p>
      </div>

      {file && (
        <div className="selected-file">
          <div className="file-type-icon">{evidenceType === "image" ? "IMG" : evidenceType === "video" ? "VID" : evidenceType === "audio" ? "AUD" : "DOC"}</div>
          <div className="file-details">
            <strong title={file.name}>{file.name}</strong>
            <span>{evidenceType || "Unsupported type"} <i>·</i> {formatSize(file.size)}</span>
          </div>
          <button type="button" className="icon-button" onClick={() => onFileChange(null)} aria-label="Remove selected file">×</button>
        </div>
      )}

      <button
        className="button button-primary upload-action"
        type="button"
        disabled={!file || busy || !backendOnline}
        onClick={onSubmit}
      >
        {busy ? <><span className="spinner" /> Processing evidence…</> : "Upload & analyze evidence"}
        {!busy && <span aria-hidden="true">↗</span>}
      </button>
      {!backendOnline && <p className="inline-note warning-text">Connect to the Flask API at the configured address to begin analysis.</p>}
    </Panel>
  );
}
