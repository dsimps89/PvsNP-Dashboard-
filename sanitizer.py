from __future__ import annotations

import re
from dataclasses import dataclass


PAGE_FOOTER_RE = re.compile(r"^\d+\s+of\s+\d+$")
HEADER_LINES = {"NP HARD PROBLEMS"}


@dataclass
class SanitizedLine:
    text: str
    page: int


def normalize_pdf_lines(pages: list[str]) -> list[SanitizedLine]:
    """
    Convert raw PDF text pages into cleaner logical lines.

    This does not try to fully repair Python. It removes obvious PDF artifacts,
    joins continuation fragments, and keeps page metadata.
    """
    out: list[SanitizedLine] = []

    for page_number, page_text in enumerate(pages, start=1):
        for raw in page_text.splitlines():
            line = raw.rstrip()
            clean = line.strip()

            if not clean:
                continue
            if clean in HEADER_LINES:
                continue
            if PAGE_FOOTER_RE.match(clean):
                continue
            if clean.lower().startswith("title:"):
                continue
            if clean.lower().startswith("author information"):
                continue
            if clean.lower().startswith("author:"):
                continue
            if clean.lower().startswith("affiliation:"):
                continue
            if clean.lower().startswith("corresponding author"):
                continue
            if clean.lower().startswith("orcid:"):
                continue

            # Normalize odd symbols commonly seen in extracted headings.
            clean = clean.replace("∏", "Pi").replace("Π", "Pi")

            out.append(SanitizedLine(clean, page_number))

    return join_wrapped_lines(out)


def _line_is_probably_continuation(line: str) -> bool:
    if line.startswith((")", "]", "}", "==", "+", "-", "*", "/", "and ", "or ")):
        return True
    if line.endswith((",", "\\", "(", "[", "{")):
        return True
    return False


def join_wrapped_lines(lines: list[SanitizedLine]) -> list[SanitizedLine]:
    """
    Join obvious PDF line wraps. Conservative by design.
    """
    if not lines:
        return []

    joined: list[SanitizedLine] = []

    for item in lines:
        if not joined:
            joined.append(item)
            continue

        prev = joined[-1].text
        cur = item.text

        should_join = (
            prev.endswith((",", "\\", "(", "[", "{")) or
            cur.startswith((")", "]", "}", "==", "+", "-", "*", "/", "and ", "or ")) or
            (prev.count("(") > prev.count(")") and not cur.startswith(("def ", "class ", "import ", "from "))) or
            (prev.count("[") > prev.count("]") and not cur.startswith(("def ", "class ", "import ", "from ")))
        )

        if should_join:
            joined[-1] = SanitizedLine(prev + " " + cur, joined[-1].page)
        else:
            joined.append(item)

    return joined


def looks_like_heading(text: str) -> bool:
    """
    Detect problem titles such as 'Vertex Cover' or 'Hamiltonian Circuit'.
    """
    if not text:
        return False

    if len(text) > 90:
        return False

    code_prefixes = (
        "def ", "class ", "import ", "from ", "for ", "if ", "elif ", "else:",
        "return ", "print(", "graph =", "k =", "#", "visited =", "queue =",
        "stack =", "subgraph =", "max_", "min_", "model.", "x ="
    )
    if text.startswith(code_prefixes):
        return False

    if re.search(r"[=\[\]\{\}:]{2,}", text):
        return False

    # Title Case / acronym-ish headings.
    words = text.split()
    if not words:
        return False

    starts_titleish = sum(1 for w in words if w[:1].isupper() or w.isupper())
    return starts_titleish >= max(1, len(words) - 1)


def sanitize_code_block(lines: list[str]) -> str:
    """
    Clean a section's code block enough for catalog display and rough AST checks.

    This intentionally avoids aggressive auto-indentation, because bad repairs can
    produce misleading executable code.
    """
    cleaned = []

    for line in lines:
        s = line.strip()

        if not s:
            continue
        if looks_like_heading(s):
            continue

        # Remove leading bullets or page extraction artifacts.
        s = re.sub(r"^[•\-\u2022]\s*", "", s)

        # Repair common spaced operators/fragments.
        s = s.replace(" = = ", " == ")
        s = s.replace(" ! = ", " != ")
        s = s.replace(" < = ", " <= ")
        s = s.replace(" > = ", " >= ")

        cleaned.append(s)

    return "\n".join(cleaned).strip()


def build_sections(lines: list[SanitizedLine]) -> list[dict]:
    """
    Build raw sections from sanitized lines.
    """
    sections = []
    current_title = None
    current_page = 1
    current_lines: list[str] = []

    def flush():
        nonlocal current_title, current_page, current_lines
        if current_title and current_lines:
            code = sanitize_code_block(current_lines)
            if code:
                sections.append({
                    "title": current_title,
                    "page": current_page,
                    "code": code
                })
        current_lines = []

    for item in lines:
        if looks_like_heading(item.text):
            flush()
            current_title = item.text
            current_page = item.page
        else:
            if current_title:
                current_lines.append(item.text)

    flush()
    return sections