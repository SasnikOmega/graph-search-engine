from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class NodeCreate(BaseModel):
    labels: list[str] = Field(..., min_length=1)
    properties: dict[str, Any] = Field(default_factory=dict)


class NodeUpdate(BaseModel):
    properties: dict[str, Any]
    replace: bool = False


class NodeResponse(BaseModel):
    element_id: str
    labels: list[str]
    properties: dict[str, Any]


class RelationshipCreate(BaseModel):
    start_node_element_id: str
    end_node_element_id: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class RelationshipUpdate(BaseModel):
    properties: dict[str, Any]
    replace: bool = False


class RelationshipResponse(BaseModel):
    element_id: str
    type: str
    properties: dict[str, Any]
    start_node_element_id: str
    end_node_element_id: str


class NeighborItem(BaseModel):
    relationship: RelationshipResponse
    node: NodeResponse


class ShortestPathRequest(BaseModel):
    start_node_element_id: str
    end_node_element_id: str
    max_hops: int = Field(default=15, ge=1, le=50)
    rel_types: list[str] | None = None


class PathResponse(BaseModel):
    nodes: list[NodeResponse]
    relationships: list[RelationshipResponse]


class PatternSearchRequest(BaseModel):
    """Templated match: anchor node by element id, optional label filter on matched nodes."""

    anchor_element_id: str
    min_hops: int = Field(default=1, ge=1, le=20)
    max_hops: int = Field(default=2, ge=1, le=20)
    direction: Literal["out", "in", "both"] = "both"
    node_label: str | None = None


class JsonGraphNode(BaseModel):
    id: str | None = None
    labels: list[str] = Field(default_factory=lambda: ["GraphNode"])
    properties: dict[str, Any] = Field(default_factory=dict)


class JsonGraphEdge(BaseModel):
    type: str
    source: str
    target: str
    properties: dict[str, Any] = Field(default_factory=dict)


class JsonGraphDocument(BaseModel):
    """Bulk graph: nodes keyed by optional id; edges reference source/target by that id."""

    nodes: list[JsonGraphNode]
    edges: list[JsonGraphEdge]


class GraphImportMode(BaseModel):
    mode: Literal["append", "replace"] = "append"


class DatabaseCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]*$",
        description="Neo4j database name (letters, digits, underscore, hyphen).",
    )
    wait: bool = Field(
        default=True,
        description="Wait for the database to be ready before returning.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v
