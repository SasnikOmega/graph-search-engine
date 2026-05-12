from neo4j import ManagedTransaction, Session

from app.cypher_utils import format_labels_cypher, validate_rel_type
from app.schemas import JsonGraphDocument, JsonGraphEdge, JsonGraphNode


def import_json_graph(
    session: Session, doc: JsonGraphDocument, *, replace: bool
) -> dict[str, int]:
    def work(tx: ManagedTransaction) -> dict[str, int]:
        if replace:
            tx.run("MATCH (n) DETACH DELETE n").consume()

        id_map: dict[str, str] = {}
        for i, node in enumerate(doc.nodes):
            key = node.id if node.id is not None else str(i)
            labels = node.labels if node.labels else ["GraphNode"]
            label_part = format_labels_cypher(labels)
            props = dict(node.properties)
            rec = tx.run(
                f"CREATE (n:{label_part}) SET n += $props RETURN elementId(n) AS eid",
                props=props,
            ).single()
            if rec is None:
                raise RuntimeError("Failed to create node during import.")
            id_map[key] = rec["eid"]

        edges_created = 0
        for edge in doc.edges:
            sid = id_map.get(edge.source)
            tid = id_map.get(edge.target)
            if sid is None or tid is None:
                raise ValueError(
                    f"Edge references unknown node id: {edge.source!r} -> {edge.target!r}"
                )
            rel = validate_rel_type(edge.type)
            rec = tx.run(
                f"""
                MATCH (a) WHERE elementId(a) = $sid
                MATCH (b) WHERE elementId(b) = $eid
                CREATE (a)-[r:{rel}]->(b)
                SET r += $props
                RETURN r AS rel
                """,
                sid=sid,
                eid=tid,
                props=edge.properties,
            ).single()
            if rec is None:
                raise RuntimeError("Failed to create relationship during import.")
            edges_created += 1

        return {"nodes_created": len(doc.nodes), "edges_created": edges_created}

    return session.execute_write(work)


def export_json_graph(session: Session) -> JsonGraphDocument:
    n_rows = session.run(
        """
        MATCH (n)
        RETURN elementId(n) AS eid, labels(n) AS labels, properties(n) AS props
        """
    )
    nodes: list[JsonGraphNode] = []
    for rec in n_rows:
        props = dict(rec["props"])
        nodes.append(
            JsonGraphNode(
                id=rec["eid"],
                labels=list(rec["labels"]),
                properties=props,
            )
        )

    e_rows = session.run(
        """
        MATCH (a)-[r]->(b)
        RETURN type(r) AS t,
               properties(r) AS props,
               elementId(a) AS s,
               elementId(b) AS e
        """
    )
    edges: list[JsonGraphEdge] = []
    for rec in e_rows:
        edges.append(
            JsonGraphEdge(
                type=rec["t"],
                source=rec["s"],
                target=rec["e"],
                properties=dict(rec["props"]),
            )
        )

    return JsonGraphDocument(nodes=nodes, edges=edges)
