"""
Global variables for pygnssutils.

Created on 26 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

UBX_HDR = b"\xb5\x62"
NMEA_HDR = [b"\x24\x47", b"\x24\x50"]
OUTPORT = 50010
OUTPORT_NTRIP = 2101
MIN_NMEA_PAYLOAD = 3  # minimum viable length of NMEA message payload
EARTH_RADIUS = 6371  # km
GET = 0
SET = 1
POLL = 2
VALNONE = 0
VALCKSUM = 1
ALL_PROTOCOL = 0
NMEA_PROTOCOL = 1
UBX_PROTOCOL = 2
RTCM3_PROTOCOL = 4
ERR_IGNORE = 0
ERR_LOG = 1
ERR_RAISE = 2
FORMAT_PARSED = 1
FORMAT_BINARY = 2
FORMAT_HEX = 4
FORMAT_HEXTABLE = 8
FORMAT_PARSEDSTRING = 16
FORMAT_JSON = 32
VERBOSITY_LOW = 1
VERBOSITY_MEDIUM = 2
VERBOSITY_HIGH = 4
DISCONNECTED = 0
CONNECTED = 1
LOGLIMIT = 1000  # max lines in logfile

GNSSLIST = {
    0: "GPS",
    1: "SBAS",
    2: "Galileo",
    3: "BeiDou",
    4: "IMES",
    5: "QZSS",
    6: "GLONASS",
}
