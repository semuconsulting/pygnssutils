"""
rinex_subframes_bds.py

Beidou NAV Subframe definitions.

B1I: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/201902/P020190227601370045731.pdf
B1C: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/201806/P020180608525871869457.pdf
B2a: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/201806/P020180608525870555377.pdf
B3I: http://en.beidou.gov.cn/SYSTEMS/Officialdocument/201806/P020180608525869304359.pdf
Open Service: http://en.beidou.gov.cn/SYSTEMS/ICD/201806/P020180608523308843290.pdf

D1 is the BDS-2/3 legacy navigation message on MEO/IGSO satellites (obscode 2I, 6I, 7I).
D2 is the BDS-2/3 legacy navigation message on GEO satellites (obscode 2I, 6I, 7I).
CNV1 is the navigation message on the Beidou-3 B1C signal (obscode 1D).
CNV2 is the navigation message on the Beidou-3 B2a signal (obscode 5D).

These are provided as the basis of a capability to parse and store
the payloads of raw NAV subframe messages, via the associated
`pygnssutils.RawNav` class defined in `rawnav.py`.

NB:

- MSB, intermediate bit and LSB fields MUST be suffixed '_msb', '_isb' and '_lsb' respectively.
- Non-data bits (reserved, parity, non) MUST be prefixed '_'.
- Avoid the following reserved field names: gnss, svid, sigid, subframeacq, epoch

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=fixme, unused-import

from pygnssutils.rawnav import PREAMBLE, SID, SPID, VALPREAMBLE, WN, S, U
from pygnssutils.rinex_globals import (
    CNV1,
    CNV2,
    D1,
    D2,
    P1_D1,
    P2_N6,
    P2_N19,
    P2_N24,
    P2_N27,
    P2_N30,
    P2_N31,
    P2_N33,
    P2_N43,
    P2_N50,
    P2_N66,
    P2_P3,
    P2_P11,
    P2_P14,
    P2_P16,
    START,
    TARGET,
)

# **********************************************************************
# D1 - "2I", "6I", "7I" (B1I, B3I, B2I - D1 MEO/IGSO)
#
# each subframe/page 300 bits, comprising 10 * 30 bit words
# subframes 1,2,3 CEI
# subframe 4,5 Almanac & time corrections
# **********************************************************************

# attribute_name: (bit offset, bit length, bit encoding, scaling)
BDS_D1_TLM = {
    # VALPREAMBLE: 0b11100010010,  # optional, used to validate preamble value
    PREAMBLE: (0, 11, U, 0),
    "rev": (11, 4, U, 0),
    SID: (15, 3, U, 0),  # subframe id
    "tow_msb": (18, 8, U, 0),  # used to derive epoch
    "_parity1": (26, 4, U, 0),
    "tow_lsb": (30, 12, U, 0),
}

BDS_D1_SUBFRAME_1 = {
    **BDS_D1_TLM,
    "sath1": (42, 1, U, 0),
    "aodc": (43, 5, U, 0),
    "urai": (48, 4, U, 1),
    "_parity2": (52, 8, U, 0),
    WN: (60, 13, U, 1),  # used to derive epoch
    "toc_msb": (73, 9, U, P2_P3),  # must be named "toc"
    "_parity3": (82, 8, U, 0),
    "toc_lsb": (90, 8, U, P2_P3),  # must be named "toc"
    "tgd1": (98, 10, S, P1_D1),
    "tgd2_msb": (108, 4, S, P1_D1),
    "_parity4": (112, 8, U, 0),
    "tgd2_lsb": (120, 6, S, P1_D1),
    "alpha0": (126, 8, S, P2_N30),
    "alpha1": (134, 8, S, P2_N27),
    "_parity5": (142, 8, U, 0),
    "alpha2": (150, 8, S, P2_N24),
    "alpha3": (158, 8, S, P2_N24),
    "beta0_msb": (166, 6, S, P2_P11),
    "_parity6": (172, 8, U, 0),
    "beta0_lsb": (180, 2, S, P2_P11),
    "beta1": (182, 8, S, P2_P14),
    "beta2": (190, 8, S, P2_P16),
    "beta3_msb": (198, 4, S, P2_P16),
    "_parity7": (202, 8, U, 0),
    "beta3_lsb": (210, 4, S, P2_P16),
    "af2": (214, 11, S, P2_N66),
    "af0_msb": (225, 7, S, P2_N33),
    "_parity8": (232, 8, U, 0),
    "af0_lsb": (240, 17, S, P2_N33),
    "af1_msb": (257, 5, S, P2_N50),
    "_parity9": (262, 8, U, 0),
    "af1_lsb": (270, 17, S, P2_N50),
    "aode": (287, 5, U, 0),
    "_parity10": (292, 8, U, 0),
}

BDS_D1_SUBFRAME_2 = {
    **BDS_D1_TLM,
    "deltan_msb": (42, 10, S, P2_N43),
    "_parity2": (52, 8, U, 0),
    "deltan_lsb": (60, 6, S, P2_N43),
    "cuc_msb": (66, 16, S, P2_N31),
    "_parity3": (82, 8, U, 0),
    "cuc_lsb": (90, 2, S, P2_N31),
    "m0_msb": (92, 20, S, P2_N31),
    "_parity4": (112, 8, U, 0),
    "m0_lsb": (120, 12, S, P2_N31),
    "e_msb": (132, 10, U, P2_N33),
    "_parity5": (142, 8, U, 0),
    "e_lsb": (150, 22, U, P2_N33),
    "_parity6": (172, 8, U, 0),
    "cus": (180, 18, S, P2_N31),
    "crc_msb": (198, 4, S, P2_N6),
    "_parity7": (202, 8, U, 0),
    "crc_lsb": (210, 14, S, P2_N6),
    "crs_msb": (224, 8, S, P2_N6),
    "_parity8": (232, 8, U, 0),
    "crs_lsb": (240, 10, S, P2_N6),
    "sqrta_msb": (250, 12, U, P2_N19),
    "_parity9": (262, 8, U, 0),
    "sqrta_lsb": (270, 20, U, P2_N19),
    "toe_msb": (290, 2, U, P2_P3),  # split between subframes 2 and 3
    "_parity10": (292, 8, U, 0),
}

BDS_D1_SUBFRAME_3 = {
    **BDS_D1_TLM,
    "toe_isb": (42, 10, U, P2_P3),  # between MSB & LSB
    "_parity2": (52, 8, U, 0),
    "toe_lsb": (60, 5, U, P2_P3),  # split between subframes 2 and 3
    "i0_msb": (65, 17, S, P2_N31),
    "_parity3": (82, 8, U, 0),
    "i0_lsb": (90, 15, S, P2_N31),
    "cic_msb": (105, 7, S, P2_N31),
    "_parity4": (112, 8, U, 0),
    "cic_lsb": (120, 11, S, P2_N31),
    "omegadot_msb": (131, 11, S, P2_N43),
    "_parity5": (142, 8, U, 0),
    "omegadot_lsb": (150, 13, S, P2_N43),
    "cis_msb": (163, 9, S, P2_N31),
    "_parity6": (172, 8, U, 0),
    "cis_lsb": (180, 9, S, P2_N31),
    "idot_msb": (189, 13, S, P2_N43),
    "_parity7": (202, 8, U, 0),
    "idot_lsb": (210, 1, S, P2_N43),
    "omega0_msb": (211, 21, S, P2_N31),
    "_parity8": (232, 8, U, 0),
    "omega0_lsb": (240, 11, S, P2_N31),
    "omega_msb": (251, 11, S, P2_N31),
    "_parity9": (262, 8, U, 0),
    "omega_lsb": (270, 21, S, P2_N31),
    "rev1": (291, 1, U, 0),
    "_parity10": (292, 8, U, 0),
}
BDS_D1_SUBFRAME_4_P01_24 = {
    **BDS_D1_TLM,
    SPID: (42, 7, U, 0),
    "_remainder": (49, 251, U, 0),  # TODO not needed for RINEX NAV
}
BDS_D1_SUBFRAME_5_P01_6 = BDS_D1_SUBFRAME_4_P01_24
BDS_D1_SUBFRAME_5_P07 = {
    **BDS_D1_TLM,
    SPID: (42, 7, U, 0),
    "_remainder": (49, 251, U, 0),  # TODO not needed for RINEX NAV
}
BDS_D1_SUBFRAME_5_P08 = {
    **BDS_D1_TLM,
    SPID: (42, 7, U, 0),
    "_remainder": (49, 251, U, 0),  # TODO not needed for RINEX NAV
}
BDS_D1_SUBFRAME_5_P09 = {
    **BDS_D1_TLM,
    "_rev1": (42, 1, U, 0),
    SPID: (43, 7, U, 0),
    "_rev2": (50, 2, U, 0),
    "_parity2": (52, 8, U, 0),
    "_rev3": (60, 22, U, 0),
    "_parity3": (82, 8, U, 0),
    "_rev4": (90, 6, U, 0),
    "a0gps": (96, 14, U, 0.1),
    "a1gps_msb": (110, 2, U, 0.1),
    "_parity4": (112, 8, U, 0),
    "a1gps_lsb": (120, 14, U, 0.1),
    "a0gal_msb": (134, 8, U, 0.1),
    "_parity5": (142, 8, U, 0),
    "a0gal_lsb": (150, 6, U, 0.1),
    "a1gal": (156, 16, U, 0.1),
    "_parity6": (172, 8, U, 0),
    "a0glo": (180, 14, U, 0.1),
    "a1glo_msb": (194, 8, U, 0.1),
    "_parity7": (202, 8, U, 0),
    "a1glo_lsb": (210, 8, U, 0.1),
    "_rev5": (218, 58, U, 0),
    "_parity10": (276, 24, U, 0),
}
BDS_D1_SUBFRAME_5_P10 = {
    **BDS_D1_TLM,
    "_rev1": (42, 1, U, 0),
    SPID: (43, 7, U, 0),
    "deltatls_msb": (50, 2, U, 0),
    "_parity2": (52, 8, U, 0),
    "deltatls_lsb": (60, 6, U, 1),
    "deltatlsf": (66, 8, U, 1),
    "wnlsf": (74, 8, U, 1),
    "_parity3": (82, 8, U, 0),
    "a0_msb": (90, 22, U, P2_N30),  # utc
    "_parity4": (112, 8, U, 0),
    "a0_lsb": (120, 10, U, P2_N30),  # utc
    "a1_msb": (130, 12, U, P2_N50),  # utc
    "_parity5": (142, 8, U, 0),
    "a1_lsb": (150, 12, U, P2_N50),  # utc
    "dn": (162, 8, U, 1),
    "_rev2": (170, 90, U, 0),
    "_parity6": (260, 40, U, 0),
}
BDS_D1_SUBFRAME_5_P11_23 = {
    **BDS_D1_TLM,
    SPID: (42, 7, U, 0),
    "_remainder": (49, 251, U, 0),  # TODO not needed for RINEX NAV
}
BDS_D1_SUBFRAME_5_P24 = {
    **BDS_D1_TLM,
    SPID: (42, 7, U, 0),
    "_remainder": (49, 251, U, 0),  # TODO not needed for RINEX NAV
}

# **********************************************************************
# D2 - "2I", "6I", "7I" (B1I, B3I, B2I - D2 GEO)
#
# each subframe/page 300 bits
# subframes 1,2,3, 4 CEI
# subframe 5 Almanac, Ionosphere, Time Offsets
# **********************************************************************

BDS_D2_TLM = {
    # VALPREAMBLE: 0b11100010010,  # optional, used to validate preamble value
    PREAMBLE: (0, 11, U, 0),
    "rev": (11, 4, U, 0),
    SID: (15, 3, U, 0),  # subframe id
    "tow_msb": (18, 8, U, 0),  # used to derive epoch
    "_parity1": (26, 4, U, 0),
    "tow_lsb": (30, 12, U, 0),
    SPID: (42, 4, U, 0),
}

BDS_D2_SUBFRAME_1_END = {
    "_parity5": (142, 8, U, 0),
    "_reserved1": (150, 150, U, 0),
}

BDS_D2_SUBFRAME_1_P01 = {
    **BDS_D2_TLM,
    "sath1": (46, 1, U, 0),
    "aodc": (47, 5, U, 0),
    "_parity2": (52, 8, U, 0),
    "urai": (60, 4, U, 1),
    WN: (64, 13, U, 1),  # used to derive epoch
    "toc_msb": (77, 5, U, P2_P3),  # must be named "toc"
    "_parity3": (82, 8, U, 0),
    "toc_lsb": (90, 12, U, P2_P3),  # must be named "toc"
    "tgd1": (102, 10, S, P1_D1),
    "_parity4": (112, 8, U, 0),
    "tgd2": (120, 10, S, P1_D1),
    "_rev1": (130, 12, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P02 = {
    **BDS_D2_TLM,
    "alpha0_msb": (46, 6, S, P2_N30),
    "_parity2": (52, 8, U, 0),
    "alpha0_lsb": (60, 2, S, P2_N30),
    "alpha1": (62, 8, S, P2_N27),
    "alpha2": (70, 8, S, P2_N24),
    "alpha3_msb": (78, 4, S, P2_N24),
    "_parity3": (82, 8, U, 0),
    "alpha3_lsb": (90, 4, S, P2_N24),
    "beta0": (94, 8, S, P2_P11),
    "beta1": (102, 8, S, P2_P14),
    "beta2_msb": (110, 2, S, P2_P16),
    "_parity4": (112, 8, U, 0),
    "beta2_lsb": (120, 6, S, P2_P16),
    "beta3": (126, 8, S, P2_P16),
    "_rev1": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P03 = {
    **BDS_D2_TLM,
    "_rev1": (46, 6, U, 0),
    "_parity2": (52, 8, U, 0),
    "_rev2": (60, 22, U, 0),
    "_parity3": (82, 8, U, 0),
    "_rev3": (90, 10, U, 0),
    "af0_msb": (100, 12, S, P2_N33),
    "_parity4": (112, 8, U, 0),
    "af0_lsb": (120, 12, S, P2_N33),
    "af1_msb": (132, 4, S, P2_N50),
    "_rev4": (136, 6, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P04 = {
    **BDS_D2_TLM,
    "af1_isb": (46, 6, S, P2_N50),
    "_parity2": (52, 8, U, 0),
    "af1_lsb": (60, 12, S, P2_N50),
    "af2_msb": (72, 10, S, P2_N66),
    "_parity3": (82, 8, U, 0),
    "af2_lsb": (90, 1, S, P2_N66),
    "aode": (91, 5, U, 0),
    "deltan": (96, 16, S, P2_N43),
    "_parity4": (112, 8, U, 0),
    "cuc_msb": (120, 14, S, P2_N31),
    "_rev2": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P05 = {
    **BDS_D2_TLM,
    "cuc": (46, 4, S, P2_N31),
    "m0_msb": (50, 2, S, P2_N31),
    "_parity2": (52, 8, U, 0),
    "m0_isb": (60, 22, S, P2_N31),
    "_parity3": (82, 8, U, 0),
    "m0_lsb": (90, 8, S, P2_N31),
    "cus_msb": (98, 14, S, P2_N31),
    "_parity4": (112, 8, U, 0),
    "cus_lsb": (120, 4, S, P2_N31),
    "e_msb": (124, 10, U, P2_N33),
    "_rev2": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P06 = {
    **BDS_D2_TLM,
    "e_isb": (46, 6, U, P2_N33),
    "_parity2": (52, 8, U, 0),
    "e_lsb": (60, 16, U, P2_N33),
    "sqrta_msb": (76, 6, U, P2_N19),
    "_parity3": (82, 8, U, 0),
    "sqrta_isb": (90, 22, U, P2_N19),
    "_parity4": (112, 8, U, 0),
    "sqrta_lsb": (120, 4, U, P2_N19),
    "cic_msb": (124, 10, S, P2_N31),
    "_rev2": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P07 = {
    **BDS_D2_TLM,
    "cic_isb": (46, 6, S, P2_N31),
    "_parity2": (52, 8, U, 0),
    "cic_lsb": (60, 2, S, P2_N31),
    "cis_msb": (62, 18, S, P2_N31),
    "toe_msb": (80, 2, U, P2_P3),
    "_parity3": (82, 8, U, 0),
    "toe_lsb": (90, 15, U, P2_P3),
    "i0_msb": (105, 7, S, P2_N31),
    "_parity4": (112, 8, U, 0),
    "i0_is1": (120, 14, S, P2_N31),
    "_rev2": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P08 = {
    **BDS_D2_TLM,
    "i0_isb": (46, 6, S, P2_N31),
    "_parity2": (52, 8, U, 0),
    "i0_lsb": (60, 5, S, P2_N31),
    "crc_msb": (65, 17, S, P2_N6),
    "_parity3": (82, 8, U, 0),
    "crc_lsb": (90, 1, S, P2_N6),
    "crs_msb": (91, 18, S, P2_N6),
    "omegadot_msb": (109, 3, S, P2_N43),
    "_parity4": (112, 8, U, 0),
    "omegadot_isb": (120, 16, S, P2_N43),
    "_rev2": (136, 6, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P09 = {
    **BDS_D2_TLM,
    "omegadot_lsb": (46, 5, S, P2_N43),
    "omega0_msb": (51, 1, S, P2_N31),
    "_parity2": (52, 8, U, 0),
    "omega0_isb": (60, 22, S, P2_N31),
    "_parity3": (82, 8, U, 0),
    "omega0_lsb": (90, 9, S, P2_N31),
    "omega_msb": (99, 13, S, P2_N31),
    "_parity4": (112, 8, U, 0),
    "omega_isb": (120, 14, S, P2_N31),
    "_rev2": (134, 8, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}
BDS_D2_SUBFRAME_1_P10 = {
    **BDS_D2_TLM,
    "omega_isb": (46, 5, S, P2_N31),
    "idot_msb": (51, 1, S, P2_N43),
    "_parity2": (52, 8, U, 0),
    "idot_lsb": (60, 13, S, P2_N43),
    "rev1": (73, 9, U, 0),
    "_parity3": (82, 8, U, 0),
    "rev2": (90, 22, U, 0),
    "_parity4": (112, 8, U, 0),
    "rev3": (120, 22, U, 0),
    **BDS_D2_SUBFRAME_1_END,
}

BDS_D2_SUBFRAME_2 = {}
BDS_D2_SUBFRAME_3 = {}
BDS_D2_SUBFRAME_4 = {}
BDS_D2_SUBFRAME_5_P01 = {}
BDS_D2_SUBFRAME_5_P61 = {}
BDS_D2_SUBFRAME_5_P02 = {}
BDS_D2_SUBFRAME_5_P62 = {}
BDS_D2_SUBFRAME_5_P03 = {}
BDS_D2_SUBFRAME_5_P63 = {}
BDS_D2_SUBFRAME_5_P04 = {}
BDS_D2_SUBFRAME_5_P64 = {}
BDS_D2_SUBFRAME_5_P05 = {}
BDS_D2_SUBFRAME_5_P65 = {}
BDS_D2_SUBFRAME_5_P06 = {}
BDS_D2_SUBFRAME_5_P66 = {}
BDS_D2_SUBFRAME_5_P07 = {}
BDS_D2_SUBFRAME_5_P67 = {}
BDS_D2_SUBFRAME_5_P08 = {}
BDS_D2_SUBFRAME_5_P68 = {}
BDS_D2_SUBFRAME_5_P09 = {}
BDS_D2_SUBFRAME_5_P69 = {}
BDS_D2_SUBFRAME_5_P10 = {}
BDS_D2_SUBFRAME_5_P70 = {}
BDS_D2_SUBFRAME_5_P11 = {}
BDS_D2_SUBFRAME_5_P71 = {}
BDS_D2_SUBFRAME_5_P12 = {}
BDS_D2_SUBFRAME_5_P72 = {}
BDS_D2_SUBFRAME_5_P13 = {}
BDS_D2_SUBFRAME_5_P73 = {}
BDS_D2_SUBFRAME_5_P35 = {}
BDS_D2_SUBFRAME_5_P36 = {}
BDS_D2_SUBFRAME_5_P37_60 = {}
BDS_D2_SUBFRAME_5_P95_100 = BDS_D2_SUBFRAME_5_P37_60
BDS_D2_SUBFRAME_5_P101 = {}
BDS_D2_SUBFRAME_5_P102 = {}
BDS_D2_SUBFRAME_5_P103_115 = {}
BDS_D2_SUBFRAME_5_P116 = {}
BDS_D2_SUBFRAME_5_P14_34 = {}
BDS_D2_SUBFRAME_5_P74_94 = BDS_D2_SUBFRAME_5_P14_34
BDS_D2_SUBFRAME_5_P117_120 = BDS_D2_SUBFRAME_5_P14_34

# **********************************************************************
# CNV1 - "1D" (B1C)
#
# subframe 1 14 bits
# subframe 2 600 bits
# subframe 3 264 bits
# **********************************************************************

BDS_CNV1_SUBFRAME_1 = {}
BDS_CNV1_SUBFRAME_2 = {}
BDS_CNV1_SUBFRAME_3_P01 = {}
BDS_CNV1_SUBFRAME_3_P02 = {}
BDS_CNV1_SUBFRAME_3_P03 = {}
BDS_CNV1_SUBFRAME_3_P04 = {}

# **********************************************************************
# CNV2 - "5D" (B2a) (formerly B2I)
#
# each subframe/page 288 bits
# **********************************************************************

BDS_CNV2_SUBFRAME_10 = {}
BDS_CNV2_SUBFRAME_11 = {}
BDS_CNV2_SUBFRAME_30 = {}
BDS_CNV2_SUBFRAME_31 = {}
BDS_CNV2_SUBFRAME_32 = {}
BDS_CNV2_SUBFRAME_33 = {}
BDS_CNV2_SUBFRAME_34 = {}
BDS_CNV2_SUBFRAME_40 = {}

# mapping for (subframe, page) acquisition mask subframeacq
BDS_SUBFRAMEACQ_MAP = {
    D1: {
        TARGET: 0b1111,  # subframes 1,2,3,5p10
        START: 1,
        (1, 0): (BDS_D1_SUBFRAME_1, 1),
        (2, 0): (BDS_D1_SUBFRAME_2, 2),
        (3, 0): (BDS_D1_SUBFRAME_3, 4),
        (5, 10): (BDS_D1_SUBFRAME_5_P10, 8),
        (4, 1): (BDS_D1_SUBFRAME_4_P01_24, 16),
    },
    D2: {
        TARGET: 0b1111111111,  # subframes 1-10
        START: 1,
        (1, 1): (BDS_D2_SUBFRAME_1_P01, 1),
        (1, 2): (BDS_D2_SUBFRAME_1_P02, 2),
        (1, 3): (BDS_D2_SUBFRAME_1_P03, 4),
        (1, 4): (BDS_D2_SUBFRAME_1_P04, 8),
        (1, 5): (BDS_D2_SUBFRAME_1_P05, 16),
        (1, 6): (BDS_D2_SUBFRAME_1_P06, 32),
        (1, 7): (BDS_D2_SUBFRAME_1_P07, 64),
        (1, 8): (BDS_D2_SUBFRAME_1_P08, 128),
        (1, 9): (BDS_D2_SUBFRAME_1_P09, 256),
        (1, 10): (BDS_D2_SUBFRAME_1_P10, 512),
    },
    CNV1: {
        TARGET: 0b111,  # subframes 1,2,3p01
        START: 1,
        (1, 0): (BDS_CNV1_SUBFRAME_1, 1),
        (2, 0): (BDS_CNV1_SUBFRAME_2, 2),
        (3, 1): (BDS_CNV1_SUBFRAME_3_P01, 4),
        (3, 2): (BDS_CNV1_SUBFRAME_3_P02, 8),
        (3, 3): (BDS_CNV1_SUBFRAME_3_P03, 16),
        (3, 4): (BDS_CNV1_SUBFRAME_3_P04, 32),
    },
    CNV2: {
        TARGET: 0b1111,  # subframes 10,20,30,31
        START: 10,
        (10, 0): (BDS_CNV2_SUBFRAME_10, 1),
        (11, 0): (BDS_CNV2_SUBFRAME_11, 2),
        (30, 0): (BDS_CNV2_SUBFRAME_30, 4),
        (31, 0): (BDS_CNV2_SUBFRAME_31, 8),
        (32, 0): (BDS_CNV2_SUBFRAME_32, 16),
        (33, 0): (BDS_CNV2_SUBFRAME_33, 32),
        (34, 0): (BDS_CNV2_SUBFRAME_34, 64),
        (40, 0): (BDS_CNV2_SUBFRAME_40, 128),
    },
}
