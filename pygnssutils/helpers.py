"""
Collection of GNSS related helper methods.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from math import sin, cos, acos, radians
from datetime import datetime, timedelta
from pygnssutils.globals import (
    UBX_HDR,
    NMEA_HDR,
    EARTH_RADIUS,
    NMEA_PROTOCOL,
    UBX_PROTOCOL,
    RTCM3_PROTOCOL,
)


def protocol(raw: bytes) -> int:
    """
    Gets protocol of raw GNSS message.

    :param bytes raw: raw (binary) message
    :return: protocol type (1 = NMEA, 2 = UBX, 4 = RTCM3, 0 = unknown)
    :rtype: int
    """

    p = raw[0:2]
    if p == UBX_HDR:
        return UBX_PROTOCOL
    if p in NMEA_HDR:
        return NMEA_PROTOCOL
    if p[0] == 0xD3 and (p[1] & ~0x03) == 0:
        return RTCM3_PROTOCOL
    return 0


def hextable(raw: bytes, cols: int = 8) -> str:
    """
    Formats raw (binary) message in tabular hexadecimal format e.g.

    000: 2447 4e47 5341 2c41 2c33 2c33 342c 3233 | b'$GNGSA,A,3,34,23' |

    :param bytes raw: raw (binary) data
    :param int cols: number of columns in hex table (8)
    :return: table of hex data
    :rtype: str
    """

    hextbl = ""
    colw = cols * 4
    rawh = raw.hex()
    for i in range(0, len(rawh), colw):
        rawl = rawh[i : i + colw].ljust(colw, " ")
        hextbl += f"{int(i/2):03}: "
        for col in range(0, colw, 4):
            hextbl += f"{rawl[col : col + 4]} "
        hextbl += f" | {bytes.fromhex(rawl)} |\n"

    return hextbl


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
        + str(round(seconds, 3))
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
    return str(int(degrees)) + "\u00b0" + str(round(minutes, 5)) + "\u2032" + sfx


def dop2str(dop: float) -> str:
    """
    Convert Dilution of Precision float to descriptive string.

    :param float dop: dilution of precision as float
    :return: dilution of precision as string e.g. "Good"
    :rtype: str

    """

    if dop <= 1:
        dops = "Ideal"
    elif dop <= 2:
        dops = "Excellent"
    elif dop <= 5:
        dops = "Good"
    elif dop <= 10:
        dops = "Moderate"
    elif dop <= 20:
        dops = "Fair"
    else:
        dops = "Poor"
    return dops


def format_json(message: object) -> str:
    """
    Format message as JSON document.

    :return: human readable representation
    :rtype: str

    """

    if hasattr(message, "identity"):
        ident = message.identity
    else:
        ident = "MESSAGE"

    sta = "{"
    end = "}"
    stg = f'{sta}"class": "{type(message)}", "identity": "{ident}", "payload": {sta}'
    for i, att in enumerate(message.__dict__):
        if att[0] != "_":  # only format public attributes
            val = message.__dict__[att]
            if att == "iTOW":  # convert UBX iTOW to UTC
                val = itow2utc(val)
            if isinstance(val, (int, float)):
                stg += f'"{att}": {val}'
            elif isinstance(val, bool):
                stg += f'"{att}": {"true" if val else "false"})'
            else:
                stg += f'"{att}": "{str(val)}"'
            if i < len(message.__dict__) - 1:
                stg += ", "
    stg += f"{end}{end}"

    return stg


def itow2utc(itow: int) -> datetime.time:
    """
    Convert UBX GPS Time Of Week to UTC time
    (UTC = GPS - 18 seconds; correct as from 2017/1/1).

    :param int itow: GPS Time Of Week
    :return: UTC time hh.mm.ss
    :rtype: datetime.time
    """

    utc = datetime(1980, 1, 6) + timedelta(seconds=(itow / 1000) - 18)
    return utc.time()
