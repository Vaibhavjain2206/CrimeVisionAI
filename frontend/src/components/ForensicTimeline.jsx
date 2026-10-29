import React from "react";
import Panel from "./Panel.jsx";
import { formatConfidence, observationText } from "../utils/presentation.js";

export default function ForensicTimeline({ result }) {
  if (!result) return null;
  const timeline = result.forensic_timeline || [];
  return (
    <Panel eyebrow="CHRONOLOGICAL RECORD · SERVICE ORDER" title="Forensic timeline" aside={<span className="count-chip">{timeline.length} events</span>}>
      {timeline.length === 0 ? <p className="empty-state">No timeline events were returned.</p> : (
        <ol className="timeline-list">
          {timeline.map((event, index) => (
            <li className="timeline-item" key={event.evidence_id || `${event.evidence_type}-${index}`}>
              <span className="timeline-node" />
              <div className="timeline-time">{event.timestamp ?? "Timestamp not supplied"}</div>
              <div className="timeline-content">
                <div className="evidence-tags"><span>{event.evidence_type}</span><span>{event.modality}</span></div>
                <p>{observationText(event.observation)}</p>
                <span className="small-muted">Confidence: {formatConfidence(event.confidence)}{event.evidence_id ? ` · ${event.evidence_id}` : ""}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}
