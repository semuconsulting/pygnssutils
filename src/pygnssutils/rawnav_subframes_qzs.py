"""
rawnav_subframes_qzss.py

QZSS NAV Subframe (Message Type) definitions.

L1C/A,L2CM, L2CL, L5I:
https://qzss.go.jp/en/technical/download/pdf/ps-is-qzss/is-qzss-pnt-006.pdf?t=1782205084546
L1S: https://qzss.go.jp/en/technical/ps-is-qzss/is_qzss_l1s_007_agree.html

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
- Avoid the following reserved field names: gnss, svid, sigid, subframeacq, epoch

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

from pygnssutils.rawnav import PREAMBLE, SID, SPID, SUBFRAMELENGTH, TOC, TOW, WN, S, U
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

QZS_LNAV_TLM = {
    SUBFRAMELENGTH: 300,
    PREAMBLE: (8, U, 0),
    "tlm": (14, U, 0),
    "integrity": (1, U, 0),
    "_reserved1": (1, U, 0),
    "_parity1": (6, U, 0),
}

QZS_LNAV_HOW = {
    TOW: (17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (1, U, 0),
    "antispoof": (1, U, 0),
    SID: (3, U, 0),  # subframe id
    "_non1": (2, U, 0),
    "_parity2": (6, U, 0),
}

QZS_LNAV_GENERIC = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # words 3 - 10
    "_word3_10": (240, U, 0),
}

QZS_LNAV_SUBFRAME_1 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    WN: (10, U, 1),  # used to derive epoch
    "l2codes": (2, U, 1),
    "ura": (4, U, 1),
    "svhealth": (6, U, 1),
    # "l1health": (76,1,U,0),
    # "l1cahealth": (77,1,U,0),
    # "l2health": (78,1,U,0),
    # "l5health": (79,1,U,0),
    # "l1chealth": (80,1,U,0),
    # "l1cbhealth": (81,1,U,0),
    "iodc_msb": (2, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "l2pdata": (1, U, 1),
    "_reserved2": (23, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "_reserved3": (24, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "_reserved4": (24, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "_reserved5": (16, U, 0),
    "tgd": (8, S, P2_N31),
    "_parity7": (6, U, 0),
    # word8
    "iodc_lsb": (8, U, 0),
    TOC: (16, U, P2_P4),  # must be named "toc"
    "_parity8": (6, U, 0),
    # word9
    "af2": (8, S, P2_N55),
    "af1": (16, S, P2_N43),
    "_parity9": (6, U, 0),
    # word10
    "af0": (22, S, P2_N31),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}

QZS_LNAV_SUBFRAME_2 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "iode": (8, U, 0),
    "crs": (16, S, P2_N5),
    "_parity3": (6, U, 0),
    # word4
    "deltan": (16, S, P2_N43),
    "m0_msb": (8, S, P2_N31),
    "_parity4": (6, U, 0),
    # word5
    "m0_lsb": (24, S, P2_N31),
    "_parity5": (6, U, 0),
    # word6
    "cuc": (16, S, P2_N29),
    "e_msb": (8, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "e_lsb": (24, U, P2_N33),
    "_parity7": (6, U, 0),
    # word8
    "cus": (16, S, P2_N29),
    "sqrta_msb": (8, U, P2_N19),
    "_parity8": (6, U, 0),
    # word9
    "sqrta_lsb": (24, U, P2_N19),
    "_parity9": (6, U, 0),
    # word10
    "toe": (16, U, P2_P4),
    "fit": (1, U, 0),
    "aodo": (5, U, 900),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}

QZS_LNAV_SUBFRAME_3 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "cic": (16, S, P2_N29),
    "omega0_msb": (8, S, P2_N31),
    "_parity3": (6, U, 0),
    # word4
    "omega0_lsb": (24, S, P2_N31),
    "_parity4": (6, U, 0),
    # word5
    "cis": (16, S, P2_N29),
    "i0_msb": (8, S, P2_N31),
    "_parity5": (6, U, 0),
    # word6
    "i0_lsb": (24, S, P2_N31),
    "_parity6": (6, U, 0),
    # word7
    "crc": (16, S, P2_N5),
    "omega_msb": (8, S, P2_N31),
    "_parity7": (6, U, 0),
    # word8
    "omega_lsb": (24, S, P2_N31),
    "_parity8": (6, U, 0),
    # word9
    "omegadot": (24, S, P2_N43),
    "_parity9": (6, U, 0),
    # word10
    "iode": (8, U, 0),
    "idot": (14, S, P2_N43),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}

QZS_LNAV_SUBFRAME_4_P56 = {
    # word1
    **QZS_LNAV_TLM,
    # word2
    **QZS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),  # = 3
    SPID: (6, U, 0),  # = 56
    "alpha0": (8, S, P2_N30),
    "alpha1": (8, S, P2_N27),
    "_parity3": (6, U, 0),
    # word4
    "alpha2": (8, S, P2_N24),
    "alpha3": (8, S, P2_N24),
    "beta0": (8, S, P2_P11),
    "_parity4": (6, U, 0),
    # word5
    "beta1": (8, S, P2_P14),
    "beta2": (8, S, P2_P16),
    "beta3": (8, S, P2_P16),
    "_parity5": (6, U, 0),
    # word6
    "a1": (24, S, P2_N30),
    "_parity6": (6, U, 0),
    # word7
    "a0_msb": (24, S, P2_N50),
    "_parity7": (6, U, 0),
    # word8
    "a0_lsb": (8, S, P2_N50),
    "tot": (8, U, P2_P12),
    "wnt": (8, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "deltatls": (8, S, 1),
    "wnlsf": (8, U, 0),
    "dn": (8, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "deltatlsf": (8, S, 1),
    "_reserved2": (14, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}

QZS_LNAV_SUBFRAME_5_P56 = QZS_LNAV_SUBFRAME_4_P56

# **********************************************************************
# CNAV - "2S","2L","5I","5Q" (L2C, L5) - SAME AS GPS CNAV
# **********************************************************************

QZS_CNAV_TLM = {
    SUBFRAMELENGTH: 300,
    PREAMBLE: (8, U, 0),
    "prn": (6, U, 0),
    SID: (6, U, 0),
    TOW: (17, U, 6),  # used to derive epoch, check TOW * 6 = seconds
    "alert": (1, U, 0),
}

QZS_CNAV_CLOCK = {
    "top": (11, U, 300),
    "uraned0": (5, S, 0),
    "uraned1": (3, U, 0),
    "uraned2": (3, U, 0),
    TOC: (11, U, 300),
    "af0n": (26, S, P2_N35),
    "af1n_msb": (3, S, P2_N48),
    "af1n_lsb": (17, S, P2_N48),
    "af2n": (10, S, P2_N60),
}

QZS_CNAV_PARITY = {
    "_parity": (24, U, 0),
}

QZS_CNAV_SUBFRAME_10 = {
    **QZS_CNAV_TLM,
    WN: (13, U, 0),  # used to derive epoch
    "l1health": (1, U, 0),
    "l2health": (1, U, 0),
    "l5health": (1, U, 0),
    "top": (11, U, 300),
    "uraed": (5, U, 0),
    "toe": (11, U, 300),
    "deltaa_msb": (19, S, P2_N9),
    "deltaa_lsb": (7, S, P2_N9),
    "adot": (25, S, P2_N21),
    "deltan0": (17, S, P2_N44),
    "deltan0dot": (23, S, P2_N57),
    "m0_msb": (28, S, P2_N32),
    "m0_lsb": (5, S, P2_N32),
    "e": (33, U, P2_N34),
    "omega": (33, S, P2_N32),
    "integrity": (1, U, 0),
    "l2phase": (1, U, 0),
    "_reserved1": (3, U, 0),
    **QZS_CNAV_PARITY,
}  # Ephemeris 1

QZS_CNAV_SUBFRAME_11 = {
    **QZS_CNAV_TLM,
    "toe": (11, U, 300),
    "omega0": (33, S, P2_N32),
    "i0_msb": (18, S, P2_N32),
    "i0_lsb": (15, S, P2_N32),
    "deltaomegadot": (17, S, P2_N44),
    "idot": (15, S, P2_N44),
    "cis": (16, S, P2_N30),
    "cic": (16, S, P2_N30),
    "crs_msb": (21, S, P2_N8),
    "crs_lsb": (3, S, P2_N8),
    "crc": (24, S, P2_N8),
    "cus": (21, S, P2_N30),
    "cuc": (21, S, P2_N30),
    "_reserved1": (7, U, 0),
    **QZS_CNAV_PARITY,
}  # Ephemeris 2

QZS_CNAV_SUBFRAME_30 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "tgd": (13, S, P2_N35),
    "iscl1ca": (13, S, P2_N35),
    "iscl2c": (13, S, P2_N35),
    "iscl5i5": (13, S, P2_N35),
    "iscl5q5": (13, S, P2_N35),
    "alpha0": (8, U, P2_N30),  # where is scaling defined for CNAV?
    "alpha1": (8, U, P2_N27),  # have assumed same as LNAV
    "alpha2": (8, U, P2_N24),
    "alpha3": (8, U, P2_N24),
    "beta0": (8, U, P2_P11),
    "beta1": (8, U, P2_P14),
    "beta2": (8, U, P2_P16),
    "beta3": (8, U, P2_P16),
    "wno": (8, U, 0),
    "_reserved1": (12, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock, IONO & Group Delay

QZS_CNAV_SUBFRAME_32 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "teop": (16, U, P2_P4),
    "pmx": (21, S, P2_N20),
    "pmxdot": (15, S, P2_N21),
    "pmy": (21, S, P2_N20),
    "pmydot": (15, S, P2_N21),
    "deltautgps": (31, S, P2_N23),
    "deltautgpsdot": (19, S, P2_N25),
    "_reserved1": (11, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock & EOP

QZS_CNAV_SUBFRAME_33 = {
    **QZS_CNAV_TLM,
    **QZS_CNAV_CLOCK,
    "a0": (16, S, P2_N35),
    "a1": (13, S, P2_N51),
    "a2": (7, S, P2_N68),
    "deltatls": (8, S, 1),
    "tot": (16, U, P2_P4),
    "wnot": (13, U, 1),
    "wnlsf": (13, U, 1),
    "dn": (4, U, 1),
    "deltatlsf": (8, S, 1),
    "_reserved1": (51, U, 0),
    **QZS_CNAV_PARITY,
}  # Clock & UTC

# **********************************************************************
# CNV2 - "1S" (L1S)
# **********************************************************************

QZS_CNV2_SUBFRAME_1 = {"toi": (9, U, 18)}

QZS_CNV2_SUBFRAME_2 = {
    SUBFRAMELENGTH: 600,
    WN: (13, U, 1),
    "itow": (8, U, 1),
    "top": (11, U, 300),
    "l1chealth": (1, U, 1),
    "uraed": (5, S, 1),
    "toe": (11, U, 300),
    "deltaa": (26, S, P2_N9),
    "adot": (25, S, P2_N21),
    "deltan0": (17, S, P2_N44),
    "deltan0dot": (23, S, P2_N57),
    "m0_msb": (10, S, P2_N32),
    "m0_lsb": (23, S, P2_N32),
    "e": (33, S, P2_N34),
    "omega": (33, S, P2_N32),
    "omega0": (33, S, P2_N32),
    "i0_msb": (28, S, P2_N32),
    "i0_lsb": (5, S, P2_N32),
    "deltanomegadot": (17, S, P2_N44),
    "idot": (15, S, P2_N44),
    "cis": (16, S, P2_N30),
    "cic": (16, S, P2_N30),
    "crs": (24, S, P2_N8),
    "crc": (24, S, P2_N8),
    "cus": (21, S, P2_N30),
    "cuc_msb": (12, S, P2_N30),
    "cuc_lsb": (9, S, P2_N30),
    "uraned0": (5, S, 1),
    "uraned1": (3, U, 1),
    "uraned2": (3, U, 1),
    "af0": (26, S, P2_N35),
    "af1": (20, S, P2_N48),
    "af2": (10, S, P2_N60),
    "tgd": (13, S, P2_N35),
    "iscl1gp": (13, S, P2_N35),
    "iscl1cd": (13, S, P2_N35),
    "isf": (1, S, 0),
    "wnop": (8, S, 1),
    "_reserved": (2, U, 0),
    "_crc": (24, U, 0),
}  # emphemeris

QZS_CNV2_SUBFRAME_3_TLM = {
    SUBFRAMELENGTH: 274,
    "prn": (8, U, 0),
    SPID: (6, U, 0),
}

QZS_CNV2_SUBFRAME_3_P1 = {
    **QZS_CNV2_SUBFRAME_3_TLM,
    "a0": (16, S, P2_N35),
    "a1": (13, S, P2_N51),
    "a2": (7, S, P2_N68),
    "deltatls": (8, S, 1),
    "tot": (16, U, P2_P4),
    "wnot": (13, U, 1),
    "wnlsf": (13, U, 1),
    "dn": (4, U, 1),
    "deltatlsf": (8, S, 1),
    "alpha0": (8, S, P2_N30),
    "alpha1": (8, S, P2_N27),
    "alpha2": (8, S, P2_N24),
    "alpha3": (8, S, P2_N24),
    "beta0_msb": (6, S, P2_P11),
    "beta0_lsb": (2, S, P2_P11),
    "beta1": (8, S, P2_P14),
    "beta2": (8, S, P2_P16),
    "beta3": (8, S, P2_P16),
    "iscl1": (13, S, P2_N35),
    "lscl2": (13, S, P2_N35),
    "iscl5i5": (13, S, P2_N35),
    "iscl5q5": (13, S, P2_N35),
    "_reserved1": (22, U, 0),
    "_crc": (24, U, 0),
}  # UTC and iono parameters (wide area)

QZS_CNV2_SUBFRAME_3_P2 = {
    **QZS_CNV2_SUBFRAME_3_TLM,
    "gnssid": (3, U, 0),
    "tggto": (16, U, P2_P4),
    "wnggto": (13, U, 1),
    "a0ggto": (16, S, P2_N35),
    "a1ggto": (13, S, P2_N51),
    "a2ggto": (7, S, P2_N68),
    "teop": (16, U, P2_P4),
    "pmx": (21, S, P2_N20),
    "pmxdot": (15, S, P2_N21),
    "pmy_msb": (16, S, P2_N20),
    "pmy_lsb": (5, S, P2_N20),
    "pmydot": (15, S, P2_N21),
    "deltaut1": (31, S, P2_N24),
    "deltaut1dot": (19, S, P2_N25),
    "_reserved": (30, U, 0),
    "_crc": (24, U, 0),
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
