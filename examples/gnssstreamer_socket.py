"""
pygnssutils - gnssstreamer_socket.py

This example illustrates how to use GNSSStreamer in
conjunction with a single-client TCP socket server as an
external output handler to stream binary GNSS data to a socket.

Usage:
 
python3 gnssstreamer_socket.py inport="/dev/ttyACM0" hostip="0.0.0.0" outport=50010

gnssdump can serve as a client:

> gnssdump socket=HOSTIP:OUTPORT

Example will terminate on client disconnection.

NB: this is just a simple illustration of how to use output handlers
with the GNSSStreamer class. The gnssserver CLI utility provides a
more comprehensive, multi-client socket server capability.

Created on 28 May 2022

@author: semuadmin
"""

import socket
from sys import argv

from pygnssutils import FORMAT_BINARY, GNSSStreamer


def main(**kwargs):
    """
    Main routine.
    """

    inport = kwargs.get("inport", "/dev/ttyACM0")
    hostip = kwargs.get("hostip", "0.0.0.0")
    outport = int(kwargs.get("outport", 50010))

    try:
        print(f"Opening TCP socket server {hostip}:{outport}, waiting for client...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((hostip, outport))
            sock.listen(1)
            conn, addr = sock.accept()
            with conn:
                print(f"Client {addr} has connected")
                print(f"Creating GNSSStreamer with serial port {inport}...")
                with GNSSStreamer(
                    port=inport, format=FORMAT_BINARY, outputhandler=conn
                ) as gns:
                    gns.run()
    except (
        ConnectionRefusedError,
        ConnectionAbortedError,
        ConnectionResetError,
        BrokenPipeError,
        TimeoutError,
    ):
        print(f"Client {addr} has disconnected")
    except KeyboardInterrupt:
        pass
    print("Streaming ended")


if __name__ == "__main__":

    main(**dict(arg.split("=") for arg in argv[1:]))
