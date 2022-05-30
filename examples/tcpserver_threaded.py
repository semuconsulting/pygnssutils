"""
pygnssutils - FOR TESTING ONLY

Threaded TCP socket server test harness.

Sends arbitrary NMEA, UBX & RTCM3 messages to connected clients.

Created on 26 Apr 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""

from socketserver import ThreadingTCPServer, StreamRequestHandler
import random

# from serial import Serial
from datetime import datetime, timezone

from time import sleep
from pyubx2 import UBXMessage, GET
from pynmeagps import NMEAMessage
from pyrtcm import RTCMMessage

# amend as required...
BAUD = 9600
TIMEOUT = 3
HOST = "localhost"
PORT = 50010
DELAY = 0.25


class TestServer(StreamRequestHandler):
    """
    Threaded TCP client connection handler class.
    """

    @staticmethod
    def create_unknownubx_msg() -> UBXMessage:
        """
        Create unknown UBX message to test error handling.
        """

        return b"\xb5b\x06\x99\x08\x00\xf0\x01\x00\x01\x00\x01\x00\x00\x9a\xba"

    @staticmethod
    def create_ubx_msg() -> UBXMessage:
        """
        Create arbitrary UBX message.
        """
        # pylint: disable=invalid-name

        dat = datetime.now(timezone.utc)
        msg = UBXMessage(
            "NAV",
            "NAV-PVT",
            GET,
            year=dat.year,
            month=dat.month,
            day=dat.day,
            hour=dat.hour,
            min=dat.minute,
            second=dat.second,
            validDate=1,
            validTime=1,
            fixType=3,
            lat=random.uniform(-90.0, 90.0),
            lon=random.uniform(-180.0, 180.0),
            hMSL=random.randint(0, 100000),
            numSV=random.randint(1, 26),
        )
        return msg.serialize()

    @staticmethod
    def create_nmea_msg() -> NMEAMessage:
        """
        Create arbitrary NMEA message.
        """
        # pylint: disable=invalid-name

        lat = random.uniform(-90.0, 90.0)
        lon = random.uniform(-180.0, 180.0)
        msg = NMEAMessage(
            "GN",
            "GLL",
            GET,
            lat=lat,
            lon=lon,
            NS="N" if lat > 0 else "S",
            EW="E" if lon > 0 else "W",
            status="A",
            posMode="A",
        )
        return msg.serialize()

    @staticmethod
    def create_rtcm3_msg() -> RTCMMessage:
        """
        Create arbitrary RTCM3 message.
        """
        # pylint: disable=invalid-name

        msg = RTCMMessage(
            payload=b">\xd0\x00\x03\x8aX\xd9I<\x87/4\x10\x9d\x07\xd6\xafH "
        )
        return msg.serialize()

    def handle(self):
        """
        Handle client connection.
        """

        print(f"Client connected: {self.client_address[0]}:{self.client_address[1]}")
        while True:
            try:
                # put multiple random msgs on buffer, mixed in with junk
                # to exercise the clients' parsing routine
                data = bytearray()
                for _ in range(random.randint(1, 5)):
                    rdm = random.randint(1, 7)
                    if rdm in (1, 2, 3):
                        data += self.create_nmea_msg() + b"\x04\x05\x06"
                    elif rdm == 4:
                        data += self.create_rtcm3_msg() + b"\x07\x08\x09"
                    elif rdm == 5:
                        data += self.create_unknownubx_msg() + b"\x03\x04\x05"
                    else:
                        data += self.create_ubx_msg() + b"\x01\x02\x03"
                # data = self.create_UBX_msg()
                if data is not None:
                    self.wfile.write(data)
                    self.wfile.flush()
                sleep(DELAY)
            except (ConnectionAbortedError, BrokenPipeError):
                print(
                    f"Client disconnected: {self.client_address[0]}:{self.client_address[1]}"
                )
                break


if __name__ == "__main__":

    print(f"Creating TCP server on {HOST}:{PORT}")
    server = ThreadingTCPServer((HOST, PORT), TestServer)

    print("Starting TCP server, waiting for client connections...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("TCP server terminated by user")
