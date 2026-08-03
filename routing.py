# -*- coding: utf-8 -*-
"""
Valhalla drive-time (isochrone) client for the US Demographic Reports plugin.

Fetches drive-time isochrone polygons from a Valhalla routing server and returns
them as QGIS geometries (EPSG:4326), ready to feed straight into
SpatialProcessor.aggregate_demographics (which accepts any analysis geometry).

Fair-use / good-citizen behaviour toward the public FOSSGIS demo server:
  - every request is identified with an X-Client-Id header
  - a process-wide client-side throttle guarantees the plugin never issues more
    than one routing request per second (no bursts, no parallel isochrone calls)

The routing server URL is supplied by the caller (read from a user setting). The
public/open-source build ships with no default server; each user configures their
own (or opts in to the public server) - see the plugin README.
"""

import json
import time
import urllib.request
import urllib.error

from qgis.core import QgsGeometry, QgsPointXY

# Identifies this application to the routing server, as published apps are asked to do.
CLIENT_ID = "retailgravity-qgis-demographic-reports"

# Minimum seconds between outbound routing requests (fair-use: <= 1 request/second).
_MIN_REQUEST_INTERVAL = 1.0
# Process-wide timestamp of the last request, shared across every call.
_last_request_time = 0.0


class RoutingError(Exception):
    """Raised when a drive-time isochrone cannot be retrieved.

    The message is written to be shown directly to the user.
    """
    pass


def _throttle():
    """Block until at least _MIN_REQUEST_INTERVAL has passed since the last request."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def get_drive_time_isochrones(server_url, lon, lat, minutes_list,
                              costing="auto", timeout=30):
    """
    Request cumulative drive-time isochrone polygons from a Valhalla server.

    Args:
        server_url: str - Base URL of the Valhalla server
            (e.g. https://valhalla1.openstreetmap.de)
        lon: float - Origin longitude in WGS84 (EPSG:4326) degrees
        lat: float - Origin latitude in WGS84 (EPSG:4326) degrees
        minutes_list: list[float] - Up to 3 drive times in minutes, ascending
        costing: str - Valhalla costing model ("auto" = driving)
        timeout: int - Request timeout in seconds

    Returns:
        list[tuple] - (minutes, QgsGeometry) per contour, ascending by minutes.
            Geometries are in EPSG:4326 (lon/lat). Each drive-time polygon is the
            full cumulative area reachable within that many minutes.

    Raises:
        RoutingError - with a user-facing message on any failure.
    """
    if not server_url or not server_url.strip():
        raise RoutingError(
            "No drive-time routing server is configured. Enter a Valhalla server "
            "URL in the 'Drive-time server' field (see the plugin README for "
            "options, including running your own)."
        )

    base = server_url.strip().rstrip("/")
    url = base + "/isochrone"

    payload = {
        "locations": [{"lat": float(lat), "lon": float(lon)}],
        "costing": costing,
        "contours": [{"time": float(m)} for m in minutes_list],
        "polygons": True,
        "denoise": 1.0,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("X-Client-Id", CLIENT_ID)
    req.add_header("User-Agent", CLIENT_ID)

    _throttle()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise RoutingError(
            f"The routing server returned an error (HTTP {e.code}) for the "
            f"drive-time request. {detail}".strip()
        )
    except urllib.error.URLError as e:
        raise RoutingError(
            f"Could not reach the routing server at {base}. Check your internet "
            f"connection and the server URL. ({e.reason})"
        )
    except Exception as e:
        raise RoutingError(f"Unexpected error contacting the routing server: {e}")

    try:
        collection = json.loads(raw)
    except ValueError:
        raise RoutingError(
            "The routing server returned a response that could not be parsed."
        )

    features = collection.get("features") if isinstance(collection, dict) else None
    if not features:
        raise RoutingError(
            "The routing server did not return any drive-time areas for this "
            "location. The point may be outside the routable road network."
        )

    results = []
    for feature in features:
        props = feature.get("properties", {}) or {}
        geom = _geometry_from_geojson(feature.get("geometry"))
        if geom is None or geom.isEmpty():
            continue
        try:
            minutes = float(props.get("contour"))
        except (TypeError, ValueError):
            minutes = None
        results.append((minutes, geom))

    if not results:
        raise RoutingError(
            "The routing server response contained no usable drive-time polygons."
        )

    # Ascending by minutes so report columns read small -> large (like radii).
    results.sort(key=lambda item: (item[0] is None, item[0]))
    return results


def _geometry_from_geojson(geom_dict):
    """Build a QgsGeometry (EPSG:4326) from a GeoJSON Polygon/MultiPolygon dict."""
    if not geom_dict:
        return None
    geom_type = geom_dict.get("type")
    coords = geom_dict.get("coordinates")
    if not coords:
        return None

    def ring_to_points(ring):
        return [QgsPointXY(float(pt[0]), float(pt[1])) for pt in ring]

    if geom_type == "Polygon":
        return QgsGeometry.fromPolygonXY([ring_to_points(r) for r in coords])
    if geom_type == "MultiPolygon":
        return QgsGeometry.fromMultiPolygonXY(
            [[ring_to_points(r) for r in polygon] for polygon in coords]
        )
    return None
