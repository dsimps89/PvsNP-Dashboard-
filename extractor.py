from __future__ import annotations

from pathlib import Path
import ast
import re

import fitz
from pydantic import BaseModel, Field

from engine.sanitizer import normalize_pdf_lines, build_sections


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
    status: str = "needs_review"


class Catalog(BaseModel):
    source_file: str
    page_count: int
    item_count: int
    items: list[ProblemItem]
    summary: dict


def _read_pages(pdf_path: Path) -> list[str]:
    doc = fitz.open(pdf_path)
    return [page.get_text("text") for page in doc]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "section"


def _find_functions(code: str) -> list[CodeFunction]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            out.append(CodeFunction(
                name=node.name,
                line_start=node.lineno,
                args=[a.arg for a in node.args.args]
            ))

    return sorted(out, key=lambda f: f.line_start)


def _find_imports(code: str) -> list[str]:
    return [
        line.strip()
        for line in code.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]


def _warnings_for(code: str) -> list[str]:
    warnings = []

    if "pass" in code:
        warnings.append("Contains placeholder pass.")
    if "return True" in code and "# check" in code:
        warnings.append("Likely stub logic: comment says check, but function returns True.")
    if "gurobipy" in code:
        warnings.append("External dependency: gurobipy.")
    if "networkx" in code:
        warnings.append("External dependency: networkx.")
    if "itertools" in code and "import itertools" not in code and "from itertools" not in code:
        warnings.append("Possible missing itertools import.")
    if "combinations(" in code and "from itertools import combinations" not in code:
        warnings.append("Possible missing combinations import.")
    if "nx." in code and "import networkx as nx" not in code:
        warnings.append("Possible missing networkx import.")

    try:
        ast.parse(code)
    except SyntaxError as exc:
        warnings.append(f"Syntax issue after sanitation: {exc.msg} near line {exc.lineno}.")

    return warnings


def _status(functions: list[CodeFunction], warnings: list[str]) -> str:
    if any(w.startswith("Syntax issue") for w in warnings):
        return "syntax_review"
    if not functions:
        return "no_function_found"
    if warnings:
        return "needs_review"
    return "candidate"


def extract_pdf_to_catalog(pdf_path: Path) -> Catalog:
    pages = _read_pages(pdf_path)
    sanitized_lines = normalize_pdf_lines(pages)
    sections = build_sections(sanitized_lines)

    items = []

    for index, section in enumerate(sections, start=1):
        code = section["code"]

        # Only keep sections that contain likely Python/code.
        if not any(marker in code for marker in ("def ", "import ", "print(", "graph =", "nx.")):
            continue

        functions = _find_functions(code)
        imports = _find_imports(code)
        warnings = _warnings_for(code)

        items.append(ProblemItem(
            id=f"{index}-{section['page']}-{_slug(section['title'])}",
            title=section["title"],
            page=section["page"],
            code=code,
            functions=functions,
            imports=imports,
            warnings=warnings,
            status=_status(functions, warnings)
        ))

    status_counts = {}
    for item in items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    return Catalog(
        source_file=pdf_path.name,
        page_count=len(pages),
        item_count=len(items),
        items=items,
        summary={
            "status": "sanitized_pass",
            "status_counts": status_counts,
            "warning_count": sum(len(i.warnings) for i in items),
            "sanitized_line_count": len(sanitized_lines),
            "raw_section_count": len(sections),
            "note": "PDF was sanitized before section extraction. Execution still requires manual verification."
        }
    )