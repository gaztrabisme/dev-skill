#!/usr/bin/env python3
"""Generate work graph visualization from .tracks/ nodes.

Reads node markdown files, generates:
  - index.md  — machine-readable state table
  - map.html  — self-contained interactive graph (Mermaid.js, zero deps)

Usage:
  python3 generate-map.py <project-root>        # regenerate from existing nodes
  python3 generate-map.py --init <project-root>  # initialize .tracks/ structure
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter parser (no PyYAML dependency)
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML-like frontmatter from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}, content

    fm = {}
    for line in match.group(1).strip().split("\n"):
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        # Parse bracket lists: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip() for v in val[1:-1].split(",") if v.strip()]
        fm[key] = val

    return fm, content[match.end() :]


# ---------------------------------------------------------------------------
# Node I/O
# ---------------------------------------------------------------------------

def load_nodes(project_root: str) -> list[dict]:
    """Load all node files from .tracks/nodes/."""
    nodes_dir = Path(project_root) / ".tracks" / "nodes"
    if not nodes_dir.exists():
        return []

    nodes = []
    for f in sorted(nodes_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        fm["_file"] = f.name
        fm["_body"] = body.strip()
        fm.setdefault("id", f.stem)
        fm.setdefault("title", fm["id"].replace("-", " ").title())
        fm.setdefault("status", "paused")
        fm.setdefault("created", "?")
        fm.setdefault("updated", "?")
        # Normalize depends to list
        deps = fm.get("depends", [])
        if isinstance(deps, str):
            deps = [deps] if deps else []
        fm["depends"] = deps
        nodes.append(fm)

    return nodes


def init_tracks(project_root: str) -> None:
    """Create .tracks/ skeleton with an example node."""
    tracks = Path(project_root) / ".tracks"
    nodes_dir = tracks / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    # Example node so the user sees the format
    example = nodes_dir / "example.md"
    if not example.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        example.write_text(
            f"""---
id: example
title: Example Workstream
status: active
created: {today}
updated: {today}
depends: []
---

## Objective
Describe what this workstream is trying to achieve.

## Ideas
- [ ] First hypothesis to test
- [ ] Second hypothesis to test

## Breadcrumbs
- **{today}** -- Created this workstream.

## Next
- Define the first concrete step.
""",
            encoding="utf-8",
        )

    print(json.dumps({"initialized": str(tracks), "example": str(example)}))


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def generate_index(nodes: list[dict], project_root: str) -> None:
    """Write .tracks/index.md — a compact status table Claude reads on entry."""
    tracks = Path(project_root) / ".tracks"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Work Graph",
        f"> Last generated: {now}",
        "",
    ]

    status_order = ["active", "paused", "blocked", "done"]
    status_icons = {"active": ">>", "paused": "..", "blocked": "!!", "done": "ok"}

    for status in status_order:
        group = [n for n in nodes if n.get("status") == status]
        if not group:
            continue
        lines.append(f"## {status_icons[status]} {status.upper()}")
        for n in group:
            deps = ", ".join(n["depends"]) if n["depends"] else ""
            deps_str = f" (depends: {deps})" if deps else ""
            lines.append(
                f"- [{n['title']}](nodes/{n['_file']}){deps_str} — updated {n.get('updated', '?')}"
            )
        lines.append("")

    if not nodes:
        lines.append("*No workstreams yet. Create nodes in `.tracks/nodes/`.*")

    (tracks / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Mermaid graph
# ---------------------------------------------------------------------------

def sanitize_id(node_id: str) -> str:
    """Make a node ID safe for Mermaid."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", node_id)


def generate_mermaid(nodes: list[dict]) -> str:
    """Build Mermaid flowchart definition from nodes."""
    if not nodes:
        return "graph LR\n    empty[No workstreams yet]"

    lines = ["graph LR"]

    status_label = {
        "active": "ACTIVE",
        "paused": "paused",
        "blocked": "BLOCKED",
        "done": "done",
    }

    for n in nodes:
        nid = sanitize_id(n["id"])
        title = n.get("title", n["id"])
        if len(title) > 35:
            title = title[:32] + "..."
        status = n.get("status", "paused")
        label = f"{title}\\n[{status_label.get(status, status)}]"
        lines.append(f'    {nid}["{label}"]')

    # Edges from depends
    node_ids = {n["id"] for n in nodes}
    for n in nodes:
        nid = sanitize_id(n["id"])
        for dep in n["depends"]:
            if dep in node_ids:
                lines.append(f"    {sanitize_id(dep)} --> {nid}")

    # Style classes
    lines.append("")
    lines.append(
        "    classDef active fill:#1a3d1a,stroke:#4ade80,color:#e6edf3,stroke-width:2px"
    )
    lines.append(
        "    classDef paused fill:#3d3d1a,stroke:#facc15,color:#e6edf3,stroke-width:1px"
    )
    lines.append(
        "    classDef blocked fill:#3d1a1a,stroke:#f87171,color:#e6edf3,stroke-width:2px"
    )
    lines.append(
        "    classDef done fill:#1a2d3d,stroke:#67e8f9,color:#8b949e,stroke-width:1px"
    )

    for n in nodes:
        nid = sanitize_id(n["id"])
        status = n.get("status", "paused")
        if status in ("active", "paused", "blocked", "done"):
            lines.append(f"    class {nid} {status}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(nodes: list[dict], mermaid_def: str, project_root: str) -> str:
    """Self-contained HTML with Mermaid graph + expandable node cards."""
    project_name = Path(project_root).name
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Prepare node data for JS (strip internal fields)
    cards = []
    for n in nodes:
        cards.append(
            {
                "id": n["id"],
                "title": n.get("title", n["id"]),
                "status": n.get("status", "paused"),
                "updated": n.get("updated", "?"),
                "depends": n.get("depends", []),
                "body": n.get("_body", ""),
            }
        )
    cards_json = json.dumps(cards, indent=2, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Work Graph - {project_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0d1117; color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    padding: 24px; max-width: 1400px; margin: 0 auto;
  }}
  h1 {{ color: #58a6ff; font-size: 1.5em; margin-bottom: 2px; }}
  .subtitle {{ color: #8b949e; font-size: 0.85em; margin-bottom: 20px; }}
  .legend {{ display: flex; gap: 20px; margin-bottom: 16px; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.85em; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .dot-active {{ background: #4ade80; }}
  .dot-paused {{ background: #facc15; }}
  .dot-blocked {{ background: #f87171; }}
  .dot-done {{ background: #67e8f9; }}
  .graph-box {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 24px; margin-bottom: 24px; text-align: center; overflow-x: auto;
  }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 12px; }}
  .card {{
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 16px; cursor: pointer; transition: border-color 0.15s;
  }}
  .card:hover {{ border-color: #58a6ff; }}
  .card.open {{ grid-column: 1 / -1; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; }}
  .card-title {{ font-weight: 600; color: #e6edf3; }}
  .badge {{ font-size: 0.75em; padding: 2px 10px; border-radius: 12px; }}
  .badge-active {{ background: #1a3d1a; color: #4ade80; }}
  .badge-paused {{ background: #3d3d1a; color: #facc15; }}
  .badge-blocked {{ background: #3d1a1a; color: #f87171; }}
  .badge-done {{ background: #1a2d3d; color: #67e8f9; }}
  .card-meta {{ font-size: 0.8em; color: #8b949e; margin-top: 4px; }}
  .card-body {{
    max-height: 0; overflow: hidden; transition: max-height 0.3s ease;
    font-size: 0.85em; line-height: 1.6; white-space: pre-wrap;
    border-top: 1px solid transparent; margin-top: 0; padding-top: 0;
  }}
  .card.open .card-body {{
    max-height: 5000px; border-color: #30363d; margin-top: 12px; padding-top: 12px;
  }}
  .card-body h2 {{ font-size: 1em; color: #58a6ff; margin: 12px 0 4px; }}
  .card-body h2:first-child {{ margin-top: 0; }}
  strong {{ color: #e6edf3; }}
  .refresh {{
    position: fixed; bottom: 20px; right: 20px; background: #238636; color: #fff;
    border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.85em;
  }}
  .refresh:hover {{ background: #2ea043; }}
</style>
</head>
<body>

<h1>Work Graph</h1>
<p class="subtitle">{project_name} &mdash; {now}</p>

<div class="legend">
  <div class="legend-item"><div class="dot dot-active"></div> Active</div>
  <div class="legend-item"><div class="dot dot-paused"></div> Paused</div>
  <div class="legend-item"><div class="dot dot-blocked"></div> Blocked</div>
  <div class="legend-item"><div class="dot dot-done"></div> Done</div>
</div>

<div class="graph-box">
  <pre class="mermaid">
{mermaid_def}
  </pre>
</div>

<div class="cards" id="cards"></div>

<button class="refresh" onclick="location.reload()">Refresh</button>

<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'dark',
    flowchart: {{ curve: 'basis', padding: 16 }}
  }});

  const nodes = {cards_json};
  const box = document.getElementById('cards');

  function esc(s) {{ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}

  function renderBody(md) {{
    return md
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^- \\[x\\] (.+)$/gm, '  <s>$1</s>')
      .replace(/^- \\[ \\] (.+)$/gm, '  &#9744; $1')
      .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  }}

  nodes.forEach(n => {{
    const c = document.createElement('div');
    c.className = 'card';
    const deps = n.depends.length ? ' | depends: ' + n.depends.join(', ') : '';
    c.innerHTML = `
      <div class="card-head">
        <span class="card-title">${{esc(n.title)}}</span>
        <span class="badge badge-${{n.status}}">${{n.status}}</span>
      </div>
      <div class="card-meta">updated ${{n.updated}}${{deps}}</div>
      <div class="card-body">${{renderBody(esc(n.body))}}</div>
    `;
    c.onclick = () => c.classList.toggle('open');
    box.appendChild(c);
  }});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate work graph from .tracks/")
    parser.add_argument("project_root", nargs="?", default=".", help="Project root")
    parser.add_argument("--init", action="store_true", help="Initialize .tracks/")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)

    if args.init:
        init_tracks(project_root)
        return

    tracks = Path(project_root) / ".tracks"
    if not tracks.exists():
        print("Error: no .tracks/ found. Run with --init first.", file=sys.stderr)
        sys.exit(1)

    nodes = load_nodes(project_root)
    generate_index(nodes, project_root)

    mermaid_def = generate_mermaid(nodes)
    html = generate_html(nodes, mermaid_def, project_root)
    (tracks / "map.html").write_text(html, encoding="utf-8")

    summary = {
        "total": len(nodes),
        "active": sum(1 for n in nodes if n.get("status") == "active"),
        "paused": sum(1 for n in nodes if n.get("status") == "paused"),
        "blocked": sum(1 for n in nodes if n.get("status") == "blocked"),
        "done": sum(1 for n in nodes if n.get("status") == "done"),
        "map": str(tracks / "map.html"),
        "index": str(tracks / "index.md"),
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
