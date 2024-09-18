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

from pygnssutils.globals import NTRIP2, OUTPORT
from pygnssutils.gnssstreamer import GNSSStreamer
from pygnssutils.helpers import format_conn, ipprot2int
from pygnssutils.socket_server import ClientHandler, SocketServer


class GNSSSocketServer:
    """
    GNSS Socket Server Class.
    """

    def __init__(
        self,
        app=None,
        stream: object = None,
        ipprot: str = "IPv4",
        hostip: str = "0.0.0.0",
        outport: int = OUTPORT,
        maxclients: int = 5,
        ntripmode: int = 0,
        ntripversion: str = NTRIP2,
        ntripuser: str = "anon",
        ntrippassword: str = "password",
        **kwargs,
    ):
        """
        Context manager constructor.

        Example of usage:

        gnssserver inport=COM3 hostip=192.168.0.20 outport=50010 ntripmode=0

        :param object app: application from which this class is invoked (None)
        :param object stream: input datastream
        :param str ipprot: IP protocol IPv4/IPv6 ("IPv4")
        :param int hostip: host ip address (0.0.0.0)
        :param str outport: TCP port (50010)
        :param int maxclients: maximum number of connected clients (5)
        :param int ntripmode: 0 = socket server, 1 - NTRIP server (0)
        :param str ntripversion: NTRIP version "1.0"/"2.0" ("2.0")
        :param str ntripuser: NTRIP caster authentication user ("anon")
        :param str ntrippassword: NTRIP caster authentication password ("password")
        :param dict kwargs: optional keyword arguments to pass to GNSSStreamer
        """

        # Reference to calling application class (if applicable)
        self.__app = app  # pylint: disable=unused-private-member
        # configure logger with name "pygnssutils" in calling module
        self.logger = getLogger(__name__)
        self.logger.debug(kwargs)
        try:
            self._stream = stream
            self._ipprot = ipprot
            self._ntripmode = int(ntripmode)
            self._ntripversion = ntripversion
            self._ntripuser = ntripuser
            self._ntrippassword = ntrippassword
            self._hostip = hostip
            self._outport = int(outport)
            self._maxclients = int(maxclients)
            self._kwargs = kwargs
            self._output = Queue()
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

        self.run()
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

        :returns: rc 0 = fail, 1 = ok
        :rtype: int
        """

        if self._validargs:
            self.logger.info("Starting server (type CTRL-C to stop)...")
            self._in_thread = self._start_input_thread(**self._kwargs)
            sleep(0.5)
            if self._in_thread.is_alive():
                self._out_thread = self._start_output_thread()
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

        :param dict kwargs: optional keyword arguments to pass to GNSSStreamer
        :returns: thread
        :rtype: Thread
        """

        self.logger.info(f"Starting input thread, reading from {self._stream}...")
        thread = Thread(
            target=self._input_thread,
            args=(self._stream, self._output, kwargs),
            daemon=True,
        )
        thread.start()
        return thread

    def _start_output_thread(self) -> Thread:
        """
        Start output (socket) thread.

        :returns: thread
        :rtype: Thread
        """

        self.logger.info(
            f"Starting output thread, broadcasting on {self._hostip}:{self._outport}..."
        )
        thread = Thread(
            target=self._output_thread,
            args=(
                self._ipprot,
                self._hostip,
                self._outport,
                self._ntripmode,
                self._maxclients,
                self._output,
                self._ntripversion,
                self._ntripuser,
                self._ntrippassword,
            ),
            daemon=True,
        )
        thread.start()
        return thread

    def _input_thread(self, stream, output, kwargs):
        """
        THREADED

        Input (Serial reader) thread.

        :param object stream: input datastream
        :param Queue output: output queue
        :param dict kwargs: optional keyword arguments to pass to GNSSStreamer
        """

        with GNSSStreamer(self, stream, outqueue=output, **kwargs) as self._streamer:
            while True:
                sleep(1)

    def _output_thread(
        self,
        ipprot: str,
        hostip: str,
        outport: int,
        ntripmode: int,
        maxclients: int,
        output: object,
        ntripversion: int,
        ntripuser: str,
        ntrippassword: str,
    ):
        """
        THREADED

        Output (socket server) thread.

        :param str ipprot: IP protocol
        :param int hostip: host ip address
        :param str outport: TCP port
        :param int maxclients: maximum number of connected clients
        :param int ntripmode:
        :param str ntripversion: NTRIP version
        :param str ntripuser: NTRIP caster authentication user
        :param str ntrippassword: NTRIP caster authentication password
        """

        try:
            conn = format_conn(ipprot2int(ipprot), hostip, outport)
            with SocketServer(
                self,
                ntripmode,
                maxclients,
                output,
                conn,
                ClientHandler,
                ntripversion=ntripversion,
                ntripuser=ntripuser,
                ntrippassword=ntrippassword,
                ipprot=ipprot,
            ) as self._socket_server:
                self._socket_server.serve_forever()
        except OSError as err:
            self.logger.critical(f"Error starting socket server {err}")
