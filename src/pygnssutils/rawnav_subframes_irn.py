"""
rawnav_subframes_irn.py

IRNSS (NAVIC) NAV Subframe (Message Type) definitions.

L5a:
https://www.isro.gov.in/media_isro/pdf/Publications/Vispdf/Pdf2017/irnss_sps_icd_version1.1-2017.pdf

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

from pygnssutils.rawnav import SID, SPID, TOW, WN, S, U
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
    "_tlm": (0, 8, U, 0),
    TOW: (8, 17, U, 12),
    "alert": (25, 1, U, 0),
    "autonav": (26, 1, U, 0),
    SID: (27, 2, U, 0),
    "_spare": (29, 1, U, 0),
}

IRN_LNAV_SUBFRAME_END = {"_parity": (262, 24, U, 0), "_tail": (286, 6, U, 0)}

IRN_LNAV_SUBFRAME_1 = {
    **IRN_LNAV_SUBFRAME_TLM,
    WN: (30, 10, U, 0),
    "af0": (40, 22, S, P2_N31),
    "af1": (62, 16, S, P2_N43),
    "af2": (78, 8, S, P2_N55),
    "ura": (86, 4, U, 0),
    "toc": (90, 16, U, 16),
    "tgd": (106, 8, S, P2_N31),
    "deltan": (114, 22, S, P2_N41),
    "iodec": (136, 8, U, 1),
    "_reserved1": (144, 10, U, 0),
    "l5flag": (154, 1, U, 0),
    "sflag": (155, 1, U, 0),
    "cuc": (156, 15, S, P2_N28),
    "cus": (171, 15, S, P2_N28),
    "cic": (186, 15, S, P2_N28),
    "cis": (201, 15, S, P2_N28),
    "crc": (216, 15, S, P2_N4),
    "crs": (231, 15, S, P2_N4),
    "idot": (246, 14, S, P2_N43),
    "_reserved2": (260, 2, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_2 = {
    **IRN_LNAV_SUBFRAME_TLM,
    "m0": (30, 32, S, P2_N31),
    "toe": (62, 16, U, 16),
    "e": (78, 32, U, P2_N33),
    "sqrta": (110, 32, U, P2_N19),
    "omega0": (142, 32, S, P2_N31),
    "omega": (174, 32, S, P2_N31),
    "omegadot": (206, 22, S, P2_N41),
    "i0": (228, 32, S, P2_N31),
    "_reserved1": (260, 2, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_3_P9 = {
    **IRN_LNAV_SUBFRAME_TLM,
    SPID: (30, 6, U, 0),
    "a0utc": (36, 16, S, P2_N35),
    "a1utc": (52, 13, S, P2_N51),
    "a2utc": (65, 7, S, P2_N68),
    "deltatls": (72, 8, S, 1),
    "toutc": (80, 16, U, P2_P4),
    "wnoutc": (96, 10, U, 1),
    "wnlsf": (106, 10, U, 1),
    "dn": (116, 4, U, 1),
    "deltatlsf": (120, 8, S, 1),
    "a0": (128, 16, S, P2_N35),
    "a1": (144, 13, S, P2_N51),
    "a2": (157, 7, S, P2_N68),
    "tot": (164, 16, U, P2_P4),
    "wnot": (180, 10, U, 1),
    "gnssid": (190, 3, U, 0),
    "_reserved1": (193, 63, U, 0),
    "prn": (256, 6, U, 0),
    **IRN_LNAV_SUBFRAME_END,
}

IRN_LNAV_SUBFRAME_3_P11 = {
    **IRN_LNAV_SUBFRAME_TLM,
    SPID: (30, 6, U, 0),
    "teop": (36, 16, S, P2_P4),
    "pmx": (52, 21, S, P2_N20),
    "pmxdot": (73, 15, S, P2_N21),
    "pmy": (88, 21, S, P2_N20),
    "pmydot": (109, 15, S, P2_N21),
    "deltaut1": (124, 31, S, P2_N24),
    "deltautdot1": (155, 19, S, P2_N25),
    "alpha0": (174, 8, S, P2_N30),
    "alpha1": (182, 8, S, P2_N27),
    "alpha2": (190, 8, S, P2_N24),
    "alpha3": (198, 8, S, P2_N24),
    "beta0": (206, 8, S, P2_P11),
    "beta1": (214, 8, S, P2_P14),
    "beta2": (222, 8, S, P2_P16),
    "beta3": (230, 8, S, P2_P16),
    "_reserved1": (238, 18, U, 0),
    "prn": (256, 6, U, 0),
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
