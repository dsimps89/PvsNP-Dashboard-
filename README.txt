NP PDF Unified HTML/Python Program

Open np_pdf_single_file_program.html in a browser.

What it does:
1. Uploads the PDF directly in the browser.
2. Extracts all PDF pages with PDF.js.
3. Sanitizes the extracted text.
4. Compiles a searchable catalog.
5. Renders code line by line in HTML.
6. Uses Pyodide to run Python inside the browser.
7. Exports:
   - np_pdf_catalog.json
   - unified_np_pdf_script.py

Important:
- This is a single-file HTML program.
- It requires internet access for PDF.js and Pyodide CDNs.
- It does not mathematically validate the document.
- Some extracted sections still need manual repair because PDF text extraction loses indentation and wraps lines.
