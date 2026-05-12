# Graph engine

Course project: a **Neo4j** graph store behind a **FastAPI** REST API (node and relationship CRUD, search, JSON/GraphML import and export) and a **wxPython** desktop client.

## Requirements

- Docker with Compose (for Neo4j + API), or a local Neo4j 5 instance
- Python 3.12+ for the API and optional GUI

## API (Docker)

```bash
docker compose up --build
```

- OpenAPI UI: `http://localhost:8000/docs`
- Neo4j Browser (default image): `http://localhost:7474` (user `neo4j`, password from `.env` / `.env.example`)

## Desktop client

```bash
pip install -r requirements.txt -r requirements-gui.txt
python -m gui
```

The **Graph** menu supports importing `.json` / `.graphml` files and exporting to `.json`, `.graphml`, or `.gexf`, with a short result dialog after import. Two plot modes: a normal window with a summary line, or a **minimal fullscreen** view (Escape closes).

Connection settings: `%USERPROFILE%\.graph_engine_gui.json` (Linux/macOS: `$HOME/.graph_engine_gui.json`).

## Example dataset

Pre-built pip dependency graph: `examples/README.md` and `examples/pip_dependency_graph.json`.

```bash
curl -s -X POST "http://127.0.0.1:8000/graph/import?mode=replace" -H "Content-Type: application/json" -d @examples/pip_dependency_graph.json
```

Regenerate:

```bash
python scripts/build_pip_graph.py -o examples/pip_dependency_graph.json
```

## Local API (without Docker API image)

```bash
pip install -r requirements.txt
set NEO4J_URI=bolt://localhost:7687
set NEO4J_PASSWORD=changeme
uvicorn app.main:app --reload --port 8000
```

Run Neo4j separately if needed (`docker compose up neo4j`).

## Licence

Add your institution’s licence or copyright line here.
