"""
Collection of GNSS related helper methods.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from math import sin, cos, acos, radians
from pyubx2 import itow2utc
from pygnssutils.globals import EARTH_RADIUS


def haversine(
    lat1: float, lon1: float, lat2: float, lon2: float, rds: int = EARTH_RADIUS
) -> float:
    """
    Calculate spherical distance between two coordinates using haversine formula.

    :param float lat1: lat1
    :param float lon1: lon1
    :param float lat2: lat2
    :param float lon2: lon2
    :param float rds: earth radius (6371 km)
    :return: spherical distance in km
    :rtype: float
    """

    coordinates = lat1, lon1, lat2, lon2
    phi1, lambda1, phi2, lambda2 = [radians(c) for c in coordinates]
    dist = rds * acos(
        cos(phi2 - phi1) - cos(phi1) * cos(phi2) * (1 - cos(lambda2 - lambda1))
    )

    return dist


def get_mp_distance(lat: float, lon: float, mp: list) -> float:
    """
    Get distance to mountpoint from current location (if known).

    Predicated on the sourcetable being formatted as a
    list of sourcetable entries, where for each entry:
    entry[0] = mountpoint name
    entry[8] = mountpoint latitude
    entry[9] = mountpoint longitude

    :param float lat: current latitude
    :param float lon: current longitude
    :param list mp: sourcetable mountpoint entry
    :return: distance to mountpoint in km, or None if n/a
    :rtype: float or None
    """

    dist = None
    try:
        if len(mp) > 9:  # if location provided for this mountpoint
            lat = float(lat)
            lon = float(lon)
            lat2 = float(mp[8])
            lon2 = float(mp[9])
            dist = haversine(lat, lon, lat2, lon2)
    except (TypeError, ValueError):
        pass

    return dist


def find_mp_distance(
    lat: float, lon: float, sourcetable: list, name: str = ""
) -> tuple:
    """
    Find distance to named mountpoint. If mountpoint name
    is not provided, find closest mountpoint in sourcetable.

    Predicated on the sourcetable being formatted as a
    list of sourcetable entries, where for each entry:
    entry[0] = mountpoint name
    entry[8] = mountpoint latitude
    entry[9] = mountpoint longitude

    :param float lat: reference latitude
    :param float lon: reference longitude
    :param list sourcetable: sourcetable as list
    :param str name: (optional) mountpoint name (None)
    :returns: tuple of (name of closest mountpoint, distance in km)
    :rtype: tuple
    """

    mindist = 9999999
    mpname = None
    for mp in sourcetable:
        dist = get_mp_distance(lat, lon, mp)
        if dist is not None:
            if name == "":  # find closest
                if dist < mindist:
                    mpname = mp[0]
                    mindist = dist
            else:
                if mp[0] == name:
                    mpname = mp[0]
                    mindist = dist
                    break

    return mpname, round(mindist, 2)


def cel2cart(elevation: float, azimuth: float) -> tuple:
    """
    Convert celestial coordinates (degrees) to Cartesian coordinates.

    :param float elevation: elevation
    :param float azimuth: azimuth
    :return: cartesian x,y coordinates
    :rtype: tuple
    """

    if not (isinstance(elevation, (float, int)) and isinstance(azimuth, (float, int))):
        return (0, 0)
    elevation = radians(elevation)
    azimuth = radians(azimuth)
    x = cos(azimuth) * cos(elevation)
    y = sin(azimuth) * cos(elevation)
    return (x, y)


def latlon2dms(latlon: tuple) -> tuple:
    """
    Converts decimal lat/lon tuple to degrees minutes seconds.

    :param tuple latlon: tuple of (lat, lon) as floats
    :return: (lat,lon) in d.m.s. format
    :rtype: tuple
    """

    lat, lon = latlon
    lat = deg2dms(lat, "lat")
    lon = deg2dms(lon, "lon")
    return lat, lon


def latlon2dmm(latlon: tuple) -> tuple:
    """
    Converts decimal lat/lon tuple to degrees decimal minutes.

    :param tuple latlon: tuple of (lat, lon) as floats
    :return: (lat,lon) in d.mm.m format
    :rtype: tuple
    """

    lat, lon = latlon
    lat = deg2dmm(lat, "lat")
    lon = deg2dmm(lon, "lon")
    return lat, lon


def deg2dms(degrees: float, latlon: str) -> str:
    """
    Convert decimal degrees to degrees minutes seconds string.

    :param float degrees: degrees
    :param str latlon: "lat" or "lon"
    :return: degrees as d.mm.m formatted string
    :rtype: str
    """

    if not isinstance(degrees, (float, int)):
        return ""
    negative = degrees < 0
    degrees = abs(degrees)
    minutes, seconds = divmod(degrees * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    if negative:
        sfx = "S" if latlon == "lat" else "W"
    else:
        sfx = "N" if latlon == "lat" else "E"
    return (
        str(int(degrees))
        + "\u00b0"
        + str(int(minutes))
        + "\u2032"
        + str(round(seconds, 5))
        + "\u2033"
        + sfx
    )


def deg2dmm(degrees: float, latlon: str) -> str:
    """
    Convert decimal degrees to degrees decimal minutes string.

    :param float degrees: degrees
    :param str latlon: "lat" or "lon"
    :return: degrees as d.mm.m formatted string
    :rtype: str
    """

    if not isinstance(degrees, (float, int)):
        return ""
    negative = degrees < 0
    degrees = abs(degrees)
    degrees, minutes = divmod(degrees * 60, 60)
    if negative:
        sfx = "S" if latlon == "lat" else "W"
    else:
        sfx = "N" if latlon == "lat" else "E"
    return str(int(degrees)) + "\u00b0" + str(round(minutes, 7)) + "\u2032" + sfx


def format_json(message: object) -> str:
    """
    Format object as JSON document.

    :return: JSON document as string
    :rtype: str

    """

    ident = ""
    if hasattr(message, "identity"):
        ident = message.identity

    sta = "{"
    end = "}"
    stg = f'{sta}"class": "{type(message)}", "identity": "{ident}", "payload": {sta}'
    for i, att in enumerate(message.__dict__):
        if att[0] != "_":  # only format public attributes
            val = message.__dict__[att]
            if att == "iTOW":  # convert UBX iTOW to UTC
                val = itow2utc(val)
            if isinstance(val, bool):
                stg += f'"{att}": {"true" if val else "false"}'
            elif isinstance(val, (int, float)):
                stg += f'"{att}": {val}'
            else:
                stg += f'"{att}": "{str(val)}"'
            if i < len(message.__dict__) - 1:
                stg += ", "
    stg += f"{end}{end}"

    return stg
