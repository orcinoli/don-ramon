import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DR_HOME = Path.home() / ".don-ramon"
CONFIG_PATH = DR_HOME / "config.yaml"
CHROMA_PATH = DR_HOME / "chroma"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

EXCLUDED_DIRS = {
    "migrations", "__pycache__", ".git", "venv", ".venv",
    "env", "node_modules", "staticfiles", "media", ".tox",
}


@dataclass
class RepoInfo:
    path: str
    collection_name: str
    chunk_count: int = 0
    alias: str = ""


@dataclass
class DonRamonConfig:
    repos: list[RepoInfo] = field(default_factory=list)
    embedding_model: str = DEFAULT_EMBEDDING_MODEL


def collection_name_for(repo_path: str) -> str:
    h = hashlib.sha256(repo_path.encode()).hexdigest()[:12]
    return f"dr_{h}"


def load_config() -> DonRamonConfig:
    if not CONFIG_PATH.exists():
        return DonRamonConfig()
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}
    repos = [RepoInfo(**r) for r in data.get("repos", [])]
    return DonRamonConfig(
        repos=repos,
        embedding_model=data.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
    )


def save_config(cfg: DonRamonConfig) -> None:
    DR_HOME.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(
            {
                "repos": [
                    {
                        "path": r.path,
                        "collection_name": r.collection_name,
                        "chunk_count": r.chunk_count,
                        "alias": r.alias,
                    }
                    for r in cfg.repos
                ],
                "embedding_model": cfg.embedding_model,
            },
            f,
            default_flow_style=False,
            allow_unicode=True,
        )


def register_repo(repo_path: str, chunk_count: int, alias: str = "") -> None:
    cfg = load_config()
    col_name = collection_name_for(repo_path)
    for r in cfg.repos:
        if r.path == repo_path:
            r.chunk_count = chunk_count
            if alias:
                r.alias = alias
            save_config(cfg)
            return
    cfg.repos.append(
        RepoInfo(
            path=repo_path,
            collection_name=col_name,
            chunk_count=chunk_count,
            alias=alias,
        )
    )
    save_config(cfg)


def _find_repo(cfg: DonRamonConfig, repo_selector: str) -> RepoInfo | None:
    repo_abs = str(Path(repo_selector).resolve())
    for r in cfg.repos:
        if r.path == repo_abs or (r.alias and r.alias == repo_selector):
            return r
    return None


def alias_in_use(cfg: DonRamonConfig, alias: str, except_path: str = "") -> bool:
    for r in cfg.repos:
        if r.alias == alias and r.path != except_path:
            return True
    return False


def resolve_repo_path(repo_selector: str) -> str | None:
    cfg = load_config()
    target = _find_repo(cfg, repo_selector.strip())
    return target.path if target else None


def set_repo_alias(repo_selector: str, alias: str) -> bool:
    cfg = load_config()
    target = _find_repo(cfg, repo_selector)
    if not target:
        return False
    if alias_in_use(cfg, alias, except_path=target.path):
        return False
    target.alias = alias
    save_config(cfg)
    return True
