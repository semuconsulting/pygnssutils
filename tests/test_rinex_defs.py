"""
Sanity check ICD payload definitions for RINEX conversion.

Check that individual bit offsets and lengths and total payload
length are consistent with ICD definition.

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

import unittest

from pygnssutils.rawnav import VALPREAMBLE
import pygnssutils.rinex_subframes_gps as gps
import pygnssutils.rinex_subframes_gal as gal
import pygnssutils.rinex_subframes_bds as bds

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

    def testGPSLNAVdefs(self):

        sfrdefs = (
            gps.GPS_LNAV_SUBFRAME_1,
            gps.GPS_LNAV_SUBFRAME_2,
            gps.GPS_LNAV_SUBFRAME_3,
            gps.GPS_LNAV_SUBFRAME_4_P18,
        )
        sfrlen = 300
        self.scandefs(sfrdefs,sfrlen)

    def testGPSCNAVdefs(self):
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
            gps.GPS_CNAV_SUBFRAME_40
        )
        sfrlen = 300
        self.scandefs(sfrdefs,sfrlen)

    def testGALFNAV(self):

        sfrdefs = (
            gal.GAL_FNAV_SUBFRAME_1,
            gal.GAL_FNAV_SUBFRAME_2,
            gal.GAL_FNAV_SUBFRAME_3,
            gal.GAL_FNAV_SUBFRAME_4,
            gal.GAL_FNAV_SUBFRAME_5,
            gal.GAL_FNAV_SUBFRAME_6
        )
        sfrlen = 244
        self.scandefs(sfrdefs,sfrlen)

    def testGALINAV(self):
    
        sfrdefs = (gal.GAL_INAV_SUBFRAME,)
        sfrlen = 256
        self.scandefs(sfrdefs,sfrlen)

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
            gal.GAL_INAV_WORD_16
        )
        sfrlen = 128
        self.scandefs(sfrdefs,sfrlen)

    def testBDSD1(self):

        sfrdefs = (
            bds.BDS_D1_SUBFRAME_1,
            bds.BDS_D1_SUBFRAME_2,
            bds.BDS_D1_SUBFRAME_3,
            bds.BDS_D1_SUBFRAME_5_P09,
            bds.BDS_D1_SUBFRAME_5_P10,
        )
        sfrlen = 300
        self.scandefs(sfrdefs,sfrlen)

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
        self.scandefs(sfrdefs,sfrlen)
