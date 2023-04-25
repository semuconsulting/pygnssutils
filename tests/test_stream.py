"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

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

    def testnofilter(self):  # test gnssdump with no message filter
        EXPECTED_OUTPUT1 = (
            "Streaming terminated, 5,941 messages processed with 0 errors."
        )
        EXPECTED_OUTPUT2 = "Messages output:   {'1005': 158, '1077': 158, '1087': 158, '1097': 158, '1127': 158, '1230': 158, '4072': 158, 'GAGSV': 628, 'GBGSV': 720, 'GLGSV': 628, 'GNGGA': 157, 'GNGLL': 158, 'GNGSA': 785, 'GNRMC': 157, 'GNVTG': 157, 'GPGSV': 1114, 'GQGSV': 157, 'NAV-PVT': 158, 'NAV-SVIN': 16}"
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
        self.catchio()
        gns = GNSSStreamer(filename=filename, verbosity=2)
        gns.run()
        output = self.restoreio().split("\n")
        out1 = output[-1][28:]
        out2 = output[-2][28:]
        self.assertEqual(out1, EXPECTED_OUTPUT1)
        self.assertEqual(out2, EXPECTED_OUTPUT2)
        # print(out1, out2)

    def testfilter(self):  # test gnssdump with message filter
        EXPECTED_OUTPUT1 = "Streaming terminated, 316 messages processed with 0 errors."
        EXPECTED_OUTPUT2 = "Messages output:   {'1077': 158, '1087': 158}"
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
        self.catchio()
        gns = GNSSStreamer(filename=filename, verbosity=2, msgfilter="1077,1087")
        gns.run()
        output = self.restoreio().split("\n")
        out1 = output[-1][28:]
        out2 = output[-2][28:]
        self.assertEqual(out1, EXPECTED_OUTPUT1)
        self.assertEqual(out2, EXPECTED_OUTPUT2)
        # print(out1, out2)

    def testfilterperiod(self):  # test gnssdump with message period filter
        EXPECTED_OUTPUT1 = (
            r"Streaming terminated, [0-9][0-9][0-9] messages processed with 0 errors."
        )
        EXPECTED_OUTPUT2 = r"Messages output:   {'1077': [0-9]?[0-9], '1087': [0-9]?[0-9], '1097': [0-9][0-9][0-9]}"
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "pygpsdata-rtcm3.log")
        self.catchio()
        gns = GNSSStreamer(
            filename=filename, verbosity=2, msgfilter="1077(.05),1087(.05),1097"
        )
        gns.run()
        output = self.restoreio().split("\n")
        out1 = output[-1][28:]
        out2 = output[-2][28:]
        self.assertRegex(out1, EXPECTED_OUTPUT1)
        self.assertRegex(out2, EXPECTED_OUTPUT2)
        # print(out1, out2)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
