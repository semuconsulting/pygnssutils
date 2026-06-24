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

from pygnssutils.rawnav import PREAMBLE, SID, SUBFRAMELENGTH, TOC, TOW, WN, S, U
from pygnssutils.rinex_globals import (
    L1CA,
    P2_N3,
    P2_N11,
    P2_N30,
    P2_N31,
    P2_N39,
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
    SUBFRAMELENGTH: 250,
    PREAMBLE: (8, U, 0),
    SID: (6, U, 0),  # MT record number
}

SBA_L1CA_MT_END = {
    "_parity": (24, U, 0),
}

SBA_L1CA_MT_1 = {
    **SBA_L1CA_MT_TLM,
    "prnmask": (210, U, 0),
    "iodp": (2, U, 0),
    **SBA_L1CA_MT_END,
}  # PRN mask

SBA_L1CA_MT_2 = {
    **SBA_L1CA_MT_TLM,
    "iodf": (2, U, 1),
    "iodp": (2, U, 1),
    "prc_grp": (  # repeating group x 13
        13,
        {
            "prc": (12, S, P2_N3),
        },
    ),
    "udrei_grp": (  # repeating group x 13
        13,
        {
            "udrei": (4, U, 1),
        },
    ),
    **SBA_L1CA_MT_END,
}  # fast corrections
SBA_L1CA_MT_0 = SBA_L1CA_MT_2  # while testing, otherwise all zeros
SBA_L1CA_MT_3 = SBA_L1CA_MT_2
SBA_L1CA_MT_4 = SBA_L1CA_MT_2
SBA_L1CA_MT_5 = SBA_L1CA_MT_2

SBA_L1CA_MT_6 = {
    **SBA_L1CA_MT_TLM,
    "iodf2": (2, U, 1),
    "iodf3": (2, U, 1),
    "iodf4": (2, U, 1),
    "iodf5": (2, U, 1),
    "udrei_grp": (  # repeating group x 51
        51,
        {
            "udrei": (4, U, 1),
        },
    ),
    **SBA_L1CA_MT_END,
}  # integrity

SBA_L1CA_MT_7 = {
    **SBA_L1CA_MT_TLM,
    "tl": (4, U, 1),
    "iodp": (2, U, 1),
    "_spare": (2, U, 0),
    "udre_grp": (  # repeating group x 51
        51,
        {
            "udre": (4, U, 1),
        },
    ),
    **SBA_L1CA_MT_END,
}  # fast correction degradation factors

SBA_L1CA_MT_9 = {
    **SBA_L1CA_MT_TLM,
    "iodn": (8, U, 0),  # marked as reserved
    "t0": (13, U, 16),
    "ura": (4, U, 0),  # 15 = do not use for ranging
    "xpos": (30, S, 0.08),
    "ypos": (30, S, 0.08),
    "zpos": (25, S, 0.4),
    "xdot": (17, S, 0.000625),
    "ydot": (17, S, 0.000625),
    "zdot": (18, S, 0.004),
    "xdot2": (10, S, 0.0000125),
    "ydot2": (10, S, 0.0000125),
    "zdot2": (10, S, 0.0000625),
    "agf0": (12, S, P2_N31),
    "agf1": (8, S, P2_N40),
    **SBA_L1CA_MT_END,
}  # GEO navigation

SBA_L1CA_MT_10 = {
    **SBA_L1CA_MT_TLM,
    "brrc": (10, U, 0.002),
    "cltc_lsb": (10, U, 0.002),
    "cltc_v1": (10, U, 0.00005),
    "iltc_v1": (9, U, 1),
    "cltc_v0": (10, U, 0.002),
    "iltc_v0": (9, U, 1),
    "cgeo_lsb": (10, U, 0.0005),
    "cgeo_v": (10, U, 0.00005),
    "igeo": (9, U, 1),
    "cer": (6, U, 0.5),
    "ciono_step": (10, U, 0.001),
    "iiono": (9, U, 1),
    "ciono_ramp": (10, U, 0.000005),
    "rssudre": (1, U, 0),
    "rssiono": (1, U, 0),
    "ccovariance": (7, U, 0.1),
    "_spare": (81, U, 0),
    **SBA_L1CA_MT_END,
}  # degradation factors

SBA_L1CA_MT_12 = {
    **SBA_L1CA_MT_TLM,
    "a1": (24, S, P2_N50),
    "a0": (32, S, P2_N30),
    TOC: (8, U, P2_P12),  # tot
    "wnt": (8, U, 1),
    "deltatls": (8, S, 1),
    "wnlsf": (8, U, 1),
    "dn": (8, U, 1),
    "deltatlsf": (8, S, 1),
    "utcid": (3, U, 1),  # see UTCID lookup
    TOW: (20, U, 1),
    WN: (10, U, 1),
    "gloind": (1, U, 0),
    "deltatglo": (74, U, 0),
    **SBA_L1CA_MT_END,
}  # Network time offset

SBA_L1CA_MT_17 = {
    **SBA_L1CA_MT_TLM,
    "prn_grp": (  # repeating group x 3
        3,
        {
            "dataid": (2, U, 0),
            "prn": (8, U, 0),
            "svhealth": (8, U, 0),
            # Bit 0 (LSB) Ranging On (0), Off (1); 1 = do not use for ranging
            # Bit 1 Corrections On (0), Off (1); 1 = do not use for corrections
            # Bit 2 Broadcast Integrity On (0), Off (1)
            # Bits 3 Reserved
            # Bits 4-7 Service Provider ID
            "xg": (15, S, 2600),
            "yg": (15, S, 2600),
            "zg": (9, S, 26000),
            "xgdot": (3, S, 10),
            "ygdot": (3, S, 10),
            "zgdot": (4, S, 60),
        },
    ),
    "t0": (11, S, 64),
    **SBA_L1CA_MT_END,
}  # GEO almanac

SBA_L1CA_MT_18 = {
    **SBA_L1CA_MT_TLM,
    "numbands": (4, U, 1),
    "bandno": (4, U, 1),
    "iodi": (2, U, 1),
    "igpmask": (201, U, 1),
    "_spare": (1, U, 0),
    **SBA_L1CA_MT_END,
}  # ionospheric grid mask

SBA_L1CA_MT_25_V0 = {
    "prn_grp": (  # repeating group x 2
        2,
        {
            "prnmask": (6, U, 1),
            "iod": (8, S, 1),
            "deltax": (9, S, P2_N3),
            "deltay": (9, S, P2_N3),
            "deltaz": (9, S, P2_N3),
            "deltaaf0": (10, S, P2_N31),
        },
    ),
    "iodpv0": (2, U, 1),
    "_spare2": (1, U, 0),
}  # 105 bits - Position and Clock Offset Corrections Only

SBA_L1CA_MT_25_V1 = {
    "prn_grp": (  # nominal repeating group x 1
        1,
        {
            "prnmask": (6, U, 1),
            "iod": (8, S, 1),
            "deltax": (11, S, P2_N3),
            "deltay": (11, S, P2_N3),
            "deltaz": (11, S, P2_N3),
            "deltaaf0": (11, S, P2_N31),
            "deltaxdot": (8, S, P2_N11),
            "deltaydot": (8, S, P2_N11),
            "deltazdot": (8, S, P2_N11),
            "deltaaf1": (8, S, P2_N39),
        },
    ),
    "t0": (13, U, 16),
    "iodpv1": (2, U, 0),
}  # 105 bits - Velocity and Clock Drift Corrections Included

SBA_L1CA_MT_24 = {
    **SBA_L1CA_MT_TLM,
    "prn_grp": (  # repeating group x 6
        6,
        {
            "prc": (12, S, P2_N3),
        },
    ),
    "udrei_grp": (  # repeating group x 6
        6,
        {
            "udrei": (4, U, 1),
        },
    ),
    "iodpfc": (2, U, 0),
    "blockid": (2, U, 0),
    "iodffc": (2, U, 0),
    "_spare1": (4, U, 0),
    "velcode": (1, U, 1),  # velocity code = 0 or 1
    "v0_alt": (  # if velcode = 0
        ("velcode", 0),
        {**SBA_L1CA_MT_25_V0},
    ),
    "v1_alt": (  # if velcode = 1
        ("velcode", 1),
        {**SBA_L1CA_MT_25_V1},
    ),
    **SBA_L1CA_MT_END,
}  # mixed fast correction / long term satellite error

SBA_L1CA_MT_25 = {
    **SBA_L1CA_MT_TLM,
    "velcode1": (1, U, 1),  # velocity code = 0 or 1
    "v10_alt": (  # if velcode1 = 0
        ("velcode1", 0),
        {**SBA_L1CA_MT_25_V0},
    ),
    "v11_alt": (  # if velcode1 = 1
        ("velcode1", 1),
        {**SBA_L1CA_MT_25_V1},
    ),
    "velcode2": (1, U, 1),  # velocity code = 0 or 1
    "v20_alt": (  # if velcode2 = 0
        ("velcode2", 0),
        {**SBA_L1CA_MT_25_V0},
    ),
    "v21_alt": (  # if velcode2 = 1
        ("velcode2", 1),
        {**SBA_L1CA_MT_25_V1},
    ),
    **SBA_L1CA_MT_END,
}  # long term satellite error correction

SBA_L1CA_MT_26 = {
    **SBA_L1CA_MT_TLM,
    "bandno": (4, U, 1),
    "blockid": (4, U, 1),
    "igp_grp": (  # repeating group x 15
        15,
        {
            "igpvde": (9, U, P2_N3),
            "givei": (4, U, 1),
        },
    ),
    "iodi": (2, U, 1),
    "_spare": (7, U, 0),
    **SBA_L1CA_MT_END,
}  # ionospheric delay model parameters

SBA_L1CA_MT_27 = {
    **SBA_L1CA_MT_TLM,
    "iods": (3, U, 1),
    "nummsg": (3, U, 1),
    "msgno": (3, U, 1),
    "numregions": (3, U, 1),
    "ptycode": (2, U, 1),
    "deltaudre_in": (4, U, 1),
    "deltaudre_out": (4, U, 1),
    "shape_grp": (  # repeating group x 5
        5,
        {
            "lat1": (8, S, 1),
            "lon1": (9, S, 1),
            "lat2": (8, S, 1),
            "lon2": (9, S, 1),
            "shape": (1, U, 1),
        },
    ),
    "_spare": (15, U, 1),
    **SBA_L1CA_MT_END,
}  # service message parameters

SBA_L1CA_MT_28 = {
    **SBA_L1CA_MT_TLM,
    "iodp": (2, U, 1),
    "prn_grp": (  # repeating group x 2
        2,
        {
            "prnmaskno": (6, U, 1),
            "scaleexp": (3, U, 1),
            "e11": (9, U, 1),
            "e22": (9, U, 1),
            "e33": (9, U, 1),
            "e44": (9, U, 1),
            "e12": (10, S, 1),
            "e13": (10, S, 1),
            "e14": (10, S, 1),
            "e23": (10, S, 1),
            "e24": (10, S, 1),
            "e34": (10, S, 1),
        },
    ),
    **SBA_L1CA_MT_END,
}  # clock emphemeris covariance

# mapping for (subframe, page) acquisition mask subframeacq
# NB subframes containing only almanac data are not generally
# required for RINEX conversion purposes
SBA_SUBFRAMEACQ_MAP = {
    L1CA: {
        TARGET: 0b111,  # Message Type (MT) codes 9,12,17
        START: 9,
        (9, 0): (SBA_L1CA_MT_9, 1),
        (12, 0): (SBA_L1CA_MT_12, 2),
        (17, 0): (SBA_L1CA_MT_17, 4),
        # (6, 0): (SBA_L1CA_MT_6, 8),
        # (7, 0): (SBA_L1CA_MT_7, 16),
        # (10, 0): (SBA_L1CA_MT_10, 32),
        # (18, 0): (SBA_L1CA_MT_18, 64),
        # (24, 0): (SBA_L1CA_MT_24, 128),
        # (25, 0): (SBA_L1CA_MT_25, 256),
        # (26, 0): (SBA_L1CA_MT_26, 512),
        # (27, 0): (SBA_L1CA_MT_27, 1024),
        # (28, 0): (SBA_L1CA_MT_28, 2048),
    },
}
