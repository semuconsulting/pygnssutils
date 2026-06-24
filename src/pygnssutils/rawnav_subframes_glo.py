"""
rawnav_subframes_glo.py

GLONASS NAV Subframe definitions.

L1OF,L2OF: http://gauss.gge.unb.ca/GLONASS.ICD.pdf
L1OF,L2OF: https://web.archive.org/web/20161020203029/http://russianspacesystems.ru/wp-content/uploads/2016/08/ICD_GLONASS_eng_v5.1.pdf

These are provided as the basis of a capability to parse and store
the payloads of raw NAV subframe messages, via the associated
`pygnssutils.RawNav` class defined in `rawnav.py`.

Format of subframe definition dictionary::

   dict[attribute_name, tuple[length, encoding, scaling]

where

 - length = attribute length in bits
 - encoding = U (unsigned integer) or S (two's complement signed integer)
 - scaling = scaling factor (resolution) as integer or float (0 = no scaling)

NB:

- MSB and LSB fields MUST be suffixed '_msb' and '_lsb' respectively.
- Non-data bits (reserved, parity, non) MUST be prefixed '_'.
- '#' character in almanac attributes will be replaced with relevant almanac svid.
- Avoid the following reserved field names: gnss, svid, sigid, subframeacq, epoch.

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

from pygnssutils.rawnav import SID, SUBFRAMELENGTH, SVIDALM, S, U
from pygnssutils.rinex_globals import (
    L1OF,
    P2_N5,
    P2_N9,
    P2_N10,
    P2_N11,
    P2_N14,
    P2_N15,
    P2_N16,
    P2_N18,
    P2_N20,
    P2_N30,
    P2_N31,
    P2_N40,
    START,
    TARGET,
)

# **********************************************************************
# L1OF (FDMA) - "1C" (same as L2OF - "2C")
# **********************************************************************

# TODO check that GLONASS is actually using two's complement for -ve values
# (ICD just refers to MSB being sign bit, without explicitly using the term
# two's complement)

# GLONASS ICD refers to subframes as 'strings' and individual attributes as 'words'

GLO_L1OF_SUBFRAME_TLM = {
    SUBFRAMELENGTH: 85,
    "_idle": (1, U, 0),
    SID: (4, U, 0),  # subframe (string) number
}

GLO_L1OF_SUBFRAME_END = {
    "_hamming": (8, U, 0),
}

# content of 4 32-bit dwrds in RXM-SFRBX payload:
GLO_SUPERFRAME = {
    **GLO_L1OF_SUBFRAME_TLM,
    "data": (72, U, 0),  # payloads defined below
    **GLO_L1OF_SUBFRAME_END,
    "_padding1": (11, U, 0),
    "superframeid": (16, U, 0),
    "_padding2": (8, U, 0),
    "frameid": (8, U, 0),
}

GLO_L1OF_SUBFRAME_1 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "_reserved1": (2, U, 0),
    "p1": (2, U, 1),  # data update interval
    "tk": (12, U, 0),  # time
    # "tk_hours": (5, U, 0),
    # "tk_mins": (6, U, 0),
    # "tk_secs": (1, U, 30),
    "xntbdot": (24, S, P2_N20),  # x velocity
    "xntbdot2": (5, S, P2_N30),  # x acceleration
    "xntb": (27, S, P2_N11),  # x position
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_2 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "bn": (3, U, 0),  # health flag
    "p2": (1, U, 1),  # flag for odd/even tb
    "tb": (7, U, 15),  # index time interval
    "_reserved1": (5, U, 0),
    "yntbdot": (24, S, P2_N20),  # y velocity
    "yntbdot2": (5, S, P2_N30),  # y acceleration
    "yntb": (27, S, P2_N11),  # y position
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_3 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "p3": (1, U, 1),  # num satellites in frame (4/5)
    "gammantb": (11, S, P2_N40),
    "_reserved1": (1, U, 0),
    "p": (2, U, 1),
    "ln": (1, U, 1),  # ephemeris health flag
    "zntbdot": (24, S, P2_N20),  # z velocity
    "zntbdot2": (5, S, P2_N30),  # z acceleration
    "zntb": (27, S, P2_N11),  # z position
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_4 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "tauntb": (22, S, P2_N30),
    "deltataun": (5, S, P2_N30),
    "en": (5, U, 1),
    "_reserved1": (14, U, 0),
    "p4": (1, U, 1),  # ephemeris present flag
    "ft": (4, U, 0),  # satellite URA
    "_reserved2": (3, U, 0),
    "nt": (11, U, 0),  # current day/date
    "n": (5, U, 0),  # slot number
    "m": (2, U, 0),  # 0 = GLONASS, 1 = GLONASS-M
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_5 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "na": (11, S, P2_N30),  # calendar day within 4-year period
    "tauc": (32, S, P2_N31),  # time correction GLO -> UTC
    "_reserved1": (1, U, 0),
    "n4": (5, U, 1),  # 4-year interval from 1996
    "taugps": (22, S, P2_N30),  # time correction GPS -> GLO
    "lna": (1, U, 0),  # almanac health flag
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_6 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "cna#": (1, U, 1),  # health flag
    "mna#": (2, U, 1),  # 0 = GLONASS, 1 = GLONASS-M
    SVIDALM: (5, U, 1),  # almanac svid (slot) number (will replace '#' below)
    "tauna#": (10, S, P2_N18),  # time correction to GLO time
    "lambdana#": (21, S, P2_N20),  # longitude of ascending node
    "deltaina#": (18, S, P2_N20),  # rate of change of inclination
    "epsilonna#": (15, S, P2_N20),  # eccentricity
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_7 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "omegana#": (16, S, P2_N15),  # argument of perigee
    "taulambdana#": (21, S, P2_N5),  # time of first ascending node
    "deltatna#": (22, S, P2_N9),  # correction to Draconian period
    "deltatdotna#": (7, S, P2_N14),  # rate of change of Draconian period
    "hna#": (5, U, 1),  # carrier frequency number
    "lna#": (1, U, 0),  # almanac health flag
    **GLO_L1OF_SUBFRAME_END,
}

GLO_L1OF_SUBFRAME_8 = GLO_L1OF_SUBFRAME_6
GLO_L1OF_SUBFRAME_9 = GLO_L1OF_SUBFRAME_7
GLO_L1OF_SUBFRAME_10 = GLO_L1OF_SUBFRAME_6
GLO_L1OF_SUBFRAME_11 = GLO_L1OF_SUBFRAME_7
GLO_L1OF_SUBFRAME_12 = GLO_L1OF_SUBFRAME_6
GLO_L1OF_SUBFRAME_13 = GLO_L1OF_SUBFRAME_7
GLO_L1OF_SUBFRAME_14 = GLO_L1OF_SUBFRAME_6  # frames 1-4
GLO_L1OF_SUBFRAME_15 = GLO_L1OF_SUBFRAME_7  # frames 1-4

GLO_L1OF_SUBFRAME_14_F5 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "b1": (11, S, P2_N10),  # time coefficient UT1 UTC(SU)
    "b2": (10, S, P2_N16),  # time coefficient delta UT1
    "kp": (2, U, 1),  # notification of leapsecond
    "_reserved": (49, U, 0),
    **GLO_L1OF_SUBFRAME_END,
}  # frame 5

GLO_L1OF_SUBFRAME_15_F5 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "_reserved": (71, U, 0),
    "lna#": (1, U, 0),  # almanac health flag
    **GLO_L1OF_SUBFRAME_END,
}  # frame 5

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
GLO_SUBFRAMEACQ_MAP = {
    L1OF: {
        TARGET: 0b11111,  # subframes 1,2,3,4,5
        START: 1,
        (1, 0): (GLO_L1OF_SUBFRAME_1, 1),
        (2, 0): (GLO_L1OF_SUBFRAME_2, 2),
        (3, 0): (GLO_L1OF_SUBFRAME_3, 4),
        (4, 0): (GLO_L1OF_SUBFRAME_4, 8),
        (5, 0): (GLO_L1OF_SUBFRAME_5, 16),
        # (6, 0): (GLO_L1OF_SUBFRAME_6, 32),
        # (7, 0): (GLO_L1OF_SUBFRAME_7, 64),
        # (8, 0): (GLO_L1OF_SUBFRAME_8, 128),
        # (9, 0): (GLO_L1OF_SUBFRAME_9, 256),
        # (10, 0): (GLO_L1OF_SUBFRAME_10, 512),
        # (11, 0): (GLO_L1OF_SUBFRAME_11, 1024),
        # (12, 0): (GLO_L1OF_SUBFRAME_12, 2048),
        # (13, 0): (GLO_L1OF_SUBFRAME_13, 4096),
        # (14, 0): (GLO_L1OF_SUBFRAME_14, 8192),
        # (15, 0): (GLO_L1OF_SUBFRAME_15, 16384),
        # (114, 0): (GLO_L1OF_SUBFRAME_14_F5, 32768),
        # (115, 0): (GLO_L1OF_SUBFRAME_15_F5, 65536),
    },
}
