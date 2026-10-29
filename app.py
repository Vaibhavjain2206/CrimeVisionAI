import os

from flask import Flask, jsonify
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

from api.upload_routes import upload_blueprint
from api.analyze_routes import analyze_blueprint
from api.report_routes import report_blueprint

app.register_blueprint(upload_blueprint)
app.register_blueprint(analyze_blueprint)
app.register_blueprint(report_blueprint)

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "project": "CrimeVision AI"})

if __name__ == "__main__":
    app.run(
        debug=app.config["DEBUG"],
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
    )
