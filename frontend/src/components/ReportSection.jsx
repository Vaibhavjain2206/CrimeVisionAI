import React from "react";
import Panel from "./Panel.jsx";

export default function ReportSection({ report, onGenerate, onDownload, busy, disabled, error }) {
  return (
    <Panel eyebrow="CASE DOCUMENTATION" title="Forensic report" className="report-panel">
      <div className="report-row">
        <div className="report-symbol" aria-hidden="true">PDF</div>
        <div className="report-copy">
          <strong>Evidence analysis report</strong>
          <span>Includes deterministic findings, timeline, reasoning, and cautions.</span>
        </div>
        {report && <span className="report-status"><i /> GENERATED</span>}
      </div>
      {error && <p className="inline-note error-text">{error}</p>}
      {report && <div className="report-id"><span>REPORT ID</span><code>{report.report_id}</code><small>{report.filename}</small></div>}
      <div className="report-actions">
        <button className="button button-secondary" type="button" disabled={busy || disabled} onClick={onGenerate}>
          {busy ? <><span className="spinner" /> Generating…</> : report ? "Generate new report" : "Generate forensic PDF report"}
        </button>
        {report && <button className="button button-primary" type="button" onClick={onDownload}>
          Download PDF report <span aria-hidden="true">↓</span>
        </button>}
      </div>
    </Panel>
  );
}
