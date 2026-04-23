#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Don Ramón - Semantic code search for AI agents
# Copyright (c) 2026 Julian Orcinoli
# Licensed under PolyForm Noncommercial 1.0.0
# See LICENSE file for details

import time
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from don_ramon.indexer.parser import is_supported_code_file


class _CodeFileHandler(FileSystemEventHandler):
    def __init__(self, repo_path: Path, on_change: Callable[[Path], None], on_delete: Callable[[Path], None]):
        self._repo_path = repo_path
        self._on_change = on_change
        self._on_delete = on_delete

    def _is_relevant(self, path: str) -> bool:
        return is_supported_code_file(Path(path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_relevant(event.src_path):
            self._on_change(Path(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_relevant(event.src_path):
            self._on_change(Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_relevant(event.src_path):
            self._on_delete(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            if self._is_relevant(event.src_path):
                self._on_delete(Path(event.src_path))
            if self._is_relevant(event.dest_path):
                self._on_change(Path(event.dest_path))


def watch(
    repo_path: Path,
    on_change: Callable[[Path], None],
    on_delete: Callable[[Path], None],
) -> None:
    handler = _CodeFileHandler(repo_path, on_change, on_delete)
    observer = Observer()
    observer.schedule(handler, str(repo_path), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
