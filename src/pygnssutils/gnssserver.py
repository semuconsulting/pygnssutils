"""
gnssserver.py

This is a simple implementation of a TCP Socket
Server or NTRIP Server which reads the binary data stream from
a connected GNSS receiver and broadcasts the data to any
TCP socket or NTRIP client running on a local or remote
machine.

Created on 24 May 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=too-many-arguments

import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from datetime import datetime
from queue import Queue
from threading import Thread
from time import sleep

from pygnssutils._version import __version__ as VERSION
from pygnssutils.globals import (
    CONNECTED,
    EPILOG,
    FORMAT_BINARY,
    LOGLIMIT,
    OUTPORT,
    OUTPORT_NTRIP,
    VERBOSITY_LOW,
    VERBOSITY_MEDIUM,
)
from pygnssutils.gnssdump import GNSSStreamer
from pygnssutils.helpers import format_conn, ipprot2int
from pygnssutils.socket_server import ClientHandler, SocketServer


class GNSSSocketServer:
    """
    GNSS Socket Server Class.
    """

    # pylint: disable=line-too-long

    def __init__(self, **kwargs):
        """
        Context manager constructor.

        Example of usage:

        gnssserver inport=COM3 hostip=192.168.0.20 outport=50010 ntripmode=0

        :param object app: application from which this class is invoked (None)
        :param str inport: (kwarg) input serial port name (None)
        :param str socket: (kwarg) input socket host:port
        :param int baudrate: (kwarg) serial baud rate (9600)
        :param int timeout: (kwarg) serial timeout in seconds (3)
        :param str ipprot: (kwarg) IP protocol IPv4/IPv6 ("IPv4")
        :param int hostip: (kwarg) host ip address (0.0.0.0)
        :param str outport: (kwarg) TCP port (50010, or 2101 in NTRIP mode)
        :param int maxclients: (kwarg) maximum number of connected clients (5)
        :param int ntripmode: (kwarg) 0 = socket server, 1 - NTRIP server (0)
        :param int validate: (kwarg) 1 = validate checksums, 0 = do not validate (1)
        :param int parsebitfield: (kwarg) 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: (kwarg) output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, 16 = parsed as string (1), 32 = JSON (can be OR'd)
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)
        :param str msgfilter: (kwarg) comma-separated string of message identities e.g. 'NAV-PVT,GNGSA' (None)
        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        :param int verbosity: (kwarg) log message verbosity 0 = low, 1 = medium, 3 = high (1)
        :param int logtofile: (kwarg) 0 = log to stdout, 1 = log to file '/logpath/gnssserver-timestamp.log' (0)
        :param int logpath: {kwarg} fully qualified path to logfile folder (".")
        """

        try:
            self._kwargs = kwargs
            # overrideable command line arguments..
            # 0 = TCP Socket Server mode, 1 = NTRIP Server mode
            self._kwargs["ntripmode"] = int(kwargs.get("ntripmode", 0))
            ipprot = kwargs.get("ipprot", "IPv4")
            self._kwargs["ipprot"] = ipprot
            self._kwargs["flowinfo"] = int(kwargs.get("flowinfo", 0))
            self._kwargs["scopeid"] = int(kwargs.get("scopeid", 0))
            # 0.0.0.0 (or :: on IPv6) binds to all host IP addresses
            host = "::" if ipprot == "IPv6" else "0.0.0.0"
            self._kwargs["hostip"] = kwargs.get("hostip", host)
            # amend default as required
            self._kwargs["port"] = kwargs.get("inport", None)
            self._kwargs["outport"] = int(
                kwargs.get(
                    "outport", OUTPORT_NTRIP if self._kwargs["ntripmode"] else OUTPORT
                )
            )
            # 5 is an arbitrary limit; could be significantly higher
            self._kwargs["maxclients"] = int(kwargs.get("maxclients", 5))
            self._kwargs["format"] = int(kwargs.get("format", FORMAT_BINARY))
            self._kwargs["verbosity"] = int(kwargs.get("verbosity", VERBOSITY_MEDIUM))
            self._kwargs["logtofile"] = int(kwargs.get("logtofile", 0))
            self._kwargs["logpath"] = kwargs.get("logpath", ".")
            # required fixed arguments...
            msgqueue = Queue()
            self._kwargs["outputhandler"] = msgqueue
            self._socket_server = None
            self._streamer = None
            self._in_thread = None
            self._out_thread = None
            self._clients = 0
            self._validargs = True
            self._logpath = ""
            self._logfile = ""
            self._loglines = 0

        except ValueError as err:
            self._do_log(
                f"Invalid input arguments {kwargs}\n{err}",
                VERBOSITY_LOW,
            )
            self._validargs = False

    def __enter__(self):
        """
        Context manager enter routine.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Context manager exit routine.

        Terminates SocketServer client threads in an orderly fashion.
        """

        self.stop()

    def run(self) -> int:
        """
        Run server.

        :return: rc 0 = fail, 1 = ok
        :rtype: int
        """

        if self._validargs:
            self._do_log("Starting server (type CTRL-C to stop)...", VERBOSITY_MEDIUM)
            self._in_thread = self._start_input_thread(**self._kwargs)
            sleep(0.5)
            if self._in_thread.is_alive():
                self._out_thread = self._start_output_thread(**self._kwargs)
                sleep(0.5)
                if self._out_thread.is_alive():
                    return 1
        return 0

    def stop(self):
        """
        Shutdown server.
        """

        self._do_log("Stopping server...", VERBOSITY_MEDIUM)
        if self._streamer is not None:
            self._streamer.stop()
        if self._socket_server is not None:
            self._socket_server.shutdown()
        self._do_log("Server shutdown.", VERBOSITY_MEDIUM)

    def _start_input_thread(self, **kwargs) -> Thread:
        """
        Start input (read) thread.

        :pararm dict kwargs: optional keyword args
        :return: thread
        :rtype: Thread
        """

        self._do_log(
            f"Starting input thread, reading from {kwargs['port']}...", VERBOSITY_MEDIUM
        )
        thread = Thread(
            target=self._input_thread,
            args=(kwargs,),
            daemon=True,
        )
        thread.start()
        return thread

    def _start_output_thread(self, **kwargs) -> Thread:
        """
        Start output (socket) thread.

        :pararm dict kwargs: optional keyword args
        :return: thread
        :rtype: Thread
        """

        self._do_log(
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

        self._streamer = GNSSStreamer(**kwargs)
        self._streamer.run()

    def _output_thread(self, app: object, kwargs):
        """
        THREADED

        Output (socket server) thread.
        """

        try:
            conn = format_conn(
                ipprot2int(kwargs["ipprot"]), kwargs["hostip"], kwargs["outport"]
            )
            with SocketServer(
                app,
                kwargs["ntripmode"],
                kwargs["maxclients"],
                kwargs["outputhandler"],
                conn,
                ClientHandler,
                ipprot=kwargs["ipprot"],
            ) as self._socket_server:
                self._socket_server.serve_forever()
        except OSError as err:
            self._do_log(f"Error starting socket server {err}", VERBOSITY_MEDIUM)

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
        self._do_log(
            f"Client {address} has {pre}connected. Total clients: {self._clients}",
            VERBOSITY_MEDIUM,
        )

    def _do_log(
        self,
        message: str,
        loglevel: int = VERBOSITY_MEDIUM,
    ):
        """
        Write timestamped log message according to verbosity and logfile settings.

        :param str message: message to log
        :param int loglevel: log level for this message (0,1,2)
        """

        msg = f"{datetime.now()}: {message}"
        if self._kwargs["verbosity"] >= loglevel:
            if self._kwargs["logtofile"]:
                self._cycle_log()
                with open(self._logfile, "a", encoding="utf-8") as log:
                    log.write(msg + "\n")
                    self._loglines += 1
            else:
                print(msg)

    def _cycle_log(self):
        """
        Generate new timestamped logfile path.
        """

        if not self._loglines % LOGLIMIT:
            tim = datetime.now().strftime("%Y%m%d%H%M%S")
            self._logfile = os.path.join(
                self._kwargs["logpath"], f"gnssserver-{tim}.log"
            )
            self._loglines = 0


def main():
    """
    CLI Entry point.

    :param int waittime: response wait time in seconds (1)
    :param: as per NSSSocketServer constructor.
    """

    arp = ArgumentParser(
        epilog=EPILOG,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    arp.add_argument("-V", "--version", action="version", version="%(prog)s " + VERSION)
    arp.add_argument("-I", "--inport", required=False, help="Input serial port")
    arp.add_argument("-S", "--socket", required=False, help="Input socket host:port")
    arp.add_argument(
        "-O",
        "--outport",
        required=False,
        help="Output TCP port",
        type=int,
        default=50010,
    )
    arp.add_argument(
        "--ipprot",
        required=False,
        help="IP protocol",
        choices=["IPv4", "IPv6"],
        default="IPv4",
    )
    arp.add_argument(
        "-H",
        "--hostip",
        required=False,
        help="Host IP Address Binding (0.0.0.0/:: = all)",
        default="0.0.0.0",
    )
    arp.add_argument(
        "-N",
        "--ntripmode",
        required=False,
        help="NTRIP Mode 0 = socket server, 1 = NTRIP caster",
        type=int,
        choices=[0, 1],
        default=0,
    )
    arp.add_argument(
        "--baudrate",
        required=False,
        help="Serial baud rate",
        type=int,
        choices=[4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800],
        default=9600,
    )
    arp.add_argument(
        "--timeout",
        required=False,
        help="Serial timeout in seconds",
        type=float,
        default=3.0,
    )
    arp.add_argument(
        "--format",
        required=False,
        help="Output format 1 = parsed, 2 = binary, 4 = hex, 8 = tabulated hex,"
        + "16 = parsed as string, 32 = JSON (can be OR'd)",
        type=int,
        default=2,
    )
    arp.add_argument(
        "-v",
        "--validate",
        required=False,
        help="1 = validate checksums, 0 = do not validate",
        type=int,
        choices=[0, 1],
        default=1,
    )
    arp.add_argument(
        "--msgmode",
        required=False,
        help="0 = GET, 1 = SET, 2 = POLL",
        type=int,
        choices=[0, 1, 2],
        default=0,
    )
    arp.add_argument(
        "--maxclients",
        required=False,
        help="Maximum number of clients",
        type=int,
        choices=range(1, 21),
        default=5,
    )
    arp.add_argument(
        "--parsebitfield",
        required=False,
        help="1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes",
        type=int,
        choices=[0, 1],
        default=1,
    )
    arp.add_argument(
        "--quitonerror",
        required=False,
        help="0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors",
        type=int,
        choices=[0, 1, 2],
        default=1,
    )
    arp.add_argument(
        "--protfilter",
        required=False,
        help="1 = NMEA, 2 = UBX, 4 = RTCM3 (can be OR'd)",
        type=int,
        default=7,
    )
    arp.add_argument(
        "--msgfilter",
        required=False,
        help="Comma-separated string of message identities e.g. 'NAV-PVT,GNGSA'",
        default=None,
    )
    arp.add_argument(
        "--limit",
        required=False,
        help="Maximum number of messages to read (0 = unlimited)",
        type=int,
        default=0,
    )
    arp.add_argument(
        "--verbosity",
        required=False,
        help="Log message verbosity 0 = low, 1 = medium, 2 = high, 3 = debug",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
    )
    arp.add_argument(
        "--outfile",
        required=False,
        help="Fully qualified path to output file",
        default=None,
    )
    arp.add_argument(
        "--waittime",
        required=False,
        help="Response wait time",
        type=int,
        default=1,
    )
    arp.add_argument(
        "--logtofile",
        required=False,
        help="0 = log to stdout, 1 = log to file '/logpath/gnssserver-timestamp.log'",
        type=int,
        choices=[0, 1],
        default=0,
    )
    arp.add_argument(
        "--logpath",
        required=False,
        help="Fully qualified path to logfile folder",
        default=".",
    )

    args = arp.parse_args()
    kwargs = vars(args)
    if kwargs["hostip"] == "0.0.0.0" and kwargs["ipprot"] == "IPv6":
        kwargs["hostip"] = "::"

    try:
        with GNSSSocketServer(**kwargs) as server:
            goodtogo = server.run()

            while goodtogo:  # run until user presses CTRL-C
                sleep(args.waittime)
            sleep(args.waittime)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
