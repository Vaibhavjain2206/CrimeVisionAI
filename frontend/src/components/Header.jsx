import React from "react";

export default function Header({ backendOnline }) {
  return (
    <header className="topbar">
      <a className="brand" href="#top" aria-label="CrimeVision AI home">
        <span className="brand-mark" aria-hidden="true">CV</span>
        <span className="brand-copy">
          <strong>CRIMEVISION <span>AI</span></strong>
          <small>FORENSIC INTELLIGENCE WORKSPACE</small>
        </span>
      </a>
      <div className="topbar-right">
        <span className="header-meta">MULTIMODAL EVIDENCE ANALYSIS</span>
        <span className={`system-status ${backendOnline ? "is-online" : "is-offline"}`}>
          <i aria-hidden="true" /> {backendOnline ? "SYSTEM ONLINE" : "BACKEND OFFLINE"}
        </span>
      </div>
    </header>
  );
}
