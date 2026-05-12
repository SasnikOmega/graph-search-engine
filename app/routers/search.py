from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session

from app.cypher_utils import validate_rel_type
from app.deps import get_neo4j_session
from app.schemas import (
    NeighborItem,
    PathResponse,
    PatternSearchRequest,
    RelationshipResponse,
    ShortestPathRequest,
    NodeResponse,
)
from app.serialization import node_dict, relationship_dict

router = APIRouter()


@router.get("/nodes/{element_id}/neighbors", response_model=list[NeighborItem])
def neighbors(
    element_id: str,
    session: Annotated[Session, Depends(get_neo4j_session)],
    direction: str = Query(default="both", pattern="^(out|in|both)$"),
    max_hops: int = Query(default=1, ge=1, le=20),
) -> list[NeighborItem]:
    if direction == "out":
        pat = f"-[*1..{max_hops}]->"
    elif direction == "in":
        pat = f"<-[*1..{max_hops}]-"
    else:
        pat = f"-[*1..{max_hops}]-"

    q = f"""
    MATCH (n) WHERE elementId(n) = $eid
    MATCH p = (n){pat}(m)
    WITH relationships(p) AS rels, m
    UNWIND rels AS r
    RETURN DISTINCT r,
           elementId(startNode(r)) AS sid,
           elementId(endNode(r)) AS eid,
           m AS node
    """
    rows = list(session.run(q, eid=element_id))
    if not rows:
        anchor = session.run(
            "MATCH (n) WHERE elementId(n) = $eid RETURN n AS node",
            eid=element_id,
        ).single()
        if anchor is None:
            raise HTTPException(status_code=404, detail="Node not found.")
        return []

    out: list[NeighborItem] = []
    seen: set[str] = set()
    for rec in rows:
        r = rec["r"]
        other = rec["node"]
        key = f"{r.element_id}:{other.element_id}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            NeighborItem(
                relationship=RelationshipResponse(
                    **relationship_dict(
                        r,
                        start_element_id=rec["sid"],
                        end_element_id=rec["eid"],
                    )
                ),
                node=NodeResponse(**node_dict(other)),
            )
        )
    return out


@router.post("/shortest-path", response_model=PathResponse)
def shortest_path(
    body: ShortestPathRequest,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> PathResponse:
    max_h = body.max_hops
    if body.rel_types:
        inner = "|".join(validate_rel_type(t) for t in body.rel_types)
        rel_pat = f"[:{inner}*..{max_h}]"
    else:
        rel_pat = f"[*..{max_h}]"

    q = f"""
    MATCH (a), (b)
    WHERE elementId(a) = $s AND elementId(b) = $t
    MATCH p = shortestPath((a)-{rel_pat}-(b))
    RETURN p
    """
    rec = session.run(
        q,
        s=body.start_node_element_id,
        t=body.end_node_element_id,
    ).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="No path found or endpoint missing.")
    path = rec["p"]
    nodes = [NodeResponse(**node_dict(n)) for n in path.nodes]
    rels = []
    for r in path.relationships:
        rels.append(
            RelationshipResponse(
                **relationship_dict(
                    r,
                    start_element_id=r.start_node.element_id,
                    end_element_id=r.end_node.element_id,
                )
            )
        )
    return PathResponse(nodes=nodes, relationships=rels)


@router.post("/pattern", response_model=PathResponse)
def pattern_search(
    body: PatternSearchRequest,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> PathResponse:
    if body.min_hops > body.max_hops:
        raise HTTPException(status_code=400, detail="min_hops cannot exceed max_hops.")

    if body.direction == "out":
        arrow = f"-[*{body.min_hops}..{body.max_hops}]->"
    elif body.direction == "in":
        arrow = f"<-[*{body.min_hops}..{body.max_hops}]-"
    else:
        arrow = f"-[*{body.min_hops}..{body.max_hops}]-"

    apply_lbl = body.node_label is not None
    lbl = body.node_label or ""
    if apply_lbl:
        from app.cypher_utils import validate_label

        validate_label(lbl)

    q = f"""
    MATCH (anchor) WHERE elementId(anchor) = $aid
    MATCH p = (anchor){arrow}(m)
    WHERE $apply_lbl = false OR $lbl IN labels(m)
    WITH collect(DISTINCT m) + [anchor] AS alln
    UNWIND alln AS n
    WITH collect(DISTINCT n) AS node_set
    OPTIONAL MATCH (a)-[r]->(b)
    WHERE a IN node_set AND b IN node_set
    RETURN node_set AS nodes, collect(DISTINCT r) AS rels
    """
    rec = session.run(
        q,
        aid=body.anchor_element_id,
        apply_lbl=apply_lbl,
        lbl=lbl,
    ).single()
    if rec is None:
        anchor_row = session.run(
            "MATCH (a) WHERE elementId(a) = $aid RETURN a AS n",
            aid=body.anchor_element_id,
        ).single()
        if anchor_row is None:
            raise HTTPException(status_code=404, detail="Anchor not found.")
        return PathResponse(
            nodes=[NodeResponse(**node_dict(anchor_row["n"]))],
            relationships=[],
        )

    nodes_raw = [x for x in (rec["nodes"] or []) if x is not None]
    rels_raw = [x for x in (rec["rels"] or []) if x is not None]

    if not nodes_raw:
        raise HTTPException(status_code=404, detail="Anchor not found.")

    node_out = [NodeResponse(**node_dict(n)) for n in nodes_raw]
    rel_out: list[RelationshipResponse] = []
    for r in rels_raw:
        rel_out.append(
            RelationshipResponse(
                **relationship_dict(
                    r,
                    start_element_id=r.start_node.element_id,
                    end_element_id=r.end_node.element_id,
                )
            )
        )

    return PathResponse(nodes=node_out, relationships=rel_out)
