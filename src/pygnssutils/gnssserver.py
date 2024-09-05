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

from logging import getLogger
from queue import Queue
from threading import Thread
from time import sleep

from pygnssutils.globals import FORMAT_BINARY, OUTPORT, OUTPORT_NTRIP
from pygnssutils.gnssstreamer import GNSSStreamer
from pygnssutils.helpers import format_conn, ipprot2int
from pygnssutils.socket_server import ClientHandler, SocketServer


class GNSSSocketServer:
    """
    GNSS Socket Server Class.
    """

    # pylint: disable=line-too-long

    def __init__(self, app=None, **kwargs):
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
        :param str ntripversion: (kwarg) NTRIP version "1.0", "2.0" ("2.0")
        :param str ntripuser: (kwarg) NTRIP caster authentication user ("anon")
        :param str ntrippassword: (kwarg) NTRIP caster authentication password ("password")
        :param int validate: (kwarg) 1 = validate checksums, 0 = do not validate (1)
        :param int parsebitfield: (kwarg) 1 = parse UBX 'X' attributes as bitfields, 0 = leave as bytes (1)
        :param int format: (kwarg) output format 1 = parsed, 2 = raw, 4 = hex, 8 = tabulated hex, 16 = parsed as string (1), 32 = JSON (can be OR'd)
        :param int quitonerror: (kwarg) 0 = ignore errors,  1 = log errors and continue, 2 = (re)raise errors (1)
        :param int protfilter: (kwarg) 1 = NMEA, 2 = UBX, 4 = RTCM3 (7 - ALL)
        :param str msgfilter: (kwarg) comma-separated string of message identities e.g. 'NAV-PVT,GNGSA' (None)
        :param int limit: (kwarg) maximum number of messages to read (0 = unlimited)
        """

        # Reference to calling application class (if applicable)
        self.__app = app  # pylint: disable=unused-private-member
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self.logger.debug(kwargs)
        try:
            self._kwargs = kwargs
            # overrideable command line arguments..
            # 0 = TCP Socket Server mode, 1 = NTRIP Server mode
            self._kwargs["ntripmode"] = int(kwargs.get("ntripmode", 0))
            self._kwargs["ntripversion"] = kwargs.get("ntripversion", "2.0")
            self._kwargs["ntripuser"] = kwargs.get("ntripuser", "anon")
            self._kwargs["ntrippassword"] = kwargs.get("ntrippassword", "password")
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
            # required fixed arguments...
            # msgqueue = Queue()
            # self._kwargs["outputhandler"] = msgqueue
            self._kwargs["output"] = Queue()
            self._socket_server = None
            self._streamer = None
            self._in_thread = None
            self._out_thread = None
            self._validargs = True

        except ValueError as err:
            self.logger.critical(f"Invalid input arguments {kwargs}\n{err}")
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
            self.logger.info("Starting server (type CTRL-C to stop)...")
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

        self.logger.info("Stopping server...")
        if self._streamer is not None:
            self._streamer.stop()
        if self._socket_server is not None:
            self._socket_server.shutdown()
        self.logger.info("Server shutdown.")

    def _start_input_thread(self, **kwargs) -> Thread:
        """
        Start input (read) thread.

        :pararm dict kwargs: optional keyword args
        :return: thread
        :rtype: Thread
        """

        self.logger.info(f"Starting input thread, reading from {kwargs['port']}...")
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

        self.logger.info(
            f"Starting output thread, broadcasting on {kwargs['hostip']}:{kwargs['outport']}..."
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
                kwargs["output"],
                conn,
                ClientHandler,
                ntripversion=kwargs["ntripversion"],
                ntripuser=kwargs["ntripuser"],
                ntrippassword=kwargs["ntrippassword"],
                ipprot=kwargs["ipprot"],
            ) as self._socket_server:
                self._socket_server.serve_forever()
        except OSError as err:
            self.logger.critical(f"Error starting socket server {err}")
