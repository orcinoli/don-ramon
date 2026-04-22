# Don Ramón — search for AI agents

**The wise neighbor of your codebase. Built on MCP.**

Named after Don Ramón, inspired by the latin tradition of the wise neighbor who knows where everything is in the barrio. Technically, it's also a nod to Santiago Ramón y Cajal, the father of neuroscience who mapped how neurons connect — just like embeddings map how code connects.

Author: Julian Orcinoli

---

## Quick Start

### 1) Clone the repository

```bash
git clone https://github.com/YOUR_USER/don-ramon.git
cd don-ramon
```

### 2) Create the MCP venv

Don Ramón needs its own venv **outside** your project folder so AI tools (which run sandboxed on macOS) can reach it:

```bash
python3 -m venv ~/.don-ramon/venv
~/.don-ramon/venv/bin/pip install -e /absolute/path/to/don-ramon/
```

The `dr` command will live at `~/.don-ramon/venv/bin/dr` — that's the path you'll use in all MCP configs.

> **Dev workflow**: you can also do `pip install -e .` inside a local `.venv` for day-to-day terminal use, but MCP configs must always point to `~/.don-ramon/venv/bin/dr`.

### 3) First-time setup

```bash
dr init
```

This creates `~/.don-ramon/config.yaml` and `~/.don-ramon/chroma` (vector database).

### 4) Index your first repo

```bash
dr index /absolute/path/to/your/repo --name myrepo
```

### 5) Search

```bash
dr search "where is the payment webhook handled?" --repo myrepo
```

---

## MCP Configuration

Don Ramón exposes three MCP tools to any compatible AI agent:

| Tool | Description |
|---|---|
| `search_code` | Semantic search over indexed repos |
| `get_file_structure` | List supported code files in an indexed repo |
| `list_indexed_repos` | Show all indexed repos with chunk counts |

---

### Claude Desktop

Config file:
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

> **macOS sandbox note**: Claude Desktop cannot access files inside `~/Desktop/`. Always use `~/.don-ramon/venv/bin/dr` — never a venv path under `~/Desktop/`.

**All repos:**
```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve"]
    }
  }
}
```

**Scoped to one project (recommended):**
```json
{
  "mcpServers": {
    "don-ramon-myproject": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    },
    "don-ramon-otherapp": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "otherapp"]
    }
  }
}
```

After saving, restart Claude Desktop.

---

### Claude CLI (claude-code)

**Project-level** — create `/your-project/.claude/mcp.json` (applies only to that project):
```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    }
  }
}
```

**Global** — applies to all projects. Add via CLI:
```bash
claude mcp add don-ramon /Users/YOUR_USER/.don-ramon/venv/bin/dr -- serve --repo myproject
```

Or edit `~/.claude/settings.json` directly (in your home directory, not inside any project):
```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    }
  }
}
```

Verify with:
```bash
claude mcp list
```

---

### Cursor

**Project-level** — create `/your-project/.cursor/mcp.json` (applies only to that project):
```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    }
  }
}
```

**Global** — create or edit `~/.cursor/mcp.json` (in your home directory, applies to all projects):
```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    }
  }
}
```

Restart Cursor or reload the window. The `don-ramon` tools will appear in Cursor's MCP panel.

---

### Gemini CLI

Gemini CLI supports MCP servers via its config file at `~/.gemini/settings.json`.

```json
{
  "mcpServers": {
    "don-ramon": {
      "command": "/Users/YOUR_USER/.don-ramon/venv/bin/dr",
      "args": ["serve", "--repo", "myproject"]
    }
  }
}
```

After saving, restart the Gemini CLI session. The `search_code`, `get_file_structure`, and `list_indexed_repos` tools will be available automatically.

---

## Daily Usage

### Interactive console

```bash
dr
```

Commands inside `dr>`:

- `status`
- `aliases`
- `index /path/to/repo --name alias`
- `search "your query" --repo alias`
- `rename alias newalias`
- `exit`

### Watch mode (auto-reindex on file changes)

```bash
dr index /path/to/repo --name myrepo --watch
```

### Manage aliases

```bash
dr set-alias /path/to/repo myrepo
dr rename myrepo mynewrepo
dr aliases
```

---

## Commands Reference

| Command | Description |
|---|---|
| `dr` | Open interactive console |
| `dr console` | Open interactive console |
| `dr init` | First-time setup |
| `dr index <path>` | Index a repo |
| `dr index <path> --name <alias>` | Index with alias |
| `dr index <path> --watch` | Index and watch for changes |
| `dr search "<query>"` | Semantic search across all repos |
| `dr search "<query>" --repo <alias>` | Search one repo |
| `dr status` | Show indexed repos and chunk counts |
| `dr aliases` | Show alias → path mapping |
| `dr set-alias <repo\|alias> <new-name>` | Assign/update alias |
| `dr rename <repo\|alias> <new-name>` | Rename alias |
| `dr serve` | Start MCP server (all repos) |
| `dr serve --repo <alias-or-path>` | Start MCP server (one repo) |

---

## Troubleshooting

### `dr: command not found`

- Activate dev venv: `source .venv/bin/activate`
- Or use the MCP venv: `~/.don-ramon/venv/bin/dr --help`
- Reinstall: `~/.don-ramon/venv/bin/pip install -e /path/to/don-ramon/`

### MCP server fails to start in Claude Desktop

On macOS, Claude Desktop runs sandboxed and cannot read `~/Desktop/`. If your project lives there:

- Use `~/.don-ramon/venv/bin/dr` as the command (not a `.venv` inside your project)
- Or grant Full Disk Access in *System Preferences → Privacy & Security → Full Disk Access*

### Python version errors

Requires Python 3.11+:

```bash
python --version
```

### No repos indexed

```bash
dr index /path/to/repo --name myrepo
```

---

## How It Works

- Parses supported code files into semantic chunks (Python AST + heuristic chunking for other languages)
- Generates embeddings locally with `sentence-transformers/all-MiniLM-L6-v2`
- Stores vectors in ChromaDB at `~/.don-ramon/chroma`
- Exposes `search_code`, `get_file_structure`, and `list_indexed_repos` via MCP
