"""
Sanity check ICD payload definitions for RINEX conversion.

Check that individual bit offsets and lengths and total payload
length are consistent with ICD definition.

Created on 26 May 2022

@author: semuadmin
"""

import unittest

import pygnssutils.rawnav_subframes_bds as bds
import pygnssutils.rawnav_subframes_gal as gal
import pygnssutils.rawnav_subframes_glo as glo
import pygnssutils.rawnav_subframes_gps as gps
import pygnssutils.rawnav_subframes_sba as sba
import pygnssutils.rawnav_subframes_qzs as qzs
import pygnssutils.rawnav_subframes_irn as irn
from pygnssutils.rawnav import VALPREAMBLE


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def scandefs(self, sfrdefs, sfrlen):
        for dic in sfrdefs:
            offset = 0
            totlen = 0
            for key, vals in dic.items():
                if key == VALPREAMBLE:
                    continue
                off, len, typ, sca = vals
                self.assertEqual(off, offset)
                # print(f'"{key}": ({offset},{len},{typ},{sca}),')
                offset += len
                totlen += len
            self.assertEqual(totlen, sfrlen)

    def testGPSLNAV(self):

        sfrdefs = (
            gps.GPS_LNAV_SUBFRAME_1,
            gps.GPS_LNAV_SUBFRAME_2,
            gps.GPS_LNAV_SUBFRAME_3,
            gps.GPS_LNAV_SUBFRAME_4_P18,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testGPSCNAV(self):
        sfrdefs = (
            gps.GPS_CNAV_SUBFRAME_10,
            gps.GPS_CNAV_SUBFRAME_11,
            gps.GPS_CNAV_SUBFRAME_12,
            gps.GPS_CNAV_SUBFRAME_13,
            gps.GPS_CNAV_SUBFRAME_14,
            gps.GPS_CNAV_SUBFRAME_15,
            gps.GPS_CNAV_SUBFRAME_30,
            gps.GPS_CNAV_SUBFRAME_31,
            gps.GPS_CNAV_SUBFRAME_32,
            gps.GPS_CNAV_SUBFRAME_33,
            gps.GPS_CNAV_SUBFRAME_34,
            gps.GPS_CNAV_SUBFRAME_35,
            gps.GPS_CNAV_SUBFRAME_36,
            gps.GPS_CNAV_SUBFRAME_37,
            gps.GPS_CNAV_SUBFRAME_40,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testGALFNAV(self):

        sfrdefs = (
            gal.GAL_FNAV_SUBFRAME_1,
            gal.GAL_FNAV_SUBFRAME_2,
            gal.GAL_FNAV_SUBFRAME_3,
            gal.GAL_FNAV_SUBFRAME_4,
            gal.GAL_FNAV_SUBFRAME_5,
            gal.GAL_FNAV_SUBFRAME_6,
        )
        sfrlen = 244
        self.scandefs(sfrdefs, sfrlen)

    def testGALINAV(self):

        sfrdefs = (gal.GAL_INAV_SUBFRAME,)
        sfrlen = 256
        self.scandefs(sfrdefs, sfrlen)

        sfrdefs = (
            gal.GAL_INAV_WORD_1,
            gal.GAL_INAV_WORD_2,
            gal.GAL_INAV_WORD_3,
            gal.GAL_INAV_WORD_4,
            gal.GAL_INAV_WORD_5,
            gal.GAL_INAV_WORD_6,
            gal.GAL_INAV_WORD_7,
            gal.GAL_INAV_WORD_8,
            gal.GAL_INAV_WORD_9,
            gal.GAL_INAV_WORD_10,
            gal.GAL_INAV_WORD_16,
        )
        sfrlen = 128
        self.scandefs(sfrdefs, sfrlen)

    def testBDSD1(self):

        sfrdefs = (
            bds.BDS_D1_SUBFRAME_1,
            bds.BDS_D1_SUBFRAME_2,
            bds.BDS_D1_SUBFRAME_3,
            bds.BDS_D1_SUBFRAME_5_P09,
            bds.BDS_D1_SUBFRAME_5_P10,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testBDSD2(self):

        sfrdefs = (
            bds.BDS_D2_SUBFRAME_1_P01,
            bds.BDS_D2_SUBFRAME_1_P02,
            bds.BDS_D2_SUBFRAME_1_P03,
            bds.BDS_D2_SUBFRAME_1_P04,
            bds.BDS_D2_SUBFRAME_1_P05,
            bds.BDS_D2_SUBFRAME_1_P06,
            bds.BDS_D2_SUBFRAME_1_P07,
            bds.BDS_D2_SUBFRAME_1_P08,
            bds.BDS_D2_SUBFRAME_1_P09,
            bds.BDS_D2_SUBFRAME_1_P10,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testGLOL1OF(self):

        sfrdefs = (
            glo.GLO_L1OF_SUBFRAME_1,
            glo.GLO_L1OF_SUBFRAME_2,
            glo.GLO_L1OF_SUBFRAME_3,
            glo.GLO_L1OF_SUBFRAME_4,
            glo.GLO_L1OF_SUBFRAME_5,
        )
        sfrlen = 85
        self.scandefs(sfrdefs, sfrlen)

    def testSBAL1CA(self):

        sfrdefs = (
            sba.SBA_L1CA_MT_9,
            sba.SBA_L1CA_MT_12,
            sba.SBA_L1CA_MT_17,
        )
        sfrlen = 250
        self.scandefs(sfrdefs, sfrlen)

    def testQZSLNAV(self):

        sfrdefs = (
            qzs.QZS_LNAV_SUBFRAME_1,
            qzs.QZS_LNAV_SUBFRAME_2,
            qzs.QZS_LNAV_SUBFRAME_3,
            qzs.QZS_LNAV_SUBFRAME_4_P56,
            qzs.QZS_LNAV_SUBFRAME_5_P56,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testQZSCNAV(self):
        sfrdefs = (
           qzs.QZS_CNAV_SUBFRAME_10,
            qzs.QZS_CNAV_SUBFRAME_11,
            qzs.QZS_CNAV_SUBFRAME_30,
            qzs.QZS_CNAV_SUBFRAME_32,
            qzs.QZS_CNAV_SUBFRAME_33,
        )
        sfrlen = 300
        self.scandefs(sfrdefs, sfrlen)

    def testQZSCNV2_2(self):
        sfrdefs = (
           qzs.QZS_CNV2_SUBFRAME_2,
        )
        sfrlen = 600
        self.scandefs(sfrdefs, sfrlen)

    def testQZSCNV2_3(self):
        sfrdefs = (
           qzs.QZS_CNV2_SUBFRAME_3_P1,
           qzs.QZS_CNV2_SUBFRAME_3_P2,
           qzs.QZS_CNV2_SUBFRAME_3_P61,
        )
        sfrlen = 274
        self.scandefs(sfrdefs, sfrlen)

    def testIRNLNAV(self):

        sfrdefs = (
            irn.IRN_LNAV_SUBFRAME_1,
            irn.IRN_LNAV_SUBFRAME_2,
            # irn.IRN_LNAV_SUBFRAME_3_P5,
            irn.IRN_LNAV_SUBFRAME_3_P9,
            irn.IRN_LNAV_SUBFRAME_3_P11,
        )
        sfrlen = 292
        self.scandefs(sfrdefs, sfrlen)
