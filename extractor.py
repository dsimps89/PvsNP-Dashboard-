from __future__ import annotations

from pathlib import Path
from typing import Optional
import ast
import re

import fitz
from pydantic import BaseModel, Field


class CodeFunction(BaseModel):
    name: str
    line_start: int
    args: list[str] = Field(default_factory=list)


class ProblemItem(BaseModel):
    id: str
    title: str
    page: int
    code: str
    functions: list[CodeFunction] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Catalog(BaseModel):
    source_file: str
    page_count: int
    item_count: int
    items: list[ProblemItem]
    summary: dict


HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9 ∏Π\\-/()]+$")
CODE_START_RE = re.compile(
    r"^(def |class |import |from |graph\s*=|k\s*=|print\(|[a-zA-Z_][a-zA-Z0-9_]*\s*=)"
)


def _read_pages(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    return [page.get_text("text") for page in doc]


def _find_functions(code: str) -> list[CodeFunction]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [arg.arg for arg in node.args.args]
            functions.append(CodeFunction(name=node.name, line_start=node.lineno, args=args))
    return sorted(functions, key=lambda f: f.line_start)


def _find_imports(code: str) -> list[str]:
    imports = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
    return imports


def _warnings_for(code: str) -> list[str]:
    warnings = []

    if "pass" in code:
        warnings.append("Contains placeholder 'pass'.")
    if "gurobipy" in code:
        warnings.append("Requires Gurobi/gurobipy.")
    if "networkx" in code:
        warnings.append("Requires networkx.")
    if "return True" in code and "# check" in code:
        warnings.append("May contain stub logic that always returns True.")

    try:
        ast.parse(code)
    except SyntaxError as exc:
        warnings.append(f"Syntax issue detected: {exc.msg} near line {exc.lineno}.")

    return warnings


def _looks_like_heading(line: str) -> bool:
    clean = line.strip()

    if not clean:
        return False
    if clean == "NP HARD PROBLEMS":
        return False
    if re.match(r"^\d+\s+of\s+\d+$", clean):
        return False
    if CODE_START_RE.match(clean):
        return False
    if clean.startswith("#"):
        return False
    if len(clean) > 90:
        return False

    return bool(HEADING_RE.match(clean))


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "section"


def extract_pdf_to_catalog(pdf_path: Path) -> Catalog:
    pages = _read_pages(pdf_path)

    items: list[ProblemItem] = []
    current_title: Optional[str] = None
    current_page = 1
    current_lines: list[str] = []

    def flush():
        nonlocal current_title, current_page, current_lines

        if current_title and current_lines:
            code = "\n".join(current_lines).strip()
            # Keep only sections that have at least some likely code.
            if "def " in code or "import " in code or "print(" in code:
                item_id = f"{current_page}-{_slug(current_title)}"
                items.append(ProblemItem(
                    id=item_id,
                    title=current_title,
                    page=current_page,
                    code=code,
                    functions=_find_functions(code),
                    imports=_find_imports(code),
                    warnings=_warnings_for(code),
                ))

        current_lines = []

    for page_index, text in enumerate(pages, start=1):
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            clean = line.strip()

            if _looks_like_heading(clean):
                flush()
                current_title = clean
                current_page = page_index
                continue

            if current_title:
                if clean and clean != "NP HARD PROBLEMS" and not re.match(r"^\d+\s+of\s+\d+$", clean):
                    current_lines.append(line)

    flush()

    warning_count = sum(len(item.warnings) for item in items)
    runnable_count = sum(
        1 for item in items
        if item.functions and not any("Syntax issue" in w for w in item.warnings)
    )

    return Catalog(
        source_file=pdf_path.name,
        page_count=len(pages),
        item_count=len(items),
        items=items,
        summary={
            "status": "first_pass_fixed",
            "warning_count": warning_count,
            "runnable_candidate_count": runnable_count,
            "note": "Structural extraction only. Some source snippets need manual repair before execution."
        }
    )