"""QGIS osm-conflator Plugin."""

from osm-conflator.OSMConflatorPlugin import OSMConflatorPlugin


def classFactory(iface):  # pylint: disable=invalid-name
    """Load plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    return OSMConflatorPlugin(iface)
