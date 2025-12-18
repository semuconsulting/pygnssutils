"""
Global variables for pygnssutils.

Created on 26 May 2022

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2022
:license: BSD 3-Clause
"""

from pathlib import Path

HOME = Path.home()

OKCOL = "green"
ERRCOL = "salmon"
INFOCOL = "steelblue2"

CLIAPP = "CLI"
DEFAULT_BUFSIZE = 4096  # buffer size for NTRIP client
"""Default socket buffer size"""
EARTH_RADIUS = 6371  # km
"""Earth radius in km"""
ENV_NTRIP_PASSWORD = "PYGPSCLIENT_PASSWORD"
""" Environment variable for NTRIP password """
ENV_NTRIP_USER = "PYGPSCLIENT_USER"
""" Environment variable for NTRIP user """
ENV_MQTT_CLIENTID = "MQTTCLIENTID"
""" Environment variable for MQTT Client ID """
ENV_MQTT_KEY = "MQTTKEY"
""" Environment variable for MQTT SPARTN decryption key """
ENCODE_NONE = 0
"""No socket encoding"""
ENCODE_CHUNKED = 1
"""chunked socket encoding"""
ENCODE_GZIP = 2
"""gzip socket encoding"""
ENCODE_COMPRESS = 4
"""compress socket encoding"""
ENCODE_DEFLATE = 8
"""deflate socket encoding"""
FORMAT_PARSED = 1
"""parsed format"""
FORMAT_BINARY = 2
"""binary (raw) format"""
FORMAT_HEX = 4
"""hexadecimal string format"""
FORMAT_HEXTABLE = 8
"""tabular hexadecimal format"""
FORMAT_PARSEDSTRING = 16
"""parsed as string format"""
FORMAT_JSON = 32
"""JSON format"""
INPUT_NONE = 0
"""No input medium"""
INPUT_NTRIP_RTCM = 1
"""NTRIP RTCM input"""
INPUT_NTRIP_SPARTN = 2
"""NTRIP SPARTN input"""
INPUT_MQTT_SPARTN = 3
"""MQTT SPARTN input"""
INPUT_SERIAL = 4
"""Serial input (e.g. RXM-PMP from D9S SPARTN L-band receiver)"""
INPUT_FILE = 5
"""File input (e.g. CFG-VALSET commands)"""
MAXPORT = 65535  # max valid TCP port
"""Maximum permissible port number"""
MIN_NMEA_PAYLOAD = 3  # minimum viable length of NMEA message payload
NTRIP1 = "1.0"
"""NTRIP version 1.0 descriptor"""
NTRIP2 = "2.0"
"""NTRIP version 2.0 descriptor"""
OUTPORT = 50010
"""Default socket server port"""
OUTPORT_NTRIP = 2101
"""Default NTRIP caster port"""
OUTPUT_NONE = 0
"""No output medium"""
OUTPUT_FILE = 1
"""Binary file output"""
OUTPUT_SERIAL = 2
"""Serial output"""
OUTPUT_SOCKET = 3
"""Socket output"""
OUTPUT_SOCKET_TLS = 6
"""Socket output with TLS"""
OUTPUT_HANDLER = 4
"""Custom output handler"""
OUTPUT_TEXT_FILE = 5
"""Text file output"""
VERBOSITY_CRITICAL = -1
"""Verbosity critical"""
VERBOSITY_LOW = 0
"""Verbosity error"""
VERBOSITY_MEDIUM = 1
"""Verbosity warning"""
VERBOSITY_HIGH = 2
"""Verbosity info"""
VERBOSITY_DEBUG = 3
"""Verbosity debug"""
UBXSIMULATOR = "UBXSIMULATOR"
"""UBX simulator"""
LOGGING_LEVELS = {
    VERBOSITY_CRITICAL: "CRITICAL",
    VERBOSITY_LOW: "ERROR",
    VERBOSITY_MEDIUM: "WARNING",
    VERBOSITY_HIGH: "INFO",
    VERBOSITY_DEBUG: "DEBUG",
}
"""Logging level descriptors"""
DISCONNECTED = 0
"""Disconnected"""
CONNECTED = 1
"""Connected"""
MAXCONNECTION = 5
"""Maximum connections reached (for socket server)"""
LOGFORMAT = "{asctime}.{msecs:.0f} - {levelname} - {name} - {message}"
"""Logging format"""
LOGLIMIT = 10485760  # max size of logfile in bytes
"""Logfile limit"""
NOGGA = -1
"""No GGA sentence to be sent (for NTRIP caster)"""
EPILOG = (
    "© 2022 semuadmin (Steve Smith) BSD 3-Clause license"
    " - https://github.com/semuconsulting/pygnssutils/"
)
"""CLI argument parser epilog"""

GNSSLIST = {
    0: "GPS",
    1: "SBAS",
    2: "Galileo",
    3: "BeiDou",
    4: "IMES",
    5: "QZSS",
    6: "GLONASS",
}
"""GNSS identifiers"""

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
"""Fix enumeration"""

FIXTYPE_GGA = {
    0: "NO FIX",
    1: "3D",
    2: "3D",
    4: "RTK FIXED",
    5: "RTK FLOAT",
    6: "DR",
}
"""NMEA GGA `fixtype` decode"""

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
"""HTTP response codes used by NTRIP"""

HTTPERR = [f"{i[0]} {i[1]}" for i in HTTPCODES.items() if 400 <= i[0] <= 599]

RTCMTYPES = {
    "1002": 1,
    "1006": 5,
    "1010": 1,
    "1077": 1,
    "1087": 1,
    "1097": 1,
    "1127": 1,
    "1230": 1,
    "4072_0": 1,
    "4072_1": 1,
}
"""RTCM3 message types output in NTRIP caster mode"""
RTCMSTR = (
    "1002(1),1006(5),1010(1),1077(1),1087(1),"
    "1097(1),1127(1),1230(1),4072_0(1),4072_1(1)"
)
"""RTCM3 types sourcetable entry for NTRIP caster"""
PYGPSMP = "pygnssutils"
"""Name of NTRIP caster mountpoint"""

# ranges for ubxsetrate CLI
ALLNMEA = "allnmea"
ALLUBX = "allubx"
MINNMEA = "minnmea"
MINUBX = "minubx"
ALLNMEA_CLS = [b"\xf0", b"\xf1"]
MINMMEA_ID = [b"\xf0\x00", b"\xf0\x02", b"\xf0\x03", b"\xf0\x04", b"\xf0\x05"]
ALLUBX_CLS = [b"\x01"]
MINUBX_ID = [b"\x01\x04", b"\x01\x07", b"\x01\x35"]
PYGNSSUTILS_CRT = f"{HOME}/pygnssutils.crt"
"""Name of default TLS CRT file"""
PYGNSSUTILS_CRTPATH = "PYGNSSUTILS_CRTPATH"
"""Name of environment variable containing path to TLS CRT file"""
PYGNSSUTILS_PEM = f"{HOME}/pygnssutils.pem"
"""Name of default TLS PEM file"""
PYGNSSUTILS_PEMPATH = "PYGNSSUTILS_PEMPATH"
"""Name of environment variable containing path to TLS PEM file"""
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
