"""
rinex_subframes_gps.py

!!! WORK IN PROGRESS !!!

GPS NAV Subframe definitions.

https://archive.gps.gov/technical/icwg/IS-GPS-200N.pdf

These are provided as the basis of a capability to parse and store
the payloads of raw NAV subframe messages, via the associated
`pygnssutils.RawNav` class defined in `rawnav.py`.

NB:

- MSB and LSB fields MUST be suffixed '_msb' and '_lsb' respectively.
- Non-data bits (reserved, parity, non) MUST be prefixed '_'.
- Avoid the following reserved field names: gnss, svid, sigid, sfracq, epoch

NOTE: if extracting raw subframe data from UBX RXM-SFRBX messages, note
that the native 30-bit GPS words are padded to 32-bit dwrds `BUT` the padding
treatment depends on the signal type. For L1 (LNAV) signals, the final
2 bits of each 32-bit dwrd are padding and can simply be stripped off,
but for other signal types things are more complicated, and the relevant
treatment does not appear to be specified in any public domain UBX protocol
specification.

There have been attempts to 'reverse engineer' the treatment. See, for example:

https://portal.u-blox.com/s/question/0D52p00008HKD1kCAH/why-are-the-sfrbx-messages-words-32-bits-but-in-isgps200h-the-words-are-specified-as-being-30-bits-long
https://github.com/semuconsulting/pyubx2/blob/master/src/pyubx2/ubxtypes_get.py

GPS L1 : pads 2 bits at the end of each word (30 bit message + 2 bit padding) x 10 words = 320 bits total
GPS L5: pads 20 bits at end (300 bit message + 20 bit padding using the next frame) = 320 bits total

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=fixme

from pygnssutils.rawnav import PREAMBLE, SFR, TOW, VALPREAMBLE, S, U
from pygnssutils.rinex_globals import (
    P2_N5,
    P2_N19,
    P2_N24,
    P2_N27,
    P2_N29,
    P2_N30,
    P2_N31,
    P2_N33,
    P2_N43,
    P2_N50,
    P2_N55,
    P2_P4,
    P2_P11,
    P2_P12,
    P2_P14,
    P2_P16,
)

# TODO complete scaling factors for all subframe definitions

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
    TOW: (30, 17, U, 0),
    "alert": (47, 1, U, 0),
    "antispoof": (48, 1, U, 0),
    SFR: (49, 3, U, 0),
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
    "wn": (60, 10, U, 1),
    "ca": (70, 2, U, 1),
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
    "toc": (218, 16, S, P2_P4),
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
    "sqrta_msb": (226, 8, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "sqrta_lsb": (240, 24, U, P2_N19),
    "_parity9": (264, 6, U, 0),
    # word10
    "toe": (270, 16, S, P2_P4),
    "fit": (286, 1, U, 0),
    "aodo": (287, 5, U, 0),
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
    "svcode": (62, 6, U, 0),
    "_word3_10": (68, 232, U, 0),
}

GPS_LNAV_SUBFRAME_5_P01 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (60, 2, U, 0),
    "svcode": (62, 6, U, 0),
    "e": (68, 16, U, 0),
    "_parity3": (84, 6, U, 0),
    # word4
    "toa": (90, 8, U, 0),
    "deltai": (98, 16, U, 0),
    "_parity4": (114, 6, U, 0),
    # word5
    "omegadot": (120, 16, U, 0),
    "svhealth": (136, 8, U, 0),
    "_parity5": (144, 6, U, 0),
    # word6
    "sqrta": (150, 24, U, 0),
    "_parity6": (174, 6, U, 0),
    # word7
    "omega0": (180, 24, U, 0),
    "_parity7": (204, 6, U, 0),
    # word8
    "omega": (210, 24, U, 0),
    "_parity8": (234, 6, U, 0),
    # word9
    "m0": (240, 24, U, 0),
    "_parity9": (264, 6, U, 0),
    # word10
    "af0_msb": (270, 8, U, 0),
    "af1": (278, 11, U, 0),
    "af0_lsb": (289, 3, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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
    "svcode": (62, 6, U, 0),
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


"""
Utility to apply and validate offsets and word partitions
"""
# offset = 0
# w = 0
# for key, (_, len, typ, sca) in GPS_LNAV_SUBFRAME_45_GENERIC.items():
#     if not offset % 30:
#         w += 1
#         print(f"# word{w}")
#     print(f'"{key}": ({offset},{len},{typ},{sca}),')
#     offset += len
# if w != 10:
#     print("!!! check attribute lengths !!!")
