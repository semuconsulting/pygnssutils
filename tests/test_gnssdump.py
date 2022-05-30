"""
Test GNSSStreamer class 

Created on 3 Oct 2020 

@author: semuadmin
"""
# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import os
from io import StringIO
import sys
import unittest

from pygnssutils.gnssdump import (
    GNSSStreamer,
    FORMAT_PARSED,
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSEDSTRING,
)


class GNSSDumpTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.mixedfile = os.path.join(os.path.dirname(__file__), "pygpsdata-MIXED3.log")

    def tearDown(self):
        pass

    def testgnssdump_parsed(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(filename=self.mixedfile, format=FORMAT_PARSED)
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_parsedstr(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(filename=self.mixedfile, format=FORMAT_PARSEDSTRING)
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_binary(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(filename=self.mixedfile, format=FORMAT_BINARY)
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_hex(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(filename=self.mixedfile, format=FORMAT_HEX)
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_hextable(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(filename=self.mixedfile, format=FORMAT_HEXTABLE)
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_json(self):

        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with GNSSStreamer(filename=self.mixedfile, format=FORMAT_JSON) as gns:
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
