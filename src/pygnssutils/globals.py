"""
Global variables for pygnssutils.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

CLIAPP = "CLI"
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
OUTPUT_NONE = 0
OUTPUT_FILE = 1
OUTPUT_SERIAL = 2
OUTPUT_SOCKET = 3
OUTPUT_HANDLER = 4
VERBOSITY_CRITICAL = -1
VERBOSITY_LOW = 0
VERBOSITY_MEDIUM = 1
VERBOSITY_HIGH = 2
VERBOSITY_DEBUG = 3
UBXSIMULATOR = "UBXSIMULATOR"
LOGGING_LEVELS = {
    VERBOSITY_CRITICAL: "CRITICAL",
    VERBOSITY_LOW: "ERROR",
    VERBOSITY_MEDIUM: "WARNING",
    VERBOSITY_HIGH: "INFO",
    VERBOSITY_DEBUG: "DEBUG",
}
DISCONNECTED = 0
CONNECTED = 1
LOGFORMAT = "{asctime}.{msecs:.0f} - {levelname} - {name} - {message}"
LOGLIMIT = 10485760  # max size of logfile in bytes
NOGGA = -1
EPILOG = (
    "© 2022 SEMU Consulting BSD 3-Clause license"
    " - https://github.com/semuconsulting/pygnssutils/"
)

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
    "NO FIX": 0,
    "TIME ONLY": 0,
    "2D": 1,
    "3D": 1,
    "GPS + DR": 1,
    "GNSS+DR": 1,
    "RTK": 5,
    "RTK FLOAT": 5,
    "RTK FIXED": 4,
    "DR": 6,
}

HTTPCODES = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    408: "Request Timeout",
    409: "Conflict",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    503: "Service Unavailable",
}

HTTPERR = [f"{i[0]} {i[1]}" for i in HTTPCODES.items() if 400 <= i[0] <= 599]

# ranges for ubxsetrate CLI
ALLNMEA = "allnmea"
ALLUBX = "allubx"
MINNMEA = "minnmea"
MINUBX = "minubx"
ALLNMEA_CLS = [b"\xF0", b"\xF1"]
MINMMEA_ID = [b"\xF0\x00", b"\xF0\x02", b"\xF0\x03", b"\xF0\x04", b"\xF0\x05"]
ALLUBX_CLS = [b"\x01"]
MINUBX_ID = [b"\x01\x07", b"\x01\x35"]

TOPIC_KEY = "/pp/ubx/0236/{}"
TOPIC_ASSIST = "/pp/ubx/mga"
TOPIC_DATA = "/pp/{}/{}"
TOPIC_FREQ = "/pp/frequencies/Lb"
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

# Center point of rectangular regions mapped to the
# SPARTN MQTT PointPerfect region name
REGION_MAPPING = {
    (-26.55, 134.70): "au",
    (52.45, 011.85): "eu",
    (38.95, 139.60): "jp",  # East
    (33.10, 132.20): "jp",  # West
    (36.30, 128.20): "kr",
    (39.20, -096.60): "us",
}
