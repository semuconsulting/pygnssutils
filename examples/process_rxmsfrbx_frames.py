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
from pygnssutils.rawnav import RawNav
from pygnssutils.rawnav_reader import RawNavReader
from pygnssutils.rinex_globals import L1CA, LNAV, CNAV, FNAV, L1OF, INAV, D1, D2, START, TARGET
from pygnssutils.rawnav_subframes_gps import GPS_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_gal import GAL_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_bds import BDS_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_glo import GLO_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_sba import SBA_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_qzs import QZS_SUBFRAMEACQ_MAP
from pygnssutils.rawnav_subframes_irn import IRN_SUBFRAMEACQ_MAP

# INFILE = "pygpsdata-rxmsfrbx.log"
# INFILE = "/Users/steve/Downloads/pygpsdata-20260602101842.log"
INFILE = "/Users/steve/Downloads/pygpsdata-20260611094239.ubx"

gps = 0
navframes = {}
navstart = {}
rxm = 0
# sfrmap = GPS_SUBFRAMEACQ_MAP[LNAV]  # subframe payload definitions
# sfrmap = GPS_SUBFRAMEACQ_MAP[CNAV]  # subframe payload definitions
# sfrmap = GAL_SUBFRAMEACQ_MAP[FNAV]  # subframe payload definitions
# sfrmap = GAL_SUBFRAMEACQ_MAP[INAV]  # subframe payload definitions
# sfrmap = BDS_SUBFRAMEACQ_MAP[D1]  # subframe payload definitions
# sfrmap = BDS_SUBFRAMEACQ_MAP[D2]  # subframe payload definitions
# sfrmap = GLO_SUBFRAMEACQ_MAP[L1OF]  # subframe payload definitions
sfrmap = SBA_SUBFRAMEACQ_MAP[L1CA]  # subframe payload definitions
# sfrmap = QZS_SUBFRAMEACQ_MAP[LNAV]  # subframe payload definitions
# sfrmap = QZS_SUBFRAMEACQ_MAP[CNAV]  # subframe payload definitions
# sfrmap = QZS_SUBFRAMEACQ_MAP[CNV2]  # subframe payload definitions
# sfrmap = IRN_SUBFRAMEACQ_MAP[L1CA]  # subframe payload definitions
subframes = {}

with open(INFILE, "rb") as stream:
    gnr = GNSSReader(stream)
    rnr = RawNavReader()
    for raw, parsed in gnr:
        if parsed is None:
            continue
        if parsed.identity == "RXM-SFRBX":
            rxm += 1
            # if parsed.gnssId == 0 and parsed.sigId in (0,):  # GPS LNAV:
            # if parsed.gnssId == 0 and parsed.sigId in (3,4,6,7,):  # GPS CNAV:
            # if parsed.gnssId == 2 and parsed.sigId in (3,):  # GAL FNAV:
            # if parsed.gnssId == 2 and parsed.sigId in (1,5):  # GAL INAV:
            # if parsed.gnssId == 3 and parsed.sigId in (0,2,4,):  # BDS D1:
            # if parsed.gnssId == 3 and parsed.sigId in (1,3,10,):  # BDS D2:
            # if parsed.gnssId == 6 and parsed.sigId in (0,):  # GLO L1OF:
            if parsed.gnssId == 1 and parsed.sigId in (0,):  # SBA L1CA:
                gps += 1
                # extract the subframe from the RXM-SFRBX message
                sfrdata = rnr.process_rxm_sfrbx(parsed)
                gnss = sfrdata["gnss"]
                svid = sfrdata["svid"]
                sigcode = sfrdata["sigcode"]
                sv = (gnss, svid, sigcode)
                subframeid = sfrdata["subframeid"]
                subframepageid = sfrdata.get("subframepageid", 0)
                subframe = sfrdata["subframe"]
                sfrdict, sfracq = sfrmap.get((subframeid, subframepageid), (None, 0))
                target = sfrmap[TARGET]
                sfrstart = sfrmap[START]

                if subframeid == sfrstart:  # start at first subframe of frame
                    navstart[sv] = True
                if not navstart.get(sv, False) or sfrdict is None:
                    continue

                # instantiate a new RawNav object if one does not already exist
                navframes[sv] = navframes.get(sv, RawNav(gnss, svid, sigcode))
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
