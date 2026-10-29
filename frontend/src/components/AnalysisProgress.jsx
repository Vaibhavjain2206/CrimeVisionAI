import React from "react";
import Panel from "./Panel.jsx";

const STEPS = [
  ["upload", "Evidence Upload", "01"],
  ["analysis", "AI Analysis", "02"],
  ["fusion", "Evidence Fusion", "03"],
  ["reasoning", "AI Reasoning", "04"],
  ["report", "Forensic Report", "05"],
];

export default function AnalysisProgress({ steps }) {
  return (
    <Panel eyebrow="ANALYSIS PIPELINE" title="Workflow status" className="progress-panel">
      <ol className="workflow-list">
        {STEPS.map(([key, label, number], index) => {
          const status = steps[key] || "idle";
          return (
            <li className={`workflow-step step-${status}`} key={key}>
              <span className="step-marker">{status === "done" ? "✓" : number}</span>
              <div className="step-copy">
                <strong>{label}</strong>
                <span>{status === "done" ? "Complete" : status === "active" ? "Processing" : status === "error" ? "Failed · needs attention" : "Waiting"}</span>
              </div>
              {index < STEPS.length - 1 && <span className="step-connector" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}
