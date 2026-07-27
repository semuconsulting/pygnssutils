"""
Sanity check ICD payload definitions for RINEX conversion.

Check that individual bit lengths and total payload
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
from pygnssutils.rawnav import SUBFRAMELENGTH


class StaticTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def scandefs(self, sfrdefs):
        for dic in sfrdefs:
            offset = 0
            totlen = 0
            sfrlen = 0
            for key, vals in dic.items():
                if key == SUBFRAMELENGTH:
                    sfrlen = vals
                    continue
                self.assertGreater(sfrlen,0)
                len, typ, sca = vals
                # print(f'"{key}": (len},{typ},{sca}),')
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
        self.scandefs(sfrdefs)

    def testGPSCNAV(self):
        sfrdefs = (
            gps.GPS_CNAV_SUBFRAME_10,
            gps.GPS_CNAV_SUBFRAME_11,
            #gps.GPS_CNAV_SUBFRAME_12,
            #gps.GPS_CNAV_SUBFRAME_13,
            #gps.GPS_CNAV_SUBFRAME_14,
            gps.GPS_CNAV_SUBFRAME_15,
            gps.GPS_CNAV_SUBFRAME_30,
            #gps.GPS_CNAV_SUBFRAME_31,
            gps.GPS_CNAV_SUBFRAME_32,
            gps.GPS_CNAV_SUBFRAME_33,
            gps.GPS_CNAV_SUBFRAME_34,
            gps.GPS_CNAV_SUBFRAME_35,
            gps.GPS_CNAV_SUBFRAME_36,
            gps.GPS_CNAV_SUBFRAME_37,
            gps.GPS_CNAV_SUBFRAME_40,
        )
        self.scandefs(sfrdefs)

    def testGALFNAV(self):

        sfrdefs = (
            gal.GAL_FNAV_SUBFRAME_1,
            gal.GAL_FNAV_SUBFRAME_2,
            gal.GAL_FNAV_SUBFRAME_3,
            gal.GAL_FNAV_SUBFRAME_4,
            gal.GAL_FNAV_SUBFRAME_5,
            gal.GAL_FNAV_SUBFRAME_6,
        )
        self.scandefs(sfrdefs)

    def testGALINAV(self):

        sfrdefs = (gal.GAL_INAV_SUBFRAME,)
        self.scandefs(sfrdefs)

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
        self.scandefs(sfrdefs)

    def testBDSD1(self):

        sfrdefs = (
            bds.BDS_D1_SUBFRAME_1,
            bds.BDS_D1_SUBFRAME_2,
            bds.BDS_D1_SUBFRAME_3,
            bds.BDS_D1_SUBFRAME_5_P09,
            bds.BDS_D1_SUBFRAME_5_P10,
        )
        self.scandefs(sfrdefs)

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
        self.scandefs(sfrdefs)

    def testGLOL1OF(self):

        sfrdefs = (
            glo.GLO_L1OF_SUBFRAME_1,
            glo.GLO_L1OF_SUBFRAME_2,
            glo.GLO_L1OF_SUBFRAME_3,
            glo.GLO_L1OF_SUBFRAME_4,
            glo.GLO_L1OF_SUBFRAME_5,
            glo.GLO_L1OF_SUBFRAME_6,
            glo.GLO_L1OF_SUBFRAME_7,
            glo.GLO_L1OF_SUBFRAME_8,
            glo.GLO_L1OF_SUBFRAME_9,
            glo.GLO_L1OF_SUBFRAME_10,
            glo.GLO_L1OF_SUBFRAME_11,
            glo.GLO_L1OF_SUBFRAME_12,
            glo.GLO_L1OF_SUBFRAME_13,
            glo.GLO_L1OF_SUBFRAME_14,
            glo.GLO_L1OF_SUBFRAME_15,
            glo.GLO_L1OF_SUBFRAME_14_F5,
            glo.GLO_L1OF_SUBFRAME_15_F5,
        )
        self.scandefs(sfrdefs)

    def testSBAL1CA(self):

        sfrdefs = (
            # sba.SBA_L1CA_MT_0,
            sba.SBA_L1CA_MT_1,
            # sba.SBA_L1CA_MT_2,
            # sba.SBA_L1CA_MT_3,
            # sba.SBA_L1CA_MT_4,
            # sba.SBA_L1CA_MT_5,
            # sba.SBA_L1CA_MT_6,
            # sba.SBA_L1CA_MT_7,
            sba.SBA_L1CA_MT_9,
            sba.SBA_L1CA_MT_10,
            sba.SBA_L1CA_MT_12,
            # sba.SBA_L1CA_MT_17,
            sba.SBA_L1CA_MT_18,
            # sba.SBA_L1CA_MT_24,
            # sba.SBA_L1CA_MT_25,
            # sba.SBA_L1CA_MT_26,
            # sba.SBA_L1CA_MT_27,
            # sba.SBA_L1CA_MT_28,
        )
        self.scandefs(sfrdefs)

    def testQZSLNAV(self):

        sfrdefs = (
            qzs.QZS_LNAV_SUBFRAME_1,
            qzs.QZS_LNAV_SUBFRAME_2,
            qzs.QZS_LNAV_SUBFRAME_3,
            qzs.QZS_LNAV_SUBFRAME_4_P56,
            qzs.QZS_LNAV_SUBFRAME_5_P56,
        )
        self.scandefs(sfrdefs)

    def testQZSCNAV(self):
        sfrdefs = (
           qzs.QZS_CNAV_SUBFRAME_10,
           qzs.QZS_CNAV_SUBFRAME_10,
            qzs.QZS_CNAV_SUBFRAME_11,
            qzs.QZS_CNAV_SUBFRAME_30,
            qzs.QZS_CNAV_SUBFRAME_32,
            qzs.QZS_CNAV_SUBFRAME_33,
        )
        self.scandefs(sfrdefs)

    def testQZSCNV2_2(self):
        sfrdefs = (
           qzs.QZS_CNV2_SUBFRAME_2,
        )
        self.scandefs(sfrdefs)

    def testQZSCNV2_3(self):
        sfrdefs = (
           qzs.QZS_CNV2_SUBFRAME_3_P1,
           qzs.QZS_CNV2_SUBFRAME_3_P2,
           qzs.QZS_CNV2_SUBFRAME_3_P61,
        )
        self.scandefs(sfrdefs)

    def testIRNLNAV(self):

        sfrdefs = (
            irn.IRN_LNAV_SUBFRAME_1,
            irn.IRN_LNAV_SUBFRAME_2,
            # irn.IRN_LNAV_SUBFRAME_3_P5,
            irn.IRN_LNAV_SUBFRAME_3_P9,
            irn.IRN_LNAV_SUBFRAME_3_P11,
        )
        self.scandefs(sfrdefs)
