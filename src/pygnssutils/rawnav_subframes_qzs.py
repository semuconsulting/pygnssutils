"""
rawnav_subframes_qzss.py

QZSS NAV Subframe (Message Type) definitions.

L1C/A,L2CM, L2CL, L5I:
https://qzss.go.jp/en/technical/download/pdf/ps-is-qzss/is-qzss-pnt-006.pdf?t=1782205084546
L1S: https://qzss.go.jp/en/technical/ps-is-qzss/is_qzss_l1s_007_agree.html

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

from pygnssutils.rawnav import PREAMBLE, SID, SPID, TOC, TOW, WN, S, U
from pygnssutils.rinex_globals import (
    CNAV,
    CNV2,
    LNAV,
    P2_N5,
    P2_N8,
    P2_N9,
    P2_N19,
    P2_N20,
    P2_N21,
    P2_N23,
    P2_N24,
    P2_N25,
    P2_N27,
    P2_N29,
    P2_N30,
    P2_N31,
    P2_N32,
    P2_N33,
    P2_N34,
    P2_N35,
    P2_N43,
    P2_N44,
    P2_N48,
    P2_N50,
    P2_N51,
    P2_N55,
    P2_N57,
    P2_N60,
    P2_N68,
    P2_P4,
    P2_P11,
    P2_P12,
    P2_P14,
    P2_P16,
    START,
    TARGET,
)

# **********************************************************************
# LNAV - "1C" (L1C/A, L1C/B) - SAME AS GPS LNAV
# **********************************************************************

# attribute_name: (bit offset, bit length, bit encoding, scaling)
QZS_LNAV_TLM = {
    PREAMBLE: (0, 8, U, 0),
    "tlm": (8, 14, U, 0),
    "integrity": (22, 1, U, 0),
    "_reserved1": (23, 1, U, 0),
    "_parity1": (24, 6, U, 0),
}

QZS_LNAV_HOW = {
    TOW: (30, 17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (47, 1, U, 0),
    "antispoof": (48, 1, U, 0),
    SID: (49, 3, U, 0),  # subframe id
    "_non1": (52, 2, U, 0),
    "_parity2": (54, 6, U, 0),
}

QZS_LNAV_GENERIC = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # words 3 - 10
    "_word3_10": (60, 240, U, 0),
}

QZS_LNAV_SUBFRAME_1 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    WN: (60, 10, U, 1),  # used to derive epoch
    "l2codes": (70, 2, U, 1),
    "ura": (72, 4, U, 1),
    "svhealth": (76, 6, U, 1),
    # "l1health": (76,1,U,0),
    # "l1cahealth": (77,1,U,0),
    # "l2health": (78,1,U,0),
    # "l5health": (79,1,U,0),
    # "l1chealth": (80,1,U,0),
    # "l1cbhealth": (81,1,U,0),
    "iodc_msb": (82, 2, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "l2pdata": (90, 1, U, 1),
    "_reserved2": (91, 23, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "_reserved3": (120, 24, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "_reserved4": (150, 24, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "_reserved5": (180, 16, U, 0),
    "tgd": (196, 8, S, P2_N31),
    "_parity7": (204, 6, U, 0),
    # word8
    "iodc_lsb": (210, 8, U, 0),
    TOC: (218, 16, U, P2_P4),  # must be named "toc"
    "_parity8": (234, 6, U, 0),
    # word9
    "af2": (240, 8, S, P2_N55),
    "af1": (248, 16, S, P2_N43),
    "_parity9": (264, 6, U, 0),
    # word10
    "af0": (270, 22, S, P2_N31),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

QZS_LNAV_SUBFRAME_2 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "iode": (60, 8, U, 0),
    "crs": (68, 16, S, P2_N5),
    "_parity3": (84, 6, U, 0),
    # word4
    "deltan": (90, 16, S, P2_N43),
    "m0_msb": (106, 8, S, P2_N31),
    "_parity4": (114, 6, U, 0),
    # word5
    "m0_lsb": (120, 24, S, P2_N31),
    "_parity5": (144, 6, U, 0),
    # word6
    "cuc": (150, 16, S, P2_N29),
    "e_msb": (166, 8, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "e_lsb": (180, 24, U, P2_N33),
    "_parity7": (204, 6, U, 0),
    # word8
    "cus": (210, 16, S, P2_N29),
    "sqrta_msb": (226, 8, U, P2_N19),
    "_parity8": (234, 6, U, 0),
    # word9
    "sqrta_lsb": (240, 24, U, P2_N19),
    "_parity9": (264, 6, U, 0),
    # word10
    "toe": (270, 16, U, P2_P4),
    "fit": (286, 1, U, 0),
    "aodo": (287, 5, U, 900),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

QZS_LNAV_SUBFRAME_3 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "cic": (60, 16, S, P2_N29),
    "omega0_msb": (76, 8, S, P2_N31),
    "_parity3": (84, 6, U, 0),
    # word4
    "omega0_lsb": (90, 24, S, P2_N31),
    "_parity4": (114, 6, U, 0),
    # word5
    "cis": (120, 16, S, P2_N29),
    "i0_msb": (136, 8, S, P2_N31),
    "_parity5": (144, 6, U, 0),
    # word6
    "i0_lsb": (150, 24, S, P2_N31),
    "_parity6": (174, 6, U, 0),
    # word7
    "crc": (180, 16, S, P2_N5),
    "omega_msb": (196, 8, S, P2_N31),
    "_parity7": (204, 6, U, 0),
    # word8
    "omega_lsb": (210, 24, S, P2_N31),
    "_parity8": (234, 6, U, 0),
    # word9
    "omegadot": (240, 24, S, P2_N43),
    "_parity9": (264, 6, U, 0),
    # word10
    "iode": (270, 8, U, 0),
    "idot": (278, 14, S, P2_N43),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

QZS_LNAV_SUBFRAME_4_P56 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),  # = 3
    SPID: (62, 6, U, 0),  # = 56
    "alpha0": (68, 8, S, P2_N30),
    "alpha1": (76, 8, S, P2_N27),
    "_parity3": (84, 6, U, 0),
    # word4
    "alpha2": (90, 8, S, P2_N24),
    "alpha3": (98, 8, S, P2_N24),
    "beta0": (106, 8, S, P2_P11),
    "_parity4": (114, 6, U, 0),
    # word5
    "beta1": (120, 8, S, P2_P14),
    "beta2": (128, 8, S, P2_P16),
    "beta3": (136, 8, S, P2_P16),
    "_parity5": (144, 6, U, 0),
    # word6
    "a1": (150, 24, S, P2_N30),
    "_parity6": (174, 6, U, 0),
    # word7
    "a0_msb": (180, 24, S, P2_N50),
    "_parity7": (204, 6, U, 0),
    # word8
    "a0_lsb": (210, 8, S, P2_N50),
    "tot": (218, 8, U, P2_P12),
    "wnt": (226, 8, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "deltatls": (240, 8, S, 1),
    "wnlsf": (248, 8, U, 0),
    "dn": (256, 8, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "deltatlsf": (270, 8, S, 1),
    "_reserved2": (278, 14, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

QZS_LNAV_SUBFRAME_5_P56 = QZS_LNAV_SUBFRAME_4_P56

# **********************************************************************
# CNAV - "2S","2L","5I","5Q" (L2C, L5) - SAME AS GPS CNAV
# **********************************************************************

QZS_CNAV_TLM = {
    # VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
    PREAMBLE: (0, 8, U, 0),
    "prn": (8, 6, U, 0),
    SID: (14, 6, U, 0),
    TOW: (20, 17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (37, 1, U, 0),
}

QZS_CNAV_CLOCK = {
    "top": (38, 11, U, 300),
    "uraned0": (49, 5, S, 0),
    "uraned1": (54, 3, U, 0),
    "uraned2": (57, 3, U, 0),
    TOC: (60, 11, U, 300),
    "af0n": (71, 26, S, P2_N35),
    "af1n_msb": (97, 3, S, P2_N48),
    "af1n_lsb": (100, 17, S, P2_N48),
    "af2n": (117, 10, S, P2_N60),
}

QZS_CNAV_PARITY = {
    "_parity": (276, 24, U, 0),
}

QZS_CNAV_SUBFRAME_10 = {
    **QZS_CNAV_TLM,
    WN: (38, 13, U, 0),  # used to derive epoch
    "l1health": (51, 1, U, 0),
    "l2health": (52, 1, U, 0),
    "l5health": (53, 1, U, 0),
    "top": (54, 11, U, 300),
    "uraed": (65, 5, U, 0),
    "toe": (70, 11, U, 300),
    "deltaa_msb": (81, 19, S, P2_N9),
    "deltaa_lsb": (100, 7, S, P2_N9),
    "adot": (107, 25, S, P2_N21),
    "deltan0": (132, 17, S, P2_N44),
    "deltan0dot": (149, 23, S, P2_N57),
    "m0_msb": (172, 28, S, P2_N32),
    "m0_lsb": (200, 5, S, P2_N32),
    "e": (205, 33, U, P2_N34),
    "omega": (238, 33, S, P2_N32),
    "integrity": (271, 1, U, 0),
    "l2phase": (272, 1, U, 0),
    "_reserved1": (273, 3, U, 0),
    **QZS_CNAV_PARITY,
}  # Ephemeris 1

QZS_CNAV_SUBFRAME_11 = {
    **QZS_CNAV_TLM,
    "toe": (38, 11, U, 300),
    "omega0": (49, 33, S, P2_N32),
    "i0_msb": (82, 18, S, P2_N32),
    "i0_lsb": (100, 15, S, P2_N32),
    "deltaomegadot": (115, 17, S, P2_N44),
    "idot": (132, 15, S, P2_N44),
    "cis": (147, 16, S, P2_N30),
    "cic": (163, 16, S, P2_N30),
    "crs_msb": (179, 21, S, P2_N8),
    "crs_lsb": (200, 3, S, P2_N8),
    "crc": (203, 24, S, P2_N8),
    "cus": (227, 21, S, P2_N30),
    "cuc": (248, 21, S, P2_N30),
    "_reserved1": (269, 7, U, 0),
    **QZS_CNAV_PARITY,
}  # Ephemeris 2

QZS_CNAV_SUBFRAME_30 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "tgd": (127, 13, S, P2_N35),
    "iscl1ca": (140, 13, S, P2_N35),
    "iscl2c": (153, 13, S, P2_N35),
    "iscl5i5": (166, 13, S, P2_N35),
    "iscl5q5": (179, 13, S, P2_N35),
    "alpha0": (192, 8, U, P2_N30),  # where is scaling defined for CNAV?
    "alpha1": (200, 8, U, P2_N27),  # have assumed same as LNAV
    "alpha2": (208, 8, U, P2_N24),
    "alpha3": (216, 8, U, P2_N24),
    "beta0": (224, 8, U, P2_P11),
    "beta1": (232, 8, U, P2_P14),
    "beta2": (240, 8, U, P2_P16),
    "beta3": (248, 8, U, P2_P16),
    "wno": (256, 8, U, 0),
    "_reserved1": (264, 12, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock, IONO & Group Delay

QZS_CNAV_SUBFRAME_32 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "teop": (127, 16, U, P2_P4),
    "pmx": (143, 21, S, P2_N20),
    "pmxdot": (164, 15, S, P2_N21),
    "pmy": (179, 21, S, P2_N20),
    "pmydot": (200, 15, S, P2_N21),
    "deltautgps": (215, 31, S, P2_N23),
    "deltautgpsdot": (246, 19, S, P2_N25),
    "_reserved1": (265, 11, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock & EOP

QZS_CNAV_SUBFRAME_33 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "a0": (127, 16, S, P2_N35),
    "a1": (143, 13, S, P2_N51),
    "a2": (156, 7, S, P2_N68),
    "deltatls": (163, 8, S, 1),
    "tot": (171, 16, U, P2_P4),
    "wnot": (187, 13, U, 1),
    "wnlsf": (200, 13, U, 1),
    "dn": (213, 4, U, 1),
    "deltatlsf": (217, 8, S, 1),
    "_reserved1": (225, 51, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock & UTC

# **********************************************************************
# CNV2 - "1S" (L1S)
# **********************************************************************

QZS_CNV2_SUBFRAME_1 = {"toi": (0, 9, U, 18)}

QZS_CNV2_SUBFRAME_2 = {
    WN: (0, 13, U, 1),
    "itow": (13, 8, U, 1),
    "top": (21, 11, U, 300),
    "l1chealth": (32, 1, U, 1),
    "uraed": (33, 5, S, 1),
    "toe": (38, 11, U, 300),
    "deltaa": (49, 26, S, P2_N9),
    "adot": (75, 25, S, P2_N21),
    "deltan0": (100, 17, S, P2_N44),
    "deltan0dot": (117, 23, S, P2_N57),
    "m0_msb": (140, 10, S, P2_N32),
    "m0_lsb": (150, 23, S, P2_N32),
    "e": (173, 33, S, P2_N34),
    "omega": (206, 33, S, P2_N32),
    "omega0": (239, 33, S, P2_N32),
    "i0_msb": (272, 28, S, P2_N32),
    "i0_lsb": (300, 5, S, P2_N32),
    "deltanomegadot": (305, 17, S, P2_N44),
    "idot": (322, 15, S, P2_N44),
    "cis": (337, 16, S, P2_N30),
    "cic": (353, 16, S, P2_N30),
    "crs": (369, 24, S, P2_N8),
    "crc": (393, 24, S, P2_N8),
    "cus": (417, 21, S, P2_N30),
    "cuc_msb": (438, 12, S, P2_N30),
    "cuc_lsb": (450, 9, S, P2_N30),
    "uraned0": (459, 5, S, 1),
    "uraned1": (464, 3, U, 1),
    "uraned2": (467, 3, U, 1),
    "af0": (470, 26, S, P2_N35),
    "af1": (496, 20, S, P2_N48),
    "af2": (516, 10, S, P2_N60),
    "tgd": (526, 13, S, P2_N35),
    "iscl1gp": (539, 13, S, P2_N35),
    "iscl1cd": (552, 13, S, P2_N35),
    "isf": (565, 1, S, 0),
    "wnop": (566, 8, S, 1),
    "_reserved": (574, 2, U, 0),
    "_crc": (576, 24, U, 0),
}  # emphemeris

QZS_CNV2_SUBFRAME_3_P1 = {
    "prn": (0, 8, U, 0),
    SPID: (8, 6, U, 0),  # = 1
    "a0": (14, 16, S, P2_N35),
    "a1": (30, 13, S, P2_N51),
    "a2": (43, 7, S, P2_N68),
    "deltatls": (50, 8, S, 1),
    "tot": (58, 16, U, P2_P4),
    "wnot": (74, 13, U, 1),
    "wnlsf": (87, 13, U, 1),
    "dn": (100, 4, U, 1),
    "deltatlsf": (104, 8, S, 1),
    "alpha0": (112, 8, S, P2_N30),
    "alpha1": (120, 8, S, P2_N27),
    "alpha2": (128, 8, S, P2_N24),
    "alpha3": (136, 8, S, P2_N24),
    "beta0_msb": (144, 6, S, P2_P11),
    "beta0_lsb": (150, 2, S, P2_P11),
    "beta1": (152, 8, S, P2_P14),
    "beta2": (160, 8, S, P2_P16),
    "beta3": (168, 8, S, P2_P16),
    "iscl1": (176, 13, S, P2_N35),
    "lscl2": (189, 13, S, P2_N35),
    "iscl5i5": (202, 13, S, P2_N35),
    "iscl5q5": (215, 13, S, P2_N35),
    "_reserved1": (228, 22, U, 0),
    "_crc": (250, 24, U, 0),
}  # UTC and iono parameters (wide area)

QZS_CNV2_SUBFRAME_3_P2 = {
    "prn": (0, 8, U, 0),
    SPID: (8, 6, U, 0),  # = 2
    "gnssid": (14, 3, U, 0),
    "tggto": (17, 16, U, P2_P4),
    "wnggto": (33, 13, U, 1),
    "a0ggto": (46, 16, S, P2_N35),
    "a1ggto": (62, 13, S, P2_N51),
    "a2ggto": (75, 7, S, P2_N68),
    "teop": (82, 16, U, P2_P4),
    "pmx": (98, 21, S, P2_N20),
    "pmxdot": (119, 15, S, P2_N21),
    "pmy_msb": (134, 16, S, P2_N20),
    "pmy_lsb": (150, 5, S, P2_N20),
    "pmydot": (155, 15, S, P2_N21),
    "deltaut1": (170, 31, S, P2_N24),
    "deltaut1dot": (201, 19, S, P2_N25),
    "_reserved": (220, 30, U, 0),
    "_crc": (250, 24, U, 0),
}  # GGTO and EOP

QZS_CNV2_SUBFRAME_3_P61 = QZS_CNV2_SUBFRAME_3_P1  # UTC and IONO parameters (Japan area)

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
QZS_SUBFRAMEACQ_MAP = {
    LNAV: {
        TARGET: 0b1111,  # subframes 1,2,3,4p56
        START: 1,
        (1, 0): (QZS_LNAV_SUBFRAME_1, 1),
        (2, 0): (QZS_LNAV_SUBFRAME_2, 2),
        (3, 0): (QZS_LNAV_SUBFRAME_3, 4),
        (4, 56): (QZS_LNAV_SUBFRAME_4_P56, 8),
        (5, 56): (QZS_LNAV_SUBFRAME_5_P56, 8),
    },
    CNAV: {
        TARGET: 0b1111,  # subframes 10,11,30,33 (32 EOP optional)
        START: 10,
        (10, 0): (QZS_CNAV_SUBFRAME_10, 1),
        (11, 0): (QZS_CNAV_SUBFRAME_11, 2),
        (30, 0): (QZS_CNAV_SUBFRAME_30, 4),
        (33, 0): (QZS_CNAV_SUBFRAME_33, 8),
        (32, 0): (QZS_CNAV_SUBFRAME_32, 16),
    },
    CNV2: {
        TARGET: 0b1111,  # subframes 1,2,3P1,3P2 (3P61 for JAPAN)
        START: 1,
        (1, 0): (QZS_CNV2_SUBFRAME_1, 1),
        (2, 0): (QZS_CNV2_SUBFRAME_2, 2),
        (3, 1): (QZS_CNV2_SUBFRAME_3_P1, 4),
        (3, 2): (QZS_CNV2_SUBFRAME_3_P2, 8),
        # (3, 61): (QZS_CNV2_SUBFRAME_3_P61, 16),
    },
}
