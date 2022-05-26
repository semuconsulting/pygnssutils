"""
ubxsocket.py

A simple example implementation of a GNSS socket reader
using the GNSSReader iterator functions.
Parses UBX, NMEA and RTCM3 messages.

Designed to be used in conjunction with the
tcpserver_thread.py test harness, but can be
used with any accessible open TCP socket.

Press CTRL-C to terminate.

Created on 05 May 2022

@author: semuadmin
"""

import socket
from datetime import datetime
from pygnssutils import GNSSReader


def read(stream: socket.socket):
    """
    Reads and parses UBX, NMEA and RTCM3 message data from stream.
    """

    msgcount = 0
    start = datetime.now()

    gnr = GNSSReader(
        stream,
        protfilter=7,
    )
    try:
        for (_, parsed_data) in gnr.iterate():
            print(parsed_data)
            msgcount += 1
    except KeyboardInterrupt:
        dur = datetime.now() - start
        secs = dur.seconds + dur.microseconds / 1e6
        print("Session terminated by user")
        print(
            f"{msgcount:,d} messages read in {secs:.2f} seconds:",
            f"{msgcount/secs:.2f} msgs per second",
        )


if __name__ == "__main__":

    SERVER = "localhost"
    PORT = 50010

    print(f"Opening socket {SERVER}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER, PORT))
        read(sock)
