# Example graph data

## `pip_dependency_graph.json`

This file was produced from **installed packages in one Python environment** (see `../scripts/build_pip_graph.py`). It is meant as a ready-made demo graph:

- **Nodes** (`:Module`): `display_name`, `version`, `summary`
- **Edges** (`REQUIRES`): dependent module → required module (only when the target is also installed)

### Load into Neo4j via API

With the API running (default `http://127.0.0.1:8000`):

```bash
curl -s -X POST "http://127.0.0.1:8000/graph/import?mode=replace" ^
  -H "Content-Type: application/json" ^
  -d @examples/pip_dependency_graph.json
```

### Example Cypher (most depended-on modules)

```cypher
MATCH ()-[r:REQUIRES]->(m:Module)
RETURN m.display_name AS module, count(r) AS dependents
ORDER BY dependents DESC
LIMIT 25
```

Regenerate the file from your machine:

```bash
python scripts/build_pip_graph.py -o examples/pip_dependency_graph.json
```
