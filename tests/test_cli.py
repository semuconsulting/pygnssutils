"""
Helper, Property and Static method tests for pygnssutils

Created on 26 May 2022

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

from subprocess import run, PIPE
import sys
import unittest
from io import StringIO


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

    def teststreamer(self):
        res = run(["gnssstreamer", "-h"], stdout=PIPE, check=False)
        res = res.stdout.decode("utf-8")
        self.assertEqual(res[0:19], "usage: gnssstreamer")

    def testserver(self):
        res = run(["gnssserver", "-h"], stdout=PIPE, check=False)
        res = res.stdout.decode("utf-8")
        self.assertEqual(res[0:17], "usage: gnssserver")

    def testntripclient(self):
        res = run(["gnssntripclient", "-h"], stdout=PIPE, check=False)
        res = res.stdout.decode("utf-8")
        self.assertEqual(res[0:22], "usage: gnssntripclient")

    def testsmqttlient(self):
        res = run(["gnssmqttclient", "-h"], stdout=PIPE, check=False)
        res = res.stdout.decode("utf-8")
        self.assertEqual(res[0:21], "usage: gnssmqttclient")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
