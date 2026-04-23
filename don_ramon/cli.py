#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Don Ramón - Semantic code search for AI agents
# Copyright (c) 2026 Julian Orcinoli
# Licensed under PolyForm Noncommercial 1.0.0
# See LICENSE file for details
from __future__ import annotations

import sys
from pathlib import Path
import shlex
from typing import Optional

import typer

app = typer.Typer(
    name="dr",
    help="Don Ramón — semantic search for code repositories.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def cidx_deprecated() -> None:
    print(
        "Warning: 'cidx' is deprecated. Use 'dr' or 'don-ramon' instead.",
        file=sys.stderr,
    )
    app()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Open interactive console when no subcommand is passed."""
    if ctx.invoked_subcommand is None:
        console_mode()


@app.command()
def init() -> None:
    """Set up Don Ramón and create ~/.don-ramon/config.yaml."""
    from don_ramon.config import DR_HOME, CONFIG_PATH, save_config, load_config
    from don_ramon import display

    display.print_banner("Initializing...")

    DR_HOME.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        display.warn(f"Config already exists at {CONFIG_PATH}")
    else:
        save_config(load_config())
        display.ok(f"Config created at {CONFIG_PATH}")

    display.ok(f"ChromaDB path: {DR_HOME / 'chroma'}")
    display.rule()
    display.console.print(
        "  Add don-ramon as an MCP server in [accent]claude_desktop_config.json[/]:\n"
        '\n  [dim]"don-ramon": {\n'
        '    "command": "dr",\n'
        '    "args": ["serve"]\n'
        "  }[/]"
    )


@app.command()
def index(
    path: str = typer.Argument(..., help="Path to the repo to index"),
    name: Optional[str] = typer.Option(None, "--name", help="Alias/name for the repo"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch for changes and re-index automatically"),
) -> None:
    """Index a repo. Use --watch to keep listening for file changes."""
    from don_ramon.config import alias_in_use, load_config, register_repo
    from don_ramon.indexer.parser import parse_repo, parse_file
    from don_ramon.indexer.embeddings import embed
    from don_ramon.indexer import storage
    from don_ramon import display

    repo_path = Path(path).resolve()
    if not repo_path.exists():
        display.error(f"Path not found: {repo_path}")
        raise typer.Exit(1)

    repo_str = str(repo_path)
    alias_clean = (name or "").strip()
    if alias_clean:
        cfg = load_config()
        if alias_in_use(cfg, alias_clean, except_path=repo_str):
            display.error(f'Alias "{alias_clean}" is already used by another repo.')
            raise typer.Exit(1)

    display.print_banner(f"Indexing  {repo_path}")

    def _index_full() -> int:
        with display.spinner("Parsing source files…"):
            chunks = parse_repo(repo_path)

        if not chunks:
            display.warn("No chunks found. Are there supported code files in this repo?")
            return 0

        display.ok(f"{len(chunks)} chunks parsed")

        from don_ramon.indexer.storage import _chunk_document
        texts = [_chunk_document(c) for c in chunks]

        with display.spinner(f"Generating embeddings for {len(chunks)} chunks…"):
            embeddings = embed(texts)

        with display.spinner("Saving to ChromaDB…"):
            storage.upsert_chunks(repo_str, chunks, embeddings)
            total = storage.count(repo_str)
            register_repo(repo_str, total, alias=alias_clean)

        display.ok(f"Done — {total} chunks stored")
        return total

    _index_full()

    if watch:
        from don_ramon.indexer.watcher import watch as start_watch
        from don_ramon.indexer.storage import delete_file_chunks

        display.rule()
        display.ok(f"Watching {repo_path}  (Ctrl+C to stop)")

        def on_change(file_path: Path) -> None:
            rel = str(file_path.relative_to(repo_path))
            display.step(f"changed  {rel}")
            delete_file_chunks(repo_str, rel)
            new_chunks = parse_file(file_path, repo_path)
            if new_chunks:
                from don_ramon.indexer.storage import _chunk_document
                texts = [_chunk_document(c) for c in new_chunks]
                embeddings = embed(texts)
                storage.upsert_chunks(repo_str, new_chunks, embeddings)
                register_repo(repo_str, storage.count(repo_str), alias=alias_clean)
                display.ok(f"{len(new_chunks)} chunks updated")

        def on_delete(file_path: Path) -> None:
            rel = str(file_path.relative_to(repo_path))
            display.step(f"deleted  {rel}")
            delete_file_chunks(repo_str, rel)
            register_repo(repo_str, storage.count(repo_str), alias=alias_clean)

        start_watch(repo_path, on_change, on_delete)


@app.command()
def serve(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Scope to a specific indexed repo (path or alias)"),
) -> None:
    """Start the MCP server for Claude Desktop."""
    import os
    from don_ramon.config import load_config, resolve_repo_path
    from don_ramon import display

    if repo:
        resolved = resolve_repo_path(repo)
        if not resolved:
            display.error(f"Repo not indexed (path/alias): {repo}")
            raise typer.Exit(1)
        os.environ["DR_REPO"] = resolved

    cfg = load_config()

    display.print_banner("MCP Server")
    with display.spinner("Starting MCP server…", done_message=""):
        from don_ramon.server import mcp

    display.server_ready(
        repos=cfg.repos,
        repo_filter=os.environ.get("DR_REPO", ""),
    )

    mcp.run()


@app.command()
def search(
    query: str = typer.Argument(..., help="Natural language search query"),
    repo: Optional[str] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Limit search to a specific indexed repo (path or alias)",
    ),
    n: int = typer.Option(5, "--n", "-n", help="Number of results"),
) -> None:
    """Semantic search from the terminal."""
    from don_ramon.config import load_config
    from don_ramon.indexer.embeddings import embed_one
    from don_ramon.indexer import storage
    from don_ramon import display

    cfg = load_config()
    if not cfg.repos:
        display.error("No repos indexed. Run: dr index <path>")
        raise typer.Exit(1)

    repos_to_search = cfg.repos
    if repo:
        from don_ramon.config import resolve_repo_path

        repo_filter = repo.strip()
        resolved = resolve_repo_path(repo_filter)
        if not resolved:
            display.error(f"Repo not indexed (path/alias): {repo_filter}")
            raise typer.Exit(1)
        repos_to_search = [r for r in cfg.repos if r.path == resolved]

    with display.spinner(f'Searching for "{query}"…'):
        embedding = embed_one(query)

    found_any = False
    for repo_info in repos_to_search:
        results = storage.query(repo_info.path, embedding, n_results=n)
        ids = results["ids"][0]
        if not ids:
            continue
        found_any = True
        if len(repos_to_search) > 1:
            typer.echo(f"\n=== {repo_info.path} ===")
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            score = round(1 - dist, 3)
            typer.echo(
                f"\n[{score}] {meta['qualified_name']} ({meta.get('language', 'unknown')}:{meta.get('chunk_type', meta.get('django_type', 'other'))}) "
                f"— {meta['file_path']}:{meta['start_line']}"
            )
            typer.echo("-" * 60)
            typer.echo(doc[:500] + ("..." if len(doc) > 500 else ""))

    if not found_any:
        display.warn("No results found.")


@app.command("set-alias")
def set_alias(
    repo: str = typer.Argument(..., help="Indexed repo path or current alias"),
    alias: str = typer.Argument(..., help="Alias to assign"),
) -> None:
    """Assign or update alias for an indexed repo."""
    from don_ramon.config import set_repo_alias
    from don_ramon import display

    alias_clean = alias.strip()
    if not alias_clean:
        display.error("Alias cannot be empty.")
        raise typer.Exit(1)

    if not set_repo_alias(repo, alias_clean):
        display.error(f'Cannot set alias "{alias_clean}". Repo not found or alias already in use.')
        raise typer.Exit(1)

    display.ok(f'Alias "{alias_clean}" assigned successfully')


@app.command()
def rename(
    repo: str = typer.Argument(..., help="Indexed repo path or current alias"),
    name: str = typer.Argument(..., help="New alias/name"),
) -> None:
    """Rename repo alias (shortcut for set-alias)."""
    set_alias(repo=repo, alias=name)


@app.command("console")
def console_mode() -> None:
    """Open an interactive Don Ramón console."""
    from don_ramon import display
    from don_ramon.config import DR_HOME
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    display.print_banner("Interactive Console")
    typer.echo('Type "help" for commands, "exit" to quit.')

    DR_HOME.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(
        history=FileHistory(str(DR_HOME / "history")),
    )

    while True:
        try:
            raw = session.prompt("dr> ")
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            break

        line = raw.strip()
        if not line:
            continue
        if line in {"exit", "quit"}:
            break
        if line == "help":
            typer.echo("Commands: status, aliases, search, index, set-alias, rename, init, serve, console")
            typer.echo('Use: search "query" --repo myalias')
            continue

        try:
            args = shlex.split(line)
        except ValueError as e:
            display.error(f"Invalid command: {e}")
            continue

        if args and args[0] in {"dr", "don-ramon"}:
            args = args[1:]
        if not args:
            continue
        if args[0] in {"console"}:
            display.warn("Already inside Don Ramón console.")
            continue

        try:
            app(args=args, prog_name="dr", standalone_mode=False)
        except typer.Exit:
            continue
        except Exception as e:  # pragma: no cover - runtime safety for interactive mode
            display.error(str(e))

    typer.echo("Bye.")


@app.command()
def aliases() -> None:
    """List aliases and their repo paths."""
    from don_ramon.config import load_config
    from don_ramon import display

    cfg = load_config()
    if not cfg.repos:
        display.warn("No repos indexed.")
        return

    has_aliases = any(r.alias for r in cfg.repos)
    if not has_aliases:
        display.warn("No aliases configured yet.")

    for r in cfg.repos:
        alias_label = r.alias if r.alias else "(no alias)"
        typer.echo(f"{alias_label} -> {r.path}")


@app.command()
def status() -> None:
    """Show indexed repos and their state."""
    from don_ramon.config import load_config, CONFIG_PATH, DR_HOME
    from don_ramon import display

    cfg = load_config()
    display.print_banner("Status")
    display.step(f"Config:   {CONFIG_PATH}")
    display.step(f"ChromaDB: {DR_HOME / 'chroma'}")
    display.step(f"Model:    {cfg.embedding_model}")
    display.console.print()

    if not cfg.repos:
        display.warn("No repos indexed.")
        display.step("Run: dr index <path>")
        return

    display.console.print(f"  [accent]{len(cfg.repos)} repo(s) indexed:[/]")
    for r in cfg.repos:
        exists_mark = "[ok]✓[/]" if Path(r.path).exists() else "[err]✗[/]"
        alias_suffix = f" [dim](alias: {r.alias})[/]" if r.alias else ""
        display.console.print(f"    {exists_mark}  {r.path}{alias_suffix}")
        display.console.print(
            f"       [dim]chunks: {r.chunk_count}  ·  collection: {r.collection_name}[/]"
        )
