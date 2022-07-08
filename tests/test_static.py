"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import os
import unittest

from pyubx2 import (
    UBXMessage,
    UBXReader,
    SET,
    NMEA_PROTOCOL,
    UBX_PROTOCOL,
    RTCM3_PROTOCOL,
    protocol,
    dop2str,
    itow2utc,
    hextable,
)
from pygnssutils.helpers import (
    haversine,
    cel2cart,
    deg2dmm,
    deg2dms,
    latlon2dms,
    latlon2dmm,
    format_json,
    get_mp_distance,
    find_mp_distance,
)
from tests.test_sourcetable import TESTSRT


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        # dirname = os.path.dirname(__file__)
        # self.streamNAV = open(os.path.join(dirname, "pygpsdata-NAV.log"), "rb")

    def tearDown(self):
        # self.streamNAV.close()
        pass

    def testhaversine(self):
        res = haversine(51.23, -2.41, 34.205, 56.34)
        self.assertAlmostEqual(res, 5005.114961720793, 4)
        res = haversine(-12.645, 34.867, 145.1745, -56.27846)
        self.assertAlmostEqual(res, 10703.380604004034, 4)

    def testcel2cart(self):
        (elev, azim) = cel2cart(34, 128)
        self.assertAlmostEqual(elev, -0.510406, 5)
        self.assertAlmostEqual(azim, 0.653290, 5)
        (elev, azim) = cel2cart("xxx", 128)
        self.assertEqual(elev, 0)

    def testdeg2dms(self):
        res = deg2dms(53.346, "lat")
        self.assertEqual(res, ("53°20′45.6″N"))
        res = deg2dms("xxx", "lat")
        self.assertEqual(res, "")

    def testdeg2dmm(self):
        res = deg2dmm(-2.5463, "lon")
        self.assertEqual(res, ("2°32.778′W"))
        res = deg2dmm("xxx", "lon")
        self.assertEqual(res, "")

    def testlatlon2dms(self):
        res = latlon2dms((53.346, -2.5463))
        self.assertEqual(res, ("53°20′45.6″N", "2°32′46.68″W"))

    def testlatlon2dmm(self):
        res = latlon2dmm((53.346, -2.5463))
        self.assertEqual(res, ("53°20.76′N", "2°32.778′W"))

    def testlatlon2dmm(self):
        res = latlon2dmm((53.346, -2.5463))
        self.assertEqual(res, ("53°20.76′N", "2°32.778′W"))

    def testitow2utc(self):
        res = str(itow2utc(387092000))
        self.assertEqual(res, "11:31:14")

    def testformatjson1(self):
        cls = "<class 'pyubx2.ubxmessage.UBXMessage'>"
        json = (
            '{"class": "'
            + cls
            + '", "identity": "NAV-STATUS", "payload": {"iTOW": "11:46:18", "gpsFix": 3, "gpsFixOk": 1, "diffSoln": 0, "wknSet": 1, "towSet": 1, "diffCorr": 0, "carrSolnValid": 0, "mapMatching": 0, "psmState": 0, "spoofDetState": 0, "carrSoln": 0, "ttff": 15434, "msss": 255434}}'
        )
        msg = UBXReader.parse(
            b"\xb5\x62\x01\x03\x10\x00\x60\x45\xad\x07\x03\xdd\x00\x00\x4a\x3c\x00\x00\xca\xe5\x03\x00\x85\xbd"
        )  # NAV-STATUS
        res = format_json(msg)
        self.assertEqual(res, json)

    def testformatjson2(self):
        class Dummy:
            def __init__(self):

                self.bogoff = False
                self.bangon = True

            @property
            def identity(self):

                return "dummy"

        cls = "<class 'test_static.StaticTest.testformatjson2.<locals>"
        json = (
            '{"class": "'
            + cls
            + '", "identity": "dummy", "payload": {"bogoff": false, "bangon": true}}'
        )
        msg = Dummy()
        res = format_json(msg)
        self.assertEqual(res[-70:], json[-70:])

    def testfindmpdist1(self):  # no name, find closest
        lat = 54.8
        lon = -7.4
        name = ""
        res = find_mp_distance(lat, lon, TESTSRT, name)
        self.assertEqual(res, ("ballymagorry85", 6.94))

    def testfindmpdist2(self):  # name, find distance
        lat = 53.0
        lon = -2.24
        name = "apinhal"
        res = find_mp_distance(lat, lon, TESTSRT, name)
        self.assertEqual(res, ("apinhal", 1412.37))

    def testfindmpdist3(self):  # no coords available
        lat = 53
        lon = -2.24
        name = "AUADL"
        res = find_mp_distance(lat, lon, TESTSRT, name)
        self.assertEqual(res, (None, 9999999))

    def testfindmpdist4(self):  # invalid coords
        name = "apinhal"
        lat = ""
        lon = ""
        res = find_mp_distance(lat, lon, TESTSRT, name)
        self.assertEqual(res, (None, 9999999))

    def testgetmpdist1(self):  # valid
        mp = TESTSRT[12]
        lat = 54.8
        lon = -7.4
        res = get_mp_distance(lat, lon, mp)
        self.assertAlmostEqual(res, 6214.2395, 4)

    def testgetmpdist2(self):  # mp has no coords
        mp = TESTSRT[27]
        lat = 53
        lon = -2.24
        res = get_mp_distance(lat, lon, mp)
        self.assertEqual(res, None)

    def testgetmpdist3(self):  # invalid coords
        mp = TESTSRT[12]
        lat = ""
        lon = ""
        res = get_mp_distance(lat, lon, mp)
        self.assertEqual(res, None)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
