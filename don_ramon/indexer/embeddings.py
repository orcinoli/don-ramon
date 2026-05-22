#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Don Ramón - Semantic code search for AI agents
# Copyright (c) 2026 Julian Orcinoli
# Licensed under PolyForm Noncommercial 1.0.0
# See LICENSE file for details
from sentence_transformers import SentenceTransformer

from don_ramon.config import load_config

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(load_config().embedding_model)
    return _model


def embed(texts: list[str], batch_size: int = 256) -> list[list[float]]:
    return get_model().encode(texts, batch_size=batch_size, show_progress_bar=False).tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
