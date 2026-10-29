"""REST endpoints for generating and downloading forensic PDF reports."""

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from services.report_service import (
    ReportInputError,
    generate_report,
    resolve_report_path,
)


report_blueprint = Blueprint("report", __name__)


def _reports_directory():
    return Path(current_app.root_path) / current_app.config.get(
        "REPORT_FOLDER", "data/reports"
    )


@report_blueprint.post("/api/report/generate")
def generate_forensic_report():
    # Parse silently so absent content types, empty bodies, and malformed JSON
    # are handled by this endpoint with the same validation response.
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"success": False, "message": "Request body must be a non-empty JSON object."}), 400
    try:
        report = generate_report(payload, _reports_directory())
    except ReportInputError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except OSError:
        current_app.logger.exception("Forensic PDF report could not be written")
        return jsonify({"success": False, "message": "Report generation failed."}), 500
    except Exception:
        current_app.logger.exception("Forensic PDF report generation failed")
        return jsonify({"success": False, "message": "Report generation failed."}), 500
    return jsonify({
        "success": True,
        "report_id": report["report_id"],
        "filename": report["filename"],
        "report_path": "/api/report/{}".format(report["report_id"]),
        "status": "generated",
    }), 201


@report_blueprint.get("/api/report/<report_id>")
def download_forensic_report(report_id):
    path = resolve_report_path(report_id, _reports_directory())
    if path is None:
        return jsonify({"success": False, "message": "Report not found."}), 404
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name=path.name)
