"""
Collection of GNSS related helper methods.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2020
:license: BSD 3-Clause
"""

# pylint: disable=invalid-name

import logging
import logging.handlers
from argparse import ArgumentParser
from math import cos, radians, sin
from socket import AF_INET, AF_INET6, gaierror, getaddrinfo

from pynmeagps import haversine
from pyubx2 import itow2utc

from pygnssutils.globals import (
    LOGFORMAT,
    LOGGING_LEVELS,
    LOGLIMIT,
    VERBOSITY_CRITICAL,
    VERBOSITY_DEBUG,
    VERBOSITY_HIGH,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)


def parse_config(configfile: str) -> dict:
    """
    Parse config file.

    :param str configfile: fully qualified path to config file
    :return: config as kwargs, or None if file not found
    :rtype: dict
    """

    try:
        config = {}
        with open(configfile, "r", encoding="utf-8") as infile:
            for cf in infile:
                key, val = cf.split("=", 1)
                config[key.strip()] = val.strip()
        return config
    except (FileNotFoundError, ValueError):
        return None


def set_common_args(
    ap: ArgumentParser,
    logname: str = "pygnssutils",
    logdefault: int = VERBOSITY_MEDIUM,
) -> dict:
    """
    Set common argument parser and logging args.

    :param ArgumentParserap: argument parser instance
    :param str logname: logger name
    :param int logdefault: default logger verbosity level
    :return: parsed arguments as kwargs
    :rtype: dict
    """

    ap.add_argument(
        "-C",
        "--config",
        required=False,
        help="Fully qualified path to CLI configuration file",
        default=None,
    )
    ap.add_argument(
        "--verbosity",
        required=False,
        help=(
            f"Log message verbosity "
            f"{VERBOSITY_CRITICAL} = critical, "
            f"{VERBOSITY_LOW} = low (error), "
            f"{VERBOSITY_MEDIUM} = medium (warning), "
            f"{VERBOSITY_HIGH} = high (info), {VERBOSITY_DEBUG} = debug"
        ),
        type=int,
        choices=[
            VERBOSITY_CRITICAL,
            VERBOSITY_LOW,
            VERBOSITY_MEDIUM,
            VERBOSITY_HIGH,
            VERBOSITY_DEBUG,
        ],
        default=logdefault,
    )
    ap.add_argument(
        "--logtofile",
        required=False,
        help="fully qualified log file name, or '' for no log file",
        type=str,
        default="",
    )

    kwargs = vars(ap.parse_args())
    # config file settings will supplement CLI and default args
    cfg = kwargs.pop("config", None)
    if cfg is not None:
        kwargs = {**kwargs, **parse_config(cfg)}

    logger = logging.getLogger(logname)
    set_logging(
        logger, kwargs.pop("verbosity", logdefault), kwargs.pop("logtofile", "")
    )

    return kwargs


def set_logging(
    logger: logging.Logger,
    verbosity: int = VERBOSITY_MEDIUM,
    logtofile: str = "",
    logform: str = LOGFORMAT,
    limit: int = LOGLIMIT,
):
    """
    Set logging format and level.

    :param logging.Logger logger: module log handler
    :param int verbosity: verbosity level -1,0,1,2,3 (2 - MEDIUM)
    :param str logtofile: fully qualified log file name ("")
    :param str logform: logging format (datetime - level - name)
    :param int limit: maximum logfile size in bytes (10MB)
    """

    try:
        level = LOGGING_LEVELS[int(verbosity)]
    except (KeyError, ValueError):
        level = logging.WARNING

    logger.setLevel(logging.DEBUG)
    logformat = logging.Formatter(
        logform,
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )
    if logtofile == "":
        loghandler = logging.StreamHandler()
    else:
        loghandler = logging.handlers.RotatingFileHandler(
            logtofile, mode="a", maxBytes=limit, backupCount=10, encoding="utf-8"
        )
    loghandler.setFormatter(logformat)
    loghandler.setLevel(level)
    logger.addHandler(loghandler)


def progbar(i: int, lim: int, inc: int = 50):
    """
    Display progress bar on console.
    """

    i = min(i, lim)
    pct = int(i * inc / lim)
    if not i % int(lim / inc):
        print(
            f"{int(pct*100/inc):02}% " + "\u2593" * pct + "\u2591" * (inc - pct),
            end="\r",
        )


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


def format_conn(
    family: int, server: str, port: int, flowinfo: int = 0, scopeid: int = 0
) -> tuple:
    """
    Return formatted socket connection string.

    :param int family: IP family (AF_INET, AF_INET6)
    :param str server: server
    :param int port: port
    :param int flowinfo: flow info (0)
    :param int scopeid: scope ID (0)
    :return: connection tuple
    :rtype: tuple
    """

    if family == AF_INET6:
        if family == AF_INET6:
            if flowinfo != 0 or scopeid != 0:
                return (server, port, flowinfo, scopeid)
            try:
                return getaddrinfo(server, port)[1][4]
            except gaierror as err:
                raise ValueError(f"Invalid server or port {server} {port}") from err
    if family == AF_INET:
        return (server, port)
    raise ValueError(f"Invalid family value {family}")


def ipprot2int(family: str) -> int:
    """
    Convert IP family string to integer.

    :param str family: family string ("IPv4", "IPv6")
    :return: value as int AF_INET, AF_INET6
    :rtype: int
    """

    if family == "IPv4":
        return AF_INET
    if family == "IPv6":
        return AF_INET6
    raise ValueError(f"Invalid family value {family}")


def ipprot2str(family: int) -> str:
    """
    Convert IP family integer to string.

    :param str family: family int (AF_INET, AF_INET6)
    :return: value as str ("IPv4", "IPv6")
    :rtype: int
    """

    if family == AF_INET:
        return "IPv4"
    if family == AF_INET6:
        return "IPv6"
    raise ValueError(f"Invalid family value {family}")
