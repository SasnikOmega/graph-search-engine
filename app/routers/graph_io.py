from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from neo4j import Session

from app.deps import get_neo4j_session
from app.exporters.format_export import export_gexf_bytes, export_graphml_string
from app.importers import json_graph as json_graph_importer
from app.importers.graphml import graphml_to_document
from app.schemas import JsonGraphDocument

router = APIRouter()


@router.post("/import")
def import_json_graph(
    body: JsonGraphDocument,
    session: Annotated[Session, Depends(get_neo4j_session)],
    mode: Literal["append", "replace"] = Query(
        default="append",
        description="replace clears the database before importing.",
    ),
) -> dict[str, int]:
    try:
        return json_graph_importer.import_json_graph(
            session, body, replace=(mode == "replace")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/export", response_model=JsonGraphDocument)
def export_json_graph(
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> JsonGraphDocument:
    return json_graph_importer.export_json_graph(session)


@router.get("/export/graphml")
def export_graphml(
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> Response:
    xml = export_graphml_string(session)
    return Response(
        content=xml.encode("utf-8"),
        media_type="application/xml; charset=utf-8",
    )


@router.get("/export/gexf")
def export_gexf(
    session: Annotated[Session, Depends(get_neo4j_session)],
) -> Response:
    data = export_gexf_bytes(session)
    return Response(
        content=data,
        media_type="application/gexf+xml; charset=utf-8",
    )


@router.post("/import/graphml")
def import_graphml(
    session: Annotated[Session, Depends(get_neo4j_session)],
    mode: Literal["append", "replace"] = Query(default="append"),
    xml: str = Body(..., media_type="application/xml"),
) -> dict[str, int]:
    try:
        doc = graphml_to_document(xml)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not parse GraphML: {e}"
        ) from e
    try:
        return json_graph_importer.import_json_graph(
            session, doc, replace=(mode == "replace")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
