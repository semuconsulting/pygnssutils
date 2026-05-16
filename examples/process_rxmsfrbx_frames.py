"""
process_rxmsfrbx_frames.py

Illustration of parsing raw GPS LNAV and CNAV subframes from
UBX RXM-SFRBX binary datalog using RawNav utility class and
subframe definitions derived from the relevant GPS ICD.

https://www.gps.gov/sites/default/files/2025-07/IS-GPS-200N.pdf

Created on 14 May 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

from pygnssutils import GNSSReader
import pygnssutils.rinex_subframes_gps as rsg

from pygnssutils.rawnav import RawNav

SFRMAP = {
    1: rsg.GPS_LNAV_SUBFRAME_1,
    2: rsg.GPS_LNAV_SUBFRAME_2,
    3: rsg.GPS_LNAV_SUBFRAME_3,
    4: rsg.GPS_LNAV_GENERIC,
    5: rsg.GPS_LNAV_GENERIC,
    10: rsg.GPS_CNAV_SUBFRAME_10,
    11: rsg.GPS_CNAV_SUBFRAME_11,
    12: rsg.GPS_CNAV_SUBFRAME_12,
    13: rsg.GPS_CNAV_SUBFRAME_13,
    14: rsg.GPS_CNAV_SUBFRAME_14,
    15: rsg.GPS_CNAV_SUBFRAME_15,
    30: rsg.GPS_CNAV_SUBFRAME_30,
    31: rsg.GPS_CNAV_SUBFRAME_31,
    32: rsg.GPS_CNAV_SUBFRAME_32,
    33: rsg.GPS_CNAV_SUBFRAME_33,
    34: rsg.GPS_CNAV_SUBFRAME_34,
    35: rsg.GPS_CNAV_SUBFRAME_35,
    36: rsg.GPS_CNAV_SUBFRAME_36,
    37: rsg.GPS_CNAV_SUBFRAME_37,
    40: rsg.GPS_CNAV_SUBFRAME_40,
}

INFILE = "pygpsdata-rxmsfrbx.log"

rxm = 0
gps = 0
subframes = {}
with open(INFILE, "rb") as stream:
    gnr = GNSSReader(stream)
    for raw, parsed in gnr:
        if parsed.identity == "RXM-SFRBX":
            rxm += 1
            if parsed.gnssId == 0:  # GPS
                gps += 1
                output = RawNav.process_rxm_sfrbx(parsed)
                sv = f"{output["gnss"]}{output["svid"]:02d}_{output["sigid"]}"
                subframes[sv] = subframes.get(sv, {})
                msg = RawNav(output["gnss"], output["svid"], output["sigid"])
                msg.parse(output["subframe"], SFRMAP[output["subframeid"]], rsg.GPS_SFRACQ_MAP)
                print(msg)
                subframes[sv][output["subframeid"]] = (
                    subframes[sv].get(output["subframeid"], 0) + 1
                )

    # print summary of subframes captured
    print(f"\nTotal records processed - RXM-SFRBX: {rxm:,}, GPS: {gps:,}")
    print("Summary of subframes processed by PRN/Signal:")
    for key, val in sorted(subframes.items()):
        print(f"{key} {sorted(val.items())}")
