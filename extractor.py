from __future__ import annotations

from pathlib import Path
from typing import List, Optional
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


HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9 ∏\\-/()]+$")
CODE_START_RE = re.compile(r"^(def |class |import |from |graph\s*=|k\s*=|print\(|[a-zA-Z_][a-zA-Z0-9_]*\s*=)")


def _read_pages(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    return pages


def _find_functions(code: str) -> list[CodeFunction]:
    functions: list[CodeFunction] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return functions

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
        warnings.append("Requires Gurobi/gurobipy, which is usually not installed by default.")
    if "networkx" in code:
        warnings.append("Requires networkx if this function is executed.")
    try:
        ast.parse(code)
    except SyntaxError as exc:
        warnings.append(f"Syntax issue detected: {exc.msg} near line {exc.lineno}.")
    return warnings


def _looks_like_heading(line: str) -> bool:
    clean = line.strip()
    if not clean:
        return False
    if clean in {"NP HARD PROBLEMS"}:
        return False
    if clean.lower().endswith("of 225"):
        return False
    if CODE_START_RE.match(clean):
        return False
    return bool(HEADING_RE.match(clean)) and len(clean) <= 80


def extract_pdf_to_catalog(pdf_path: Path) -> Catalog:
    pages = _read_pages(pdf_path)

    items: list[ProblemItem] = []
    current_title: Optional[str] = None
    current_page: int = 1
    current_lines: list[str] = []

    def flush():
        nonlocal current_title, current_page, current_lines
        if current_title and current_lines:
            code = "\n".join(current_lines).strip()
            if code:
                item_id = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-")
                items.append(ProblemItem(
                    id=f"{current_page}-{item_id}",
                    title=current_title,
                    page=current_page,
                    code=code,
                    functions=_find_functions(code),
                    imports=_find_imports(code),
                    warnings=_warnings_for(code),
                ))
        current_lines = []

    for page_index, text in enumerate(pages, start=1):
        lines = [line.rstrip() for line in text.splitlines()]
        for line in lines:
            clean = line.strip()
            if _looks_like_heading(clean):
                flush()
                current_title = clean
                current_page = page_index
                continue

            if current_title:
                # Keep likely code and example lines, skip page headers/footers.
                if clean and clean != "NP HARD PROBLEMS" and not clean.endswith("of 225"):
                    current_lines.append(line)

    flush()

    warning_count = sum(len(item.warnings) for item in items)
    runnable_count = sum(1 for item in items if item.functions and not any("Syntax issue" in w for w in item.warnings))

    return Catalog(
        source_file=pdf_path.name,
        page_count=len(pages),
        item_count=len(items),
        items=items,
        summary={
            "status": "first_pass",
            "warning_count": warning_count,
            "runnable_candidate_count": runnable_count,
            "note": "This is a structural extraction pass. Some snippets from the source PDF may need manual repair before execution."
        }
    )