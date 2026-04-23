#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Don Ramón - Semantic code search for AI agents
# Copyright (c) 2026 Julian Orcinoli
# Licensed under PolyForm Noncommercial 1.0.0
# See LICENSE file for details
"""Terminal display helpers — banner, spinners, progress."""
from __future__ import annotations

import random
import sys
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

QUOTES = [
    "Let me take a look, let me take a look...",
    "This old neighbor knows his way around.",
    "Pull up a chair, let's see what we've got.",
    "I've been around this block before, chamaco.",
    "Every codebase has its secrets. I know most of them.",
]

_THEME = Theme(
    {
        "logo": "bold cyan",
        "accent": "cyan",
        "dim": "dim white",
        "ok": "bold green",
        "warn": "bold yellow",
        "err": "bold red",
    }
)

# stderr=True so that `dr serve` never corrupts MCP stdio
console = Console(stderr=True, theme=_THEME)

_banner_shown = False

_ART_TOP = """\
           .-\"\"\"-. \n\
          /       \\\n\
         |  ._._.  |"""

_ART_MID = """\
         | (o) (o) |
         |    >    |
         |  \\___/  |"""

_ART_BOT = """\
      |   |  DR   |   |
      |   |_______|   |
       \\_____________/"""


def _build_banner(version: str) -> str:
    quote = random.choice(QUOTES)

    use_color = sys.stderr.isatty()

    ver_line = f"  Don Ramón v{version}  "
    author_line = "  Author: Julian Orcinoli  "
    qt_line = f"  {quote}  "
    inner_w = max(len(ver_line), len(author_line), len(qt_line))
    ver_line = ver_line.ljust(inner_w)
    author_line = author_line.ljust(inner_w)
    qt_line = qt_line.ljust(inner_w)

    if use_color:
        Y = "\033[33m"   # yellow/tierra
        C = "\033[36m"   # cyan accent
        M = "\033[35m"   # magenta accent
        D = "\033[2m"    # dim
        I = "\033[3m"    # italic
        R = "\033[0m"    # reset
        h_bar = "─" * inner_w
        top    = f"{Y}┌{h_bar}┐{R}"
        b_ver  = f"{Y}│{R}{C}{ver_line}{R}{Y}│{R}"
        b_auth = f"{Y}│{R}{M}{author_line}{R}{Y}│{R}"
        b_qt   = f"{Y}│{R}{D}{I}{qt_line}{R}{Y}│{R}"
        bottom = f"{Y}└{h_bar}┘{R}"

        art_y = f"{Y}{_ART_TOP}{R}"
        art_m = f"{M}{_ART_MID}{R}"
        art_b = f"{C}{_ART_BOT}{R}"
    else:
        h_bar = "-" * inner_w
        top    = f"+{h_bar}+"
        b_ver  = f"|{ver_line}|"
        b_auth = f"|{author_line}|"
        b_qt   = f"|{qt_line}|"
        bottom = f"+{h_bar}+"

        art_y = _ART_TOP
        art_m = _ART_MID
        art_b = _ART_BOT

    art_lines = art_y.split("\n")
    mid_lines = art_m.split("\n")

    line0 = art_lines[0]
    line1 = art_lines[1]
    line2 = f"{art_lines[2]}     {top}"
    line3 = f"{mid_lines[0]}     {b_ver}"
    line4 = f"{mid_lines[1]}     {b_auth}"
    line5 = f"{mid_lines[2]}     {b_qt}"
    pad = " " * len(_ART_MID.split("\n")[2])
    line6 = f"{pad}     {bottom}"

    return "\n".join([line0, line1, line2, line3, line4, line5, line6]) + "\n" + art_b


def print_banner(subtitle: str = "") -> None:
    global _banner_shown
    if _banner_shown:
        return
    _banner_shown = True

    from don_ramon import __version__
    banner = _build_banner(__version__)
    print(banner, file=sys.stderr)
    if subtitle:
        print(f"  {subtitle}", file=sys.stderr)
    print(file=sys.stderr)


# Keep old name as alias used throughout cli.py
def print_logo(subtitle: str = "") -> None:
    print_banner(subtitle)


@contextmanager
def spinner(message: str, done_message: str = ""):
    with console.status(f"[accent]{message}[/]", spinner="dots"):
        yield
    if done_message:
        console.print(f"  [ok]✓[/] {done_message}")


def step(message: str) -> None:
    console.print(f"  [dim]·[/] {message}")


def ok(message: str) -> None:
    console.print(f"  [ok]✓[/] {message}")


def warn(message: str) -> None:
    console.print(f"  [warn]![/] {message}")


def error(message: str) -> None:
    console.print(f"  [err]✗[/] {message}")


def rule(title: str = "") -> None:
    console.rule(f"[dim]{title}[/]" if title else "")


def server_ready(repos: list, repo_filter: str = "") -> None:
    lines: list[str] = []

    if repo_filter:
        lines.append(f"[dim]scope:[/]  [accent]{repo_filter}[/]")
    elif repos:
        total_chunks = sum(r.chunk_count for r in repos)
        lines.append(
            f"[dim]repos:[/]  [accent]{len(repos)}[/]  "
            f"[dim]·[/]  [accent]{total_chunks:,}[/] chunks"
        )
        for r in repos:
            lines.append(f"         [dim]{r.path}[/]")
    else:
        lines.append("[warn]No repos indexed yet.[/]  Run: dr index <path>")

    lines.append("")
    lines.append("[dim]transport:[/]  stdio   [dim]|[/]  waiting for Claude Desktop…")

    console.print(
        Panel(
            "\n".join(lines),
            title="[ok]MCP server ready[/]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
