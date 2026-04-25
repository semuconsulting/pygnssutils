"""
process_rxmsfrbx_frames.py

Demo script to illustrate acquisition and collation of
raw NAV subframes from a UBX RXM-SFRBX data log using
the pygnssutils.RawNav utility class.

This collates the following subframes for each SV4
into a single RawNav object.

 - subframe 1: clock corrections, sv health, etc.
 - subframes 2 & 3: ephemerides
 - subframe 4 page 18: (optional) ionospheric and time corrections

(NB: subframe data dictionaries only currently defined
for GPS LNAV, but others can be added)

python3 process_rxmsfrbx_frames.py infile=pygpsdata-rxmsfrbx.log

Created on 21 Apr 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable=no-member

from sys import argv

from pyubx2 import UBXMessage

from pygnssutils import GPS, GNSSReader, RawNav, RINEXProcessingError
from pygnssutils.rinex_subframes_gps import (
    GPS_LNAV_SUBFRAME_1,
    GPS_LNAV_SUBFRAME_2,
    GPS_LNAV_SUBFRAME_3,
    GPS_LNAV_SUBFRAME_4_P18,
)

SFR1 = 1
SFR2 = 2
SFR3 = 4
SFR4 = 8
TARGET_SFR = SFR1 | SFR2 | SFR3 # | SFR4


def main(**kwargs):
    """
    Main routine.
    """

    infile = kwargs["infile"]

    tot = 0
    sfr = 0
    err = 0
    lnavs = {}
    navs = {}
    with open(infile, "rb") as stream:
        gnr = GNSSReader(stream)
        for _, parsed in gnr:
            if not isinstance(parsed, UBXMessage):
                continue
            if parsed.identity != "RXM-SFRBX":  # UBX RXM-SFRBX (raw subframes) only
                continue
            tot += 1
            
            sfrdata = RawNav.process_rxm_sfrbx(parsed)
            if sfrdata.get("gnss", "") != GPS or sfrdata.get("sigid", "") not in ("1C",):
                continue

            gnss = sfrdata["gnss"]
            svid = sfrdata["svid"]
            sigid = sfrdata["sigid"]
            subframeid = sfrdata["subframeid"]
            svcode = sfrdata.get("svcode", 0)
            subframe = sfrdata["subframe"]
            
            try:
                navs[(gnss, svid, sigid)] = navs.get(
                    (gnss, svid, sigid), RawNav(gnss, svid, sigid)
                )
                nav = navs[(gnss, svid, sigid)]
                if subframeid == 1:  # clock parameters, sv health, etc.
                    wn = subframe >> 230 & 0b1111111111
                    toc = (subframe >> 66 & 0b1111111111111111) * 16
                    tow = subframe >> 253 & 0b11111111111111111
                    print(f"{tow=}, {wn=}, {toc=}")
                    nav.parse(subframe, GPS_LNAV_SUBFRAME_1)
                elif subframeid == 2:  # ephemerides
                    nav.parse(subframe, GPS_LNAV_SUBFRAME_2)
                elif subframeid == 3:  # ephemerides
                    nav.parse(subframe, GPS_LNAV_SUBFRAME_3)
                elif subframeid == 4:
                    if svcode == 56:  # page 18, ionospheric corrections
                        nav.parse(subframe, GPS_LNAV_SUBFRAME_4_P18)
                if nav.sfracq & 0b111 == TARGET_SFR:
                    frame = navs.pop((gnss, svid, sigid))
                    # print(f"{str(frame)}\n")
                    lnavs[svid] = lnavs.get(svid, 0) + 1
                sfr += 1
            except RINEXProcessingError:
                err += 1

    if tot:
        print(
            f"Total RXM-SFRBX records: {tot}, errors: {err} ({err*100/tot:.0f}%)"
        )
        print(f"Total GPS LNAV subrames processed: {sfr}")
        print(
            (
                f"Total GPS LNAV full frames acquired (sfracq={TARGET_SFR}): "
                f"{sum(lnavs.values())}"
            )
        )
        print(
            (
                f"Breakdown of GPS LNAV frames by SV: {sorted(lnavs.items())}   "
                f"Sum: {sum(lnavs.values())}"
            )
        )
    else:
        print("No RXM-SFRBX records in file")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
