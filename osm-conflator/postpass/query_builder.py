"""Minimal PostGIS query builder inspired by HOTOSM raw-data-api.

This reimplements a *small* subset of the logic from
`src/query_builder/builder.py` in HOT's raw-data-api project
(see https://github.com/hotosm/raw-data-api/blob/master/src/query_builder/builder.py)
but is designed to be:

* stand-alone (no QGIS, no HTTP, no database connection),
* lightweight (only the bits needed by this QGIS plugin), and
* easy to extend later if we need more of raw-data-api's features.

The resulting SQL is suitable for use with woodpeck/postpass, which
exposes a PostGIS-enabled PostgreSQL database over HTTP:
https://github.com/woodpeck/postpass
"""

from typing import Optional, Sequence, Tuple


BBox = Tuple[float, float, float, float]


def create_column_filter(
    columns: Sequence[str],
    use_centroid: bool = False,
) -> str:
    """Generate the SELECT column list.

    This loosely follows ``create_column_filter`` in raw-data-api's builder
    module, but is simplified for our use case:

    * Always includes ``osm_id`` and ``tags``.
    * Adds per-tag projection columns for any explicit ``columns`` values
      (e.g. ``tags->>'amenity' as "amenity"``).
    * Always returns a geometry column named ``geom`` (either centroid or
      the original geometry).
    """

    select_cols = ["osm_id", "tags"]

    for col in columns:
        col = col.strip()
        if not col or col == "*":
            # ``*`` is treated as "just keep tags" which we already do.
            continue
        select_cols.append(f"tags->>'{col}' as \"{col}\"")

    geom_expr = "ST_Centroid(geom) as geom" if use_centroid else "geom"
    select_cols.append(geom_expr)

    return ", ".join(select_cols)


def create_bbox_filter(bbox: BBox, geom_col: str = "geom") -> str:
    """Return a PostGIS bbox filter using ST_MakeBox2D/SetSRID.

    Matches the style used in the Postpass examples, e.g.:

        geom && ST_SetSRID(
            ST_MakeBox2D(ST_MakePoint(min_lon, min_lat),
                         ST_MakePoint(max_lon, max_lat)),
            4326
        )
    """

    min_lon, min_lat, max_lon, max_lat = bbox
    return (
        f"{geom_col} && "
        "ST_SetSRID("
        "ST_MakeBox2D("
        f"ST_MakePoint({min_lon}, {min_lat}),"
        f"ST_MakePoint({max_lon}, {max_lat})"
        "), 4326)"
    )


def create_tag_filter(key: str, values: Sequence[str]) -> str:
    """Return a simple tag filter over the ``tags`` jsonb column.

    This closely mirrors ``create_tag_sql_logic`` in raw-data-api:

    * no values   → ``tags ? 'key'`` (presence only),
    * one value   → ``tags->>'key' = 'value'``,
    * many values → ``tags->>'key' IN ('v1','v2',...)``,
    * single value of ``"*"``
      (wildcard) is treated as "presence only", like raw-data-api.
    """

    cleaned = [v for v in (values or []) if v is not None and v != ""]
    if len(cleaned) == 1 and cleaned[0] == "*":
        cleaned = []

    if not cleaned:
        return f"tags ? '{key.strip()}'"

    if len(cleaned) == 1:
        return f"tags->>'{key.strip()}' = '{cleaned[0].strip()}'"

    in_list = ", ".join(f"'{v.strip()}'" for v in cleaned)
    return f"tags->>'{key.strip()}' IN ({in_list})"


def build_simple_query(
    *,
    table: str,
    bbox: BBox,
    columns: Optional[Sequence[str]] = None,
    tag_key: Optional[str] = None,
    tag_values: Optional[Sequence[str]] = None,
    use_centroid: bool = False,
) -> str:
    """Build a minimal extraction query suitable for Postpass.

    Parameters
    ----------
    table:
        Table or view name, e.g. ``postpass_point``.
    bbox:
        (min_lon, min_lat, max_lon, max_lat) in EPSG:4326.
    columns:
        Optional additional tag keys to project as individual columns.
    tag_key, tag_values:
        Optional tag filter: see :func:`create_tag_filter`.
    use_centroid:
        If True, returns ``ST_Centroid(geom) as geom`` instead of full geometry.

    The returned SQL intentionally **does not** end in a semicolon to match
    the usage patterns in both Postpass and raw-data-api.
    """

    if not table:
        raise ValueError("table is required for Postpass query.")

    select_sql = create_column_filter(columns or [], use_centroid=use_centroid)
    where_clauses = [create_bbox_filter(bbox)]

    if tag_key:
        where_clauses.append(create_tag_filter(tag_key, tag_values or []))

    where_sql = " AND ".join(where_clauses)
    return f"SELECT {select_sql} FROM {table} WHERE {where_sql}"


