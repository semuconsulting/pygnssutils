"""
rawnav_subframes_gps.py

GPS NAV Subframe definitions.

L1C/A,L2CL,L2CM: https://www.gps.gov/sites/default/files/2025-07/IS-GPS-200N.pdf
L5I: https://www.gps.gov/sites/default/files/2025-07/IS-GPS-705J.pdf

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

from pygnssutils.rawnav import (
    PREAMBLE,
    SID,
    SPID,
    SUBFRAMELENGTH,
    SVIDALM,
    TOC,
    TOW,
    WN,
    S,
    U,
)
from pygnssutils.rinex_globals import (
    CNAV,
    LNAV,
    P2_N4,
    P2_N5,
    P2_N6,
    P2_N8,
    P2_N9,
    P2_N11,
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

GPS_LNAV_TLM = {
    SUBFRAMELENGTH: 300,
    PREAMBLE: (8, U, 0),
    "tlm": (14, U, 0),
    "integrity": (1, U, 0),
    "_reserved1": (1, U, 0),
    "_parity1": (6, U, 0),
}

GPS_LNAV_HOW = {
    TOW: (17, U, 6),  # TOW * 6 = seconds
    "alert": (1, U, 0),
    "antispoof": (1, U, 0),
    SID: (3, U, 0),  # subframe id
    "_non1": (2, U, 0),
    "_parity2": (6, U, 0),
}

GPS_LNAV_GENERIC = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # words 3 - 10
    "_word3_10": (240, U, 0),
}

GPS_LNAV_SUBFRAME_1 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    WN: (10, U, 1),  # used to derive epoch
    "l2codes": (2, U, 1),
    "ura": (4, U, 1),
    "svhealth": (6, U, 1),
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
    TOC: (16, U, P2_P4),  # used to derive epoch
    "_parity8": (6, U, 0),
    # word9
    "af2": (8, S, P2_N55),
    "af1": (16, S, P2_N43),
    "_parity9": (6, U, 0),
    # word10
    "af0": (22, S, P2_N31),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # clock corrections

GPS_LNAV_SUBFRAME_2 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
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
}  # emphemeredes 1 of 2

GPS_LNAV_SUBFRAME_3 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
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
}  # emphemeredes 2 of 2

GPS_LNAV_SUBFRAME_45_GENERIC = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "_word3_10": (232, U, 0),
}

GPS_LNAV_SUBFRAME_5_P01 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SVIDALM: (6, U, 0),  # = subframe page id (will replace '#' below)
    "e#": (16, U, P2_N21),
    "_parity3": (6, U, 0),
    # word4
    "toa#": (8, U, P2_P12),
    "deltai#": (16, S, P2_N19),
    "_parity4": (6, U, 0),
    # word5
    "omegadot#": (16, S, P2_N38),
    "svhealth#": (8, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "sqrta#": (24, U, P2_N11),
    "_parity6": (6, U, 0),
    # word7
    "omega0#": (24, S, P2_N23),
    "_parity7": (6, U, 0),
    # word8
    "omega#": (24, S, P2_N23),
    "_parity8": (6, U, 0),
    # word9
    "m0#": (24, S, P2_N23),
    "_parity9": (6, U, 0),
    # word10
    "af0#_msb": (8, S, P2_N20),
    "af1#": (11, S, P2_N38),
    "af0#_lsb": (3, U, P2_N20),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # almanac

GPS_LNAV_SUBFRAME_5_P25 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "toa": (8, U, P2_P12),
    "wna": (8, U, 1),
    "_parity3": (6, U, 0),
    # word4
    "sv01health": (6, U, 0),
    "sv02health": (6, U, 0),
    "sv03health": (6, U, 0),
    "sv04health": (6, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "sv05health": (6, U, 0),
    "sv06health": (6, U, 0),
    "sv07health": (6, U, 0),
    "sv08health": (6, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "sv09health": (6, U, 0),
    "sv10health": (6, U, 0),
    "sv11health": (6, U, 0),
    "sv12health": (6, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "sv13health": (6, U, 0),
    "sv14health": (6, U, 0),
    "sv15health": (6, U, 0),
    "sv16health": (6, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "sv17health": (6, U, 0),
    "sv18health": (6, U, 0),
    "sv19health": (6, U, 0),
    "sv20health": (6, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "sv21health": (6, U, 0),
    "sv22health": (6, U, 0),
    "sv23health": (6, U, 0),
    "sv24health": (6, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "_reserved2": (6, U, 0),
    "_reserved3": (16, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # SV health

GPS_LNAV_SUBFRAME_4_P01 = {
    # 1,6,11,16,21
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "_reserved2": (16, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "_reserved3": (24, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "_reserved4": (24, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "_reserved5": (24, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "_reserved6": (24, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "_reserved7": (24, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "_reserved8": (8, U, 0),
    "_reserved9": (16, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "af0": (22, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # reserved

GPS_LNAV_SUBFRAME_4_P12 = {
    # 12,19,20,22,23,24
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "_reserved2": (16, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "_reserved3": (24, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "_reserved4": (24, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "_reserved5": (24, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "_reserved6": (24, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "_reserved7": (24, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "_reserved8": (8, U, 0),
    "_reserved9": (16, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "_reserved10": (22, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # reserved

GPS_LNAV_SUBFRAME_4_P18 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
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
}  # ionospheric corrections

GPS_LNAV_SUBFRAME_4_P25 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "sv01asc": (4, U, 0),
    "sv02asc": (4, U, 0),
    "sv03asc": (4, U, 0),
    "sv04asc": (4, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "sv05asc": (4, U, 0),
    "sv06asc": (4, U, 0),
    "sv07asc": (4, U, 0),
    "sv08asc": (4, U, 0),
    "sv09asc": (4, U, 0),
    "sv10asc": (4, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "sv11asc": (4, U, 0),
    "sv12asc": (4, U, 0),
    "sv13asc": (4, U, 0),
    "sv14asc": (4, U, 0),
    "sv15asc": (4, U, 0),
    "sv16asc": (4, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "sv17asc": (4, U, 0),
    "sv18asc": (4, U, 0),
    "sv19asc": (4, U, 0),
    "sv20asc": (4, U, 0),
    "sv21asc": (4, U, 0),
    "sv22asc": (4, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "sv23asc": (4, U, 0),
    "sv24asc": (4, U, 0),
    "sv25asc": (4, U, 0),
    "sv26asc": (4, U, 0),
    "sv27asc": (4, U, 0),
    "sv28asc": (4, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "sv29asc": (4, U, 0),
    "sv30asc": (4, U, 0),
    "sv31asc": (4, U, 0),
    "sv32asc": (4, U, 0),
    "_reserved2": (2, U, 0),
    "sv25health": (6, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "sv26health": (6, U, 0),
    "sv27health": (6, U, 0),
    "sv28health": (6, U, 0),
    "sv29health": (6, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "sv30health": (6, U, 0),
    "sv31health": (6, U, 0),
    "sv32health": (6, U, 0),
    "_reserved3": (4, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # SV anti-spoof

GPS_LNAV_SUBFRAME_4_P13 = {
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "avail": (2, U, 0),
    "erd1": (6, U, 0),
    "erd2": (6, U, 0),
    "erd3_msb": (2, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "erd3_lsb": (4, U, 0),
    "erd4": (6, U, 0),
    "erd5": (6, U, 0),
    "erd6": (6, U, 0),
    "erd7_msb": (2, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "erd7_lsb": (4, U, 0),
    "erd8": (6, U, 0),
    "erd9": (6, U, 0),
    "erd10": (6, U, 0),
    "erd11_msb": (2, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "erd11_lsb": (4, U, 0),
    "erd12": (6, U, 0),
    "erd13": (6, U, 0),
    "erd14": (6, U, 0),
    "erd15_msb": (2, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "erd15_lsb": (4, U, 0),
    "erd16": (6, U, 0),
    "erd17": (6, U, 0),
    "erd18": (6, U, 0),
    "erd19_msb": (2, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "erd19_lsb": (4, U, 0),
    "erd20": (6, U, 0),
    "erd21": (6, U, 0),
    "erd22": (6, U, 0),
    "erd23_msb": (2, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "erd23_lsb": (4, U, 0),
    "erd24": (6, U, 0),
    "erd25": (6, U, 0),
    "erd26": (6, U, 0),
    "erd27_msb": (2, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "erd27_lsb": (4, U, 0),
    "erd28": (6, U, 0),
    "erd29": (6, U, 0),
    "erd30": (6, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # Navigation Message Correction Table (NMCT) estimated range deviation

GPS_LNAV_SUBFRAME_4_P14 = {
    # 14,15,17
    # word1
    **GPS_LNAV_TLM,
    # word2
    **GPS_LNAV_HOW,
    # word3
    "dataid": (2, U, 0),
    SPID: (6, U, 0),
    "_reserved2": (16, U, 0),
    "_parity3": (6, U, 0),
    # word4
    "_reserved3": (24, U, 0),
    "_parity4": (6, U, 0),
    # word5
    "_reserved4": (24, U, 0),
    "_parity5": (6, U, 0),
    # word6
    "_reserved5": (24, U, 0),
    "_parity6": (6, U, 0),
    # word7
    "_reserved6": (24, U, 0),
    "_parity7": (6, U, 0),
    # word8
    "_reserved7": (24, U, 0),
    "_parity8": (6, U, 0),
    # word9
    "_reserved8": (24, U, 0),
    "_parity9": (6, U, 0),
    # word10
    "_reserved9": (22, U, 0),
    "_non2": (2, U, 0),
    "_parity10": (6, U, 0),
}  # reserved

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
    "word": (300, U, 0),
    "padding": (20, U, 0),
}  # 10 * 32-bit dwrds

GPS_CNAV_TLM = {
    SUBFRAMELENGTH: 300,
    PREAMBLE: (8, U, 0),
    "prn": (6, U, 0),
    SID: (6, U, 0),
    TOW: (17, U, 6),  # TOW * 6 = seconds
    "alert": (1, U, 0),
}

GPS_CNAV_CLOCK = {
    "top": (11, U, 300),
    "uraned0": (5, S, 0),
    "uraned1": (3, U, 0),
    "uraned2": (3, U, 0),
    TOC: (11, U, 300),  # used to derive epoch
    "af0n": (26, S, P2_N35),
    "af1n_msb": (3, S, P2_N48),
    "af1n_lsb": (17, S, P2_N48),
    "af2n": (10, S, P2_N60),
}

GPS_CNAV_PARITY = {
    "_parity": (24, U, 0),
}

GPS_CNAV_RAP = {
    SVIDALM: (6, U, 0),  # will replace '#' below
    "deltaa#": (8, S, P2_P9),  # Relative to Aref = 26,559,710 meters, meters
    "omega0#": (7, S, P2_N6),  # semi-circles
    "phi0#": (7, S, P2_N6),  # M0 + omega, semi-circles
    "l1health#": (1, U, 0),
    "l2health#": (1, U, 0),
    "l5health#": (1, U, 0),
}
# 31 bit reduced almanac packet

GPS_CNAV_CDC = {
    "prn": (8, U, 0),
    "deltaaf0": (13, U, P2_N35),
    "deltaaf1": (8, U, P2_N51),
    "udra": (5, S, 0),
}
# 34 bit clock differential correction

GPS_CNAV_EDC = {
    "prn": (8, U, 0),
    "deltaalpha": (14, S, P2_N34),
    "deltabeta": (14, S, P2_N34),
    "deltalambda": (15, S, P2_N32),
    "deltai": (12, S, P2_N31),
    "deltaomega": (12, S, P2_N32),
    "deltaa": (12, S, P2_N9),
    "udradot": (5, S, 0),
}
# 92 bit ephemeris differential correction

GPS_CNAV_SUBFRAME_10 = {
    **GPS_CNAV_TLM,
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
    **GPS_CNAV_PARITY,
}  # Ephemeris 1

GPS_CNAV_SUBFRAME_11 = {
    **GPS_CNAV_TLM,
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
    **GPS_CNAV_PARITY,
}  # Ephemeris 2

GPS_CNAV_SUBFRAME_12 = {
    **GPS_CNAV_TLM,
    "wna": (13, U, 0),
    "toa": (8, U, P2_P12),
    "rap_grp": (
        7,
        {
            **GPS_CNAV_RAP,
        },
    ),
    **GPS_CNAV_PARITY,
}  # Reduced Almanac

GPS_CNAV_SUBFRAME_13 = {
    **GPS_CNAV_TLM,
    "topd": (11, U, 300),
    "tod": (11, U, 300),
    "cdc_grp": (
        6,
        {
            "dctype": (1, U, 0),
            **GPS_CNAV_CDC,
        },
    ),
    "_reserved1": (6, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock Differential Correction

GPS_CNAV_SUBFRAME_14 = {
    **GPS_CNAV_TLM,
    "topd": (11, U, 300),
    "tod": (11, U, 300),
    "edc_grp": (
        2,
        {
            **GPS_CNAV_EDC,
        },
    ),
    "_reserved1": (30, U, 0),
    **GPS_CNAV_PARITY,
}  # Ephemeris Differential Correction

GPS_CNAV_SUBFRAME_15 = {
    **GPS_CNAV_TLM,
    "text": (232, U, 0),
    "textpage": (4, U, 0),
    "_reserved1": (2, U, 0),
    **GPS_CNAV_PARITY,
}  # Text

GPS_CNAV_SUBFRAME_30 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
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
    **GPS_CNAV_PARITY,
}  # Clock, IONO & Group Delay

GPS_CNAV_SUBFRAME_31 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "wna": (13, U, 0),
    "toa": (8, U, P2_P12),
    "rap_grp": (
        4,
        {
            **GPS_CNAV_RAP,  # GPS_CNAV_RAP
        },
    ),
    "_reserved1": (4, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Reduced Almanac

GPS_CNAV_SUBFRAME_32 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "teop": (16, U, P2_P4),
    "pmx": (21, S, P2_N20),
    "pmxdot": (15, S, P2_N21),
    "pmy": (21, S, P2_N20),
    "pmydot": (15, S, P2_N21),
    "deltautgps": (31, S, P2_N23),
    "deltautgpsdot": (19, S, P2_N25),
    "_reserved1": (11, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Earth Orientation Parameters

GPS_CNAV_SUBFRAME_33 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
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
    **GPS_CNAV_PARITY,
}  # Clock & UTC

GPS_CNAV_SUBFRAME_34 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "topd": (11, U, 300),
    "tod": (11, U, 300),
    "dctype": (1, U, 0),
    "cdc": (34, U, 0),  # GPS_CNAV_CDC
    "edc_msb": (16, U, 0),  # GPS_CNAV_EDC
    "edc_lsb": (76, U, 0),
    # "_reserved1": (51, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Differential Correction

GPS_CNAV_SUBFRAME_35 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "tggto": (16, U, P2_P4),
    "wnggto": (13, U, 1),
    "gnssid": (3, U, 0),
    "a0ggto": (16, U, P2_N35),
    "a1ggto": (13, U, P2_N51),
    "a2ggto": (7, U, P2_N68),
    "_reserved1": (5, U, 0),
    "_reserved2": (76, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & GGTO (GPS/GNSS Time Offset)

GPS_CNAV_SUBFRAME_36 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "text_msb": (73, U, 0),
    "text_lsb": (71, U, 0),
    "textpage": (4, U, 0),
    "_reserved1": (1, U, 0),
    **GPS_CNAV_PARITY,
}  # Clock & Text

GPS_CNAV_SUBFRAME_37 = {
    **GPS_CNAV_TLM,
    **GPS_CNAV_CLOCK,
    "wna": (13, U, 0),
    "toa": (8, U, P2_P12),
    SVIDALM: (6, U, 0),
    "l1health#": (1, U, 0),
    "l2health#": (1, U, 0),
    "l5health#": (1, U, 0),
    "e#": (11, U, P2_N16),
    "omegai#": (11, S, P2_N14),
    "omegadot#": (11, S, P2_N33),
    "sqrta#": (17, U, P2_N4),
    "omega0#": (16, S, P2_N15),
    "omega#": (16, S, P2_N15),
    "m0#": (16, S, P2_N15),
    "af0#": (11, S, P2_N20),
    "af1#": (10, S, P2_N37),
    **GPS_CNAV_PARITY,
}  # Clock & Midi Almanac

GPS_CNAV_SUBFRAME_40 = {
    **GPS_CNAV_TLM,
    "gnssid": (4, U, 0),
    "wnism": (13, U, 1),
    "towism": (6, U, 4),
    "tcorrel": (4, U, 0),
    "bnom": (4, U, 0),
    "lambdanom": (4, U, 0),
    "rsat": (4, U, 0),
    "pconst": (4, U, 0),
    "mfd": (4, U, 0),
    "servicelevel": (3, U, 0),
    "mask": (63, U, 0),
    "filler": (93, U, 0),
    "_ism_crc": (32, U, 0),
    **GPS_CNAV_PARITY,
}  # Integrity Support Message

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
GPS_SUBFRAMEACQ_MAP = {
    LNAV: {
        TARGET: 0b1111,  # subframes 1,2,3,4p56
        START: 1,
        (1, 0): (GPS_LNAV_SUBFRAME_1, 1),
        (2, 0): (GPS_LNAV_SUBFRAME_2, 2),
        (3, 0): (GPS_LNAV_SUBFRAME_3, 4),
        (4, 56): (GPS_LNAV_SUBFRAME_4_P18, 8),
        # (5, 1): (GPS_LNAV_SUBFRAME_5_P01, 16),
        # (5, 2): (GPS_LNAV_SUBFRAME_5_P01, 32),
        # (5, 3): (GPS_LNAV_SUBFRAME_5_P01, 64),
        # (5, 4): (GPS_LNAV_SUBFRAME_5_P01, 128),
        # (5, 5): (GPS_LNAV_SUBFRAME_5_P01, 256),
        # (5, 6): (GPS_LNAV_SUBFRAME_5_P01, 512),
        # (5, 7): (GPS_LNAV_SUBFRAME_5_P01, 1024),
        # (5, 8): (GPS_LNAV_SUBFRAME_5_P01, 2048),
        # (5, 9): (GPS_LNAV_SUBFRAME_5_P01, 4096),
        # (5, 10): (GPS_LNAV_SUBFRAME_5_P01, 8192),
        # (5, 11): (GPS_LNAV_SUBFRAME_5_P01, 16384),
        # (5, 12): (GPS_LNAV_SUBFRAME_5_P01, 2**15),
        # (5, 13): (GPS_LNAV_SUBFRAME_5_P01, 2**16),
        # (5, 14): (GPS_LNAV_SUBFRAME_5_P01, 2**17),
        # (5, 15): (GPS_LNAV_SUBFRAME_5_P01, 2**18),
        # (5, 16): (GPS_LNAV_SUBFRAME_5_P01, 2**19),
        # (5, 17): (GPS_LNAV_SUBFRAME_5_P01, 2**20),
        # (5, 18): (GPS_LNAV_SUBFRAME_5_P01, 2**21),
        # (5, 19): (GPS_LNAV_SUBFRAME_5_P01, 2**22),
        # (5, 20): (GPS_LNAV_SUBFRAME_5_P01, 2**23),
        # (5, 21): (GPS_LNAV_SUBFRAME_5_P01, 2**24),
        # (5, 22): (GPS_LNAV_SUBFRAME_5_P01, 2**25),
        # (5, 23): (GPS_LNAV_SUBFRAME_5_P01, 2**26),
        # (5, 24): (GPS_LNAV_SUBFRAME_5_P01, 2**27),
        # (4, 25): (GPS_LNAV_SUBFRAME_5_P01, 2**28),
        # (4, 26): (GPS_LNAV_SUBFRAME_5_P01, 2**29),
        # (4, 27): (GPS_LNAV_SUBFRAME_5_P01, 2**30),
        # (4, 28): (GPS_LNAV_SUBFRAME_5_P01, 2**31),
        # (4, 29): (GPS_LNAV_SUBFRAME_5_P01, 2**32),
        # (4, 30): (GPS_LNAV_SUBFRAME_5_P01, 2**33),
        # (4, 31): (GPS_LNAV_SUBFRAME_5_P01, 2**34),
        # (4, 32): (GPS_LNAV_SUBFRAME_5_P01, 2**35),
        # (4, 52): (GPS_LNAV_SUBFRAME_4_P13, 2**36),
        # (4, 53): (GPS_LNAV_SUBFRAME_4_P14, 2**37),
        # (4, 54): (GPS_LNAV_SUBFRAME_4_P14, 2**38),
        # (4, 55): (GPS_LNAV_SUBFRAME_4_P14, 2**39),
        # (4, 57): (GPS_LNAV_SUBFRAME_4_P01, 2**40),
        # (4, 58): (GPS_LNAV_SUBFRAME_4_P12, 2**41),
        # (4, 59): (GPS_LNAV_SUBFRAME_4_P12, 2**42),
        # (4, 60): (GPS_LNAV_SUBFRAME_4_P12, 2**43),
        # (4, 61): (GPS_LNAV_SUBFRAME_4_P12, 2**44),
        # (4, 62): (GPS_LNAV_SUBFRAME_4_P12, 2**45),
        # (4, 63): (GPS_LNAV_SUBFRAME_4_P25, 2**46),
        # (5, 51): (GPS_LNAV_SUBFRAME_5_P25, 2**47),
    },
    CNAV: {
        TARGET: 0b11111,  # subframes 10,11,30,32,33
        START: 10,
        (10, 0): (GPS_CNAV_SUBFRAME_10, 1),
        (11, 0): (GPS_CNAV_SUBFRAME_11, 2),
        (30, 0): (GPS_CNAV_SUBFRAME_30, 4),
        (32, 0): (GPS_CNAV_SUBFRAME_32, 8),  # EOP
        (33, 0): (GPS_CNAV_SUBFRAME_33, 16),
        # (12, 0): (GPS_CNAV_SUBFRAME_12, 32),
        # (13, 0): (GPS_CNAV_SUBFRAME_13, 64),
        # (14, 0): (GPS_CNAV_SUBFRAME_14, 128),
        # (15, 0): (GPS_CNAV_SUBFRAME_15, 256),
        # (31, 0): (GPS_CNAV_SUBFRAME_31, 512),
        # (34, 0): (GPS_CNAV_SUBFRAME_34, 1024),
        # (35, 0): (GPS_CNAV_SUBFRAME_35, 2048),
        # (36, 0): (GPS_CNAV_SUBFRAME_36, 4096),
        # (37, 0): (GPS_CNAV_SUBFRAME_37, 8192),
        # (40, 0): (GPS_CNAV_SUBFRAME_40, 16384),
    },
}
