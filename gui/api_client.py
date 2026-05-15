"""HTTP client for the graph engine REST API."""

from __future__ import annotations

import json
from typing import Any

import httpx


class ApiError(Exception):
    """Raised when the server returns an error or the request cannot complete."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _detail_from_response(r: httpx.Response) -> str:
    try:
        data = r.json()
        d = data.get("detail")
        if isinstance(d, list):
            return "\n".join(
                str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d
            )
        return str(d)
    except (json.JSONDecodeError, ValueError, TypeError):
        return (r.text or r.reason_phrase or "").strip() or f"HTTP {r.status_code}"


class ApiClient:
    def __init__(
        self,
        base_url: str,
        database: str = "neo4j",
        timeout: float = 45.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.database = database
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def set_database(self, name: str) -> None:
        self.database = name.strip() or "neo4j"

    def close(self) -> None:
        self._client.close()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _db_headers(self) -> dict[str, str]:
        return {"X-Database": self.database}

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", None) or {})
        headers.update(self._db_headers())
        if "json" in kwargs and kwargs["json"] is not None:
            headers.setdefault("Content-Type", "application/json")
        try:
            r = self._client.request(method, self._url(path), headers=headers, **kwargs)
        except httpx.ConnectError as e:
            raise ApiError(
                "Не удалось подключиться к серверу. Убедитесь, что API запущен "
                "и в параметрах подключения указан верный адрес.\n\n"
                f"Подробности: {e}",
            ) from e
        except httpx.TimeoutException as e:
            raise ApiError(f"Превышено время ожидания ответа: {e}") from e
        except httpx.RequestError as e:
            raise ApiError(f"Сетевая ошибка: {e}") from e

        if r.is_error:
            raise ApiError(
                _detail_from_response(r),
                status_code=r.status_code,
                body=(r.text or "")[:4000],
            )
        return r

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health").json()

    def list_databases(self) -> list[dict[str, Any]]:
        return self._request("GET", "/admin/databases").json()

    def create_database(self, name: str, *, wait: bool = True) -> dict[str, Any]:
        r = self._request("POST", "/admin/databases", json={"name": name, "wait": wait})
        return r.json() if r.content else {}

    def nodes_list(self, *, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/nodes/list",
            params={"skip": skip, "limit": limit},
        ).json()

    def node_get(self, element_id: str) -> dict[str, Any]:
        return self._request("GET", f"/nodes/{element_id}").json()

    def node_create(self, labels: list[str], properties: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            "/nodes",
            json={"labels": labels, "properties": properties},
        ).json()

    def node_update(
        self,
        element_id: str,
        properties: dict[str, Any],
        *,
        replace: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/nodes/{element_id}",
            json={"properties": properties, "replace": replace},
        ).json()

    def node_delete(self, element_id: str, *, detach: bool = False) -> None:
        self._request(
            "DELETE",
            f"/nodes/{element_id}",
            params={"detach": detach},
        )

    def rels_list(self, *, skip: int = 0, limit: int = 200) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/relationships/list",
            params={"skip": skip, "limit": limit},
        ).json()

    def rel_create(
        self,
        start_id: str,
        end_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/relationships",
            json={
                "start_node_element_id": start_id,
                "end_node_element_id": end_id,
                "type": rel_type,
                "properties": properties or {},
            },
        ).json()

    def rel_delete(self, element_id: str) -> None:
        self._request("DELETE", f"/relationships/{element_id}")

    def graph_export(self) -> dict[str, Any]:
        return self._request("GET", "/graph/export").json()

    def graph_import_json(self, document: dict[str, Any], *, mode: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/graph/import",
            params={"mode": mode},
            json=document,
        ).json()

    def graph_import_graphml(self, xml_text: str, *, mode: str) -> dict[str, Any]:
        body = xml_text.encode("utf-8")
        return self._request(
            "POST",
            "/graph/import/graphml",
            params={"mode": mode},
            content=body,
            headers={"Content-Type": "application/xml; charset=utf-8"},
        ).json()

    def graph_export_bytes(self, fmt: str) -> bytes:
        fmt = fmt.lower().lstrip(".")
        if fmt == "json":
            return self._request("GET", "/graph/export").content
        if fmt == "graphml":
            return self._request("GET", "/graph/export/graphml").content
        if fmt == "gexf":
            return self._request("GET", "/graph/export/gexf").content
        raise ApiError(f"Неподдерживаемый формат экспорта: {fmt!r}. Допустимы json, graphml, gexf.")
