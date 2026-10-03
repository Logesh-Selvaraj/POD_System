import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees).

    WHY HAVERSINE AND NOT EUCLIDEAN:
        GPS coordinates are angular measurements on a sphere, not points on
        a flat plane.  A naive Pythagorean calculation in degree-space
        introduces significant errors at equatorial latitudes (up to ~1.2 %
        per degree of separation) and grows worse near the poles.  The
        Haversine formula accounts for Earth's curvature and produces metre-
        accurate distances for the short ranges relevant to last-mile delivery
        (≤ a few kilometres).

    WHY 150 METRES AS THE ACCEPTANCE THRESHOLD:
        Indoor GPS signals in dense urban environments (high-rise blocks,
        shopping-centre basements, underground car parks) commonly drift
        10–80 m from the actual location.  A 150 m threshold absorbs this
        sensor noise while still catching fraudulent submissions from a
        different street.  The value is configurable via GPS_MISMATCH_THRESHOLD_METERS
        so operations teams can tune it per deployment geography.

    ALGORITHM:
        a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)
        c = 2·arcsin(√a)
        d = R·c   where R = 6 371 000 m (mean Earth radius)

        arcsin is used instead of arctan2 (the 'Vincenty' variant) because
        arcsin is numerically stable for the short distances encountered in
        delivery geofencing and avoids the more expensive atan2 computation.
    """
    # Convert decimal degrees to radians; all four values processed in one map
    # call to avoid repeated function-call overhead.
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Mean radius of Earth in metres (WGS-84 approximation)
    return c * r
