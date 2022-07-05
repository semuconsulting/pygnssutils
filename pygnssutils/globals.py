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
DISCONNECTED = 0
CONNECTED = 1
LOGLIMIT = 1000  # max lines in logfile
NOGGA = -1

GNSSLIST = {
    0: "GPS",
    1: "SBAS",
    2: "Galileo",
    3: "BeiDou",
    4: "IMES",
    5: "QZSS",
    6: "GLONASS",
}
