"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import logging
import os
import sys
import unittest
from io import StringIO

from pygnssutils import GNSSStreamer


class StreamTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    def catchio(self):
        """
        Capture stdout as string.
        """

        self._saved_stdout = sys.stdout
        self._strout = StringIO()
        sys.stdout = self._strout

    def restoreio(self) -> str:
        """
        Return captured output and restore stdout.
        """

        sys.stdout = self._saved_stdout
        return self._strout.getvalue().strip()

    # def testnofilter(self):  # test gnssstreamer with no message filter
    #     EXPECTED_OUTPUT1 = "INFO:pygnssutils.gnssstreamer:Streaming terminated, 5,941 messages processed with 0 errors."
    #     EXPECTED_OUTPUT2 = "INFO:pygnssutils.gnssstreamer:Messages output:   {'1005': 158, '1077': 158, '1087': 158, '1097': 158, '1127': 158, '1230': 158, '4072': 158, 'GAGSV': 628, 'GBGSV': 720, 'GLGSV': 628, 'GNGGA': 157, 'GNGLL': 158, 'GNGSA': 785, 'GNRMC': 157, 'GNVTG': 157, 'GPGSV': 1114, 'GQGSV': 157, 'NAV-PVT': 158, 'NAV-SVIN': 16}"
    #     self.catchio()
    #     with self.assertLogs(level=logging.INFO) as log:
    #         dirname = os.path.dirname(__file__)
    #         filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
    #         gns = GNSSStreamer(filename=filename, verbosity=2)
    #         gns.run()
    #     # print(log.output[-1], log.output[-2])
    #     self.assertEqual(log.output[-1], EXPECTED_OUTPUT1)
    #     self.assertEqual(log.output[-2], EXPECTED_OUTPUT2)
    #     self.restoreio()

    # def testfilter(self):  # test gnssstreamer with message filter
    #     EXPECTED_OUTPUT1 = "INFO:pygnssutils.gnssstreamer:Streaming terminated, 316 messages processed with 0 errors."
    #     EXPECTED_OUTPUT2 = "INFO:pygnssutils.gnssstreamer:Messages output:   {'1077': 158, '1087': 158}"
    #     self.catchio()
    #     with self.assertLogs(level=logging.INFO) as log:
    #         dirname = os.path.dirname(__file__)
    #         filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
    #         gns = GNSSStreamer(filename=filename, verbosity=2, msgfilter="1077,1087")
    #         gns.run()
    #     self.assertEqual(log.output[-1], EXPECTED_OUTPUT1)
    #     self.assertEqual(log.output[-2], EXPECTED_OUTPUT2)
    #     self.restoreio()

    # def testfilterperiod(self):  # test gnssstreamer with message period filter
    #     EXPECTED_OUTPUT1 = r"INFO:pygnssutils.gnssstreamer:Streaming terminated, [0-9][0-9][0-9] messages processed with 0 errors."
    #     EXPECTED_OUTPUT2 = r"INFO:pygnssutils.gnssstreamer:Messages output:   {'1077': [0-9]?[0-9], '1087': [0-9]?[0-9], '1097': [0-9][0-9][0-9]}"
    #     self.catchio()
    #     with self.assertLogs(level=logging.INFO) as log:
    #         dirname = os.path.dirname(__file__)
    #         filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
    #         gns = GNSSStreamer(
    #             filename=filename, verbosity=2, msgfilter="1077(.05),1087(.05),1097"
    #         )
    #         gns.run()
    #     self.assertRegex(log.output[-1], EXPECTED_OUTPUT1)
    #     self.assertRegex(log.output[-2], EXPECTED_OUTPUT2)
    #     self.restoreio()


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
