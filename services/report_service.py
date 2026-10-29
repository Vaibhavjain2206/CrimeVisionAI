"""Create evidence-grounded PDF reports from fusion and reasoning outputs."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPORT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
REASONING_FIELDS = (
    "case_summary",
    "key_observations",
    "timeline_interpretation",
    "evidence_assessment",
    "uncertainties",
    "recommended_investigator_checks",
)


class UncompressedTextCanvas(Canvas):
    """Canvas that overrides Platypus' pageCompression argument explicitly."""

    def __init__(self, *args, **kwargs):
        # BaseDocTemplate._makeCanvas forwards its own pageCompression setting
        # (which may be enabled) to canvasmaker. Override that forwarded value
        # here so the actual Canvas used for every page writes plain streams.
        kwargs["pageCompression"] = 0
        super().__init__(*args, **kwargs)
        if getattr(self, "_pageCompression", 0) != 0:
            raise RuntimeError("ReportLab page compression must be disabled")


class ReportInputError(ValueError):
    """Raised when report input does not match the expected structure."""


def _unwrap(value):
    if not isinstance(value, dict):
        return {}
    if isinstance(value.get("analysis"), dict):
        return value["analysis"]
    return value


def validate_report_input(payload):
    """Extract the Milestone 7 evidence result and Milestone 8 reasoning result."""
    if not isinstance(payload, dict) or not payload:
        raise ReportInputError("Request body must be a non-empty JSON object.")
    fusion = payload.get("fusion", payload.get("evidence_fusion"))
    if fusion is None and any(
        field in payload
        for field in ("normalized_evidence", "forensic_timeline", "summary")
    ):
        # Also accept the Milestone 7 result fields at the request root, alongside
        # the Milestone 8 `reasoning` field.
        fusion = payload
    reasoning = payload.get("reasoning")
    if not isinstance(fusion, dict) or not isinstance(reasoning, dict):
        raise ReportInputError("Request must include fusion and reasoning objects.")
    if isinstance(reasoning.get("reasoning"), dict):
        reasoning = reasoning["reasoning"]

    evidence = fusion.get("normalized_evidence")
    timeline = fusion.get("forensic_timeline")
    summary = fusion.get("summary")
    if not isinstance(evidence, list) or not isinstance(timeline, list):
        raise ReportInputError(
            "Fusion output must include normalized_evidence and forensic_timeline arrays."
        )
    if not isinstance(summary, dict):
        raise ReportInputError("Fusion output must include a summary object.")
    if any(field not in reasoning for field in REASONING_FIELDS):
        raise ReportInputError("Reasoning output is missing required fields.")
    if not isinstance(reasoning["case_summary"], str) or not isinstance(
        reasoning["timeline_interpretation"], str
    ):
        raise ReportInputError("Reasoning summary fields must be strings.")
    for field in REASONING_FIELDS:
        if field not in ("case_summary", "timeline_interpretation") and not isinstance(
            reasoning[field], list
        ):
            raise ReportInputError("Reasoning field {} must be an array.".format(field))
    if any(not isinstance(item, dict) for item in evidence + timeline):
        raise ReportInputError("Fusion evidence and timeline entries must be objects.")
    return {"evidence": evidence, "timeline": timeline, "summary": summary,
            "reasoning": {field: reasoning[field] for field in REASONING_FIELDS}}


def _display(value):
    if value is None or value == "":
        return "Not provided in submitted evidence."
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return escape(str(value)).replace("\n", "<br/>")


def _evidence_observation(item):
    """Return the submitted observation, or the exact missing-value marker."""
    observation = item.get("observation")
    if observation is None or (isinstance(observation, str) and not observation.strip()):
        return "Not provided in submitted evidence."
    return observation


def _detected_object_text(item):
    """Render object labels from evidence without inferring absent observations."""
    metadata = item.get("metadata")
    label = metadata.get("label") if isinstance(metadata, dict) else None
    if isinstance(label, str) and label.strip():
        return "Detected object: {}".format(label)
    observation = item.get("observation")
    if isinstance(observation, str) and observation.startswith("Detected object: "):
        return observation
    return None


def _section(title, styles):
    return Paragraph(escape(title), styles["Heading2"])


def _list_items(items, styles, empty_message="No entries supplied."):
    if not items:
        items = [empty_message]
    return [Paragraph("&#8226; {}".format(_display(item)), styles["BodyText"]) for item in items]


def _evidence_rows(entries, predicate):
    rows = []
    for item in entries:
        if predicate(item):
            observation = _evidence_observation(item)
            metadata = item.get("metadata")
            if isinstance(metadata, (dict, list)) and metadata:
                observation = "{} | Metadata: {}".format(
                    observation,
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str),
                )
            rows.append([
                item.get("timestamp"),
                "{} / {}".format(
                    item.get("evidence_type") or "Not provided",
                    item.get("modality") or "Not provided",
                ),
                item.get("source_filename"),
                observation,
                item.get("confidence"),
                item.get("evidence_id"),
            ])
    return rows


def _table(rows, styles):
    header = ["Timestamp", "Type / modality", "Source file", "Evidence observation", "Confidence", "Evidence ID"]
    table_styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "EvidenceTableHeader",
        parent=table_styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        "EvidenceTableCell",
        parent=table_styles["BodyText"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#243746"),
        wordWrap="CJK",
    )
    data = [[Paragraph(_display(value), header_style) for value in header]]
    data.extend([
        [Paragraph(_display(value), cell_style) for value in row]
        for row in rows
    ])
    if not rows:
        data.append([
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph("No matching evidence supplied.", cell_style),
            Paragraph("", cell_style),
            Paragraph("", cell_style),
        ])
    table = Table(
        data,
        colWidths=[0.7 * inch, 1.05 * inch, 1.1 * inch, 2.65 * inch, 0.65 * inch, 0.9 * inch],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#18324B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _draw_page(canvas, document):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.HexColor("#18324B"))
    canvas.rect(0, height - 0.22 * inch, width, 0.22 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#607080"))
    canvas.drawString(0.65 * inch, 0.42 * inch, "CrimeVision AI | AI-assisted forensic analysis")
    canvas.drawRightString(width - 0.65 * inch, 0.42 * inch, "Page {}".format(document.page))
    canvas.restoreState()


def generate_report(payload, reports_directory):
    """Write one uniquely named PDF report and return its opaque identifier."""
    normalized = validate_report_input(payload)
    report_id = uuid.uuid4().hex
    filename = "crimevision_report_{}.pdf".format(report_id)
    report_path = Path(reports_directory).resolve() / filename
    report_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#18324B"), fontSize=20, leading=24,
    ))
    story = [
        Spacer(1, 0.12 * inch),
        Paragraph("CrimeVision AI", styles["ReportTitle"]),
        Paragraph("Multimodal Forensic Analysis Report", styles["Heading2"]),
        Spacer(1, 0.12 * inch),
    ]
    metadata = [
        ["Report ID", report_id],
        ["Generated (UTC)", datetime.now(timezone.utc).isoformat(timespec="seconds")],
        ["Case identifier", payload.get("case_id") or "Not provided"],
        ["Evidence items", str(len(normalized["evidence"]))],
    ]
    meta_table = Table([[Paragraph(_display(k), styles["BodyText"]),
                         Paragraph(_display(v), styles["BodyText"])] for k, v in metadata],
                       colWidths=[1.5 * inch, 4.8 * inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7EEF3")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([_section("Case and report metadata", styles), meta_table, Spacer(1, 10)])
    story.extend([_section("Evidence summary", styles),
                  Paragraph(_display(normalized["summary"]), styles["BodyText"]), Spacer(1, 8)])
    reasoning = normalized["reasoning"]
    story.append(_section("AI reasoning and interpretation", styles))
    story.append(Paragraph(
        "The following statements are Groq-generated interpretations of submitted fusion results. "
        "Review them against the deterministic evidence and original source files.",
        styles["Italic"],
    ))
    story.extend([_section("Case summary (interpretation)", styles),
                  Paragraph(_display(reasoning["case_summary"]), styles["BodyText"]), Spacer(1, 8)])
    story.extend([_section("Key observations", styles),
                  *_list_items(reasoning["key_observations"], styles), Spacer(1, 8)])

    sections = [
        ("Detected objects", lambda item: item.get("evidence_type") == "object_detection"),
        ("Scene analysis", lambda item: item.get("evidence_type") == "scene_classification"),
        ("Audio and transcription findings", lambda item: item.get("modality") == "audio"),
        ("Video analysis and timeline", lambda item: item.get("modality") == "video"),
    ]
    for title, predicate in sections:
        story.append(_section(title, styles))
        if title == "Detected objects":
            story.append(Paragraph(
                "RT-DETR results are probabilistic model predictions and require investigator review.",
                styles["Italic"],
            ))
        elif title == "Scene analysis":
            story.append(Paragraph(
                "CLIP scene categories are model predictions and should be interpreted with uncertainty.",
                styles["Italic"],
            ))
        if title == "Detected objects":
            object_labels = [
                _detected_object_text(item)
                for item in normalized["evidence"]
                if predicate(item)
            ]
            object_labels = [label for label in object_labels if label]
            story.extend(_list_items(object_labels, styles, "No detected objects supplied."))
        story.extend([
            _table(_evidence_rows(normalized["evidence"], predicate), styles),
            Spacer(1, 8),
        ])

    story.extend([_section("Evidence fusion timeline", styles),
                  _table(_evidence_rows(normalized["timeline"], lambda _item: True), styles), Spacer(1, 8)])
    story.extend([_section("Timeline interpretation", styles),
                  Paragraph(_display(reasoning["timeline_interpretation"]), styles["BodyText"]), Spacer(1, 8)])
    for title, field in (
        ("Evidence assessment", "evidence_assessment"),
        ("Uncertainties and conflicting evidence", "uncertainties"),
        ("Recommended investigator checks", "recommended_investigator_checks"),
    ):
        story.append(_section(title, styles))
        story.extend(_list_items(reasoning[field], styles))
        story.append(Spacer(1, 8))
    story.extend([KeepTogether([
        _section("Important disclaimer", styles),
        Paragraph(
            _display(
                "CrimeVision AI does not determine guilt or make definitive criminal accusations."
            ),
            styles["BodyText"],
        ),
        Paragraph(
            _display(
                "This report provides analytical assistance and decision support. "
                "Interpretations are limited to the submitted analysis results and "
                "should be independently reviewed by qualified investigators."
            ),
            styles["BodyText"],
        ),
    ])])

    document = SimpleDocTemplate(
        str(report_path), pagesize=letter, rightMargin=0.65 * inch,
        leftMargin=0.65 * inch, topMargin=0.55 * inch, bottomMargin=0.7 * inch,
        title="CrimeVision AI Forensic Analysis Report",
        author="CrimeVision AI",
    )
    # Keep page content streams uncompressed so evidence remains present as
    # searchable, directly inspectable PDF text (including bytes-level checks).
    document.build(
        story,
        onFirstPage=_draw_page,
        onLaterPages=_draw_page,
        canvasmaker=UncompressedTextCanvas,
    )
    return {"report_id": report_id, "filename": filename, "path": str(report_path)}


def resolve_report_path(report_id, reports_directory):
    """Resolve an existing report ID without accepting arbitrary paths."""
    if not isinstance(report_id, str) or not REPORT_ID_PATTERN.fullmatch(report_id):
        return None
    path = Path(reports_directory).resolve() / "crimevision_report_{}.pdf".format(report_id)
    if not path.is_file():
        return None
    return path
