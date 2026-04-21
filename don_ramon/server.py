"""
MCP Server for Claude Desktop.

claude_desktop_config.json:
{
  "mcpServers": {
    "don-ramon": {
      "command": "dr",
      "args": ["serve"]
    }
  }
}

To scope to a single repo:
  "args": ["serve", "--repo", "myrepo"]

With Docker:
  "command": "docker",
  "args": ["run", "--rm", "-i", "-v", "don-ramon-data:/root/.don-ramon", "don-ramon", "serve"]
"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from don_ramon.config import load_config, resolve_repo_path
from don_ramon.indexer import storage
from don_ramon.indexer.embeddings import embed_one

_REPO_FILTER = os.environ.get("DR_REPO", "")

mcp = FastMCP("don-ramon")


def _resolve_indexed_repo(selector: str) -> str | None:
    return resolve_repo_path(selector) if selector else None


def _format_results(results: dict) -> str:
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not ids:
        return "No relevant results found."

    parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        score = round(1 - dist, 3)
        header = (
            f"## {meta['qualified_name']} [{meta['django_type']}] "
            f"— {meta['file_path']}:{meta['start_line']} "
            f"(score: {score})"
        )
        parts.append(f"{header}\n\n{doc}")

    return "\n\n---\n\n".join(parts)


@mcp.tool()
def search_code(query: str, n_results: int = 5, repo_path: str = "") -> str:
    """
    Search for code fragments in indexed repos using semantic search.

    Args:
        query: Natural language description of what you're looking for (e.g. "payment webhook", "login view")
        n_results: Number of results to return (default 5, max 10)
        repo_path: Repo path or alias (optional — omit to search all indexed repos)
    """
    n_results = min(n_results, 10)
    embedding = embed_one(query)

    target = repo_path or _REPO_FILTER
    if target:
        resolved_target = _resolve_indexed_repo(target)
        if not resolved_target:
            return f"Repo not indexed (path/alias): {target}"
        results = storage.query(resolved_target, embedding, n_results=n_results)
        return _format_results(results)

    cfg = load_config()
    if not cfg.repos:
        return "No repos indexed. Run: dr index <path>"

    all_parts: list[str] = []
    for repo in cfg.repos:
        results = storage.query(repo.path, embedding, n_results=n_results)
        formatted = _format_results(results)
        if formatted != "No relevant results found.":
            header = f"# Repo: {repo.path}\n\n" if len(cfg.repos) > 1 else ""
            all_parts.append(f"{header}{formatted}")

    return "\n\n===\n\n".join(all_parts) if all_parts else "No relevant results found."


@mcp.tool()
def get_file_structure(repo_path: str = "", subpath: str = "") -> str:
    """
    List .py files in an indexed repo (excluding migrations, __pycache__, etc.).

    Args:
        repo_path: Repo path or alias. Can be omitted if only one repo is indexed.
        subpath: Subdirectory to list (relative to repo root). Empty = root.
    """
    from don_ramon.config import EXCLUDED_DIRS

    target = repo_path or _REPO_FILTER
    if not target:
        cfg = load_config()
        if not cfg.repos:
            return "No repos indexed."
        if len(cfg.repos) == 1:
            target = cfg.repos[0].path
        else:
            paths = "\n".join(f"  - {r.path}" for r in cfg.repos)
            return f"Multiple repos indexed. Specify repo_path:\n{paths}"
    else:
        resolved_target = _resolve_indexed_repo(target)
        if not resolved_target:
            return f"Repo not indexed (path/alias): {target}"
        target = resolved_target

    base = Path(target)
    if subpath:
        base = base / subpath

    if not base.exists():
        return f"Path does not exist: {base}"

    lines = []
    for py_file in sorted(base.rglob("*.py")):
        if any(part in EXCLUDED_DIRS for part in py_file.parts):
            continue
        lines.append(str(py_file.relative_to(Path(target))))

    return "\n".join(lines) if lines else "No .py files found."


@mcp.tool()
def list_indexed_repos() -> str:
    """List all indexed repos with chunk counts."""
    cfg = load_config()
    if not cfg.repos:
        return "No repos indexed."
    lines = []
    for r in cfg.repos:
        alias_part = f"alias: {r.alias} | " if r.alias else ""
        lines.append(f"- {alias_part}{r.path} ({r.chunk_count} chunks)")
    return "\n".join(lines)
