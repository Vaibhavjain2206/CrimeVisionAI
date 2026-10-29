import React from "react";
import Panel from "./Panel.jsx";
import { formatConfidence } from "../utils/presentation.js";

export default function VideoResults({ result }) {
  if (!result) return null;
  const metadata = result.metadata || {};
  const frames = result.sampled_frames || [];
  return (
    <Panel eyebrow="OPENCV · SAMPLED FRAME ANALYSIS" title="Video findings" aside={<span className="count-chip">{frames.length} sampled frames</span>}>
      <div className="video-metadata">
        {[["FPS", metadata.fps], ["FRAME COUNT", metadata.frame_count], ["DURATION", metadata.duration_seconds], ["FRAME SIZE", metadata.width && metadata.height ? `${metadata.width} × ${metadata.height}` : null]].map(([label, value]) => (
          <div key={label}><span className="field-label">{label}</span><strong>{value ?? "—"}</strong></div>
        ))}
      </div>
      {frames.length === 0 ? <p className="empty-state">No sampled frames were returned.</p> : (
        <div className="frame-list">
          {frames.map((frame, index) => (
            <article className="frame-card" key={`${frame.frame_number}-${index}`}>
              <div className="frame-heading">
                <strong>Frame {frame.frame_number}</strong>
                <span>{frame.timestamp_seconds != null ? `${frame.timestamp_seconds} sec` : "Timestamp unavailable"}</span>
              </div>
              {frame.frame_info && <p className="frame-info">{frame.frame_info.width} × {frame.frame_info.height}{frame.frame_info.channels != null ? ` · ${frame.frame_info.channels} channel(s)` : ""}</p>}
              {Array.isArray(frame.detections) && frame.detections.map((detection, detectionIndex) => (
                <div className="frame-detection" key={`${detection.label}-${detectionIndex}`}>
                  <span>{detection.label}</span><strong>Model prediction · {formatConfidence(detection.confidence)}</strong>
                </div>
              ))}
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}
