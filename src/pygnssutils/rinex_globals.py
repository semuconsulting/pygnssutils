"""
rinex_globals.py

RINEX global constants, decodes and enumerations.

https://files.igs.org/pub/data/format/rinex305.pdf

Created on 6 Oct 2025

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2025
:license: BSD 3-Clause
"""

# pylint: disable=line-too-long

from datetime import datetime, timezone

BDS = "C"
COLWIDTH = 80
CONT = "\u2192"  # "→"
DATAWIDTH = 60
EPOCH0_BEIDOU = datetime(2006, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
EPOCH0_GAL = datetime(1999, 8, 22, 0, 0, 0, tzinfo=timezone.utc)
EPOCH0_GPS = datetime(1980, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
EPOCH0_IRN = datetime(1999, 8, 22, 0, 0, 0, tzinfo=timezone.utc)
EPOCHMAX = datetime(9999, 12, 31, tzinfo=timezone.utc)
EPOCHMIN = datetime(1900, 1, 1, tzinfo=timezone.utc)
GAL = "E"
GLO = "R"
GPS = "G"
IRN = "I"
LEAPS0 = datetime(1900, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
MIX = "M"
MET = "M"
MINOBS = 0
NAV = "N"
OBS = "O"
PYRINEXCONV_VERSION = "0.1.0 Alpha"
QZS = "J"
RINEX_CANCELLED = 2
RINEX_ERROR = 99
RINEX_NORECS = 1
RINEX_OK = 0
RINEXVERSIONS = ["3.05", "4.02"]  # only 3.05 supported in Alpha release
RINEXVER_DEFAULT = RINEXVERSIONS[0]
SBA = "S"
TIME_BEIDOU = "BDT"
TIME_GPS = "GPS"
TIME_UNDEFINED = "00U"

ALLGNSS = [GPS, GLO, GAL, BDS, SBA, QZS, IRN]
"""All Available GNSS Codes."""
ALLOBS = [OBS, NAV, MET]
"""All Available Observation Codes."""
RINEXTYPE = {OBS: "observation", NAV: "navigation", MET: "meteorology"}
"""RINEX File Types."""

# scaling factors
P2_N5 = 0.03125  # 2**-5
P2_N19 = 1.9073486328125e-06  # 2**-19
P2_N24 = 5.960464477539063e-08  # 2**-24
P2_N27 = 7.450580596923828e-09  # 2**-27
P2_N29 = 1.862645149230957e-09  # 2**-29
P2_N30 = 9.313225746154785e-10  # 2**-30
P2_N31 = 4.656612873077393e-10  # 2**-31
P2_N33 = 1.1641532182693481e-10  # 2**-33
P2_N43 = 1.1368683772161603e-13  # 2**-43
P2_N50 = 8.881784197001252e-16  # 2**-50
P2_N55 = 2.7755575615628914e-17  # 2**-55
P2_P4 = 16  # 2**4
P2_P11 = 2048  # 2**11
P2_P12 = 4096  # 2**12
P2_P14 = 16384  # 2**14
P2_P16 = 65536  # 2**16

RINEXGNSSR = {
    GPS: "GPS",
    SBA: "SBAS",
    GAL: "GALILEO",
    BDS: "BEIDOU",
    "N": "N/A",
    QZS: "QZSS",
    GLO: "GLONASS",
    IRN: "IRNSS/NAVIC",
    MIX: "MIXED",
}
"""RINEX GNSS Codes."""

RINEXOBSPREFIX = {
    BDS: "Pseudo Range",
    "L": "Carrier Phase",
    "D": "Doppler Shift",
    "S": "Signal Strength",
}
"""RINEX Observation Code Prefixes."""

GNSS_FREQUENCIES = {
    "B1": 1561.098,
    "B1A": 1575.42,
    "B1C": 1575.42,
    "B2 (BDS-2)": 1207.140,
    "B2a": 1176.45,
    "B2a+B2b (BDS-3)": 1191.795,
    "B2b (BDS-3)": 1207.140,
    "B3": 1268.52,
    "B3A (BDS-3)": 1268.52,
    "E1": 1575.42,
    "E5(A+B)": 1191.795,
    "E5A": 1176.45,
    "E5B": 1207.140,
    "E6": 1278.75,
    "G1": 1602,  # + k*9/16,
    "G1a": 1600.995,
    "G2": 1246,  #  + k*7/16,
    "G2a": 1248.06,
    "G3": 1202.025,
    "L1": 1575.42,
    "L2": 1227.60,
    "L5": 1176.45,
    "L5S": 1176.45,
    "L6": 1278.75,
    "S": 2492.028,
}
"""
GNSS Signal Code -> Frequency Lookup.

- key is RINEX Frequency Band
- value is Frequency in kHz
"""

EVENT_TYPE = {
    0: "observation",
    1: "observation",
    2: "new site occupation",
    3: "site move event",
    4: "header records follow",
    5: "external event",
    6: "cycle slip",
}
"""RINEX Epoch Flag Description Lookup"""

UBXRINEXGNSS = {
    0: GPS,  # GPS
    1: SBA,  # SBAS
    2: GAL,  # GAL
    3: BDS,  # BDS
    # 4: "N",  # N/A
    5: QZS,  # QZSS
    6: GLO,  # GLO
    7: IRN,  # NavIC
}
"""
UBX GNSS code -> RINEX GNSS Code Lookup.

- key is msg.gnss where msg = UBX-RXM-RAWX
- value is RINEX GNSS code ('GNSSR')
"""

UBXRINEXOBSCODE = {
    (0, 0): "1C",  # L1_C/A",
    (0, 3): "2L",  # "L2_CL",
    (0, 4): "2S",  # "L2_CM",
    (0, 6): "5I",  # "L5_I",
    (0, 7): "5Q",  # "L5_Q",
    (1, 0): "1C",  # "L1_C/A",
    (2, 0): "1C",  # "E1_C",
    (2, 1): "1B",  # "E1_B",
    (2, 3): "5I",  # "E5_aI",
    (2, 4): "5Q",  # "E5_aQ",
    (2, 5): "7I",  # "E5_bI",
    (2, 6): "7Q",  # "E5_bQ",
    (2, 8): "6B",  # "E6_B",
    (2, 9): "6C",  # "E6_C",
    (3, 0): "2I",  # "B1I_D1",
    (3, 1): "1C",  # "B1I_D2",
    (3, 2): "1C",  # "B2I_D1",
    (3, 3): "2C",  # "B2I_D2",
    (3, 4): "6C",  # "B3I_D1",
    (3, 5): "1P",  # "B1_Cp",
    (3, 6): "1D",  # "B1_Cd",
    (3, 7): "5P",  # "B2_ap",
    (3, 8): "5D",  # "B2_ad",
    (3, 10): "6I",  # "B3I_D2",
    (5, 0): "1C",  # "L1_C/A",
    (5, 1): "1Z",  # "L1_S",
    (5, 4): "2S",  # "L2_CM",
    (5, 5): "2L",  # "L2_CL",
    (5, 8): "5I",  # "L5_I",
    (5, 9): "5Q",  # "L5_Q",
    (5, 12): "1B",  # "L1_CB",
    (6, 0): "1C",  # "L1_OF",
    (6, 2): "2C",  # "L2_OF",
    (7, 0): "5A",  # "L5_A",
}
"""
UBX Signal ID -> RINEX Observation Code Lookup. TODO CHECK THIS MAPPING!!!

- key is (msg.gnss, msg.sigId) where msg = UBX-RXM-RAWX
- value is RINEX Observation Code, minus prefix (see RINEXOBSPREFIX for appropriate prefix)
"""

RINEX_PHASE_ALIGNMENT = {
    (GPS, "L1C"): ("L1", "C/A", "REF"),
    (GPS, "L1S"): ("L1", "L1C-D", " L1C"),
    (GPS, "L1L"): ("L1", "L1C-P", " L1C"),
    (GPS, "L1X"): ("L1", "L1C-(D+P)", " L1C"),
    (GPS, "L1P"): ("L1", "P", " L1C"),
    (GPS, "L1W"): ("L1", "Z-tracking", " L1C"),
    (GPS, "L1N"): ("L1", "Codeless", " L1C"),
    (GPS, "L1R"): ("L1", "M (RMP)", "Restricted"),
    (GPS, "L2C"): (
        "L2",
        "C/A",
        "None/L2P",
    ),  # For Block II/IIA/IIR, None, For Block IIR-M/IIF/III,  L2P
    (GPS, "L2D"): ("L2", "Semi-codeless", "None"),
    (GPS, "L2S"): ("L2", "L2C(M)", " L2P"),
    (GPS, "L2L"): ("L2", "L2C(L)", " L2P"),
    (GPS, "L2X"): ("L2", "L2C(M+L)", " L2P"),
    (GPS, "L2P"): ("L2", "P", "REF"),
    (GPS, "L2W"): ("L2", "Z-tracking", "None"),
    (GPS, "L2N"): ("L2", "Codeless", "None"),
    (GPS, "L1R"): ("L2", "M (RMP)", "Restricted"),
    (GPS, "L5I"): ("L5", "I", "REF"),
    (GPS, "L5Q"): ("L5", "Q", " L5I"),
    (GPS, "L5X"): ("L5", "I+Q", " L5I"),
    (GLO, "L1C"): ("G1", "C/A", "REF"),
    (GLO, "L1P"): ("G1", "P", " L1C"),
    (GLO, "L4A"): ("G1a", "L1OCd", "REF"),
    (GLO, "L4B"): ("G1a", "L1OCp", "None"),
    (GLO, "L4X"): ("G1a", "L1OCd+ L1OCd", "None"),
    (GLO, "L2C"): ("G2", "C/A", "REF"),
    (GLO, "L2P"): ("G2", "P", " L2C"),
    (GLO, "L6A"): ("G2a", "L2CSI", "REF"),
    (GLO, "L6B"): ("G2a", "L2OCp", "None"),
    (GLO, "L6X"): ("G2a", "L2CSI+ L2OCp", "None"),
    (GLO, "L3I"): ("G3", "I", "REF"),
    (GLO, "L3Q"): ("G3", "Q", " L3I"),
    (GLO, "L3X"): ("G3", "I+Q", " L3I"),
    (GAL, "L1B"): ("E1", "B I/NAV OS/CS/SoL", "REF"),
    (GAL, "L1C"): ("E1", "C no data", " L1B"),
    (GAL, "L1X"): ("E1", "B+C", " L1B"),
    (GAL, "L5I"): ("E5A", "I", "REF"),
    (GAL, "L5Q"): ("E5A", "Q", " L5I"),
    (GAL, "L5X"): ("E5A", "I+Q", " L5I"),
    (GAL, "L7I"): ("E5B", "I", "REF"),
    (GAL, "L7Q"): ("E5B", "Q", " L7I"),
    (GAL, "L7X"): ("E5B", "I+Q", " L7I"),
    (GAL, "L8I"): ("E5(A+B)", "I", "REF"),
    (GAL, "L8Q"): ("E5(A+B)", "Q", " L8I"),
    (GAL, "L8X"): ("E5(A+B)", "I+Q", " L8I"),
    (GAL, "L6B"): ("E6", "B", "REF"),
    (GAL, "L6C"): ("E6", "C", " L6B"),
    (GAL, "L6X"): ("E6", "B+C", " L6B"),
    (QZS, "L1C"): ("L1", "C/A", "REF"),
    (QZS, "L1E"): ("L1", "C/B", "REF"),
    (QZS, "L1S"): ("L1", "L1C (D)", " L1C/L1E"),
    (QZS, "L1L"): ("L1", "L1C (P)", " L1C/L1E"),
    (QZS, "L1X"): ("L1", "L1C-(D+P)", " L1C/L1E"),
    (QZS, "L1Z"): ("L1", "L1S", "N/A"),
    (QZS, "L1B"): ("L1", "L1Sb", "N/A"),
    (QZS, "L2S"): ("L2", "L2C (M)", "REF"),
    (QZS, "L2L"): ("L2", "L2C (L)", " L2S"),
    (QZS, "L2X"): ("L2", "L2C (M+L)", " L2S"),
    (QZS, "L5I"): ("L5", "I", "REF"),
    (QZS, "L5Q"): ("L5", "Q", " L5I"),
    (QZS, "L5X"): ("L5", "I+Q", " L5I"),
    (QZS, "L5D"): ("L5S", "I", "REF"),
    (QZS, "L5P"): ("L5S", "Q", " L5D"),
    (QZS, "L5Z"): ("L5S", "I+Q", " L5D"),
    (QZS, "L6S"): ("L6", "L6D", "REF"),
    (QZS, "L6L"): ("L6", "L6P", "None"),
    (QZS, "L6X"): ("L6", "L6(D+P)", "None"),
    (QZS, "L6E"): ("L6", "L6E", "None"),
    (QZS, "L6Z"): ("L6", "L6(D+E)", "None"),
    (BDS, "L2I"): ("B1", "I", "REF"),
    (BDS, "L2Q"): ("B1", "Q", " L2I"),
    (BDS, "L2X"): ("B1", "I+Q", " L2I"),
    (BDS, "L1D"): ("B1C", "Data (D)", "REF"),
    (BDS, "L1P"): ("B1C", "Pilot(P)", " L1D"),
    (BDS, "L1X"): ("B1C", "D+P", " L1D"),
    (BDS, "L1S"): ("B1A", "Data (D)", "REF"),
    (BDS, "L1L"): ("B1A", "Pilot(P)", " L1S"),
    (BDS, "L1Z"): ("B1A", "D+P", " L1S"),
    (BDS, "L5D"): ("B2a", "Data (D)", "REF"),
    (BDS, "L5P"): ("B2a", "Pilot(P)", " L5D"),
    (BDS, "L5X"): ("B2a", "D+P", " L5D"),
    (BDS, "L7I"): ("B2 (BDS-2)", "I", "REF"),
    (BDS, "L7Q"): ("B2 (BDS-2)", "Q", " L7I"),
    (BDS, "L7X"): ("B2 (BDS-2)", "I+Q", " L7I"),
    (BDS, "L7D"): ("B2b (BDS-3)", "Data (D)", "REF"),
    (BDS, "L7P"): ("B2b (BDS-3)", "Pilot(P)", " L7D"),
    (BDS, "L7Z"): ("B2b (BDS-3)", "D+P", " L7D"),
    (BDS, "L8D"): ("B2a+B2b (BDS-3)", "Data (D)", "REF"),
    (BDS, "L8P"): ("B2a+B2b (BDS-3)", "Pilot(P)", " L8D"),
    (BDS, "L8X"): ("B2a+B2b (BDS-3)", "D+P", " L8D"),
    (BDS, "L6I"): ("B3", "I", "REF"),
    (BDS, "L6Q"): ("B3", "Q", " L6I"),
    (BDS, "L6X"): ("B3", "I+Q", " L6I"),
    (BDS, "L6D"): ("B3A (BDS-3)", "Data (D)", "REF"),
    (BDS, "L6P"): ("B3A (BDS-3)", "Pilot (P)", " L6D"),
    (BDS, "L6Z"): ("B3A (BDS-3)", "D+P", " L6D"),
    (IRN, "L1D"): ("L1", "D", "REF"),
    (IRN, "L1P"): ("L1", "P", " L1D"),
    (IRN, "L1X"): ("L1", "D+P", " L1D"),
    (IRN, "L5A"): ("L5", "A SPS", "REF"),
    (IRN, "L5B"): ("L5", "B RS(D)", "Restricted"),
    (IRN, "L5C"): ("L5", "C RS(P)", "None"),
    (IRN, "L5X"): ("L5", "B+C", " L5A"),
    (IRN, "L9A"): ("S", "A SPS", "REF"),
    (IRN, "L9B"): ("S", "B RS(D)", "Restricted"),
    (IRN, "L9C"): ("S", "C RS(P)", "None"),
    (IRN, "L9X"): ("S", "B+C", " L9A"),
}
"""
RINEX GNSS Code/Observation Code -> Signal and Phase Alignment Lookup.

- key is (RINEX GNSS Code, RINEX Carrier Phase Observation Code)
- value is (Frequency Band, Signal, Phase Alignment Frequency Band)
"""

RINEX_METOBS = {
    "PR": "Pressure (mbar)",
    "TD": "Dry temperature (deg Celsius)",
    "HR": "Relative humidity (percent)",
    "ZW": "Wet zenith path delay (mm), (for WVR data)",
    "ZD": "Dry component of zen.path delay (mm)",
    "ZT": "Total zenith path delay (mm)",
    "WD": "Wind azimuth (deg) from where the wind blows",
    "WS": "Wind speed (m/s)",
    "RI": "Rain increment (1/10 mm): Rain accumulation since last measurement",
    "HI": "Hail indicator non-zero: Hail detected since last measurement",
}
"""RINEX Meteorology Observation Codes."""
