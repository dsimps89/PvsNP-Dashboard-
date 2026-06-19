# NP PDF Unified Program — First Pass

This is a first-pass Flask + HTML application.

## What it does

- Uploads a PDF.
- Extracts text with PyMuPDF.
- Detects likely problem headings.
- Groups nearby Python code under each heading.
- Builds a searchable catalog.
- Shows functions, imports, warnings, and source page.
- Provides a limited companion runner for simple extracted functions.

## Run

```bash
cd np_pdf_html_first_pass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Notes

This is not a mathematical validator. It does not prove claims from the source PDF. It only extracts, organizes, and lightly tests code snippets.

Some snippets in the PDF contain placeholders, missing imports, indentation issues, or external dependencies. The app flags some of those issues, but manual cleanup is expected.