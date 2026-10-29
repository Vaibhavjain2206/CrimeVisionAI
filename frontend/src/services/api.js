const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

const supportedTypes = {
  png: "image",
  jpg: "image",
  jpeg: "image",
  webp: "image",
  mp4: "video",
  avi: "video",
  mov: "video",
  mkv: "video",
  mp3: "audio",
  wav: "audio",
  m4a: "audio",
  aac: "audio",
  pdf: "document",
};

export function getEvidenceType(file) {
  const extension = file?.name?.split(".").pop()?.toLowerCase();
  return supportedTypes[extension] || null;
}

async function readResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    const error = new Error(
      payload.message || payload.error || `Request failed (${response.status})`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

async function postFile(path, file) {
  const body = new FormData();
  body.append("file", file);
  return readResponse(
    await fetch(`${API_BASE_URL}${path}`, { method: "POST", body }),
  );
}

async function postJson(path, payload) {
  return readResponse(
    await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function checkHealth() {
  return readResponse(await fetch(`${API_BASE_URL}/health`));
}

export function uploadEvidence(file) {
  return postFile("/upload", file);
}

export function analyzeImage(file) {
  return postFile("/analyze/image", file);
}

export function analyzeScene(file) {
  return postFile("/analyze/scene", file);
}

export function analyzeAudio(file) {
  return postFile("/analyze/audio", file);
}

export function analyzeVideo(file) {
  return postFile("/analyze/video", file);
}

export function fuseEvidence(results) {
  return postJson("/analyze/fusion", results);
}

export function reasonOverEvidence(fusionResult) {
  return postJson("/analyze/reason", fusionResult);
}

export function generateReport(fusionResult, reasoningResult) {
  return postJson("/report/generate", {
    fusion: fusionResult,
    reasoning: reasoningResult,
  });
}

export async function downloadReport(reportPath, filename) {
  if (!reportPath) throw new Error("The backend did not return a report download path.");
  const apiOrigin = new URL(API_BASE_URL, window.location.origin).origin;
  const response = await fetch(new URL(reportPath, apiOrigin));
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.message || `Download failed (${response.status})`);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || "forensic-report.pdf";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
