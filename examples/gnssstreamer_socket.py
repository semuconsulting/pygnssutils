"""
pygnssutils - gnssstreamer_socket.py

This example illustrates how to use GNSSStreamer in
conjunction with a single-client TCP socket server as an
external output handler to stream binary GNSS data to a socket.

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
from pygnssutils import GNSSStreamer, FORMAT_BINARY

# amend as required...
INPORT = "/dev/tty.usbmodem141101"
HOSTIP = "0.0.0.0"
OUTPORT = 50010

try:
    print(f"Opening TCP socket server {HOSTIP}:{OUTPORT}, waiting for client...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOSTIP, OUTPORT))
        sock.listen(1)
        conn, addr = sock.accept()
        with conn:
            print(f"Client {addr} has connected")
            print(f"Creating GNSSStreamer with serial port {INPORT}...")
            with GNSSStreamer(
                port=INPORT, format=FORMAT_BINARY, allhandler=conn
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
