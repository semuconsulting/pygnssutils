"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

from os import path
from pathlib import Path
import unittest
from socket import AF_INET, AF_INET6
from pyubx2 import UBXReader, itow2utc

from pygnssutils.exceptions import ParameterError
from pygnssutils.helpers import (
    cel2cart,
    find_mp_distance,
    format_conn,
    ipprot2int,
    ipprot2str,
    format_json,
    get_mp_distance,
    parse_config,
    parse_url,
)
from pygnssutils.mqttmessage import MQTTMessage
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
            '{"type": "'
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
            '{"type": "'
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
        # res = format_conn(AF_INET6, "fe80::5f:89a3:300f:2dfa%en0", 50010)
        # self.assertEqual(res, ("fe80::5f:89a3:300f:2dfa", 50010, 0, 15))
        res = format_conn(AF_INET6, "fe80::5f:89a3:300f:2dfa", 50010)
        self.assertEqual(res, ("fe80::5f:89a3:300f:2dfa", 50010, 0, 0))
        res = format_conn(AF_INET6, "fe80::5f:89a3:300f:2dfa%en0", 50010, 3456, 12)
        self.assertEqual(res, ("fe80::5f:89a3:300f:2dfa%en0", 50010, 3456, 12))

    def testformatconnerr(self):  # test format connection string
        with self.assertRaisesRegex(ValueError, "Invalid family value 99"):
            format_conn(99, "192.168.0.23", 50010)

    def testformatconnerr2(self):  # test invalid IP6 address
        with self.assertRaises(ValueError):
            format_conn(AF_INET6, "fe80$$5f$89a3%300f&2dfa%xx54", 50010)

    def testipprot2int(self):  # test IP family to int
        self.assertEqual(AF_INET, ipprot2int("IPv4"))
        self.assertEqual(AF_INET6, ipprot2int("IPv6"))

    def testipprot2str(self):  # test IP family to str
        self.assertEqual("IPv4", ipprot2str(AF_INET))
        self.assertEqual("IPv6", ipprot2str(AF_INET6))

    def testparsemqttfreq(self):  # test MQTTMessage constructor
        topic = "/pp/frequencies/Lb"
        payload = b'{\n  "frequencies": {\n    "us": {\n      "current": {\n        "value": "1556.29"\n      }\n    },\n    "eu": {\n      "current": {\n        "value": "1545.26"\n      }\n    }\n  }\n}'
        parsed = MQTTMessage(topic, payload=payload)
        self.assertEqual(
            str(parsed),
            "<MQTT(/PP/FREQUENCIES/LB, frequencies_us_current_value=1556.29, frequencies_eu_current_value=1545.26)>",
        )
        payload2 = b'{\n  "frequencies": {\n    "us": {\n      "current": {\n        "value": {"msb": "1556.29", "lsb": "0.645"}\n      }\n    },\n    "eu": {\n      "current": {\n        "value": "1545.26"\n      }\n    },\n    "jp": {\n      "current": {\n        "value": "1548.23"\n      }\n    }\n}\n}'
        parsed = MQTTMessage(topic, payload=payload2)
        self.assertEqual(
            str(parsed),
            "<MQTT(/PP/FREQUENCIES/LB, frequencies_us_current_value_msb=1556.29, frequencies_us_current_value_lsb=0.645, frequencies_eu_current_value=1545.26, frequencies_jp_current_value=1548.23)>",
        )
        with self.assertRaises(ValueError):
            MQTTMessage(topic, payload=b"arsebiscuits")

    def testparseconfig(self):
        EXPECTED_RESULT = {
            "filename": "pygpsdata-MIXED3.log",
            "verbosity": "3",
            "format": "2",
            "clioutput": "1",
            "output": "testfile.bin",
        }
        cfg = parse_config(path.join(path.dirname(__file__), "gnssstreamer.conf"))
        self.assertEqual(cfg, EXPECTED_RESULT)

    def testparseurl(self):
        EXPECTED_RESULT = ("https", "rtk2go.com", 2102, "mountpoint")
        URL = "https://rtk2go.com:2102/mountpoint"
        res = parse_url(URL)
        self.assertEqual(res, EXPECTED_RESULT)
        EXPECTED_RESULT = ("http", "example.com", 80, "path1/path2.html")
        URL = "example.com/path1/path2.html"
        res = parse_url(URL)
        self.assertEqual(res, EXPECTED_RESULT)
        EXPECTED_RESULT = ("http", "example.com", 80, "path1/path2.html")
        URL = "lkjashdflk:ashj\dgfa"
        with self.assertRaises(ParameterError):
            res = parse_url(URL)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
