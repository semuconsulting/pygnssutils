"""
gnssserver.py

This is a simple implementation of a TCP Socket
Server or NTRIP Server which reads the binary data stream from
a connected GNSS receiver and broadcasts the data to any
TCP socket or NTRIP client running on a local or remote
machine (assuming firewalls allow the hostip:outport).

Settings can be entered as optional command line arguments, e.g.
> python3 gnssserver.py hostip=192.168.0.20 inport="/dev/tty.usbmodem14101" outport=6000
Any arguments not provided will be defaulted;
default hostip = 0.0.0.0 (i.e. binds to all available host IP address)
default inport = "/dev/ttyACM0",
default outport = 50010.

Press CTRL-C to stop the server.

In the default configuration ('format=FORMAT_BINARY'), the clients
must be capable of parsing binary GNSS data.
Suitable clients include (but are not limited to):
1) pyubx2's gnssdump cli utility invoked thus:
   > gnssdump socket=hostip:outport
2) The PyGPSClient GUI application, invoked thus:
   > pygpsclient

To run in NTRIP Server mode, set 'ntripmode=1'. For this mode
to function properly, the receiver must be an RTK-capable receiver
(e.g. u-blox ZED-F9P) running in "Base Station" mode (either
SURVEY_IN or FIXED). The clients must be NTRIP clients (e.g.
PyGPSClient's NTRIP Client facility).
NTRIP server login credentials are set via environment
variables PYGPSCLIENT_USER and PYGPSCLIENT_PASSWORD.


The example essentially runs two (pseudo-)concurrent threads:
- an input thread based on the pyubx2cli.gnssdump.GNSSStreamer
  class from the pyubx2cli gnssdump utility, using a message
  Queue as an external protocol handler.
- an output thread based on the pygpsclient.socket_server
  SocketServer and ClientHandler classes,
  originally designed for the PyGPSClient GUI application.
  (a local copy of the classes is in /examples/socket_server.py
  for those that don't have PYGPSClient installed)

Created on 24 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=too-many-arguments

import sys
from time import sleep
from queue import Queue
from threading import Thread
from io import TextIOWrapper
from pygnssutils.globals import (
    FORMAT_BINARY,
    VERBOSITY_MEDIUM,
    VERBOSITY_LOW,
    CONNECTED,
)
from pygnssutils.gnssdump import GNSSStreamer
from pygnssutils.socket_server import SocketServer, ClientHandler
from pygnssutils.helpstrings import GNSSSERVER_HELP


class GNSSSocketServer:
    """
    GNSS Socket Server Class.
    """

    # pylint: disable=line-too-long

    def __init__(self, **kwargs):
        """
        Constructor.

        Example of usage:

        gnssserver inport=COM3 hostip=192.168.0.20 outport=50010

        :param str inport: (kwarg) serial port name
        :param int baudrate: (kwarg) serial baud rate (9600)
        :param int timeout: (kwarg) serial timeout in seconds (3)
        :param int hostip: (kwarg) host ip address (0.0.0.0)
        :param str outport: (kwarg) TCP port (50010)
        :param int ntripmode: (kwarg) 0 = socket server, 1 - NTRIP server (0)
        :param int validate: (kwarg) 1 = validate checksums, 0 = do not validate (1)
        :param int parsebitfield: (kwarg) 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: (kwarg) output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, 16 = parsed as string (1) (can be OR'd)
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)
        :param str msgfilter: (kwarg) comma-separated string of message identities e.g. 'NAV-PVT,GNGSA' (None)
        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        :param int verbosity: (kwarg) log message verbosity 0 = low, 1 = medium, 3 = high (1)
        """

        try:

            self._kwargs = kwargs
            # overrideable command line arguments..
            # 0 = TCP Socket Server mode, 1 = NTRIP Server mode
            self._kwargs["ntripmode"] = int(kwargs.get("ntripmode", 0))
            # 0.0.0.0 binds to all host IP addresses
            self._kwargs["hostip"] = kwargs.get("hostip", "0.0.0.0")
            # amend default as required
            self._kwargs["port"] = kwargs.get("inport", "/dev/ttyACM0")
            self._kwargs["outport"] = int(kwargs.get("outport", 50010))
            # 5 is an arbitrary limit; could be significantly higher
            self._kwargs["maxclients"] = int(kwargs.get("maxclients", 5))
            self._kwargs["format"] = int(kwargs.get("format", FORMAT_BINARY))
            self._kwargs["verbosity"] = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
            # required fixed arguments...
            msgqueue = Queue()
            self._kwargs["ubxhandler"] = msgqueue
            self._kwargs["nmeahandler"] = msgqueue
            self._kwargs["rtcmhandler"] = msgqueue
            self._socket_server = None
            self._in_thread = None
            self._out_thread = None
            self._clients = 0
            self._validargs = True

        except ValueError as err:
            self.do_log(f"Invalid input arguments {kwargs}\n{err}", VERBOSITY_MEDIUM)
            self._validargs = False

    def run(self) -> int:
        """
        Run server.
        """

        if self._validargs:
            self.do_log("Starting server (type CTRL-C to stop)...", VERBOSITY_MEDIUM)
            self._in_thread = self.start_input_thread(**self._kwargs)
            sleep(0.5)
            if self._in_thread.is_alive():
                self._out_thread = self.start_output_thread(**self._kwargs)
                sleep(0.5)
                if self._out_thread.is_alive():
                    return 1
        return 0

    def stop(self):
        """
        Shutdown server.
        """

        self.do_log("\nStopping server...", VERBOSITY_MEDIUM)
        if self._socket_server is not None:
            self._socket_server.shutdown()

    def start_input_thread(self, **kwargs) -> Thread:
        """
        Start input (read) thread.

        :pararm dict kwargs: optional keyword args
        :return: thread
        :rtype: Thread
        """

        self.do_log(
            f"Starting input thread, reading from {kwargs['port']}...", VERBOSITY_MEDIUM
        )
        thread = Thread(
            target=self._input_thread,
            args=(kwargs,),
            daemon=True,
        )
        thread.start()
        return thread

    def start_output_thread(self, **kwargs) -> Thread:
        """
        Start output (socket) thread.

        :pararm dict kwargs: optional keyword args
        :return: thread
        :rtype: Thread
        """

        self.do_log(
            f"Starting output thread, broadcasting on {kwargs['hostip']}:{kwargs['outport']}...",
            VERBOSITY_MEDIUM,
        )
        thread = Thread(
            target=self._output_thread,
            args=(
                self,
                kwargs,
            ),
            daemon=True,
        )
        thread.start()
        return thread

    def _input_thread(self, kwargs):
        """
        THREADED

        Input (Serial reader) thread.
        """
        # pylint: disable=no-self-use

        # FYI: any of the permissible gnssdump kwargs could be passed here
        # from command line arguments to configure the data that is
        # actually broadcast to the clients, e.g. you could set
        # 'protfilter=4' to only output RTCM data, or 'msgfilter=NAV-PVT'
        # to only output UBX NAV-PVT messages.
        # type gnssdump -h for help.

        gns = GNSSStreamer(**kwargs)
        gns.run()

    def _output_thread(self, app: object, kwargs):
        """
        THREADED

        Output (socket server) thread.
        """

        try:
            with SocketServer(
                app,
                kwargs["ntripmode"],
                kwargs["maxclients"],
                kwargs["ubxhandler"],
                (kwargs["hostip"], kwargs["outport"]),
                ClientHandler,
            ) as self._socket_server:
                self._socket_server.serve_forever()
        except OSError as err:
            self.do_log(f"Error starting socket server {err}", VERBOSITY_MEDIUM)

    def notify_client(self, address: tuple, status: int):
        """
        Receives and logs notification of client connection or disconnection
        and increments total number of connected clients.

        :param tuple address: client address
        :param int status: 0 = disconnected, 1 = connected
        """

        if status == CONNECTED:
            pre = ""
            self._clients += 1
        else:
            pre = "dis"
            self._clients -= 1
        self.do_log(
            f"Client {address} has {pre}connected. Total clients: {self._clients}",
            VERBOSITY_MEDIUM,
        )

    def do_log(
        self,
        message: str,
        loglevel: int,
        logfile: TextIOWrapper = "",
    ):
        """
        Write output according to verbosity and logfile settings.

        :param str message: message to log
        :param int loglevel: log level for this message (0,1,2)
        :param TextIOWrapper logfile: name of open text file
        """

        if self._kwargs["verbosity"] & loglevel:
            if logfile == "":
                print(message)
            else:
                print(message, file=logfile)


def main():
    """
    CLI Entry point.
    """

    if len(sys.argv) > 1:
        if sys.argv[1] in {"-h", "--h", "help", "-help", "--help", "-H"}:
            print(GNSSSERVER_HELP)
            sys.exit()

    try:

        server = GNSSSocketServer(**dict(arg.split("=") for arg in sys.argv[1:]))
        goodtogo = server.run()

        while goodtogo:  # run until user presses CTRL-C
            sleep(1)

    except KeyboardInterrupt:
        server.stop()
        print("Terminated by user")


if __name__ == "__main__":

    main()
