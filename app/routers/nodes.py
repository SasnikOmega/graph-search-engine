from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session
from neo4j.exceptions import ClientError

from app.cypher_utils import format_labels_cypher
from app.deps import get_neo4j_session
from app.schemas import NodeCreate, NodeResponse, NodeUpdate
from app.serialization import node_dict

router = APIRouter()


@router.get("/list", response_model=list[NodeResponse])
def list_nodes(
    session: Annotated[Session, Depends(get_neo4j_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> list[NodeResponse]:
    rows = session.run(
        "MATCH (n) RETURN n AS node SKIP $skip LIMIT $limit",
        skip=skip,
        limit=limit,
    )
    return [NodeResponse(**node_dict(r["node"])) for r in rows]


@router.post("", response_model=NodeResponse)
def create_node(
    body: NodeCreate,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> NodeResponse:
    label_part = format_labels_cypher(body.labels)
    q = f"CREATE (n:{label_part}) SET n += $props RETURN n AS node"
    rec = session.run(q, props=body.properties).single()
    if rec is None:
        raise HTTPException(status_code=500, detail="Failed to create node.")
    return NodeResponse(**node_dict(rec["node"]))


@router.get("/{element_id}", response_model=NodeResponse)
def read_node(
    element_id: str,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> NodeResponse:
    rec = session.run(
        "MATCH (n) WHERE elementId(n) = $eid RETURN n AS node",
        eid=element_id,
    ).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="Node not found.")
    return NodeResponse(**node_dict(rec["node"]))


@router.patch("/{element_id}", response_model=NodeResponse)
def update_node(
    element_id: str,
    body: NodeUpdate,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> NodeResponse:
    if body.replace:
        q = "MATCH (n) WHERE elementId(n) = $eid SET n = $props RETURN n AS node"
    else:
        q = "MATCH (n) WHERE elementId(n) = $eid SET n += $props RETURN n AS node"
    rec = session.run(q, eid=element_id, props=body.properties).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="Node not found.")
    return NodeResponse(**node_dict(rec["node"]))


@router.delete("/{element_id}", status_code=204)
def delete_node(
    element_id: str,
    session: Annotated[Session, Depends(get_neo4j_session)],
    detach: bool = Query(
        default=False,
        description="If true, delete relationships before deleting the node.",
    ),
) -> None:
    if detach:
        q = "MATCH (n) WHERE elementId(n) = $eid DETACH DELETE n RETURN 1 AS ok"
    else:
        q = "MATCH (n) WHERE elementId(n) = $eid DELETE n RETURN 1 AS ok"
    try:
        rec = session.run(q, eid=element_id).single()
    except ClientError as e:
        if not detach and "relationship" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="Node still has relationships; retry with detach=true.",
            ) from e
        raise
    if rec is None:
        raise HTTPException(status_code=404, detail="Node not found.")
