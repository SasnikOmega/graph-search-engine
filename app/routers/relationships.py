from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import Session

from app.cypher_utils import validate_rel_type
from app.deps import get_neo4j_session
from app.schemas import RelationshipCreate, RelationshipResponse, RelationshipUpdate
from app.serialization import relationship_dict

router = APIRouter()


def _rel_row(rec) -> RelationshipResponse:
    r = rec["r"]
    return RelationshipResponse(
        **relationship_dict(
            r,
            start_element_id=rec["sid"],
            end_element_id=rec["eid"],
        )
    )


@router.get("/list", response_model=list[RelationshipResponse])
def list_relationships(
    session: Annotated[Session, Depends(get_neo4j_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
) -> list[RelationshipResponse]:
    rows = session.run(
        """
        MATCH ()-[r]->()
        RETURN r,
               elementId(startNode(r)) AS sid,
               elementId(endNode(r)) AS eid
        SKIP $skip LIMIT $limit
        """,
        skip=skip,
        limit=limit,
    )
    return [_rel_row(r) for r in rows]


@router.post("", response_model=RelationshipResponse)
def create_relationship(
    body: RelationshipCreate,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> RelationshipResponse:
    rel = validate_rel_type(body.type)
    q = f"""
    MATCH (a) WHERE elementId(a) = $sid
    MATCH (b) WHERE elementId(b) = $eid
    CREATE (a)-[r:{rel}]->(b)
    SET r += $props
    RETURN r,
           elementId(startNode(r)) AS sid,
           elementId(endNode(r)) AS eid
    """
    rec = session.run(
        q,
        sid=body.start_node_element_id,
        eid=body.end_node_element_id,
        props=body.properties,
    ).single()
    if rec is None:
        raise HTTPException(
            status_code=400,
            detail="Could not create relationship (missing endpoint node?).",
        )
    return _rel_row(rec)


@router.get("/{element_id}", response_model=RelationshipResponse)
def read_relationship(
    element_id: str,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> RelationshipResponse:
    rec = session.run(
        """
        MATCH ()-[r]->()
        WHERE elementId(r) = $eid
        RETURN r,
               elementId(startNode(r)) AS sid,
               elementId(endNode(r)) AS eid
        """,
        eid=element_id,
    ).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    return _rel_row(rec)


@router.patch("/{element_id}", response_model=RelationshipResponse)
def update_relationship(
    element_id: str,
    body: RelationshipUpdate,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> RelationshipResponse:
    if body.replace:
        q = """
        MATCH ()-[r]->()
        WHERE elementId(r) = $eid
        SET r = $props
        RETURN r,
               elementId(startNode(r)) AS sid,
               elementId(endNode(r)) AS eid
        """
    else:
        q = """
        MATCH ()-[r]->()
        WHERE elementId(r) = $eid
        SET r += $props
        RETURN r,
               elementId(startNode(r)) AS sid,
               elementId(endNode(r)) AS eid
        """
    rec = session.run(q, eid=element_id, props=body.properties).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    return _rel_row(rec)


@router.delete("/{element_id}", status_code=204)
def delete_relationship(
    element_id: str,
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> None:
    rec = session.run(
        """
        MATCH ()-[r]->()
        WHERE elementId(r) = $eid
        DELETE r
        RETURN 1 AS ok
        """,
        eid=element_id,
    ).single()
    if rec is None:
        raise HTTPException(status_code=404, detail="Relationship not found.")
