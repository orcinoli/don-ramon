# Don Ramón — search for AI agents

**The wise neighbor of your codebase. Built on MCP.**

Named after Don Ramón, inspired by the latin tradition of the wise neighbor who knows where everything is in the barrio. Technically, it's also a nod to Santiago Ramón y Cajal, the father of neuroscience who mapped how neurons connect — just like embeddings map how code connects.

Author: Julian Orcinoli

---

## Quick Start (Plug and Play)

### 1) Clone the repository

```bash
git clone https://github.com/YOUR_USER/don-ramon.git
cd don-ramon
```

### 2) Create the MCP venv (required for Claude Desktop)

Don Ramón needs its own venv **outside** your project folder so Claude Desktop (which runs sandboxed on macOS) can reach it:

```bash
python3 -m venv ~/.don-ramon/venv
~/.don-ramon/venv/bin/pip install -e /absolute/path/to/don-ramon/
```

The `dr` command will live at `~/.don-ramon/venv/bin/dr` — that's the path you'll use in the MCP config.

> **Dev workflow**: you can also do `pip install -e .` inside a local `.venv` for day-to-day terminal use, but the MCP server must always point to `~/.don-ramon/venv/bin/dr`.

### 3) Run first-time setup

```bash
dr init
```

This creates:

- `~/.don-ramon/config.yaml`
- `~/.don-ramon/chroma` (vector database storage)

### 5) Open the interactive console

```bash
dr
```

Inside the console you can run commands like `status`, `index`, `search`, and `aliases`.

### 6) Index your first repo

From inside `dr>`:

```bash
index /absolute/path/to/your/repo --name myrepo
```

Or from normal terminal:

```bash
dr index /absolute/path/to/your/repo --name myrepo
```

### 7) Search

Inside `dr>`:

```bash
search "where is the payment webhook handled?" --repo myrepo
```

Or from normal terminal:

```bash
dr search "where is the payment webhook handled?" --repo myrepo
```

---

## Daily Usage

### Interactive mode

```bash
dr
```

Common commands inside `dr>`:

- `status`
- `aliases`
- `index /path/to/repo --name alias`
- `search "your query" --repo alias`
- `rename alias newalias`
- `exit`

### Keep index updated while coding

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

## Claude Desktop (MCP) Setup

Config file location:
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

> **macOS sandbox note**: Claude Desktop cannot access files inside `~/Desktop/`. Always use `~/.don-ramon/venv/bin/dr` as the command — never a venv path under `~/Desktop/`.

### Single server (all indexed repos)

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

### One server per project (recommended)

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

`--repo` accepts an alias (recommended) or an absolute path.

After saving the config, restart Claude Desktop.

---

## Commands Reference

| Command | Description |
|---|---|
| `dr` | Open interactive console mode |
| `dr console` | Open interactive console mode |
| `dr init` | First-time setup |
| `dr index <path>` | Index a repo |
| `dr index <path> --name <alias>` | Index and assign alias |
| `dr index <path> --watch` | Index and watch for changes |
| `dr search "<query>"` | Semantic search across indexed repos |
| `dr search "<query>" --repo <alias-or-path>` | Search only one repo |
| `dr status` | Show indexed repos and chunk counts |
| `dr aliases` | Show alias to repo mapping |
| `dr set-alias <repo\|alias> <new-name>` | Assign/update alias |
| `dr rename <repo\|alias> <new-name>` | Rename alias |
| `dr serve` | Start MCP server for Claude Desktop |
| `dr serve --repo <alias-or-path>` | Start MCP server scoped to one repo |

---

## Troubleshooting

### `dr: command not found`

- Activate your dev venv: `source .venv/bin/activate`
- Or use the MCP venv directly: `~/.don-ramon/venv/bin/dr --help`
- Reinstall: `~/.don-ramon/venv/bin/pip install -e /path/to/don-ramon/`

### MCP server fails to start in Claude Desktop

On macOS, Claude Desktop runs sandboxed and cannot read files from `~/Desktop/`. If your project lives there:

- Use `~/.don-ramon/venv/bin/dr` as the MCP command (not the `.venv` inside your project)
- Alternatively, grant Claude Desktop Full Disk Access in *System Preferences → Privacy & Security → Full Disk Access*

### Python version errors

Use Python 3.11+:

```bash
python --version
```

### No repos indexed

Run:

```bash
dr index /path/to/repo --name myrepo
```

---

## How It Works

- Parses Python/Django files into semantic chunks (models, views, serializers, methods, functions)
- Generates embeddings locally with `sentence-transformers/all-MiniLM-L6-v2`
- Stores vectors in ChromaDB at `~/.don-ramon/chroma`
- Exposes search through MCP for Claude Desktop integration
