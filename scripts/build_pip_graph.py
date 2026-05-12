#!/usr/bin/env python3
"""
Build a JSON graph of installed Python distributions and REQUIRES edges,
then write a file and/or POST it to the graph engine API.

Edges point from a dependent distribution to each declared requirement that
exists as another installed distribution (same environment).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib.metadata import distributions
from pathlib import Path


def canon(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown"


def parse_req_project(fragment: str) -> str | None:
    fragment = fragment.split(";")[0].strip().split("[")[0].strip()
    m = re.match(r"^([A-Za-z0-9]([A-Za-z0-9_.-]*[A-Za-z0-9])?)", fragment)
    if not m:
        return None
    return re.sub(r"[^a-z0-9]+", "_", m.group(1).lower()).strip("_")


def build_graph(*, max_dist: int, max_edges: int) -> dict:
    rows = list(distributions())
    names: set[str] = set()
    for d in rows:
        try:
            names.add(canon(d.metadata["Name"]))
        except Exception:
            continue

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for d in rows[:max_dist]:
        try:
            nm = d.metadata["Name"]
            c = canon(nm)
        except Exception:
            continue
        summary = (d.metadata.get("Summary") or "")[:180]
        nodes[c] = {
            "id": c,
            "labels": ["Module"],
            "properties": {
                "display_name": nm,
                "version": d.version or "",
                "summary": summary,
            },
        }
        for req in (d.requires or [])[:40]:
            t = parse_req_project(req)
            if not t or t not in names:
                continue
            key = (c, t)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                {"type": "REQUIRES", "source": c, "target": t, "properties": {}}
            )

    for e in edges:
        tid = e["target"]
        if tid not in nodes:
            nodes[tid] = {
                "id": tid,
                "labels": ["Module"],
                "properties": {
                    "display_name": tid,
                    "version": "",
                    "summary": "Present only as a dependency reference.",
                },
            }

    edges = edges[:max_edges]
    node_list = list(nodes.values())[: max_dist * 2]
    return {"nodes": node_list, "edges": edges}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("examples/pip_dependency_graph.json"),
        help="Output JSON path (default: examples/pip_dependency_graph.json)",
    )
    p.add_argument("--max-dist", type=int, default=200, help="Max distributions to scan")
    p.add_argument("--max-edges", type=int, default=800, help="Max edges to emit")
    p.add_argument(
        "--post-url",
        type=str,
        default="",
        help="If set, POST graph to this URL (e.g. http://127.0.0.1:8000/graph/import?mode=replace)",
    )
    p.add_argument(
        "--database",
        type=str,
        default="neo4j",
        help="X-Database header when using --post-url",
    )
    args = p.parse_args()

    data = build_graph(max_dist=args.max_dist, max_edges=args.max_edges)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.output} ({len(data['nodes'])} nodes, {len(data['edges'])} edges)")

    if args.post_url:
        try:
            import httpx
        except ImportError as e:
            print("Install httpx to use --post-url:", e, file=sys.stderr)
            return 1
        r = httpx.post(
            args.post_url,
            json=data,
            headers={"X-Database": args.database},
            timeout=120.0,
        )
        r.raise_for_status()
        print("POST OK:", r.text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
