import React from "react";
import Panel from "./Panel.jsx";
import { formatConfidence } from "../utils/presentation.js";

export default function SceneAnalysis({ result }) {
  if (!result) return null;
  const predictions = result.top_predictions || [];
  return (
    <Panel eyebrow="CLIP · SCENE CLASSIFICATION" title="Scene analysis">
      <p className="panel-note">Predicted scene category from CLIP. The result is a model classification and requires review.</p>
      <div className="scene-feature">
        <div>
          <span className="field-label">PREDICTED CATEGORY</span>
          <strong>{result.scene ?? "—"}</strong>
        </div>
        <div className="scene-confidence">
          <span className="field-label">CONFIDENCE</span>
          <strong>{formatConfidence(result.confidence)}</strong>
        </div>
      </div>
      {predictions.length > 0 && <div className="prediction-list">
        <p className="field-label">RANKED PREDICTIONS</p>
        {predictions.map((prediction, index) => (
          <div className="prediction-row" key={`${prediction.category}-${index}`}>
            <span><b>{String(index + 1).padStart(2, "0")}</b>{prediction.category}</span>
            <strong>{formatConfidence(prediction.confidence)}</strong>
          </div>
        ))}
      </div>}
    </Panel>
  );
}
