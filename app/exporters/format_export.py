"""Export the current Neo4j graph snapshot to common interchange formats."""

from __future__ import annotations

import io
import re
from typing import Any

import networkx as nx
from neo4j import Session

from app.importers import json_graph as json_graph_importer
from app.schemas import JsonGraphDocument


def _safe_attr_key(k: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]", "_", str(k)).strip("_")
    return s[:80] if s else "attr"


def _stringify(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return str(v)[:500]
    return str(v)


def _document_to_multidigraph(doc: JsonGraphDocument) -> nx.MultiDiGraph:
    d = doc.model_dump()
    G = nx.MultiDiGraph()
    for node in d.get("nodes") or []:
        nid = str(node.get("id") or "")
        if not nid:
            continue
        props = node.get("properties") or {}
        safe = {_safe_attr_key(k): _stringify(v) for k, v in props.items()}
        safe["neo4j_labels"] = ",".join(node.get("labels") or [])
        G.add_node(nid, **safe)
    for i, edge in enumerate(d.get("edges") or []):
        s, t = str(edge.get("source", "")), str(edge.get("target", ""))
        if not s or not t:
            continue
        if s not in G:
            G.add_node(s)
        if t not in G:
            G.add_node(t)
        et = str(edge.get("type", "REL"))
        eprops = {_safe_attr_key(k): _stringify(v) for k, v in (edge.get("properties") or {}).items()}
        eprops["rel_type"] = et
        G.add_edge(s, t, key=f"e{i}", **eprops)
    return G


def export_graphml_string(session: Session) -> str:
    doc = json_graph_importer.export_json_graph(session)
    G = _document_to_multidigraph(doc)
    buf = io.BytesIO()
    nx.write_graphml(G, buf)
    return buf.getvalue().decode("utf-8")


def export_gexf_bytes(session: Session) -> bytes:
    doc = json_graph_importer.export_json_graph(session)
    G = _document_to_multidigraph(doc)
    buf = io.BytesIO()
    nx.write_gexf(G, buf, encoding="utf-8")
    return buf.getvalue()
