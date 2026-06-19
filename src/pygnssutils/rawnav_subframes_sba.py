"""
rawnav_subframes_sba.py

SBAS NAV Subframe (Message Type) definitions.

ICAO Standards and Recommended Practices (SARPS) Annex10 Volume I (Radio Navigation Aids)
https://www.bazl.admin.ch/dam/en/sd-web/8uK1mTR6IvZh/AN10_V1_cons.pdf
L1C/A: https://gnss-x.ac.cn/docs/RTCA-DO-229D.pdf
A.4.4.11 GEO Navigation Message Type 9
A.4.4.12 ALMANAC Navigation Message Type 17
A.4.4.15 Network Time/UTC/GLONASS Time Offset Parameters Message Type 12

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

from pygnssutils.rawnav import PREAMBLE, SID, TOW, WN, S, U
from pygnssutils.rinex_globals import (
    L1CA,
    P2_N30,
    P2_N31,
    P2_N40,
    P2_N50,
    P2_P12,
    START,
    TARGET,
)

# **********************************************************************
# L1CA - "1C"
# **********************************************************************

# SBAS ICD (RTCA-DO-229D) refers to subframes as 'Message Types' (MT)

SBA_L1CA_MT_TLM = {
    PREAMBLE: (0, 8, U, 0),
    SID: (8, 6, U, 0),  # MT record number
}

SBA_L1CA_MT_END = {
    "_parity": (226, 24, U, 0),
}

# attribute_name: (bit offset, bit length, bit encoding, scaling)
SBA_L1CA_MT_9 = {
    **SBA_L1CA_MT_TLM,
    "iodn": (14, 8, U, 0),  # marked as reserved
    "t0": (22, 13, U, 16),
    "ura": (35, 4, U, 0),  # 15 = do not use for ranging
    "xpos": (39, 30, S, 0.08),
    "ypos": (69, 30, S, 0.08),
    "zpos": (99, 25, S, 0.4),
    "xdot": (124, 17, S, 0.000625),
    "ydot": (141, 17, S, 0.000625),
    "zdot": (158, 18, S, 0.004),
    "xdot2": (176, 10, S, 0.0000125),
    "ydot2": (186, 10, S, 0.0000125),
    "zdot2": (196, 10, S, 0.0000625),
    "agf0": (206, 12, S, P2_N31),
    "agf1": (218, 8, S, P2_N40),
    **SBA_L1CA_MT_END,
}

SBA_L1CA_MT_12 = {
    **SBA_L1CA_MT_TLM,
    "a1": (14, 24, S, P2_N50),
    "a0": (38, 32, S, P2_N30),
    "toc": (70, 8, U, P2_P12),  # tot
    "wnt": (78, 8, U, 1),
    "deltatls": (86, 8, S, 1),
    "wnlsf": (94, 8, U, 1),
    "dn": (102, 8, U, 1),
    "deltatlsf": (110, 8, S, 1),
    "utcid": (118, 3, U, 1),  # see UTCID lookup
    TOW: (121, 20, U, 1),
    WN: (141, 10, U, 1),
    "gloind": (151, 1, U, 0),
    "deltatglo": (152, 74, U, 0),
    **SBA_L1CA_MT_END,
}

SBA_L1CA_MT_17 = {
    **SBA_L1CA_MT_TLM,
    "dataid_01": (14, 2, U, 0),
    "prn_01": (16, 8, U, 0),
    "svhealth_01": (24, 8, U, 0),
    # Bit 0 (LSB) Ranging On (0), Off (1); 1 = do not use for ranging
    # Bit 1 Corrections On (0), Off (1); 1 = do not use for corrections
    # Bit 2 Broadcast Integrity On (0), Off (1)
    # Bits 3 Reserved
    # Bits 4-7 Service Provider ID
    "xg_01": (32, 15, S, 2600),
    "yg_01": (47, 15, S, 2600),
    "zg_01": (62, 9, S, 26000),
    "xgdot_01": (71, 3, S, 10),
    "ygdot_01": (74, 3, S, 10),
    "zgdot_01": (77, 4, S, 60),
    "dataid_02": (81, 2, U, 0),
    "prn_02": (83, 8, U, 0),
    "svhealth_02": (91, 8, U, 0),
    "xg_02": (99, 15, S, 2600),
    "yg_02": (114, 15, S, 2600),
    "zg_02": (129, 9, S, 26000),
    "xgdot_02": (138, 3, S, 10),
    "ygdot_02": (141, 3, S, 10),
    "zgdot_02": (144, 4, S, 60),
    "dataid_03": (148, 2, U, 0),
    "prn_03": (150, 8, U, 0),
    "svhealth_03": (158, 8, U, 0),
    "xg_03": (166, 15, S, 2600),
    "yg_03": (181, 15, S, 2600),
    "zg_03": (196, 9, S, 26000),
    "xgdot_03": (205, 3, S, 10),
    "ygdot_03": (208, 3, S, 10),
    "zgdot_03": (211, 4, S, 60),
    "t0": (215, 11, S, 64),
    **SBA_L1CA_MT_END,
}

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
SBA_SUBFRAMEACQ_MAP = {
    L1CA: {
        TARGET: 0b111,  # Message Type (MT) codes 9,12 (17 optional)
        START: 9,
        (9, 0): (SBA_L1CA_MT_9, 1),
        (12, 0): (SBA_L1CA_MT_12, 2),
        (17, 0): (SBA_L1CA_MT_17, 4),
    },
}
