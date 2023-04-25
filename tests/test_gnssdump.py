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
from pygnssutils.gnssdump import (
    FORMAT_BINARY,
    FORMAT_HEX,
    FORMAT_HEXTABLE,
    FORMAT_JSON,
    FORMAT_PARSED,
    FORMAT_PARSEDSTRING,
    GNSSStreamer,
)


class GNSSDumpTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.mixedfile = os.path.join(os.path.dirname(__file__), "pygpsdata-MIXED3.log")
        self.outfilename = os.path.join(os.path.dirname(__file__), "outfile.log")

    def tearDown(self):
        try:
            os.remove(os.path.join(os.path.dirname(__file__), "outfile.log"))
        except FileNotFoundError:
            pass

    def testgnssdump_badparm1(self):
        with self.assertRaisesRegex(
            pge.ParameterError, "socket keyword must be in the format host:port"
        ):
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                socket="192.168.0.20",
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_badparm2(self):
        with self.assertRaisesRegex(
            pge.ParameterError,
            "Either stream, port, socket or filename keyword argument must be provided.",
        ):
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                protfilter=2,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_badparm3(self):
        with self.assertRaisesRegex(
            pge.ParameterError,
            "^Invalid input arguments*",
        ):
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                protfilter="X",
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

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

    def testgnssdump_filter(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(
            filename=self.mixedfile,
            format=FORMAT_PARSED,
            protfilter=2,
            msgfilter="NAV-PVT",
            limit=2,
        )
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(
            filename=self.mixedfile,
            format=FORMAT_PARSED,
            protfilter=2,
            msgfilter="NAV-PVT",
            limit=2,
            outputhandler="lambda msg: print(f'lat: {msg.lat}, lon: {msg.lon}')",
        )
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_errorhandler(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(
            filename=self.mixedfile,
            format=FORMAT_PARSED,
            limit=2,
            errorhandler="lambda err: print(f'error: {err}')",
        )
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outfile(self):
        saved_stdout = sys.stdout
        out = StringIO()
        sys.stdout = out
        gns = GNSSStreamer(
            filename=self.mixedfile,
            format=FORMAT_PARSED,
            outfile=self.outfilename,
        )
        gns.run()
        sys.stdout = saved_stdout
        print(f"output = {out.getvalue().strip()}")

    # def testgnssdump_outputhandler_file1(self):

    #     with open(self.outfile, "wb") as ofile:
    #         saved_stdout = sys.stdout
    #         out = StringIO()
    #         sys.stdout = out
    #         gns = GNSSStreamer(
    #             filename=self.mixedfile,
    #             format=FORMAT_PARSED,
    #             outputhandler=ofile,
    #         )
    #         gns.run()
    #         sys.stdout = saved_stdout
    #         print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler_file2(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                format=FORMAT_PARSEDSTRING,
                outputhandler=ofile,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler_file3(self):
        with open(self.outfilename, "wb") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                format=FORMAT_BINARY,
                outputhandler=ofile,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler_file4(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                format=FORMAT_HEX,
                outputhandler=ofile,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler_file5(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                format=FORMAT_HEXTABLE,
                outputhandler=ofile,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")

    def testgnssdump_outputhandler_file6(self):
        with open(self.outfilename, "w") as ofile:
            saved_stdout = sys.stdout
            out = StringIO()
            sys.stdout = out
            gns = GNSSStreamer(
                filename=self.mixedfile,
                format=FORMAT_JSON,
                outputhandler=ofile,
            )
            gns.run()
            sys.stdout = saved_stdout
            print(f"output = {out.getvalue().strip()}")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
