"""
Test GNSSStreamer class 

Created on 3 Oct 2020 

@author: semuadmin
"""

# pylint: disable=line-too-long, invalid-name, missing-docstring, no-member

import os
import sys
import unittest
from io import StringIO

from pygnssutils import exceptions as pge
from pygnssutils.gnssstreamer import (
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
    GNSSStreamer,
)


class gnssstreamerTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.mixedfile = os.path.join(os.path.dirname(__file__), "pygpsdata-MIXED3.log")
        self.outfilename = os.path.join(os.path.dirname(__file__), "outfile.log")

    def tearDown(self):
        try:
            os.remove(os.path.join(os.path.dirname(__file__), "outfile.log"))
        except FileNotFoundError:
            pass

    def testgnssstreamer_parsed(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_PARSED)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_parsedstr(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_PARSEDSTRING)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_binary(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_BINARY)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_hex(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_HEX)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_hextable(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_HEXTABLE)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_json(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(None, stream, format=FORMAT_JSON)
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_filter(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(
                None,
                stream,
                format=FORMAT_PARSED,
                protfilter=2,
                msgfilter="NAV-PVT",
                limit=2,
            )
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(
                None,
                stream,
                format=FORMAT_PARSED,
                protfilter=2,
                msgfilter="NAV-PVT",
                limit=2,
                output=eval("lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')"),
            )
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outfile(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        with open(self.mixedfile, "rb") as stream:
            gns = GNSSStreamer(
                None,
                stream,
                format=FORMAT_PARSED,
                output=self.outfilename,
            )
            gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler_file2(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            with open(self.mixedfile, "rb") as stream:
                gns = GNSSStreamer(
                    None,
                    stream,
                    format=FORMAT_PARSEDSTRING,
                    output=ofile,
                )
                gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler_file3(self):
        with open(self.outfilename, "wb") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            with open(self.mixedfile, "rb") as stream:
                gns = GNSSStreamer(
                    None,
                    stream,
                    format=FORMAT_BINARY,
                    output=ofile,
                )
                gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler_file4(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            with open(self.mixedfile, "rb") as stream:
                gns = GNSSStreamer(
                    None,
                    stream,
                    format=FORMAT_HEX,
                    output=ofile,
                )
                gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler_file5(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            with open(self.mixedfile, "rb") as stream:
                gns = GNSSStreamer(
                    None,
                    stream,
                    format=FORMAT_HEXTABLE,
                    output=ofile,
                )
                gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssstreamer_outputhandler_file6(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            with open(self.mixedfile, "rb") as stream:
                gns = GNSSStreamer(
                    None,
                    stream,
                    format=FORMAT_JSON,
                    output=ofile,
                )
                gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
