from typing import Any

from fastapi import APIRouter, HTTPException
from neo4j.exceptions import ClientError

from app import db
from app.schemas import DatabaseCreate

router = APIRouter()


def _jsonable_record(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in record.items():
        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@router.get("/databases")
def list_databases() -> list[dict[str, Any]]:
    try:
        with db.get_driver().session(database="system") as s:
            result = s.run("SHOW DATABASES")
            return [_jsonable_record(dict(r)) for r in result]
    except ClientError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not list databases (Neo4j system database): {e}",
        ) from e


@router.post("/databases", status_code=201)
def create_database(body: DatabaseCreate) -> dict[str, Any]:
    quoted = f"`{body.name}`"
    wait_clause = " WAIT" if body.wait else ""
    try:
        with db.get_driver().session(database="system") as s:
            s.run(f"CREATE DATABASE {quoted} IF NOT EXISTS{wait_clause}").consume()
        return {"name": body.name, "status": "created_or_exists"}
    except ClientError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e
