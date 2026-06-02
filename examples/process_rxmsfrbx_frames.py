"""
process_rxmsfrbx_frames.py

Illustration of parsing raw NAV frames from UBX RXM-SFRBX binary
datalog using RawNav utility class and subframe definitions derived
from the relevant GNSS ICD.

Created on 14 May 2026

:author: semuadmin (Steve Smith)
:copyright: semuadmin © 2026
:license: BSD 3-Clause
"""

# pylint: disable = invalid-name

from pygnssutils import GNSSReader
from pygnssutils.rawnav import RawNav, RawNavReader
from pygnssutils.rinex_globals import LNAV, TARGET
from pygnssutils.rinex_subframes_gps import GPS_SUBFRAMEACQ_MAP

INFILE = "pygpsdata-rxmsfrbx.log"

gps = 0
navframes = {}
navstart = {}
rxm = 0
sfrmap = GPS_SUBFRAMEACQ_MAP[LNAV]  # subframe payload definitions
sfrstart = 1  # number of first subframe in frame
subframes = {}

with open(INFILE, "rb") as stream:
    gnr = GNSSReader(stream)
    for raw, parsed in gnr:
        if parsed.identity == "RXM-SFRBX":
            rxm += 1
            if parsed.gnssId == 0 and parsed.sigId in (0,):  # GPS LNAV:
                gps += 1
                # extract the subframe from the RXM-SFRBX message
                rnr = RawNavReader()
                sfrdata = rnr.process_rxm_sfrbx(parsed)
                gnss = sfrdata["gnss"]
                svid = sfrdata["svid"]
                sigid = sfrdata["sigid"]
                sv = (gnss, svid, sigid)
                subframeid = sfrdata["subframeid"]
                subframepageid = sfrdata.get("subframepageid", 0)
                subframe = sfrdata["subframe"]
                sfrdict, sfracq = sfrmap.get((subframeid, subframepageid), (None, 0))
                target = sfrmap[TARGET]

                if subframeid == sfrstart:  # start at first subframe of frame
                    navstart[sv] = True
                if not navstart.get(sv, False) or sfrdict is None:
                    continue

                # instantiate a new RawNav object if one does not already exist
                navframes[sv] = navframes.get(sv, RawNav(gnss, svid, sigid))
                nav = navframes[sv]
                # parse the subframe into its constituent attributes
                nav.parse(subframe, sfrdict, sfracq)
                # when all target subframes have been acquired, print complete frame
                if nav.subframeacq & target == target:
                    print(f"\n{navframes.pop(sv)}")
                    navstart.pop(sv)
                    subframes[sv] = subframes.get(sv, 0) + 1

    print(f"\nTotal records processed - RXM-SFRBX: {rxm:,}, GPS: {gps:,}")
    print("Summary of frames processed:")
    for sv, count in sorted(subframes.items()):
        print(f"{sv}: {count}")
