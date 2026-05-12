# Graph engine

Course project: a **Neo4j** graph store behind a **FastAPI** REST API (node and relationship CRUD, search, JSON/GraphML import) and a small **wxPython** desktop client.

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

Connection settings are saved under `%USERPROFILE%\.graph_engine_gui.json` (Linux/macOS: `$HOME/.graph_engine_gui.json`).

## Example dataset

Pre-built **pip dependency** graph (modules as `:Module`, edges `REQUIRES`): see `examples/README.md` and `examples/pip_dependency_graph.json`. Import:

```bash
curl -s -X POST "http://127.0.0.1:8000/graph/import?mode=replace" -H "Content-Type: application/json" -d @examples/pip_dependency_graph.json
```

Regenerate from the current Python environment:

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
