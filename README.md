# QGIS OSM Conflator

A tool with similar functionalities to JOSM for OpenStreetMap data conflation (merging).

## Why do we need this

- QGIS is awesome. It has a lot of conflation logic already built in,
  particularly if using an attached PostGIS instance too.
- JOSM is also great and has a large community. This plugin isn't intended
  to entirely replace JOSM, but instead to do one thing well: taking the
  existing data in OpenStreeMap and attempting to merge that with a user provided
  dataset (ideally also taken from an OSM snapshot).
- In the end, we can have some simple automated conflation, but primarily
  a manual conflation workflow (allowing users to accept or reject changes
  to OSM data).

## Building and Releasing

This plugin uses [qgis-plugin-ci](https://github.com/opengisch/qgis-plugin-ci) for automated building and releasing.

### Automated Release (Recommended)

Releases are handled automatically by GitHub Actions when you create a release on GitHub. The workflow will:

- Build the plugin package
- Upload it to the QGIS Plugin Repository
- Create a GitHub release

To release:

1. Update the version in `pyproject.toml`
2. Update the version in `osm-conflator/metadata.txt`
3. Create a git tag: `git tag 0.1.0` (matching the version)
4. Push the tag: `git push origin 0.1.0`
5. Create a GitHub release from the tag

### Local Building

For local testing, you can use qgis-plugin-ci directly:

```bash
uv sync
uv run qgis-plugin-ci <version_number>
```

## Linting

```bash
uv sync
uv run ruff format
uv run ruff check
```
