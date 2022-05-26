"""
Helper, Property and Static method tests for pygnssutils.UBXMessage

Created on 3 Oct 2020

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import os
import unittest

from pygnssutils.globals import NMEA_PROTOCOL, UBX_PROTOCOL, RTCM3_PROTOCOL
from pygnssutils.helpers import (
    protocol,
    hextable,
    dop2str,
    haversine,
    deg2dmm,
    deg2dms,
)


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        dirname = os.path.dirname(__file__)
        self.streamNAV = open(os.path.join(dirname, "pygpsdata-NAV.log"), "rb")

    def tearDown(self):
        self.streamNAV.close()

    def testdop2str(self):
        dops = ["Ideal", "Excellent", "Good", "Moderate", "Fair", "Poor"]
        i = 0
        for dop in (1, 2, 5, 10, 20, 30):
            res = dop2str(dop)
            self.assertEqual(res, dops[i])
            i += 1

    def testprotocol(self):  # test protocol() method
        res = protocol(b"\xb5b\x06\x01\x02\x00\xf0\x05\xfe\x16")
        self.assertEqual(res, UBX_PROTOCOL)
        res = protocol(b"$GNGLL,5327.04319,S,00214.41396,E,223232.00,A,A*68\r\n")
        self.assertEqual(res, NMEA_PROTOCOL)
        res = protocol(b"$PGRMM,WGS84*26\r\n")
        self.assertEqual(res, NMEA_PROTOCOL)
        res = protocol(b"\xd3\x00\x04L\xe0\x00\x80\xed\xed\xd6")
        self.assertEqual(res, RTCM3_PROTOCOL)
        res = protocol(b"aPiLeOfGarBage")
        self.assertEqual(res, 0)

    def testhextable(self):  # test hextable*( method)
        EXPECTED_RESULT = "000: 2447 4e47 4c4c 2c35 3332 372e 3034 3331  | b'$GNGLL,5327.0431' |\n016: 392c 532c 3030 3231 342e 3431 3339 362c  | b'9,S,00214.41396,' |\n032: 452c 3232 3332 3332 2e30 302c 412c 412a  | b'E,223232.00,A,A*' |\n048: 3638 0d0a                                | b'68\\r\\n' |\n"
        res = hextable(b"$GNGLL,5327.04319,S,00214.41396,E,223232.00,A,A*68\r\n", 8)
        self.assertEqual(res, EXPECTED_RESULT)

    def testhaversine(self):
        res = haversine(51.23, -2.41, 34.205, 56.34)
        self.assertAlmostEqual(res, 5005.114961720793, 4)
        res = haversine(-12.645, 34.867, 145.1745, -56.27846)
        self.assertAlmostEqual(res, 10703.380604004034, 4)

    def testdeg2dms(self):
        res = deg2dms(53.346, "lat")
        self.assertEqual(res, ("53°20′45.6″N"))

    def testdeg2dmm(self):
        res = deg2dmm(-2.5463, "lon")
        self.assertEqual(res, ("2°32.778′W"))

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
