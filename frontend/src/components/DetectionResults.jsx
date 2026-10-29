import React from "react";
import Panel from "./Panel.jsx";
import { formatConfidence } from "../utils/presentation.js";

export default function DetectionResults({ detections = [] }) {
  return (
    <Panel eyebrow="RT-DETR · OBJECT DETECTION" title="Detected objects" aside={<span className="count-chip">{detections.length} predictions</span>}>
      <p className="panel-note">Model predictions for investigator review. Confidence scores are probabilistic, not certainty measures.</p>
      {detections.length === 0 ? (
        <p className="empty-state">The model returned no detections for this image.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Predicted label</th><th>Confidence</th><th>Bounding box (px)</th></tr></thead>
            <tbody>{detections.map((item, index) => (
              <tr key={`${item.label}-${index}`}>
                <td><span className="object-dot" />{item.label}</td>
                <td>{formatConfidence(item.confidence)}</td>
                <td className="mono">{item.bbox ? `x1 ${item.bbox.x1}, y1 ${item.bbox.y1} · x2 ${item.bbox.x2}, y2 ${item.bbox.y2}` : "Not provided"}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
