import ast
from dataclasses import dataclass
from pathlib import Path

from don_ramon.config import EXCLUDED_DIRS


@dataclass
class CodeChunk:
    id: str
    file_path: str
    name: str
    qualified_name: str
    chunk_type: str   # "function" | "class" | "method"
    django_type: str  # "view" | "model" | "serializer" | "viewset" | "form" | "admin" | "task" | "signal" | "test" | "other"
    start_line: int
    end_line: int
    source: str
    docstring: str


def _django_type_for_class(node: ast.ClassDef) -> str:
    bases = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            bases.append(b.id)
        elif isinstance(b, ast.Attribute):
            bases.append(b.attr)

    for base in bases:
        if base == "Model":
            return "model"
        if "Serializer" in base:
            return "serializer"
        if "ViewSet" in base:
            return "viewset"
        if base in ("APIView", "View", "ListView", "DetailView", "CreateView",
                    "UpdateView", "DeleteView", "TemplateView", "RedirectView"):
            return "view"
        if "Form" in base:
            return "form"
        if "Admin" in base or "Inline" in base:
            return "admin"
        if "TestCase" in base:
            return "test"
    return "other"


def _django_type_for_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    for decorator in node.decorator_list:
        deco = ast.unparse(decorator).lower()
        if "task" in deco:
            return "task"
        if "signal" in deco or "receiver" in deco:
            return "signal"
    args = [a.arg for a in node.args.args]
    if args and args[0] == "request":
        return "view"
    return "other"


def _get_source(source_lines: list[str], node: ast.AST) -> str:
    return "\n".join(source_lines[node.lineno - 1 : node.end_lineno])


def parse_file(file_path: Path, repo_root: Path) -> list[CodeChunk]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    source_lines = source.splitlines()
    rel_path = str(file_path.relative_to(repo_root))
    chunks: list[CodeChunk] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(CodeChunk(
                id=f"{rel_path}:{node.name}:{node.lineno}",
                file_path=rel_path,
                name=node.name,
                qualified_name=node.name,
                chunk_type="function",
                django_type=_django_type_for_function(node),
                start_line=node.lineno,
                end_line=node.end_lineno,
                source=_get_source(source_lines, node),
                docstring=ast.get_docstring(node) or "",
            ))

        elif isinstance(node, ast.ClassDef):
            class_django_type = _django_type_for_class(node)
            chunks.append(CodeChunk(
                id=f"{rel_path}:{node.name}:{node.lineno}",
                file_path=rel_path,
                name=node.name,
                qualified_name=node.name,
                chunk_type="class",
                django_type=class_django_type,
                start_line=node.lineno,
                end_line=node.end_lineno,
                source=_get_source(source_lines, node),
                docstring=ast.get_docstring(node) or "",
            ))

            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(CodeChunk(
                        id=f"{rel_path}:{node.name}.{child.name}:{child.lineno}",
                        file_path=rel_path,
                        name=child.name,
                        qualified_name=f"{node.name}.{child.name}",
                        chunk_type="method",
                        django_type=class_django_type,
                        start_line=child.lineno,
                        end_line=child.end_lineno,
                        source=_get_source(source_lines, child),
                        docstring=ast.get_docstring(child) or "",
                    ))

    return chunks


def parse_repo(repo_path: Path) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for py_file in sorted(repo_path.rglob("*.py")):
        if any(part in EXCLUDED_DIRS for part in py_file.parts):
            continue
        chunks.extend(parse_file(py_file, repo_path))
    return chunks
