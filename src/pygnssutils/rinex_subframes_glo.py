"""
rinex_subframes_glo.py

GLONASS NAV Subframe definitions.

https://web.archive.org/web/20161020203029/http://russianspacesystems.ru/wp-content/uploads/2016/08/ICD_GLONASS_eng_v5.1.pdf

These are provided as the basis of a capability to parse and store
the payloads of raw NAV subframe messages, via the associated
`pygnssutils.RawNav` class defined in `rawnav.py`.

NB:

- MSB and LSB fields MUST be suffixed '_msb' and '_lsb' respectively.
- Non-data bits (reserved, parity, non) MUST be prefixed '_'.
- Avoid the following reserved field names: gnss, svid, sigid, subframeacq, epoch

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

from pygnssutils.rawnav import SID, S, U
from pygnssutils.rinex_globals import (
    L1OF,
    P2_N11,
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

# GLONASS ICD refers to subframes as 'strings'

GLO_L1OF_SUBFRAME_TLM = {
    "_idle": (0, 1, U, 0),
    SID: (1, 4, U, 0),  # subframe (string) number
}

GLO_L1OF_SUBFRAME_END = {
    "_hamming": (77, 8, U, 0),
}

# content of 4 32-bit dwrds in RXM-SFRBX payload:
GLO_SUPERFRAME = {
    **GLO_L1OF_SUBFRAME_TLM,
    "data": (5, 72, U, 0),
    **GLO_L1OF_SUBFRAME_END,
    "_padding1": (85, 11, U, 0),
    "superframeid": (96, 16, U, 0),
    "_padding2": (112, 8, U, 0),
    "frameid": (120, 8, U, 0),
}

# attribute_name: (bit offset, bit length, bit encoding, scaling)
GLO_L1OF_SUBFRAME_1 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "_reserved1": (5, 2, U, 0),
    "p1": (7, 2, U, 1),
    "tk": (9, 12, U, 0),
    # "tk_hours": (9, 5, U, 0),
    # "tk_mins": (14, 6, U, 0),
    # "tk_secs": (20, 1, U, 30),
    "xntbdot": (21, 24, S, P2_N20),
    "xntbdot2": (45, 5, S, P2_N30),
    "xntb": (50, 27, S, P2_N11),
    **GLO_L1OF_SUBFRAME_END,
}
GLO_L1OF_SUBFRAME_2 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "bn": (5, 3, U, 0),
    "p2": (8, 1, U, 1),
    "tb": (9, 7, U, 15),
    "_reserved1": (16, 5, U, 0),
    "yntbdot": (21, 24, S, P2_N20),
    "yntbdot2": (45, 5, S, P2_N30),
    "yntb": (50, 27, S, P2_N11),
    **GLO_L1OF_SUBFRAME_END,
}
GLO_L1OF_SUBFRAME_3 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "p3": (5, 1, U, 1),
    "gammantb": (6, 11, S, P2_N40),
    "_reserved1": (17, 1, U, 0),
    "p": (18, 2, U, 1),
    "ln": (20, 1, U, 1),
    "zntbdot": (21, 24, S, P2_N20),
    "zntbdot2": (45, 5, S, P2_N30),
    "zntb": (50, 27, S, P2_N11),
    **GLO_L1OF_SUBFRAME_END,
}
GLO_L1OF_SUBFRAME_4 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "tauntb": (5, 22, S, P2_N30),
    "deltataun": (27, 5, S, P2_N30),
    "en": (32, 5, U, 1),
    "_reserved1": (37, 14, U, 0),
    "p4": (51, 1, U, 1),
    "ft": (52, 4, U, 0),
    "_reserved2": (56, 3, U, 0),
    "nt": (59, 11, U, 0),
    "n": (70, 5, U, 0),
    "m": (75, 2, U, 0),  # 0 = GLONASS, 1 = GLONASS-M
    **GLO_L1OF_SUBFRAME_END,
}
GLO_L1OF_SUBFRAME_5 = {
    **GLO_L1OF_SUBFRAME_TLM,
    "na": (5, 11, S, P2_N30),
    "tauc": (16, 32, S, P2_N31),
    "_reserved1": (48, 1, U, 0),
    "n4": (49, 5, U, 1),
    "taugps": (54, 22, S, P2_N30),
    "ln": (76, 1, U, 0),
    **GLO_L1OF_SUBFRAME_END,
}

# mapping for (subframe, page) acquisition mask subframeacq
GLO_SUBFRAMEACQ_MAP = {
    L1OF: {
        TARGET: 0b11111,  # subframes 1,2,3,4,5
        START: 1,
        (1, 0): (GLO_L1OF_SUBFRAME_1, 1),
        (2, 0): (GLO_L1OF_SUBFRAME_2, 2),
        (3, 0): (GLO_L1OF_SUBFRAME_3, 4),
        (4, 0): (GLO_L1OF_SUBFRAME_4, 8),
        (5, 0): (GLO_L1OF_SUBFRAME_5, 16),
    },
}
