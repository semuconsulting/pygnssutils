"""
Global variables for pygnssutils.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

OUTPORT = 50010
OUTPORT_NTRIP = 2101
MIN_NMEA_PAYLOAD = 3  # minimum viable length of NMEA message payload
EARTH_RADIUS = 6371  # km
DEFAULT_BUFSIZE = 4096  # buffer size for NTRIP client
MAXPORT = 65535  # max valid TCP port
FORMAT_PARSED = 1
FORMAT_BINARY = 2
FORMAT_HEX = 4
FORMAT_HEXTABLE = 8
FORMAT_PARSEDSTRING = 16
FORMAT_JSON = 32
VERBOSITY_LOW = 0
VERBOSITY_MEDIUM = 1
VERBOSITY_HIGH = 2
VERBOSITY_DEBUG = 3
DISCONNECTED = 0
CONNECTED = 1
LOGLIMIT = 1000  # max lines in logfile
NOGGA = -1
EPILOG = "© 2022 SEMU Consulting BSD 3-Clause license - https://github.com/semuconsulting/pygnssutils/"

GNSSLIST = {
    0: "GPS",
    1: "SBAS",
    2: "Galileo",
    3: "BeiDou",
    4: "IMES",
    5: "QZSS",
    6: "GLONASS",
}

FIXES = {
    "3D": 1,
    "2D": 2,
    "RTK FIXED": 4,
    "RTK FLOAT": 5,
    "RTK": 5,
    "DR": 6,
    "NO FIX": 0,
}

HTTPERR = [
    "400 Bad Request",
    "401 Unauthorized",
    "403 Forbidden",
    "404 Not Found",
    "405 Method Not Allowed",
    "406 Not Acceptable",
]

# ranges for ubxsetrate CLI
ALLNMEA = "allnmea"
ALLUBX = "allubx"
MINNMEA = "minnmea"
MINUBX = "minubx"
ALLNMEA_CLS = [b"\xF0", b"\xF1"]
MINMMEA_ID = [b"\xF0\x00", b"\xF0\x02", b"\xF0\x03", b"\xF0\x04", b"\xF0\x05"]
ALLUBX_CLS = [b"\x01"]
MINUBX_ID = [b"\x01\x07", b"\x01\x35"]

TOPIC_RXM = "/pp/ubx/0236/ip"
TOPIC_MGA = "/pp/ubx/mga"
TOPIC_IP = "/pp/ip/{}"
NTRIP_EVENT = "<<ntrip_read>>"
SPARTN_EVENT = "<<spartn_read>>"
SPARTN_PPSERVER = "pp.services.u-blox.com"
OUTPORT_SPARTN = 8883
PMP_DATARATES = {
    "B600": 600,
    "B1200": 1200,
    "B2400": 2400,
    "B4800": 4800,
}
