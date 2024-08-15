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

from pygnssutils.helpers import (
    cel2cart,
    find_mp_distance,
    format_conn,
    ipprot2int,
    ipprot2str,
    format_json,
    get_mp_distance,
    parse_config,
    process_MONVER,
    serialize_srt,
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

    def testipprot2interr(self):  # test IP family to int invalid
        with self.assertRaisesRegex(ValueError, "Invalid family value IPv99"):
            ipprot2int("IPv99")

    def testipprot2str(self):  # test IP family to str
        self.assertEqual("IPv4", ipprot2str(AF_INET))
        self.assertEqual("IPv6", ipprot2str(AF_INET6))

    def testipprot2strerr(self):  # test IP family to str invalid
        with self.assertRaisesRegex(ValueError, "Invalid family value 99"):
            ipprot2str(99)

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
        cfg = parse_config(path.join(path.dirname(__file__), "gnssdump.conf"))
        self.assertEqual(cfg, EXPECTED_RESULT)
        with self.assertRaises(FileNotFoundError):
            cfg = parse_config(path.join(path.dirname(__file__), "notexist.conf"))
        with self.assertRaises(ValueError):
            cfg = parse_config(path.join(path.dirname(__file__), "invalid.conf"))

    def testserializeert(self):
        EXPECTED_RESULT = b"ACAKO,Kovin,RTCM 3.2,1005(30),1074(1),1084(1),1094(1),2,GPS+GLO+GAL,SNIP,SRB,44.75,21.01,1,0,sNTRIP,none,B,N,3420,\r\nACASU,Subotica,RTCM 3.2,1005(30),1074(1),1084(1),1094(1),2,GPS+GLO+GAL,SNIP,SRB,46.06,19.52,1,0,sNTRIP,none,B,N,3400,\r\nADS-SAH,Ciudad Real,RTCM 3.2,1005(1),1074(1),1084(1),1094(1),1230(1),,GPS+GLO+GAL,SNIP,ESP,39.05,-4.06,1,0,sNTRIP,none,B,N,0,\r\nAgPartner_1,Zaleszany,RTCM 3.3,1004(1),1005(30),1012(1),1019(3),1033(30),1042(3),1046(2),1077(1),1087(1),1097(1),1107(1),1127(1),1230(30),2,GPS+GLO+GAL+BDS+SBS,SNIP,POL,53.62,17.23,1,0,sNTRIP,none,B,N,11980,\r\nAgPartner_2,Bozewo,RTCM 3.3,1004(1),1005(10),1007(30),1008(10),1012(1),1033(10),1042(4),1046(1),1075(1),1077(1),1085(1),1087(1),1095(1),1097(1),1107(1),1125(1),1127(1),1230(30),2,GPS+GLO+GAL+BDS+SBS,SNIP,POL,52.70,19.57,1,0,sNTRIP,none,B,N,18280,\r\nAGROORSOLIC,Orasje,RTCM 3.3,1004(1),1005(10),1008(10),1012(1),1019(3),1020(2),1033(10),1042(3),1046(2),1077(1),1087(1),1097(1),1107(1),1127(1),1230(30),2,GPS+GLO+GAL+BDS+SBS,SNIP,BIH,45.01,18.60,1,0,sNTRIP,none,B,N,11720,\r\nAJanasz,Przasnysz,RTCM 3.2,1005(1),1074(1),1084(1),1094(1),1124(1),1230(1),,GPS+GLO+GAL+BDS,SNIP,POL,53.06,20.73,1,0,sNTRIP,none,B,N,21540,\r\nAlabamaSylacauga,Sylacauga,RTCM 3.2,1005(1),1077(1),1087(1),1097(1),1127(1),1230(10),4072(1),2,GPS+GLO+GAL+BDS,SNIP,USA,33.22,-86.31,1,0,sNTRIP,none,B,N,6700,\r\nARGOACU,ACU,RTCM 3.2,1006(10),1008(10),1013(10),1033(10),1073(2),1083(2),1093(2),1123(2),1230(10),2,GPS+GLO+GAL+BDS,SNIP,BRA,-21.84,-41.00,1,0,sNTRIP,none,B,N,1100,\r\nARLINGTON-76017,Arlington,RTCM 3,PENDING,,,SNIP,USA,0.00,0.00,1,0,sNTRIP,none,B,N,0,\r\narnoldd,Pludry,RTCM 3.2,1005(1),1074(1),1084(1),1094(1),1124(1),1230(1),,GPS+GLO+GAL+BDS,SNIP,POL,50.68,18.47,1,0,sNTRIP,none,B,N,0,\r\nARSELECTRONICA,Linz,RTCM 3.2,1005(1),1077(1),1087(1),1097(1),1127(1),1230(1),2,GPS+GLO+GAL+BDS,SNIP,AUT,48.31,14.28,1,0,sNTRIP,none,B,N,7500,\r\nAsahikawa-HAMA,Asahikawa,RTCM 3.2,1005(1),1077(1),1087(1),1097(1),1127(1),1230(1),2,GPS+GLO+GAL+BDS,SNIP,JPN,43.80,142.43,1,0,sNTRIP,none,B,N,30980,\r\nAsh_NZ,Ashburton,RTCM 3.2,1005(20),1074(2),1084(2),1094(2),1124(2),1230(10),2,GPS+GLO+GAL+BDS,SNIP,NZL,-43.90,171.76,1,0,sNTRIP,none,B,N,2440,\r\nASKJA,Askja,RTCM 3.2,1005(10),1008(10),1033(10),1077(1),1087(1),1097(1),1127(1),1230(1),2,GPS+GLO+GAL+BDS,SNIP,SWE,63.02,18.21,1,0,sNTRIP,none,B,N,7380,\r\n"
        SOURCETABLE = [
            [
                "ACAKO",
                "Kovin",
                "RTCM 3.2",
                "1005(30),1074(1),1084(1),1094(1)",
                "2",
                "GPS+GLO+GAL",
                "SNIP",
                "SRB",
                "44.75",
                "21.01",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "3420",
                "",
            ],
            [
                "ACASU",
                "Subotica",
                "RTCM 3.2",
                "1005(30),1074(1),1084(1),1094(1)",
                "2",
                "GPS+GLO+GAL",
                "SNIP",
                "SRB",
                "46.06",
                "19.52",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "3400",
                "",
            ],
            [
                "ADS-SAH",
                "Ciudad Real",
                "RTCM 3.2",
                "1005(1),1074(1),1084(1),1094(1),1230(1)",
                "",
                "GPS+GLO+GAL",
                "SNIP",
                "ESP",
                "39.05",
                "-4.06",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "0",
                "",
            ],
            [
                "AgPartner_1",
                "Zaleszany",
                "RTCM 3.3",
                "1004(1),1005(30),1012(1),1019(3),1033(30),1042(3),1046(2),1077(1),1087(1),1097(1),1107(1),1127(1),1230(30)",
                "2",
                "GPS+GLO+GAL+BDS+SBS",
                "SNIP",
                "POL",
                "53.62",
                "17.23",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "11980",
                "",
            ],
            [
                "AgPartner_2",
                "Bozewo",
                "RTCM 3.3",
                "1004(1),1005(10),1007(30),1008(10),1012(1),1033(10),1042(4),1046(1),1075(1),1077(1),1085(1),1087(1),1095(1),1097(1),1107(1),1125(1),1127(1),1230(30)",
                "2",
                "GPS+GLO+GAL+BDS+SBS",
                "SNIP",
                "POL",
                "52.70",
                "19.57",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "18280",
                "",
            ],
            [
                "AGROORSOLIC",
                "Orasje",
                "RTCM 3.3",
                "1004(1),1005(10),1008(10),1012(1),1019(3),1020(2),1033(10),1042(3),1046(2),1077(1),1087(1),1097(1),1107(1),1127(1),1230(30)",
                "2",
                "GPS+GLO+GAL+BDS+SBS",
                "SNIP",
                "BIH",
                "45.01",
                "18.60",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "11720",
                "",
            ],
            [
                "AJanasz",
                "Przasnysz",
                "RTCM 3.2",
                "1005(1),1074(1),1084(1),1094(1),1124(1),1230(1)",
                "",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "POL",
                "53.06",
                "20.73",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "21540",
                "",
            ],
            [
                "AlabamaSylacauga",
                "Sylacauga",
                "RTCM 3.2",
                "1005(1),1077(1),1087(1),1097(1),1127(1),1230(10),4072(1)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "USA",
                "33.22",
                "-86.31",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "6700",
                "",
            ],
            [
                "ARGOACU",
                "ACU",
                "RTCM 3.2",
                "1006(10),1008(10),1013(10),1033(10),1073(2),1083(2),1093(2),1123(2),1230(10)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "BRA",
                "-21.84",
                "-41.00",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "1100",
                "",
            ],
            [
                "ARLINGTON-76017",
                "Arlington",
                "RTCM 3",
                "PENDING",
                "",
                "",
                "SNIP",
                "USA",
                "0.00",
                "0.00",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "0",
                "",
            ],
            [
                "arnoldd",
                "Pludry",
                "RTCM 3.2",
                "1005(1),1074(1),1084(1),1094(1),1124(1),1230(1)",
                "",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "POL",
                "50.68",
                "18.47",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "0",
                "",
            ],
            [
                "ARSELECTRONICA",
                "Linz",
                "RTCM 3.2",
                "1005(1),1077(1),1087(1),1097(1),1127(1),1230(1)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "AUT",
                "48.31",
                "14.28",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "7500",
                "",
            ],
            [
                "Asahikawa-HAMA",
                "Asahikawa",
                "RTCM 3.2",
                "1005(1),1077(1),1087(1),1097(1),1127(1),1230(1)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "JPN",
                "43.80",
                "142.43",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "30980",
                "",
            ],
            [
                "Ash_NZ",
                "Ashburton",
                "RTCM 3.2",
                "1005(20),1074(2),1084(2),1094(2),1124(2),1230(10)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "NZL",
                "-43.90",
                "171.76",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "2440",
                "",
            ],
            [
                "ASKJA",
                "Askja",
                "RTCM 3.2",
                "1005(10),1008(10),1033(10),1077(1),1087(1),1097(1),1127(1),1230(1)",
                "2",
                "GPS+GLO+GAL+BDS",
                "SNIP",
                "SWE",
                "63.02",
                "18.21",
                "1",
                "0",
                "sNTRIP",
                "none",
                "B",
                "N",
                "7380",
                "",
            ],
        ]
        res = serialize_srt(SOURCETABLE)
        self.assertEqual(res, EXPECTED_RESULT)

    def testprocessmonver(self):
        EXPECTED_RESULT = {
            "model": "ZED-F9P",
            "hw_version": "ZED-F9P 00190000",
            "fw_version": "HPG 1.50",
            "sw_version": "Flash 1.00 (f17067)",
            "rom_version": "27.50",
            "gnss_supported": "GPS GLO GAL BDS SBAS QZSS ",
        }
        msg = UBXReader.parse(
            b"\xb5b\n\x04\xdc\x00EXT CORE 1.00 (f17067)\x00\x00\x00\x00\x00\x00\x00\x0000190000\x00\x00ROM BASE 0x118B2060\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00FWVER=HPG 1.50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00PROTVER=27.50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00MOD=ZED-F9P\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00GPS;GLO;GAL;BDS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00SBAS;QZSS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xce\x8b"
        )
        res = process_MONVER(msg)
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
