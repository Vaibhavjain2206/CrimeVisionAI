import React from "react";
import Panel from "./Panel.jsx";
import { formatConfidence, observationText } from "../utils/presentation.js";

export default function EvidenceFusion({ result }) {
  if (!result) return null;
  const evidence = result.normalized_evidence || [];
  return (
    <Panel
      eyebrow="MILESTONE 7 · DETERMINISTIC SOURCE OF TRUTH"
      title="Deterministic evidence"
      aside={<span className="count-chip">{evidence.length} evidence items</span>}
      className="fusion-panel"
    >
      <p className="panel-note">Normalized evidence from the Flask fusion service. AI reasoning is displayed separately and does not modify these records.</p>
      {evidence.length === 0 ? <p className="empty-state">The fusion service returned no normalized evidence items.</p> : (
        <div className="evidence-list">
          {evidence.map((item, index) => (
            <article className="evidence-row" key={item.evidence_id || `${item.evidence_type}-${index}`}>
              <span className="evidence-index">{String(index + 1).padStart(2, "0")}</span>
              <div className="evidence-main">
                <div className="evidence-tags"><span>{item.evidence_type}</span><span>{item.modality}</span></div>
                <strong>{observationText(item.observation)}</strong>
                {item.source_filename && <small>{item.source_filename}</small>}
              </div>
              <div className="evidence-meta">
                <span className="field-label">TIMESTAMP</span>
                <strong>{item.timestamp ?? "—"}</strong>
                <span className="field-label">CONFIDENCE</span>
                <strong>{formatConfidence(item.confidence)}</strong>
              </div>
              {item.evidence_id && <span className="evidence-id">ID · {item.evidence_id}</span>}
              {item.metadata && Object.keys(item.metadata).length > 0 && (
                <details className="metadata-details">
                  <summary>Evidence metadata</summary>
                  <pre>{JSON.stringify(item.metadata, null, 2)}</pre>
                </details>
              )}
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}
