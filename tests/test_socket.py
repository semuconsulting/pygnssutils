"""
SocketWrapper method tests for pygnssutils

Created on 20 Aug 2024

*** NB: must be saved in UTF-8 format ***

@author: semuadmin
"""

# pylint: disable=line-too-long

import os
import sys
import unittest
from io import StringIO

from pyubx2 import ERR_LOG, UBXReader

from pygnssutils import (
    DEFAULT_BUFSIZE,
    ENCODE_CHUNKED,
    ENCODE_NONE,
    SocketWrapper,
)


class DummySocket:
    """
    Dummy socket class for testing SocketWrapper.
    """

    def __init__(self, filename: str, bufsize: int = DEFAULT_BUFSIZE):
        """
        Constructor.
        """

        self._buffer = b""
        with open(filename, "rb") as infile:
            while len(self._buffer) < bufsize:
                b = infile.read(16)
                if b == b"":
                    break
                self._buffer += b

    def recv(self, n: int) -> bytes:
        """
        Read n bytes from dummy socket.
        """

        b = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return b

    def send(self, data) -> int:
        """
        Send data to socket
        """

        print(f"data sent: {data}")
        return len(data)

    def sendall(self, data):
        """
        Send data to socket
        """

        print(f"data sent: {data}")
        return None

    def close():
        """
        Close socket
        """

        print("socket closed")


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

    def testnoencode(self):  # test socket read with no encoding
        EXPECTED_RESULT = "<RTCM(1020, DF002=1020, DF038=12, DF040=6, DF104=0, DF105=0, DF106=0, DF107=0, DF108=0, DF109=0, DF110=1, DF111=-0.7158985137939453, DF112=3457.43310546875, DF113=9.313225746154785e-10, DF114=2.4072818756103516, DF115=17375.4150390625, DF116=-9.313225746154785e-10, DF117=-2.1426753997802734, DF118=18386.60009765625, DF119=-2.7939677238464355e-09, DF120=0, DF121=1, DF122=0, DF123=0, DF124=-47014, DF125=7, DF126=0, DF127=0, DF128=1, DF129=232, DF130=1, DF131=1, DF132=231, DF133=2, DF134=0, DF135=1, DF136=0, DF001_7=0)>"

        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "ntrip_noencode.bin")
        dsock = DummySocket(filename)
        sock = SocketWrapper(dsock, encoding=ENCODE_NONE)
        ubr = UBXReader(sock, quitonerror=ERR_LOG)
        count = 0
        for raw, parsed in ubr:
            if parsed is not None:
                count += 1
        # print(parsed)
        # print(f"{count=}")
        self.assertEqual(str(parsed), EXPECTED_RESULT)
        self.assertEqual(count, 19)

    def testchunked(self):  # test socket read with chunking
        EXPECTED_RESULT = "<RTCM(1087, DF002=1087, DF003=25, DF416=6, DF034=38609000, DF393=1, DF409=0, DF001_7=0, DF411=1, DF412=0, DF417=0, DF418=0, DF394=6954086689753006080, NSat=8, DF395=1635778560, NSig=4, DF396=4294967295, NCell=32, PRN_01=002, PRN_02=003, PRN_03=009, PRN_04=016, PRN_05=017, PRN_06=018, PRN_07=019, PRN_08=024, DF397_01=66, DF397_02=73, DF397_03=74, DF397_04=75, DF397_05=66, DF397_06=65, DF397_07=75, DF397_08=79, DF419_01=3, DF419_02=12, DF419_03=5, DF419_04=6, DF419_05=11, DF419_06=4, DF419_07=10, DF419_08=9, DF398_01=0.7119140625, DF398_02=0.1103515625, DF398_03=0.068359375, DF398_04=0.6728515625, DF398_05=0.271484375, DF398_06=0.5830078125, DF398_07=0.41015625, DF398_08=0.9521484375, DF399_01=-150, DF399_02=-779, DF399_03=-1, DF399_04=640, DF399_05=328, DF399_06=-302, DF399_07=-659, DF399_08=696, CELLPRN_01=002, CELLSIG_01=1C, CELLPRN_02=002, CELLSIG_02=1P, CELLPRN_03=002, CELLSIG_03=2C, CELLPRN_04=002, CELLSIG_04=2P, CELLPRN_05=003, CELLSIG_05=1C, CELLPRN_06=003, CELLSIG_06=1P, CELLPRN_07=003, CELLSIG_07=2C, CELLPRN_08=003, CELLSIG_08=2P, CELLPRN_09=009, CELLSIG_09=1C, CELLPRN_10=009, CELLSIG_10=1P, CELLPRN_11=009, CELLSIG_11=2C, CELLPRN_12=009, CELLSIG_12=2P, CELLPRN_13=016, CELLSIG_13=1C, CELLPRN_14=016, CELLSIG_14=1P, CELLPRN_15=016, CELLSIG_15=2C, CELLPRN_16=016, CELLSIG_16=2P, CELLPRN_17=017, CELLSIG_17=1C, CELLPRN_18=017, CELLSIG_18=1P, CELLPRN_19=017, CELLSIG_19=2C, CELLPRN_20=017, CELLSIG_20=2P, CELLPRN_21=018, CELLSIG_21=1C, CELLPRN_22=018, CELLSIG_22=1P, CELLPRN_23=018, CELLSIG_23=2C, CELLPRN_24=018, CELLSIG_24=2P, CELLPRN_25=019, CELLSIG_25=1C, CELLPRN_26=019, CELLSIG_26=1P, CELLPRN_27=019, CELLSIG_27=2C, CELLPRN_28=019, CELLSIG_28=2P, CELLPRN_29=024, CELLSIG_29=1C, CELLPRN_30=024, CELLSIG_30=1P, CELLPRN_31=024, CELLSIG_31=2C, CELLPRN_32=024, CELLSIG_32=2P, DF405_01=0.0003364346921443939, DF405_02=0.00033187493681907654, DF405_03=0.000347210094332695, DF405_04=0.000347040593624115, DF405_05=0.00033445097506046295, DF405_06=0.0003337077796459198, DF405_07=0.0003527458757162094, DF405_08=0.00035262852907180786, DF405_09=6.475485861301422e-05, DF405_10=6.272271275520325e-05, DF405_11=7.64559954404831e-05, DF405_12=7.501058280467987e-05, DF405_13=7.7027827501297e-05, DF405_14=7.306598126888275e-05, DF405_15=9.336695075035095e-05, DF405_16=9.517930448055267e-05, DF405_17=-0.00010707974433898926, DF405_18=-0.00011054612696170807, DF405_19=-9.698234498500824e-05, DF405_20=-9.526126086711884e-05, DF405_21=0.00027042999863624573, DF405_22=0.00026645511388778687, DF405_23=0.0002793166786432266, DF405_24=0.000280553475022316, DF405_25=-0.00020200945436954498, DF405_26=-0.00020228326320648193, DF405_27=-0.00018753297626972198, DF405_28=-0.00018708966672420502, DF405_29=-0.0004944838583469391, DF405_30=-0.0004978980869054794, DF405_31=-0.00046785175800323486, DF405_32=-0.0004657786339521408, DF406_01=0.00033787358552217484, DF406_02=0.00032974593341350555, DF406_03=0.0003543947823345661, DF406_04=0.00032786931842565536, DF406_05=0.0003548162057995796, DF406_06=0.0003573126159608364, DF406_07=0.0004041716456413269, DF406_08=0.0004009706899523735, DF406_09=6.921309977769852e-05, DF406_10=5.048559978604317e-05, DF406_11=6.66244886815548e-05, DF406_12=7.463479414582253e-05, DF406_13=4.6292319893836975e-05, DF406_14=2.6946887373924255e-05, DF406_15=2.774316817522049e-05, DF406_16=3.576837480068207e-05, DF406_17=-9.721098467707634e-05, DF406_18=-9.533483535051346e-05, DF406_19=-0.00014329003170132637, DF406_20=-6.87548890709877e-05, DF406_21=0.0002894303761422634, DF406_22=0.0002850503660738468, DF406_23=0.0003277016803622246, DF406_24=0.00032046856358647346, DF406_25=-0.0002066437155008316, DF406_26=-0.00020103110000491142, DF406_27=-0.00017888005822896957, DF406_28=-0.00018529081717133522, DF406_29=-0.0005289451219141483, DF406_30=-0.0005283071659505367, DF406_31=-0.0005094804801046848, DF406_32=-0.0005126702599227428, DF407_01=590, DF407_02=590, DF407_03=590, DF407_04=590, DF407_05=552, DF407_06=552, DF407_07=552, DF407_08=552, DF407_09=582, DF407_10=582, DF407_11=582, DF407_12=582, DF407_13=617, DF407_14=617, DF407_15=617, DF407_16=617, DF407_17=628, DF407_18=631, DF407_19=631, DF407_20=631, DF407_21=599, DF407_22=599, DF407_23=599, DF407_24=599, DF407_25=537, DF407_26=537, DF407_27=537, DF407_28=537, DF407_29=647, DF407_30=647, DF407_31=647, DF407_32=647, DF420_01=0, DF420_02=0, DF420_03=0, DF420_04=0, DF420_05=0, DF420_06=0, DF420_07=0, DF420_08=0, DF420_09=0, DF420_10=0, DF420_11=0, DF420_12=0, DF420_13=0, DF420_14=0, DF420_15=0, DF420_16=0, DF420_17=0, DF420_18=0, DF420_19=0, DF420_20=0, DF420_21=0, DF420_22=0, DF420_23=0, DF420_24=0, DF420_25=0, DF420_26=0, DF420_27=0, DF420_28=0, DF420_29=0, DF420_30=0, DF420_31=0, DF420_32=0, DF408_01=53.1875, DF408_02=51.5, DF408_03=49.875, DF408_04=47.625, DF408_05=48.125, DF408_06=47.1875, DF408_07=45.8125, DF408_08=44.5, DF408_09=47.375, DF408_10=45.125, DF408_11=46.3125, DF408_12=43.375, DF408_13=42.5, DF408_14=41.3125, DF408_15=45.125, DF408_16=44.6875, DF408_17=53.8125, DF408_18=51.1875, DF408_19=50.5, DF408_20=48.3125, DF408_21=51.125, DF408_22=50.0, DF408_23=50.1875, DF408_24=48.375, DF408_25=36.6875, DF408_26=35.375, DF408_27=43.625, DF408_28=40.875, DF408_29=42.875, DF408_30=40.8125, DF408_31=38.875, DF408_32=37.625, DF404_01=0.3285, DF404_02=0.3285, DF404_03=0.3287, DF404_04=0.3287, DF404_05=-0.2391, DF404_06=-0.2391, DF404_07=-0.2393, DF404_08=-0.2393, DF404_09=0.2275, DF404_10=0.2275, DF404_11=0.22690000000000002, DF404_12=0.22690000000000002, DF404_13=-0.3136, DF404_14=-0.3136, DF404_15=-0.31320000000000003, DF404_16=-0.31320000000000003, DF404_17=0.3214, DF404_18=0.3214, DF404_19=0.32130000000000003, DF404_20=0.32130000000000003, DF404_21=0.1388, DF404_22=0.1388, DF404_23=0.1396, DF404_24=0.1396, DF404_25=-0.13240000000000002, DF404_26=-0.13240000000000002, DF404_27=-0.1327, DF404_28=-0.1327, DF404_29=-0.40990000000000004, DF404_30=-0.40990000000000004, DF404_31=-0.4101, DF404_32=-0.4101)>"
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "ntrip_chunked.bin")
        dsock = DummySocket(filename)
        sock = SocketWrapper(dsock, encoding=ENCODE_CHUNKED)
        ubr = UBXReader(sock, quitonerror=ERR_LOG)
        count = 0
        parsed = None
        for raw, parsed in ubr:
            if parsed is not None:
                count += 1
        # print(parsed)
        # print(f"{count=}")
        self.assertEqual(str(parsed), EXPECTED_RESULT)
        self.assertEqual(count, 15)

    def testsend(self):  # test socket send
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "ntrip_chunked.bin")
        self.catchio()
        dsock = DummySocket(filename)
        sock = SocketWrapper(dsock, encoding=ENCODE_CHUNKED)
        data = b"this is a test data sequence"
        n = sock.write(data)
        res = self.restoreio()
        self.assertEqual(n, len(data))
        self.assertEqual(res, "data sent: b'this is a test data sequence'")
