import ast
import re
from dataclasses import dataclass
from pathlib import Path

from don_ramon.config import EXCLUDED_DIRS

EXTENSION_LANGUAGE = {
    ".py": "python",
    ".php": "php",
    ".pas": "delphi",
    ".dpr": "delphi",
    ".cs": "csharp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".swift": "swift",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
}
SUPPORTED_CODE_EXTENSIONS = set(EXTENSION_LANGUAGE.keys())


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
    language: str


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


def is_supported_code_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_CODE_EXTENSIONS and not any(
        part in EXCLUDED_DIRS for part in path.parts
    )


def _parse_python_file(file_path: Path, repo_root: Path) -> list[CodeChunk]:
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
                language="python",
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
                language="python",
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
                        language="python",
                    ))

    return chunks


def _language_patterns(language: str) -> tuple[list[re.Pattern], list[re.Pattern]]:
    class_patterns = [
        re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    ]
    function_patterns = [
        re.compile(r"^\s*(?:public|private|protected|static|final|async|virtual|override|\s)*\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.IGNORECASE),
        re.compile(r"^\s*(?:public|private|protected|internal|static|async|virtual|override|\s)+[\w<>\[\],\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(r"^\s*func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
    ]

    if language == "delphi":
        class_patterns = [
            re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*class\b", re.IGNORECASE),
            re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE),
        ]
        function_patterns = [
            re.compile(r"^\s*(?:class\s+)?(?:procedure|function|constructor|destructor)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE),
        ]
    elif language in {"c", "cpp"}:
        function_patterns.append(
            re.compile(r"^\s*[\w:<>\*\&\s]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{?\s*$")
        )

    return class_patterns, function_patterns


def _parse_non_python_file(file_path: Path, repo_root: Path, language: str) -> list[CodeChunk]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    source_lines = source.splitlines()
    rel_path = str(file_path.relative_to(repo_root))
    class_patterns, function_patterns = _language_patterns(language)
    symbols: list[tuple[int, str, str]] = []

    for idx, line in enumerate(source_lines, start=1):
        for pattern in class_patterns:
            match = pattern.search(line)
            if match:
                symbols.append((idx, match.group(1), "class"))
                break
        else:
            for pattern in function_patterns:
                match = pattern.search(line)
                if match:
                    symbols.append((idx, match.group(1), "function"))
                    break

    chunks: list[CodeChunk] = []
    seen: set[tuple[int, str]] = set()
    for i, (start_line, symbol_name, symbol_type) in enumerate(symbols):
        if (start_line, symbol_name) in seen:
            continue
        seen.add((start_line, symbol_name))
        end_line = (symbols[i + 1][0] - 1) if i + 1 < len(symbols) else len(source_lines)
        if end_line < start_line:
            end_line = start_line
        snippet = "\n".join(source_lines[start_line - 1 : end_line])
        chunks.append(CodeChunk(
            id=f"{rel_path}:{symbol_name}:{start_line}",
            file_path=rel_path,
            name=symbol_name,
            qualified_name=symbol_name,
            chunk_type=symbol_type,
            django_type=symbol_type,
            start_line=start_line,
            end_line=end_line,
            source=snippet,
            docstring="",
            language=language,
        ))

    if chunks:
        return chunks

    # Fallback: chunk entire file in windows when no symbols are detected.
    window = 200
    overlap = 20
    start = 1
    while start <= len(source_lines):
        end = min(start + window - 1, len(source_lines))
        snippet = "\n".join(source_lines[start - 1 : end])
        chunks.append(CodeChunk(
            id=f"{rel_path}:block:{start}",
            file_path=rel_path,
            name=f"block_{start}",
            qualified_name=f"{rel_path}::block_{start}",
            chunk_type="file",
            django_type="other",
            start_line=start,
            end_line=end,
            source=snippet,
            docstring="",
            language=language,
        ))
        if end == len(source_lines):
            break
        start = max(end - overlap + 1, start + 1)

    return chunks


def parse_file(file_path: Path, repo_root: Path) -> list[CodeChunk]:
    if not is_supported_code_file(file_path):
        return []

    ext = file_path.suffix.lower()
    language = EXTENSION_LANGUAGE.get(ext)
    if language == "python":
        return _parse_python_file(file_path, repo_root)
    return _parse_non_python_file(file_path, repo_root, language=language or "other")


def parse_repo(repo_path: Path) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for file_path in sorted(repo_path.rglob("*")):
        if not file_path.is_file():
            continue
        if not is_supported_code_file(file_path):
            continue
        chunks.extend(parse_file(file_path, repo_path))
    return chunks
