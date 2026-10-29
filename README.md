# CrimeVision AI

CrimeVision AI is an intelligent multimodal forensic analysis and decision-support platform. It accepts image, video, audio, and PDF evidence, runs pretrained analysis models through a Flask API, fuses returned observations deterministically, and presents the results in a React dashboard with an optional Groq reasoning step and PDF report.

It assists investigators; model output is probabilistic and must be reviewed. It does not determine guilt or make definitive criminal accusations.

## Features

- Evidence upload for PNG, JPG/JPEG, WEBP, MP4, AVI, MOV, MKV, MP3, WAV, M4A, AAC, and PDF.
- RT-DETR object detection for supported images and sampled video frames.
- CLIP scene classification with ranked candidate labels.
- OpenAI Whisper transcription for supported audio.
- OpenCV video metadata extraction and configurable frame sampling.
- Deterministic normalization and chronological forensic timeline.
- Optional Groq evidence-grounded reasoning over the deterministic fusion result.
- ReportLab PDF reports and report download endpoint.
- React + Vite investigator dashboard.

## Architecture

```text
React dashboard → Flask REST API → analysis services
                               ├→ RT-DETR / CLIP / Whisper / OpenCV
                               ├→ deterministic evidence fusion + timeline
                               ├→ Groq reasoning (optional interpretation)
                               └→ ReportLab PDF generation
```

The Flask backend owns all AI analysis. The frontend sends evidence to the existing API and presents its returned data. Groq reasoning is shown separately from deterministic evidence and does not modify it. See [docs/architecture.md](docs/architecture.md) for the data flow and security boundaries.

## Project Structure

```text
CrimeVisionAI/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── api/
│   ├── __init__.py
│   ├── upload_routes.py
│   ├── analyze_routes.py
│   └── report_routes.py
├── services/
│   ├── __init__.py
│   ├── object_detection_service.py
│   ├── scene_analysis_service.py
│   ├── audio_analysis_service.py
│   ├── video_analysis_service.py
│   ├── evidence_fusion_service.py
│   ├── groq_service.py
│   └── report_service.py
├── utils/
│   ├── __init__.py
│   └── file_utils.py
├── data/                 # generated uploads, temporary processing, and reports
├── models/               # reserved for local model artifacts; pretrained models load lazily
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── Panel.jsx
│   │   │   ├── EvidenceUploader.jsx
│   │   │   ├── AnalysisProgress.jsx
│   │   │   ├── DetectionResults.jsx
│   │   │   ├── SceneAnalysis.jsx
│   │   │   ├── AudioTranscription.jsx
│   │   │   ├── VideoResults.jsx
│   │   │   ├── EvidenceFusion.jsx
│   │   │   ├── ForensicTimeline.jsx
│   │   │   ├── AIReasoning.jsx
│   │   │   └── ReportSection.jsx
│   │   ├── services/api.js
│   │   ├── styles/global.css
│   │   └── utils/presentation.js
│   ├── css/style.css       # retained legacy asset; not loaded by the React app
│   └── js/app.js           # retained legacy asset; not loaded by the React app
├── docs/
│   └── architecture.md
└── tests/
    ├── test_upload.py
    ├── test_analyze_image.py
    ├── test_scene_analysis.py
    ├── test_audio_analysis.py
    ├── test_video_analysis.py
    ├── test_evidence_fusion.py
    ├── test_groq_reasoning.py
    └── test_report_generation.py
```

## Requirements

- Python 3.10 recommended.
- Node.js and npm for the React development frontend.
- A Groq API key is needed only for the reasoning endpoint.
- Pretrained RT-DETR, CLIP, and Whisper weights are loaded lazily when their analysis is requested. First use may download model weights and require substantial disk space and memory.

## Setup

### Backend (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit the local `.env` and set `GROQ_API_KEY` for Groq reasoning. Keep `.env` private; it is ignored by Git. Start Flask:

```powershell
python app.py
```

The development API listens on `http://127.0.0.1:5000` by default. Debug mode is off by default. Set `FLASK_DEBUG=true` only for local development when needed.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal (by default `http://127.0.0.1:5173`). Vite proxies `/api` requests to the local Flask server. To use a different API base, set `VITE_API_BASE_URL` in `frontend/.env.local`; this value is a public API URL and must never contain secrets.

## Environment Variables

Backend settings are loaded from the process environment and local `.env` by `python-dotenv`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | empty | Server-side Groq credential. Never place this in a `VITE_*` variable. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name; override to the model enabled for your account. |
| `SECRET_KEY` | random per process | Flask signing key; set a stable random value for deployments using sessions. |
| `FLASK_DEBUG` | `false` | Enables Flask debug mode only when explicitly true. |
| `FLASK_HOST` | `127.0.0.1` | Development server bind address. |
| `FLASK_PORT` | `5000` | Development server port. |
| `RTDETR_CONFIDENCE_THRESHOLD` | `0.5` | RT-DETR confidence threshold, from 0 to 1. |
| `RTDETR_MODEL_ID` | `PekingU/rtdetr_r50vd` | Transformers model identifier. |
| `CLIP_MODEL_ID` | `openai/clip-vit-base-patch32` | Transformers CLIP model identifier. |
| `WHISPER_MODEL` | `base` | Whisper model size/name. |
| `VIDEO_FRAME_INTERVAL_SECONDS` | `1.0` | OpenCV sampling interval for video frames. |
| `UPLOAD_FOLDER` | `data/uploads` | Evidence upload and temporary analysis files. Relative paths resolve from the project root. |
| `PROCESSED_FOLDER` | `data/processed` | Reserved configured processing directory; current frame extraction uses temporary storage. |
| `REPORT_FOLDER` | `data/reports` | Generated PDF reports. Relative paths resolve from the project root. |
| `VITE_API_BASE_URL` | `/api` | React API base. Vite proxies `/api` to Flask in development. |

`.env.example` contains empty placeholders only. Never commit `.env` or publish API keys in frontend configuration.

## API Endpoints

All endpoints are served by Flask on port 5000. Upload and analysis routes use multipart field `file`; JSON endpoints require JSON request bodies.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health check. |
| `POST` | `/api/upload` | Validate and persist evidence in `data/uploads/`. |
| `POST` | `/api/analyze/image` | RT-DETR object detection on an image. |
| `POST` | `/api/analyze/scene` | CLIP scene category and ranked predictions. |
| `POST` | `/api/analyze/audio` | Whisper transcription and language detection. |
| `POST` | `/api/analyze/video` | OpenCV metadata, sampled frames, and available detections. |
| `POST` | `/api/analyze/fusion` | Normalize supplied modality results and create a deterministic timeline. |
| `POST` | `/api/analyze/reason` | Groq interpretation of deterministic fusion context. |
| `POST` | `/api/report/generate` | Create a PDF from fusion and reasoning results. |
| `GET` | `/api/report/<report_id>` | Download a generated PDF. |

The React workflow uploads evidence, calls the matching analysis route(s), submits their results to fusion, then optionally requests Groq reasoning and PDF generation. PDF upload is supported; direct PDF content analysis is not implemented.

## Testing

Run all backend tests:

```powershell
python -m pytest tests -v
```

Run the eight milestone regression modules:

```powershell
python -m pytest tests/test_report_generation.py tests/test_groq_reasoning.py tests/test_evidence_fusion.py tests/test_video_analysis.py tests/test_audio_analysis.py tests/test_scene_analysis.py tests/test_analyze_image.py tests/test_upload.py -v
```

The model/provider calls are mocked in unit tests; the tests should not download pretrained weights or make Groq API requests.

Build the frontend after installing dependencies:

```powershell
cd frontend
npm run build
```

## Forensic Safety

- RT-DETR and CLIP outputs are probabilistic model predictions, not confirmed facts.
- Transcriptions, video frame results, and timestamps must be checked against source evidence.
- Deterministic fusion organizes supplied results; it does not independently establish what occurred.
- Groq output is an interpretation of supplied context, may be uncertain or incomplete, and does not alter deterministic evidence.
- Investigators must manually review source evidence and all model outputs.
- CrimeVision AI does not determine guilt, identify a criminal with certainty, or make definitive criminal accusations.
