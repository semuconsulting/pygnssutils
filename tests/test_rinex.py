"""
Helper, Property and Static method tests for pygnssutils rinex conversion

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from platform import system
from time import sleep

from pygnssutils.rinex_conv import RinexConverter
from pygnssutils.rinex_globals import BDS, EPOCH0_GPS, EPOCHMAX, EPOCHMIN, GAL, GPS, IRN
from pygnssutils.rinex_helpers import (
    DRNX,
    FRNX,
    adjust_time_units,
    format_antennabsight,
    format_antennadeltahen,
    format_antennadeltaxyz,
    format_antennatype,
    format_antennazerodirazi,
    format_antennazerodirxyz,
    format_approxpos,
    format_centermass,
    format_clockoffset,
    format_cnrunit,
    format_comments,
    format_fileend,
    format_filename,
    format_glonassfrq,
    format_glonassphasebias,
    format_headerend,
    format_interval,
    format_iono_corr,
    format_leapseconds,
    format_marker,
    format_met_obstypes,
    format_met_sensorpos,
    format_met_sensortype,
    format_numsats,
    format_observer,
    format_obstypes,
    format_rcvrtype,
    format_runby,
    format_sys_antennaphasecentre,
    format_sys_dcbsapplied,
    format_sys_pcvsapplied,
    format_sys_phaseshift,
    format_sys_scalefactor,
    format_time_corr,
    format_timefirstlast,
    format_version,
    listify,
)

SENSORTYPES = {
    "PR": {
        "sensmod": "PR model",
        "senstyp": "PR type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "TD": {
        "sensmod": "TD model",
        "senstyp": "TD type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "HR": {
        "sensmod": "HR model",
        "senstyp": "HR type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "ZW": {
        "sensmod": "ZW model",
        "senstyp": "ZW type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "ZD": {
        "sensmod": "ZD model",
        "senstyp": "ZD type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "ZT": {
        "sensmod": "ZT model",
        "senstyp": "ZT type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "WD": {
        "sensmod": "WD model",
        "senstyp": "WD type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "WS": {
        "sensmod": "WS model",
        "senstyp": "WS type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "PI": {
        "sensmod": "PI model",
        "senstyp": "PI type",
        "accuracy": 1.23456,
        "count": 1,
    },
    "HI": {
        "sensmod": "HI model",
        "senstyp": "HI type",
        "accuracy": 1.23456,
        "count": 1,
    },
}

# only run RINEX file tests locally
RINEXFILETEST = False # system() == "Darwin"


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def testFRNX(self):
        self.assertEqual(FRNX(1234.56, 9, 4), "1234.5600")
        self.assertEqual(FRNX(1234.56, 14, 3), "      1234.560")
        self.assertEqual(FRNX(1234.56, 14, 4), "     1234.5600")
        self.assertEqual(FRNX(1234.56, 15, 7), "   1234.5600000")
        self.assertEqual(FRNX("", 14, 4), "              ")
        self.assertEqual(FRNX(" ", 14, 4), "              ")

    def testDRNX(self):
        self.assertEqual(DRNX(1234567890123456789, 9, 3), "1.235e+18")
        self.assertEqual(
            DRNX(0.00000000000001234567890123456789, 12, 3), "   1.235e-14"
        )
        self.assertEqual(DRNX(0.0000001331791282, 17, 9), "  1.331791282e-07")
        self.assertEqual(DRNX(0.000000000000107469589, 16, 8), "  1.07469589e-13")
        self.assertEqual(DRNX(0.000000000000107469589, 19, 12), " 1.074695890000e-13")
        self.assertEqual(DRNX(-0.000000000000107469589, 19, 12), "-1.074695890000e-13")
        self.assertEqual(DRNX(107469589012345466, 19, 12), " 1.074695890123e+17")
        self.assertEqual(DRNX(0, 19, 12), " 0.000000000000e+00")
        self.assertEqual(DRNX("", 14, 7), "              ")
        self.assertEqual(DRNX(" ", 14, 8), "              ")

    def testformat_filename(self):
        firstobs = datetime(2026, 3, 14, 12, 4, 6)
        lastobs = firstobs + timedelta(minutes=60)
        interval = 15
        res = format_filename(
            "O", [GPS, GAL], firstobs, lastobs, interval, Path("/Users/steve/Downloads")
        )
        # print(res)
        self.assertTrue(
            str(res), "/Users/steve/Downloads/pygpsdata_R_202603141204_60M_15S_MO.rnx"
        )
        firstobs = EPOCHMAX
        lastobs = EPOCHMIN
        interval = 0
        res = format_filename(
            "N", [GPS], firstobs, lastobs, interval, Path("/Users/steve/Downloads")
        )
        # print(res)
        self.assertTrue(
            str(res), "/Users/steve/Downloads/pygpsdata_R_999912310000_00U_00U_GN.rnx"
        )

    def testformat_antennabsight(self):
        res = format_antennabsight()

    def testformat_antennadeltahen(self):
        res = format_antennadeltahen()

    def testformat_antennadeltaxyz(self):
        res = format_antennadeltaxyz()

    def testformat_antennatype(self):
        res = format_antennatype()

    def testformat_antennazerodirazi(self):
        res = format_antennazerodirazi()

    def testformat_antennazerodirxyz(self):
        res = format_antennazerodirxyz()

    def testformat_approxpos(self):
        res = format_approxpos()

    def testformat_centermass(self):
        res = format_centermass()

    def testformat_clockoffset(self):
        res = format_clockoffset()

    def testformat_cnrunit(self):
        res = format_cnrunit()

    def testformat_comments(self):
        res = format_comments()

    def testformat_fileend(self):
        res = format_fileend()

    def testformat_glonassfrq(self):
        res = format_glonassfrq()

    def testformat_glonassphasebias(self):
        res = format_glonassphasebias()

    def testformat_headerend(self):
        res = format_headerend()

    def testformat_interval(self):
        res = format_interval()

    def testformat_leapseconds(self):
        ep = datetime(2016, 5, 12, 12, 34, 34, tzinfo=timezone.utc)
        res = format_leapseconds(ep, "")
        # print(res)
        self.assertEqual(
            res,
            "    17        1896     4GPS                                 LEAPSECONDS\n",
        )
        res = format_leapseconds(ep, [BDS])
        # print(res)
        self.assertEqual(
            res,
            "     3         540     3BDT                                 LEAPSECONDS\n",
        )

    def testformat_marker(self):
        res = format_marker()

    def testformat_numsats(self):
        res = format_numsats()

    def testformat_observer(self):
        res = format_observer()

    def testformat_obstypes(self):
        res = format_obstypes()

    def testformat_rcvrtype(self):
        res = format_rcvrtype()

    def testformat_runby(self):
        res = format_runby()

    def testformat_sys_antennaphasecentre(self):
        res = format_sys_antennaphasecentre()

    def testformat_sys_dcbsapplied(self):
        res = format_sys_dcbsapplied()

    def testformat_sys_pcvsapplied(self):
        res = format_sys_pcvsapplied()

    def testformat_sys_phaseshift(self):
        res = format_sys_phaseshift()

    def testformat_sys_scalefactor(self):
        res = format_sys_scalefactor()

    def testformat_timefirstlast(self):
        res = format_timefirstlast(datetime(2026, 4, 23, 8, 34, 14), "FIRST")
        self.assertEqual(
            res,
            "  2026     4    23     8    34   14.0000000     GPS         TIME OF FIRST OBS\n",
        )

    def testformat_version(self):
        res = format_version("3.05", "O", "M")
        self.assertEqual(
            res,
            "     3.05           O: OBSERVATION      M: MIXED            RINEX VERSION / TYPE\n",
        )

    def testformat_iono_corr(self):
        EXPECTED_RESULT = (
            "GPSA   1.2481e-07  5.0391e-06  2.3771e-07  1.2346e-13 A 02  IONOSPHERIC CORR\n"
            "GPSB   1.2481e-07  5.0391e-06  2.3771e-07  1.2346e-13 B 14  IONOSPHERIC CORR\n"
        )
        ionocorr = {
            "GPSA": {
                "parm1": 0.00000012481234567890,
                "parm2": 0.0000050391234567890,
                "parm3": 0.00000023771234567890,
                "parm4": 0.00000000000012345678909,
                "timemark": "A",
                "svid": 2,
            },
            "GPSB": {
                "parm1": 0.00000012481234567890,
                "parm2": 0.0000050391234567890,
                "parm3": 0.00000023771234567890,
                "parm4": 0.00000000000012345678909,
                "timemark": "B",
                "svid": 14,
            },
        }
        res = format_iono_corr(ionocorr)
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_time_corr(self):
        EXPECTED_RESULT = "GAUT  3.7252902980e-09 5.329070520e-15 345600 1849   E10  5 TIME SYSTEM CORR\n"
        timecorr = {
            "GAUT": {
                "a0": 0.000000003725290298,
                "a1": 0.00000000000000532907052,
                "timeref": 345600,
                "weekno": 1849,
                "svcode": "E10",
                "source": "5",
            }
        }
        res = format_time_corr(timecorr)
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_met_obstypes(self):
        EXPECTED_RESULT = (
            "    10    PR    TD    HR    ZW    ZD    ZT    WD    WS    PI# / TYPES OF OBSERV\n"
            "          HI                                                # / TYPES OF OBSERV\n"
        )
        res = format_met_obstypes(SENSORTYPES)
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_met_sensortype(self):
        EXPECTED_RESULT = (
            "PR model            PR type                       1.2    PR SENSOR MOD/TYPE/ACC\n"
            "TD model            TD type                       1.2    TD SENSOR MOD/TYPE/ACC\n"
            "HR model            HR type                       1.2    HR SENSOR MOD/TYPE/ACC\n"
            "ZW model            ZW type                       1.2    ZW SENSOR MOD/TYPE/ACC\n"
            "ZD model            ZD type                       1.2    ZD SENSOR MOD/TYPE/ACC\n"
            "ZT model            ZT type                       1.2    ZT SENSOR MOD/TYPE/ACC\n"
            "WD model            WD type                       1.2    WD SENSOR MOD/TYPE/ACC\n"
            "WS model            WS type                       1.2    WS SENSOR MOD/TYPE/ACC\n"
            "PI model            PI type                       1.2    PI SENSOR MOD/TYPE/ACC\n"
            "HI model            HI type                       1.2    HI SENSOR MOD/TYPE/ACC\n"
        )
        res = format_met_sensortype(SENSORTYPES)
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_met_sensorpos(self):
        EXPECTED_RESULT = "        1.2345        2.3456        3.4567        4.5678 PR SENSOR POS XYZ/H\n"
        res = format_met_sensorpos([1.2345, 2.3456, 3.4567, 4.5678], "PR")
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testadjust_time_units(self):
        self.assertEqual(adjust_time_units(34), (34, "S"))
        self.assertEqual(adjust_time_units(345), (6.0, "M"))
        self.assertEqual(adjust_time_units(4800), (80, "M"))
        self.assertEqual(adjust_time_units(12345), (3.0, "H"))
        self.assertEqual(adjust_time_units(1958400), (23.0, "D"))
        self.assertEqual(adjust_time_units(1958400000), (62.0, "Y"))
        self.assertEqual(adjust_time_units("asdfa"), (0, "U"))
        self.assertEqual(adjust_time_units(1.23e20), (0, "U"))

    def testlistify(self):
        self.assertEqual(listify("first,second,third"), ["first", "second", "third"])
        self.assertEqual(listify("first, second, third "), ["first", "second", "third"])
        self.assertEqual(
            listify(["first", "second", "third"]), ["first", "second", "third"]
        )
        self.assertEqual(listify("test"), ["test"])
        self.assertEqual(listify(""), [""])
        self.assertEqual(listify(None), [""])
        self.assertEqual(listify([""]), [""])

    def testrinexnav(self):
        EXPECTED_RESULT_OBS = [
            r"     3.05           O: OBSERVATION      M: MIXED            RINEX VERSION / TYPE\n",
            r"PYRINEXCONV 0.1.0 ALSTEVE               \b\d{8}\b \b\d{6}\b UTC PGM / RUN BY / DATE\n",
            r"RinexConverter 0.1.0 NAV test                               COMMENT\n",
            r"LOCAL                                                       MARKER NAME\n",
            r"1                                                           MARKER NUMBER\n",
            r"GEODETIC                                                    MARKER TYPE\n",
            r"semuadmin                                                   OBSERVER / AGENCY\n",
            r"1                   ublox X20P          HPG 2.02            REC # / TYPE / VERS\n",
            r"1                   Beitian BT-184                          ANT # / TYPE\n",
            r"  3803648.1838  -148798.4259  5100640.5407                  APPROX POSITION XYZ\n",
            r"        0.0000        0.0000        0.0000                  ANTENNA: DELTA H/E/N\n",
            r"G   12 C5Q L5Q D5Q S5Q C1C L1C D1C S1C C2L L2L D2L S2L      SYS / # / OBS TYPES\n",
            r"C   12 C5P L5P D5P S5P C6C L6C D6C S6C C1P L1P D1P S1P      SYS / # / OBS TYPES\n",
            r"E   12 C5Q L5Q D5Q S5Q C1C L1C D1C S1C C6B L6B D6B S6B      SYS / # / OBS TYPES\n",
            r"DBHZ                                                        SIGNAL STRENGTH UNIT\n",
            r"     1.000                                                  INTERVAL\n",
            r"  2026     4    24     8    47   32.0040000     GPS         TIME OF FIRST OBS\n",
            r"  2026     4    24     9     7   19.0030000     GPS         TIME OF LAST OBS\n",
            r"                                                            GLONASS SLOT / FRQ\n",
            r" C1C    0.000 C1P    0.000 C2C    0.000 C2P    0.000        GLONASS COD/PHS/BIS\n",
            r"    18        2415     5GPS                                 LEAPSECONDS\n",
            r"    34                                                      # OF SATELLITES\n",
            r"                                                            END OF HEADER\n",
            r"> 2026  4 24  8 47 32.0040000  0 27                     \n",
            r"G26  21437036.766    84123533.8310        209.268          48.000    21437038.61\n",
            r"→4   112652397.0350        280.161          53.000    21437038.650    87781089.8\n",
            r"→610        218.296          44.000  \n",
            r"G27  24519701.570    96220582.5730       2916.127          42.000    24519698.27\n",
            r"→4   128851890.4480       3904.912          40.000    24519702.984   100404084.7\n",
            r"→711       3041.609          24.000  \n",
        ]

        EXPECTED_RESULT_NAV = [
            r"     3.05           N: NAVIGATION       M: MIXED            RINEX VERSION / TYPE\n",
            r"PYRINEXCONV 0.1.0 ALSTEVE               \b\d{8}\b \b\d{6}\b UTC PGM / RUN BY / DATE\n",
            r"RinexConverter 0.1.0 NAV test                               COMMENT\n",
            r"GPSA   1.8626e-08  1.4901e-08 -1.1921e-07 -1.1921e-07 V 29  IONOSPHERIC CORR\n",
            r"GPSB   1.1469e\+05  6.5536e\+04 -1.9661e\+05 -6.5536e\+04 V 29  IONOSPHERIC CORR\n",
            r"GPUT  0.0000000000e\+00-4.656612873e-09 61440  112    G56  0 TIME SYSTEM CORR\n",
            r"    18        2415     5GPS                                 LEAPSECONDS\n",
            r"                                                            END OF HEADER\n",
            r"G26 2026 04 24 09 59 42-3.574695438147e-04-4.433786671143e-12 0.000000000000e\+00\n",
            r"     9.300000000000e\+01 2.503125000000e\+01 1.804437488317e-09 5.920644043945e-01\n",
            r"     1.300126314163e-06 1.103244593833e-02 7.566064596176e-06 5.153741914749e\+03\n",
            r"     4.680000000000e\+05-3.576278686523e-07-3.539365250617e-03 4.284083843231e-08\n",
            r"     2.955303755589e-01 2.191875000000e\+02 2.267913562246e-01-2.714386937441e-09\n",
            r"     5.184119800106e-11                    3.670000000000e\+02                   \n",
            r"     0.000000000000e\+00 0.000000000000e\+00 6.519258022308e-09                   \n",
            r"     7.747300000000e\+04                                                         \n",
        ]

        if RINEXFILETEST is False:
            return
        rc = RinexConverter(
            app="cliapp",
            rinex_version="3.05",
            rinex_types=[""],
            gnssfilter=[""],
            obsfilter=[""],
            datasource=["R", "R", "R"],
            minobs=10,
            marker=["LOCAL", "1", "GEODETIC"],
            antenna=["1", "Beitian BT-184"],
            receiver=["1", "ublox X20P", "HPG 2.02"],
            observer="semuadmin",
            comments=["RinexConverter 0.1.0 NAV test"],
        )
        rc.process_input("tests/pygpsdata_x20p_rxmsfrbx.log")
        sleep(0.1)
        with open("tests/pygpsdata_R_202604240959_16S_16S_MN.rnx", "r") as infile:
            for i, ln in enumerate(infile.readlines()):
                # print(ln)
                self.assertRegex(ln, EXPECTED_RESULT_NAV[i])
                if i == 15:
                    break
        with open("tests/pygpsdata_R_202604240847_20M_01S_MO.rnx", "r") as infile:
            for i, ln in enumerate(infile.readlines()):
                # print(ln)
                self.assertRegex(ln, EXPECTED_RESULT_OBS[i])
                if i == 29:
                    break
