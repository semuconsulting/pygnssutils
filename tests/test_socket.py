"""
Socket reader tests for pysocketstream - uses dummy socket class
to achieve 99% test coverage of SocketStream.

Created on 11 May 2022

*** NB: must be saved in UTF-8 format ***

:author: semuadmin
"""

from socket import socket
import unittest
from pygnssutils.socket_stream import SocketStream


class DummySocket(socket):
    """
    Dummy socket class which simulates recv() method
    and TimeoutError.
    """

    def __init__(self, *args, **kwargs):

        self._timeout = False
        if "timeout" in kwargs:
            self._timeout = kwargs["timeout"]
            kwargs.pop("timeout")

        super().__init__(*args, **kwargs)

        pool = (
            b"\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00\x68\x00\x11\x40\xb6\xf3\x9d\x3f\xdb\x3d"
            + b"\xb5b\x10\x02\x1c\x00\x6d\xd8\x07\x00\x18\x20\x00\x00\xcd\x06\x00\x0e\xe4\xfe\xff\x0d\x03\xfa\xff\x05\x09\x0b\x00\x0c\x6d\xd8\x07\x00\xee\x51"
            + b"\xb5b\x10\x02\x18\x00\x72\xd8\x07\x00\x18\x18\x00\x00\x4b\xfd\xff\x10\x40\x02\x00\x11\x23\x28\x00\x12\x72\xd8\x07\x00\x03\x9c"
            + b"$GNDTM,W84,,0.0,N,0.0,E,0.0,W84*71\r\n"
            + b"$GNRMC,103607.00,A,5327.03942,N,10214.42462,W,0.046,,060321,,,A,V*0E\r\n"
            + b"$GPRTE,2,1,c,0,PBRCPK,PBRTO,PTELGR,PPLAND,PYAMBU,PPFAIR,PWARRN,PMORTL,PLISMR*73\r\n"
            + b"\xd3\x00\x13\x3E\xD7\xD3\x02\x02\x98\x0E\xDE\xEF\x34\xB4\xBD\x62\xAC\x09\x41\x98\x6F\x33\x36\x0B\x98"
            + b"\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7"
            + b"\xd3\x00\x12B\x91\x81\xc9\x84\x00\x04B\xb8\x88\x008\x80\t\xd0F\x00(\xf0kf"
        )
        self._stream = pool * round(4096 / len(pool))
        self._buffer = self._stream

    def recv(self, num: int) -> bytes:

        if self._timeout:
            raise TimeoutError
        if len(self._buffer) < num:
            self._buffer = self._buffer + self._stream
        buff = self._buffer[:num]
        self._buffer = self._buffer[num:]
        return buff


class SocketTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def tearDown(self):
        pass

    # *******************************************
    # Helper methods
    # *******************************************

    def testSocketStub(self):  # test for LF-delimited iterator
        EXPECTED_RESULTS = (
            b"\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00h\x00\x11@\xb6\xf3\x9d?\xdb=\xb5b\x10\x02\x1c\x00m\xd8\x07\x00\x18 \x00\x00\xcd\x06\x00\x0e\xe4\xfe\xff\r\x03\xfa\xff\x05\t\x0b\x00\x0cm\xd8\x07\x00\xeeQ\xb5b\x10\x02\x18\x00r\xd8\x07\x00\x18\x18\x00\x00K\xfd\xff\x10@\x02\x00\x11#(\x00\x12r\xd8\x07\x00\x03\x9c$GNDTM,W84,,0.0,N,0.0,E,0.0,W84*71\r\n",
            b"$GNRMC,103607.00,A,5327.03942,N,10214.42462,W,0.046,,060321,,,A,V*0E\r\n",
            b"$GPRTE,2,1,c,0,PBRCPK,PBRTO,PTELGR,PPLAND,PYAMBU,PPFAIR,PWARRN,PMORTL,PLISMR*73\r\n",
            b"\xd3\x00\x13>\xd7\xd3\x02\x02\x98\x0e\xde\xef4\xb4\xbdb\xac\tA\x98o36\x0b\x98\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7\xd3\x00\x12B\x91\x81\xc9\x84\x00\x04B\xb8\x88\x008\x80\t\xd0F\x00(\xf0kf\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00h\x00\x11@\xb6\xf3\x9d?\xdb=\xb5b\x10\x02\x1c\x00m\xd8\x07\x00\x18 \x00\x00\xcd\x06\x00\x0e\xe4\xfe\xff\r\x03\xfa\xff\x05\t\x0b\x00\x0cm\xd8\x07\x00\xeeQ\xb5b\x10\x02\x18\x00r\xd8\x07\x00\x18\x18\x00\x00K\xfd\xff\x10@\x02\x00\x11#(\x00\x12r\xd8\x07\x00\x03\x9c$GNDTM,W84,,0.0,N,0.0,E,0.0,W84*71\r\n",
            b"$GNRMC,103607.00,A,5327.03942,N,10214.42462,W,0.046,,060321,,,A,V*0E\r\n",
            b"$GPRTE,2,1,c,0,PBRCPK,PBRTO,PTELGR,PPLAND,PYAMBU,PPFAIR,PWARRN,PMORTL,PLISMR*73\r\n",
            b"\xd3\x00\x13>\xd7\xd3\x02\x02\x98\x0e\xde\xef4\xb4\xbdb\xac\tA\x98o36\x0b\x98\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7\xd3\x00\x12B\x91\x81\xc9\x84\x00\x04B\xb8\x88\x008\x80\t\xd0F\x00(\xf0kf\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00h\x00\x11@\xb6\xf3\x9d?\xdb=\xb5b\x10\x02\x1c\x00m\xd8\x07\x00\x18 \x00\x00\xcd\x06\x00\x0e\xe4\xfe\xff\r\x03\xfa\xff\x05\t\x0b\x00\x0cm\xd8\x07\x00\xeeQ\xb5b\x10\x02\x18\x00r\xd8\x07\x00\x18\x18\x00\x00K\xfd\xff\x10@\x02\x00\x11#(\x00\x12r\xd8\x07\x00\x03\x9c$GNDTM,W84,,0.0,N,0.0,E,0.0,W84*71\r\n",
            b"$GNRMC,103607.00,A,5327.03942,N,10214.42462,W,0.046,,060321,,,A,V*0E\r\n",
            b"$GPRTE,2,1,c,0,PBRCPK,PBRTO,PTELGR,PPLAND,PYAMBU,PPFAIR,PWARRN,PMORTL,PLISMR*73\r\n",
            b"\xd3\x00\x13>\xd7\xd3\x02\x02\x98\x0e\xde\xef4\xb4\xbdb\xac\tA\x98o36\x0b\x98\xd3\x00\x13>\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH Z\xd7\xf7\xd3\x00\x12B\x91\x81\xc9\x84\x00\x04B\xb8\x88\x008\x80\t\xd0F\x00(\xf0kf\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00h\x00\x11@\xb6\xf3\x9d?\xdb=\xb5b\x10\x02\x1c\x00m\xd8\x07\x00\x18 \x00\x00\xcd\x06\x00\x0e\xe4\xfe\xff\r\x03\xfa\xff\x05\t\x0b\x00\x0cm\xd8\x07\x00\xeeQ\xb5b\x10\x02\x18\x00r\xd8\x07\x00\x18\x18\x00\x00K\xfd\xff\x10@\x02\x00\x11#(\x00\x12r\xd8\x07\x00\x03\x9c$GNDTM,W84,,0.0,N,0.0,E,0.0,W84*71\r\n",
            b"$GNRMC,103607.00,A,5327.03942,N,10214.42462,W,0.046,,060321,,,A,V*0E\r\n",
            b"$GPRTE,2,1,c,0,PBRCPK,PBRTO,PTELGR,PPLAND,PYAMBU,PPFAIR,PWARRN,PMORTL,PLISMR*73\r\n",
        )
        raw = None
        stream = DummySocket()
        skr = SocketStream(stream, bufsize=1024)
        buff = skr.buffer  # test buffer getter method
        i = 0
        for data in skr:
            if data is not None:
                # print(data)
                self.assertEqual(data, EXPECTED_RESULTS[i])
                i += 1
                if i >= 12:
                    break
        self.assertEqual(i, 12)

    def testFixedSize(self):  # test for fixed byte length iterator
        EXPECTED_RESULTS = (
            b"\xb5b\x06\x8b\x0c\x00\x00\x00\x00\x00",
            b"h\x00\x11@\xb6\xf3\x9d?\xdb=",
            b"\xb5b\x10\x02\x1c\x00m\xd8\x07\x00",
        )
        raw = None
        stream = DummySocket()
        skr = SocketStream(stream, itersize=10)
        i = 0
        for data in skr:
            # print(data)
            self.assertEqual(data, EXPECTED_RESULTS[i])
            i += 1
            if i >= 3:
                break
        self.assertEqual(i, 3)

    def testSocketError(self):  # test for simulated socket timeout

        raw = None
        stream = DummySocket(timeout=True)
        skr = SocketStream(stream)
        i = 0
        for data in skr:
            i += 1
            if i >= 12:
                break
        self.assertEqual(i, 0)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
