from __future__ import annotations

from pathlib import Path
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from engine.extractor import extract_pdf_to_catalog
from engine.runner import safe_run_snippet

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/upload")
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No file field named 'pdf' was provided."}), 400

    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported in this first pass."}), 400

    safe_name = secure_filename(file.filename)
    pdf_path = UPLOAD_DIR / safe_name
    file.save(pdf_path)

    catalog = extract_pdf_to_catalog(pdf_path)
    CATALOG_PATH.write_text(
        catalog.model_dump_json(indent=2),
        encoding="utf-8"
    )
    return jsonify(catalog.model_dump(mode="json"))


@app.get("/api/catalog")
def catalog():
    if not CATALOG_PATH.exists():
        return jsonify({"items": [], "summary": {"status": "empty"}})
    return jsonify(CATALOG_PATH.read_text(encoding="utf-8"))


@app.get("/api/problems")
def problems():
    if not CATALOG_PATH.exists():
        return jsonify([])
    import json
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return jsonify(data.get("items", []))


@app.post("/api/run")
def run_problem():
    payload = request.get_json(force=True)
    code = payload.get("code", "")
    function_name = payload.get("function_name", "")
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})

    result = safe_run_snippet(code, function_name, args, kwargs)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
