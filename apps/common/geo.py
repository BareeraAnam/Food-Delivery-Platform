"""
Pure-Python geolocation helpers. Using Haversine formula means this project
needs no PostGIS/GDAL system dependencies and still supports:
  - distance-based restaurant search ("restaurants near me")
  - nearest-available-driver assignment
"""
import math

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two (lat, lon) points, in kilometers."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def bounding_box(lat, lon, radius_km):
    """
    Returns a (min_lat, max_lat, min_lon, max_lon) box around a point.
    Used as a cheap first-pass DB filter (indexable) before computing exact
    Haversine distance in Python on the smaller candidate set.
    """
    lat_delta = radius_km / 111.0  # ~111km per degree of latitude
    lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.0001))
    return (
        lat - lat_delta, lat + lat_delta,
        lon - lon_delta, lon + lon_delta,
    )
