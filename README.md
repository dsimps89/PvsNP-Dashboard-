# NP PDF Unified Program — Sanitized Pass

This version adds a sanitation layer before catalog compilation.

## Why

The source PDF contains code-like text across many pages. Direct PDF extraction can create:

- broken indentation
- wrapped lines
- page headers and footers inside code
- incomplete functions
- missing imports
- section headings mixed with snippets

## Pipeline

```text
PDF upload
  ↓
PyMuPDF raw text extraction
  ↓
sanitizer.py
  - removes headers/footers
  - normalizes symbols
  - joins wrapped lines conservatively
  - detects headings
  - builds raw sections
  ↓
extractor.py
  - creates catalog
  - finds functions/imports
  - detects warnings
  - assigns review status
  ↓
HTML dashboard
```

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

## Status meanings

- `candidate`: no obvious issue detected
- `needs_review`: usable section, but warnings exist
- `syntax_review`: sanitation still leaves syntax problems
- `no_function_found`: code-like section but no function detected

## Important

This program does not validate the mathematical correctness of the source material.
It only sanitizes, organizes, indexes, and lightly tests extracted code.