"""Primary dialog for Postpass-based OSM data extraction."""

import json
import tempfile
from typing import Optional

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .postpass.client import PostpassClient, PostpassClientError
from .postpass.query_builder import build_simple_query


class OSMConflatorDialog(QDialog):
    """Dialog to construct a simple Postpass query and load results."""

    def __init__(self, iface, parent=None):
        """Initialise dialog."""
        super().__init__(parent)
        self.iface = iface

        self.setWindowTitle("OSM Conflator – Postpass Extraction")
        self.setMinimumWidth(450)

        # Endpoint configuration
        self.endpointEdit = QLineEdit(
            "https://postpass.geofabrik.de/api/0.2/interpreter"
        )

        # Geometry/table selector (following postpass / raw-data-api schema)
        self.geomCombo = QComboBox()
        self.geomCombo.addItem("Points", "postpass_point")
        self.geomCombo.addItem("Lines", "postpass_line")
        self.geomCombo.addItem("Polygons", "postpass_polygon")
        self.geomCombo.addItem("Point + Polygon (view)", "postpass_pointpolygon")
        self.geomCombo.addItem("Point + Line (view)", "postpass_pointline")
        self.geomCombo.addItem("Line + Polygon (view)", "postpass_linepolygon")
        self.geomCombo.addItem(
            "Point + Line + Polygon (view)", "postpass_pointlinepolygon"
        )

        # Bounding box (minlon,minlat,maxlon,maxlat) – simple text field for now
        self.bboxEdit = QLineEdit()
        self.bboxEdit.setPlaceholderText("min_lon,min_lat,max_lon,max_lat")

        # Simple tag filter key/value (using jsonb tags like in raw-data-api
        # https://github.com/hotosm/raw-data-api)
        self.tagKeyEdit = QLineEdit()
        self.tagKeyEdit.setPlaceholderText("e.g. amenity")
        self.tagValueEdit = QLineEdit()
        self.tagValueEdit.setPlaceholderText("e.g. fast_food")

        # Layer name
        self.layerNameEdit = QLineEdit()
        self.layerNameEdit.setPlaceholderText("Optional; defaults to table + filter")

        # Action buttons
        self.runButton = QPushButton("Run query and load layer")
        self.runButton.setDefault(True)

        # Status label
        self.statusLabel = QLabel("")
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setStyleSheet("color: red")

        # Layout
        form = QFormLayout()
        form.addRow("Postpass endpoint:", self.endpointEdit)
        form.addRow("Geometry / table:", self.geomCombo)

        bbox_row = QHBoxLayout()
        bbox_row.addWidget(self.bboxEdit)
        form.addRow("Bounding box (WGS84):", bbox_row)

        tag_row = QHBoxLayout()
        tag_row.addWidget(self.tagKeyEdit)
        tag_row.addWidget(self.tagValueEdit)
        form.addRow("Tag filter (key / value):", tag_row)

        form.addRow("Layer name:", self.layerNameEdit)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.runButton, alignment=Qt.AlignRight)
        self.setLayout(layout)

        # Connections
        self.runButton.clicked.connect(self._on_run_clicked)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_bbox(self) -> Optional[tuple]:
        text = self.bboxEdit.text().strip()
        if not text:
            self._set_error(
                "Please enter a bounding box in the form "
                "min_lon,min_lat,max_lon,max_lat."
            )
            return None
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 4:
            self._set_error(
                "Bounding box must have exactly four comma-separated values."
            )
            return None
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, parts)
        except ValueError:
            self._set_error("Bounding box values must be numeric.")
            return None
        if min_lon >= max_lon or min_lat >= max_lat:
            self._set_error("Bounding box min values must be less than max values.")
            return None
        return min_lon, min_lat, max_lon, max_lat

    def _set_error(self, message: str) -> None:
        self.statusLabel.setStyleSheet("color: red")
        self.statusLabel.setText(message)
        QgsMessageLog.logMessage(message, "OSM Conflator", level=Qgis.Warning)

    def _set_success(self, message: str) -> None:
        self.statusLabel.setStyleSheet("color: green")
        self.statusLabel.setText(message)
        QgsMessageLog.logMessage(message, "OSM Conflator", level=Qgis.Info)

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        """Validate input, build SQL and execute request against Postpass."""
        self.statusLabel.clear()

        bbox = self._parse_bbox()
        if bbox is None:
            return

        table_name = self.geomCombo.currentData()
        tag_key = self.tagKeyEdit.text().strip() or None
        tag_value = self.tagValueEdit.text().strip() or None

        endpoint = self.endpointEdit.text().strip()
        if not endpoint:
            self._set_error("Please enter a Postpass endpoint URL.")
            return
        client = PostpassClient(endpoint=endpoint)
        try:
            # MVP default: buildings extraction when no explicit tag filter is provided.
            if not tag_key:
                geojson = client.extract_buildings(bbox)
                tag_key = "building"
                tag_value = "yes"
                table_name = "postpass_pointpolygon"
            else:
                sql = build_simple_query(
                    table=table_name,
                    bbox=bbox,
                    columns=[],  # keep default osm_id, tags, geom
                    tag_key=tag_key,
                    tag_values=[tag_value] if tag_value else [],
                )
                geojson = client.run_sql(sql)
        except (ValueError, PostpassClientError) as exc:
            self._set_error(str(exc))
            return

        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".geojson", prefix="osm_conflator_postpass_", delete=False
            )
            with tmp:
                tmp.write(json.dumps(geojson).encode("utf-8"))
            geojson_path = tmp.name
        except Exception as exc:  # noqa: BLE001
            self._set_error(f"Failed to write temporary GeoJSON file: {exc}")
            return

        layer_name = self.layerNameEdit.text().strip()
        if not layer_name:
            if tag_key and tag_value:
                layer_name = f"{table_name} {tag_key}={tag_value}"
            elif tag_key:
                layer_name = f"{table_name} {tag_key}"
            else:
                layer_name = table_name

        layer = QgsVectorLayer(geojson_path, layer_name, "ogr")
        if not layer.isValid():
            self._set_error("Loaded layer from Postpass response is not valid.")
            return

        QgsProject.instance().addMapLayer(layer)
        self._set_success(f"Loaded layer '{layer_name}' from Postpass.")
