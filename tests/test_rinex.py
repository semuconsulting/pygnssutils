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
from time import sleep

from pygnssutils.rawnav import RawNav
from pygnssutils.rawnav_subframes_glo import (
    GLO_L1OF_SUBFRAME_1,
    GLO_L1OF_SUBFRAME_2,
    GLO_L1OF_SUBFRAME_3,
)
from pygnssutils.rawnav_subframes_bds import (
    BDS_D1_SUBFRAME_1,
    BDS_D1_SUBFRAME_2,
    BDS_D1_SUBFRAME_3,
)
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
    format_eop,
    format_fileend,
    format_filename,
    format_glonassfrq,
    format_glonassphasebias,
    format_headerend,
    format_interval,
    format_ion,
    format_iono_corr,
    format_leapseconds,
    format_marker,
    format_met_obstypes,
    format_met_sensorpos,
    format_met_sensortype,
    format_nav_typesvmssg,
    format_numsats,
    format_observer,
    format_obstypes,
    format_rcvrtype,
    format_runby,
    format_sto,
    format_sys_antennaphasecentre,
    format_sys_dcbsapplied,
    format_sys_pcvsapplied,
    format_sys_phaseshift,
    format_sys_scalefactor,
    format_time_corr,
    format_timefirstlast,
    format_version,
    get_epoch,
    get_epoch_glo,
    get_svcode,
    gpsura2m,
    glotk2sec,
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
RINEXFILETEST = False  # system() == "Darwin"


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

    def testgetsvcode(self):
        self.assertEqual(get_svcode("G", 3), "G03")
        self.assertEqual(get_svcode("G", 3, False), "G 3")
        self.assertEqual(get_svcode("E", 12), "E12")
        self.assertEqual(get_svcode("E", 12, False), "E12")
        self.assertEqual(get_svcode("S", 112), "S12")
        self.assertEqual(get_svcode("S", 112, False), "S12")
        self.assertEqual(get_svcode("J", 194), "J02")
        self.assertEqual(get_svcode("J", 194, False), "J 2")
        self.assertEqual(get_svcode("G", 3), "G03")
        self.assertEqual(get_svcode("G", 3, False), "G 3")
        self.assertEqual(get_svcode("S", 112 - 100), "S12")
        self.assertEqual(get_svcode("S", 112 - 100, False), "S12")
        self.assertEqual(get_svcode("J", 194 - 192), "J02")
        self.assertEqual(get_svcode("J", 194 - 192, False), "J 2")

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
        firstobs = datetime(2026, 3, 14, 12, 4, 6)
        lastobs = firstobs + timedelta(minutes=60)
        interval = 15
        res = format_filename(
            rinextype="O",
            gnssfilter=[GPS],
            startepoch=firstobs,
            endepoch=lastobs,
            interval=interval,
            outputpath=Path("/Users/steve/Downloads"),
            form="IGS",
            site="SITE",
            marker=1,
            receiver=1,
            country="GBR",
        )
        # print(res)
        self.assertTrue(
            str(res), "/Users/steve/Downloads/SITE11GBR_R_202603141204_60M_15S_GO.rnx"
        )

    def test_getepoch(self):
        res = get_epoch(366, 411634, "G")
        # print(res)
        self.assertEqual(
            res, (datetime(2026, 4, 16, 18, 20, 34, tzinfo=timezone.utc), 2414)
        )

    def test_glotk2sec(self):
        res = glotk2sec(1584)
        # print(res)
        self.assertEqual(res, 44640)
        res = glotk2sec(1585)
        # print(res)
        self.assertEqual(res, 44670)
        res = glotk2sec(1586)
        # print(res)
        self.assertEqual(res, 44700)

    def test_getepochglo(self):
        res = get_epoch_glo(884, 8, 1584)
        # print(res)
        self.assertEqual(res, datetime(2026, 6, 2, 9, 24, 0, tzinfo=timezone.utc))
        res = get_epoch_glo(884, 8, 1646)
        # print(res)
        self.assertEqual(res, (datetime(2026, 6, 2, 9, 55, 0, tzinfo=timezone.utc)))

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
        res = format_iono_corr(
            svid=2,
            timemark="A",
            corrtype="GPSA",
            parm1=0.00000012481234567890,
            parm2=0.0000050391234567890,
            parm3=0.00000023771234567890,
            parm4=0.00000000000012345678909,
        )
        res += format_iono_corr(
            svid=14,
            timemark="B",
            corrtype="GPSB",
            parm1=0.00000012481234567890,
            parm2=0.0000050391234567890,
            parm3=0.00000023771234567890,
            parm4=0.00000000000012345678909,
        )
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_ion(self):
        EXPECTED_RESULT = (
            "> ION G24 LNAV XXXX\n"
            "    2026 05 13 08 34 02 1.234567000000e-12 1.234567000000e-12-1.234567000000e-12\n"
            "     1.234567000000e-12 1.234567000000e-12 1.234567000000e-12-1.234567000000e-12\n"
            "     1.234567000000e-12\n"
        )
        res = format_ion(
            svcode="G24",
            msgtype="LNAV",
            msgsubtype="XXXX",
            epoch=datetime(2026, 5, 13, 8, 34, 2, tzinfo=timezone.utc),
            a0=1.234567e-12,
            a1=1.234567e-12,
            a2=-1.234567e-12,
            a3=1.234567e-12,
            b0=1.234567e-12,
            b1=1.234567e-12,
            b2=-1.234567e-12,
            b3=1.234567e-12,
        )
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_eop(self):
        EXPECTED_RESULT = (
            "> EOP G24 LNAV XXXX\n"
            "    2026 05 13 08 34 02 2.082471847534e-01-6.551742553711e-04 0.000000000000e+00\n"
            "                        3.444433212280e-01-9.121894836426e-04 0.000000000000e+00\n"
            "     1.729860000000e+05-1.754972934723e-01 5.635917186737e-04 0.000000000000e+00\n"
        )
        res = format_eop(
            svcode="G24",
            msgtype="LNAV",
            msgsubtype="XXXX",
            epoch=datetime(2026, 5, 13, 8, 34, 2, tzinfo=timezone.utc),
            tom=1.729860000000e05,
            xp=2.082471847534e-01,
            dxpdt=-6.551742553711e-04,
            dxpdt2=0.000000000000e00,
            yp=3.444433212280e-01,
            dypdt=-9.121894836426e-04,
            dypdt2=0.000000000000e00,
            deltaut1=-1.754972934723e-01,
            ddeltaut1dt=5.635917186737e-04,
            d2deltaut1dt2=0.000000000000e00,
        )
        print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_time_corr(self):
        EXPECTED_RESULT = "GAUT  3.7252902980e-09 5.329070520e-15 345600 1849   E10  5 TIME SYSTEM CORR\n"
        res = format_time_corr(
            svcode="E10",
            corrtype="GAUT",
            timeref=345600,
            weekno=1849,
            source="5",
            a0=0.000000003725290298,
            a1=0.00000000000000532907052,
        )
        # print(res)
        self.assertEqual(res, EXPECTED_RESULT)

    def testformat_sto(self):
        EXPECTED_RESULT = (
            "> STO G24 LNAV XXXX\n"
            "    2026 05 13 08 34 02 GPUT               SSSS               UTC(USNO)         \n"
            "     4.567890000000e+05 1.234567000000e-23 1.234567000000e-23-1.234567800000e-12\n"
        )
        res = format_sto(
            svcode="G24",
            msgtype="LNAV",
            msgsubtype="XXXX",
            epoch=datetime(2026, 5, 13, 8, 34, 2, tzinfo=timezone.utc),
            timecode="GPUT",
            sbasid="SSSS",
            utcid="UTC(USNO)",
            tot=456789,
            a0=1.234567e-23,
            a1=1.234567e-23,
            a2=-1.2345678e-12,
        )
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

    def testformat_nav_typesvmssg(self):
        EXPECTED_RESULT = "> EPH G04 LNAV     \n"
        res = format_nav_typesvmssg("EPH", "G04", "LNAV")
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

    def testgpsura2m(self):

        self.assertEqual(gpsura2m(1), 2.8)
        self.assertEqual(gpsura2m(2), 4.0)
        self.assertEqual(gpsura2m(3), 5.7)
        self.assertEqual(gpsura2m(5), 11.3)
        self.assertEqual(gpsura2m(8), 64)
        self.assertEqual(gpsura2m(14), 4096)
        self.assertEqual(gpsura2m(15), 0)
        self.assertEqual(gpsura2m(-16), 0)
        self.assertEqual(gpsura2m(-8), 0.1)
