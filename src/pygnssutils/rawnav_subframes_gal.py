"""
rawnav_subframes_gal.py

Galileo NAV Subframe definitions.

E1,E5a,E6: https://www.gsc-europa.eu/sites/default/files/sites/all/files/Galileo_OS_SIS_ICD_v2.1.pdf

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

# pylint: disable=fixme

from pygnssutils.rawnav import SID, SUBFRAMELENGTH, TOC, TOW, WN, S, U
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
    "word": (244, U, 0),
    "padding": (12, U, 0),
}  # 8 * 32-bit dwrds

GAL_FNAV_SUBFRAME_TLM = {
    SUBFRAMELENGTH: 244,
    SID: (6, U, 0),  # subframe id
}

GAL_FNAV_CRC = {
    "_parity": (24, U, 0),
    "_tail": (6, U, 0),
}

GAL_FNAV_SUBFRAME_GENERIC = {
    **GAL_FNAV_SUBFRAME_TLM,
    "payload": (208, U, 0),
    **GAL_FNAV_CRC,
}

# SVID, Clock correction, SISA, Ionospheric correction (NEQUICK-G),
# BGD, GST, Signal health and Data validity status
GAL_FNAV_SUBFRAME_1 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "sv": (6, U, 0),
    "iodn": (10, U, 0),
    TOC: (14, U, 60),
    "af0": (31, S, P2_N34),
    "af1": (21, S, P2_N46),
    "af2": (6, S, P2_N59),
    "sisa": (8, U, 0),
    "ai0": (11, U, P2_N2),
    "ai1": (11, S, P2_N8),
    "ai2": (14, S, P2_N15),
    "idf1": (1, U, 0),
    "idf2": (1, U, 0),
    "idf3": (1, U, 0),
    "idf4": (1, U, 0),
    "idf5": (1, U, 0),
    "bgde5a": (10, S, P2_N32),
    "e5ahs": (2, U, 0),
    WN: (12, U, 1),  # used to derive epoch
    TOW: (20, U, 1),  # used to derive epoch
    "e5advs": (1, U, 0),
    "_spare": (26, U, 0),
    **GAL_FNAV_CRC,
}

# Ephemeris (1/3) and GST
GAL_FNAV_SUBFRAME_2 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (10, U, 0),
    "m0": (32, S, P2_N31),
    "omegadot": (24, S, P2_N43),
    "e": (32, U, P2_N33),
    "sqrta": (32, U, P2_N19),
    "omega0": (32, S, P2_N31),
    "idot": (14, S, P2_N43),
    WN: (12, U, 1),
    TOW: (20, U, 1),
    **GAL_FNAV_CRC,
}

# Ephemeris (2/3) and GST
GAL_FNAV_SUBFRAME_3 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (10, U, 0),
    "i0": (32, S, P2_N31),
    "omega": (32, S, P2_N31),
    "deltan": (16, S, P2_N43),
    "cuc": (16, S, P2_N29),
    "cus": (16, S, P2_N29),
    "crc": (16, S, P2_N5),
    "crs": (16, S, P2_N5),
    "toe": (14, U, 60),
    WN: (12, U, 1),
    TOW: (20, U, 1),
    "_spare": (8, U, 0),
    **GAL_FNAV_CRC,
}

# Ephemeris (3/3), GST-UTC conversion, GST-GPS conversion and TOW.
GAL_FNAV_SUBFRAME_4 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "iodn": (10, U, 0),
    "cic": (16, S, P2_N29),
    "cis": (16, S, P2_N29),
    "a0": (32, S, P2_N30),
    "a1": (24, S, P2_N50),
    "deltatls": (8, S, 1),
    "tot": (8, U, 3600),
    "wn0t": (8, U, 1),
    "wnlsf": (8, U, 1),
    "dn": (3, U, 1),
    "deltatlsf": (8, S, 1),
    "t0g": (8, U, 3600),
    "a0g": (16, S, P2_N35),
    "a1g": (12, S, P2_N51),
    "wn0g": (6, U, 1),
    TOW: (20, U, 0),
    "_spare": (5, U, 0),
    **GAL_FNAV_CRC,
}

# Almanac (SVID1 and SVID2(1/2)), Week Number and almanac reference time
GAL_FNAV_SUBFRAME_5 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "ioda": (4, U, 0),
    "wna": (2, U, 1),
    "t0a": (10, U, 600),
    "sv1": (6, U, 0),
    "sv1_deltasqrta": (13, S, P2_N9),
    "sv1_e": (11, U, P2_N16),
    "sv1_omega": (16, S, P2_N15),
    "sv1_deltai": (11, S, P2_N14),
    "sv1_omega0": (16, S, P2_N15),
    "sv1_omegadot": (11, S, P2_N33),
    "sv1_m0": (16, S, P2_N15),
    "sv1_af0": (16, S, P2_N19),
    "sv1_af1": (13, S, P2_N38),
    "sv1_e5ahs": (2, U, 0),
    "sv2": (6, U, 0),
    "sv2_deltasqrta": (13, S, P2_N9),
    "sv2_e": (11, U, P2_N16),
    "sv2_omega": (16, S, P2_N15),
    "sv2_deltai": (11, S, P2_N14),
    "sv2_omega0_msb": (4, S, P2_N15),
    **GAL_FNAV_CRC,
}

# Almanac (SVID2(2/2) and SVID3)
GAL_FNAV_SUBFRAME_6 = {
    **GAL_FNAV_SUBFRAME_TLM,
    "ioda": (4, U, 0),
    "sv2_omega0_lsb": (12, S, P2_N15),
    "sv2_omegadot": (11, S, P2_N33),
    "sv2_m0": (16, S, P2_N15),
    "sv2_af0": (16, S, P2_N19),
    "sv2_af1": (13, S, P2_N38),
    "sv2_e5ahs": (2, U, 0),
    "sv3": (6, U, 0),
    "sv3_deltasqrta": (13, S, P2_N9),
    "sv3_e": (11, U, P2_N16),
    "sv3_omega": (16, S, P2_N15),
    "sv3_deltai": (11, S, P2_N14),
    "sv3_omega0": (16, S, P2_N15),
    "sv3_omegadot": (11, S, P2_N33),
    "sv3_m0": (16, S, P2_N15),
    "sv3_af0": (16, S, P2_N19),
    "sv3_af1": (13, S, P2_N38),
    "sv3_e5ahs": (2, U, 0),
    "_spare": (3, U, 0),
    **GAL_FNAV_CRC,
}

# **********************************************************************
# INAV - "7I" (E5b-I), "1B" (E1-B)
# **********************************************************************

# preamble = 0b0101100000

GAL_INAV_SUBFRAME = {
    SUBFRAMELENGTH: 256,
    "eo1": (1, U, 0),
    "pagetype1": (1, U, 0),  # 0 = nominal, 1 = alert
    "word_msb": (112, U, 0),  # 6 msb is word number
    "tail1": (6, U, 0),
    "padding1": (8, U, 0),
    "eo2": (1, U, 0),
    "pagetype2": (1, U, 0),
    "word_lsb": (16, U, 0),
    "reserved1": (40, U, 0),
    "sar": (22, U, 0),  # E-1B only, else reserved
    "spare": (2, U, 0),
    "crc": (24, U, 0),
    "ssp": (8, U, 0),
    "tail2": (6, U, 0),
    "padding2": (8, U, 0),
}  # 8 * 32-bit dwrds

# Ephemeris (1/4)
GAL_INAV_WORD_1 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "iodn": (10, U, 0),
    "toe": (14, U, 60),
    "m0": (32, S, P2_N31),
    "e": (32, U, P2_N33),
    "sqrta": (32, U, P2_N19),
    "_spare": (2, U, 0),
}

# Ephemeris (2/4)
GAL_INAV_WORD_2 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "iodn": (10, U, 0),
    "omega0": (32, S, P2_N31),
    "i0": (32, S, P2_N31),
    "omega": (32, S, P2_N31),
    "idot": (14, S, P2_N43),
    "_spare": (2, U, 0),
}

# Ephemeris (3/4) and SISA
GAL_INAV_WORD_3 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "iodn": (10, U, 0),
    "omegadot": (24, S, P2_N43),
    "deltan": (16, S, P2_N43),
    "cuc": (16, S, P2_N29),
    "cus": (16, S, P2_N29),
    "crc": (16, S, P2_N5),
    "crs": (16, S, P2_N5),
    "sisa": (8, U, 0),
}

# SVID, Ephemeris (4/4), and Clock correction parameters
GAL_INAV_WORD_4 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "iodn": (10, U, 0),
    "sv": (6, U, 0),
    "cic": (16, S, P2_N29),
    "cis": (16, S, P2_N29),
    TOC: (14, U, 60),
    "af0": (31, S, P2_N34),
    "af1": (21, S, P2_N46),
    "af2": (6, S, P2_N59),
    "_spare": (2, U, 0),
}

# Ionospheric correction, BGD, signal health and data validity status and GST
GAL_INAV_WORD_5 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "ai0": (11, U, P2_N2),
    "ai1": (11, S, P2_N8),
    "ai2": (14, S, P2_N15),
    "idf1": (1, U, 0),
    "idf2": (1, U, 0),
    "idf3": (1, U, 0),
    "idf4": (1, U, 0),
    "idf5": (1, U, 0),
    "bgde5a": (10, S, P2_N32),
    "bgde5b": (10, S, P2_N32),
    "e5ahs": (2, U, 0),
    "e5bhs": (2, U, 0),
    "e5advs": (1, U, 0),
    "e5bdvs": (1, U, 0),
    WN: (12, U, 1),  # used to derive epoch
    TOW: (20, U, 1),  # used to derive epoch
    "_spare": (23, U, 0),
}

# GST-UTC conversion parameters
GAL_INAV_WORD_6 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "a0": (32, S, P2_N30),
    "a1": (24, S, P2_N50),
    "deltatls": (8, S, 1),
    "tot": (8, U, 3600),
    "wn0t": (8, U, 1),
    "wnlsf": (8, U, 1),
    "dn": (3, U, 1),
    "deltatlsf": (8, S, 1),
    TOW: (20, U, 1),
    "_spare": (3, U, 0),
}

# Almanac for SVID1 (1/2), almanac reference time and almanac reference week number
GAL_INAV_WORD_7 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "ioda": (4, U, 0),
    "wna": (2, U, 1),
    "t0a": (10, U, 600),
    "sv1": (6, U, 0),
    "sv1_deltasqrta": (13, S, P2_N9),
    "sv1_e": (11, U, P2_N16),
    "sv1_omega": (16, S, P2_N15),
    "sv1_deltai": (11, S, P2_N14),
    "sv1_omega0": (16, S, P2_N15),
    "sv1_omegadot": (11, S, P2_N33),
    "sv1_m0": (16, S, P2_N15),
    "_reserved": (6, U, 0),
}

# Almanac for SVID1 (2/2) and SVID2 (1/2))
GAL_INAV_WORD_8 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "ioda": (4, U, 0),
    "sv1_af0": (16, S, P2_N19),
    "sv1_af1": (13, S, P2_N38),
    "sv1_e5ahs": (2, U, 0),
    "sv1_e5bhs": (2, U, 0),
    "sv2": (6, U, 0),
    "sv2_deltasqrta": (13, S, P2_N9),
    "sv2_e": (11, U, P2_N16),
    "sv2_omega": (16, S, P2_N15),
    "sv2_deltai": (11, S, P2_N14),
    "sv2_omega0": (16, S, P2_N15),
    "sv2_omegadot": (11, S, P2_N33),
    "_spare": (1, U, 0),
}

# Almanac for SVID2 (2/2) and SVID3 (1/2))
GAL_INAV_WORD_9 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "ioda": (4, U, 0),
    "wna": (2, U, 1),
    "t0a": (10, U, 600),
    "sv2_m0": (16, S, P2_N15),
    "sv2_af0": (16, S, P2_N19),
    "sv2_af1": (13, S, P2_N38),
    "sv2_e5ahs": (2, U, 0),
    "sv2_e5bhs": (2, U, 0),
    "sv3": (6, U, 0),
    "sv3_deltasqrta": (13, S, P2_N9),
    "sv3_e": (11, U, P2_N16),
    "sv3_omega": (16, S, P2_N15),
    "sv3_deltai": (11, S, P2_N14),
}

# Almanac for SVID3 (2/2) and GST-GPS conversion parameters
GAL_INAV_WORD_10 = {
    SUBFRAMELENGTH: 128,
    "wordid": (6, U, 0),
    "ioda": (4, U, 0),
    "sv3_omega0": (16, S, P2_N15),
    "sv3_omegadot": (11, S, P2_N33),
    "sv3_m0": (16, S, P2_N15),
    "sv3_af0": (16, S, P2_N19),
    "sv3_af1": (13, S, P2_N38),
    "sv3_e5ahs": (2, U, 0),
    "sv3_e5bhs": (2, U, 0),
    "a0g": (16, S, P2_N35),
    "a1g": (12, S, P2_N51),
    "t0g": (8, U, 3600),
    "wn0g": (6, U, 1),
}

# Reduced Clock and Ephemeris Data (CED) parameters
GAL_INAV_WORD_16 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "deltaared": (5, S, P2_P8),
    "exred": (13, S, P2_N22),
    "eyred": (13, S, P2_N22),
    "deltaiored": (17, S, P2_N22),
    "omega0red": (23, S, P2_N22),
    "lambda0red": (23, S, P2_N22),
    "af0red": (22, S, P2_N26),
    "af1red": (6, S, P2_N35),
}

# dummy word
GAL_INAV_WORD_0 = {
    SUBFRAMELENGTH: 128,
    SID: (6, U, 0),
    "time": (2, U, 0),
    "_spare": (88, U, 0),
    WN: (12, U, 1),
    TOW: (20, U, 1),
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
        # (5, 0): (GAL_FNAV_SUBFRAME_5, 16),
        # (6, 0): (GAL_FNAV_SUBFRAME_6, 32),
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
        # (7, 0): (GAL_INAV_WORD_7, 64),
        # (8, 0): (GAL_INAV_WORD_8, 128),
        # (9, 0): (GAL_INAV_WORD_9, 256),
        # (10, 0): (GAL_INAV_WORD_10, 512),
        # (16, 0): (GAL_INAV_WORD_16, 1024),
    },
}
