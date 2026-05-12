import re
from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, Query
from neo4j import Session

from app import db

_DB_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def get_database(
    database: str = Query(
        "neo4j",
        description="Target Neo4j database for this request.",
    ),
    x_database: str | None = Header(default=None, alias="X-Database"),
) -> str:
    name = (x_database or database or "neo4j").strip()
    if not _DB_NAME.match(name):
        raise HTTPException(
            status_code=400,
            detail="Invalid database name (use letters, digits, underscore, hyphen).",
        )
    return name


def get_neo4j_session(
    database: str = Depends(get_database),
) -> Generator[Session, None, None]:
    with db.get_driver().session(database=database) as session:
        yield session
