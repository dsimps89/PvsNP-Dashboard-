# NP PDF Unified Program — First Pass Fixed

## Run

```bash
cd np_pdf_html_first_pass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Fix included

This version removes the Pydantic v2-only `model_dump_json()` dependency that likely caused upload to succeed but catalog compilation to fail.

## Current features

- PDF upload
- PDF text extraction
- problem/code section detection
- catalog JSON compilation
- searchable HTML dashboard
- warning detection
- limited safe function runner