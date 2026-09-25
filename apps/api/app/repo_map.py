"""Repository mapper: turns code and docs into a knowledge graph plus retrieval chunks, in the spirit of graphify.

Python is parsed with `ast` (modules, classes, functions, imports, calls); TypeScript and JavaScript with light regular
expressions (imports, exported functions, classes, components); Markdown by headings. Communities come from label propagation.
Local paths are restricted to configured roots; GitHub URLs are cloned shallowly into a temporary directory.
"""

from __future__ import annotations

import ast
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from app.config import REPO_ROOT, settings

SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".next", "dist", "build", "public", "coverage", ".pytest_cache", ".ruff_cache", "test-results", "playwright-report", "jupyterlite", "checkpoints"}
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".mdx"}
MAX_FILES = 400
MAX_NODES = 700
MAX_CHUNK = 1400

_TS_IMPORT = re.compile(r"""import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"]""")
_TS_SYMBOL = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+([A-Za-z_$][\w$]*)|class\s+([A-Za-z_$][\w$]*)|const\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)", re.MULTILINE)
_MD_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def allowed_roots() -> list[Path]:
    extra = [Path(p).expanduser().resolve() for p in (getattr(settings, "repo_roots", "") or "").split(",") if p.strip()]
    return [Path(REPO_ROOT).resolve(), *extra]


def resolve_source(source: str) -> tuple[Path, str, tempfile.TemporaryDirectory | None]:
    """A GitHub URL is cloned (depth 1); a local path must sit under an allowed root."""
    if re.match(r"^https://github\.com/[\w.-]+/[\w.-]+", source):
        tmp = tempfile.TemporaryDirectory(prefix="pg-repo-")
        url = source.rstrip("/")
        if not url.endswith(".git"):
            url += ".git"
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, tmp.name], check=True, timeout=120, capture_output=True)
        return Path(tmp.name), source, tmp
    path = Path(source).expanduser().resolve()
    if not any(path == root or root in path.parents for root in allowed_roots()):
        raise PermissionError("Local paths must be inside an allowed repository root")
    if not path.exists():
        raise FileNotFoundError(source)
    return path, str(path), None


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in CODE_EXT and p.stat().st_size < 400_000:
            files.append(p)
        if len(files) >= MAX_FILES:
            break
    return files


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: set[tuple[str, str, str]] = set()
        self.chunks: list[tuple[str, dict]] = []

    def node(self, nid: str, label: str, kind: str, file: str, line: int = 0, **extra) -> None:
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "label": label, "kind": kind, "file": file, "line": line, **extra}

    def edge(self, a: str, b: str, kind: str) -> None:
        if a != b and a in self.nodes and b in self.nodes:
            self.edges.add((a, b, kind))


def _py(g: Graph, rel: str, text: str, module_ids: dict[str, str]) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    lines = text.splitlines()
    defined: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            nid = f"{rel}::{node.name}"
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            g.node(nid, node.name, kind, rel, node.lineno)
            g.edge(rel, nid, "defines")
            defined[node.name] = nid
            end = getattr(node, "end_lineno", None) or node.lineno + 40
            src = "\n".join(lines[node.lineno - 1 : min(end, node.lineno + 60)])
            doc = ast.get_docstring(node) or ""
            g.chunks.append((f"{rel} {kind} {node.name}\n{doc}\n\n{src}"[:MAX_CHUNK], {"file": rel, "symbol": node.name, "kind": kind, "line": node.lineno}))
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                        mid = f"{nid}.{sub.name}"
                        g.node(mid, f"{node.name}.{sub.name}", "method", rel, sub.lineno)
                        g.edge(nid, mid, "defines")
                        defined[sub.name] = mid
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            target = module_ids.get(node.module) or module_ids.get(node.module.split(".")[-1])
            if target:
                g.edge(rel, target, "imports")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = module_ids.get(alias.name)
                if target:
                    g.edge(rel, target, "imports")
    # call edges between symbols defined in this file (cheap and accurate enough for a map)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            src_id = defined.get(node.name)
            for call in ast.walk(node):
                if isinstance(call, ast.Call):
                    name = call.func.id if isinstance(call.func, ast.Name) else call.func.attr if isinstance(call.func, ast.Attribute) else None
                    if name and name in defined and src_id:
                        g.edge(src_id, defined[name], "calls")


def _ts(g: Graph, rel: str, text: str, file_ids: dict[str, str]) -> None:
    for m in _TS_SYMBOL.finditer(text):
        name = m.group(1) or m.group(2) or m.group(3)
        line = text.count("\n", 0, m.start()) + 1
        kind = "class" if m.group(2) else "component" if name[:1].isupper() else "function"
        nid = f"{rel}::{name}"
        g.node(nid, name, kind, rel, line)
        g.edge(rel, nid, "defines")
        snippet = text[m.start() : m.start() + 900]
        g.chunks.append((f"{rel} {kind} {name}\n\n{snippet}"[:MAX_CHUNK], {"file": rel, "symbol": name, "kind": kind, "line": line}))
    for m in _TS_IMPORT.finditer(text):
        spec = m.group(1)
        if spec.startswith("@/"):
            candidate = "apps/web/src/" + spec[2:]
            if candidate not in file_ids and "src/" + spec[2:] in file_ids:
                candidate = "src/" + spec[2:]
        elif spec.startswith("."):
            candidate = (Path(rel).parent / spec).as_posix()
            candidate = re.sub(r"/\./", "/", candidate)
            while "/../" in candidate:
                candidate = re.sub(r"[^/]+/\.\./", "", candidate, count=1)
        else:
            continue
        for ext in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"):
            target = file_ids.get(candidate + ext)
            if target:
                g.edge(rel, target, "imports")
                break


def _md(g: Graph, rel: str, text: str) -> None:
    heads = list(_MD_HEADING.finditer(text))
    stack: list[tuple[int, str]] = []
    for i, m in enumerate(heads):
        level, title = len(m.group(1)), m.group(2).strip()
        nid = f"{rel}::{title[:60]}"
        line = text.count("\n", 0, m.start()) + 1
        g.node(nid, title[:60], "section", rel, line)
        while stack and stack[-1][0] >= level:
            stack.pop()
        g.edge(stack[-1][1] if stack else rel, nid, "contains")
        stack.append((level, nid))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end() : end].strip()
        if body:
            g.chunks.append((f"{rel} § {title}\n\n{body}"[:MAX_CHUNK], {"file": rel, "symbol": title, "kind": "section", "line": line}))


def communities(nodes: list[str], edges: set[tuple[str, str, str]], rounds: int = 12) -> dict[str, int]:
    """Deterministic label propagation over the undirected graph."""
    adj: dict[str, list[str]] = defaultdict(list)
    for a, b, _ in edges:
        adj[a].append(b)
        adj[b].append(a)
    label = {n: i for i, n in enumerate(sorted(nodes))}
    for _ in range(rounds):
        changed = False
        for n in sorted(nodes):
            if not adj[n]:
                continue
            counts: dict[int, int] = defaultdict(int)
            for m in adj[n]:
                counts[label[m]] += 1
            best = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            if best != label[n]:
                label[n] = best
                changed = True
        if not changed:
            break
    remap = {old: i for i, old in enumerate(sorted(set(label.values())))}
    return {n: remap[v] for n, v in label.items()}


def map_repository(source: str) -> dict:
    root, ref, tmp = resolve_source(source)
    try:
        files = iter_files(root)
        g = Graph()
        rels = [p.relative_to(root).as_posix() for p in files]
        for rel in rels:
            g.node(rel, Path(rel).name, "file", rel, 0, ext=Path(rel).suffix)
        module_ids: dict[str, str] = {}
        for rel in rels:
            if rel.endswith(".py"):
                dotted = rel[:-3].replace("/__init__", "").replace("/", ".")
                module_ids[dotted] = rel
                for prefix in ("apps.api.", "app."):
                    if dotted.startswith(prefix):
                        module_ids[dotted[len(prefix) :]] = rel
                module_ids.setdefault(dotted.split(".")[-1], rel)
        file_ids = {rel[: -len(Path(rel).suffix)]: rel for rel in rels} | {rel: rel for rel in rels}
        for p, rel in zip(files, rels, strict=True):
            text = p.read_text("utf-8", "ignore")
            if rel.endswith(".py"):
                _py(g, rel, text, module_ids)
            elif rel.endswith((".ts", ".tsx", ".js", ".jsx")):
                _ts(g, rel, text, file_ids)
            else:
                _md(g, rel, text)
        # folder edges so isolated files still cluster by directory
        for rel in rels:
            parent = Path(rel).parent.as_posix()
            if parent and parent != ".":
                g.node(f"dir:{parent}", parent.split("/")[-1], "folder", parent, 0)
                g.edge(f"dir:{parent}", rel, "contains")
        degree: dict[str, int] = defaultdict(int)
        for a, b, _ in g.edges:
            degree[a] += 1
            degree[b] += 1
        keep = set(sorted(g.nodes, key=lambda n: (-degree[n], n))[:MAX_NODES])
        edges = {e for e in g.edges if e[0] in keep and e[1] in keep}
        comm = communities(list(keep), edges)
        nodes = [{**g.nodes[n], "degree": degree[n], "community": comm.get(n, 0)} for n in sorted(keep)]
        summary = {"files": len(rels), "symbols": sum(1 for n in nodes if n["kind"] in ("function", "class", "method", "component")), "sections": sum(1 for n in nodes if n["kind"] == "section"), "edges": len(edges), "communities": len(set(comm.values())), "source": ref}
        return {"nodes": nodes, "edges": [{"source": a, "target": b, "kind": k} for a, b, k in sorted(edges)], "summary": summary, "chunks": g.chunks}
    finally:
        if tmp is not None:
            tmp.cleanup()
