import React, { useCallback, useEffect, useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import EvidenceUploader from "./components/EvidenceUploader.jsx";
import AnalysisProgress from "./components/AnalysisProgress.jsx";
import DetectionResults from "./components/DetectionResults.jsx";
import SceneAnalysis from "./components/SceneAnalysis.jsx";
import AudioTranscription from "./components/AudioTranscription.jsx";
import VideoResults from "./components/VideoResults.jsx";
import EvidenceFusion from "./components/EvidenceFusion.jsx";
import ForensicTimeline from "./components/ForensicTimeline.jsx";
import AIReasoning from "./components/AIReasoning.jsx";
import ReportSection from "./components/ReportSection.jsx";
import {
  analyzeAudio,
  analyzeImage,
  analyzeScene,
  analyzeVideo,
  checkHealth,
  downloadReport,
  fuseEvidence,
  generateReport,
  getEvidenceType,
  reasonOverEvidence,
  uploadEvidence,
} from "./services/api.js";

const INITIAL_STEPS = { upload: "idle", analysis: "idle", fusion: "idle", reasoning: "idle", report: "idle" };

function Sidebar({ backendOnline, evidence, summary }) {
  const stats = [
    ["Evidence items", summary?.evidence_count ?? "—"],
    ["Timestamped", summary?.timestamped_count ?? "—"],
    ["Detected objects", summary?.object_detection_count ?? "—"],
  ];
  return (
    <aside className="sidebar">
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Dashboard sections">
        <a className="nav-link active" href="#overview"><span>⌂</span>Overview</a>
        <a className="nav-link" href="#intake"><span>＋</span>Evidence intake</a>
        <a className="nav-link" href="#findings"><span>◈</span>Analysis findings</a>
        <a className="nav-link" href="#timeline"><span>↕</span>Forensic timeline</a>
        <a className="nav-link" href="#report"><span>▤</span>Reports</a>
      </nav>
      <div className="sidebar-divider" />
      <div className="sidebar-label">CASE SNAPSHOT</div>
      {evidence ? (
        <div className="case-snapshot">
          <span className="case-indicator">ACTIVE EVIDENCE</span>
          <strong title={evidence.original_filename}>{evidence.original_filename}</strong>
          <small>{evidence.file_type} · {evidence.extension}</small>
          {stats.map(([label, value]) => <div className="snapshot-stat" key={label}><span>{label}</span><b>{value}</b></div>)}
        </div>
      ) : <p className="sidebar-empty">Upload evidence to create a case analysis snapshot.</p>}
      <div className="sidebar-footer">
        <span className={`mini-status ${backendOnline ? "online" : "offline"}`} />
        <span>{backendOnline ? "Flask analysis service" : "Flask service unavailable"}</span>
      </div>
    </aside>
  );
}

function initialWorkflowError(error) {
  if (error.status === 413) return "The evidence file exceeds the 100 MiB upload limit.";
  if (error.status === 503) return "An AI service is unavailable. Check the backend configuration and try again.";
  if (error.status === 504) return "The AI analysis timed out. You can retry the analysis.";
  if (error.status >= 500) return "The analysis service could not complete this request. Please try again.";
  if (error instanceof TypeError) return "Could not reach the Flask service. Check that the backend is running.";

  const message = typeof error.message === "string" ? error.message : "";
  const mayContainInternalDetails = /traceback|exception|[A-Z]:[\\/]|\/(?:home|Users|tmp)\/|GROQ_API_KEY\s*[:=]|Bearer\s+\S+/i.test(message);
  return message && !mayContainInternalDetails
    ? message
    : "The request could not be completed. Please review the input and try again.";
}

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [file, setFile] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [steps, setSteps] = useState(INITIAL_STEPS);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [fusion, setFusion] = useState(null);
  const [reasoning, setReasoning] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [reportError, setReportError] = useState("");

  useEffect(() => {
    let mounted = true;
    checkHealth()
      .then(() => mounted && setBackendOnline(true))
      .catch(() => mounted && setBackendOnline(false));
    return () => { mounted = false; };
  }, []);

  const updateStep = useCallback((key, status) => {
    setSteps((current) => ({ ...current, [key]: status }));
  }, []);

  const handleFileChange = useCallback((nextFile) => {
    setFile(nextFile);
    setEvidence(null);
    setAnalysis(null);
    setFusion(null);
    setReasoning(null);
    setReport(null);
    setError("");
    setReportError("");
    setSteps(INITIAL_STEPS);
  }, []);

  const runWorkflow = useCallback(async () => {
    if (!file) {
      setError("Choose an evidence file before starting analysis.");
      return;
    }
    const evidenceType = getEvidenceType(file);
    if (!evidenceType) {
      setError("This file extension is not supported by the evidence upload API.");
      return;
    }
    if (file.size === 0) {
      setError("The selected file is empty.");
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setError("The selected file exceeds the 100 MiB upload limit.");
      return;
    }

    setWorkflowBusy(true);
    setError("");
    setAnalysis(null);
    setFusion(null);
    setReasoning(null);
    setReport(null);
    setReportError("");
    setSteps(INITIAL_STEPS);
    let activeStep = "upload";
    try {
      updateStep(activeStep, "active");
      const uploaded = await uploadEvidence(file);
      setEvidence(uploaded.evidence);
      updateStep(activeStep, "done");

      if (evidenceType === "document") {
        setError("PDF evidence was uploaded successfully. The current analysis APIs support image, audio, and video evidence only.");
        return;
      }

      activeStep = "analysis";
      updateStep(activeStep, "active");
      let apiResults;
      let displayResults;
      if (evidenceType === "image") {
        const [imageResult, sceneResult] = await Promise.all([
          analyzeImage(file),
          analyzeScene(file),
        ]);
        apiResults = { image_analysis: imageResult, scene_analysis: sceneResult };
        displayResults = { image: imageResult.analysis, scene: sceneResult.analysis };
      } else if (evidenceType === "audio") {
        const audioResult = await analyzeAudio(file);
        apiResults = { audio_analysis: audioResult };
        displayResults = { audio: audioResult.analysis };
      } else {
        const videoResult = await analyzeVideo(file);
        apiResults = { video_analysis: videoResult };
        displayResults = { video: videoResult.analysis };
      }
      setAnalysis(displayResults);
      updateStep(activeStep, "done");

      activeStep = "fusion";
      updateStep(activeStep, "active");
      const fusionResult = await fuseEvidence(apiResults);
      setFusion(fusionResult);
      updateStep(activeStep, "done");

      activeStep = "reasoning";
      updateStep(activeStep, "active");
      const reasoningResult = await reasonOverEvidence(fusionResult);
      setReasoning(reasoningResult.reasoning);
      updateStep(activeStep, "done");
    } catch (requestError) {
      updateStep(activeStep, "error");
      setError(initialWorkflowError(requestError));
    } finally {
      setWorkflowBusy(false);
    }
  }, [file, updateStep]);

  const createReport = useCallback(async () => {
    if (!fusion || !reasoning) return;
    setReportBusy(true);
    setReportError("");
    updateStep("report", "active");
    try {
      const result = await generateReport(fusion, reasoning);
      setReport(result);
      updateStep("report", "done");
    } catch (requestError) {
      updateStep("report", "error");
      setReportError(initialWorkflowError(requestError));
    } finally {
      setReportBusy(false);
    }
  }, [fusion, reasoning, updateStep]);

  const summary = fusion?.summary;
  const canReport = useMemo(() => Boolean(fusion && reasoning && !workflowBusy), [fusion, reasoning, workflowBusy]);

  async function handleDownload() {
    try {
      await downloadReport(report?.report_path, report?.filename);
      setReportError("");
    } catch (downloadError) {
      setReportError(`Report download failed: ${initialWorkflowError(downloadError)}`);
    }
  }

  return (
    <div className="app-shell" id="top">
      <Header backendOnline={backendOnline} />
      <div className="workspace-layout">
        <Sidebar backendOnline={backendOnline} evidence={evidence} summary={summary} />
        <main className="main-content">
          <section className="page-heading" id="overview">
            <div>
              <p className="eyebrow">INVESTIGATOR CONSOLE <span className="heading-separator">/</span> MULTIMODAL ANALYSIS</p>
              <h1>Intelligent Multimodal<br /><span>Forensic Analysis Platform</span></h1>
              <p className="page-intro">Review submitted evidence through transparent AI-assisted analysis and deterministic evidence fusion.</p>
            </div>
            <div className="heading-mark"><span>CV</span><i>FORENSIC<br />WORKSPACE</i></div>
          </section>

          <section className="intake-grid" id="intake">
            <EvidenceUploader file={file} onFileChange={handleFileChange} onSubmit={runWorkflow} busy={workflowBusy} backendOnline={backendOnline} />
            <AnalysisProgress steps={steps} />
          </section>

          {error && <div className={`${evidence && getEvidenceType(file) === "document" ? "notice-info" : "notice-error"}`} role="alert"><span>{evidence && getEvidenceType(file) === "document" ? "ⓘ" : "!"}</span>{error}</div>}

          {evidence && <section className="intake-receipt" aria-label="Uploaded evidence record">
            <span className="receipt-check">✓</span>
            <div><span className="field-label">EVIDENCE INGESTED · {evidence.id}</span><strong>{evidence.original_filename}</strong></div>
            <small>{evidence.file_type} · {evidence.size} bytes</small>
          </section>}

          <div className="results-heading" id="findings">
            <div><p className="eyebrow">ANALYSIS OUTPUT</p><h2>Evidence findings</h2></div>
            {fusion && <span className="results-source">SOURCE · FLASK ANALYSIS SERVICES</span>}
          </div>

          {analysis?.image && <div className="findings-grid">
            <DetectionResults detections={analysis.image.detections || []} />
            <SceneAnalysis result={analysis.scene} />
          </div>}
          {analysis?.audio && <AudioTranscription result={analysis.audio} />}
          {analysis?.video && <VideoResults result={analysis.video} />}
          {fusion && <EvidenceFusion result={fusion} />}
          {fusion && <div id="timeline"><ForensicTimeline result={fusion} /></div>}
          {reasoning && <AIReasoning result={reasoning} />}
          {fusion && !reasoning && <div className="notice-info" role="status">Deterministic evidence is ready. AI reasoning is unavailable; review the evidence above.</div>}
          {fusion && <div id="report"><ReportSection report={report} onGenerate={createReport} onDownload={handleDownload} busy={reportBusy} disabled={!canReport} error={reportError} /></div>}

          <footer className="app-footer"><span>CRIMEVISION AI · ANALYTICAL DECISION SUPPORT</span><span>Evidence remains subject to investigator review.</span></footer>
        </main>
      </div>
    </div>
  );
}
