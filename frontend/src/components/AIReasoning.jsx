import React from "react";
import Panel from "./Panel.jsx";

const REASONING_SECTIONS = [
  ["key_observations", "Key observations"],
  ["evidence_assessment", "Evidence assessment"],
  ["uncertainties", "Uncertainties"],
  ["recommended_investigator_checks", "Recommended investigator checks"],
];

function ReasoningList({ items }) {
  if (!Array.isArray(items) || items.length === 0) return <p className="small-muted">No entries returned.</p>;
  return <ul className="reasoning-list">{items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul>;
}

export default function AIReasoning({ result }) {
  if (!result) return null;
  return (
    <Panel eyebrow="GROQ · INTERPRETATION LAYER" title="AI evidence reasoning" className="reasoning-panel">
      <div className="reasoning-boundary"><span aria-hidden="true">✳</span>Interpretation only · deterministic evidence remains unchanged</div>
      <div className="reasoning-summary">
        <span className="field-label">CASE SUMMARY</span>
        <p>{result.case_summary || "No case summary returned."}</p>
      </div>
      <div className="reasoning-grid">
        {REASONING_SECTIONS.map(([key, title]) => (
          <section className="reasoning-block" key={key}>
            <h3>{title}</h3>
            <ReasoningList items={result[key]} />
          </section>
        ))}
      </div>
      <div className="reasoning-summary timeline-reading">
        <span className="field-label">TIMELINE INTERPRETATION</span>
        <p>{result.timeline_interpretation || "No timeline interpretation returned."}</p>
      </div>
      <p className="disclaimer">AI reasoning is evidence-grounded assistance and does not determine guilt or make definitive criminal accusations.</p>
    </Panel>
  );
}
