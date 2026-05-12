from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from neo4j import Session

from app import db
from app.deps import get_neo4j_session
from app.routers import admin, graph_io, nodes, relationships, search


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.verify_connectivity()
    yield
    db.close_driver()


app = FastAPI(
    title="Graph engine API",
    description="CRUD on Neo4j nodes and relationships, minimal graph search, JSON/GraphML import.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health(session: Session = Depends(get_neo4j_session)) -> dict[str, str]:
    session.run("RETURN 1 AS ok").consume()
    return {"status": "ok"}


app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(relationships.router, prefix="/relationships", tags=["relationships"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(graph_io.router, prefix="/graph", tags=["graph"])
