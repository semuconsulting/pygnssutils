"""
Helper, Property and Static method tests for RawNav class.

Created on 18 Apr May 2026

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

import unittest

from datetime import datetime, timezone
from pygnssutils.exceptions import RINEXProcessingError
from pygnssutils.rawnav import RawNav, PREAMBLE, VALPREAMBLE, U, S
from pygnssutils.rinex_subframes_gps import (
    GPS_LNAV_SUBFRAME_1,
    GPS_LNAV_SUBFRAME_3,
    GPS_LNAV_SUBFRAME_2,
)

SUBFRAME1 = {
            VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
            PREAMBLE: (0, 8, U, 0),
            "test": (8, 8, U, 0),
            "tlm_msb": (8, 6, U, 0),
            "integrity": (22, 1, U, 0),
            "_reserved1": (23, 1, U, 0),
            "_parity1": (24, 6, U, 0),
        }
SUBFRAME2 = {
            VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
            PREAMBLE: (0, 8, U, 0),
            "tlm_lsb": (8, 14, U, 0),
            "antispoof": (22, 1, U, 0),
            "_reserved1": (23, 1, U, 0),
            "_parity1": (24, 6, U, 0),
        }
SUBFRAME3 = {
            VALPREAMBLE: 0b10001011,  # optional, used to validate preamble value
            PREAMBLE: (0, 8, U, 0),
            "omegadot": (8, 7, S, 2e-23),
            "m0": (22, 8, S, 2e-8),
            "_reserved1": (23, 1, U, 0),
            "_parity1": (24, 6, U, 0),
        }

class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def testconstructor(self):
        EXPECTED_RESULTS = [
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, tlm=16022, integrity=1, tow=77101, alert=0, antispoof=0, subframeid=5, wn=662, ca=2, ura=5, svhealth=41, l2pdata=0, tgd=-1.8200000000000002e-29, iodc=361, toc=539700000.0, af2=1.8e-53, af1=4.626e-39, af0=-3.454134e-25)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, tlm=16022, integrity=1, tow=77101, alert=0, antispoof=0, subframeid=5, iode=165, crs=-0.46262000000000003, deltan=5.3970000000000005e-39, m0=3.5350581000000003e-22, cuc=-5.3972e-25, e=5.05487649e-24, cus=5.396999999999999e-25, sqrta=3.5350581e-10, toe=-539720000.0, fit=1, aodo=5)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, tlm=16022, integrity=1, tow=77101, alert=0, antispoof=0, subframeid=5, cic=-4.626199999999999e-25, omega0=-3.0396367820000005e-22, cis=4.626e-25, i0=3.0396367800000003e-22, crc=-0.46262000000000003, omega=-3.0396367820000005e-22, omegadot=1.1842740000000002e-36, iode=150, idot=-1.3494e-39)>",
        ]
        for i, sfr in enumerate(
            (GPS_LNAV_SUBFRAME_1, GPS_LNAV_SUBFRAME_2, GPS_LNAV_SUBFRAME_3)
        ):
            raw = RawNav(
                "G",
                32,
                "1C",
                epoch=datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc),
            )
            data = int("10001011" + "1111" + "10100101" * 36, 2)
            raw.parse(data, sfr, sequence=False)
            print(f'"{raw}",')
            #self.assertEqual(str(raw), EXPECTED_RESULTS[i])
            #self.assertEqual((raw.gnss, raw.svid, raw.sigid, raw.epoch),("G",32,"1C",datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc)))

    def testsequence(self):
        EXPECTED_RESULTS = [
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1, tlm=699050, antispoof=1)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1, tlm=699050, antispoof=1, omegadot=-8.599999999999999e-22, m0=-1.72e-06)>",
        ]
        raw = RawNav(
            "G", 32, "1C", epoch=datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc)
        )
        for i, sfr in enumerate((SUBFRAME1, SUBFRAME2, SUBFRAME3)):
            data = int("10001011" + "1010101010101010101010", 2)
            raw.parse(data, sfr, sequence=True)
            print(f'"{raw}",')
            # self.assertEqual(str(raw), EXPECTED_RESULTS[i])

    def testnosequence(self):
        EXPECTED_RESULTS = [
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1, tlm_msb=42)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1, tlm_msb=42, tlm_lsb=10922, antispoof=1)>",
            "<RAWNAV(G321C, gnss=G, svid=32, sigid=1C, epoch=2026-04-18-09:42:13.000000+0000, preamble=139, test=170, integrity=1, tlm_msb=42, tlm_lsb=10922, antispoof=1, omegadot=-8.599999999999999e-22, m0=-1.72e-06)>", 
        ]
        raw = RawNav(
            "G", 32, "1C", epoch=datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc)
        )
        for i, sfr in enumerate((SUBFRAME1, SUBFRAME2, SUBFRAME3)):
            data = int("10001011" + "1010101010101010101010", 2)
            raw.parse(data, sfr, sequence=False)
            print(f'"{raw}",')
            # self.assertEqual(str(raw), EXPECTED_RESULTS[i])

    def testbaddata(self):
        raw = RawNav(
            "G", 32, "1C", epoch=datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc)
        )
        data = int("110001011" + "1111" + "10100101" * 36, 2)
        with self.assertRaisesRegex(
            RINEXProcessingError,
            "Data bit size 301 does not match defined subframe bit size 300",
        ):
            raw.parse(data, GPS_LNAV_SUBFRAME_3)

    # def testbadpreamble(self):
    #     raw = RawNav(
    #         "G", 32, "1C", epoch=datetime(2026, 4, 18, 9, 42, 13, tzinfo=timezone.utc)
    #     )
    #     data = int("10011011" + "1111" + "10100101" * 36, 2)
    #     with self.assertRaisesRegex(
    #         RINEXProcessingError,
    #         "Invalid preamble - expected 0b10001011, got 0b10011011",
    #     ):
    #         raw.parse(data, GPS_LNAVL_SUBFRAME_3)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
