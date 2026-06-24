"""
rawnav_subframes_gal.py

Galileo NAV Subframe definitions.

E1,E5a,E6: https://www.gsc-europa.eu/sites/default/files/sites/all/files/Galileo_OS_SIS_ICD_v2.1.pdf

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

# pylint: disable=fixme

from pygnssutils.rawnav import SID, TOC, TOW, WN, S, U
from pygnssutils.rinex_globals import (
    FNAV,
    INAV,
    P2_N2,
    P2_N5,
    P2_N8,
    P2_N9,
    P2_N14,
    P2_N15,
    P2_N16,
    P2_N19,
    P2_N22,
    P2_N26,
    P2_N29,
    P2_N30,
    P2_N31,
    P2_N32,
    P2_N33,
    P2_N34,
    P2_N35,
    P2_N38,
    P2_N43,
    P2_N46,
    P2_N50,
    P2_N51,
    P2_N59,
    P2_P8,
    START,
    TARGET,
)

# **********************************************************************
# FNAV - "5I" (E5a-I)
# **********************************************************************

# preamble = 0b101101110000

GAL_FNAV_SUBFRAME = {
    "word": (0, 244, U, 0),
    "padding": (244, 12, U, 0),
}  # 8 * 32-bit dwrds

GAL_FNAV_SUBFRAME_TLM = {
    SID: (0, 6, U, 0),  # subframe id
}

GAL_FNAV_CRC = {
    "_parity": (214, 24, U, 0),
    "_tail": (238, 6, U, 0),
}

GAL_FNAV_SUBFRAME_GENERIC = {
    **GAL_FNAV_SUBFRAME_TLM,
    "payload": (6, 208, U, 0),
    **GAL_FNAV_CRC,
}

# SVID, Clock correction, SISA, Ionospheric correction (NEQUICK-G),
# BGD, GST, Signal health and Data validity status
GAL_FNAV_SUBFRAME_1 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "sv": (6, 6, U, 0),
    "iodn": (12, 10, U, 0),
    TOC: (22, 14, U, 60),
    "af0": (36, 31, S, P2_N34),
    "af1": (67, 21, S, P2_N46),
    "af2": (88, 6, S, P2_N59),
    "sisa": (94, 8, U, 0),
    "ai0": (102, 11, U, P2_N2),
    "ai1": (113, 11, S, P2_N8),
    "ai2": (124, 14, S, P2_N15),
    "idf1": (138, 1, U, 0),
    "idf2": (139, 1, U, 0),
    "idf3": (140, 1, U, 0),
    "idf4": (141, 1, U, 0),
    "idf5": (142, 1, U, 0),
    "bgde5a": (143, 10, S, P2_N32),
    "e5ahs": (153, 2, U, 0),
    WN: (155, 12, U, 1),  # used to derive epoch
    TOW: (167, 20, U, 1),  # used to derive epoch
    "e5advs": (187, 1, U, 0),
    "_spare": (188, 26, U, 0),
    **GAL_FNAV_CRC,
}

# Ephemeris (1/3) and GST
GAL_FNAV_SUBFRAME_2 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (6, 10, U, 0),
    "m0": (16, 32, S, P2_N31),
    "omegadot": (48, 24, S, P2_N43),
    "e": (72, 32, U, P2_N33),
    "sqrta": (104, 32, U, P2_N19),
    "omega0": (136, 32, S, P2_N31),
    "idot": (168, 14, S, P2_N43),
    WN: (182, 12, U, 1),
    TOW: (194, 20, U, 1),
    **GAL_FNAV_CRC,
}

# Ephemeris (2/3) and GST
GAL_FNAV_SUBFRAME_3 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (6, 10, U, 0),
    "i0": (16, 32, S, P2_N31),
    "omega": (48, 32, S, P2_N31),
    "deltan": (80, 16, S, P2_N43),
    "cuc": (96, 16, S, P2_N29),
    "cus": (112, 16, S, P2_N29),
    "crc": (128, 16, S, P2_N5),
    "crs": (144, 16, S, P2_N5),
    "toe": (160, 14, U, 60),
    WN: (174, 12, U, 1),
    TOW: (186, 20, U, 1),
    "_spare": (206, 8, U, 0),
    **GAL_FNAV_CRC,
}

# Ephemeris (3/3), GST-UTC conversion, GST-GPS conversion and TOW.
GAL_FNAV_SUBFRAME_4 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (6, 10, U, 0),
    "cic": (16, 16, S, P2_N29),
    "cis": (32, 16, S, P2_N29),
    "a0": (48, 32, S, P2_N30),
    "a1": (80, 24, S, P2_N50),
    "deltatls": (104, 8, S, 1),
    "tot": (112, 8, U, 3600),
    "wn0t": (120, 8, U, 1),
    "wnlsf": (128, 8, U, 1),
    "dn": (136, 3, U, 1),
    "deltatlsf": (139, 8, S, 1),
    "t0g": (147, 8, U, 3600),
    "a0g": (155, 16, S, P2_N35),
    "a1g": (171, 12, S, P2_N51),
    "wn0g": (183, 6, U, 1),
    TOW: (189, 20, U, 0),
    "_spare": (209, 5, U, 0),
    **GAL_FNAV_CRC,
}

# Almanac (SVID1 and SVID2(1/2)), Week Number and almanac reference time
GAL_FNAV_SUBFRAME_5 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "ioda": (6, 4, U, 0),
    "wna": (10, 2, U, 1),
    "t0a": (12, 10, U, 600),
    "sv1": (22, 6, U, 0),
    "sv1_deltasqrta": (28, 13, S, P2_N9),
    "sv1_e": (41, 11, U, P2_N16),
    "sv1_omega": (52, 16, S, P2_N15),
    "sv1_deltai": (68, 11, S, P2_N14),
    "sv1_omega0": (79, 16, S, P2_N15),
    "sv1_omegadot": (95, 11, S, P2_N33),
    "sv1_m0": (106, 16, S, P2_N15),
    "sv1_af0": (122, 16, S, P2_N19),
    "sv1_af1": (138, 13, S, P2_N38),
    "sv1_e5ahs": (151, 2, U, 0),
    "sv2": (153, 6, U, 0),
    "sv2_deltasqrta": (159, 13, S, P2_N9),
    "sv2_e": (172, 11, U, P2_N16),
    "sv2_omega": (183, 16, S, P2_N15),
    "sv2_deltai": (199, 11, S, P2_N14),
    "sv2_omega0_msb": (210, 4, S, P2_N15),
    **GAL_FNAV_CRC,
}

# Almanac (SVID2(2/2) and SVID3)
GAL_FNAV_SUBFRAME_6 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "ioda": (6, 4, U, 0),
    "sv2_omega0_lsb": (10, 12, S, P2_N15),
    "sv2_omegadot": (22, 11, S, P2_N33),
    "sv2_m0": (33, 16, S, P2_N15),
    "sv2_af0": (49, 16, S, P2_N19),
    "sv2_af1": (65, 13, S, P2_N38),
    "sv2_e5ahs": (78, 2, U, 0),
    "sv3": (80, 6, U, 0),
    "sv3_deltasqrta": (86, 13, S, P2_N9),
    "sv3_e": (99, 11, U, P2_N16),
    "sv3_omega": (110, 16, S, P2_N15),
    "sv3_deltai": (126, 11, S, P2_N14),
    "sv3_omega0": (137, 16, S, P2_N15),
    "sv3_omegadot": (153, 11, S, P2_N33),
    "sv3_m0": (164, 16, S, P2_N15),
    "sv3_af0": (180, 16, S, P2_N19),
    "sv3_af1": (196, 13, S, P2_N38),
    "sv3_e5ahs": (209, 2, U, 0),
    "_spare": (211, 3, U, 0),
    **GAL_FNAV_CRC,
}

# **********************************************************************
# INAV - "7I" (E5b-I), "1B" (E1-B)
# **********************************************************************

# preamble = 0b0101100000

GAL_INAV_SUBFRAME = {
    "eo1": (0, 1, U, 0),
    "pagetype1": (1, 1, U, 0),  # 0 = nominal, 1 = alert
    "word_msb": (2, 112, U, 0),  # 6 msb is word number
    "tail1": (114, 6, U, 0),
    "padding1": (120, 8, U, 0),
    "eo2": (128, 1, U, 0),
    "pagetype2": (129, 1, U, 0),
    "word_lsb": (130, 16, U, 0),
    "reserved1": (146, 40, U, 0),
    "sar": (186, 22, U, 0),  # E-1B only, else reserved
    "spare": (208, 2, U, 0),
    "crc": (210, 24, U, 0),
    "ssp": (234, 8, U, 0),
    "tail2": (242, 6, U, 0),
    "padding2": (248, 8, U, 0),
}  # 8 * 32-bit dwrds

# Ephemeris (1/4)
GAL_INAV_WORD_1 = {
    SID: (0, 6, U, 0),
    "iodn": (6, 10, U, 0),
    "toe": (16, 14, U, 60),
    "m0": (30, 32, S, P2_N31),
    "e": (62, 32, U, P2_N33),
    "sqrta": (94, 32, U, P2_N19),
    "_spare": (126, 2, U, 0),
}

# Ephemeris (2/4)
GAL_INAV_WORD_2 = {
    SID: (0, 6, U, 0),
    "iodn": (6, 10, U, 0),
    "omega0": (16, 32, S, P2_N31),
    "i0": (48, 32, S, P2_N31),
    "omega": (80, 32, S, P2_N31),
    "idot": (112, 14, S, P2_N43),
    "_spare": (126, 2, U, 0),
}

# Ephemeris (3/4) and SISA
GAL_INAV_WORD_3 = {
    SID: (0, 6, U, 0),
    "iodn": (6, 10, U, 0),
    "omegadot": (16, 24, S, P2_N43),
    "deltan": (40, 16, S, P2_N43),
    "cuc": (56, 16, S, P2_N29),
    "cus": (72, 16, S, P2_N29),
    "crc": (88, 16, S, P2_N5),
    "crs": (104, 16, S, P2_N5),
    "sisa": (120, 8, U, 0),
}

# SVID, Ephemeris (4/4), and Clock correction parameters
GAL_INAV_WORD_4 = {
    SID: (0, 6, U, 0),
    "iodn": (6, 10, U, 0),
    "sv": (16, 6, U, 0),
    "cic": (22, 16, S, P2_N29),
    "cis": (38, 16, S, P2_N29),
    TOC: (54, 14, U, 60),
    "af0": (68, 31, S, P2_N34),
    "af1": (99, 21, S, P2_N46),
    "af2": (120, 6, S, P2_N59),
    "_spare": (126, 2, U, 0),
}

# Ionospheric correction, BGD, signal health and data validity status and GST
GAL_INAV_WORD_5 = {
    SID: (0, 6, U, 0),
    "ai0": (6, 11, U, P2_N2),
    "ai1": (17, 11, S, P2_N8),
    "ai2": (28, 14, S, P2_N15),
    "idf1": (42, 1, U, 0),
    "idf2": (43, 1, U, 0),
    "idf3": (44, 1, U, 0),
    "idf4": (45, 1, U, 0),
    "idf5": (46, 1, U, 0),
    "bgde5a": (47, 10, S, P2_N32),
    "bgde5b": (57, 10, S, P2_N32),
    "e5ahs": (67, 2, U, 0),
    "e5bhs": (69, 2, U, 0),
    "e5advs": (71, 1, U, 0),
    "e5bdvs": (72, 1, U, 0),
    WN: (73, 12, U, 1),  # used to derive epoch
    TOW: (85, 20, U, 1),  # used to derive epoch
    "_spare": (105, 23, U, 0),
}

# GST-UTC conversion parameters
GAL_INAV_WORD_6 = {
    SID: (0, 6, U, 0),
    "a0": (6, 32, S, P2_N30),
    "a1": (38, 24, S, P2_N50),
    "deltatls": (62, 8, S, 1),
    "tot": (70, 8, U, 3600),
    "wn0t": (78, 8, U, 1),
    "wnlsf": (86, 8, U, 1),
    "dn": (94, 3, U, 1),
    "deltatlsf": (97, 8, S, 1),
    TOW: (105, 20, U, 1),
    "_spare": (125, 3, U, 0),
}

# Almanac for SVID1 (1/2), almanac reference time and almanac reference week number
GAL_INAV_WORD_7 = {
    SID: (0, 6, U, 0),
    "ioda": (6, 4, U, 0),
    "wna": (10, 2, U, 1),
    "t0a": (12, 10, U, 600),
    "sv1": (22, 6, U, 0),
    "sv1_deltasqrta": (28, 13, S, P2_N9),
    "sv1_e": (41, 11, U, P2_N16),
    "sv1_omega": (52, 16, S, P2_N15),
    "sv1_deltai": (68, 11, S, P2_N14),
    "sv1_omega0": (79, 16, S, P2_N15),
    "sv1_omegadot": (95, 11, S, P2_N33),
    "sv1_m0": (106, 16, S, P2_N15),
    "_reserved": (122, 6, U, 0),
}

# Almanac for SVID1 (2/2) and SVID2 (1/2))
GAL_INAV_WORD_8 = {
    SID: (0, 6, U, 0),
    "ioda": (6, 4, U, 0),
    "sv1_af0": (10, 16, S, P2_N19),
    "sv1_af1": (26, 13, S, P2_N38),
    "sv1_e5ahs": (39, 2, U, 0),
    "sv1_e5bhs": (41, 2, U, 0),
    "sv2": (43, 6, U, 0),
    "sv2_deltasqrta": (49, 13, S, P2_N9),
    "sv2_e": (62, 11, U, P2_N16),
    "sv2_omega": (73, 16, S, P2_N15),
    "sv2_deltai": (89, 11, S, P2_N14),
    "sv2_omega0": (100, 16, S, P2_N15),
    "sv2_omegadot": (116, 11, S, P2_N33),
    "_spare": (127, 1, U, 0),
}

# Almanac for SVID2 (2/2) and SVID3 (1/2))
GAL_INAV_WORD_9 = {
    SID: (0, 6, U, 0),
    "ioda": (6, 4, U, 0),
    "wna": (10, 2, U, 1),
    "t0a": (12, 10, U, 600),
    "sv2_m0": (22, 16, S, P2_N15),
    "sv2_af0": (38, 16, S, P2_N19),
    "sv2_af1": (54, 13, S, P2_N38),
    "sv2_e5ahs": (67, 2, U, 0),
    "sv2_e5bhs": (69, 2, U, 0),
    "sv3": (71, 6, U, 0),
    "sv3_deltasqrta": (77, 13, S, P2_N9),
    "sv3_e": (90, 11, U, P2_N16),
    "sv3_omega": (101, 16, S, P2_N15),
    "sv3_deltai": (117, 11, S, P2_N14),
}

# Almanac for SVID3 (2/2) and GST-GPS conversion parameters
GAL_INAV_WORD_10 = {
    "wordid": (0, 6, U, 0),
    "ioda": (6, 4, U, 0),
    "sv3_omega0": (10, 16, S, P2_N15),
    "sv3_omegadot": (26, 11, S, P2_N33),
    "sv3_m0": (37, 16, S, P2_N15),
    "sv3_af0": (53, 16, S, P2_N19),
    "sv3_af1": (69, 13, S, P2_N38),
    "sv3_e5ahs": (82, 2, U, 0),
    "sv3_e5bhs": (84, 2, U, 0),
    "a0g": (86, 16, S, P2_N35),
    "a1g": (102, 12, S, P2_N51),
    "t0g": (114, 8, U, 3600),
    "wn0g": (122, 6, U, 1),
}

# Reduced Clock and Ephemeris Data (CED) parameters
GAL_INAV_WORD_16 = {
    SID: (0, 6, U, 0),
    "deltaared": (6, 5, S, P2_P8),
    "exred": (11, 13, S, P2_N22),
    "eyred": (24, 13, S, P2_N22),
    "deltaiored": (37, 17, S, P2_N22),
    "omega0red": (54, 23, S, P2_N22),
    "lambda0red": (77, 23, S, P2_N22),
    "af0red": (100, 22, S, P2_N26),
    "af1red": (122, 6, S, P2_N35),
}

# dummy word
GAL_INAV_WORD_0 = {
    SID: (0, 6, U, 0),
    "time": (6, 2, U, 0),
    "_spare": (8, 88, U, 0),
    WN: (96, 12, U, 1),
    TOW: (108, 20, U, 1),
}

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
GAL_SUBFRAMEACQ_MAP = {
    FNAV: {
        TARGET: 0b1111,  # subframes 1,2,3,4
        START: 1,
        (1, 0): (GAL_FNAV_SUBFRAME_1, 1),
        (2, 0): (GAL_FNAV_SUBFRAME_2, 2),
        (3, 0): (GAL_FNAV_SUBFRAME_3, 4),
        (4, 0): (GAL_FNAV_SUBFRAME_4, 8),
        (5, 0): (GAL_FNAV_SUBFRAME_5, 16),
        (6, 0): (GAL_FNAV_SUBFRAME_6, 32),
    },
    INAV: {
        TARGET: 0b111111,  # subframes 1,2,3,4,5,6
        START: 1,
        (1, 0): (GAL_INAV_WORD_1, 1),
        (2, 0): (GAL_INAV_WORD_2, 2),
        (3, 0): (GAL_INAV_WORD_3, 4),
        (4, 0): (GAL_INAV_WORD_4, 8),
        (5, 0): (GAL_INAV_WORD_5, 16),
        (6, 0): (GAL_INAV_WORD_6, 32),
        (7, 0): (GAL_INAV_WORD_7, 64),
        (8, 0): (GAL_INAV_WORD_8, 128),
        (9, 0): (GAL_INAV_WORD_9, 256),
        (10, 0): (GAL_INAV_WORD_10, 512),
        (16, 0): (GAL_INAV_WORD_16, 1024),
    },
}
