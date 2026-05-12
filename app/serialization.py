from neo4j.graph import Node, Relationship


def node_dict(n: Node) -> dict:
    return {
        "element_id": n.element_id,
        "labels": list(n.labels),
        "properties": dict(n),
    }


def relationship_dict(
    r: Relationship,
    *,
    start_element_id: str | None = None,
    end_element_id: str | None = None,
) -> dict:
    out = {
        "element_id": r.element_id,
        "type": r.type,
        "properties": dict(r),
    }
    if start_element_id is not None:
        out["start_node_element_id"] = start_element_id
    if end_element_id is not None:
        out["end_node_element_id"] = end_element_id
    return out
