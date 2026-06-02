"""
rinex_subframes_gps.py

GPS NAV Subframe definitions.

https://archive.gps.gov/technical/icwg/IS-GPS-200N.pdf

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

from pygnssutils.rawnav import PREAMBLE, SID, SPID, TOC, TOW, VALPREAMBLE, WN, S, U
from pygnssutils.rinex_globals import (
    CNAV,
    LNAV,
    P2_N4,
    P2_N5,
    P2_N6,
    P2_N8,
    P2_N9,
    P2_N14,
    P2_N15,
    P2_N16,
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
    P2_N37,
    P2_N38,
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
    P2_P9,
    P2_P11,
    P2_P12,
    P2_P14,
    P2_P16,
    START,
    TARGET,
)

# **********************************************************************
# LNAV - L1 C/A
# **********************************************************************

# attribute_name: (bit offset, bit length, bit encoding, scaling)
GPS_LNAV_TLM = {
    VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
    PREAMBLE: (0, 8, U, 0),
    "tlm": (8, 14, U, 0),
    "integrity": (22, 1, U, 0),
    "_reserved1": (23, 1, U, 0),
    "_parity1": (24, 6, U, 0),
}

GPS_LNAV_HOW = {
    TOW: (30, 17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (47, 1, U, 0),
    "antispoof": (48, 1, U, 0),
    SID: (49, 3, U, 0),  # subframe id
    "_non1": (52, 2, U, 0),
    "_parity2": (54, 6, U, 0),
}

GPS_LNAV_GENERIC = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # words 3 - 10
    "_word3_10": (60, 240, U, 0),
}

GPS_LNAV_SUBFRAME_1 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    WN: (60, 10, U, 1),  # used to derive epoch
    "l2codes": (70, 2, U, 1),
    "ura": (72, 4, U, 1),
    "svhealth": (76, 6, U, 1),
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

GPS_LNAV_SUBFRAME_2 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
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

GPS_LNAV_SUBFRAME_3 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
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

GPS_LNAV_SUBFRAME_45_GENERIC = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "_word3_10": (68, 232, U, 0),
}

GPS_LNAV_SUBFRAME_5_P01 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),  # subframe page id
    "e": (68, 16, U, P2_N21),
    "_parity3": (84, 6, U, 0),
    # word4
    "toa": (90, 8, U, P2_P12),
    "deltai": (98, 16, S, P2_N19),
    "_parity4": (114, 6, U, 0),
    # word5
    "omegadot": (120, 16, S, P2_N38),
    "svhealth": (136, 8, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "sqrta": (150, 24, U, P2_N21),
    "_parity6": (174, 6, U, 0),
    # word7
    "omega0": (180, 24, S, P2_N23),
    "_parity7": (204, 6, U, 0),
    # word8
    "omega": (210, 24, S, P2_N23),
    "_parity8": (234, 6, U, 0),
    # word9
    "m0": (240, 24, S, P2_N23),
    "_parity9": (264, 6, U, 0),
    # word10
    "af0_msb": (270, 8, S, P2_N20),
    "af1": (278, 11, S, P2_N38),
    "af0_lsb": (289, 3, U, P2_N20),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_5_P25 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "toa": (68, 8, U, 0),
    "wna": (76, 8, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "sv65health": (90, 6, U, 0),
    "sv66health": (96, 6, U, 0),
    "sv67health": (102, 6, U, 0),
    "sv68health": (108, 6, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "sv69health": (120, 6, U, 0),
    "sv70health": (126, 6, U, 0),
    "sv71health": (132, 6, U, 0),
    "sv72health": (138, 6, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "sv73health": (150, 6, U, 0),
    "sv74health": (156, 6, U, 0),
    "sv75health": (162, 6, U, 0),
    "sv76health": (168, 6, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "sv77health": (180, 6, U, 0),
    "sv78health": (186, 6, U, 0),
    "sv79health": (192, 6, U, 0),
    "sv80health": (198, 6, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "sv81health": (210, 6, U, 0),
    "sv82health": (216, 6, U, 0),
    "sv83health": (222, 6, U, 0),
    "sv84health": (228, 6, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "sv85health": (240, 6, U, 0),
    "sv86health": (246, 6, U, 0),
    "sv87health": (252, 6, U, 0),
    "sv88health": (258, 6, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "_reserved2": (270, 6, U, 0),
    "_reserved3": (276, 16, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P01 = {
    # 1,6,11,16,21
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "_reserved2": (68, 16, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "_reserved3": (90, 24, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "_reserved4": (120, 24, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "_reserved5": (150, 24, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "_reserved6": (180, 24, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "_reserved7": (210, 24, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "_reserved8": (240, 8, U, 0),
    "_reserved9": (248, 16, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "af0": (270, 22, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P12 = {
    # 12,19,20,22,23,24
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "_reserved2": (68, 16, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "_reserved3": (90, 24, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "_reserved4": (120, 24, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "_reserved5": (150, 24, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "_reserved6": (180, 24, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "_reserved7": (210, 24, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "_reserved8": (240, 8, U, 0),
    "_reserved9": (248, 16, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "_reserved10": (270, 22, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P18 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
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

GPS_LNAV_SUBFRAME_4_P25 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "sv65asc": (68, 4, U, 0),
    "sv66asc": (72, 4, U, 0),
    "sv67asc": (76, 4, U, 0),
    "sv68asc": (80, 4, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "sv69asc": (90, 4, U, 0),
    "sv70asc": (94, 4, U, 0),
    "sv71asc": (98, 4, U, 0),
    "sv72asc": (102, 4, U, 0),
    "sv73asc": (106, 4, U, 0),
    "sv74asc": (110, 4, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "sv75asc": (120, 4, U, 0),
    "sv76asc": (124, 4, U, 0),
    "sv77asc": (128, 4, U, 0),
    "sv78asc": (132, 4, U, 0),
    "sv79asc": (136, 4, U, 0),
    "sv80asc": (140, 4, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "sv81asc": (150, 4, U, 0),
    "sv82asc": (154, 4, U, 0),
    "sv83asc": (158, 4, U, 0),
    "sv84asc": (162, 4, U, 0),
    "sv85asc": (166, 4, U, 0),
    "sv86asc": (170, 4, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "sv87asc": (180, 4, U, 0),
    "sv88asc": (184, 4, U, 0),
    "sv89asc": (188, 4, U, 0),
    "sv90asc": (192, 4, U, 0),
    "sv91asc": (196, 4, U, 0),
    "sv92asc": (200, 4, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "sv93asc": (210, 4, U, 0),
    "sv94asc": (214, 4, U, 0),
    "sv95asc": (218, 4, U, 0),
    "_reserved2": (222, 4, U, 0),
    "_reserved3": (226, 2, U, 0),
    "sv89health": (228, 6, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "sv90health": (240, 6, U, 0),
    "sv91health": (246, 6, U, 0),
    "sv92health": (252, 6, U, 0),
    "sv93health": (258, 6, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "sv94health": (270, 6, U, 0),
    "sv95health": (276, 6, U, 0),
    "_reserved4": (282, 10, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P13 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "avail": (68, 2, U, 0),
    "erd1": (70, 6, U, 0),
    "erd2": (76, 6, U, 0),
    "erd3_msb": (82, 2, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "erd3_lsb": (90, 4, U, 0),
    "erd4": (94, 6, U, 0),
    "erd5": (100, 6, U, 0),
    "erd6": (106, 6, U, 0),
    "erd7_msb": (112, 2, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "erd7_lsb": (120, 4, U, 0),
    "erd8": (124, 6, U, 0),
    "erd9": (130, 6, U, 0),
    "erd10": (136, 6, U, 0),
    "erd11_msb": (142, 2, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "erd11_lsb": (150, 4, U, 0),
    "erd12": (154, 6, U, 0),
    "erd13": (160, 6, U, 0),
    "erd14": (166, 6, U, 0),
    "erd15_msb": (172, 2, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "erd15_lsb": (180, 4, U, 0),
    "erd16": (184, 6, U, 0),
    "erd17": (190, 6, U, 0),
    "erd18": (196, 6, U, 0),
    "erd19_msb": (202, 2, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "erd19_lsb": (210, 4, U, 0),
    "erd20": (214, 6, U, 0),
    "erd21": (220, 6, U, 0),
    "erd22": (226, 6, U, 0),
    "erd23_msb": (232, 2, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "erd23_lsb": (240, 4, U, 0),
    "erd24": (244, 6, U, 0),
    "erd25": (250, 6, U, 0),
    "erd26": (256, 6, U, 0),
    "erd27_msb": (262, 2, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "erd27_lsb": (270, 4, U, 0),
    "erd28": (274, 6, U, 0),
    "erd29": (280, 6, U, 0),
    "erd30": (286, 6, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P14 = {
    # 14,15,17
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    SPID: (62, 6, U, 0),
    "_reserved2": (68, 16, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "_reserved3": (90, 24, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "_reserved4": (120, 24, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "_reserved5": (150, 24, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "_reserved6": (180, 24, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "_reserved7": (210, 24, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "_reserved8": (240, 24, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "_reserved9": (270, 22, U, 0),
    "_non2": (292, 2, U, 0),
    "_parity10": (294, 6, U, 0),
}

GPS_LNAV_SUBFRAME_4_P02 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P03 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P04 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P05 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P06 = GPS_LNAV_SUBFRAME_4_P01
GPS_LNAV_SUBFRAME_4_P07 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P08 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P09 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P10 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_4_P11 = GPS_LNAV_SUBFRAME_4_P01
GPS_LNAV_SUBFRAME_4_P15 = GPS_LNAV_SUBFRAME_4_P14
GPS_LNAV_SUBFRAME_4_P16 = GPS_LNAV_SUBFRAME_4_P01
GPS_LNAV_SUBFRAME_4_P17 = GPS_LNAV_SUBFRAME_4_P14
GPS_LNAV_SUBFRAME_4_P19 = GPS_LNAV_SUBFRAME_4_P12
GPS_LNAV_SUBFRAME_4_P20 = GPS_LNAV_SUBFRAME_4_P12
GPS_LNAV_SUBFRAME_4_P21 = GPS_LNAV_SUBFRAME_4_P01
GPS_LNAV_SUBFRAME_4_P22 = GPS_LNAV_SUBFRAME_4_P12
GPS_LNAV_SUBFRAME_4_P23 = GPS_LNAV_SUBFRAME_4_P12
GPS_LNAV_SUBFRAME_4_P24 = GPS_LNAV_SUBFRAME_4_P12
GPS_LNAV_SUBFRAME_5_P02 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P03 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P04 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P05 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P06 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P07 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P08 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P09 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P10 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P11 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P12 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P13 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P14 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P15 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P16 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P17 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P18 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P19 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P20 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P21 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P22 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P23 = GPS_LNAV_SUBFRAME_5_P01
GPS_LNAV_SUBFRAME_5_P24 = GPS_LNAV_SUBFRAME_5_P01

# **********************************************************************
# CNAV - L2C, L5
# **********************************************************************

GPS_CNAV_SUBFRAME = {
    "word": (0, 300, U, 0),
    "padding": (300, 20, U, 0),
}  # 10 * 32-bit dwrds

GPS_CNAV_TLM = {
    # VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
    PREAMBLE: (0, 8, U, 0),
    "prn": (8, 6, U, 0),
    SID: (14, 6, U, 0),
    TOW: (20, 17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (37, 1, U, 0),
}

GPS_CNAV_CLOCK = {
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

GPS_CNAV_PARITY = {
    "_parity": (276, 24, U, 0),
}

GPS_CNAV_RAP = {
    "prn": (0, 6, U, 0),
    "deltaa": (6, 8, S, P2_P9),  # Relative to Aref = 26,559,710 meters, meters
    "omega0": (14, 7, S, P2_N6),  # semi-circles
    "phi0": (21, 7, S, P2_N6),  # M0 + omega, semi-circles
    "l1health": (28, 1, U, 0),
    "l2health": (29, 1, U, 0),
    "l5health": (30, 1, U, 0),
}
# 31 bit reduced almanac packet

GPS_CNAV_CDC = {
    "prn": (0, 8, U, 0),
    "deltaaf0": (8, 13, U, P2_N35),
    "deltaaf1": (21, 8, U, P2_N51),
    "udra": (29, 5, S, 0),
}
# 34 bit clock differential correction

GPS_CNAV_EDC = {
    "prn": (0, 8, U, 0),
    "deltaalpha": (8, 14, S, P2_N34),
    "deltabeta": (22, 14, S, P2_N34),
    "deltalambda": (36, 15, S, P2_N32),
    "deltai": (51, 12, S, P2_N31),
    "deltaomega": (63, 12, S, P2_N32),
    "deltaa": (75, 12, S, P2_N9),
    "udradot": (87, 5, S, 0),
}
# 92 bit ephemeris differential correction

GPS_CNAV_SUBFRAME_10 = {
    **GPS_CNAV_TLM,
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
    **GPS_CNAV_PARITY,
}  # Ephemeris 1

GPS_CNAV_SUBFRAME_11 = {
    **GPS_CNAV_TLM,
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
    **GPS_CNAV_PARITY,
}  # Ephemeris 2

GPS_CNAV_SUBFRAME_12 = {
    **GPS_CNAV_TLM,
    "wna": (38, 13, U, 0),
    "toa": (51, 8, U, P2_P12),
    "rap1": (59, 31, U, 0),  # GPS_CNAV_RAP
    "rap2_msb": (90, 10, U, 0),
    "rap2_lsb": (100, 21, U, 0),
    "rap3": (121, 31, U, 0),
    "rap4": (152, 31, U, 0),
    "rap5_msb": (183, 17, U, 0),
    "rap5_lsb": (200, 14, U, 0),
    "rap6": (214, 31, U, 0),
    "rap7": (245, 31, U, 0),
    **GPS_CNAV_PARITY,
}  # Reduced Almanac

GPS_CNAV_SUBFRAME_13 = {
    **GPS_CNAV_TLM,
    "topd": (38, 11, U, 300),
    "tod": (49, 11, U, 300),
    "dctype1": (60, 1, U, 0),
    "cdc1": (61, 34, U, 0),  # GPS_CNAV_CDC
    "dctype2": (95, 1, U, 0),
    "cdc2_msb": (96, 4, U, 0),
    "cdc2_lsb": (100, 30, U, 0),
    "dctype3": (130, 1, U, 0),
    "cdc3": (131, 34, U, 0),
    "dctype4": (165, 1, U, 0),
    "cdc4": (166, 34, U, 0),
    "dctype5": (200, 1, U, 0),
    "cdc5": (201, 34, U, 0),
    "dctype6": (235, 1, U, 0),
    "cdc6": (236, 34, U, 0),
    "_reserved1": (270, 6, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock Differential Correction

GPS_CNAV_SUBFRAME_14 = {
    **GPS_CNAV_TLM,
    "topd": (38, 11, U, 300),
    "tod": (49, 11, U, 300),
    "dctype1": (60, 1, U, 0),
    "edc1_msb": (61, 39, U, 0),  # GPS_CNAV_EDC
    "edc1_lsb": (100, 53, U, 0),
    "dctype2": (153, 1, U, 0),
    "edc2_msb": (154, 46, U, 0),
    "edc2_lsb": (200, 46, U, 0),
    "_reserved1": (246, 30, U, 0),
    **GPS_CNAV_PARITY,
}  # Ephemeris Differential Correction

GPS_CNAV_SUBFRAME_15 = {
    **GPS_CNAV_TLM,
    "text": (38, 232, U, 0),
    "textpage": (270, 4, U, 0),
    "_reserved1": (274, 2, U, 0),
    **GPS_CNAV_PARITY,
}  # Text

GPS_CNAV_SUBFRAME_30 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
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
    **GPS_CNAV_PARITY,
}  # Clock, IONO & Group Delay

GPS_CNAV_SUBFRAME_31 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "wna": (127, 13, U, 0),
    "toa": (140, 8, U, P2_P12),
    "rap1": (148, 31, U, 0),  # GPS_CNAV_RAP
    "rap2_msb": (179, 21, U, 0),
    "rap2_lsb": (200, 10, U, 0),
    "rap3": (210, 31, U, 0),
    "rap4": (241, 31, U, 0),
    "_reserved1": (272, 4, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Reduced Almanac

GPS_CNAV_SUBFRAME_32 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "teop": (127, 16, U, P2_P4),
    "pmx": (143, 21, S, P2_N20),
    "pmxdot": (164, 15, S, P2_N21),
    "pmy": (179, 21, S, P2_N20),
    "pmydot": (200, 15, S, P2_N21),
    "deltautgps": (215, 31, S, P2_N23),
    "deltautgpsdot": (246, 19, S, P2_N25),
    "_reserved1": (265, 11, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & EOP

GPS_CNAV_SUBFRAME_33 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
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
    **GPS_CNAV_PARITY,
}  # Clock & UTC

GPS_CNAV_SUBFRAME_34 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "topd": (127, 11, U, 300),
    "tod": (138, 11, U, 300),
    "dctype": (149, 1, U, 0),
    "cdc": (150, 34, U, 0),  # GPS_CNAV_CDC
    "edc_msb": (184, 16, U, 0),  # GPS_CNAV_EDC
    "edc_lsb": (200, 76, U, 0),
    # "_reserved1": (276, 51, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Differential Correction

GPS_CNAV_SUBFRAME_35 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "tggto": (127, 16, U, P2_P4),
    "wnggto": (143, 13, U, 1),
    "gnssid": (156, 3, U, 0),
    "a0ggto": (159, 16, U, P2_N35),
    "a1ggto": (175, 13, U, P2_N51),
    "a2ggto": (188, 7, U, P2_N68),
    "_reserved1": (195, 5, U, 0),
    "_reserved2": (200, 76, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & GGTO (GPS/GNSS Time Offset)

GPS_CNAV_SUBFRAME_36 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "text_msb": (127, 73, U, 0),
    "text_lsb": (200, 71, U, 0),
    "textpage": (271, 4, U, 0),
    "_reserved1": (275, 1, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Text

GPS_CNAV_SUBFRAME_37 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "wna": (127, 13, U, 0),
    "toa": (140, 8, U, P2_P12),
    "prna": (148, 6, U, 0),
    "l1health": (154, 1, U, 0),
    "l2health": (155, 1, U, 0),
    "l5health": (156, 1, U, 0),
    "e": (157, 11, U, P2_N16),
    "omegai": (168, 11, S, P2_N14),
    "omegadot": (179, 11, S, P2_N33),
    "sqrta_msb": (190, 10, U, P2_N4),
    "sqrta_lsb": (200, 7, U, P2_N4),
    "omega0": (207, 16, S, P2_N15),
    "omega": (223, 16, S, P2_N15),
    "m0": (239, 16, S, P2_N15),
    "af0": (255, 11, S, P2_N20),
    "af1": (266, 10, S, P2_N37),
    **GPS_CNAV_PARITY,
}  # Clock & Midi Almanac

GPS_CNAV_SUBFRAME_40 = {
    **GPS_CNAV_TLM,
    "gnssid": (38, 4, U, 0),
    "wnism": (42, 13, U, 1),
    "towism": (55, 6, U, 4),
    "tcorrel": (61, 4, U, 0),
    "bnom": (65, 4, U, 0),
    "lambdanom": (69, 4, U, 0),
    "rsat": (73, 4, U, 0),
    "pconst": (77, 4, U, 0),
    "mfd": (81, 4, U, 0),
    "servicelevel": (85, 3, U, 0),
    "mask": (88, 63, U, 0),
    "filler": (151, 93, U, 0),
    "_ism_crc": (244, 32, U, 0),
    **GPS_CNAV_PARITY,
}  # Integrity Support Message

# mapping for (subframe, page) acquisition mask subframeacq
GPS_SUBFRAMEACQ_MAP = {
    LNAV: {
        TARGET: 0b1111,  # subframes 1,2,3,4p18
        START: 1,
        (1, 0): (GPS_LNAV_SUBFRAME_1, 1),
        (2, 0): (GPS_LNAV_SUBFRAME_2, 2),
        (3, 0): (GPS_LNAV_SUBFRAME_3, 4),
        (4, 56): (GPS_LNAV_SUBFRAME_4_P18, 8),
        (5, 0): (GPS_LNAV_SUBFRAME_45_GENERIC, 16),
    },
    CNAV: {
        TARGET: 0b1111,  # subframes 10,11,30,33
        START: 10,
        (10, 0): (GPS_CNAV_SUBFRAME_10, 1),
        (11, 0): (GPS_CNAV_SUBFRAME_11, 2),
        (30, 0): (GPS_CNAV_SUBFRAME_30, 4),
        (33, 0): (GPS_CNAV_SUBFRAME_33, 8),
        (12, 0): (GPS_CNAV_SUBFRAME_12, 16),
        (13, 0): (GPS_CNAV_SUBFRAME_13, 32),
        (14, 0): (GPS_CNAV_SUBFRAME_14, 64),
        (15, 0): (GPS_CNAV_SUBFRAME_15, 128),
        (31, 0): (GPS_CNAV_SUBFRAME_31, 256),
        (32, 0): (GPS_CNAV_SUBFRAME_32, 512),
        (34, 0): (GPS_CNAV_SUBFRAME_34, 1024),
        (35, 0): (GPS_CNAV_SUBFRAME_35, 2048),
        (36, 0): (GPS_CNAV_SUBFRAME_36, 4096),
        (37, 0): (GPS_CNAV_SUBFRAME_37, 8192),
        (40, 0): (GPS_CNAV_SUBFRAME_40, 16384),
    },
}
