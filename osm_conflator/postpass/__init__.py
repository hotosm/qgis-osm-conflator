"""OSM data extraction helpers using Postpass + osm2pgsql flex schema.

This module implements a tiny subset of the query-building ideas from
`hotosm/raw-data-api` (see https://github.com/hotosm/raw-data-api) against a
PostGIS database exposed through `woodpeck/postpass`
(see https://github.com/woodpeck/postpass).

The database is expected to follow the osm2pgsql flex schema used in
`postpass-ops`, with at least the following objects available:

* `postpass_point` (geom: Point)
* `postpass_line` (geom: MultiLineString)
* `postpass_polygon` (geom: MultiPolygon)
* combined geometry views like `postpass_pointlinepolygon`

Tags are stored in a `jsonb` column named ``tags``; we use ``tags->>'key'`` in
WHERE clauses, similar to the examples in the Postpass README and the
raw-data-api prompts.
"""

from __future__ import annotations

from typing import Sequence, Tuple

BBox = Tuple[float, float, float, float]


def _bbox_where(bbox: BBox, geom_column: str = "geom") -> str:
    """Return SQL snippet restricting a geometry column to a WGS84 bbox."""
    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        f"{geom_column} && "
        "ST_SetSRID("
        "ST_MakeBox2D("
        f"ST_MakePoint({min_lon}, {min_lat}),"
        f"ST_MakePoint({max_lon}, {max_lat})"
        "), 4326)"
    )


def _tag_where(tag_key: str | None, tag_value: str | None) -> str | None:
    """Return SQL snippet for a simple key[/=value] filter on the tags jsonb."""
    if not tag_key:
        return None
    if tag_value is None or tag_value == "":
        # Only check presence
        return f"tags ? '{tag_key}'"
    return f"tags->>'{tag_key}' = '{tag_value}'"


def build_simple_bbox_query(
    *,
    table_name: str,
    bbox: BBox,
    tag_key: str | None = None,
    tag_value: str | None = None,
    select_columns: Sequence[str] | None = None,
) -> str:
    """Build a minimal SQL SELECT for Postpass over the flex schema.

    Parameters
    ----------
    table_name:
        Name of the table or view to query (e.g. ``postpass_point``).
    bbox:
        A (min_lon, min_lat, max_lon, max_lat) bounding box in EPSG:4326.
    tag_key, tag_value:
        Optional OSM tag filter. If only ``tag_key`` is provided we require the
        tag to be present. If both key and value are provided we require exact
        equality on the JSONB field.
    select_columns:
        Optional list of additional columns to fetch besides ``geom``.
        Defaults to ``['tags']`` for convenience.
    """
    if not table_name:
        raise ValueError("table_name is required for Postpass query.")

    if select_columns is None:
        select_columns = ["tags"]

    # Geometry is always returned; Postpass by default responds with GeoJSON
    # when a geometry column is present, see woodpeck/postpass docs:
    # https://github.com/woodpeck/postpass
    columns_sql = ", ".join([*select_columns, "geom"])

    where_clauses = [_bbox_where(bbox)]
    tag_clause = _tag_where(tag_key, tag_value)
    if tag_clause:
        where_clauses.append(tag_clause)

    where_sql = " AND ".join(where_clauses)

    # Postpass requires that the query not end with a semicolon in many of the
    # examples, especially when embedded in URL-encoded requests or curl
    # commands. We follow that convention here.
    sql = f"SELECT {columns_sql} FROM {table_name} WHERE {where_sql}"
    return sql
