#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Don Ramón - Semantic code search for AI agents
# Copyright (c) 2026 Julian Orcinoli
# Licensed under PolyForm Noncommercial 1.0.0
# See LICENSE file for details

from __future__ import annotations

import chromadb

from don_ramon.config import CHROMA_PATH, collection_name_for
from don_ramon.indexer.parser import CodeChunk

_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def get_collection(repo_path: str):
    name = collection_name_for(repo_path)
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(repo_path: str, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
    col = get_collection(repo_path)
    col.upsert(
        ids=[c.id for c in chunks],
        embeddings=embeddings,
        documents=[_chunk_document(c) for c in chunks],
        metadatas=[{**_chunk_metadata(c), "repo_path": repo_path} for c in chunks],
    )


def query(repo_path: str, embedding: list[float], n_results: int = 5) -> dict:
    col = get_collection(repo_path)
    available = col.count()
    n = min(n_results, available) if available > 0 else 0
    if n == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    return col.query(
        query_embeddings=[embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )


def delete_file_chunks(repo_path: str, file_rel_path: str) -> None:
    col = get_collection(repo_path)
    results = col.get(where={"file_path": file_rel_path})
    if results["ids"]:
        col.delete(ids=results["ids"])


def count(repo_path: str) -> int:
    return get_collection(repo_path).count()


def _chunk_document(c: CodeChunk) -> str:
    parts = [f"{c.qualified_name} ({c.language}:{c.chunk_type}) in {c.file_path}"]
    if c.docstring:
        parts.append(c.docstring)
    parts.append(c.source)
    return "\n\n".join(parts)


def _chunk_metadata(c: CodeChunk) -> dict:
    return {
        "file_path": c.file_path,
        "name": c.name,
        "qualified_name": c.qualified_name,
        "chunk_type": c.chunk_type,
        "django_type": c.django_type,
        "language": c.language,
        "start_line": c.start_line,
        "end_line": c.end_line,
        "repo_path": "",
    }
