"""
rawnav_subframes_irn.py

IRNSS (NAVIC) NAV Subframe (Message Type) definitions.

L5a:
https://www.isro.gov.in/media_isro/pdf/Publications/Vispdf/Pdf2017/irnss_sps_icd_version1.1-2017.pdf

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

from pygnssutils.rawnav import SID, SPID, SUBFRAMELENGTH, TOC, TOW, WN, S, U
from pygnssutils.rinex_globals import (
    L1CA,
    P2_N4,
    P2_N19,
    P2_N20,
    P2_N21,
    P2_N24,
    P2_N25,
    P2_N27,
    P2_N28,
    P2_N30,
    P2_N31,
    P2_N33,
    P2_N35,
    P2_N41,
    P2_N43,
    P2_N51,
    P2_N55,
    P2_N68,
    P2_P4,
    P2_P11,
    P2_P14,
    P2_P16,
    START,
    TARGET,
)

# **********************************************************************
# LNAV - "5A"
# **********************************************************************

IRN_LNAV_SUBFRAME_TLM = {
    SUBFRAMELENGTH: 292,
    "_tlm": (8, U, 0),
    TOW: (17, U, 12),
    "alert": (1, U, 0),
    "autonav": (1, U, 0),
    SID: (2, U, 0),
    "_spare": (1, U, 0),
}

IRN_LNAV_SUBFRAME_END = {"_parity": (24, U, 0), "_tail": (6, U, 0)}

IRN_LNAV_SUBFRAME_1 = {
    **IRN_LNAV_SUBFRAME_TLM,
    WN: (10, U, 0),
    "af0": (22, S, P2_N31),
    "af1": (16, S, P2_N43),
    "af2": (8, S, P2_N55),
    "ura": (4, U, 0),
    TOC: (16, U, 16),
    "tgd": (8, S, P2_N31),
    "deltan": (22, S, P2_N41),
    "iodec": (8, U, 1),
    "_reserved1": (10, U, 0),
    "l5flag": (1, U, 0),
    "sflag": (1, U, 0),
    "cuc": (15, S, P2_N28),
    "cus": (15, S, P2_N28),
    "cic": (15, S, P2_N28),
    "cis": (15, S, P2_N28),
    "crc": (15, S, P2_N4),
    "crs": (15, S, P2_N4),
    "idot": (14, S, P2_N43),
    "_reserved2": (2, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_2 = {
    **IRN_LNAV_SUBFRAME_TLM,
    "m0": (32, S, P2_N31),
    "toe": (16, U, 16),
    "e": (32, U, P2_N33),
    "sqrta": (32, U, P2_N19),
    "omega0": (32, S, P2_N31),
    "omega": (32, S, P2_N31),
    "omegadot": (22, S, P2_N41),
    "i0": (32, S, P2_N31),
    "_reserved1": (2, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_3_P9 = {
    **IRN_LNAV_SUBFRAME_TLM,
    SPID: (6, U, 0),
    "a0utc": (16, S, P2_N35),
    "a1utc": (13, S, P2_N51),
    "a2utc": (7, S, P2_N68),
    "deltatls": (8, S, 1),
    "toutc": (16, U, P2_P4),
    "wnoutc": (10, U, 1),
    "wnlsf": (10, U, 1),
    "dn": (4, U, 1),
    "deltatlsf": (8, S, 1),
    "a0": (16, S, P2_N35),
    "a1": (13, S, P2_N51),
    "a2": (7, S, P2_N68),
    "tot": (16, U, P2_P4),
    "wnot": (10, U, 1),
    "gnssid": (3, U, 0),
    "_reserved1": (63, U, 0),
    "prn": (6, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_3_P11 = {
    **IRN_LNAV_SUBFRAME_TLM,
    SPID: (6, U, 0),
    "teop": (16, S, P2_P4),
    "pmx": (21, S, P2_N20),
    "pmxdot": (15, S, P2_N21),
    "pmy": (21, S, P2_N20),
    "pmydot": (15, S, P2_N21),
    "deltaut1": (31, S, P2_N24),
    "deltautdot1": (19, S, P2_N25),
    "alpha0": (8, S, P2_N30),
    "alpha1": (8, S, P2_N27),
    "alpha2": (8, S, P2_N24),
    "alpha3": (8, S, P2_N24),
    "beta0": (8, S, P2_P11),
    "beta1": (8, S, P2_P14),
    "beta2": (8, S, P2_P16),
    "beta3": (8, S, P2_P16),
    "_reserved1": (18, U, 0),
    "prn": (6, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_4_P9 = IRN_LNAV_SUBFRAME_3_P9
IRN_LNAV_SUBFRAME_4_P11 = IRN_LNAV_SUBFRAME_3_P11

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
IRN_SUBFRAMEACQ_MAP = {
    L1CA: {
        TARGET: 0b1111,  # Subframes 1, 2, 3/4P9, 3/4P11
        START: 1,
        (1, 0): (IRN_LNAV_SUBFRAME_1, 1),
        (2, 0): (IRN_LNAV_SUBFRAME_2, 2),
        (3, 9): (IRN_LNAV_SUBFRAME_3_P9, 4),
        (4, 9): (IRN_LNAV_SUBFRAME_4_P9, 4),
        (3, 11): (IRN_LNAV_SUBFRAME_3_P11, 8),
        (4, 11): (IRN_LNAV_SUBFRAME_4_P11, 8),
    },
}
