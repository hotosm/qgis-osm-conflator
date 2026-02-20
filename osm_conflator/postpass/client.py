"""HTTP wrapper for PostPass extraction calls."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .query_builder import BBox, build_simple_query

DEFAULT_POSTPASS_ENDPOINT = "https://postpass.geofabrik.de/api/0.2/interpreter"


class PostpassClientError(RuntimeError):
    """Raised when a PostPass request fails or returns invalid data."""


class PostpassClient:
    """Small HTTP wrapper around a PostPass SQL interpreter endpoint."""

    def __init__(self, endpoint: str = DEFAULT_POSTPASS_ENDPOINT, timeout: int = 60):
        """Initialise a PostPass client."""
        self.endpoint = endpoint
        self.timeout = timeout

    def run_sql(self, sql: str) -> dict[str, Any]:
        """Execute SQL against PostPass and return parsed GeoJSON."""
        if not self.endpoint:
            raise PostpassClientError("PostPass endpoint is required.")
        if not sql or not sql.strip():
            raise PostpassClientError("SQL query is required.")

        body = urlencode({"data": sql}).encode("utf-8")
        request = Request(self.endpoint, data=body, method="POST")

        try:
            with urlopen(request, timeout=self.timeout) as resp:
                raw = resp.read()
        except Exception as exc:  # noqa: BLE001
            raise PostpassClientError(f"HTTP request failed: {exc}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise PostpassClientError("PostPass response was not valid JSON.") from exc

        if not isinstance(payload, dict):
            raise PostpassClientError("PostPass response must be a GeoJSON object.")
        return payload

    def extract_buildings(self, bbox: BBox) -> dict[str, Any]:
        """Extract OSM buildings in a bbox from the PostPass point/polygon view."""
        sql = build_simple_query(
            table="postpass_pointpolygon",
            bbox=bbox,
            columns=[],
            tag_key="building",
            tag_values=["yes"],
        )
        return self.run_sql(sql)
