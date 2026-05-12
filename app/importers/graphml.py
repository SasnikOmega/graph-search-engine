import io

import networkx as nx

from app.cypher_utils import validate_rel_type
from app.schemas import JsonGraphDocument, JsonGraphEdge, JsonGraphNode


def _safe_rel_type(name: object) -> str:
    raw = str(name) if name is not None else "LINK"
    try:
        return validate_rel_type(raw)
    except ValueError:
        return "LINK"


def graphml_to_document(xml: str) -> JsonGraphDocument:
    """Parse GraphML into the same JSON graph shape used by bulk import."""
    G = nx.read_graphml(io.StringIO(xml))
    nodes: list[JsonGraphNode] = []
    for nid, data in G.nodes(data=True):
        props = {str(k): _coerce_val(v) for k, v in data.items()}
        nodes.append(JsonGraphNode(id=str(nid), labels=["GraphNode"], properties=props))

    edges: list[JsonGraphEdge] = []
    if G.is_multigraph():
        edge_iter = G.edges(keys=True, data=True)
        for u, v, _k, data in edge_iter:
            props = {str(k): _coerce_val(val) for k, val in data.items()}
            et = props.pop("type", None) or props.pop("label", None) or "LINK"
            edges.append(
                JsonGraphEdge(
                    type=_safe_rel_type(et),
                    source=str(u),
                    target=str(v),
                    properties=props,
                )
            )
    else:
        for u, v, data in G.edges(data=True):
            props = {str(k): _coerce_val(val) for k, val in data.items()}
            et = props.pop("type", None) or props.pop("label", None) or "LINK"
            edges.append(
                JsonGraphEdge(
                    type=_safe_rel_type(et),
                    source=str(u),
                    target=str(v),
                    properties=props,
                )
            )

    return JsonGraphDocument(nodes=nodes, edges=edges)


def _coerce_val(v):
    if isinstance(v, (dict, list)):
        return str(v)
    return v
