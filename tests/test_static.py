"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import unittest
from socket import AF_INET, AF_INET6
from pyubx2 import UBXReader, itow2utc

from pygnssutils.helpers import (
    cel2cart,
    find_mp_distance,
    format_conn,
    ipprot2int,
    ipprot2str,
    format_json,
    get_mp_distance,
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

    def testcel2cart(self):
        (elev, azim) = cel2cart(34, 128)
        self.assertAlmostEqual(elev, -0.510406, 5)
        self.assertAlmostEqual(azim, 0.653290, 5)
        (elev, azim) = cel2cart("xxx", 128)
        self.assertEqual(elev, 0)

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
        self.assertEqual(res, ("ballymagorry85", 6.95))

    def testfindmpdist2(self):  # name, find distance
        lat = 53.0
        lon = -2.24
        name = "apinhal"
        res = find_mp_distance(lat, lon, TESTSRT, name)
        self.assertEqual(res, ("apinhal", 1413.95))

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
        self.assertAlmostEqual(res, 6221.200922509212, 4)

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

    def testformatconn(self):  # test format connection string
        res = format_conn(AF_INET, "192.168.0.23", 50010)
        self.assertEqual(res, ("192.168.0.23", 50010))
        res = format_conn(AF_INET6, "fe80::5f:89a3:300f:2dfa%en0", 50010)
        self.assertEqual(res, ("fe80::5f:89a3:300f:2dfa%en0", 50010, 0, 0))
        res = format_conn(AF_INET6, "fe80::5f:89a3:300f:2dfa%en0", 50010, 3456, 12)
        self.assertEqual(res, ("fe80::5f:89a3:300f:2dfa%en0", 50010, 3456, 12))

    def testformatconnerr(self):  # test format connection string
        with self.assertRaisesRegex(ValueError, "Invalid family value 99"):
            format_conn(99, "192.168.0.23", 50010)

    def testipprot2int(self):  # test IP family to int
        self.assertEqual(AF_INET, ipprot2int("IPv4"))
        self.assertEqual(AF_INET6, ipprot2int("IPv6"))

    def testipprot2interr(self):  # test IP family to int invalid
        with self.assertRaisesRegex(ValueError, "Invalid family value IPv99"):
            ipprot2int("IPv99")

    def testipprot2str(self):  # test IP family to str
        self.assertEqual("IPv4", ipprot2str(AF_INET))
        self.assertEqual("IPv6", ipprot2str(AF_INET6))

    def testipprot2strerr(self):  # test IP family to str invalid
        with self.assertRaisesRegex(ValueError, "Invalid family value 99"):
            ipprot2str(99)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
