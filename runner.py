from __future__ import annotations

import ast
import multiprocessing as mp
import traceback


ALLOWED_IMPORTS = {
    "itertools", "math", "statistics", "collections", "functools", "heapq"
}


def _validate_ast(code: str) -> tuple[bool, str | None]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"

    blocked = (ast.ImportFrom, ast.Import)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    return False, f"Import blocked in safe runner: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                return False, f"Import blocked in safe runner: {node.module}"
        if isinstance(node, (ast.Call,)):
            if isinstance(node.func, ast.Name) and node.func.id in {"open", "exec", "eval", "__import__", "compile", "input"}:
                return False, f"Blocked call: {node.func.id}"

    return True, None


def _worker(queue, code: str, function_name: str, args: list, kwargs: dict):
    namespace = {"__builtins__": {
        "range": range, "len": len, "print": print, "set": set, "list": list,
        "dict": dict, "tuple": tuple, "sum": sum, "min": min, "max": max,
        "all": all, "any": any, "enumerate": enumerate, "zip": zip,
        "float": float, "int": int, "str": str, "bool": bool
    }}
    try:
        exec(code, namespace, namespace)
        fn = namespace.get(function_name)
        if not callable(fn):
            queue.put({"ok": False, "error": f"Function not found: {function_name}"})
            return
        value = fn(*args, **kwargs)
        queue.put({"ok": True, "result": repr(value)})
    except Exception:
        queue.put({"ok": False, "error": traceback.format_exc(limit=5)})


def safe_run_snippet(code: str, function_name: str, args=None, kwargs=None, timeout_seconds=3):
    args = args or []
    kwargs = kwargs or {}

    valid, error = _validate_ast(code)
    if not valid:
        return {"ok": False, "error": error}

    queue = mp.Queue()
    process = mp.Process(target=_worker, args=(queue, code, function_name, args, kwargs))
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        return {"ok": False, "error": f"Execution timed out after {timeout_seconds} seconds."}

    if queue.empty():
        return {"ok": False, "error": "No result returned."}
    return queue.get()