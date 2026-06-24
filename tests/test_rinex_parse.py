"""
Parse tests for pygnssutils rinex conversion

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long

import unittest

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
from pygnssutils.rawnav_subframes_sba import (
    SBA_L1CA_MT_9,
    SBA_L1CA_MT_12,
    SBA_L1CA_MT_17,
)
from pygnssutils.rinex_helpers import adjust_time_units,gpsura2m,listify

# only run RINEX file tests locally
RINEXFILETEST = False  # system() == "Darwin"


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

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

    def testrawnavparserGLO(
        self,
    ):  # test parser produces correct scaled values from subframe bits
        EXPECTED_RESULT = "<RAWNAV(R021C, gnss=R, svid=2, sigid=1C, sfracq=7, sid=3, p1=1, tk=398, xntbdot=6.67572021484375e-06, xntbdot2=-6.51925802230835e-09, xntb=0.00732421875, bn=1, p2=1, tb=105, yntbdot=1.430511474609375e-05, yntbdot2=-1.3969838619232178e-08, yntb=0.01513671875, p3=1, gammantb=6.366462912410498e-12, p=1, ln=1, zntbdot=2.956390380859375e-05, zntbdot2=-2.7939677238464355e-09, zntb=0.03076171875)>"
        BITS = (
            (
                (
                    "0", # idle
                    "0001", # sid
                    "00", # reserved
                    "01", # p1
                    "000110001110", # tk
                    "000000000000000000000111", # xntbdot
                    "11001", # xntbdot2
                    "000000000000000000000001111", # xntb
                    "00000000", # hamming
                ),
                GLO_L1OF_SUBFRAME_1,
            ),
            (
                (
                    "0", # idle
                    "0010",  # sid
                    "001", # bn
                    "1", # p2
                    "0000111", # tb
                    "00000", # reserved
                    "000000000000000000001111", # yntbdot
                    "10001", # yntbdot2
                    "000000000000000000000011111", # yntb
                    "00000000",  # hamming
                ),
                GLO_L1OF_SUBFRAME_2,
            ),
            (
                (
                    "0", # idle
                    "0011",  # sid
                    "1", # p3
                    "00000000111", # gammantb
                    "0", # reserved
                    "01", # p
                    "1", # ln
                    "000000000000000000011111", # zntbdot
                    "11101", # zntbdot2
                    "000000000000000000000111111", # zntb
                    "00000000",  # hamming
                ),
                GLO_L1OF_SUBFRAME_3,
            ),
        )
        raw = RawNav("R", 2, "1C")
        for data, dic in BITS:
            sfrbits = "0b" + "".join(data)
            self.assertEqual(len(sfrbits), 85 + 2)
            raw.parse(int(sfrbits, 2), dic, 0b111)
        self.assertEqual(raw.gnss, "R")
        self.assertEqual(raw.svid, 2)
        self.assertEqual(raw.sigcode, "1C")
        self.assertEqual(raw.svcode, "R 2")
        self.assertEqual(raw.identity, "R021C")
        self.assertEqual(raw.sid, 3)
        self.assertEqual(raw.subframeacq, 7)
        self.assertEqual(raw.tk, 398)
        self.assertEqual(raw.tb, 7 * 15)
        self.assertEqual(raw.gammantb, 7 * 2**-40)
        self.assertEqual(raw.xntbdot, 7 * 2**-20)
        self.assertEqual(raw.xntbdot2, -7 * 2**-30)
        self.assertEqual(raw.xntb, 15 * 2**-11)
        self.assertEqual(raw.yntbdot, 15 * 2**-20)
        self.assertEqual(raw.yntbdot2, -15 * 2**-30)
        self.assertEqual(raw.yntb, 31 * 2**-11)
        self.assertEqual(raw.zntbdot, 31 * 2**-20)
        self.assertEqual(raw.zntbdot2, -3 * 2**-30)
        self.assertEqual(raw.zntb, 63 * 2**-11)
        self.assertEqual(str(raw), EXPECTED_RESULT)

    def testrawnavparserBDS(
        self,
    ):  # test parser produces correct scaled values from subframe bits
        EXPECTED_RESULT = "<RAWNAV(C122I, gnss=C, svid=12, sigid=2I, sfracq=7, wn=0, toc=0, tow=28679, rev=0, sid=3, sath1=0, aodc=0, urai=0, tgd1=0.0, tgd2=0.0, alpha0=0.0, alpha1=0.0, alpha2=0.0, alpha3=0.0, beta0=0, beta1=0, beta2=0, beta3=0, af2=0.0, af0=0.0, af1=0.0, aode=0, deltan=0.0, cuc=0.0, m0=0.0, e=0.0, cus=0.0, crc=0.0, crs=0.0, sqrta=5282.639436721802, toe=263992, i0=0.0, cic=0.0, omegadot=6.520053830172401e-09, cis=0.0, idot=0.0, omega0=0.0, omega=0.0, rev1=0)>"
        BITS = (
            (
                (
                    "11100010010", # preamble
                    "0000", # rev
                    "001", # sid
                    "00000111", # tow_msb
                    "0000", # _parity1
                    "000000000111", # tow_lsb
                    "0", # sath1
                    "00000", # aodc
                    "0000", # urai
                    "00000000", # _parity2
                    "0000000000000", # wn
                    "000000000", # toc_msb
                    "00000000", # _parity3
                    "00000000", # toc_lsb
                    "0000000000", # tgd1
                    "0000", # tgd2_msb
                    "00000000", # _parity4
                    "000000", # tgd2_lsb
                    "00000000", # alpha0
                    "00000000", # alpha1
                    "00000000", # _parity5
                    "00000000", # alpha2
                    "00000000", # alpha3
                    "000000", # beta0_msb
                    "00000000", # _parity6
                    "00", # beta0_lsb
                    "00000000", # beta1
                    "00000000", # beta2
                    "0000", # beta3_msb
                    "00000000", # _parity7
                    "0000", # beta3_lsb
                    "00000000000", # af2
                    "0000000", # af0_msb
                    "00000000", # _parity8
                    "00000000000000000", # af0_lsb
                    "00000", # af1_msb
                    "00000000", # _parity9
                    "00000000000000000", # af1_lsb
                    "00000", # aode
                    "00000000", # _parity10
                ),
               BDS_D1_SUBFRAME_1,
            ),
            (
                (
                    "11100010010", # preamble
                    "0000", # rev
                    "010", # sid
                    "00000111", # tow_msb
                    "0000", # _parity1
                    "000000000111", # tow_lsb
                    "0000000000", # deltan_msb
                    "00000000", # _parity2
                    "000000", # deltan_lsb
                    "0000000000000000", # cuc_msb
                    "00000000", # _parity3
                    "00", # cuc_lsb
                    "00000000000000000000", # m0_msb
                    "00000000", # _parity4
                    "000000000000", # m0_lsb
                    "0000000000", # e_msb
                    "00000000", # _parity5
                    "0000000000000000000000", # e_lsb
                    "00000000", # _parity6
                    "000000000000000000", # cus
                    "0000", # crc_msb
                    "00000000", # _parity7
                    "00000000000000", # crc_lsb
                    "00000000", # crs_msb
                    "00000000", # _parity8
                    "0000000000", # crs_lsb
                    "101001010001", # sqrta_msb
                    "00000000", # _parity9
                    "01010001110110010001", # sqrta_lsb
                    "01", # toe_msb
                    "00000000", # _parity10
                ),
                BDS_D1_SUBFRAME_2,
            ),
            (
                (
                    "11100010010", # preamble
                    "0000", # rev
                    "011", # sid
                    "00000111", # tow_msb
                    "0000", # _parity1
                    "000000000111", # tow_lsb
                    "0000000111", # toe_isb
                    "00000000", # _parity2
                    "00111", # toe_lsb
                    "00000000000000000", # i0_msb
                    "00000000", # _parity3
                    "000000000000000", # i0_lsb
                    "0000000", # cic_msb
                    "00000000", # _parity4
                    "00000000000", # cic_lsb
                    "00000000111", # omegadot_msb
                    "00000000", # _parity5
                    "0000000000111", # omegadot_lsb
                    "000000000", # cis_msb
                    "00000000", # _parity6
                    "000000000", # cis_lsb
                    "0000000000000", # idot_msb
                    "00000000", # _parity7
                    "0", # idot_lsb
                    "000000000000000000000", # omega0_msb
                    "00000000", # _parity8
                    "00000000000", # omega0_lsb
                    "00000000000", # omega_msb
                    "00000000", # _parity9
                    "000000000000000000000", # omega_lsb
                    "0", # rev1
                    "00000000", # _parity10
                ),
                BDS_D1_SUBFRAME_3,
            ),
        )
        raw = RawNav("C", 12, "2I")
        for data, dic in BITS:
            sfrbits = "0b" + "".join(data)
            self.assertEqual(len(sfrbits), 300 + 2)
            raw.parse(int(sfrbits, 2), dic, 0b111)
        self.assertEqual(raw.gnss, "C")
        self.assertEqual(raw.svid, 12)
        self.assertEqual(raw.sigcode, "2I")
        self.assertEqual(raw.svcode, "C12")
        self.assertEqual(raw.identity, "C122I")
        self.assertEqual(raw.sid, 3)
        self.assertEqual(raw.subframeacq, 7)
        self.assertEqual(raw.tow, 0b00000111000000000111)
        self.assertEqual(raw.toe, 0b01000000011100111 * 2**3)
        self.assertEqual(raw.sqrta, 0b10100101000101010001110110010001 * 2**-19)
        self.assertEqual(raw.omegadot, 0b00000000001110000000000111 * 2**-43)

        self.assertEqual(str(raw), EXPECTED_RESULT)

    def testrawnavparserSBA(
        self,
    ):  # test parser produces correct scaled values from subframe bits
        EXPECTED_RESULT = "<RAWNAV(S361C, gnss=S, svid=136, sigid=1C, sfracq=7, wn=7, toc=28672, tow=7, sid=17, iodn=0, t0=0, ura=0, xpos=0.56, ypos=1.2, zpos=12.4, xdot=0.004375, ydot=0.009375, zdot=0.124, xdot2=8.75e-05, ydot2=0.0001875, zdot2=0.0019375, agf0=3.259629011154175e-09, agf1=1.3642420526593924e-11, a1=6.217248937900877e-15, a0=1.3969838619232178e-08, wnt=7, deltatls=7, wnlsf=7, dn=7, deltatlsf=7, utcid=3, gloind=0, deltatglo=7, dataid_01=0, prn_01=0, svhealth_01=0, xg_01=0, yg_01=0, zg_01=0, xgdot_01=0, ygdot_01=0, zgdot_01=0, dataid_02=0, prn_02=0, svhealth_02=0, xg_02=0, yg_02=0, zg_02=0, xgdot_02=0, ygdot_02=0, zgdot_02=0, dataid_03=0, prn_03=0, svhealth_03=0, xg_03=0, yg_03=0, zg_03=0, xgdot_03=0, ygdot_03=0, zgdot_03=0)>"
        BITS = (
            (
                (
                    "00000000", # _preamble
                    "001001", # sid
                    "00000000", # iodn
                    "0000000000000", # t0
                    "0000", # ura
                    "000000000000000000000000000111", # xpos
                    "000000000000000000000000001111", # ypos
                    "0000000000000000000011111", # zpos
                    "00000000000000111", # xdot
                    "00000000000001111", # ydot
                    "000000000000011111", # zdot
                    "0000000111", # xdot2
                    "0000001111", # ydot2
                    "0000011111", # zdot2
                    "000000000111", # agf0
                    "00001111", # agf1
                    "000000000000000000000000", # _parity
                ),
                SBA_L1CA_MT_9,
            ),
            (
                (
                    "00000000", # _preamble
                    "001100", # sid
                    "000000000000000000000111", # a1
                    "00000000000000000000000000001111", # a0
                    "00000111", # toc
                    "00000111", # wnt
                    "00000111", # deltatls
                    "00000111", # wnlsf
                    "00000111", # dn
                    "00000111", # deltatlsf
                    "011", # utcid
                    "00000000000000000111", # tow
                    "0000000111", # wn
                    "0", # gloind
                    "00000000000000000000000000000000000000000000000000000000000000000000000111", # deltatglo
                    "000000000000000000000000", # _parity
                ),
                SBA_L1CA_MT_12,
            ),
            (
                (
                    "00000000", # _preamble
                    "010001", # sid
                    "00", # dataid_01
                    "00000000", # prn_01
                    "00000000", # svhealth_01
                    "000000000000000", # xg_01
                    "000000000000000", # yg_01
                    "000000000", # zg_01
                    "000", # xgdot_01
                    "000", # ygdot_01
                    "0000", # zgdot_01
                    "00", # dataid_02
                    "00000000", # prn_02
                    "00000000", # svhealth_02
                    "000000000000000", # xg_02
                    "000000000000000", # yg_02
                    "000000000", # zg_02
                    "000", # xgdot_02
                    "000", # ygdot_02
                    "0000", # zgdot_02
                    "00", # dataid_03
                    "00000000", # prn_03
                    "00000000", # svhealth_03
                    "000000000000000", # xg_03
                    "000000000000000", # yg_03
                    "000000000", # zg_03
                    "000", # xgdot_03
                    "000", # ygdot_03
                    "0000", # zgdot_03
                    "00000000000", # t0
                    "000000000000000000000000", # _parity
                ),
                SBA_L1CA_MT_17,
            ),
        )
        raw = RawNav("S", 136, "1C")
        for data, dic in BITS:
            sfrbits = "0b" + "".join(data)
            self.assertEqual(len(sfrbits), 250 + 2)
            raw.parse(int(sfrbits, 2), dic, 0b111)
        self.assertEqual(raw.gnss, "S")
        self.assertEqual(raw.svid, 136)
        self.assertEqual(raw.sigcode, "1C")
        self.assertEqual(raw.svcode, "S36")
        self.assertEqual(raw.identity, "S361C")
        self.assertEqual(raw.sid, 17)
        self.assertEqual(raw.subframeacq, 7)
        self.assertEqual(raw.xpos, 0b111 * .08)
        self.assertEqual(raw.ypos, 0b1111 * .08)
        self.assertEqual(raw.zpos, 0b11111 * .4)
        self.assertEqual(raw.xdot, 0b111 * .000625)
        self.assertEqual(raw.ydot, 0b1111 * .000625)
        self.assertEqual(raw.zdot, 0b11111 * .004)
        self.assertEqual(raw.xdot2, 0b111 * .0000125)
        self.assertEqual(raw.ydot2, 0b1111 * .0000125)
        self.assertEqual(raw.zdot2, 0b11111 * .0000625)
        self.assertEqual(raw.agf0, 0b111 * 2**-31)
        self.assertEqual(raw.agf1, 0b1111 * 2**-40)
        self.assertEqual(raw.a1, 0b111 * 2**-50)
        self.assertEqual(raw.a0, 0b1111 * 2**-30)
        self.assertEqual(str(raw), EXPECTED_RESULT)

    # def testrinexnav(self):
    #     EXPECTED_RESULT_OBS = [
    #         r"     3.05           O: OBSERVATION      M: MIXED            RINEX VERSION / TYPE\n",
    #         r"PYRINEXCONV 0.1.0 ALSTEVE               \b\d{8}\b \b\d{6}\b UTC PGM / RUN BY / DATE\n",
    #         r"RinexConverter 0.1.0 NAV test                               COMMENT\n",
    #         r"LOCAL                                                       MARKER NAME\n",
    #         r"1                                                           MARKER NUMBER\n",
    #         r"GEODETIC                                                    MARKER TYPE\n",
    #         r"semuadmin                                                   OBSERVER / AGENCY\n",
    #         r"1                   ublox X20P          HPG 2.02            REC # / TYPE / VERS\n",
    #         r"1                   Beitian BT-184                          ANT # / TYPE\n",
    #         r"  3803648.1838  -148798.4259  5100640.5407                  APPROX POSITION XYZ\n",
    #         r"        0.0000        0.0000        0.0000                  ANTENNA: DELTA H/E/N\n",
    #         r"G   12 C5Q L5Q D5Q S5Q C1C L1C D1C S1C C2L L2L D2L S2L      SYS / # / OBS TYPES\n",
    #         r"C   12 C5P L5P D5P S5P C6C L6C D6C S6C C1P L1P D1P S1P      SYS / # / OBS TYPES\n",
    #         r"E   12 C5Q L5Q D5Q S5Q C1C L1C D1C S1C C6B L6B D6B S6B      SYS / # / OBS TYPES\n",
    #         r"DBHZ                                                        SIGNAL STRENGTH UNIT\n",
    #         r"     1.000                                                  INTERVAL\n",
    #         r"  2026     4    24     8    47   32.0040000     GPS         TIME OF FIRST OBS\n",
    #         r"  2026     4    24     9     7   19.0030000     GPS         TIME OF LAST OBS\n",
    #         r"                                                            GLONASS SLOT / FRQ\n",
    #         r" C1C    0.000 C1P    0.000 C2C    0.000 C2P    0.000        GLONASS COD/PHS/BIS\n",
    #         r"    18        2415     5GPS                                 LEAPSECONDS\n",
    #         r"    34                                                      # OF SATELLITES\n",
    #         r"                                                            END OF HEADER\n",
    #         r"> 2026  4 24  8 47 32.0040000  0 27                     \n",
    #         r"G26  21437036.766    84123533.8310        209.268          48.000    21437038.61\n",
    #         r"→4   112652397.0350        280.161          53.000    21437038.650    87781089.8\n",
    #         r"→610        218.296          44.000  \n",
    #         r"G27  24519701.570    96220582.5730       2916.127          42.000    24519698.27\n",
    #         r"→4   128851890.4480       3904.912          40.000    24519702.984   100404084.7\n",
    #         r"→711       3041.609          24.000  \n",
    #     ]

    #     EXPECTED_RESULT_NAV = [
    #         r"     3.05           N: NAVIGATION       M: MIXED            RINEX VERSION / TYPE\n",
    #         r"PYRINEXCONV 0.1.0 ALSTEVE               \b\d{8}\b \b\d{6}\b UTC PGM / RUN BY / DATE\n",
    #         r"RinexConverter 0.1.0 NAV test                               COMMENT\n",
    #         r"GPSA   1.8626e-08  1.4901e-08 -1.1921e-07 -1.1921e-07 V 29  IONOSPHERIC CORR\n",
    #         r"GPSB   1.1469e\+05  6.5536e\+04 -1.9661e\+05 -6.5536e\+04 V 29  IONOSPHERIC CORR\n",
    #         r"GPUT  0.0000000000e\+00-4.656612873e-09 61440  112    G56  0 TIME SYSTEM CORR\n",
    #         r"    18        2415     5GPS                                 LEAPSECONDS\n",
    #         r"                                                            END OF HEADER\n",
    #         r"G26 2026 04 24 09 59 42-3.574695438147e-04-4.433786671143e-12 0.000000000000e\+00\n",
    #         r"     9.300000000000e\+01 2.503125000000e\+01 1.804437488317e-09 5.920644043945e-01\n",
    #         r"     1.300126314163e-06 1.103244593833e-02 7.566064596176e-06 5.153741914749e\+03\n",
    #         r"     4.680000000000e\+05-3.576278686523e-07-3.539365250617e-03 4.284083843231e-08\n",
    #         r"     2.955303755589e-01 2.191875000000e\+02 2.267913562246e-01-2.714386937441e-09\n",
    #         r"     5.184119800106e-11                    3.670000000000e\+02                   \n",
    #         r"     0.000000000000e\+00 0.000000000000e\+00 6.519258022308e-09                   \n",
    #         r"     7.747300000000e\+04                                                         \n",
    #     ]

    #     if RINEXFILETEST is False:
    #         return
    #     rc = RinexConverter(
    #         app="cliapp",
    #         rinex_version="3.05",
    #         rinex_types=[""],
    #         gnssfilter=[""],
    #         obsfilter=[""],
    #         datasource=["R", "R", "R"],
    #         minobs=10,
    #         marker=["LOCAL", "1", "GEODETIC"],
    #         antenna=["1", "Beitian BT-184"],
    #         receiver=["1", "ublox X20P", "HPG 2.02"],
    #         observer="semuadmin",
    #         comments=["RinexConverter 0.1.0 NAV test"],
    #     )
    #     rc.process_input("tests/pygpsdata_x20p_rxmsfrbx.log")
    #     sleep(0.1)
    #     with open("tests/pygpsdata_R_202604240959_16S_16S_MN.rnx", "r") as infile:
    #         for i, ln in enumerate(infile.readlines()):
    #             # print(ln)
    #             self.assertRegex(ln, EXPECTED_RESULT_NAV[i])
    #             if i == 15:
    #                 break
    #     with open("tests/pygpsdata_R_202604240847_20M_01S_MO.rnx", "r") as infile:
    #         for i, ln in enumerate(infile.readlines()):
    #             # print(ln)
    #             self.assertRegex(ln, EXPECTED_RESULT_OBS[i])
    #             if i == 29:
    #                 break
